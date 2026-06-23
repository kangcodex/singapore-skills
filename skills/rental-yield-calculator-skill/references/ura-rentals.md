# URA Rentals of Non-Landed Residential Properties (coll 1660)

Quarterly median rent by district and property type. Used by `rental-yield-calculator-skill` for the rent series that drives the yield calculation.

## Dataset

- **ID:** `d_149ac00a2734bb0a03867bbe2ec0e7b0`
- **Collection:** 1660
- **Agency:** "Urban Redevelopment Authority"
- **Refresh:** quarterly
- **Record count:** ~570 rows (8 quarters × ~25 districts × 3 property types)

## Fetcher

```python
from singapore_api import fetch_ura_rentals

# All districts + property types
all_rentals = fetch_ura_rentals()
```

The fetcher uses the v2 dataset flow (initiate → poll → signed S3 CSV via `fetch_dataset_rows`).

## Schema

| Field                       | Type   | Description                                                                 |
| --------------------------- | ------ | --------------------------------------------------------------------------- |
| `qtr`                       | str    | Quarter label, e.g. `2025-Q4` (normalised by the fetcher)                    |
| `district`                  | str    | Singapore postal district, e.g. `D09` \| `D23` \| `D20`                     |
| `property_type`             | str    | `Non-Landed` \| `Landed`                                                     |
| `median_rent_psf_pm`        | float  | Median rent in SGD per square foot per month (the headline metric)         |
| `median_rent_pm`            | float  | Median rent in SGD per month (whole unit)                                  |
| `lease_count`               | int    | Number of leases that quarter (rough volume indicator)                      |

## Quirks

- **Rent is per square foot per month, not per unit.** A 1,000 sqft unit at $5 psf/pm rents for $5,000/month. The skill normalises to per-unit via the `median_rent_pm` field, which is more useful for the investor.
- **The skill uses `median_rent_pm` directly when present**, falling back to `median_rent_psf_pm × unit_size` only when needed. For District 9, the typical unit size is 700-1,000 sqft.
- **`qtr` is normalised to `YYYY-Q#`.** The raw field from URA is `20254Q` (no hyphen); the fetcher rewrites to `2025-Q4`. The trend block in the skill output uses the normalised form.
- **Records with missing or zero rent are skipped.** A row where `median_rent_pm` is null or 0 is excluded from the trend series.
- **Quarterly data, not monthly.** A new data point lands every 3 months. The trend block shows 8 quarters = 2 years.
- **District-level aggregation.** No block-level or street-level rent. The yield is a district-wide median, not a specific unit's rent.

## Example output

```python
[
    {
        "qtr": "2024-Q1",
        "district": "D09",
        "property_type": "Non-Landed",
        "median_rent_psf_pm": 5.20,
        "median_rent_pm": 5200.0,
        "lease_count": 312
    },
    {
        "qtr": "2024-Q2",
        "district": "D09",
        "property_type": "Non-Landed",
        "median_rent_psf_pm": 5.30,
        "median_rent_pm": 5300.0,
        "lease_count": 287
    }
]
```

## How the skill uses this dataset

The `calculate(asking, town, region, flat_type, since)` function:

1. Filters records to `district == town` AND `property_type == flat_type`.
2. Filters to `qtr >= since` (chronological lower bound).
3. Sorts by `qtr` ascending.
4. Takes the last 8 quarters for the trend block.
5. Uses the latest quarter's `median_rent_pm` for the monthly_rent_estimate.

The yield is then `(latest.median_rent_pm × 12) / asking × 100`.

## See also

- `references/ura-private-trans.md` — the buy-price baseline dataset (colls 1655-1658)
- Canonical `docs/api/URA.md` — the full URA catalog (273 collections)
