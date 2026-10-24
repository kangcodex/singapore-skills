# Question-led Property Advisor — proposed next iteration

Version 1.0 design package | 24 October 2026

**Status: reviewed proposal, not newly implemented skill behavior.** This package
ships the product idea, contracts, spike findings, acceptance plan and roadmap.
The existing executable skill remains at its current behavior. Implementation
requires its own approved change and verification.

## Product in one paragraph

Help Singapore households answer the next useful property question—from “is this
close to MRT?” to a complete housing decision—using adaptable requirements,
category-specific rules, actual household functions, dated evidence and explicit
financial scenarios. Cover HDB new/resale, EC routes, private flats/condos and
landed. The best action can be investigate, view, negotiate conditionally, buy,
rent, wait, stay or reject all. Success is a better-supported household decision.

## Read this package

| Document | Purpose |
|---|---|
| [Product specification](product-spec.md) | Outcomes, scope, 18 functional requirements, answer modes and delivery boundaries |
| [70 business questions](business-questions.md) | Seven user journeys; original A01–G08 identifiers retained, with two added questions per journey |
| [Decision contracts](decision-contracts.md) | Age/future TOP, transport, brochure, family comfort, funding, comparables, scenarios and updates |
| [Capability and spike review](capability-and-spikes.md) | What exists, what was tested, reuse decisions, limitations and unresolved blockers |
| [Acceptance plan](acceptance-plan.json) | 35 planned cases with explicit oracles and requirement/question traceability; not an executed benchmark |
| [Implementation roadmap](roadmap.md) | Thin slices, dependencies, exit checks, migration decisions and launch gates |

## Main design decisions

1. Use **one question-led case**, with focused answers and selective deepening.
   Small location questions do not require financial intake.
2. Treat **actual age, completion status, expected TOP, contractual possession and
   practical occupancy** independently. Recent completed OR permitted future
   launch is a legitimate requirement; the move deadline remains separate.
3. Assess **household functions**, not headcount or headline sqft alone.
4. Produce **dated funding balances**, not just a purchase subtotal or maximum loan.
5. Connect comparable evidence to **explicit scenarios and net exit outcomes**.
   A calibrated appreciation forecast is outside this iteration.
6. Use native tools and existing utilities where validated. A helper's name or
   metadata is not proof it provides accurate routes, rents or rule applicability.
7. Gate recommendations on hard constraints and evidence scope; preserve useful
   partial answers and never impute favorable values for unknowns.

## Evidence behind the proposal

At reviewed source revision `afcc654`, the property-advisor suite passed **179
tests**. Additional ignored-workspace experiments exercised 16 temporal/logic
cases, seven funding scenarios, a net-exit identity, an eight-observation comparable
screen, a sleeping-group example, native parsing of two two-page synthetic PDFs,
and offline sibling-tool probes. Results and limits are curated in the spike review.

These experiments demonstrate feasibility and expose gaps. They do not implement
the proposed behavior, validate real regulatory outcomes, prove scanned-PDF visual
extraction, establish market-wide inventory or complete the acceptance plan.

## Delivery and data handling

Version-control this curated specification and synthetic acceptance descriptions.
Keep raw prototypes, probe outputs, PDFs, transcripts, personal cases, source
snapshots and generated reports under ignored `reports/` or the skill's existing
ignored case/workspace paths. No personal household case or commercial brochure
is required to understand this package. The proposal does not authorize outreach,
transactions, paid subscriptions or unattended monitoring.
