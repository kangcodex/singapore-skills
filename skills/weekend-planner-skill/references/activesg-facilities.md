# ActiveSG Facilities (`fetch_activesg_facilities`)

`weekend-planner-skill` uses this dataset as the **indoor pivot** when
UV ≥ 11 or PSI ≥ 101. The skill picks the nearest indoor facility by
haversine distance from the user's geocoded location.

## Endpoint

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the GeoJSON body
```

`DATASET_ID` is `d_9b87bab59d036a60fad2a91530e10773` (canonical: see
`SPORTSG_FACILITIES_DATASET_ID` in `singapore_api.py`). Headers: `User-Agent:
singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>` is
included when the env var is set.

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_9b87bab59d036a60fad2a91530e10773/view

## Record shape

| field | type | notes |
|-------|------|-------|
| `name` | str | e.g. "Our Tampines Hub Swimming Complex" |
| `lat` / `lon` | float | WGS84 |
| `indoor` | bool | `True` for sports halls, gyms, indoor swimming complexes; `False` for stadiums, fields |
| `facility_type` | str | e.g. `SWIMMING`, `GYM`, `SPORTS_HALL`, `STADIUM`, `TENNIS` |
| `operating_hours` | str | free-form ("06:00–22:00 daily") |
| `postal_code` | str | 6-digit Singapore postal |

## Truncated real response (`2026-06-21`)

```json
{
  "success": true,
  "result": {
    "records": [
      {
        "name": "Our Tampines Hub Swimming Complex",
        "facility_type": "SWIMMING",
        "indoor": true,
        "lat": 1.3526,
        "lon": 103.9401,
        "postal_code": "529510",
        "operating_hours": "06:00–22:00 daily"
      },
      {
        "name": "Bishan Stadium",
        "facility_type": "STADIUM",
        "indoor": false,
        "lat": 1.3625,
        "lon": 103.8480,
        "postal_code": "579700",
        "operating_hours": "06:00–22:00 daily"
      }
    ],
    "total": 314
  }
}
```

## Pitfalls

1. **`indoor` is a bool, but JSON may render it as the string `"True"`/`"False"`** (CKAN quirk — depends on the underlying PostgreSQL type). The skill uses `str(v).lower() == "true"` to be defensive.
2. **314 total facilities as of 2026-06.** `limit=1000` is a safe upper bound; if ActiveSG adds new facilities, the limit still covers them.
3. **The pivot only filters `indoor: True`.** A `STADIUM` or outdoor `TENNIS` court is excluded even if it's the nearest — staying outdoor under extreme UV is the wrong call.
4. **`facility_type` values are uppercase English constants.** SWIMMING, GYM, SPORTS_HALL, etc. The skill does not branch on type (any indoor facility is acceptable for a generic "go indoors" pivot).
5. **WGS84 directly.** No SVY21 conversion needed; NEA / ActiveSG store lat/lon.
6. **Resource id can change.** Empty `result.records` → skill returns `alternates: []` and tells the user to find shelter manually. No crash.
7. **Operating hours are free-form text.** The skill does **not** parse them to check "is it open right now". If a user asks at 02:00, the skill still recommends a closed facility. This is a known limitation — see Out-of-Scope in `weekend-planner-skill/SKILL.md`.

## What the skill uses vs drops

- Uses: `name`, `lat`, `lon`, `indoor`.
- Drops: `operating_hours`, `postal_code` (not relevant for "go indoors" recommendation), `facility_type` (skill is type-agnostic for the indoor pivot).

## Indoor pivot ranking

The skill ranks indoor facilities by haversine distance from the user's
geocoded location and returns the top 3 as `alternates[]`. The agent
then asks the user to pick one (or generate a fresh recommendation).
