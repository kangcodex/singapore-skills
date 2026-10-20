---
name: property-advisor-skill
description: "Evaluate any Singapore property asking price — HDB resale, private condo resale, rental, executive condo, or any of the four with an investment-lens overlay (supply pipeline + unsold + vacancy). Compares against the cluster baseline, computes trend (last 8 quarters, QoQ + YoY, 8-char unicode sparkline), overlays URA future amenities within 1 km, and (HDB mode only) contextualises with NEA rainfall history. Optional --verify-salesperson flag embeds a CEA lookup. Outputs a uniform JSON verdict and recommendation. A sixth `--mode agent` mimics a property agent: buyer-profile shortlists (DINK couple, first-home couple, family of five), due-diligence checklists, a dated cash/CPF purchase timeline with TDSR/MSR checks, and condo-vs-HDB comparison with lifestyle add-ons and break-even. Use when the user asks 'is this asking price fair?', 'evaluate this condo / HDB / EC / rental', 'should I invest in this property?', or 'what should we buy and how much cash and CPF do we need?'."
---

# property-advisor-skill

A Singapore property value advisor covering five valuation modes plus an agent-style advisory layer (`--mode agent`). Every mode returns a
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

# Agent mode (no network): buyer profile -> shortlist, questions, red flags, due diligence
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode agent --task profile --profile family_of_five --variant multigen

# Agent mode: cash/CPF timeline, monthly commitments and TDSR/MSR check for one option
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode agent --task plan --scenario my-scenario.json

# Agent mode: condo vs HDB (+ gym membership add-ons) with break-even, in plain language
python3 skills/property-advisor-skill/scripts/property_advisor.py \
    --mode agent --task advise --summary-only \
    --scenario skills/property-advisor-skill/references/examples/dink-couple.json

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
    |       |
    |       +-- yes --> --mode investment --property-mode {hdb|private|rental|ec}
    |
    +-- "What should we buy / how much cash and CPF do we need?"
            |
            +-- which kind of property for this household? --> --mode agent --task profile
            +-- cash + CPF per stage, monthly, stress test   --> --mode agent --task plan
            +-- condo vs HDB (+ lifestyle add-ons)           --> --mode agent --task compare
            +-- all of the above in agent language           --> --mode agent --task advise
```

Typical agent flow: `profile` (what to look for) -> pick candidates -> price
check each with `--mode hdb|private|ec` (is the asking price fair?) -> `compare`
(can we afford it, and what does it cost to live there?) -> `advise` for the
write-up.

**Short form (load-bearing question first):**

> "What are you trying to do?"
>
> - **Live in it** --> `--mode hdb` or `--mode private`
> - **Rent it out** --> `--mode rental` (what should I charge?) or `--mode rental` (is this rent fair?)
> - **Buying an EC** --> `--mode ec`
> - **Buying as an investment** --> `--mode investment --property-mode {hdb|private|rental|ec}` (overlays SINGSTAT supply + URA unsold)

## The five valuation modes (plus `--mode agent`, below)

| Mode       | Primary dataset                                | Cluster metric       | Premium unit | Verdict basis        | NEA rainfall? | URA future amenities? | Investment overlay? | CEA verify?         |
| ---------- | ---------------------------------------------- | -------------------- | ------------ | -------------------- | ------------- | --------------------- | ------------------- | ------------------- |
| `hdb`        | HDB_RESALE_DATASET_ID                          | mean of `resale_price` | absolute $  | 5-cell matrix (v1)   | yes           | yes (1 km)            | no                  | optional            |
| `private`    | URA Private Resi Trans by region                | median `median_psf`   | $/psf        | 3-cell (fair/justified/above) | no    | yes (1 km)            | no                  | optional            |
| `rental`     | URA Rentals of Non-Landed (coll 1660)           | median `median_rent_psf_pm` | $/psf/pm | 3-cell          | no            | yes (1 km)            | no                  | optional            |
| `ec`         | URA EC Sales (1643) + EC Position (1661)        | median `median_psf`   | $/psf        | 3-cell               | no            | yes (1 km)            | no                  | optional            |
| `investment` | any of the above + SINGSTAT supply + URA unsold | base mode's metric    | base unit    | base mode's verdict   | if base=hdb   | yes (1 km)            | **yes — always**    | optional            |

`--mode hdb` is the default. Existing v1 commands work unchanged.

## Agent mode (`--mode agent`)

An additive advisor layer (ADR-008). It never calls the network; it reads dated
reference data and does Decimal arithmetic. Existing modes are unchanged.

| `--task`  | Needs                              | Returns (in `agent.*`)                                                     |
| --------- | ---------------------------------- | -------------------------------------------------------------------------- |
| `profile` | `--profile dink\|first_home_couple\|family_of_five` [`--variant multigen`] | shortlist by category/segment, location checks, key questions, red flags, due-diligence checklists, valuation modes to run |
| `plan`    | `--scenario FILE` (one `option`)    | dated cash/CPF timeline, monthly schedule, TDSR/MSR, upfront cash and CPF, affordability ceiling (largest stress-tested loan/price), year 1/5/10/15 cost split cash vs CPF, interest and appreciation scenarios |
| `compare` | `--scenario FILE` (`options` list)  | side-by-side up-front, monthly, 5/10/15-year cost of occupancy, equity built, lifestyle add-ons, break-even |
| `advise`  | `--scenario FILE` + `profile`       | profile + comparison (or plan) + one plain-language summary                |

`--summary-only` prints the property-agent-style summary instead of JSON. The JSON keeps the
uniform top-level keys (`mode`, `town`, `since`, `asking`, `verdict`, `premium_pct`, `trend`,
`location`, `ura_context`, `cea_verification`; `null` when not applicable) and adds `task`,
`agent`, `summary`, `disclaimer` and `policy_as_of`. Money values are decimal **strings**.
Scenario format: [`references/agent-scenario.md`](references/agent-scenario.md); runnable
examples for each profile: `references/examples/`.

**Policy is data.** BSD, ABSD, SSD, property tax, LTV, TDSR/MSR, the stress-test rate, EHG, the
OTP terms, the progressive payment schedule and CPF rules live in
[`references/policy-tables.json`](references/policy-tables.json), each with `as_of`,
`source_url` and `status` (`verified` = read from the official page; `unverified` = could not be
confirmed, with `unverified_reason`). A rule change is an edit to that file. Unverified items
the calculation touches are listed in the output (`unverified_assumptions`) and the summary.
See [`references/policy-sources.md`](references/policy-sources.md).

**Scenarios are assumptions.** Interest (2/3/4%), appreciation (0/2/4%), maintenance, renovation,
opportunity cost and similar defaults come from
[`references/default-assumptions.json`](references/default-assumptions.json) and are overridable
in the scenario's `assumptions` block. They are never presented as facts.

**Lifestyle add-ons** (HDB option): `lifestyle_addons: [{"id": "virgin_active_long_termer", "count": 2}]`
or a custom `{"label": "...", "monthly": "120"}`. Defaults come from
[`references/lifestyle-addons.json`](references/lifestyle-addons.json) with an `operating` status;
Virgin Active is verified from its official page, ActiveSG prices are unverified (official page
blocked), BBQ/function-room equivalents have no default price. `break_even` reports the monthly
lifestyle spend that closes the gap to the costlier option (total commitment, cash outflow, and
5/10/15-year cost).

This is guidance, not financial or legal advice; confirm figures with HDB, the bank and a lawyer.

## CLI reference

| Flag                       | Required for                | Default       | Notes                                                                  |
| -------------------------- | --------------------------- | ------------- | ---------------------------------------------------------------------- |
| `--mode`                   | always                      | `hdb`         | one of `hdb` / `private` / `rental` / `ec` / `investment` / `agent` (agent has its own flags: `--task`, `--profile`, `--variant`, `--scenario`, `--summary-only`) |
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
- Property tax / ABSD / TDSR calculators in the valuation modes (covered by `--mode agent`, which
  reads dated policy tables instead of hard-coding numbers)
- Mortgage rate lookups (agent mode uses explicit low/base/high rate assumptions)
- EC MOP (5-year minimum occupation period) enforcement
- Live listing scraping; cash-over-valuation, CPF pro-rating for short leases and the 120%
  withdrawal limit are not modelled (flagged in the output)
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
- Agent mode: [`references/agent-scenario.md`](references/agent-scenario.md),
  [`references/policy-sources.md`](references/policy-sources.md),
  [`references/policy-tables.json`](references/policy-tables.json),
  [`references/buyer-profiles.json`](references/buyer-profiles.json),
  [`references/due-diligence.json`](references/due-diligence.json),
  [`references/lifestyle-addons.json`](references/lifestyle-addons.json),
  [`references/default-assumptions.json`](references/default-assumptions.json); decision record
  [`docs/decisions/ADR-008-property-advisor-agent-mode.md`](../../docs/decisions/ADR-008-property-advisor-agent-mode.md)
- NEA weather context (HDB mode only): [`references/nea-weather.md`](references/nea-weather.md)
  -> canonical [`docs/api/NEA.md`](../../docs/api/NEA.md)

## Tests

```bash
python3 -m unittest discover -s skills/property-advisor-skill/tests
```

The suite covers the 48 valuation-mode tests plus ~100 agent-mode tests (policy tables and
stamp-duty tiers, TDSR/MSR boundaries, profiles, cash-flow engine, comparison, CLI); none use the network.
Valuation-mode coverage (48 tests):

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
