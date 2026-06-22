# Output Schema — `property-advisor-skill` v2

All five modes (`hdb` / `private` / `rental` / `ec` / `investment`) return a
uniform JSON object. Field names are stable and match `property_advisor.py`
verbatim — agents should not invent new fields without updating the script and
this schema in lock-step.

The mode, the property type, and the requested overlays control which fields
are populated. Every other field is always present and `null` if not
applicable.

## 1. HDB resale — `--mode hdb` (default)

The v1 default mode. Cluster baseline is the mean of HDB resale transactions
for `town` + `flat_type` since `since`. Premium uses v1's `verdict()` matrix
(5-cell: fair / premium justified / above market).

```json
{
  "mode": "hdb",
  "town": "BISHAN",
  "flat_type": "5-ROOM",
  "since": "2025-12-01",
  "asking": 720000,
  "verdict": "fair",
  "cluster_avg": 698543.21,
  "premium_pct": 3.1,
  "trend": {
    "last_8_quarters": [
      {"qtr": "2024-Q3", "value": 685200.0},
      {"qtr": "2024-Q4", "value": 689100.0},
      {"qtr": "2025-Q1", "value": 692400.0},
      {"qtr": "2025-Q2", "value": 694700.0},
      {"qtr": "2025-Q3", "value": 696300.0},
      {"qtr": "2025-Q4", "value": 698000.0},
      {"qtr": "2026-Q1", "value": 698500.0},
      {"qtr": "2026-Q2", "value": 700100.0}
    ],
    "qoq_pct": 0.2,
    "yoy_pct": 1.7,
    "sparkline": "▁▂▂▂▃▃▃▄"
  },
  "location": {
    "town": "BISHAN",
    "planning_area": "Bishan",
    "region": "central",
    "nearest_mrt": "Bishan MRT"
  },
  "ura_context": {
    "future_amenities_within_1km": ["MRT", "primary_school"]
  },
  "rainfall_history": {
    "classification": "typical",
    "recent_24mo_mm": 168.4,
    "five_year_avg_mm": 172.1
  },
  "cea_verification": null,
  "recommendation": "Asking $720,000 is within 3.1% of the $698,543 cluster average for this town/flat-type. Reasonable offer; proceed with valuation inspection."
}
```

## 2. Private condo resale — `--mode private --region whole_sg`

URA Private Residential Property Transactions by region. `cluster_median_psf`
is the median transaction price in $/psf for the requested `--since` quarter
onwards. `--region` ∈ {`whole_sg`, `central`, `rest_central`, `outside_central`}.

```json
{
  "mode": "private",
  "town": "TIONG BAHRU",
  "region": "central",
  "since": "2025-12-01",
  "asking": 1500000,
  "as_of_quarter": "2026-Q1",
  "verdict": "fair",
  "cluster_median_psf": 1423.5,
  "premium_pct": 2.6,
  "trend": {
    "last_8_quarters": [
      {"qtr": "2024-Q2", "value": 1350.0},
      {"qtr": "2024-Q3", "value": 1370.0},
      {"qtr": "2024-Q4", "value": 1382.0},
      {"qtr": "2025-Q1", "value": 1395.0},
      {"qtr": "2025-Q2", "value": 1402.0},
      {"qtr": "2025-Q3", "value": 1410.0},
      {"qtr": "2025-Q4", "value": 1418.0},
      {"qtr": "2026-Q1", "value": 1423.5}
    ],
    "qoq_pct": 0.4,
    "yoy_pct": 2.9,
    "sparkline": "▁▂▂▃▃▃▃▄"
  },
  "location": {
    "town": "TIONG BAHRU",
    "planning_area": "Bukit Merah",
    "region": "central",
    "nearest_mrt": "Tiong Bahru MRT"
  },
  "ura_context": {
    "future_amenities_within_1km": ["healthcare"]
  },
  "cea_verification": null
}
```

## 3. Rental — `--mode rental --region whole_sg`

URA Rentals of Non-Landed Residential Buildings. `cluster_median_psf` is the
median monthly rent in $/psf/pm.

```json
{
  "mode": "rental",
  "town": "TIONG BAHRU",
  "region": "whole_sg",
  "since": "2025-12-01",
  "asking": 4800,
  "as_of_quarter": "2026-Q1",
  "verdict": "fair",
  "cluster_median_psf": 4.2,
  "premium_pct": 1.4,
  "trend": {
    "last_8_quarters": [
      {"qtr": "2024-Q2", "value": 3.9},
      {"qtr": "2024-Q3", "value": 4.0},
      {"qtr": "2024-Q4", "value": 4.05},
      {"qtr": "2025-Q1", "value": 4.1},
      {"qtr": "2025-Q2", "value": 4.12},
      {"qtr": "2025-Q3", "value": 4.15},
      {"qtr": "2025-Q4", "value": 4.18},
      {"qtr": "2026-Q1", "value": 4.2}
    ],
    "qoq_pct": 0.5,
    "yoy_pct": 2.4,
    "sparkline": "▁▂▂▃▃▃▃▄"
  },
  "location": {
    "town": "TIONG BAHRU",
    "planning_area": "Bukit Merah",
    "region": "central",
    "nearest_mrt": "Tiong Bahru MRT"
  },
  "ura_context": {
    "future_amenities_within_1km": ["healthcare"]
  },
  "cea_verification": null
}
```

## 4. Executive Condo — `--mode ec`

URA EC Units Launched and Sold (coll 1643) + Sale Position of ECs (coll 1661).
`verdict` is `fair` / `premium justified` / `above market` driven by
`premium_pct` against the latest quarter's median.

```json
{
  "mode": "ec",
  "town": "SENGKANG",
  "since": "2025-12-01",
  "asking": 1180000,
  "as_of_quarter": "2026-Q1",
  "verdict": "fair",
  "cluster_median_psf": 1050.0,
  "premium_pct": 1.2,
  "trend": {
    "last_8_quarters": [
      {"qtr": "2024-Q2", "value": 980.0},
      {"qtr": "2024-Q3", "value": 995.0},
      {"qtr": "2024-Q4", "value": 1010.0},
      {"qtr": "2025-Q1", "value": 1020.0},
      {"qtr": "2025-Q2", "value": 1030.0},
      {"qtr": "2025-Q3", "value": 1038.0},
      {"qtr": "2025-Q4", "value": 1045.0},
      {"qtr": "2026-Q1", "value": 1050.0}
    ],
    "qoq_pct": 0.5,
    "yoy_pct": 2.9,
    "sparkline": "▁▂▂▃▃▃▃▄"
  },
  "location": {
    "town": "SENGKANG",
    "planning_area": "Sengkang",
    "region": "outside_central",
    "nearest_mrt": "Sengkang MRT"
  },
  "ura_context": {
    "future_amenities_within_1km": ["primary_school", "MRT"]
  },
  "cea_verification": null
}
```

## 5. Investment lens — `--mode investment --property-mode {hdb|private|rental|ec}`

Runs the base mode, then overlays supply pipeline + unsold private resi +
vacancy data. Adds `investment_overlay` (always present) and copies the
underlying `property_mode`. `supply_signal`:

- `surplus` — `(supply_pipeline + unsold) > 1.5 × trailing 4Q demand`
- `tight` — `(supply_pipeline + unsold) < 0.5 × trailing 4Q demand`
- `balanced` — otherwise

```json
{
  "mode": "investment",
  "property_mode": "private",
  "town": "TIONG BAHRU",
  "region": "whole_sg",
  "since": "2025-12-01",
  "asking": 1500000,
  "as_of_quarter": "2026-Q1",
  "verdict": "fair",
  "cluster_median_psf": 1423.5,
  "premium_pct": 2.6,
  "trend": {
    "last_8_quarters": [ ... 8 rows ... ],
    "qoq_pct": 0.4,
    "yoy_pct": 2.9,
    "sparkline": "▁▂▂▃▃▃▃▄"
  },
  "location": {
    "town": "TIONG BAHRU",
    "planning_area": "Bukit Merah",
    "region": "central",
    "nearest_mrt": "Tiong Bahru MRT"
  },
  "ura_context": {
    "future_amenities_within_1km": ["healthcare"]
  },
  "investment_overlay": {
    "supply_pipeline_units": 12800,
    "unsold_units": 4200,
    "trailing_4q_demand": 7200,
    "supply_ratio": 2.36,
    "supply_signal": "surplus",
    "vacancy_series_count": 6
  },
  "cea_verification": null
}
```

## 6. CEA verification — `--verify-salesperson <name|reg_no>`

When `--verify-salesperson` is set, all 5 modes (hdb / private / rental / ec /
investment) populate `cea_verification` with the matching CEA salesperson
record. If no record matches, the field stays `null` and a warning is logged
to stderr. The base mode's other fields are unchanged.

```json
{
  "mode": "hdb",
  "town": "BISHAN",
  "flat_type": "5-ROOM",
  "since": "2025-12-01",
  "asking": 720000,
  "verdict": "fair",
  "cluster_avg": 698543.21,
  "premium_pct": 3.1,
  "trend": { ... 8 rows + qoq + yoy + sparkline ... },
  "location": { ... },
  "ura_context": { "future_amenities_within_1km": ["MRT", "primary_school"] },
  "rainfall_history": { ... },
  "cea_verification": {
    "registration_no": "R012345X",
    "name": "Alice Tan",
    "status": "active",
    "agency": "ERA Realty Network"
  },
  "recommendation": "..."
}
```

The `query` is matched case-insensitively. If it starts with `R` and is at
least 3 characters long, it is treated as a registration number (exact
match). Otherwise it is matched as a case-insensitive substring of `name`.

## Field reference (all modes)

| Field                              | Type        | Always present? | Notes                                                              |
| ---------------------------------- | ----------- | --------------- | ------------------------------------------------------------------ |
| `mode`                             | str         | yes             | `hdb` / `private` / `rental` / `ec` / `investment`                  |
| `town`                             | str         | yes             | UPPERCASED                                                         |
| `flat_type`                        | str         | hdb / ec only   | UPPERCASED, e.g. `5-ROOM`                                          |
| `region`                           | str         | private/rental/investment | one of `whole_sg` / `central` / `rest_central` / `outside_central` |
| `since`                            | str         | yes             | echoed from CLI                                                    |
| `asking`                           | number      | yes             | echoed from CLI                                                    |
| `as_of_quarter`                    | str         | non-hdb         | latest quarter in the trend block                                  |
| `verdict`                          | str         | yes             | `fair` / `premium justified` / `above market`                       |
| `cluster_avg`                      | number      | hdb only        | mean of HDB `resale_price` in window                               |
| `cluster_median_psf`               | number      | private/ec      | median $/psf for the latest quarter                                |
| `cluster_median_total`             | number      | not emitted     | reserved for future use                                            |
| `premium_pct`                      | number      | yes             | (asking − cluster) / cluster × 100, 1 dp                           |
| `trend.last_8_quarters`            | array       | yes             | list of `{qtr, value}` (or HDB quarter aggregate)                  |
| `trend.qoq_pct`                    | number      | yes             | (last − prev) / prev × 100, 1 dp                                   |
| `trend.yoy_pct`                    | number      | yes             | (last − 4Q-prior) / 4Q-prior × 100, 1 dp                           |
| `trend.sparkline`                  | str         | yes             | 8 unicode block chars `▁▂▃▄▅▆▇█`                                   |
| `location.town`                    | str         | yes             | echoed                                                             |
| `location.planning_area`           | str         | yes             | from OneMap; `unknown` on geocode failure                           |
| `location.region`                  | str         | yes             | from OneMap; `unknown` on geocode failure                          |
| `location.nearest_mrt`             | str         | yes             | from OneMap; `unknown` on geocode failure                          |
| `ura_context.future_amenities_within_1km` | array | yes             | sorted set of `{primary_school, healthcare, MRT, business_hub, industrial}` |
| `rainfall_history.classification`  | str         | hdb only        | `above-average` / `typical` / `below-average` / `unknown`          |
| `rainfall_history.recent_24mo_mm`  | number      | hdb only        | mean rainfall, last 24 months                                      |
| `rainfall_history.five_year_avg_mm`| number      | hdb only        | mean rainfall, last 5 years                                        |
| `investment_overlay`               | object      | investment only | see section 5 above                                                |
| `cea_verification`                 | object/null | yes             | null when `--verify-salesperson` not set                           |
| `recommendation`                   | str         | hdb only        | human-readable verdict explanation                                 |

## Out of scope (v2)

The following are **not** emitted by the v2 script — agents should not
expect them and should not invent them:

- Chart images / rendered visualisations
- Cross-town comparisons (only the requested town is summarised)
- Property tax / ABSD / TDSR calculators
- Mortgage rate lookups (separate skill, not in this dataset)
- EC MOP (5-year minimum occupation period) enforcement checks
- CEA Salespersons' Property Transaction Records (coll 55) — used by
  `agent-match-skill`, not this one
