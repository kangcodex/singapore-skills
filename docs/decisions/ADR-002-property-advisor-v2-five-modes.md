# ADR-002: property-advisor v2 — five modes, one uniform output

## Status
Accepted

## Date
2026-06-22

## Context

The original `resale-property-advisor-skill` (S02) answered a single
question: "Is this HDB resale asking price fair?" It compared against the
HDB cluster baseline and added URA 1km future-amenity uplift + NEA
rainfall context. Users started asking follow-up questions the v1
couldn't answer:

- "What about private condos?"
- "What about rental yield?"
- "What about ECs?"
- "Is this a good buy-to-rent or are there too many units coming online?"

Each new question would have been a new skill. We had 7 skills already
and a clear pattern of "one skill, one output shape" — adding 4 more
skills for adjacent property questions would fragment the surface area
without adding value.

## Decision

Rename `resale-property-advisor-skill` → `property-advisor-skill` and
extend it with **five modes** sharing a single uniform JSON output shape:

| Mode        | Primary data                                        |
|-------------|-----------------------------------------------------|
| `hdb`       | HDB resale CSV (existing)                           |
| `private`   | URA Private Resi Trans by region (4 regions)        |
| `rental`    | URA Rentals Non-Landed (coll 1660)                  |
| `ec`        | URA EC sales (1643) + sale position (1661)          |
| `investment`| overlay on any of the above + SINGSTAT pipeline     |

The output always includes:
- `trend` block: `last_8_quarters` + `qoq_pct` + `yoy_pct` + 8-bit unicode sparkline `▁▂▃▄▅▆▇█` (ADR-005)
- `location` block: `town` + `planning_area` + `region` + `nearest_mrt`
- `ura_context`: 1km future-amenity scan (reused from v1)
- `investment_overlay`: `supply_pipeline_units` + `unsold_units` + `supply_signal: tight|balanced|surplus` (only in investment mode)
- `cea_verification`: optional `--verify-salesperson <name|reg_no>` flag attaches the CEA record

The hdb mode is the **default** for backwards compatibility — existing
CLI invocations still work without `--mode`.

## Alternatives Considered

### One skill per mode (5 new skills)
- Pros: Each skill is small and focused.
- Cons: 5 new skills each duplicating the trend/location/ura_context
  helpers; fragmented docs; no uniform output across skills.
- Rejected: violates "don't generalize until the third use case" but
  we have 4 adjacent use cases (private, rental, EC, investment)
  with identical structure.

### Single mode with extra CLI flags
- Pros: One skill to maintain.
- Cons: The HDB cluster baseline logic is fundamentally different from
  the URA per-region series; collapsing them into one mode would force
  ugly conditional code.
- Rejected: hurts readability.

### Keep HDB-only, add 4 new skills for the others
- Pros: Existing skill untouched.
- Cons: 4 new skills for what is logically one advisor. The user
  already knows the property-advisor brand.
- Rejected: the v1 base is small enough that a rename + extension is
  cheaper than 4 sibling skills.

## Consequences

- **Pos:** Uniform output shape makes downstream composition easy
  (e.g. an agent can show any mode's verdict in the same UI widget).
- **Pos:** `--mode hdb` default preserves all existing CLI invocations.
- **Pos:** 3 helpers (sparkline, trend_block, location_block) moved to
  canonical `singapore_api.py` (ADR-005), saving ~5,300 bytes across the
  two skills that use them.
- **Neg:** A single repo-rename (resale → property) touches many
  places: `sync_singapore_api.py` SKILL_FOLDERS, the per-skill copy
  test, the docs/api index, the README, the SKILL.md itself.
- **Neg:** `trend_block`'s `value_key` default had to align with
  rental_yield's existing call signature (`"median_rent_psf_pm"`),
  which means a future skill using a different field name must pass
  `value_key` explicitly. Documented in the function docstring.

## Follow-on

- 4 modes beyond hdb (private, rental, ec, investment) were scoped in
  the design phase but **only 4 of the 5 are wired to real fetchers in
  v2** (private / rental / ec / investment all work; hdb was the v1
  path). All 5 are tested and pass.
- Future skills (e.g. `distress-deal-detector-skill`) can compose
  with this one without re-implementing the trend / location /
  investment-overlay blocks.
