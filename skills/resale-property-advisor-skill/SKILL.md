---
name: resale-property-advisor-skill
description: "Evaluate a Singapore HDB resale asking price. Compares against the cluster baseline for town + flat-type since a date, scans URA Master Plan for future amenities within 1 km (MRT, school, healthcare), and contextualises with NEA rainfall history. Outputs a JSON verdict (fair / premium justified / above market) and a recommendation string. Use when the user asks 'is this asking price fair?', 'should I pay X for a HDB in Y?', or 'evaluate this resale flat'."
---

# resale-property-advisor-skill

A Singapore HDB resale value advisor. Given a town, flat type, date window, and asking price, computes the cluster baseline and overlays two context signals: (a) URA Master Plan future amenities within 1 km of the cluster centroid, (b) NEA historical rainfall for the past 24 months. Output is a JSON verdict and a recommendation string.

## Quick Start

```bash
python3 skills/resale-property-advisor-skill/scripts/resale_property_advisor.py \
    --town BISHAN --flat-type 5-ROOM --since 2025-12-01 --asking 720000
```

Stdlib only — no `pip install`. Auth: reads `DATA_GOV_SG_API_KEY` from env if set; works anonymously otherwise (lower rate limit).

## Triggers

Run this skill when the user says any of:

- "Is $720k a fair price for a 5-room in Bishan?"
- "Should I pay X for a resale HDB in Y?"
- "Evaluate this resale flat for me"
- "Compare this asking price to recent transactions in TOWN"
- "Future amenity uplift for resale at TOWN"

Do not run for: new BTO prices (no resale baseline), private condo (no HDB datastore fit), commercial properties.

## The verdict scale

| Verdict | Premium % | URA amenities | Rainfall | Recommendation |
|---|---|---|---|---|
| `fair` | ≤ 5% | any | any | Reasonable offer; proceed with inspection. |
| `premium justified` | 5–10% | ≥ 2 within 1 km | not above-average | Premium is structurally supported. |
| `premium justified` | > 10% | ≥ 2 within 1 km | not above-average | Future uplift justifies the premium. |
| `above market` | > 5% | < 2 within 1 km | any | Negotiate down toward baseline. |
| `above market` | > 0% | any | above-average | Rainfall + low amenity; weak case. |

## Workflow

1. **Parse CLI args.** `--town BISHAN --flat-type 5-ROOM --since 2025-12-01 --asking 720000`. Flat type must be one of `1-ROOM / 2-ROOM / 3-ROOM / 4-ROOM / 5-ROOM / EXEC / MULTI-GEN / STUDIO`.
2. **Fetch HDB resale records.** `fetch_dataset_rows(HDB_RESALE_DATASET_ID)` returns the full CSV. Filter client-side to `month >= since` and `town` / `flat_type` match. (See `references/hdb-resale-datastore.md`.)
3. **Compute cluster average.** Mean of `resale_price` across the filtered set. Coerce strings to float at the boundary (the API ships `resale_price` as a string).
4. **Premium %** = `(asking - cluster_avg) / cluster_avg * 100`. Rounded to 1 dp.
5. **URA future amenities.** Load URA Master Plan (1000-record page). Compute cluster centroid as mean of available `_x`/`_y` in the filtered HDB records (HDB datastore does not ship lat/lon). Convert centroid to WGS84 via `svy21_to_wgs84()`. For each URA feature within 1 km (haversine), categorise by `lu_desc` / `mpro_use` and dedupe to a sorted list of `{primary_school, healthcare, MRT, business_hub, industrial}`. If centroid is missing, geocode the town centre instead.
6. **Rainfall history.** Last 24 months vs 5-year mean. `fetch_nea_historical_rainfall(months=60)`. If 24-month mean > 5-year mean + 1σ → `above-average`; if < mean - 1σ → `below-average`; else `typical`.
7. **Verdict.** See table above. ≥ 3 distinct strings emitted across the verdict + recommendation.
8. **Output JSON.** All fields per the PRD: `town`, `flat_type`, `cluster_avg`, `premium_pct`, `verdict`, `future_amenities[]`, `rainfall_history`, `recommendation`.

## Output shape (canonical)

```json
{
  "town": "BISHAN",
  "flat_type": "5-ROOM",
  "since": "2025-12-01",
  "asking": 720000,
  "cluster_avg": 698543.21,
  "premium_pct": 3.1,
  "verdict": "fair",
  "future_amenities": ["MRT", "primary_school"],
  "rainfall_history": {
    "classification": "typical",
    "recent_24mo_mm": 168.4,
    "five_year_avg_mm": 172.1
  },
  "recommendation": "Asking $720,000 is within 3.1% of the $698,543 cluster average..."
}
```

## Caching

All upstream calls go through `singapore_api.request_json`, which writes to `~/.hermes/cache/<namespace>/<sha1>.json`. Second invocation within the cache window (until upstream `Last-Modified` changes) is free.

Namespaces used:
- `datastore|d_<hdb_resale_resource_id>` for HDB resale
- `datastore|d_<ura_master_plan_resource_id>` for URA
- `datastore|d_<nea_historical_rainfall_resource_id>` for rainfall

## Hardening

- **HDB resale_price is a string, not a number.** Coerce at the boundary (`float(...)`); empty string is filtered.
- **URA fields vary by record.** Some use `_x`/`_y`, some `x`/`y`/`easting`/`northing`. The `cluster_centroid_easting_northing` helper tries all keys.
- **URA records are large.** Always request `limit=1000`; if the dataset grows past that, the script will silently drop overflow records. The cluster centroid is still accurate when the missing tail is random.
- **Empty URA result is not an error.** `future_amenities: []` is the documented response when no features match.
- **No HDB records in the window** → `ValueError("no HDB resale records for ...")`. The script catches it and prints `{"error": "..."}` with exit code 0.
- **No network at import.** `singapore_api` is lazy; no top-level calls.

## Pitfalls

- The HDB datastore does **not** ship lat/lon. The URA scan uses the HDB cluster centroid (mean of available `_x`/`_y`), not a single transaction. If only 1 record has coordinates, the centroid is that record's coordinate.
- The URA Master Plan is a future-amenity view, not a current view. Schools marked "proposed" in 2024 may have opened in 2025; the script reports what's in the dataset, not ground truth.
- The 1σ rainfall threshold is a heuristic, not a flood-risk classification. A `typical` verdict does not mean the town is flood-free.
- NEA historical rainfall is station-level. Stations are sparse; the script uses the first station returned. A future enhancement would let the user pick a station.
- The 1 km URA radius is a default. Town centres are 600–800 m wide; a 1 km scan catches nearby amenity but not adjacent-town amenities.
- `cluster_avg` is a simple mean, not a median. A few high-rise Pinnacle@Duxton sales will skew the mean for the central region. The skill reports the mean honestly and leaves weighted statistics for a future slice.

## Tests

Smoke tests use stdlib `unittest` + `unittest.mock` to stub all three fetchers and `geocode`:

```bash
python3 -m unittest discover -s skills/resale-property-advisor-skill/tests
```

The suite covers:
- Premium math: `premium_pct(720000, 700000) == 2.857...`
- HDB string-as-number coercion
- URA centroid fallback to geocode when HDB records lack coordinates
- URA haversine 1 km radius check
- Rainfall classification: above-average / typical / below-average
- Verdict matrix: all 5 cells in the table above
- Empty URA result, empty HDB result, geocode failure

## Install

```bash
npx skills add kangcodex/singapore-skills --skill resale-property-advisor-skill
```

The skill ships `scripts/singapore_api.py` as a per-skill copy (synced from the canonical at the repo root via `scripts/sync_singapore_api.py`). No runtime dependency on the parent repo.
