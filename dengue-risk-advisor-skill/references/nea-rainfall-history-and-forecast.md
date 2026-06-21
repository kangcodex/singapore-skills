# NEA Rainfall: History + Forecast (`fetch_nea_historical_rainfall`, `fetch_rainfall`)

`dengue-risk-advisor-skill` combines two rainfall sources to score
the "above-average rain?" decision:

- **History** — `fetch_nea_historical_rainfall(months=24)` — gives
  the 24-month baseline.
- **Forecast** — `fetch_rainfall()` (current reading) — extrapolated
  × 7 as a 7-day forecast proxy.

This document explains both endpoints, the extrapolation reasoning,
and the "above-average" formula. For the full tier math, see
`risk-scoring.md`.

## History — `fetch_nea_historical_rainfall(months=24)`

### Endpoint

```
GET https://api.data.gov.sg/v1/environment/rainfall-monthly-total
    ?date=YYYY-MM-DD
```

The skill calls it with `months=24` (no date param → server returns
the last 24 months by default). Public, no auth.

### Record shape

Each record is one **monthly** total for one station:

| field | type | notes |
|-------|------|-------|
| `month` | str | YYYY-MM (e.g. "2026-05") |
| `station_id` | str | NEA station code (e.g. "S06") |
| `station_name` | str | free-form ("Ang Mo Kio") |
| `rainfall_mm` | float | **monthly** total, in millimetres |
| `value` | float | alias for `rainfall_mm` (depending on parser) |

The skill pulls the full 24-month table (no station filter) and
takes the **mean across all stations** to get a single number per
month. The dataset contains rows per station, so 24 months × 30
stations = ~720 rows.

### Truncated real response (`2026-06-21`)

```json
{
  "success": true,
  "result": {
    "records": [
      {"month": "2026-05", "station_id": "S06", "station_name": "Ang Mo Kio", "rainfall_mm": 165.2},
      {"month": "2026-05", "station_id": "S07", "station_name": "Bukit Panjang", "rainfall_mm": 178.4},
      {"month": "2026-05", "station_id": "S08", "station_name": "Bukit Timah", "rainfall_mm": 210.6},
      ...
    ]
  }
}
```

## Forecast — `fetch_rainfall()`

### Endpoint

```
GET https://api.data.gov.sg/v1/environment/rainfall
```

Returns the **most recent** reading for every station.

### Record shape (v1, real-time)

```json
{
  "items": [
    {
      "timestamp": "2026-06-21T17:00:00+08:00",
      "readings": [
        {"station_id": "S06", "value": 0.0},
        {"station_id": "S07", "value": 0.4},
        ...
      ]
    }
  ]
}
```

The skill takes the **max** value across all stations (or the first
non-zero reading) as the "current" reading. If all are 0, the
forecast is 0 (a dry week).

## The "7-day forecast" is an extrapolation

NEA does **not** publish a 7-day cumulative rainfall forecast. The
skill uses:

```
forecast_7d_mm = current_reading_mm * 7
```

This is a deliberately crude proxy. It is:
- **Correct in dry weeks** (current = 0 → forecast = 0).
- **Reasonable in light-rain weeks** (current = 1 mm/h × 7 days = 168 mm — overshoots the real weekly total of ~30 mm but the tier math still works because the historical mean is also ~150 mm).
- **Overshoots in heavy-rain weeks** (current = 5 mm/h × 7 = 350 mm). This biases toward "elevated" tier — acceptable for a **conservative** risk advisor.

The skill explicitly notes this limitation in `SKILL.md` Pitfalls #3.

## "Above-average rain" formula

```python
forecast_7d = current_reading * 7
avg_7d = mean(monthly_mm_over_24_months) * 7 / 30
std_7d = pstdev(monthly_mm_over_24_months) * 7 / 30
above_average = forecast_7d > (avg_7d + std_7d)
```

The `7/30` factor converts "monthly mean" to "expected 7-day total"
(assuming rainfall is uniform across the month). The `+ 1σ` threshold
is a deliberate cushion — the skill wants to flag genuinely unusual
weeks, not normal variation.

## Pitfalls

1. **`pstdev` of 12 values is wrong for "true" population stdev.** The
   skill uses `pstdev` (population, divides by N) not `stdev` (sample,
   divides by N-1). This is intentional — we have all 24 months of
   the recent window, not a sample of a larger population.
2. **Station count varies by year.** NEA has ~30 stations now but
   some are <5 years old. The skill does not weight by station
   maturity.
3. **Missing months** (sensor outage) appear as gaps in the
   record list. The skill skips records with `rainfall_mm: null`
   rather than treating them as 0. Skipped records reduce the
   sample size, which can drop below the 12-month minimum and
   push the tier to `unknown`.
4. **The 7-day forecast is per-hour, not per-day.** `fetch_rainfall`
   returns instantaneous readings (mm/h). The skill's `× 7` assumes
   a full week of the same intensity — a known bias.
5. **LTA's `fetch_rainfall` is the v1 endpoint**, not v2. v2 has
   the same data but requires an API key. The skill's
   `try_v2_then_v1` falls back gracefully.
6. **El-Niño / La-Niña years skew the baseline.** The 24-month
   window means the most recent ENSO state dominates. The skill
   makes no adjustment for this.

## What the skill uses vs drops

- Uses: monthly `rainfall_mm` (history), current `value` (forecast).
- Drops: `station_id` / `station_name` (the skill averages across
  stations; the user did not specify a station), `timestamp` (the
  monthly historical data is already bucketed).
