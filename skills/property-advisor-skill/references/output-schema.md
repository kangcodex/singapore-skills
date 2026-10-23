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

The scenario `verdict` is `affordable|stretch|not affordable` for a plan, or
`lowest 10-year cost of occupancy: <option>` for a multi-option comparison.
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
