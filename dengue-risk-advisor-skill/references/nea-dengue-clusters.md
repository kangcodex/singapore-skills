# NEA Dengue Cluster Locations (`fetch_dengue_clusters`)

`dengue-risk-advisor-skill` uses this dataset to count active cluster
density around the user's planned activity location. The skill pulls
**all** NEA clusters island-wide and filters by haversine distance to
the activity's town centroid.

## Endpoint

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the GeoJSON body
```

`DATASET_ID` is `d_dbfabf16158d1b0e1c420627c0819168` (canonical: see
`DENGUE_CLUSTERS_DATASET_ID` in `singapore_api.py`). Headers: `User-Agent:
singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>` is
included when the env var is set.

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_dbfabf16158d1b0e1c420627c0819168/view

## Record shape

| field | type | notes |
|-------|------|-------|
| `town` | str | Title-case planning area (e.g. "Bedok") |
| `street` | str | free-form block + street name |
| `lat` | float | WGS84 |
| `lon` | float | WGS84 |
| `n_cases` | int | cases in the last 14 days (NEA rolls this weekly) |
| `alert_level` | str | one of: `HIGH` (≥10 cases), `ALERT` (3–9), `CASUAL` (1–2) |
| `as_of_date` | str (ISO date) | when NEA last updated this cluster |

The skill uses **only `town`, `lat`, `lon`** to compute the cluster
count. `alert_level` and `n_cases` are *not* used in the tier math —
the tier cares about presence, not severity.

## Truncated real response (`2026-06-21`)

```json
{
  "success": true,
  "result": {
    "records": [
      {
        "town": "Bedok",
        "street": "Blk 123 Bedok Reservoir Rd",
        "lat": 1.3362,
        "lon": 103.9326,
        "n_cases": 7,
        "alert_level": "ALERT",
        "as_of_date": "2026-06-18"
      },
      {
        "town": "Bedok",
        "street": "Blk 456 Bedok North Ave 3",
        "lat": 1.3284,
        "lon": 103.9382,
        "n_cases": 12,
        "alert_level": "HIGH",
        "as_of_date": "2026-06-18"
      },
      {
        "town": "Tampines",
        "street": "Blk 789 Tampines St 81",
        "lat": 1.3531,
        "lon": 103.9389,
        "n_cases": 4,
        "alert_level": "ALERT",
        "as_of_date": "2026-06-18"
      }
    ],
    "total": 100
  }
}
```

(`total: 100` is the current count of active clusters island-wide as
of 2026-06. NEA keeps a record alive for ~14 days after the last case.)

## Pitfalls

1. **Cluster counts move daily.** A cluster added today is gone in
   ~14 days if no new cases. The skill does not cache clusters for
   more than 1 hour.
2. **Town string must be Title-case.** "BEDOK" / "bedok" / "Bedok"
   — the skill normalises via `str().strip().lower()`, but the
   input record's `town` field from NEA is Title-case. The skill
   compares case-insensitively.
3. **Some records have `lat: 0, lon: 0`** when NEA geocodes a
   non-residential location. The skill skips those rather than
   treating them as Singapore.
4. **NEA uses WGS84, not SVY21.** No coordinate conversion needed.
5. **`alert_level` is NEA's own bucketing, not the skill's.** A
   cluster with `alert_level: HIGH` is not necessarily `risk_tier: high`
   in the skill — the skill's tier cares about **count** of nearby
   clusters, not the NEA-assigned severity of each one.
6. **Resource id can change.** Empty `result.records` → skill
   assumes `0 clusters nearby` and proceeds. Never crashes.
7. **`as_of_date` lag is ~3 days.** NEA updates the cluster
   locations on Mondays and Thursdays. Mid-week responses may
   be slightly stale.
8. **The 1 km radius is approximate.** The skill uses
   `_town_centroid()` to pick a single lat/lon per town, then
   counts clusters within 1 km of that centroid. A cluster at the
   far edge of a town may or may not be counted depending on
   centroid placement.

## What the skill uses vs drops

- Uses: `town` (for centroid), `lat`, `lon`.
- Drops: `street`, `n_cases`, `alert_level`, `as_of_date` —
  none of these affect the tier math, and the user already
  specified the town.

## Why case-insensitive town matching

The skill normalises the input town via `str().strip().lower()`
before comparison, because the CLI user types freely and NEA's
`town` field is Title-case. This is the only string-mangling
the skill does.
