# NEA Historical Monthly Rainfall (data.gov.sg v2 dataset flow)

NEA publishes monthly total rainfall (mm) for ~30 weather stations across
Singapore. The skill uses 60 months of data to classify the last 24 months
against a 5-year mean.

## Endpoints

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the CSV body
```

`DATASET_ID` is `d_b16d06b83473fdfcc92ed9d37b66ba58` (canonical: see
`NEA_RAINFALL_DATASET_ID` in `singapore_api.py`). Headers: `User-Agent:
singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>` is
included when the env var is set.

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_b16d06b83473fdfcc92ed9d37b66ba58/view

## Real (truncated) response

`fetch_dataset_rows()` returns a list of row dicts from the CSV body:

```python
[
  {"station_id": "S123", "month": "2025-12", "total_rainfall_mm": "240.5", "station_name": "Newton"},
  {"station_id": "S123", "month": "2025-11", "total_rainfall_mm": "198.3", "station_name": "Newton"},
  ...
]
```

Date stamp: 2026-06-20. Records sorted by month desc; oldest at the tail.

## What the skill reads vs drops

The skill reads:
- `total_rainfall_mm` (string, coerced via `to_float`)
- `month` (YYYY-MM; first 24 = recent, next 36 = 5-year baseline)

The skill drops:
- `station_name` (cosmetic)
- per-station selection is done via the `station_id` filter (a v2
  `filters=[{"columnName": "station_id", "type": "EQ", "value": "S123"}]`)

## Classification rule

```
recent_24mo = mean(total_rainfall_mm[-24:])  # last 24 months
five_year_avg = mean(total_rainfall_mm)       # 60 months
std_dev = pstdev(total_rainfall_mm)           # over 60 months

if recent_24mo > five_year_avg + 1σ: classification = "above-average"
elif recent_24mo < five_year_avg - 1σ: classification = "below-average"
else: classification = "typical"
```

The 1σ threshold is a heuristic. It catches a true wet spell (recent > 1 std
dev above baseline) without flagging normal seasonal variation.

## Pitfalls

1. **Records can be `null` or empty for a month** (sensor outage, station
   decommissioned). The skill filters these out via `to_float` and an
   `if v is not None` guard. An empty 60-month list → `classification: "unknown"`.
2. **`month` field is text, not date.** Some records use "2025-12", others
   use "Dec-2025", others "2025/12". The skill does NOT parse `month`; it
   relies on record order (most recent first).
3. **One station is a poor sample.** Singapore's weather is island-wide
   spatially correlated, so a single station is a reasonable proxy. But
   stations in the West (e.g. Jurong) read ~10% more rain than stations in
   the East (e.g. Tampines) on average. A future slice could weight by town
   centroid → nearest station distance.
4. **The 5-year window is fixed at 60 months.** NEA keeps 10+ years of
   history. The skill could take a `--baseline-years` flag; out of scope.
5. **`pstdev` (population stdev) vs `stdev` (sample stdev).** The skill uses
   `pstdev` to keep the threshold stable across small samples. Switching to
   `stdev` would change the threshold by ~1% — negligible for this use case
   but worth noting if you compare outputs.
6. **The verdict is a town-level signal, not a flood prediction.** A
   `typical` verdict does NOT mean the town is flood-free. The skill is
   contextual ("this town has been wetter than baseline"), not predictive.
7. **Rainfall in Singapore is bimodal.** NE monsoon (Dec–Mar) and SW monsoon
   (Jun–Sep) are wet; inter-monsoon (Apr–May, Oct–Nov) is dry. The 24-month
   vs 5-year comparison washes out the seasonal signal, which is what the
   skill wants (long-term trend, not this-week's storm).

## Related endpoints

- NEA 2-hour weather forecast (real-time; v1 endpoint, no dataset flow)
- NEA daily rainfall (different dataset; not used by the skill)

## Cache

Cache namespace: `dataset:d_b16d06b83473fdfcc92ed9d37b66ba58:<filter-hash>` —
the filter hash is sha1 of the filter list, so the same station always hits
the same cache slot. Cache writes to
`~/.hermes/cache/dataset:d_b16d06b83473fdfcc92ed9d37b66ba58/<sha1>.json`.
Refreshed when the upstream `Last-Modified` changes (typically monthly).
