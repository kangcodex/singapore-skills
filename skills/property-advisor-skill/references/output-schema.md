# Output and migration

The household decision record is schema **3.0**, described in
[decision-record.md](decision-record.md), with a starter at
`assets/case-template.json`. Use the readable report plus the machine-readable
case and audit, not a single financial verdict for every question.

`advisor_cli.py --case path --format json` emits `{ "case": {...}, "audit": {
"errors": [], "warnings": [], "verified_fits": [] } }`. Exit 2 signals invalid
input or failed invariants. Markdown is the default for a valid case; audit errors
are emitted as JSON even if Markdown was requested. Empty research-stage cases
remain visibly incomplete, not successful purchase advice.

## Focused executable assessments

`advisor_cli.py --assess KIND --input FILE.json --format json` returns the focused
assessment directly. Markdown is default. Inputs and examples are documented in
[assessment-inputs.md](assessment-inputs.md). Supported kinds: question,
requirements, location, amenities, documents, comfort, funding, loan_plan,
cost_comparison, exit, comparables, scenarios, search and watch.

Case schema3 remains supported with additive facts/conditions/analysis_requests.
Current references recompute; input fingerprints/change summaries expose results
and stale snapshot-only inputs. Strong verified hard-pass records need normalized
conditions and sourced facts. Question plans/source-input assessments are not
proof of actual web/route/PDF execution or institutional approval.

Unknown cost subtotals with no known components are null, not zero. A known
subtotal is still not an all-in total unless every relevant component/rule was
established. Valid fail/conditional/shortfall assessments exit0 with their status;
malformed/configuration/audit errors exit2. `--input` belongs to `--assess` and
`--previous-case` to `--case`; incompatible context flags are rejected.

## Legacy context CLI / Python callers

Existing v2 flags and assessor function signatures remain available. HDB context
requires `--flat-type`; private/rental/EC examples no longer require that unused
flag. Errors in these context modes now exit 2 instead of reporting success.

Unsupported valuation heuristics have deliberately changed:

- `verdict` is `insufficient evidence`; `premium_pct` is null for legacy assessors.
  A town mean or unmatched PSF median cannot establish exact-home value.
- HDB still reports filtered town/type context, but rainfall/amenity counts no
  longer determine financial value. Planning/MRT fields remain unknown unless
  the case workflow actually verifies them.
- Private and EC count datasets cannot supply price medians. Missing baseline
  remains null, not a fabricated price. Legacy scopes are labelled regional/
  unmatched context rather than town-matched observations.
- Supply classification is `unavailable` and ratio/demand null until scope,
  overlap and calendar periods are established. Latest source counts are context;
  vacancy series count is not a vacancy rate.
- Local trend calculation validates/sorts completed calendar quarters. Missing
  QoQ/YoY becomes null; duplicate periods require explicit aggregation.

Consumers must accept unknown/unavailable/null values instead of assuming three
market verdicts. The old schema examples mixing total asks with PSF baselines are
withdrawn; do not use them as reference valuations. Use the explicit unit-aware
calculator only after independent comparable/measurement verification.

The legacy shared API cache has no reliable freshness guarantee. The case
workflow uses native research or dated supplied evidence, not cached legacy
responses as proof of current inventory/rules. The shared generated client is
not modified by this skill release; other skills keep their existing behavior.

## Preserved agent scenario API — `--mode agent`

The separately implemented agent layer from ADR-008 remains available, including
its profiles, dated policy data, plan/compare/advise tasks and runnable examples.
It is a different input/output format from the schema-3 case record; do not pass
one format to the other or silently treat scenario output as researched evidence.

Uniform agent keys: `mode: "agent"`, `task`, `town`, `since` (start date), `asking`
(price string for single-option plan/advise), `verdict`, `premium_pct: null`,
`trend: null`, `location: null`, `ura_context: null`, `cea_verification: null`.
Additional keys: `agent`, `summary`, `disclaimer`, `policy_as_of`.

The scenario `verdict` is `affordable|stretch|not affordable|conditional` for a plan,
or a lowest modelled10-year occupancy cost among nonfailed scenarios for comparison.
Known financial/requirement/timing failures are excluded; lowest cost remains
different from an overall household recommendation.
These are results under supplied/default assumptions, NOT a final household
recommendation or current official eligibility. Inspect warnings, simplifications,
assumptions and unverified policy items before use. `policy_as_of` is a table-date
summary, not proof that all rules are equally current or applicable.

Money/ratios/rates are decimal strings. `agent.plan.checks[].ratio` is null for
missing positive income. `agent.profile`, `agent.plan` and `agent.comparison` are
documented in [agent-scenario.md](agent-scenario.md). `--summary-only` prints text.
The preserved agent CLI reports some failures as an `error` object with exit 0;
callers must inspect that object rather than treating exit 0 as successful analysis.

Its numeric categories are `resale_hdb`, `resale_condo`, `new_launch_condo`, `ec`.
Use the shared cross-category case workflow for new-HDB opportunities and landed
instead of relabelling them as condo scenarios. Reconcile scenario inputs/results
into the case with dates, assumptions, applicable rules and excluded costs.

Loan-plan changes: zero/prorated CPF usage constrains the cumulative property limit
including eligible fees and instalments; missing loan counts are conditional zero
illustrations, never an ownership-count inference. Nested unverified policy fields
reach the result. EC purchase_route distinguishes resale from developer stages;
MSR applicability must be supplied/verified for resale status. Actual payment_schedule
and milestones replace/default-override illustration dates. Unsupported contradictory
TOP metadata is not silently ignored. Different price/valuation requires quoted
loan.amount and loan.minimum_cash. Duties use max(price, supplied market_value),
with omitted market value explicitly a price-basis assumption.
