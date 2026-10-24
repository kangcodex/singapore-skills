# Decision and evidence contracts

**Proposed behavior, not a replacement for the current schema-3/agent APIs.** The
field sketches below describe business semantics. Final serialization/migration
must be approved before implementation. FR identifiers refer to the
[product specification](product-spec.md).

## 1. Question plan and minimum context — FR01, FR13

A question plan identifies intents/subquestions, resolved entities, requested
depth, minimum inputs, relevant requirement IDs, tools/providers, evidence scope,
capability limits and expected answer shape. Compose mixed questions; answer
known subquestions while asking only missing facts that change another result.

Examples:

- MRT proximity needs location/entrance/mode, not income or CPF.
- Exact affordability needs buyer/funding facts; a known-cost subtotal can still
  be returned while eligibility and excluded items remain unknown.
- A brochure can be extracted without household facts; a comfort verdict requires
  those facts and the appropriate plan.

Track supplied, derived, defaulted, missing and materially unmapped inputs. If a
request says a particular TOP/deadline/funding strategy, a calculation that cannot
consume it must say so rather than silently ignoring it.

## 2. Requirement semantics — FR02, FR03

Each requirement retains original wording, normalized kind/operator/value,
unit/basis, priority, state/provenance, reference date/applicability, approved
exception, evidence dependencies and evaluation reason.

Bounded kinds: age/status/occupancy; money/budget basis; category/eligibility;
bedroom/function; area convention; walk/travel limits; explicit all/any/conditional
groups. This is not an arbitrary-code rules language.

### Three-valued results

`pass`, `fail`, `unknown` are evaluated from facts. `not_applicable` is a separate,
justified assessment state; it is not a favorable default. For nonempty groups:

| Combination | Rule |
|---|---|
| all | Any fail→fail; otherwise any unknown→unknown; otherwise pass |
| any | Any pass→pass; otherwise any unknown→unknown; otherwise fail |

A user may approve a soft exception or change a hard requirement in a new brief
version. Neither occurs just because another feature scores well. Preserve the
original rule and provenance of the changed scenario.

### Age/future-TOP example

Interpret “maximum five years old, future launches allowed” as:

```text
any(
  all(status=completed, actual_age_at(reference_date) <= 5 years),
  all(status=uncompleted, allow_uncompleted=true)
)
```

That result addresses the age/status policy only. Occupancy deadline, availability,
household fit, financing and evidence may still fail or remain unknown. Do not
compute negative age from a future TOP.

Actual TOP, expected TOP, contractual possession, keys, renovation and practical
occupancy have separate fields and source scopes. Phased/block-level dates cannot
be replaced by an unrelated project headline. Preserve partial dates as intervals;
if they straddle a cutoff, the result is unknown. An inclusive year window such as
2021–2026 is a different predicate from a rolling five-year age limit. Specify
inclusive/exclusive boundaries and leap-day convention explicitly.

Age-at-search, age-at-contract and age-at-move-in may differ. Practical occupancy
can be a range: wholly before a hard deadline→pass, wholly after→fail, overlapping
or insufficiently known→unknown. TOP alone is not practical move-in.

### Preferences and measurements

“Closer MRT preferred” is not an automatic600m cutoff. If a hard limit exists,
evaluate its actual mode/endpoints and time/distance basis. A published strata
size does not satisfy a net-internal-area limit. Amounts/rates/areas need explicit
currency and units; do not mix annual percent3 with annual decimal0.03 silently.

## 3. Property, opportunity and assessment vectors — FR04, FR05, FR15

Keep identity, category, physical form, title/tenure, route, policy regime,
completion state and opportunity state independent. A project may have several
layouts/listings; an application is not an allocated/selectable unit. Reliable
unit IDs support deduplication; uncertain matches remain flagged.

Do not compress the decision into one verified-fit label. Retain at least:
requirement fit; attainability/availability; policy feasibility; affordability;
cost completeness; layout/unit-mapping confidence; price/value confidence; source
coverage. Overall actions include research/view/conditional decision/wait/reject.

No final recommendation can compensate a hard fail. Unknown material constraints
prevent a confirmed fit but do not require discarding a promising research lead.
Current listing/quote presence alone does not prove current availability.

## 4. Provider and route evidence — FR06, FR07, FR13

For a transport observation preserve provider/request time, travel window,
origin/destination and entrance identity, network version/horizon, modes, segments,
walk/wait/ride/transfer durations, accessibility assumptions, distance basis,
geometry where available, operating status and confidence/limitations.

Capability declarations should distinguish geocoding, straight-line distance,
pedestrian routing, whole public-transport journey, time-window support, current
service/reliability and future-network scenarios. Reuse only the capabilities
actually validated. Next-train arrival time cannot stand in for in-vehicle time.

When only a centroid/radius estimate is available, label it. When a route API is
blocked, state the missing route and preserve verified source facts; do not infer
that transport is absent. Do not switch to credential/unrestricted access to evade
denial. Current and future services stay separate; expected completion is not an
operating date. Count walking to the particular station entrance, not an arbitrary
map marker, when evaluating a hard pedestrian limit.

Multiple destinations require per-person/day/time/frequency constraints. A hard
commute limit for one member cannot be averaged away. Use official applicable
school methods/cohorts for eligibility and actual service evidence for amenities;
neither a radius nor a map category proves admission or current operation.

## 5. Document-to-dossier contract — FR08, FR09, FR16

Retain document identity/version/content fingerprint, retrieval/supply date,
publisher/source and access/reuse terms. Each claim links to page/figure/region,
extraction method/status, scope, confidence and contradictions/supersession.

Pipeline: retrieve/accept→identify versions→extract text→inspect relevant visuals
where possible→normalize facts/prices/units→map layout/property/unit→reconcile
conflicts→assess household implications→update dependent results.

Useful outputs include project particulars, layout variants and identifiers,
dimensions/area conventions, site orientation, room access, price disclaimer/type,
occupancy particulars, conflicts and targeted evidence requests. Text extraction
and visual review are different capabilities. Cropped/unclear/scanned content
remains explicit; never infer dimensions, approved use, removable walls or views.

The synthetic PDF spike confirmed page/text extraction, not general OCR, furniture
packing, actual visual accuracy or regulatory approval. Real native/scanned/watermarked
packs and independent review remain implementation gates.

## 6. Household comfort contract — FR09

Represent occupants/roles, agreed sleeping/sharing groups, work/privacy, furniture,
storage/laundry/cooking, bathroom/service, accessibility and explicitly requested
future scenarios. Do not assume sharing, helpers, children or future care needs.

Assess functions against matching plan facts and dimensions. Results can be works
for the assessed function, works with conditions, fails, or unknown. Overall
comfort also requires circulation, desks/wardrobes, service spaces and the user's
trade-offs; sleeping-group count alone is insufficient. A study is not a bedroom
without relevant access/enclosure/ventilation/approved-use evidence. A WC is not
a full bathroom. Keep unknown furniture clearances and net area visible.

## 7. Cost and funding event contract — FR11, FR12, FR13

Each event needs identity, date or window and date basis/source, amount/currency,
kind, applicable rule/contract version, permitted funders, approval/receipt status,
caps/reserves, dependencies and whether it is assumed. Distinguish cost, credited
deposit, principal/equity, loan draw, grant, refund and transfer.

Funding state includes actual available cash/CPF, per-owner limits when relevant,
approved loan draws, dated net income/CPF receipts, living expenses, existing
obligations, reserves and linked sale/transition events. Stable gross income for
underwriting is not disposable cash available to pay a bill.

Strategies may be cash-first, CPF-first or reserve-preserving, within actual fund
eligibility and caps. Apply the same restrictions to deposits, later stages, fees
and monthly obligations. Zero permitted CPF use must remain zero throughout.
Do not require a user to misstate their CPF balance to express a funding preference.

Required invariants:

- Fund allocations plus explicit unfunded amount reconcile to every obligation.
- No later/unconfirmed receipt finances an earlier payment.
- Caps, fund-specific eligibility and reserves are enforced across events.
- Report first shortfall, peak need and the reason; a later positive total does
  not erase a historical funding failure.
- Same-day event order needs evidence or an explicit uncertainty scenario.
- Compare strategies over the horizon; locally feasible cash-first allocation
  may create a later mandatory-cash shortfall.
- No double-counted deposits, grants, principal, loan proceeds or CPF refunds.

Milestones come from the relevant property/contract and applicable legal date
rules. Generic construction offsets remain labelled illustrations. Unknown fees,
valuations, grants or policy applicability prevent an all-in/confirmed affordability
claim. A complete ledger is not lender approval.

## 8. Comparables, scenarios and exit — FR10, FR14, FR15

Comparable observations retain raw data/source, price kind/date, identity,
bedrooms/function, compatible area basis, tenure/age, floor/condition/sale type,
selection/pending/exclusion reason and any justified adjustments. Same-project and
cross-project pools stay distinct. Unknown area cannot become zero or a pass;
missing observations are not absence of transactions. Duplicates and syndicated
copies do not increase independent sample confidence.

Separate historical evidence, current asking/quotation, entry judgement and
future assumptions. Calendar/sample/mix checks apply before trends. A two-record
metadata match can guide research but does not establish precise fair value.

An appreciation thesis records catalyst/mechanism, actual status/timing, demand/
supply/lease/condition evidence, competing explanation, entry premium, horizon,
falsifying evidence and downside/flat/base/upside assumptions. No probabilities or
point forecasts without a separately validated model. Construction-time holding,
interest and lack of rent must not be omitted from new-launch scenarios.

Net exit distinguishes sale value, debt redemption, selling costs/taxes, required
CPF principal/accrued refund and cash to seller. Refund rules/shortfalls depend on
applicable facts, not arbitrary clamping. Example with supplied hypothetical
amounts: 2m sale−1.2m debt−50k costs−380k CPF refund=370k cash; 800k property equity
is not 800k spendable cash. Define the break-even basis and avoid counting principal
or refunded savings as a second economic cost.

## 9. Revision and conclusion gates — FR13, FR15–FR18

Retain case, brief, source, assessment, scenario and recommendation versions plus
dependency IDs. Changes in deadlines, household functions, location, quote, rules,
plan mapping or research date invalidate the affected results. Preserve user
facts unless explicitly corrected; do not silently replace them with inference.

Recompute and explain old→new→reason. Keep consumer report and structured record
consistent. An audit distinguishes structural validity, semantic constraint checks,
calculation reconciliation, evidence applicability and human/source validation;
one passed layer does not imply the others. Expired availability or a blocked
source caps only the conclusions that depend on it.
