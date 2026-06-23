# CEA Salespersons' Property Transaction Records (coll 55)

Monthly CEA-disclosed property transactions closed by registered salespersons. Used by the `agent-match-skill` for track-record enrichment (counting closed deals per salesperson in a given town + flat type).

## Dataset

- **ID:** `d_ee7e46d3c57f7865790704632b0aef71`
- **Collection:** 55
- **Agency:** "Council For Estate Agencies" (exact case, capital F)
- **Refresh:** monthly
- **Record count:** ~30,000 (last 12 months, residential only)

## Fetcher

```python
from singapore_api import fetch_cea_transaction_records

# All records (last 12 months)
all_transactions = fetch_cea_transaction_records()

# Filter by town (e.g. "BISHAN")
bishan = fetch_cea_transaction_records(town="BISHAN")

# Filter by town + flat type
bishan_5room = fetch_cea_transaction_records(town="BISHAN", flat_type="5-ROOM")

# Filter by date (YYYY-MM lower bound)
recent = fetch_cea_transaction_records(since="2025-01")

# All three filters
filtered = fetch_cea_transaction_records(
    town="BISHAN", flat_type="5-ROOM", since="2025-06"
)
```

Filters are applied client-side after the full CSV is downloaded. The underlying CKAN resource is ~30k rows; filtering shaves that to a few hundred for typical queries.

## Schema

| Field                  | Type   | Description                                                                 |
| ---------------------- | ------ | --------------------------------------------------------------------------- |
| `transaction_id`       | str    | Unique CEA-assigned transaction ID                                          |
| `transaction_date`     | str    | ISO date (YYYY-MM-DD) the transaction was lodged                            |
| `salesperson_reg_no`   | str    | CEA registration number of the closing salesperson (joins to coll 54)        |
| `salesperson_name`     | str    | Salesperson name as disclosed on the transaction                             |
| `agency`               | str    | Agency name as disclosed                                                     |
| `property_type`        | str    | `HDB` \| `Private` \| `EC` \| `Landed`                                      |
| `district`             | str    | Singapore postal district (e.g. "D09", "D23")                               |
| `town`                 | str    | HDB town name (only for `property_type == "HDB"`)                            |
| `flat_type`            | str    | HDB flat type (only for `property_type == "HDB"`); e.g. `5-ROOM`              |
| `sale_type`            | str    | `resale` \| `new` \| `sub-sale`                                              |
| `trans_price`          | float  | Transaction price in SGD (numeric; not a string)                            |

## Quirks

- **`trans_price` is numeric, not a string.** Other CEA datasets sometimes serialize prices as strings; this one ships as a float. The skill reads it directly.
- **`town` and `flat_type` only populated for HDB transactions.** Private property transactions have `district` but not `town`/`flat_type`. The skill's `--town + --flat-type` filter naturally excludes private transactions.
- **The full dataset is large.** `fetch_cea_transaction_records()` (no filters) pulls ~30k rows and is the most expensive call the skill makes. Cache aggressively.
- **No date filter at the source.** `since` is applied client-side after the full CSV is downloaded. The skill expects a `YYYY-MM` string.
- **Joining back to coll 54.** The `salesperson_reg_no` field is the join key. Coll 54 may have an `inactive` or `resigned` status; coll 55 still includes transactions from inactive salespersons (the historical record is preserved).

## Track-record enrichment

The `with_track_record(result, town, flat_type)` helper in the skill:

1. Pulls `fetch_cea_transaction_records(town=town, flat_type=flat_type)`.
2. Groups by `salesperson_reg_no`.
3. Counts deals per reg_no, finds `max(transaction_date)` for the "last_deal_date".
4. Attaches `track_record: {closed_in_town, closed_in_flat_type, last_deal_date}` to each match in `result["matches"]`.

When a match has no transactions, `track_record` is `null` (not an error). When `--town` is set but `--flat-type` is not, the filter passes `flat_type=None` (i.e. all flat types in that town).

## Example output

```python
[
    {
        "transaction_id": "T202512-0001",
        "transaction_date": "2025-12-15",
        "salesperson_reg_no": "R012345X",
        "salesperson_name": "Alice Tan",
        "agency": "ERA Realty Network Pte Ltd",
        "property_type": "HDB",
        "district": "D20",
        "town": "BISHAN",
        "flat_type": "5-ROOM",
        "sale_type": "resale",
        "trans_price": 720000.0
    }
]
```

## See also

- `references/cea-salesperson.md` — coll 54 register schema (the join key)
- Canonical `docs/api/CEA.md` — the broader CEA catalog
