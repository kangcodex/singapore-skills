# Property advisor behavioral evaluations

`evals.json` follows skill-creator's `skill_name`/`evals` format with `id`, `prompt`,
`expected_output`, `files` and human-verifiable `expectations`. File paths resolve
from this directory. The five scenarios cover AT01–AT40 (some grouped) and source,
unit/price, authority and missing-data invariants. They are not keyword tests.

The evidence pack is explicitly synthetic; historical layout/BSD examples are
fixed fixtures, not current recommendations. Text fixtures test reasoning only.
Use actual sanitized plan images and independent extraction review before claiming
visual performance. The name-only case uses available native web tools and must
report real research/access limits; it has no pre-filled identity answer.

## Run with skill-creator

1. Preserve the old skill from the selected base revision, including its bundled
   resources. Use the identical prompt/evidence for original and candidate runs.
2. Run each case in fresh native contexts. Review transcripts as well as answers;
   do not infer a search or visual inspection from polished prose.
3. Grade each expectation with `text`, `passed`, `evidence` in `grading.json`.
   Separate automated math/audit tests from human advisory-quality evaluation.
4. Store outputs, transcripts, timings when actually reported, grades and feedback
   in ignored `runs/iteration-N/` (or sibling `property-advisor-skill-workspace/`).
   Baseline/candidate sources and grader details must be recorded for repeatability.
5. Aggregate and generate skill-creator's review viewer; obtain independent human
   review of usefulness, matching, extraction and policy applicability before
   claiming comprehensive production advisory quality.

Unit tests are independently runnable with:
`python3 -m unittest discover -s skills/property-advisor-skill/tests` from repo root.
They prove calculations/record/CLI invariants, not all natural-language expectations.
Do not equate a green scripted fixture with validated real-world recommendations.

Minimum release-review evidence includes useful named research, cross-category
discovery, exact-home/layout reasoning, category traps and multi-turn updates.
Each category needs meaningful known-evidence and missing-evidence cases; returning
unknown to every question is not adequate category support. A formal valuation,
official approval or guaranteed availability is never the expected output.
