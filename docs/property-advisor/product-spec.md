# Product specification — question-led Singapore housing advisor

Version 1.0 proposal | 24 October 2026 | Current-code review base: `afcc654`

## Purpose and product outcomes

Help households choose the next useful housing action using their requirements,
finances, daily routines and the best accessible evidence. Support a property
name/address, a listing, a document, a question or a household brief as an entry.
The user can ask a narrow question without restarting a complete buying process.

Reduce research/reconciliation effort, reveal attainable alternatives, prevent
marketing-led mistakes, expose costs and trade-offs, and preserve a challengeable
decision history. Optimize supported household decisions rather than transaction
volume, prestige, budget utilization or assumed appreciation.

This is a **proposed next iteration**, not a new implementation claim. It extends
the existing cross-category workflow and retains its evidence/authority principles.
Read the [question catalogue](business-questions.md), [contracts](decision-contracts.md),
[current capability evidence](capability-and-spikes.md) and [roadmap](roadmap.md).

## Audience and coverage

Households first: singles/couples, families, multi-generation, upgraders,
downsizers and later-life households. Investors, tenants, landlords and sellers
use the same evidence where their requested decision needs it; investment is a
decision lens, not a housing category. Do not infer household structure or future children.

| Housing/policy family | Required distinctions |
|---|---|
| HDB | New allocation versus resale, applicable scheme/lease, household/HFE/grants/loan/ownership/quota/MOP/use questions |
| EC | Developer purchase versus resale, completion/restriction dates, buyer pool, loan/payment/use applicability |
| Private non-landed | Flat/condo, new/resale/subsale, title/tenure, management, layout/unit and measurement conventions |
| Landed | Individual/strata title and approved context, form/parcel/land/building, ownership/planning/condition and repair/development limits |

Physical form, title/tenure, transaction route, completion state, policy regime
and availability are separate dimensions. Do not assign progressive construction
payments to a completed EC, or silently map landed/new HDB into a condo model.
Special products and unclear classifications remain explicitly conditional.

Public sources plus permitted uploads are the starting access model. Paid accounts,
complete live inventory and licensed redistribution are not assumed. Source failure
must preserve useful work without inventing a result.

## Service depths and answer modes

| Depth | Example | Required behavior |
|---|---|---|
| Focused answer | “Is this near MRT?” | Resolve the place, answer the specific question with evidence/limits; no unrelated financial intake |
| Targeted assessment | “Compare our three commutes” or “Will this plan fit us?” | Ask only missing material facts; produce the relevant route/function assessment |
| Decision package | “Find our home” or “Should we buy this unit?” | Build/update brief, search/evidence/cost scenarios, challenge alternatives and produce a conditional decision |
| Revision | “Here is a new plan/quote/deadline” | Identify changed facts, recompute dependent results and retire superseded advice |

Mixed questions compose relevant modes. The answer contract is: **direct result,
household implication, evidence/assumptions, material uncertainty, next action and
recommendation-changing condition**. A narrow request does not require all case
entities to be populated before a useful response.

## Functional requirements

### FR01 — Question routing and proportional intake

Identify requested decision, entities, depth and minimum material inputs. Resolve
ambiguous names/units/destinations. Start available research without demanding every
brochure or financial fact. Return useful partial answers with named missing inputs.

### FR02 — Adaptable, auditable requirements

Retain original wording, normalized meaning, unit/basis, priority, knowledge state,
provenance, applicability/reference date and approved exceptions. Support bounded
all/any/conditional combinations for common predicates. Distinguish preferences
from hard limits; never inherit another household's thresholds or compensate a
hard failure with points. Semantic checks must use applicable facts, not only a
previously declared pass label.

### FR03 — Age, status, occupancy and temporal precision

Model actual TOP/completion, expected TOP, contractual possession, practical keys/
renovation/extension and user move deadline independently. “Recent completed OR
permitted future launch” is valid. Age needs a reference date; partial dates and
phased blocks need appropriate scope/intervals. Future TOP is not negative building
age, guaranteed occupancy or an automatic rejection for exceeding the current year.

### FR04 — Category, route and policy feasibility

Apply relevant household/property/title/loan/date facts and official rules. Keep
ownership count separate from outstanding housing loans; grants/reliefs conditional
until applicable facts are established. Source verification and applicability are
distinct. Separate advisory screening from official/lender/technical approval.

### FR05 — Discovery, attainability and deduplication

Declare universe, queries, filters, covered/missing sources and dates. Explore
credible alternatives; deduplicate reliable unit identities and flag uncertainty.
Keep launch/application/allocation/selectable unit/listed/quoted/confirmed/withdrawn
states distinct. Show near-preference budgets, compromises, exclusions and no-match
results. Proposed relaxations need explicit adoption before changing the brief.

### FR06 — Actual daily transport and future-network scenarios

Use actual endpoints/entrances, travel modes, days/times, transfers/accessibility
and person/destination frequency where material. Distinguish straight-line distance,
estimated walk, routed walk, next-vehicle arrival and whole-journey duration.
Preserve source/network versions and current/future scenarios. A provider lacking
in-vehicle time or station coverage cannot validate a commute constraint.

### FR07 — Relevant schools, amenities and neighbourhood evidence

Resolve requested service types, operating status/hours, access and household
suitability. Use applicable official school-distance/cohort/address methods when
making eligibility conclusions; proximity is not admission. Distinguish local
exposure/planning evidence from rainfall, generic amenity counts or marketing.

### FR08 — Document ingestion, mapping and contradictions

Retrieve accessible primary documents or ingest supplied files. Record file/version/
page/figure provenance and text/visual extraction status. Extract particulars,
dimensions, price kind and type/block/stack/floor/unit mapping without inventing
missing fields. Reconcile revisions and propagate contradictions; source content
does not authorize actions. Scanned/visual cases need separate validation.

### FR09 — Household function and long-term comfort

Assess occupant roles, agreed sleeping/sharing groups, privacy/work, furniture and
clearances, storage/laundry/cooking, bathrooms, accessibility and stated life-stage
scenarios. Separate advertised area from verified net/internal/usable area. Full
baths and service WC, HDB room labels and bedrooms, studies and approved/practical
bedrooms remain distinct. A sleeping-room count is only one sub-assessment.

### FR10 — Matched price evidence and measurement

Classify every price, unit/area basis, date, terms and availability. Construct
traceable comparable sets with selection/exclusion/pending reasons, sample/window,
scope and justified adjustments. Separate cross-project controls from same-project
matches. District medians, count datasets, stale listings and incompatible PSF are
not exact-unit values. Missing/partial quarters are not zero growth.

### FR11 — Complete versus partial whole-decision costs

Separate acquisition, deposits already credited, fit-out, holding, transition and
exit costs, cash/CPF/loan treatment, grants and reserves. State formulas, dates,
rounding, source/quote assumptions and exclusions. Unknown components block an
all-in claim. Do not turn default fees/Annual Value into verified cost estimates.

### FR12 — Dated funding, strategy and household resilience

Build actual/estimated event schedules using applicable contract/statutory dates
and drawdown/receipt timing. Model fund eligibility/caps, cash/CPF reserves,
user-selected strategies, recurring obligations, household net cash/inflows/living
expenses and transitions. Detect first shortfall/peak need; later proceeds cannot
fund an earlier payment. Preserve money conservation and separate principal/equity
from cost. Enforce CPF limits in both stages and monthly payments.

### FR13 — Field-level applicability, confidence and capability limits

Propagate nested rule/source uncertainty and effective/applicability/retrieval dates
to the conclusions they limit. Track supplied/derived/defaulted/unused material
inputs. A dated table or successful HTTP request is not verified applicability or
successful extraction. Cap the affected conclusion, not every unrelated answer.

### FR14 — Evidence-backed scenarios, break-even and net exit

Explain thesis/counter-thesis and downside/flat/base/upside inputs/horizons using
matched evidence, competing supply and household assumptions. Negative cases must
be possible. No calibrated forecast/probability is implied. Distinguish market
value, equity, net sale proceeds, CPF refunds and spendable cash; define nominal
versus economic break-even and avoid double-counting refunds or principal.

### FR15 — Feasible, explainable household decisions

Separate requirement fit, attainability, policy feasibility, affordability,
price/value, utility and evidence confidence. Lowest TCO is a numeric comparison,
not automatically the best feasible home. Show marginal benefits/retained capital,
credible alternatives and strongest rejection reason. Scores are optional,
adjustable and transparent; unknowns receive no favorable defaults.

### FR16 — Revision, dependency and report consistency

Version facts/briefs/searches/scenarios/recommendations. Identify semantic changes,
refresh volatile facts, recompute affected assessments and explain old→new→reason.
Preserve exclusions and user provenance. Keep readable and structured results in
agreement. A nonempty history field alone does not prove reassessment occurred.

### FR17 — Authority, privacy and requested execution

Research/drafts are autonomous within the request. Outreach, enquiry submission or
personal-data sharing need explicit instructions; transactions are outside default
authority. Make storage/retention/export/correction visible. Keep licensed/personal
material local unless authorized. Monitoring needs explicit scope/triggers/expiry
and an actual execution/channel; otherwise offer a saved specification/on-demand
refresh without claiming active alerts.

### FR18 — Evaluation and capability-based release claims

Verify deterministic logic at the cheapest meaningful boundary, and native/source/
visual behavior with appropriate actual artifacts and independent review. Keep
prototype checks, mocked provider responses, live-source validation and human
acceptance distinct. Log access limits honestly. Production claims require passed
journey/category evidence, not merely a larger prompt or green unit suite.

## Distinctive decision materials

- **Requirement interpretation sheet:** original phrase, meaning, hard/preference
  status, date/unit basis and approved exception.
- **Daily-routine comparison:** burden by person/destination/time, not a single
  average that hides a hard commute failure.
- **Family function map:** source-linked rooms/storage/service/access needs now
  and under stated future scenarios.
- **Premium justification sheet:** what each spending tier adds and displaces;
  distinguish purchase-price headroom from actual retained cash.
- **Milestone funding map:** due date/window, eligible funds, available balances,
  reserve floor and shortfall/next funding action.
- **Evidence/readiness board:** material contradictions, blocked facts and the
  next information most likely to change the decision; no unexplained readiness %.
- **Entry/exit scenario sheet:** comparable evidence, scenario rationale, costs,
  break-even and cash/CPF outcomes.

## Alternatives and assumptions to validate

| Approach | Value | Main trade-off / decision |
|---|---|---|
| Expand checklists only | Fast, broad native conversation coverage | Does not correct funding inconsistencies, evaluate predicates or establish source capability; insufficient on its own |
| Question-led native workflow plus bounded contracts/calculators | Useful small answers and deep decisions sharing evidence, with deterministic checks where needed | Selected direction; requires adapters, real source/visual packs and careful conclusion gates |
| Full inventory/geospatial/forecast platform | Could improve automated coverage and continuous monitoring | Large access/licensing/operational commitment; not required to prove the household decision job and not the selected forecasting scope |

| Assumption / possible failure | Validation and response |
|---|---|
| Public/native/supplied evidence is useful enough | Prove actual route, comparable and brochure paths; narrow unsupported claims and request specific permitted evidence rather than inventing completeness |
| A bounded predicate set captures common requirements | Test paraphrases, grouping, date precision, units and conflicting wishes; ask a material clarification when meaning changes the decision |
| One case can reconcile current scenario/report formats | Test adapters, consumed/defaulted/unsupported inputs and changed dependencies; preserve interfaces through an explicit migration |
| Funding strategies remain correct under actual rules | Start with the reproduced usage/confidence issues, then test caps, reserves, chronology and real contract dates; do not market a prototype as a financial plan |
| Native documents support reliable family reasoning | Use real native/scanned/watermarked packs and independent review; keep extraction, dimensions, approved use and comfort as separate claims |
| Comparisons remain helpful without a forced winner | Review infeasible-cheapest, missing-evidence and no-match cases; surface marginal trade-offs and the next decision-changing fact |

## Success and release criteria

Measure hard-constraint violations, source/price/mapping/unit accuracy, numeric
errors, inappropriate confirmed conclusions, useful-answer time, duplication,
coverage transparency, revision consistency and user understanding. Evaluate
whether the next action is useful even with partial evidence. Short-term property
price performance is not a proof of advisory quality.

Before claiming the proposed comprehensive behavior, satisfy the [roadmap's
combined gates](roadmap.md), retain existing acceptance coverage, and execute the
[35-case plan](acceptance-plan.json). Every category needs a useful known-evidence
case and an appropriate missing-evidence case. Returning unknown to everything is
not sufficient; inventing evidence to force a winner is also unacceptable.

## Delivery boundaries and unresolved decisions

No new forecast platform, paid-data dependency, autonomous agent contact, formal
valuation/lender/structural/legal certification or guaranteed allocation/admission/
returns is introduced. Native tools may be sufficient for some workflows; provider
access and actual visual extraction remain engineering/validation gates.

Before implementation decide the bounded requirement schema, case/scenario adapter
and migration; funded-ledger contract; source/provider access/reuse; native-tool
targets and real sanitized evaluation packs. Preserve current interfaces unless
a separately approved migration changes them. Scope breadth is confirmed; claims
of implemented depth must follow evidence.
