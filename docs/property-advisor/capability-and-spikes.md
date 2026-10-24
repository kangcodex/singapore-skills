# Capability review and deeper spike findings

Reviewed source: `afcc654` | Experiments: 24 October 2026 | Scope: design evidence

**No production behavior was changed.** Current tests, synthetic prototypes,
offline mocked observations, native document parsing and live-source availability
are separate forms of evidence. Raw scripts/PDFs/results remain under ignored
`reports/`; this document is the curated, publishable record.

## Current capability boundary

| Area | Observed support | Limit / proposed response |
|---|---|---|
| Question/research workflow | [SKILL.md](../../skills/property-advisor-skill/SKILL.md#L13-L119) supports task routing, native research, briefs and category modules | Add focused-answer contracts and actual behavior validation, not necessarily a CLI for every question |
| Case audit | [advisor_case.py](../../skills/property-advisor-skill/scripts/advisor_case.py#L70-L149) validates declared checks/provenance, IDs and revision metadata | It does not evaluate age/travel predicates or prove dependent recalculation occurred |
| Arithmetic | [advisor_calculations.py](../../skills/property-advisor-skill/scripts/advisor_calculations.py) protects price units and provides Decimal costs/mortgage/calendar trends | Comparable selection, source applicability and comfortable affordability are separate |
| Finance scenarios | [agent_cashflow.py](../../skills/property-advisor-skill/scripts/agent_cashflow.py) implements schedules, funding and stress/horizon assumptions | Fixed offsets, zero-CPF inconsistency and incomplete household liquidity/applicability remain important gaps |
| Comparison | [agent_compare.py](../../skills/property-advisor-skill/scripts/agent_compare.py) separates TCO/principal/equity and lifestyle costs | Lowest TCO is not a feasibility/comfort recommendation; case/scenario formats need reconciliation |
| Brochure/comfort | [liveability guidance](../../skills/property-advisor-skill/references/liveability.md) and native tools | Actual document extraction/mapping and family-fit quality require real artifact evaluation |
| Market/source access | [source guidance](../../skills/property-advisor-skill/references/research-and-evidence.md) and legacy fetchers | Official forms or table metadata do not prove queried matched data/current availability |
| Coverage | Four policy families in instructions; numeric engine has resale HDB, resale condo, new-launch condo, EC | New/resale EC, HDB new and landed require the correct route-specific contracts/capabilities |
| Tests | Property-advisor suite: **179 passed** on this unchanged source | Unit success does not validate the proposed expanded journeys |

## SP01 — Semantic requirements and temporal precision

**Question:** can a small bounded predicate model express recent completed OR
permitted future launches without rejecting future TOP or ignoring a move deadline?

**Observed prototype:** 16 synthetic temporal/logic examples passed. They include
recent/old completed homes, allowed/disallowed future branches, missing/unknown
status, inclusive cutoff, a partial-year interval crossing the age boundary,
age-at-search versus age-at-move-in, inconsistent future actual-TOP metadata,
occupancy ranges and all/any with unknowns.

The prototype's age cutoff uses a calendar anniversary and clamps a leap-day
cutoff to February28. This convention must be explicitly chosen in implementation;
the spike is not evidence that natural-language interpretation or all calendars
are solved. A future branch can satisfy the age policy while the overall timing
predicate fails. Empty/unknown groups do not become favorable defaults.

**Existing-code probe:** a synthetic TOP2010 property with a falsely declared age
pass returned no audit errors and `verified_fits:[c1]`. This demonstrates the
structural auditor's scope, not failed external-source authentication.

**Decision:** adopt bounded normalized predicates with explicit time/measurement
basis. Keep semantic and structural validation distinct. See FR02/FR03 and AC03–AC07.

## SP02 — Dated liquidity and funding strategy

**Question:** does an event-based allocation expose decisions an upfront-total
calculator misses, while enforcing CPF/cash restrictions consistently?

Seven synthetic ledger fixtures were executed with Decimal amounts, distinct
event dates and supplied eligibility/reserve assumptions:

| Fixture | Observed result |
|---|---|
| Later sale proceeds | **S$30k shortfall** at payment time despite enough eventual aggregate funds |
| Same proceeds before payment | No shortfall |
| Cash-only bill with large CPF balance | **S$10k shortfall**; CPF did not cover an ineligible payment |
| CPF cumulative usable cap0 | **S$0 CPF used** for both deposit and monthly payment in the prototype |
| Cash-first before a later cash-only bill | **S$15k later shortfall** |
| CPF-first with the same balances/obligations/reserves | No shortfall |
| CPF reserve equal to balance on a CPF-only payment | **S$20k shortfall** rather than silent reserve spending |

The source engine's existing `cpf_usable_pct="0"` probe still produced downpayment
CPF0 but first-instalment CPF **S$5,334.88**. Source: [allocation](../../skills/property-advisor-skill/scripts/agent_cashflow.py#L259-L322).
The prototype demonstrates a possible invariant-preserving allocation seam; it
does not fix that production inconsistency.

**Limits:** fixture eligibility/receipts were supplied, not verified from current
law/banks. The prototype is not a full loan/CPF/tax engine, strategy optimizer or
household forecast. Same-day ordering, uncertain receipts, per-owner constraints,
income shocks and real-contract schedules remain acceptance work.

**Decision:** implement one dated allocation/ledger contract, enforce all-stage
restrictions, compare strategies over the horizon, and report first shortfall.
See FR11–FR13 and AC19–AC25.

## SP03 — Property-specific milestones

**Existing-code observation:** supplying expected-TOP metadata2028 or2032 to the
same new-launch fixture produced TOP **1May2030**, move-in month **45**, because
the current API does not consume those fields. Generic42-/54-month TOP/CSC offsets
are [declared illustrative](../../skills/property-advisor-skill/references/policy-tables.json#L232-L251).

This is a missing property-specific input contract, not an arithmetic failure
under the documented scenario format. Resale duty timing is also attached to the
completion event in [the current model](../../skills/property-advisor-skill/scripts/agent_cashflow.py#L153-L205).
Applicable statutory/contractual due-date anchors require independent verification
before using outputs as payment instructions; no current legal deadline was
established by this code-review spike.

**Decision:** accept actual/estimated milestone schedules and date windows with
source/rule basis, record unsupported inputs, and recompute occupancy/drawdown/
interim housing when dates change. See FR03/FR12/FR13 and AC06/AC23.

## SP04 — Native PDF ingestion and version reconciliation

Two two-page **synthetic vector PDFs** were generated and read through the native
reader. Parsed text retained page numbers and these differences:

| Field | Revision A | Revision B |
|---|---|---|
| Expected TOP | 2029 | 2030 |
| Marketed type | Three bedrooms advertised | Two bedrooms plus study |
| Plan labels | Master, bedroom2, study | Same labels |
| Bathroom wording | Three headline; two full plus WC in plan text | Same distinction |
| Price matrix | 1,000sqft × S$2,000psf; **NOT ACTUAL PRICES** | Same disclaimer |
| Contractual possession / study's approved use | Not provided / not established | Same unknowns |

**Confirmed:** actual native PDF page/text extraction of both revisions. **Not
confirmed:** scanned/photo OCR, pixel/geometry interpretation, furniture fit,
approved-bedroom use, real developer documents or exact unit mapping. The generated
rectangles/dimensions are fictional. Do not equate parsed room labels with visual
or regulatory certification.

**Decision:** native-first document-to-dossier workflow is feasible enough to
prototype further. Preserve version/page scope, reconcile changed TOP/type and
keep matrix amounts as scenarios. Choose OCR/parsing technology only after real
packs expose a need. See FR08/FR09/FR16 and AC14–AC17.

## SP05 — Household function instead of area/headcount

A four-person fixture with two evidenced sleeping rooms gives different partial
results when the user requires separate child rooms versus explicitly permits
sharing: sleeping-group check fails in the first case and passes in the second.
**Overall comfort remains unknown** because desks, clearances, storage and other
needs were not fully assessed. This is a small semantic illustration, not a
validated comfort algorithm or a universal rule about four people.

**Decision:** represent functions/sharing groups and stated life-stage scenarios;
use real dimensions/evidence and independent review. See FR09 and AC16/AC17.

## SP06 — Comparable selection and unit basis

An eight-observation fictional same-project screen retained two three-bedroom,
compatible-strata-area transactions within its fixed window. It rejected bedroom,
date, asking-price and land-area mismatches; retained missing area as pending; and
kept a cross-project observation in a separate pool needing adjustments. The
selected metadata-only PSF median was **S$1,865.59**.

This is not a valuation or evidence for market appreciation: floor/condition and
actual source quality were not assessed. It shows why raw project/mixed-unit
medians and silently dropped unknowns are inappropriate inputs to precise advice.

**Decision:** require explicit selection/pending/exclusion rationale and compatible
measurement before arithmetic. Scenario rationale remains separate from growth
prediction. See FR10/FR14 and AC26/AC27/AC30.

## SP07 — Net exit identity

With supplied fictional inputs, **2m sale−1.2m debt−50k selling costs−380k CPF
refund=370k cash to seller**. Cash plus CPF refund plus selling costs reconciles
to800k pre-cost property equity. This proves only the accounting identity, not
actual refund/tax applicability or eligibility to sell. See FR12/FR14 and AC28.

## SP08 — Sibling-tool reuse is conditional

| Component inspected | Concrete observation | Reuse decision |
|---|---|---|
| [MRT rerouter](../../skills/mrt-rerouter-skill/scripts/mrt_rerouter.py#L19-L153) | Station table has **12** entries and omits Hillview/Mayflower/Buangkok/Potong Pasir. A synthetic next-train arrival5min with zero walk yielded **9min Bishan→Changi Airport**: formula adds arrival+4min transfer, no in-vehicle journey. | Do not use as a whole-journey/commute constraint provider. A validated network/journey adapter is needed; small utilities may be reusable. |
| [Smart commuter](../../skills/smart-commuter-skill/scripts/smart_commuter.py#L90-L171) | Driver/carpark focus; walk time comes from haversine/80m-min; nearby camera presence can drive a slow advisory. | Not actual pedestrian routing or evidence of long-run public-transport convenience. |
| [Rental yield](../../skills/rental-yield-calculator-skill/scripts/rental_yield.py#L83-L109) | Offline fixture with `median_rent_psf_pm:5` was read as **S$5 monthly**, yielding rounded gross0%; no unit-area conversion. Net deduction is fixed15%. | Do not reuse as unit-specific net yield or rental-value provider without a corrected source/unit/expense contract. |
| Shared geocoder/distance primitives | Existing utilities resolve coordinates and measure straight-line separation | Potential discovery utilities only; not gate-to-entrance routes, school eligibility or proven amenity operation. |

No live LTA/URA/OneMap call was made by these sibling probes; narrow mocks isolated
their formula contracts. All sibling code remains unchanged. Public OneMap API
documentation fetched in this session yielded no readable content. Earlier local
research recorded an anonymous walking-route403; it was not retried or bypassed.
Current authentication, licensing, routing coverage and practical providers remain
an integration spike, not an asserted working capability.

## SP09 — Confidence traversal and remaining baseline findings

The policy table marks a nested ABSD joint-rule item unverified while the current
[top-level traversal](../../skills/property-advisor-skill/scripts/agent_policy.py#L21-L39)
does not surface its parent in the unverified-items list. This is metadata behavior,
not a calculation of any real buyer's duty. Loan-count fallback, category/payment
route distinctions and current-rule/valuation gaps also remain as documented in
the existing source; no regulatory refresh was performed.

The existing appreciation calculator correctly labels default0/2/4% as assumptions
and accepts an explicit−2% override. Keep that capability. Add evidence-backed
scenario justification and net exit, not a claim that those defaults predict the
market. See FR04/FR13/FR14 and AC24/AC25/AC27.

## Observed, prototyped and unresolved

**Observed current code:** 179 tests pass; declaration-only semantic gap, fixed
timelines, zero-CPF allocation inconsistency, nested confidence traversal and
sibling reuse limitations reproduced/inspected.

**Prototyped:** bounded temporal logic, supplied-input funding ledger, metadata
comparable filtering, partial sleeping-group check and exit reconciliation.

**Native tool checked:** two two-page vector PDF text extractions.

**Still unresolved:** real provider access/terms, actual routes/time windows,
school methods, scanned/complex visual documents, dimensioned comfort validation,
real policy/contracts, complete matched inventory/caveats, migration integration
and all new end-to-end acceptance. None is converted to a favorable default.
