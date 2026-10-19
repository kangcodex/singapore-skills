# Agent-mode scenario format

`--task plan|compare|advise` read a JSON scenario (`--scenario FILE`). Money and rates are strings
(or integers); floats are parsed as Decimal. Runnable examples:
[`examples/dink-couple.json`](examples/dink-couple.json),
[`examples/first-home-couple.json`](examples/first-home-couple.json),
[`examples/family-of-five.json`](examples/family-of-five.json).

```json
{
  "profile": "dink",                       // advise only: dink | first_home_couple | family_of_five
  "variant": "multigen",                   // optional, family_of_five only
  "town": "BISHAN",                        // optional label
  "start_date": "2026-11-01",              // option date
  "buyers": [
    {"age": 34, "residency": "sc",         // sc | spr | foreigner | entity
     "existing_properties": 0,             // drives ABSD and the LTV tier
     "outstanding_loans": 0,               // optional, defaults to existing_properties
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
      "cpf_usable_pct": "1",               // override when the lease limits CPF usage
      "annual_value": "15500",             // optional; property tax input (default: % of price)
      "monthly_maintenance": "90",         // optional overrides: monthly_insurance, renovation, furnishing, valuation (CPF valuation limit, default = price)
      "lifestyle_addons": [
        {"id": "virgin_active_long_termer", "count": 2},
        {"label": "Condo-club day passes", "monthly": "120"}
      ]
    }
  ],
  "assumptions": {                         // every key optional; shallow-merged over default-assumptions.json
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
- `plan.upfront`: minimum cash and CPF through completion (resale) or S&P signing (new launch/EC).
- `plan.monthly_schedule[]`: first 36 months from the option date; `monthly_schedule_full` covers 180.
- `plan.checks[]`: TDSR (bank loans) and/or MSR (HDB flats, ECs) at the stress rate.
- `plan.horizon{1,5,10,15}`: cumulative `cash`/`cpf`, `interest_paid`, `principal_repaid`, `loan_balance`,
  `property_value`, `equity_value`, `equity_built`, `cpf_used_for_property`, `cpf_accrued_interest`.
- `plan.scenarios.interest` and `.appreciation`: low/base/high, labelled `status: "assumption"`.
- `comparison.options[]`, `comparison.break_even[]`, `comparison.assumptions`, `comparison.warnings`.

Simplifications are listed in `plan.notes.simplifications`.
