# NEA Hawker Cleaning Schedule (`fetch_hawker_closures`)

`weekend-planner-skill` and `hawker-discover-skill` share this dataset.
Returns the **full** hawker-centre list, not just closures — the skill
filters for "closed now" by comparing the cleaning window to today's date.

## Endpoint

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the CSV body
```

`DATASET_ID` is `d_bda4baa634dd1cc7a6c7cad5f19e2d68` (canonical: see
`NEA_HAWKER_CLOSURES_DATASET_ID` in `singapore_api.py`). Headers: `User-Agent:
singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>` is
included when the env var is set.

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view

## Record shape

Each record in `result.records` is a hawker centre:

| field | type | notes |
|-------|------|-------|
| `name` | str | e.g. "Tiong Bahru Market" |
| `lat` / `lon` | float | WGS84 (CKAN stores WGS84, **not** SVY21) |
| `address_myenv` | str | block + street |
| `next_closure_start` | str (ISO date) | e.g. `2026-07-01` |
| `next_closure_end` | str (ISO date) | inclusive of the start day |
| `closure_reason` | str | always "Quarterly Cleaning" in v1 |

## Quarterly cleaning pattern

NEA cleans every hawker centre **once every three months** for ~14 days.
A given hawker is "closed today" iff `today in [next_closure_start, next_closure_end]`.
The skill computes this in pure Python — no API-side filter.

## Truncated real response (`2026-06-21`)

```json
{
  "success": true,
  "result": {
    "records": [
      {
        "name": "Tiong Bahru Market",
        "address_myenv": "30 Seng Poh Rd, Singapore 168898",
        "lat": 1.2846,
        "lon": 103.8271,
        "next_closure_start": "2026-08-03",
        "next_closure_end": "2026-08-16",
        "closure_reason": "Quarterly Cleaning"
      },
      {
        "name": "Maxwell Food Centre",
        "address_myenv": "1 Kadayanallur St, Singapore 069184",
        "lat": 1.2803,
        "lon": 103.8447,
        "next_closure_start": "2026-06-15",
        "next_closure_end": "2026-06-28",
        "closure_reason": "Quarterly Cleaning"
      }
    ],
    "total": 117
  }
}
```

(`2026-06-21` falls in Maxwell's cleaning window — that's why the
weekend-planner skill would pivot Maxwell to the nearest open hawker.)

## Pitfalls

1. **`next_closure_*` is the *next* closure, not the current one.** A
   record with `next_closure_start = 2026-08-03` is **open** today.
   The skill filters for "closed today" by date arithmetic, not by
   string match.
2. **The dates are inclusive on both ends.** A centre with
   `2026-06-15 → 2026-06-28` is closed on 2026-06-15 and 2026-06-28.
3. **WGS84, not SVY21.** Unlike URA's Master Plan, NEA stores lat/lon
   directly. `svy21_to_wgs84` from `singapore_api` is **not** needed
   for hawker centres.
4. **Total record count is ~117** as of 2026-06. `limit=500` is a
   safe upper bound but if NEA adds new centres, bump the limit.
5. **Resource id can change.** data.gov.sg is free to rotate the
   UUID for the same dataset. The skill treats empty `result.records`
   as "no data" and surfaces a `hawker_closures: []` block — never
   crashes.
6. **`closure_reason` is always "Quarterly Cleaning" in v1.** If
   NEA adds ad-hoc closures (post-flood repairs, say), they will
   appear with new reason strings; the skill does not branch on
   reason text.

## What the skill uses vs drops

- Uses: `name`, `lat`, `lon`, `next_closure_start`, `next_closure_end`.
- Drops: `address_myenv` (the user already typed a location), all
  remaining administrative fields, the `total` count.

## Sharing with S06a

`hawker-discover-skill` uses the same helper. Both skills filter
the result for "closed now" independently. The shared module returns
the **whole** list because each skill filters differently:
`weekend-planner` filters for "target hawker is closed, suggest nearest open",
`hawker-discover` filters for "any open hawker within radius".
