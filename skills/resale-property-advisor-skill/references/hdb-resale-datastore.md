# HDB Resale Prices (data.gov.sg v2 dataset flow)

The HDB Resale Price Index is published as a data.gov.sg dataset and accessed
via the v2 Collection/Dataset API (initiate-download → poll-download → fetch).
The skill wraps it as `fetch_dataset_rows(HDB_RESALE_DATASET_ID)` and filters
client-side by `month >= since`, `town`, `flat_type`.

## Endpoints

```
POST https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/initiate-download
GET  https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download
GET  <signed S3 URL from poll response>            # the CSV body
```

`DATASET_ID` is `d_8b84c4ee58e3cfc0ece0d773c8ca6abc` (canonical: see
`HDB_RESALE_DATASET_ID` in `singapore_api.py`). Headers:
`User-Agent: singapore-skills/0.1` is mandatory; `x-api-key: <DATA_GOV_SG_API_KEY>`
is included when the env var is set (v2 keys work for this endpoint; the
`v2:` prefix is preserved verbatim).

The dataset page on data.gov.sg: https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view

## Real (truncated) response

`fetch_dataset_rows()` returns a list of row dicts from the CSV body:

```python
[
  {
    "month": "2025-12",
    "town": "BISHAN",
    "flat_type": "5-ROOM",
    "block": "123",
    "street_name": "ANG MO KIO AVE 3",
    "storey_range": "10 TO 12",
    "floor_area_sqm": "121",
    "flat_model": "Improved",
    "lease_commence_date": "1989",
    "remaining_lease": "63 years 09 months",
    "resale_price": "685000.00"
  },
  ...
]
```

Date stamp: 2026-06-20. Schema version: as published by HDB via data.gov.sg.

## What the skill reads vs drops

The skill reads:
- `town` (filter exact match, case-insensitive)
- `flat_type` (filter exact match; e.g. "5-ROOM")
- `month` (YYYY-MM; filter `>= since`)
- `resale_price` (string, coerced via `to_float`)
- `block`, `street_name` (for per-flat estimates)

The skill drops:
- `floor_area_sqm`, `flat_model`, `lease_commence_date`, `remaining_lease` (not used by current premium calc)

## Pitfalls

1. **`resale_price` is a STRING, not a number.** Coerce at the boundary with `float(str(r["resale_price"]).replace(",", "").strip())`. Empty string fails — skip the record, don't crash.
2. **`town` casing changed.** HDB's v2 dataset ships uppercase ("BISHAN", "TAMPINES", "YISHUN") — the old CKAN source used lowercase. The skill uppercases both the data and the user's `--town` before filtering.
3. **`flat_type` uses uppercase with hyphen.** "5-ROOM", not "5 Room" or "5room". The skill normalises user input to "5-ROOM" before filtering.
4. **Date filter is `month >= since` and `month` is YYYY-MM.** The skill parses `--since 2025-12-01` and `2025-12` the same way (first 7 chars). A `since` of `2025-12-31` correctly includes all of December 2025.
5. **One fetch, no pagination.** The CSV is delivered as a single signed-S3 download; the v2 flow no longer requires limit/offset. A full dump is ~250k rows (~30 MB); cached after first fetch.
6. **`block` and `street_name` may be empty** in some records (HDB withholds for privacy in a small number of cases). The skill falls back to town-level stats.

## Related endpoints

The HDB Resale dataset has the same columns across monthly releases; no
pagination or filter parameters are exposed at the v2 initiate-download step.
For finer slicing (e.g. specific block or lease range), download the full
CSV and filter in memory.

## Cache

The skill uses the canonical `singapore_api._cache_get` / `_cache_put` helpers.
Cache namespace: `dataset:d_8b84c4ee58e3cfc0ece0d773c8ca6abc:rows` (no filters
in the current callers — single full-dump cache slot). Cache writes to
`~/.hermes/cache/dataset:d_8b84c4ee58e3cfc0ece0d773c8ca6abc/<sha1>.json`.
