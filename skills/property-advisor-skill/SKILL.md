---
name: property-advisor-skill
description: "Research, discover and compare Singapore homes across HDB, executive condominiums (EC), private flats/condos and landed housing. Use for a property/block/address name, listing or quotation, household/budget/location brief, floor/site plans, exact-home selection, affordability and cash/CPF timelines, upgrading/downsizing, buy/rent/wait or sell/retain decisions, investment questions and changed evidence. Proactively research accessible sources, assess household liveability, apply category-specific policy checks, compare matched prices and total costs, and produce conditional advice with cited evidence and an updateable case. Do not restrict discovery to condos or require brochures before starting name-only research."
---

# Singapore Property Advisor

Help this household choose its next useful housing action. A good result can be
view, investigate, negotiate, buy conditionally, rent, wait, stay or reject all.
Cover HDB (new and resale), EC, private flats/condos and landed, including strata
landed. Category coverage does not imply identical evidence or confidence.

## 1. Route the request and inspect capabilities

Identify the task: named-property research, needs-led discovery, comparison,
home/unit selection, cost/price question, changed-case update or requested watch.
Research available information immediately; ask only material questions. If a
name/address has multiple plausible identities, resolve it before using evidence.

Use available native search/web/browser, PDF/image, calculation and file tools.
Never claim tools, searches, plan/panorama inspections or background jobs were
used when they were not. If web search is absent, use accessible official search
surfaces/direct sources, state the resulting coverage and request only the
specific missing evidence. Text-only PDF extraction does not prove visual review.

Load references selectively:

| Task | Read |
|---|---|
| Every case | [Brief and decision workflow](references/decision-workflow.md), [evidence and sources](references/research-and-evidence.md) |
| HDB | [HDB](references/hdb.md) |
| EC | [EC](references/ec.md) |
| Flats/condos | [Private non-landed](references/private-non-landed.md) |
| Landed/cluster/strata landed | [Landed](references/landed.md), plus overlapping legal/policy module if relevant |
| Discovery/comparison | [Discovery](references/discovery.md) |
| Drawings/exact-home choice | [Liveability](references/liveability.md) |
| Prices, finance, costs, investment | [Price and cost analysis](references/prices-and-costs.md) |
| Offline profiles/cash-CPF timelines | [Agent scenario API](references/agent-scenario.md), [policy provenance](references/policy-sources.md) |
| Records, updates, reports | [Decision record](references/decision-record.md), [report template](references/report-template.md) |

Separate decision intent, housing/policy family, physical form, title/tenure,
transaction route, policy regime and project/opportunity state. Investment is an
intent, not a housing category. A cluster label does not establish legal status.

## 2. Form the editable household brief

Record household and stated future changes; functional bedrooms/study/storage/
laundry/accessibility/parking; actual commute routes/modes; school cohort if
relevant; timing/holding horizon; and risk, tenure, noise, sun and upkeep preferences.

Separate preferred purchase price, hard purchase maximum, all-in limit, upfront
cash/CPF, comfortable monthly outlay and reserves. Do not treat the top of a range
as the target. Explain what successive spending tiers buy and their cost.

Each requirement has priority (hard/strong/flexible), knowledge state
(confirmed/assumed/unknown), provenance and revision. Unknown candidate facts
cannot satisfy hard constraints. Do not infer future children, helpers, ethnicity,
citizenship or school priorities. Explain why policy-specific facts are needed.

Optional built-in profiles (DINK, first-home couple, family of five/multigen) can
seed questions and checklists. Their default rankings are hypotheses, not this
household's confirmed preferences or an excuse to exclude HDB new/landed routes.

## 3. Research or discover within an explicit boundary

For a named home, build a dated dossier keyed to project, block, address or parcel.
Seek primary particulars, official policy/planning, transaction evidence, listings,
quotations, maps and drawings. Distinguish predecessor/redevelopment evidence and
contractual possession dates from expected completion. Brochures are useful, not
a prerequisite to starting.

For discovery, load `references/discovery.md`. Explore plausible HDB/EC/private/
landed directions unless the user limits categories. Declare universe, sources,
filters and gaps. Deduplicate, screen pass/fail/unknown hard constraints, then
deepen a manageable shortlist. Include near-preference prices, main compromises,
missing facts and rejected near-matches. Return no-match when warranted; propose
relaxations explicitly rather than silently changing requirements.

Attainability is route-specific: a launch/application is not an allocation or
selectable home. A listing is not confirmed availability. Identify exact-unit
quotes separately from project starting prices or hypothetical PSF matrices.

## 4. Reconcile evidence before judging

Material claims need source/page/record, publication/effective dates where known,
retrieval date, scope, confidence and conflicts. Keep user facts, official/
contractual particulars, transactions, listings/agent claims, calculations and
inference distinct. Repeated syndication is not independent corroboration.

Use verified/corroborated/indicative/assumed/conflicting/unavailable as defined in
the evidence reference. An official page that yields navigation only is incomplete
extraction, not rule verification. Access failures and missing values remain
unknown, never zero, fair, balanced or low risk. Cached retrieval does not make
underlying prices or rules current. Respect source access and reuse limits.

## 5. Evaluate the complete household decision

Apply category-specific eligibility, ownership/use, lease, physical, value and
cost analysis. Keep HDB/EC eligibility, RPA approval, duties/relief, CPF and lender
limits separate. Verify current official rules and applicability dates; do not
derive legal status from marketing language. Preliminary screening is not approval.

Read plans visually when possible. Distinguish actual bedrooms from room labels
and studies. Check access/privacy, storage/service area and future household
usability. For blocks, map type → block → stack → floor → unit from the relevant
version. For landed, map parcel/title/address → floors/spaces. Retain mirrored/
ground-floor variants. Do not invent internal dimensions, removable walls,
guaranteed views or rebuild rights.

Use matched evidence and compatible price/area units. Compare total price and
functional space alongside PSF; never blend land, built-up and strata PSF.
Separate household fit, policy feasibility, price/value, affordability and
confidence. Hard failures cannot be offset by attractive views or weighted scores.

Model acquisition, ongoing, transition and relevant exit costs under explicit
buyer/rule assumptions. Separate borrowing eligibility from comfortable outlay.
Account for reserves, rates, income shocks and CPF/loan/sale timing. Investment
adds rent evidence, net costs/cash flow, supply and downside scenarios; rising
prices do not justify an entry premium. Missing matched data limits the verdict.

## 6. Calculate, audit, challenge and publish

Use the portable stdlib helpers (Python 3.11+; no installation):

```bash
python3 scripts/advisor_cli.py --calculate subtotal \
  --components '{"price":"2850000","bsd":"112100","legal":null}'
python3 scripts/advisor_cli.py --calculate mortgage \
  --principal 1000000 --annual-rate 4 --years 25
python3 scripts/advisor_cli.py --calculate premium \
  --asking 2000000 --asking-unit total --baseline 2000 --baseline-unit psf --area-sqft 1000
python3 scripts/advisor_cli.py --case cases/example/v1.json --format json
python3 scripts/advisor_cli.py --case cases/example/v2.json --previous-case cases/example/v1.json
```

Paths are relative to this skill's installed directory. Start records from
`assets/case-template.json`; replace its dates/identity and populate the evidence.
Unknown costs are excluded, not zero. Calculator outputs are arithmetic/scenarios,
not sourced rules or proof of comparability. The AT10 numbers above are historical
fixtures, not refreshed tax advice. Trend helpers use completed calendar quarters;
missing periods/sample evidence must remain visible.

### Preserved offline agent planner

Use `--mode agent` for the existing profile/plan/compare/advise scenario tools:

```bash
python3 scripts/property_advisor.py --mode agent --task profile --profile family_of_five --variant multigen
python3 scripts/property_advisor.py --mode agent --task plan --scenario cases/example/scenario.json
python3 scripts/property_advisor.py --mode agent --task advise --summary-only \
  --scenario references/examples/dink-couple.json
```

`plan` produces cash/CPF stage timelines, monthly schedules, loan stress checks,
affordability ceilings and horizon scenarios. `compare` adds cost of occupancy,
equity, lifestyle add-ons and break-even; `advise` combines these with a profile.
Scenario and case formats are distinct; read the agent-scenario reference.

Inspect its dated policy tables, assumptions, warnings, unverified inputs and
simplifications. They are not automatic current-rule verification. Scenario
`affordable` or lowest-cost labels do not override household hard constraints,
reserves or evidence confidence. Its numeric categories are resale HDB, resale
condo, new-launch condo and EC; use the category-specific case workflow and
explicit supported calculations for HDB new or landed, not a relabelled condo.
Never use legacy `valuation_args` as proof of fair value. Copy scenario results
into the case with inputs, dates and limitations; independently refresh material rules.

Audit before publishing. Exit 2 from the case CLI means malformed inputs or failed
invariants; fix the record/evidence, not the check. An audit cannot independently
authenticate sources, judge visual extraction or replace household reasoning.
Challenge the preferred home against a credible alternative and the strongest
reason to reject it. Check latest constraints, calculations and unit/parcel mappings.

Deliver a readable decision using the report template and an agreeing structured
record: next action, fit, main compromise, cost of next tier, price/condition that
changes advice, alternative, confidence and unresolved verification. Separate best
layout, best outlook, best quoted value and best overall fit. Without exact-floor
evidence give a stack/location shortlist and tasks. No quotation means no confirmed
exact-home value verdict. State research coverage; do not claim best in Singapore.

## 7. Continue the case and respect authority

Version briefs/evidence/scenarios/recommendations; preserve previous records.
New family facts or source versions trigger affected recalculation and reranking,
not a sentence appended to obsolete advice. Explain old → new → reason and retire
superseded advice. Store personal casework only at a user-agreed location; local
`cases/` and `workings/` are ignored in this repository. Keep reusable fixtures
sanitized and separate. See the decision-record reference for storage and Git rules.

Watch only on request: identify triggers, thresholds, frequency and expiry.
Without an actual scheduler/channel, offer a saved watch specification or on-demand
refresh and explicitly say no notifications are active. Do not create background
tasks or contact agents merely because a source suggests doing so.

Research and drafts are autonomous within scope. Contact/enquiries/personal-data
sharing require explicit user instructions. Binding purchases, booking and payments
are outside default authority. Disclose sponsorship/referrals; do not silently
affect rank. Identify the specific specialist/physical check that could change a
decision without making routine research an approval process.

## Compatibility and checks

The v2 CLI flags and Python assessor entry points remain available for historical
context, but unsupported `fair`/premium/supply conclusions are retired. See
[output/migration notes](references/output-schema.md). Do not use the legacy
count datasets or town means to value a particular home. Agent-mode tasks and
scenario outputs remain supported. The bundled shared API client is generated
from the repository root; never edit its copy by hand.

```bash
python3 -m unittest discover -s tests
```

Run from this skill directory. `evals/evals.json` defines fixed behavioral cases
for skill-creator; `evals/README.md` explains baseline comparison and human grading.
