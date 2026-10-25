# Decision record, audit and continuity (schema 3.0)

Copy `assets/case-template.json` to a user-agreed local case directory. Use ISO
dates and a stable case id outside the installed skill. Version each revision; never overwrite previous advice
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

## Semantic facts and executable questions

Schema3 has additive `facts`, requirement `condition` and `analysis_requests`
fields. See [assessment inputs](assessment-inputs.md) for exact operators and
[bound execution](assessment-inputs.md#bound-case-execution-and-revision) for JSON Pointers.

Property/candidate facts use state/value/unit/basis/evidence_ids records. Conflicting
known overrides remain conflicting. A verified hard pass now requires an actual
semantic pass plus appropriate current fact evidence, not only a declared `pass`.
Legacy records with missing normalization should leave checks unknown or remain
explicitly conditional; unsupported strong hard-pass claims fail audit.

`--case` computes normalized checks, algorithm-owned rejections and bound
`analysis_requests`. It returns candidate_facts, assessment_results with current
input fingerprints, and change_summary on revision. Inputs and previous files are
not overwritten. JSON Pointers refer only to this case; nested input slots can
bind earlier results, such as exit proceeds into a funding receipt. Unknown/
conflicting fact values are not stripped into apparently known scalar inputs.
Constant analysis input is snapshot-only; refresh it if its real-world context
changed. Actual native research/tool execution remains separate from arithmetic.

Candidate `checks`: `{ "requirement_id":"r1", "result":"pass|fail|unknown",
"evidence_ids":["e1"] }`. Candidate `fit` is `verified|conditional|stretch|rejected`.
Usable evidence requires `extraction_status: "completed"` as well as verified or
corroborated confidence; absent/partial extraction cannot establish a verified pass.
Availability is `confirmed|quoted|listed|application|allocated|selectable|unknown|withdrawn`.
Quoted/listed opportunities still need current confirmation before action.

Explicit applicability conditions may produce `not_applicable`, which is separate
from a favorable pass. Empty/all-exempt conditions do not establish a verified fit.
The audit does not authenticate a source, approve eligibility, prove all costs or
certify a room; fit/policy/availability/affordability/value/confidence remain separate.

Recommendation `claims` are evidence-dependent conclusions, each with `kind` and
`evidence_ids`. Use `layout`, `view`, `exact_value`, `eligibility`, `redevelopment`,
`scenario` or `inference`. An exact-value claim needs identified unit/parcel price
evidence and a matched comparable set. General inference is not a way to relabel
an unsupported exact-value/view/legal claim. Describe missing evidence openly.

## Verification and reports

Run `python3 scripts/advisor_cli.py --case /path/to/cases/id/v1.json --format json`.
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

Confirmed changes/removals need history source_kind:user, a reason and
changed_requirement_ids. First-time normalization of unchanged confirmed wording
is additive. If wording changes but its old predicate remains, explicitly review
normalization (normalization_reconfirmed) or correct the predicate. A generic
“refresh” history cannot silently discard the user's hard budget/room requirement.
Unchanged old summaries/recommendations are marked superseded after material input
changes; the Markdown renderer does not show that old summary as current advice.

## Storage and Git: workings versus distributable assets

User chooses local persistence/retention; do not silently upload household data.
Store raw uploads, source snapshots, case versions, report exports, screenshots,
viewing notes, logs and watch state in a user-agreed workspace outside the skill.
In a repository checkout, `reports/` is ignored. Evaluation outputs/transcripts/
grades belong in ignored `development/property-advisor/evals/runs/` or `reports/`.

Track SKILL.md, category/source references, scripts and the case template in the
skill. Track tests, fixed eval prompts and synthetic evidence fixtures separately
under `development/property-advisor/`. Do not ignore all JSON,
PDFs/images, tests or references: those patterns hide required deliverables.
The root `.gitignore` also excludes `docs/property-advisor/` design workings,
the local PRD/research/spike documents and
already covers Python caches, coverage, environments, logs and OS junk.

Ignoring does not untrack existing Git files or establish permission to delete
them. Before committing check actual `git status`, intended staged files and
`git check-ignore --no-index` for representative workings AND retained assets.
Installed skills outside this repo may not inherit these ignore rules; check the
chosen case repository before storing personal or licensed data there. Importers
may copy ignored local files; distribute the clean runtime export, not a working
directory containing personal data.
