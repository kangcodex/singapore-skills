---
name: rental-yield-calculator-skill
description: "Estimate the rental yield of a Singapore private condo purchase. Combines URA Private Residential Property Transactions (buy-price baseline) with URA Rentals of Non-Landed Residential Properties (rent series) to compute gross yield, net yield after 15% deduction, and a 8-quarter trend of median rent. Use when the user asks 'what's the rental yield for this condo?', 'is this condo a good rental investment?', or 'how have rents trended in DISTRICT 9?'."
---

# rental-yield-calculator-skill

A Singapore rental-yield estimator for private condo buyers. Given an asking price, town/district, region, flat type, and lookback window, returns gross yield, net yield (after a 15% deduction for tax + management + insurance), and a 8-quarter trend of median rent for the area.

## Quick Start

```bash
python3 skills/rental-yield-calculator-skill/scripts/rental_yield.py \
    --asking 1500000 \
    --town "DISTRICT 9" \
    --region whole_sg \
    --flat-type "Non-Landed" \
    --since 2025-01
```

Stdlib only — no `pip install`. Auth: reads `DATA_GOV_SG_API_KEY` from env if set; works anonymously otherwise (lower rate limit).

## Triggers

Run this skill when the user says any of:

- "What's the rental yield for this condo?"
- "Is this a good buy-to-rent?"
- "How are rents trending in DISTRICT 9?"
- "What gross yield can I expect on a $1.5M condo?"

Do not run for: HDB flats (no private rental data is comparable), landed property (different rent band), commercial property, or for non-Singapore markets.

## How the yield is computed

```
gross_yield_pct = (annual_rent_estimate / asking) × 100
net_yield_pct   = gross_yield_pct × (1 - 0.15)
```

- `annual_rent_estimate` = `monthly_rent_estimate × 12` (monthly_rent_estimate is the latest quarter's median from URA Rentals Non-Landed for the town/flat-type).
- The 15% net deduction accounts for: Singapore income tax on rental income (≤24% marginal), property tax (~10% of annual value), fire insurance, and condo management fees for common areas. It's a heuristic, not a precise calculator.

## The 15% net deduction

This is a built-in assumption, not a user-configurable parameter. The skill reports:

- **`gross_yield_pct`**: the headline figure. What a casual investor would quote.
- **`net_yield_pct`**: the realistic take-home after tax + mgmt + insurance. This is what the investor actually keeps.

The 15% is appropriate for a typical Singapore private condo rental:
- Income tax: ~10% (depends on the landlord's marginal rate)
- Property tax: ~10% of annual value
- Fire insurance + condo mgmt fees: ~5%

For a 2-property landlord, income tax can climb to 24% marginal. The skill does not adjust for this.

## CLI

| Flag          | Required | Default       | Description                                                                |
| ------------- | -------- | ------------- | -------------------------------------------------------------------------- |
| `--asking`    | yes      | —             | Asking price in SGD (the purchase price you're considering)               |
| `--town`      | yes      | —             | Town or district name (e.g. "BISHAN", "DISTRICT 9", "TIONG BAHRU")        |
| `--region`    | no       | `whole_sg`    | `whole_sg` \| `central` \| `rest_central` \| `outside_central`             |
| `--flat-type` | yes      | —             | `Non-Landed` \| `Landed` (URA's flat-type enum)                            |
| `--since`     | yes      | —             | YYYY-MM lower bound for the lookback window (typically 24-36 months ago)   |

## Workflow

1. **Parse CLI args.** Validate that `--flat-type` is one of the URA enum values.
2. **Fetch URA Rentals Non-Landed** for the town + flat-type. `fetch_ura_rentals()` returns the full quarterly history.
3. **Fetch URA Private Resi Trans** for the region. `fetch_ura_private_resi_trans(region)` returns the buy-price baseline (median psf + sale count).
4. **Compute monthly_rent_estimate.** Latest quarter's median rent from the rentals dataset.
5. **Compute annual_rent_estimate.** monthly × 12.
6. **Compute gross/net yield.** annual / asking × 100; net = gross × 0.85.
7. **Build trend block.** Last 8 quarters of median rent, with QoQ + YoY deltas + unicode sparkline.
8. **Geocode town → location block.** `geocode(town)` returns (address, lat, lon, postal). Used for the URA 1km amenity scan.
9. **URA 1km context.** `fetch_ura_master_plan()` for future amenities within 1km of the geocoded point.
10. **Output JSON.** All fields per the schema below.

## Output shape (canonical)

```json
{
  "asking": 1500000,
  "town": "DISTRICT 9",
  "region": "whole_sg",
  "flat_type": "Non-Landed",
  "since": "2025-01",
  "monthly_rent_estimate": 5200.0,
  "annual_rent_estimate": 62400.0,
  "gross_yield_pct": 4.16,
  "net_yield_pct": 3.54,
  "trend": {
    "last_8_quarters": [
      {"qtr": "2024-Q1", "value": 4800.0},
      {"qtr": "2024-Q2", "value": 4900.0},
      ...
    ],
    "qoq_pct": 1.2,
    "yoy_pct": 4.4,
    "sparkline": "▁▂▂▃▄▅▅▆▆"
  },
  "location": {
    "source": "address",
    "address": "Orchard",
    "lat": 1.3036,
    "lon": 103.8318
  },
  "ura_context": {
    "future_amenities_within_1km": ["MRT", "primary_school", "healthcare"]
  }
}
```

If the geocoder fails, `location` is `{"source": "failed", "address": null, "lat": null, "lon": null}` and `ura_context.future_amenities_within_1km` is `[]`.

## Data sources

- **URA Rentals of Non-Landed Residential Properties** (coll 1660, `d_149ac00a2734bb0a03867bbe2ec0e7b0`) — quarterly median rent by district + property type. See `references/ura-rentals.md`.
- **URA Private Residential Property Transactions** (colls 1655-1658) — quarterly median psf + sale count by region. See `references/ura-private-trans.md`.
- **URA Master Plan Land Use** (coll 1653) — for the 1km future-amenity scan.
- **OneMap geocoder** for town → lat/lon.

Cross-references: canonical `docs/api/URA.md` for the full URA catalog.

## Caching

All upstream calls go through `singapore_api.request_json`, which writes to `~/.hermes/cache/<namespace>/<sha1>.json`. Second invocation within the cache window is free.

Namespaces used:
- `datastore|d_<ura_rentals_id>` for rental series
- `datastore|d_<ura_private_trans_id>` for buy-price baseline
- `datastore|d_<ura_master_plan_id>` for the 1km amenity scan
- `onemap:search` for the geocode

## Hardening

- **Empty or invalid `--flat-type` is rejected.** Must be one of URA's enum values.
- **No top-level network.** `singapore_api` is lazy; no calls at import time.
- **Missing rent data is handled.** If `fetch_ura_rentals` returns `[]`, the script returns `{"error": "no rental data for <town> <flat_type>"}` with exit 0.
- **Geocoder failure is graceful.** `location` becomes `{"source": "failed", ...}` and `ura_context` becomes `{"future_amenities_within_1km": []}`. The yield is still computed.
- **URA scan radius is 1 km.** That's a 5-10 minute walk. The 1km is hard-coded; future enhancement would expose this as a flag.

## Pitfalls

- **The 15% net deduction is a heuristic.** A landlord with multiple properties will pay higher marginal tax; a landlord with a single property and no mortgage may pay less. Adjust manually.
- **The yield is based on the current asking price, not the actual transacted price.** If you negotiate 5% off the asking, the yield goes up by ~5%.
- **URA rent data is district-level, not building-level.** District 9 has a wide range of rents; the median may not match your specific unit. Treat the yield as a ballpark, not a forecast.
- **Vacancy is not modelled.** The skill assumes 100% occupancy. A 2-month vacancy per year reduces annual rent by ~17%.
- **URA Private Resi Trans by region is region-aggregate, not town-aggregate.** `--region whole_sg` gives SG-wide median; `--region outside_central` gives the non-central region. For a town-specific buy price, you need the URA Private Resi Trans by town dataset, which this skill does not use.
- **No inflation modelling.** The trend shows nominal rent; the real yield is lower if inflation is positive.

## Tests

Smoke tests use stdlib `unittest` + `unittest.mock` to stub `fetch_ura_rentals`, `fetch_ura_private_resi_trans`, `fetch_ura_master_plan`, and `geocode`:

```bash
python3 -m unittest discover -s skills/rental-yield-calculator-skill/tests
```

The suite covers:
- Gross/net yield for a private condo (District 9)
- HDB town (Bishan) where the rent data shape is different
- Missing rent data (empty result)
- No URA amenities within 1km
- Geocoder failure (graceful fallback)
- Trend block (last 8 quarters, sparkline, QoQ/YoY)
- Module import + public surface
- No top-level network calls

## References

- `references/ura-rentals.md` — coll 1660 (rent series) schema and quirks
- `references/ura-private-trans.md` — colls 1655-1658 (buy-price baseline) schema
- `../docs/api/URA.md` — canonical URA catalog (273 collections)

## Install

```bash
npx skills add kangcodex/singapore-skills --skill rental-yield-calculator-skill
```

The skill ships `scripts/singapore_api.py` as a per-skill copy (synced from the canonical at the repo root via `scripts/sync_singapore_api.py`). No runtime dependency on the parent repo.
