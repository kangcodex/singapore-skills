# Changelog

All notable changes to singapore-skills. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed — 2026-10-25

- **Local-only developer workspaces**: `development/` is ignored and untracked,
  with existing files retained locally. Published package checks are independent;
  the broader regression/evaluation corpus is opt-in local material and is not
  included in fresh clones.
- **Lean property-advisor distribution**: moved developer tests, eval definitions
  and synthetic assessment/case/scenario fixtures to `development/property-advisor/`.
  Installed skills retain runtime scripts, reference docs/data, the case template,
  environment template and MIT license. Updated resource paths and test commands.
- Added a tracked-runtime-only folder/`.skill` exporter and extracted-archive
  regression checks, so local casework, eval outputs and caches are not packaged.
  Removed the unused private demand helper and unused radius constant; supported
  CLI/Python interfaces remain covered by compatibility tests.

### Changed — 2026-10-24

- **Question-led property advisor implementation**: focused plans and executable
  assessments for normalized requirements, actual/future-route evidence, amenities,
  document versions, household function, supplied inventory, comparables, funding,
  loan/cost scenarios, exit and inactive watch specifications.
- Semantic age/date/unit/basis checks distinguish recent completed homes from
  permitted future launches and practical occupancy. Case references recompute
  assessments with fingerprints, retire unchanged stale advice and protect
  confirmed requirement changes with user provenance.
- Added chronological cash/CPF/loan eligibility/cap/reserve allocation, strategy
  comparison, recurring household shocks and linked net-exit inputs. Corrected
  zero/prorated CPF use across fees/instalments, nested policy uncertainty,
  ownership-versus-loan count, resale EC stages, supplied dates, higher-duty value
  basis and infeasible lowest-cost selection. Legacy scenarios remain illustrations.
- Added synthetic runnable examples and regression/CLI coverage. Working design
  files in `docs/property-advisor/` are ignored and untracked while retained locally;
  maintained runtime guides ship with the skill and verification fixtures stay local. Live
  provider/complex visual/institutional outcomes require actual native evidence.

### Changed — 2026-10-23

- **`property-advisor-skill` cross-category decision workflow** — household-led
  research and discovery across HDB new/resale, EC, private flats/condos and landed,
  with category-specific policy, liveability, matched evidence and conditional advice.
- Added schema-3.0 case templates, readable reports, provenance/constraint audits,
  Decimal cost/mortgage/price-unit helpers and completed-calendar-quarter trends.
- Retired unsupported legacy fair-value and supply heuristics: unavailable evidence
  remains null/insufficient, HDB filters are applied locally, and ambiguous CEA names
  no longer verify the first result. Context-mode errors exit 2; agent-mode API and
  scenario capabilities remain supported separately from researched decisions.
- Added fixed behavioral eval definitions, synthetic evidence and regression/CLI
  checks. Development research, personal casework and generated eval outputs are
  Git-ignored; runtime skill sources and self-contained public checks remain version-controlled.

### Added — 2026-10-19

- **`property-advisor-skill` agent mode** (`--mode agent`, ADR-008) — a property-agent style advisory layer on top of the five valuation modes, for new-launch condos, resale condos, resale HDB and ECs. No network, stdlib only, Decimal arithmetic.
  - `--task profile` — three buyer profiles as data (DINK couple, first-home couple, family of five + multi-generation variant): shortlist by category and OCR/RCR/CCR segment, location and risk checks, key questions, red flags, per-category due-diligence checklists, and the existing valuation modes to run.
  - `--task plan` — dated cash/CPF timeline (option, exercise, completion or progressive payments, BSD/ABSD, fees, fit-out, move-in), month-by-month commitments, TDSR/MSR stress test, minimum upfront cash and CPF, affordability ceiling (largest stress-tested loan/price), cumulative cost and equity at year 1/5/10/15 split cash vs CPF, low/base/high interest and appreciation assumptions.
  - `--task compare` — options side by side with 5/10/15-year cost of occupancy (explicit opportunity cost), equity built, HDB lifestyle add-ons (Virgin Active verified; ActiveSG and others flagged unverified; prices user-overridable) and the break-even monthly lifestyle spend.
  - `--task advise` and `--summary-only` — plain-language summary with the not-financial-or-legal-advice note.
  - New reference data: `policy-tables.json` (every policy figure with `as_of`, official `source_url`, `verified`/`unverified` status), `default-assumptions.json`, `buyer-profiles.json`, `due-diligence.json`, `lifestyle-addons.json`, `policy-sources.md`, `agent-scenario.md`, three worked scenario examples; `output-schema.md` section 7.
  - New scripts: `agent_advisor.py`, `agent_policy.py`, `agent_profiles.py`, `agent_cashflow.py`, `agent_compare.py`, `agent_report.py`, `agent_money.py`; `property_advisor.py` delegates `--mode agent` before argparse (valuation modes unchanged).
  - ~100 new unit tests (stamp-duty tiers, TDSR/MSR boundaries, progressive totals, CPF/cash split, break-even); no network.
  - `docs/decisions/ADR-008-property-advisor-agent-mode.md`

### Added — 2026-06-30

- **`sg-home-chef-skill`** — Singapore home chef recipe coach. Turns any dish request into a 3-tier recipe brief (beginner one-pan / intermediate tumis / advanced wok hei) calibrated to HDB-cookout-kitchen reality. Bilingual SG ingredient dictionary (Malay + Chinese + English), 2 sourcing tracks (supermarket vs wet market), dietary filters (halal / vegetarian / vegan / no-pork / no-beef / gluten-free), culinary milestone delivery (visual + aroma checkpoints, not timers). Bundles 6 starter recipes (Sambal Kang Kong, Hainanese Chicken Rice, Roti Prata, Laksa, Char Kway Teow, Bak Kut Teh).
  - `scripts/sg_home_chef.py` (743 lines, stdlib-only, deterministic) — CLI with --dish, --skill-level, --sourcing-track, --dietary, --servings, --time-budget, --json; returns `params_complete`, `skill_strategy`, `sourcing_strategy`, `ingredient_substitutions[]`, `milestones[]`, `recipe_blueprint`, `warnings[]`
  - `references/` (4 files): skill-levels.md, ingredient-dictionary.md (18 ingredients × 3 languages), sourcing-tracks.md, recipe-blueprint.md (8-section markdown skeleton + worked Sambal Kang Kong)
  - `evals/evals.json` (3 evals: 29 + 21 + 20 expectations = 70 total, 100% pass)
  - `tests/test_sg_home_chef.py` (42 unittest smoke tests, 100% pass)
  - `docs/design/sg-home-chef-skill.md` — design notes
  - `Makefile` — `test-sg-home-chef` and `evals-sg-home-chef` targets

### Added — 2026-06-22

#### 3 new skills
- **`agent-match-skill`** — CEA-registered salesperson lookup by name or registration number; optional postcode-sector filter; optional track-record (closed-deal count by town + flat type) from CEA monthly transaction records. Backed by CEA coll 54 + coll 55.
- **`rental-yield-calculator-skill`** — gross + net rental yield for a private condo purchase. Combines URA Private Resi Trans (buy baseline) with URA Rentals Non-Landed (rent series) and an 8-quarter trend. Net yield uses a 15% deduction for tax + mgmt + insurance.
- **`air-quality-advisor-skill`** — current PSI / PM2.5 / UV (NEA realtime) + 4-day forecast + 5-band health advisory. Pure-realtime, no download flow, no auth.

#### 1 major update
- **`property-advisor-skill` v2** — renamed from `resale-property-advisor-skill`. Was HDB-only; now five modes:
  - `hdb` (default, v1 behavior preserved)
  - `private` — URA Private Resi Trans by region (4 regions: whole_sg / central / rest_central / outside_central)
  - `rental` — URA Rentals of Non-Landed (coll 1660)
  - `ec` — URA Executive Condo sales + sale position
  - `investment` — overlay of SINGSTAT supply pipeline + URA unsold private resi with `supply_signal: tight|balanced|surplus`
- Uniform JSON output: `trend` block (last 8 periods + qoq + yoy + 8-bit unicode sparkline), `location` block, `ura_context` (1km future-amenity scan), `investment_overlay` (when applicable), `cea_verification` (optional `--verify-salesperson` flag).

#### Foundational update
- **Canonical `singapore_api.py`** — added 11 dataset ID constants, 9 fetchers, 3 helpers, plus type annotations on `svy21_to_wgs84` and `haversine_m`. The 9 new fetchers cover URA private resi trans (4 regions), URA rentals, URA EC sales/position, URA unsold private resi, SINGSTAT supply pipeline + vacancy (legacy CKAN with wide-to-long pivot), CEA salesperson + transaction records.
- **10 per-skill copies** synced automatically via `scripts/sync_singapore_api.py`.

#### Process additions
- **Makefile** — `make test` (full pytest), `make test-skills` (per-skill), `make test-top` (top-level), `make sync` (sync canonical to per-skill copies), `make clean` (nuke `__pycache__/` + `.pytest_cache/`), `make verify` (clean + sync + test), `make lint` (placeholder).
- **`docs/api/`** — agency catalog (CEA, SINGSTAT, URA Residential Property Datasets sections) created/extended.
- **`docs/archive/`** — 25 completed issues (S00-S12b) + 25 matching PRDs moved here from `.issues/`.

### Review cleanup
- **Consolidated 3 helpers** (`sparkline`, `trend_block`, `location_block`) from `property_advisor.py` + `rental_yield.py` into canonical `singapore_api.py`. Net savings: ~5,300 bytes across the two skills; helpers now reusable by future skills.
- **Removed 14 dead imports** across 7 skill scripts.
- **Fixed 3 test bugs** uncovered by the consolidation (sys.modules cache aliasing across per-skill copies; location_block leaking uppercased town on geocode failure; air-quality test polluting sys.modules cache).

### Test results
- **417 tests pass**, 6 skipped, 183 subtests passed.
- 1 pre-existing failure: `test_psi_national_handles_string_national` in `tests/test_singapore_api.py` (unrelated to S08-S12b; was failing before S08).

## [0.x] — 2026-06-20 and earlier

### Added
- `cdc-voucher-locator-skill` (S01a/b) — CDC Voucher merchant finder.
- `smart-commuter-skill` (S00 + S04) — LTA carpark + traffic + bus + MRT real-time.
- `resale-property-advisor-skill` (S02a/b) — HDB resale cluster baseline; **renamed to `property-advisor-skill` in v2**.
- `weekend-planner-skill` (S03a/b) — NEA + ActiveSG family activity advisor.
- `mrt-rerouter-skill` (S04) — Multi-modal routing.
- `dengue-risk-advisor-skill` (S05a/b) — NEA cluster + rainfall risk advisor.
- `hawker-discover-skill` (S06a/b) — Hawker + CDC voucher composer.

### Architecture
- `.issues/` — local markdown issue tracker with vertical-slice issues + matching PRDs (S07).
- `docs/api/` — agency catalog for CEA, HDB, NEA, OneMap, SINGSTAT, SPORTSG, URA, CDC.
- `scripts/sync_singapore_api.py` — syncs canonical to 10 per-skill copies with `SYNCED FROM` header.
