# Implementation roadmap and release gates

**Proposed work, separately authorized from this documentation delivery.** No
implementation branch, integration, dependency or remote release is implied.
Keep existing runtime contracts unless an explicit migration approves changes.

## Principles

Deliver thin, testable decisions rather than a monolithic rewrite. Preserve all
four housing/policy families in the product definition. Instruction-driven/native
workflows can be appropriate if evaluated; deterministic financial and predicate
claims need meaningful calculation tests. Fix trust defects before adding confidence
to detailed financial recommendations. Data/tool access gates the conclusions, not
the household's right to receive useful partial research.

## Slices

| Slice | Owned seam / deliverable | Dependencies | Acceptance / exit check |
|---|---|---|---|
| I01 Financial trust corrections | Existing funding limits, nested verification, loan/property counts, route applicability and unsupported-input reporting | Reconfirm applicable semantics/rules; preserve interface compatibility | Failing regressions for zero CPF across all payment types and nested uncertainty; AC19/20/24/25; existing suite retained |
| I02 Requirements and focused answers | Bounded normalized predicates, date/status/occupancy semantics, question plans and proportional intake | Approved field/serialization adapter and migration plan | AC01–AC07, AC09; actual facts evaluated rather than declared labels; ordinary narrow query needs no financial profile |
| I03 Documents and household function | Native retrieve/ingest, file/page/version-to-fact contract, mapping, conflict and functional assessment | Native tool target; sanitized real native/scanned/image packs | AC14–AC18; independent extraction/fit review; no study/WC/area-basis promotion |
| I04 Location and discovery providers | Actual endpoint/entrance resolution, route/amenity/provider contracts, scoped inventory/deduplication | Provider access/reuse proof; do not reuse unsafe sibling ETA/yield output | AC08–AC13, AC30/34/35; current/future/estimated/routed results distinct; useful blocked-source fallback |
| I05 Dated household funding and exit | Property-specific milestones, eligible allocation strategies, reserve/balance ledger, sale/purchase overlap and exit cash | I01/I02 and sourced contract dates/eligibility; keep unverified values conditional | AC21–AC25/28; first/peak shortfall, no early spending of proceeds, no double-counting, strategy comparison with identical household facts |
| I06 Comparable scenarios and decision continuity | Matched selection/adjustments, entry conditions, downside/flat/base/upside rationale, feasibility-gated alternatives and dependency updates | I02–I05 plus actual source packs and stable case/scenario adapter | AC26–AC31/34; no unsupported exact-unit forecast/value; reports and records agree after changes |
| I07 Combined qualification and delivery | Category/journey matrix, native-tool transcripts, human review, corrections, capability documentation and opt-in execution boundaries | Prior slices unchanged and passing | All35 planned cases plus retained original coverage; category-specific known/missing-evidence cases, authority/export/watch checks AC32/33 |

These slices are dependency boundaries, not seven required agents or rigid parallel
teams. Tightly coupled requirements/finance changes should stay serial until
interfaces and exclusive ownership are clear.

## Mandatory design decisions before code

1. **Requirement representation:** a small tagged predicate set and grouping,
   source/date/measurement precision, hard/preference/exception provenance. Avoid
   arbitrary expression execution.
2. **Case/scenario adapter:** current schema3 records and agent scenarios differ.
   Decide versioning, consumed/unsupported input reporting and compatibility tests.
3. **Funding ledger:** input event/date-window contract, per-funder rules/caps,
   per-owner details where required, reserves and chronological failure handling.
4. **Provider feasibility:** obtain permitted route/current-network/inventory and
   school/service evidence. Record actual access/coverage rather than rely on names.
5. **Document evaluation:** select real/sanitized native/scanned examples and human
   reviewers; dimension/approved-use ambiguity must stay visible.
6. **Rules and claims:** refresh applicable sources/contracts and propagate nested
   uncertainty. Dated placeholders do not become payment instructions.

## Test and evaluation layers

- **Deterministic:** money/unit/rate/date precision, grouped predicates, cap/reserve
  allocation, conservation, duplicate/pending classifications, exit identity and
  changed-dependency invalidation. Write a failing regression for each known defect.
- **CLI/adapter:** real entry points, malformed/missing/unsupported inputs,
  compatibility and agreeing readable/structured outputs.
- **Source contracts:** source-shaped fixtures for actual provider schemas and
  error/partial/stale/withdrawn states; mocks cannot prove live access.
- **Native document/location workflows:** inspect real tool traces and evidence,
  including failures. Text-only fixtures cannot validate scanned visual extraction.
- **Human decision review:** household function, comparable rationale, useful
  trade-offs, scope/uncertainty and next actions. Avoid keyword-only grading.

The [acceptance plan](acceptance-plan.json) supplies 35 proposed case definitions,
question/requirement links and oracles. Its `planned` status must remain until an
actual implementation/run satisfies them. The design's static consistency check
is not execution of those domain cases. Retain existing skill-creator AT01–AT40
coverage; add the new cases without relabelling incomplete old runs as passes.

## Combined release gates

- Known hard-constraint violations, invented quotations/availability and
  incompatible monetary/area comparisons: **zero**.
- No CPF allocation beyond permitted/cumulative usage or reserves; zero-use
  restriction covers stage and recurring payments.
- Actual/estimated/contractual milestones labelled and sourced; insufficiently
  funded dates and unknown deadline anchors cannot yield confirmed feasibility.
- All material claims traceable to appropriate scope/date, with nested uncertainty
  and blocked/partial evidence disclosed. No false current-route/provider claim.
- Real native/scanned document packs and independent family-fit review completed
  for the visual capabilities being advertised.
- At least one useful known-evidence and one bounded missing-evidence case for HDB
  new/resale, EC developer/resale, private non-landed and landed. An unsupported
  math route is not silently substituted.
- Matched valuation/scenario conclusions bounded by evidence; appreciation remains
  scenarios, not a promised point forecast. Net exit cash reconciles.
- Changed requirements/evidence produce consistent brief/search/scenario/report
  updates and explicit supersession, with prior exclusions retained.
- Local deterministic/CLI/source tests pass; relevant native/human evaluations
  recorded; unchanged versions are the ones delivered.

## When access or evidence blocks a slice

Preserve completed facts, the attempted source/status and the exact conclusion
that cannot be made. Offer a useful bounded answer or a targeted request for a
permitted extract. Do not retry denied access through another runner, request
credentials, infer zero or weaken constraints to manufacture completion. If a
core capability cannot be supported, narrow the public claim and record the blocker.

## Delivery hygiene

Track reviewed spec/contracts, sanitized reusable fixtures, implementation and
tests once authorized. Keep raw prototypes, reports, uploaded/licensed sources,
personal cases and eval transcripts/results ignored. Commit only intended paths
and record the actual verification and remaining blockers with each delivery.
Follow the repository's authorization and review workflow for implementation,
integration, merge and deployment.
