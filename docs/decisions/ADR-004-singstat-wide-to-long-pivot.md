# ADR-004: SINGSTAT wide-to-long pivot in the canonical client

## Status
Accepted

## Date
2026-06-22

## Context

Two SINGSTAT datasets power the `property-advisor-skill` investment-lens
overlay and could power future skills:

- `d_055b6549444dedb341c50805d9682a41` (Supply of Private Residential
  Properties In The Pipeline)
- `d_01e3556fb916ca19a7e29fc39520fa78` (Available And Vacant Private
  Residential Properties)

The SINGSTAT datastore uses the **legacy CKAN** API
(`https://data.gov.sg/api/action/datastore_search?resource_id=<id>`),
which is deprecated on data.gov.sg's v2 catalog (most new datasets
have migrated to a `initiate → poll → signed S3` flow, see ADR-007).

SINGSTAT, however, has not migrated. The two datasets ship in a
**wide format** that is incompatible with every other property dataset
in this codebase (URA, CEA, HDB), which use long format `[{quarter,
value, ...}]` or `[{qtr, property_type, sale_count, ...}]`.

A SINGSTAT row looks like:

```json
{
  "_id": 1,
  "DataSeries": "Available",
  "20261Q": 12345,
  "20254Q": 11800,
  "20251Q": 11000,
  "20244Q": "n/a"
}
```

— one row per series, with one column per quarter. The data is a
2D matrix encoded as a sparse hashmap of column names.

## Decision

Add `_pivot_quarterly_wide(records)` to canonical `singapore_api.py`:

```python
def _pivot_quarterly_wide(records: list[dict]) -> list[dict]:
    """Pivot SINGSTAT wide [{DataSeries, "20261Q": v, ...}] to long
    [{series, qtr, value}]. Skips _id, DataSeries, and non-numeric
    columns (e.g. "n/a" strings)."""
    out = []
    for rec in records:
        series = (rec.get("DataSeries") or "").strip()
        if not series:
            continue
        for k, v in rec.items():
            if k in ("_id", "DataSeries") or not k:
                continue
            try:
                value = float(v)
            except (TypeError, ValueError):
                continue
            out.append({"series": series, "qtr": k, "value": value})
    return out
```

The two public fetchers (`fetch_singstat_supply_pipeline`,
`fetch_singstat_vacancy`) call this pivot before returning, so the
rest of the codebase never sees the wide format.

`_normalize_qtr_label(s)` is also added: rewrites `"20261Q"` →
`"2026-Q1"`, `"2025 4Q"` → `"2025-Q4"`, `"2025-Q3"` → `"2025-Q3"`,
`"2025q3"` → `"2025-Q3"`. Non-matching inputs pass through unchanged.
This is the same normalisation every other property dataset already uses.

## Alternatives Considered

### Pivot at the call site in each skill
- Pros: No shared helper.
- Cons: The pivot logic is non-trivial (handles 4 different Q-label
  formats + non-numeric + sparse); every skill would re-implement it
  with subtle bugs.
- Rejected.

### Force SINGSTAT to migrate to v2
- Pros: Uniform with the rest of the data flow.
- Cons: We don't control SINGSTAT's release schedule; even if we
  asked, the migration would be measured in quarters, not days.
- Rejected: not actionable.

### Skip the SINGSTAT data and use URA's supply pipeline instead
- Pros: URA has a "supply pipeline" series (colls 1641, 1642).
- Cons: URA's supply pipeline is the **total** supply (EC + private +
  landed), not just private residential. SINGSTAT's data is the only
  source for private-only pipeline + vacancy.
- Rejected: the user explicitly asked for the private lens.

## Consequences

- **Pos:** The rest of the codebase uses long format consistently
  (`[{series, qtr, value}]`); the SINGSTAT quirk is contained inside
  the canonical client.
- **Pos:** `_normalize_qtr_label` is shared too, so a future SINGSTAT
  dataset doesn't need its own normaliser.
- **Pos:** A unit test (`test_pivot_quarterly_wide_handles_real_singstat_shape`)
  pins the contract: skips `_id` and `DataSeries` keys, drops
  non-numeric values, strips whitespace in series names.
- **Neg:** The pivot adds a small per-record CPU cost (one dict
  iteration per row). At 10 records per SINGSTAT dataset this is
  sub-millisecond.
- **Neg:** If SINGSTAT later switches to a v2 long-format API, the
  pivot becomes dead code. The fetcher's return shape would change,
  but the rest of the codebase wouldn't notice. Documented in the
  docstring.
