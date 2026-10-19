# ADR-008: Property-advisor agent mode (`--mode agent`)

## Status
Accepted

## Date
2026-10-19

## Context

`property-advisor-skill` (ADR-002) answers one question well: *is this asking price fair?* A buyer
works one step earlier and one step later: *what kind of property should we look for*, and *can we
afford it, how much cash and CPF do we need at each stage, and how does it compare with the
alternative?* A property agent covers this with buyer-profile knowledge, due-diligence checklists and
a cash-flow walk-through. The request: mimic that, for new-launch condominiums, resale condominiums
and resale HDB flats (plus ECs where relevant), for a dual-income couple with no children, a couple
buying their first home, and a family of five, including a condo-vs-HDB comparison where the HDB
option can add priced lifestyle subscriptions.

Constraints from the repo: stdlib-only Python, the uniform JSON output shape, the single canonical
`singapore_api.py` (ADR-001), existing modes and tests unchanged, tests without network. Singapore
property rules (stamp duties, LTV, TDSR/MSR, grants, CPF) change often, so no number may be
hard-coded silently.

## Decision

Add an advisor layer as a sixth mode, `property_advisor.py --mode agent`, implemented in new
modules beside the existing script. `property_advisor.main()` hands `--mode agent` to
`agent_advisor.main()` before argparse runs, so the five valuation modes and their required flags
are untouched.

- **Tasks, not flags per field.** `--task profile|plan|compare|advise`; financial inputs come from a
  scenario JSON file (`--scenario`), because a purchase has dozens of inputs (buyers, CPF, debts,
  loan, add-ons) that are awkward as flags and easy to version and share as a file.
- **Policy is data.** `references/policy-tables.json` holds every rule figure with `as_of`,
  `source_url` and `status` (`verified` | `unverified` + reason). `agent_policy.py` reads it; a rule
  change is a data edit. A test fails if an item is undated, unsourced or unverified without a reason.
  Figures that could not be read from the official page on 2026-10-19 (HDB loan rate and LTV, family
  and proximity grants, progressive schedule, fees, CPF pro-rating) ship as `unverified` placeholders.
- **Assumptions are separate from policy.** `default-assumptions.json` (interest 2/3/4%,
  appreciation 0/2/4%, maintenance, fit-out, opportunity cost) is labelled `status: assumption`,
  overridable per scenario, and echoed in the output as assumptions.
- **Profiles are data.** `buyer-profiles.json` and `due-diligence.json` encode priorities,
  shortlists, location checks, questions, red flags and checklists; `agent_profiles.py` only
  assembles them. Shortlists point at the existing valuation modes (`valuation_args`) instead of
  duplicating them; sibling skills (dengue, air quality, commute) are named, not called.
- **Decimal everywhere.** `agent_money.py` rejects floats; results render money as decimal strings.
- **Cash-flow engine** (`agent_cashflow.py`): a month-indexed simulation with explicit cash vs CPF
  allocation, a dated stage timeline (resale lump sum versus progressive payments), the stress-tested
  TDSR/MSR check, and cumulative cost and equity at years 1/5/10/15. Simplifications are listed in
  every result (`notes.simplifications`).
- **Comparison** (`agent_compare.py`): total cost of occupancy with the opportunity cost of the down
  payment as a named, overridable line; lifestyle add-ons priced from `lifestyle-addons.json`
  (operator, `as_of`, source, `operating` status) or user-supplied; break-even lifestyle spend per
  month on total commitment, cash outflow and 5/10/15-year cost.
- **Agent-style output** (`agent_report.py`): the JSON keeps the uniform top-level keys and adds
  `agent`, `summary` and `disclaimer`; `--summary-only` prints the text.

## Alternatives Considered

### Extend the five modes with flags (`--mode private --profile ...`)
- Pros: one entry point per property type.
- Cons: the new work is not a valuation; it needs a different input shape and different outputs.
  Overloading the existing argparse would risk the unchanged-behaviour requirement.

### A separate new skill
- Pros: clean boundary.
- Cons: the profile shortlist exists to feed the valuation modes and share their vocabulary
  (`hdb`/`private`/`ec`, regions, flat types). A second skill would duplicate the discoverability
  and need its own `singapore_api.py` copy (ADR-001) with no network use.

### Hard-code the rules in Python constants
- Pros: simpler code.
- Cons: stale numbers with no date or source; a rule change becomes a code change. Rejected by
  the data requirement.

### Fetch rules live
- Cons: the official pages are not machine-readable APIs (several returned navigation-only HTML,
  403s or PDFs), and live fetches would break the no-network tests and the no-new-API-key rule.

## Consequences

- Positive: one data edit updates the calculators; unverified inputs are visible in every output;
  existing modes and their 48 tests are unchanged.
- Negative: the reference data needs periodic human re-verification; `unverified` items must be
  confirmed with the named authority before a decision relies on them.
- Not modelled (flagged in output): cash-over-valuation, CPF pro-rating for short leases, the 120%
  withdrawal limit, variable-income haircut, rental of the existing home, taxes on investment.
- Follow-up: a scheduled re-verification of `policy-tables.json`; pulling real nearby-transaction
  psf into the plan automatically if a fixture-backed valuation step is wanted.
