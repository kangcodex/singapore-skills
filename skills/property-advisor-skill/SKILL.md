---
name: property-advisor-skill
description: "Evaluate any Singapore property asking price — HDB resale, private condo resale, rental, executive condo, or any of the four with an investment-lens overlay (supply pipeline + unsold + vacancy). Compares against the cluster baseline, computes trend (last 8 quarters, QoQ + YoY, 8-char unicode sparkline), overlays URA future amenities within 1 km, and (HDB mode only) contextualises with NEA rainfall history. Optional --verify-salesperson flag embeds a CEA lookup. Outputs a uniform JSON verdict and recommendation. Use when the user asks 'is this asking price fair?', 'evaluate this condo / HDB / EC / rental', or 'should I invest in this property?'."
---

# property-advisor-skill

A Singapore property value advisor covering five modes. Every mode returns a
uniform JSON shape with a `trend` block (last 8 quarters, QoQ + YoY deltas,
8-char unicode sparkline), a `location` block, and optional overlays (URA
future amenities, NEA rainfall, CEA salesperson verification, supply
pipeline + unsold units for investment).

## Quick start

```bash
# HDB resale (v1 default — preserved verbatim)
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --town BISHAN --flat-type 5-ROOM --since 2025-12-01 --asking 720000

# Private condo resale
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode private --town TIONG_BAHRU --region central \
    --since 2025-12-01 --asking 1500000

# Rental
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode rental --town TIONG_BAHRU --region whole_sg \
    --since 2025-12-01 --asking 4800

# Executive Condo
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode ec --town SENGKANG --since 2025-12-01 --asking 1180000

# Investment lens (overlay on top of any of the above)
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode investment --property-mode private --town TIONG_BAHRU \
    --region whole_sg --since 2025-12-01 --asking 1500000

# With CEA salesperson verification
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode hdb --town BISHAN --flat-type 5-ROOM \
    --since 2025-12-01 --asking 720000 \
    --verify-salesperson R012345X
```

Stdlib only — no `pip install`. Auth: reads `DATA_GOV_SG_API_KEY` from env
if set; works anonymously otherwise (lower rate limit).

## When to use which mode

A 5-question decision tree. Walk top-down; the first match wins.

```
Q1. Is the user buying a resale flat to live in themselves?
    |
    +-- yes --> HDB resale?  ----- yes -------> --mode hdb
    |          |
    |          +-- no (private condo / landed)
    |              |
    |              +-- Are you the buyer? -- yes --> --mode private
    |              |                          (and ask --region)
    |              |
    |              +-- no (renting, not buying)
    |                  |
    |                  +-- Q2. Are you an OWNER deciding
    |                     what to charge?
    |                          |
    |                          +-- yes --> --mode rental
    |                          |
    |                          +-- no  (tenant sanity-check)
    |                                     --> --mode rental
    |
    +-- Executive Condo (EC)?
    |       |
    |       +-- yes --> --mode ec
    |
    +-- Investment lens (any of the above + supply pipeline)?
            |
            +-- yes --> --mode investment --property-mode {hdb|private|rental|ec}
```

**Short form (load-bearing question first):**

> "What are you trying to do?"
>
> - **Live in it** --> `--mode hdb` or `--mode private`
> - **Rent it out** --> `--mode rental` (what should I charge?) or `--mode rental` (is this rent fair?)
> - **Buying an EC** --> `--mode ec`
> - **Buying as an investment** --> `--mode investment --property-mode {hdb|private|rental|ec}` (overlays SINGSTAT supply + URA unsold)

## The five modes

| Mode       | Primary dataset                                | Cluster metric       | Premium unit | Verdict basis        | NEA rainfall? | URA future amenities? | Investment overlay? | CEA verify?         |
| ---------- | ---------------------------------------------- | -------------------- | ------------ | -------------------- | ------------- | --------------------- | ------------------- | ------------------- |
| `hdb`        | HDB_RESALE_DATASET_ID                          | mean of `resale_price` | absolute $  | 5-cell matrix (v1)   | yes           | yes (1 km)            | no                  | optional            |
| `private`    | URA Private Resi Trans by region                | median `median_psf`   | $/psf        | 3-cell (fair/justified/above) | no    | yes (1 km)            | no                  | optional            |
| `rental`     | URA Rentals of Non-Landed (coll 1660)           | median `median_rent_psf_pm` | $/psf/pm | 3-cell          | no            | yes (1 km)            | no                  | optional            |
| `ec`         | URA EC Sales (1643) + EC Position (1661)        | median `median_psf`   | $/psf        | 3-cell               | no            | yes (1 km)            | no                  | optional            |
| `investment` | any of the above + SINGSTAT supply + URA unsold | base mode's metric    | base unit    | base mode's verdict   | if base=hdb   | yes (1 km)            | **yes — always**    | optional            |

`--mode hdb` is the default. Existing v1 commands work unchanged.

## CLI reference

| Flag                       | Required for                | Default       | Notes                                                                  |
| -------------------------- | --------------------------- | ------------- | ---------------------------------------------------------------------- |
| `--mode`                   | always                      | `hdb`         | one of `hdb` / `private` / `rental` / `ec` / `investment`              |
| `--property-mode`          | `--mode investment`         | —             | one of `hdb` / `private` / `rental` / `ec`                             |
| `--town`                   | always                      | —             | UPPERCASE; e.g. `BISHAN`, `TIONG_BAHRU`                                |
| `--flat-type`              | `--mode hdb` / `--mode investment --property-mode hdb` | — | one of `1-ROOM` / `2-ROOM` / `3-ROOM` / `4-ROOM` / `5-ROOM` / `EXEC` / `MULTI-GEN` / `STUDIO` |
| `--region`                 | `--mode private` / `--mode rental` | `whole_sg` | one of `whole_sg` / `central` / `rest_central` / `outside_central`      |
| `--since`                  | always                      | —             | `YYYY-MM` or `YYYY-MM-DD`                                             |
| `--asking`                 | always                      | —             | number (SGD for sale modes, SGD/pm for rental)                         |
| `--verify-salesperson`     | optional                    | off           | CEA reg_no (e.g. `R012345X`) or name fragment; case-insensitive         |
| `--json`                   | optional                    | `true`        | always emits JSON to stdout (kept for forwards-compat)                 |

## Output shape

Every mode returns a uniform JSON object. See
[`references/output-schema.md`](references/output-schema.md) for the full
schema and 5 + 1 worked examples. The minimum-required fields are:

- `mode`, `town`, `since`, `asking`, `verdict`, `premium_pct`
- `trend.last_8_quarters`, `trend.qoq_pct`, `trend.yoy_pct`, `trend.sparkline`
- `location.town`, `location.planning_area`, `location.region`, `location.nearest_mrt`
- `ura_context.future_amenities_within_1km`
- `cea_verification` (null when `--verify-salesperson` not set)

HDB mode additionally emits `cluster_avg`, `rainfall_history`, and a
human-readable `recommendation`. Investment mode additionally emits
`investment_overlay` (with `supply_signal: tight | balanced | surplus`).

## Verdict rules

| Mode       | Cluster premium %    | Has uplift? | Rainfall     | Verdict              |
| ---------- | -------------------- | ----------- | ------------ | -------------------- |
| `hdb`        | <= 5%                | any         | any          | `fair`               |
| `hdb`        | 5-10%                | >= 2        | not above-avg | `premium justified`  |
| `hdb`        | > 5%                 | < 2         | any          | `above market`       |
| `hdb`        | > 0%                 | any         | above-average | `above market`      |
| `hdb`        | > 10%                | >= 2        | not above-avg | `premium justified`  |
| `private` / `rental` / `ec` | <= 5% | any | n/a | `fair` |
| `private` / `rental` / `ec` | 5-10% | any | n/a | `premium justified` |
| `private` / `rental` / `ec` | > 10% | any | n/a | `premium justified` (uplift implicit in trend) |
| `private` / `rental` / `ec` | > 5%  | none | n/a | `above market` |

`has uplift` = >= 2 of {primary_school, healthcare, MRT, business_hub,
industrial} within 1 km of the cluster centroid (URA Master Plan scan).
For non-HDB modes, the verdict is driven by `premium_pct` against the
quarterly median; URA future amenities are reported but not gating.

## Investment lens (`--mode investment`)

Runs the base mode, then overlays:

- **Supply pipeline** — SINGSTAT `d_055b6549444dedb341c50805d9682a41`
  (long format: `[{series, qtr, value}, ...]`)
- **Unsold private residential units** — URA `d_84d05d45049108f0fd2e99b66bd19cfe`
- **Vacancy series** — SINGSTAT `d_01e3556fb916ca19a7e29fc39520fa78`
  (reported as `vacancy_series_count`)

The `supply_signal` is computed as:

```
ratio = (supply_pipeline_units + unsold_units) / trailing_4q_demand
ratio > 1.5  -> surplus
ratio < 0.5  -> tight
otherwise    -> balanced
```

A `surplus` signal flags the submarket as over-supplied; a `tight` signal
flags it as supply-constrained. `balanced` is the default.

## Caching

All upstream calls go through `singapore_api.request_json`, which writes
to `~/.hermes/cache/<namespace>/<sha1>.json`. Second invocation within
the cache window (until upstream `Last-Modified` changes) is free.

Namespaces used:

- `datastore|d_<resource_id>` for all v2 dataset fetches
- `singstat-ckan:d_<resource_id>` for the SINGSTAT legacy CKAN path

## Hardening

- **`resale_price` is a string** in the HDB dataset — coerce at the
  boundary with `to_float()`. Empty string is filtered.
- **URA fields vary by record** — `_x`/`_y` / `x`/`y` / `easting`/
  `northing`. The centroid helper tries all keys.
- **URA records are large** — the helper requests `limit=1000`. If the
  dataset grows past that, the script will silently drop overflow
  records. The cluster centroid is still accurate when the missing
  tail is random.
- **Empty URA result is not an error** — `future_amenities: []` is the
  documented response.
- **No HDB records in the window** — raises `ValueError`. The CLI
  catches it and prints `{"error": "..."}` with exit code 0.
- **SINGSTAT errors are non-fatal** — `fetch_singstat_supply_pipeline`
  and `fetch_singstat_vacancy` return `[]` on any network or parse
  failure. Investment overlay may be missing if SINGSTAT is
  unreachable, but the base mode's verdict still computes.
- **CEA verification miss is non-fatal** — `cea_verification: null`
  with a stderr warning.
- **No network at import** — `singapore_api` is lazy; no top-level calls.

## Out of scope (v2)

- Chart rendering / images
- Cross-town comparisons (only the requested town is summarised)
- Property tax / ABSD / TDSR calculators
- Mortgage rate lookups
- EC MOP (5-year minimum occupation period) enforcement
- CEA Salespersons' Property Transaction Records (coll 55) — reserved
  for the future `agent-match-skill`

## References

- Output schema (5 mode examples + 1 CEA): [`references/output-schema.md`](references/output-schema.md)
- URA data sources: [`references/ura.md`](references/ura.md) -> canonical
  [`docs/api/URA.md`](../../docs/api/URA.md)
- SINGSTAT data sources: [`references/singstat.md`](references/singstat.md)
  -> canonical [`docs/api/SINGSTAT.md`](../../docs/api/SINGSTAT.md)
- CEA data sources: [`references/cea.md`](references/cea.md) -> canonical
  [`docs/api/CEA.md`](../../docs/api/CEA.md)
- NEA weather context (HDB mode only): [`references/nea-weather.md`](references/nea-weather.md)
  -> canonical [`docs/api/NEA.md`](../../docs/api/NEA.md)

## Tests

```bash
python3 -m unittest discover -s skills/property-advisor-skill/tests
```

The suite covers (48 tests):

- v1 preserved: premium math, HDB filter, URA amenities (centroid +
  geocode fallback), rainfall classification, verdict matrix, full
  report, recommendation, module import
- v2 new: `sparkline`, `trend_block` (QoQ + YoY + sparkline), one
  end-to-end per mode (hdb / private / rental / ec), investment
  overlay (`supply_signal`), CEA verification

## Install

```bash
npx skills add kangcodex/singapore-skills --skill property-advisor-skill
```

The skill ships `scripts/singapore_api.py` as a per-skill copy (synced
from the canonical at the repo root via `scripts/sync_singapore_api.py`).
No runtime dependency on the parent repo.
