# SINGSTAT Data Sources

This skill uses two SINGSTAT datasets, both via the **legacy CKAN**
`datastore_search` endpoint (the v2 collections catalog has no SINGSTAT
entry as of 2026-06-22).

For the full SINGSTAT catalog and download flow, see the canonical
[`docs/api/SINGSTAT.md`](../../../docs/api/SINGSTAT.md).

## Datasets used by this skill

| Dataset                            | Resource ID                                | Frequency | Used by mode               |
| ---------------------------------- | ------------------------------------------ | --------- | -------------------------- |
| `SINGSTAT_SUPPLY_PIPELINE_DATASET_ID` | `d_055b6549444dedb341c50805d9682a41`    | quarterly | investment overlay         |
| `SINGSTAT_VACANCY_DATASET_ID`      | `d_01e3556fb916ca19a7e29fc39520fa78`        | quarterly | investment overlay         |

The fetcher functions live in the shared `singapore_api` client:

- `fetch_singstat_supply_pipeline()` — pivot of 10 series across quarters
- `fetch_singstat_vacancy()` — pivot of 6 series across quarters

## Data shapes (after pivot)

The SINGSTAT datasets ship in **wide** format with one row per
`DataSeries` and one column per quarter (column name like `20261Q`,
`20254Q`, `2025-Q3`, or `2025 4Q`). The shared client normalises to
**long** format:

```json
[
  {"series": "In Planning", "qtr": "2026-Q1", "value": 5000.0},
  {"series": "Under Construction", "qtr": "2026-Q1", "value": 8000.0},
  ...
]
```

The property-advisor-skill's `investment_overlay_for` helper sums
"Under Construction" + "Completed but unsold" from the supply pipeline
and pairs it with `unsold_units` from the URA unsold dataset. The
`_trailing_4q_demand` is computed from the URA Private Resi Trans
`sale_count` column (last 4 quarters).

## Quirks

- **Not in v2 catalog.** SINGSTAT is the only major publisher that has
  not migrated to the v2 collections endpoint. The legacy CKAN
  `datastore_search` still works for these resource IDs as of
  2026-06-22, but the URL pattern (`datastore_search?resource_id=...`)
  is the same one that has been broken for every other publisher.
  Watch for silent breakage.
- **Wide-to-long pivot** is non-trivial because column names vary across
  resource IDs. The shared client normalises via the regex in
  `_normalize_qtr_label` — see `singapore_api.py` for the full set of
  supported shapes.
- The CKAN `datastore_search` endpoint has a documented 10 000-row
  limit. SINGSTAT's residential datasets are well under that
  (≤10 series × ~30 quarters = ~300 rows).
- Errors (network, JSON parse, HTTP 5xx) are caught and return `[]`.
  Downstream code should treat an empty SINGSTAT result as "no
  overlay" rather than a hard failure.

## Cross-references

- Canonical SINGSTAT catalog: [`docs/api/SINGSTAT.md`](../../../docs/api/SINGSTAT.md)
- Shared client: [`singapore_api.py`](../../../singapore_api.py) (look for
  `_fetch_singstat_ckan` and `_pivot_quarterly_wide`)
- Fetchers are smoke-tested in
  [`tests/test_singapore_api.py`](../../../tests/test_singapore_api.py) —
  class `TestS08PropertyFetchers`, methods
  `test_fetch_singstat_supply_pipeline_uses_ckan_and_pivots` and
  `test_fetch_singstat_vacancy_uses_ckan_and_pivots`
