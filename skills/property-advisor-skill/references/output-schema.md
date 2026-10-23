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

## Legacy CLI / Python callers

Existing v2 flags and assessor function signatures remain available. HDB context
requires `--flat-type`; private/rental/EC examples no longer require that unused
flag. Errors now exit 2 instead of reporting success.

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
