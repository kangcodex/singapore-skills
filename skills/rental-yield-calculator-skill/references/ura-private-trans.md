# URA Private Residential Property Transactions (colls 1655-1658)

Quarterly private condo transacted prices and volume, broken down by region. Used by `rental-yield-calculator-skill` for the buy-price baseline.

## Datasets

| Collection | Region           | Dataset ID                              |
| ---------- | ---------------- | --------------------------------------- |
| 1655       | central          | `d_c287c8be114bfa7d055b27ab2c87de83`    |
| 1656       | outside_central  | `d_1a7823f3d31e7db4b426833833762bab`    |
| 1657       | rest_central     | `d_5785799d63a9da091f4e0b456291eeb8`    |
| 1658       | whole_sg         | `d_7c69c943d5f0d89d6a9a773d2b51f337`    |

All four are quarterly, refreshed together.

## Fetcher

```python
from singapore_api import fetch_ura_private_resi_trans

# Whole SG (default)
all_sg = fetch_ura_private_resi_trans(region="whole_sg")

# One of the four regions
central = fetch_ura_private_resi_trans(region="central")
rest_central = fetch_ura_private_resi_trans(region="rest_central")
outside_central = fetch_ura_private_resi_trans(region="outside_central")
```

An unknown region raises `ValueError`. The 4 valid values are: `whole_sg`, `central`, `rest_central`, `outside_central`.

## Schema

| Field             | Type   | Description                                                                 |
| ----------------- | ------ | --------------------------------------------------------------------------- |
| `qtr`             | str    | Quarter label, e.g. `2025-Q4` (normalised)                                   |
| `district`        | str    | Postal district within the region, e.g. `D09`, `D23`                        |
| `property_type`   | str    | `Non-Landed` \| `Landed` (only Non-Landed is comparable across regions)     |
| `sale_count`      | int    | Number of transactions that quarter                                         |
| `median_psf`      | float  | Median transacted price in SGD per square foot (the headline metric)         |
| `median_trans_price` | float | Median transacted price in SGD (whole unit)                                |

## Region semantics

- **`whole_sg`**: aggregate of all 4 regions. Best for a market-wide view.
- **`central`**: postal districts D01-D08 (CBD, Marina Bay, Raffles Place, Sentosa).
- **`rest_central`**: D09-D11 (River Valley, Orchard, Newton).
- **`outside_central`**: D12-D28 (the rest of Singapore — heartland condos).

The skill accepts `--region` and uses it directly. Most users want `whole_sg` for a market overview, or one of the 3 sub-regions for a specific area.

## Quirks

- **`property_type` is `Non-Landed` for the comparable series.** Landed condo transactions are reported in a separate column / row; the skill filters to `Non-Landed` only.
- **`sale_count` is the volume indicator.** A quarter with 0 sales has `median_psf = null` and is skipped.
- **Region-level aggregation, not town-level.** A specific town (e.g. Bishan) sits inside `outside_central`, but the data is the whole region, not just Bishan. For a town-specific buy price, you need the URA Private Resi Trans by town dataset, which this skill does not use.
- **Q4 numbers may be revised.** URA releases preliminary Q4 numbers in January, then revises them in March. The fetcher pulls the latest revision.

## Example output

```python
[
    {
        "qtr": "2024-Q1",
        "district": "D09",
        "property_type": "Non-Landed",
        "sale_count": 187,
        "median_psf": 2150.0,
        "median_trans_price": 1935000.0
    },
    {
        "qtr": "2024-Q2",
        "district": "D09",
        "property_type": "Non-Landed",
        "sale_count": 165,
        "median_psf": 2200.0,
        "median_trans_price": 1980000.0
    }
]
```

## How the skill uses this dataset

The `calculate(asking, town, region, flat_type, since)` function:

1. Calls `fetch_ura_private_resi_trans(region)` for the user-chosen region.
2. Filters to `property_type == flat_type` and `qtr >= since`.
3. Takes the latest quarter's `median_psf` (not used for the yield directly, but provides context in the `ura_context` block).

The yield is computed from the rentals dataset (see `references/ura-rentals.md`), not from this dataset. The buy-price data here is for context: a "good yield" depends on whether your purchase is at, above, or below the regional median psf.

## See also

- `references/ura-rentals.md` — the rent series (coll 1660)
- Canonical `docs/api/URA.md` — the full URA catalog
