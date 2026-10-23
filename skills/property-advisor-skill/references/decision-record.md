# Decision record, audit and continuity (schema 3.0)

Copy `assets/case-template.json` to a user-agreed local case directory. Use ISO
dates and a stable case id. Version each revision; never overwrite previous advice
silently. This is a structured research record, not a mandatory database.

## Entities and fields

Top level: `schema_version: "3.0"`, `case_id`, positive integer `version`,
`research_date`, `buyer_brief`, `search_brief` and the arrays below. Empty arrays
are valid during research but do not constitute a completed decision.

| Entity | Minimum information |
|---|---|
| buyer_brief | `requirements` with id/value/priority/state/provenance; separate budget bases, assumptions/unknowns |
| search_brief | categories, coverage, sources/filters, timing, exclusions/relaxations |
| properties | id, category `hdb|ec|private_non_landed|landed`, identity, form/title/tenure/route/status and evidence |
| candidates | id, property_id, identifiers/areas/layout, price basis, availability, fit and requirement checks |
| evidence | id, claim, source/page, kind, scope, confidence, retrieved_at, extraction_status; known publication/effective dates, contradictions and candidate_id for exact-home evidence |
| comparables | id, candidate_id, rationale, sample/window, observations, area/price bases, exclusions/adjustments and evidence_ids |
| cost_scenarios | id, buyer/rule assumptions, dates, components, sensitivities, rounding, exclusions and evidence_ids |
| recommendations | id, candidate_id (nullable for search/wait), action, separate fit/policy/affordability/value/confidence, conditions/alternatives/reasons and claims |
| policy_assessments | id, applicable facts/dates, rule/version/source, result and unresolved conditions; evidence_ids |
| source_access | id, source, attempt date, completed/partial/blocked/unavailable/not_attempted, extraction/coverage limitation |
| history | id, prior/new version, changes/reasons, affected dependencies, exclusions, pending actions and superseded recommendations |

Known/unknown/not-applicable facts must be explicit; do not use null to mean both
unknown and not-applicable. Suggested field: `{ "state": "unknown", "value": null }`.
Price fields need kind/currency/unit/area basis/date/terms and availability. A
`scenario` is not `quotation`; a `listing` is not a confirmed transaction.

Candidate `checks`: `{ "requirement_id":"r1", "result":"pass|fail|unknown",
"evidence_ids":["e1"] }`. Candidate `fit` is `verified|conditional|stretch|rejected`.
Usable evidence requires `extraction_status: "completed"` as well as verified or
corroborated confidence; absent/partial extraction cannot establish a verified pass.
Availability is `confirmed|quoted|listed|application|allocated|selectable|unknown|withdrawn`.
Quoted/listed opportunities still need current confirmation before action.

Recommendation `claims` are evidence-dependent conclusions, each with `kind` and
`evidence_ids`. Use `layout`, `view`, `exact_value`, `eligibility`, `redevelopment`,
`scenario` or `inference`. An exact-value claim needs identified unit/parcel price
evidence and a matched comparable set. General inference is not a way to relabel
an unsupported exact-value/view/legal claim. Describe missing evidence openly.

## Verification and reports

Run `python3 scripts/advisor_cli.py --case cases/id/v1.json --format json`.
Exit 2 blocks publication of inconsistent records; zero indicates the checked
invariants passed, NOT independent source truth, legal approval or complete advice.
Human/agent review must still verify calculations, source accuracy, household
reasoning, measurement, matching and applicability. The renderer does not perform
research or fabricate decisions; use the consumer report template for final prose.

For updates include `supersedes` equal to previous version and a nonempty history.
Run with `--previous-case`. Preserve confirmed requirements unless the user changes
them; record that provenance. Compare old → new → reason, refresh dependent facts,
recompute costs, rescreen/rerank and retire superseded advice. Keep the readable
report consistent with the current record and retain prior versions locally.

## Storage and Git: workings versus distributable assets

User chooses local persistence/retention; do not silently upload household data.
Store raw uploads, source snapshots, case versions, report exports, screenshots,
viewing notes, logs and watch state under local `cases/` or `workings/`. Both are
ignored in this repository. Evaluation outputs/transcripts/grades belong in
`evals/runs/` or sibling `property-advisor-skill-workspace/`, also ignored.

Track SKILL.md, category/source references, scripts, sanitized reusable assets,
tests, fixed eval prompts and synthetic evidence fixtures. Do not ignore all JSON,
PDFs/images, tests or references: those patterns hide required deliverables.
The root `.gitignore` also excludes the local PRD/research/spike documents and
already covers Python caches, coverage, environments, logs and OS junk.

Ignoring does not untrack existing Git files or establish permission to delete
them. Before committing check actual `git status`, intended staged files and
`git check-ignore --no-index` for representative workings AND retained assets.
Installed skills outside this repo may not inherit these ignore rules; check the
chosen case repository before storing personal or licensed data there.
