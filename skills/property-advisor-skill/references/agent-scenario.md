# Agent-mode scenario format

`--task plan|compare|advise` read a JSON scenario (`--scenario FILE`). Money and rates are strings
(or integers); floats are parsed as Decimal. Create the household's scenario outside
the installed skill using the fields below. Synthetic regression scenarios belong
to the source repository's development fixtures and are not runtime defaults.

```json
{
  "profile": "dink",                       // advise only: dink | first_home_couple | family_of_five
  "variant": "multigen",                   // optional, family_of_five only
  "town": "BISHAN",                        // optional label
  "start_date": "2026-11-01",              // option date
  "buyers": [
    {"age": 34, "residency": "sc",         // sc | spr | foreigner | entity
     "existing_properties": 0,             // ownership/duty facts, not the loan count
     "outstanding_loans": 0,               // explicit; missing -> zero-assumption illustration, conditional
     "monthly_income": "9000",             // gross, stable income
     "cpf_oa": "120000",                   // current OA balance
     "cpf_oa_monthly": "1500"}             // OA inflow per month (0 = all instalments in cash)
  ],
  "household": {"cash": "300000", "other_monthly_debts": "500"},
  "options": [                             // compare/advise: 2+; plan: use "option": {...}
    {
      "name": "4-room resale HDB",
      "category": "resale_hdb",            // resale_hdb | resale_condo | new_launch_condo | ec
      "price": "620000",
      "loan": {"type": "hdb", "tenure_years": 25},   // type: hdb (resale_hdb only) | bank; optional ltv, amount
      "remaining_lease_years": 75,         // flags CPF/loan pro-rating below age-95 coverage
      "first_timer": false,                // true: EHG counted if income within the ceiling
       "cpf_usable_pct": "1",               // cumulative fraction of valuation-limit amount, across fees/instalments too
      "annual_value": "15500",             // optional; property tax input (default: % of price)
      "monthly_maintenance": "90",         // optional overrides: monthly_insurance, renovation, furnishing, valuation (CPF valuation limit, default = price)
      "lifestyle_addons": [
        {"id": "virgin_active_long_termer", "count": 2},
        {"label": "Condo-club day passes", "monthly": "120"}
      ]
    }
  ],
  "assumptions": {                         // every key optional; recursively merged over default-assumptions.json
    "interest_rate": {"low": "0.02", "base": "0.03", "high": "0.04"},
    "appreciation": {"low": "0.00", "base": "0.02", "high": "0.04"},
    "opportunity_cost": {"cash": "0.03", "cpf": "0.025"},
    "cpf_pays_fees": false
  }
}
```

(Comments above are for reading; real JSON has none.)

## Output blocks

- `plan.timeline[]`: `stage`, `label`, `kind` (`down` | `stage` | `duty` | `fee` | `fit_out` | `milestone`),
  `date`, `month`, `cash`, `cpf`, `loan_drawn`.
- `plan.upfront`: modelled cash/CPF subtotal through completion or S&P-signing window, not a verified all-in minimum.
- `plan.monthly_schedule[]`: first 36 months from the option date; `monthly_schedule_full` covers 180.
- `plan.checks[]`: TDSR (bank loans) and/or MSR (HDB flats, ECs) at the stress rate;
  `ratio` is `null` when no (positive) income is supplied, and the check then fails.
- `plan.affordability_ceiling`: largest stress-tested loan the TDSR/MSR room allows, the price at
  the allowed LTV, `stress_rate`, `monthly_instalment_room`, `max_loan`, `max_price`, `ltv`.
- `plan.horizon{1,5,10,15}`: cumulative `cash`/`cpf`, `interest_paid`, `principal_repaid`, `loan_balance`,
  `property_value`, `equity_value`, `equity_built`, `cpf_used_for_property`, `cpf_accrued_interest`.
- `plan.scenarios.interest` and `.appreciation`: low/base/high, labelled `status: "assumption"`.
- `comparison.options[]`, `comparison.break_even[]`, `comparison.assumptions`, `comparison.warnings`.

Simplifications are listed in `plan.notes.simplifications`.

## Dated/conditional inputs

Read [assessment-inputs.md](assessment-inputs.md) for `payment_schedule`,
`milestones`, expected_top_date/move_in_deadline, EC purchase_route/resale MSR
applicability, market_value and different-valuation loan/cash-quote requirements.
Schedules are illustrations unless actual applicable dates/contracts are supplied.
Missing ownership/loan/funding facts and unconfirmed grant/proration details remain
conditional; no lender/HFE approval follows from a table lookup. Nested unverified
policy paths reach outputs. Rate numbers here are annual decimals, not percentages.

For user-selected cash/CPF strategies, chronological household balances, reserve
floors, recurring net income/living expenses and linked sale proceeds use
`--assess funding`; bind loan_plan/exit results through case input_refs if needed.
The legacy aggregate cash_check and lowest-cost label do not establish comfortable
affordability or a feasible household recommendation. Old CLI errors may still be
exit0 with an error object; the focused assessment CLI uses exit2 for invalid input.
