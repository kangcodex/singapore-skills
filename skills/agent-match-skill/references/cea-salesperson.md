# CEA Salesperson Information (coll 54)

Council for Estate Agencies (CEA) public register of registered property salespersons in Singapore. Refreshed 3x daily.

## Dataset

- **ID:** `d_07c63be0f37e6e59c07a4ddc2fd87fcb`
- **Collection:** 54
- **Agency:** "Council For Estate Agencies" (exact case, capital F)
- **Refresh:** 3x daily
- **Record count:** ~50,000 (only active + recently-resigned salespersons)

## Fetcher

```python
from singapore_api import fetch_cea_salesperson

# All records
all_salespersons = fetch_cea_salesperson(query="")

# By registration number (exact match)
result = fetch_cea_salesperson(query="R012345X")

# By name (case-insensitive substring)
result = fetch_cea_salesperson(query="alice")
```

Empty/None/whitespace queries return `[]` without a network call. Otherwise the query is sent through the v2 dataset flow (initiate → poll → signed S3 CSV via `fetch_dataset_rows`).

## Schema

Each record is a flat dict with these fields:

| Field               | Type    | Description                                                                 |
| ------------------- | ------- | --------------------------------------------------------------------------- |
| `registration_no`   | str     | CEA registration number, e.g. `R012345X`                                    |
| `name`              | str     | Salesperson's full name as registered with CEA                              |
| `status`            | str     | `active` \| `inactive` \| `suspended` \| `resigned`                          |
| `agency`            | str     | Name of the registered estate agency, e.g. `ERA Realty Network Pte Ltd`    |
| `registered_postcode` | str   | 6-digit Singapore postcode of the salesperson's registered business address  |
| `last_refreshed`    | str     | ISO date the row was last updated by CEA                                     |

## Quirks

- **Name match is case-insensitive substring.** The fetcher lowercases both query and name; "alice" matches "Alice Tan", "Bob Alice Lee", and "Aliceson Wong".
- **Registration number must start with `R` and be ≥3 chars.** The fetcher validates: queries starting with `R` trigger an exact-match filter; otherwise substring on name.
- **Empty query returns `[]` without a network call.** Use this to fetch the full register (~50k rows, ~2 MB).
- **The full register is large.** Calling `fetch_cea_salesperson("")` will pull the entire 50k-row CSV. The skill caches it in `~/.hermes/cache/datastore|<resource_id>/` for the cache window.
- **Agency names include the legal entity suffix** (`Pte Ltd`, `LLP`, `LLC`). When matching on agency, normalize first.

## Example output

```python
[
    {
        "registration_no": "R012345X",
        "name": "Alice Tan",
        "status": "active",
        "agency": "ERA Realty Network Pte Ltd",
        "registered_postcode": "238859",
        "last_refreshed": "2026-06-22"
    },
    {
        "registration_no": "R054321Y",
        "name": "Alice Lee",
        "status": "inactive",
        "agency": "PropNex Realty Pte Ltd",
        "registered_postcode": "179101",
        "last_refreshed": "2026-06-22"
    }
]
```

## See also

- Canonical `docs/api/CEA.md` — the broader CEA catalog (coll 55 is the transaction-records dataset)
- `references/cea-transactions.md` — the coll 55 dataset used for track-record enrichment
