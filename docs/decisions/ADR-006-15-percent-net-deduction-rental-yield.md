# ADR-006: 15% net deduction in `rental-yield-calculator-skill`

## Status
Accepted

## Date
2026-06-22

## Context

`rental-yield-calculator-skill` returns both a **gross yield** and a
**net yield**:

```
gross_yield_pct = (annual_rent_estimate / asking) × 100
net_yield_pct   = gross_yield_pct × (1 - 0.15)
```

The 15% deduction is a heuristic for the costs a private condo landlord
incurs **after** receiving the rent. It bundles:

| Cost                                          | Share  |
|-----------------------------------------------|--------|
| Singapore income tax on rental income         | ~10%   |
| Property tax (10% of annual value)            | ~10%   |
| Fire insurance                                | ~5%    |
| Condo management fees (common areas)          | varies |

For a typical private condo, this lands at roughly 15% combined. A
buyer-to-rent investor comparing two condos wants a single number
that's "what I actually keep", not the headline gross figure.

## Decision

Use a **flat 15% deduction** as a built-in assumption. Not a
configurable parameter. The skill reports both gross and net; the net
is `gross × 0.85`.

The 15% is documented in:
- `SKILL.md` ("The 15% net deduction" section)
- `references/ura-rentals.md`
- The `NET_DEDUCTION` constant at the top of `rental_yield.py` with a
  one-line comment

## Alternatives Considered

### Make the deduction a CLI flag (`--net-rate 0.15`)
- Pros: User can adjust.
- Cons: Most users don't know the right number; the skill becomes a
  calculator rather than an advisor. The 15% is a sane default that
  the user can override mentally for their situation.
- Rejected: simplicity wins for v1.

### Compute exact tax per IRAS schedule
- Pros: Accurate for individuals.
- Cons: IRAS tax brackets are progressive (0%, 2%, 3.5%, 7%, 11.5%,
  15%, 18%, 19%, 19.5%, 20%, 22%) on **all** rental income, not
  marginal. A landlord with one condo at $5,000/month pays 22% on
  most of it. A landlord with 3 condos pays 22% on all of it. The
  conditional logic is non-trivial and would need a separate ADR
  for tax computation.
- Rejected: out of scope for v1.

### Skip the net figure, only show gross
- Pros: Avoids the false-precision problem.
- Cons: Loses the most-useful number ("what do I actually keep?").
- Rejected.

## Consequences

- **Pos:** One number the user can act on. The net is what hits
  their bank account.
- **Pos:** The 15% is conservative for a single-property landlord
  with no mortgage, optimistic for a multi-property landlord (who
  faces the 22% top bracket). Documented in the SKILL.md pitfalls.
- **Pos:** The `NET_DEDUCTION` constant is at the top of the file
  with a comment, so a future maintainer can re-derive the heuristic
  or replace it.
- **Neg:** The number is a heuristic, not a precise calculation. A
  user with a non-standard situation (e.g. loan interest deductible
  in some structures, property held in a trust) will get a
  misleading number. Documented in the SKILL.md pitfalls.
- **Neg:** The net figure rounds to 1 dp (per the `round(x, 2)` in
  the calculation). For a $1.5M condo at 4% gross, the net is 3.4% —
  fine for a "should I buy?" decision, not fine for tax filing.

## Follow-on

- The SKILL.md explicitly recommends the user "adjust manually" for
  multi-property situations.
- If IRAS ever changes the rental income tax treatment, this ADR
  should be updated and `NET_DEDUCTION` should be re-derived.
