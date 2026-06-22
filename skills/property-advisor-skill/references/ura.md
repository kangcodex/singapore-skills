# URA Data Sources

This skill uses four URA datasets. All are reached via the v2
initiate-poll-signed-URL flow in `singapore_api.fetch_dataset_rows()` (auth
header `x-api-key` from `DATA_GOV_SG_API_KEY` env, anonymous fallback).

For the full URA catalog (273 collections, including planning layers, price
indices, EC data, and historical transactions), see the canonical
[`docs/api/URA.md`](../../../docs/api/URA.md). This reference covers only the
8 datasets the property-advisor-skill consumes.

## Datasets used by this skill

| Dataset                                 | Collection | Frequency | Used by mode               |
| --------------------------------------- | ---------- | --------- | -------------------------- |
| `URA_RENTALS_DATASET_ID`                | 1660       | quarterly | rental, investment overlay |
| `URA_PRIVATE_RESI_TRANS_WHOLE_SG`       | 1658       | quarterly | private (whole_sg)         |
| `URA_PRIVATE_RESI_TRANS_CENTRAL`        | 1655       | quarterly | private (central)          |
| `URA_PRIVATE_RESI_TRANS_REST_CENTRAL`   | 1657       | quarterly | private (rest_central)     |
| `URA_PRIVATE_RESI_TRANS_OUTSIDE_CENTRAL`| 1656       | quarterly | private (outside_central)  |
| `URA_EC_SALES_DATASET_ID`               | 1643       | quarterly | ec                         |
| `URA_EC_POSITION_DATASET_ID`            | 1661       | quarterly | ec                         |
| `URA_UNSOLD_PRIVATE_RESI_DATASET_ID`    | 1663       | quarterly | investment overlay         |

The fetcher functions live in the shared `singapore_api` client:

- `fetch_ura_rentals()` — `d_149ac00a2734bb0a03867bbe2ec0e7b0`
- `fetch_ura_private_resi_trans(region)` — `region` ∈ `{whole_sg, central, rest_central, outside_central}`, raises `ValueError` on anything else
- `fetch_ura_ec_sales()` — `d_19c79027c2e6be3c39d637151bd2188d`
- `fetch_ura_ec_position()` — `d_8b71bc3e1386261039d7ad95efdc3328`
- `fetch_ura_unsold_private_resi()` — `d_84d05d45049108f0fd2e99b66bd19cfe`

## Data shapes (typical columns)

- **Rentals (1660)** — `qtr`, `region`, `property_type`, `median_rent_psf_pm`, `median_rent`
- **Private Resi Trans (1655–1658)** — `qtr`, `district`, `property_type`, `sale_count`, `median_psf`, `median_trans_price`
- **EC Sales (1643)** — `qtr`, `ec_name`, `units_launched`, `units_sold`
- **EC Position (1661)** — `qtr`, `ec_name`, `units_unsold`, `launch_year`
- **Unsold Private Resi (1663)** — `quarter`, `market_segment`, `unsold_units` (note: `quarter` not `qtr`)

## Quirks

- **Unsold Private Resi (1663)** has 0 `childDatasets` in the v2 catalog
  metadata, but the dataset itself is reachable via the v2 initiate-poll
  flow (verified 2026-06-22, 948 records).
- The `quarter` column in coll 1663 is not the same shape as the `qtr`
  column in 1655–1660. The skill's `_trailing_4q_demand` helper normalises
  both via the same key-fallback logic.
- URA datasets can take 30–60 s to respond on first hit. Caching is
  automatic via `request_json` (namespace `datastore|d_<resource_id>`).

## Cross-references

- Canonical URA catalog: [`docs/api/URA.md`](../../../docs/api/URA.md)
- Common residential dataset IDs table: in canonical `URA.md`, section
  "Residential Property Datasets"
- Shared client: [`singapore_api.py`](../../../singapore_api.py) (look for
  the `── Property data layer (S08) ──` section)
- Fetchers are smoke-tested in
  [`tests/test_singapore_api.py`](../../../tests/test_singapore_api.py) —
  class `TestS08PropertyFetchers`
