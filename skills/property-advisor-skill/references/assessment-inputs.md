# Runnable assessment inputs

Python 3.11+, stdlib only. Paths below are relative to the installed skill folder:

```bash
python3 scripts/advisor_cli.py --assess KIND --input FILE.json --format json
python3 scripts/advisor_cli.py --case assets/question-led-case.json --format json
```

Default output is readable Markdown; JSON is explicit. The existing
`property_advisor.py` also routes `--assess`, `--case` and `--calculate` (including
`--flag=value` syntax). Invalid/malformed inputs exit2; valid negative/conditional
assessments are not process errors. No helper performs a live search, route, OCR,
bank approval or active notification. Obtain native/source evidence first.

Top-level calculation fields are checked: unknown names are errors rather than
silently ignored. `example_notice`, `metadata` and `notes` are informational.
Fixtures under `assets/examples/` are synthetic and independently labelled.

## Question plan

`question`: `kind` or `kinds`, `known_inputs`, optional `request`. Intents:
`proximity`, `journey`, `amenities`, `documents`, `comfort`, `funding`,
`funding_options`, `value`, `scenarios`, `search`, `compare`, `eligibility`,
`update`, `watch`. The native model supplies the intent. `known_inputs.location`
may be a resolved property/address; `property`/`address` aliases are accepted.
Missing material inputs and precision inputs are returned without claiming work
was performed. See `assets/examples/question.json`.

## Requirements and facts

`requirements`: `as_of` exact ISO date, `requirements` array, `facts` object.
A requirement has id, priority `hard|strong|flexible`, knowledge state and `condition`.
An unconfirmed meaning or missing normalization yields unknown.

Facts use `{ "state":"known", "value":..., "unit":"...", "basis":"...",
"evidence_ids":["e1"] }`. Unknown/conflicting facts are not known. Keep null
unknown distinct from explicit not-applicable. This input does not authenticate
source claims; confidence and eligibility/availability/affordability are separate.

| Condition kind | Fields / semantics |
|---|---|
| `age` | `max_years`, `include_uncompleted` boolean, optional exact `reference_date`; uses `completion_status` and `actual_top` facts, never negative future age |
| `ready_by` | exact deadline `date`, optional fact `field` (default `occupancy_date`); expected TOP is not substituted |
| `date_window` | `field`, inclusive `earliest`/`latest`; explicitly different from rolling age |
| `number` | `field`, `op:min|max|eq`, decimal `value`, `unit`, optional required `basis` |
| `one_of` | `field`, explicit allowed `values` strings |
| `all` / `any` | `conditions` array; three-valued semantics, empty/all-exempt group unknown |
| `when` | `if` and `then` conditions; a known false applicability predicate yields not-applicable |
| `preference` | `field`, `direction`; no invented hard threshold; cannot establish a hard pass |

Dates accept ISO day, month, year or `{earliest,latest}`; reference/deadline dates
are exact. Partial intervals crossing a boundary stay unknown. Completed status
constrains a partial current-year date to the research date; an explicit future
actual TOP conflicts even when the age reference is future. Leap-day age cutoffs
clamp to February28. Supported conversions: sqm/sqft, km/m, hours/min; incompatible
area or route bases never convert silently. Numeric facts can hold `{min,max}`;
missing bounds and starting prices cannot prove a maximum-price fit.

## Location and amenities

`location`: `as_of`, resolved `origin_id`, `routes`, `limits`.
Routes identify id/origin/destination, source/retrieved_at, horizon `current|future`,
service status and measurement. For walking: `measurement:routed_walk`,
`endpoint_scope:entrance_to_entrance`, `distance_m`. For public-transport duration:
`measurement:whole_journey`, `endpoint_scope:door_to_destination`, `minutes`
(point or min/max). Arrival-only, straight-line and station-only data do not
satisfy those limits. Source `access_status`/`valid_until` can limit use.

Each limit has destination_id and max_walk_m, max_walk_minutes and/or max_minutes.
Walking time uses a supplied routed-walk duration, never an assumed meters/speed
conversion. Limits also support optional horizon
(current by default), allowed_primary_lines, allowed_modes and travel_window.
Mode/time-window mismatches remain unknown; the native workflow must populate
those constraints when the user specifies them. Results are per destination;
unknowns/failures are not averaged away. A failed supplied route is not proof
there is no faster alternative. Counts/frequencies/windows/accessibility remain
source/native-review context, not verified merely by the helper.

`amenities`: `as_of`, optional school `cohort`, `items`. Items carry id/kind,
operating_status, source/retrieved_at and observation details. A school official
distance band needs matching cohort, address_basis, official_distance_method,
`method_verified:true`, `distance_basis:official_method` and supplied distance_m.
It is a supplied-method distance result, never admission. Closure remains closure.

## Documents and household comfort

`documents`: documents and claims arrays, optional assessment context. Documents
need id/source/pages, version/extraction_status, optional visual_reviewed and
explicit supersedes prior IDs. Claims need unique id/document_id/page/key/scope/
value; evidence requiring visual review must say `requires_visual:true`. Page
bounds and revision cycles are checked. Unresolved differing values conflict;
superseded versions remain recorded. A document price disclaimer or
price_matrix_is_scenario prevents quotation promotion. Metadata/file paths are
never followed by this helper. Current identified-quote support also needs as_of,
matching candidate_id where requested, quoted_at and either an unexpired valid_until
or same-day quote. Layout/candidate/stack IDs keep distinct variants separate;
one assessment is one resolved property dossier. See `assets/examples/documents.json`.

`comfort`: household, layout, optional explicit future_scenarios. Household needs
sleeping_groups (agreed grouping, not headcount), optional min_full_bathrooms and
required_features. Layout rooms need unique IDs, kind, common_access/enclosed/
window/approved_bedroom knowledge and source. A study needs actual supporting use
evidence; master-access is not independent common access. `rooms_complete:true`
is required before absence in the inventory establishes too few rooms.

Bathrooms distinguish `kind:full` from `wc` with sources; missing inventory is
unknown. `bathrooms_complete:true` is needed for a deficiency conclusion. Furniture
fit requires actual dimensions_m and source-backed verification, not drawn beds;
functional_review_complete is not a substitute for missing facts. Features use
known/value/source records. Future scenarios have id, household and optional hard
status. Net internal area must be supplied with its real basis; never inferred by
an efficiency percentage. See `assets/examples/comfort.json`.

## Funding, loan scenarios and exit

`funding`: SGD funds/events, strategy `cash_first|cpf_first|preserve_cash|preserve_cpf`,
optional compare_strategies, recurring, allow_assumed_receipts and monthly_cash_limit.
Funds have unique id/kind `cash|cpf|loan`, balance, reserve and explicit usable_cap
where required. Unknown CPF cap prevents CPF allocation and keeps results conditional.
Already-available approved loan funds are ordered before the selected cash/CPF mix;
eligible fund IDs are explicit on every obligation. This is not underwriting.

Payments need id/date/kind/amount/allowed_funds and optional minimum_cash. Receipts
need id/date/kind/amount/fund/status. Only supplied-confirmed receipts are credited
by default. Explicitly opting into assumed receipts is scenario-only and retains
conditional status; unconfirmed future money is not automatically spendable.
Same-day events require unique integer sequence values. Every payment reconciles
allocations plus unfunded amount; caps/reserves apply at every stage/month.
Later receipts do not erase earlier shortfalls. Output includes first_shortfall,
total_unfunded, balances, funds_used and limitations—not lender approval or an
optimized bridge loan. See `assets/examples/funding.json`.

Monthly `recurring` rules have id/start/months (1–600), kind and event fields;
optional changes use unique one-based from_month and changed amount/status.
Calendar days clamp month ends; payroll/business-day certainty is not inferred.
Use dated net income/CPF and living-cost changes, not gross income as free cash.
Recurring cash need and an explicitly supplied monthly_cash_limit are reported
separately from whether funds can pay an obligation.

`loan_plan` and `cost_comparison` use the documented
[agent scenario](agent-scenario.md) format. They keep dated/default/unverified
policy assumptions and limited category models; new-HDB/landed exact obligations
can use the generic event ledger instead of a false condo mapping. Missing loan
counts are zero-assumption illustrations, not inferred ownership counts or approval.
These focused wrappers take its financial subset: start_date/buyers/household,
option or options, assumptions and optional town. Profile/variant belong to the
legacy `--mode agent --task advise` interface, not the focused calculation input.

For the loan planner, `option.payment_schedule` can replace the generic progressive
table: unique id/date and pct or amount, explicit cash_only where relevant, required
booking/sp_signing/top/csc stages, chronological dates and exact reconciliation to
purchase price. `option.milestones` can supply exercise/completion, stage IDs,
stamp_duty and move_in dates. `expected_top_date` is consumed as a TOP override;
if it contradicts the illustrative stage chronology, supply actual payment_schedule
rather than accepting a silently unchanged date. `move_in_deadline` yields a separate
timing_check. Defaults are illustrative, not verified statutory due dates.

`option.purchase_route:resale` prevents an EC being treated as uncompleted developer
sale. Its `ec_msr_applicable` must reflect the sourced actual status; unknown
applicability remains conditional. If price differs from `valuation`, provide quoted
`loan.amount` and `loan.minimum_cash` or use the generic funding ledger with verified
obligations. `market_value` is separate: duties use the higher supplied price/market
value; omitting it leaves an explicit price-basis assumption, not a valuation.
`cpf_usable_pct` is a cumulative fraction of the property valuation-limit amount,
not a fraction of each month's wallet; it applies to fees and instalments as well
as the downpayment. Use fund reserves/strategy rather than this policy override to
express cash/CPF preferences. Loan-plan scenarios are not actual grant/HFE approval.

Rate units differ by explicit interface: `--calculate mortgage --annual-rate 3`
means3percent; the agent/scenario JSON uses annual decimal `0.03`. Never mix them.

`exit`: supplied sale_price, loan_redemption, selling_costs,
cpf_principal_refund and cpf_accrued_refund. Missing refund is unknown, not zero.
Negative residual cash remains conditional on actual shortfall/refund rules; no
silent clamping. Equity, CPF refund and spendable sale cash are different.

## Comparables, scenarios, search and watch

`comparables`: as_of, subject (property_id/bedrooms/area_sqft/area_basis), observations;
optional window_start and area_tolerance_pct (default10% declared in output).
Observations need id/kind transaction, identity/room/area/basis/price/date and source/
retrieved_at. Missing facts are pending; incompatible/old/asking records excluded;
cross-project controls kept separate. Supplied transaction_key deduplicates known
records. Selected unadjusted median/premium and sample-labelled completed-quarter
trend are cross-checks; fair_value remains null until actual judgement is supported.

`scenarios`: entry_price, years, scenarios with id/annual_rate_decimal/rationale/
evidence_ids. Explicit decline/flat/base/upside values are assumptions, not forecasts.
Optional nonrecoverable_costs/fixed_selling_costs/selling_cost_rate_decimal produce
break-even on that stated cost basis; do not double-count principal or refunds.
Reconcile net exit separately. See `assets/examples/scenarios.json`.

`search`: as_of/coverage/requirements/candidates, optional evidence ledger.
Candidates carry facts and opportunity state. Confirmed unit_key deduplicates;
listing_fingerprint only flags suspected duplicates. Failures/withdrawn homes are
rejected, unknowns remain conditional. Verified-available fits require actual
source-support metadata, policy and availability evidence, not a lone reviewed flag.
No live inventory query or silent relaxation occurs in this helper.

`watch`: explicit_request/targets/triggers/expiry, optional frequency/channel.
It returns an inactive specification. Native scheduling requires real execution
evidence and explicit authority; a JSON flag cannot create a job.

## Bound case execution and revision

Add `analysis_requests` to schema3 cases:

```json
{"id":"screen","kind":"requirements","input_refs":{
  "as_of":"/research_date","requirements":"/buyer_brief/requirements",
  "facts":"/candidate_facts/home"}}
```

Case property/candidate facts reconcile without silent conflicting overrides.
Normalized requirements automatically refresh checks and computed rejections.
`candidate_facts` is keyed by stable candidate ID. Analysis input_refs resolve
case JSON Pointers only, never files/URLs/expressions. Earlier assessment results
may feed later requests; missing/cyclic/order-invalid references fail rather than
reuse old outputs. Nested target keys such as `/events/0/amount` update an existing
input slot from a current pointer (for example net exit proceeds). Base targets
are bound before nested overrides, independently of mapping insertion order.

Results have engine/input fingerprints and scope. Constant `input` is a snapshot;
unchanged snapshot inputs need manual refresh when the case changes. References
recompute on every run. `--previous-case` supplies changed paths/assessment summaries,
retains prior files, and retires unchanged old summaries/recommendations after
material changes. Supply increasing version/supersedes/history; confirmed requirement
changes/removals require history source_kind:user, reason and changed_requirement_ids.
Changed wording with an unchanged predicate requires normalization_reconfirmed or
a corrected predicate. First-time normalization of unchanged wording is additive.
