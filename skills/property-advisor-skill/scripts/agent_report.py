"""Plain-language, property-agent-style summaries for agent mode.

Pure formatting: every function takes the dicts produced by agent_profiles,
agent_cashflow and agent_compare and returns text. No policy numbers are computed here.
"""
from decimal import Decimal

DISCLAIMER = ("This is guidance, not financial or legal advice. Confirm every figure with HDB, "
              "your bank and a lawyer before you commit.")


def _m(x) -> str:
    return f"${Decimal(str(x)):,.0f}"


def profile_summary(p: dict) -> str:
    lines = [f"Buyer profile: {p['label']}", "", "What to prioritise:"]
    lines += [f"  - {x}" for x in p["priorities"]]
    lines += ["", "Shortlist (best fit first):"]
    for s in p["shortlist"]:
        seg = ""
        if s["segments"]:
            seg = " [" + ", ".join(x["segment"].upper() for x in s["segments"]) + "]"
        lines.append(f"  {s['rank']}. {s['label']}{seg}: {s['why']}")
        lines.append(f"     Watch out: {s['watch_out']}")
    loc = p["location"]
    lines += ["", "Location checks:", f"  - Transport: {loc['mrt']}", f"  - Jobs: {loc['jobs']}",
              f"  - Amenities: {loc['amenities']}"]
    if "schools" in loc:
        sch = loc["schools"]
        lines.append(f"  - Schools: {sch['distance_bands']['within_1km']}; {sch['distance_bands']['between_1_and_2km']} "
                     f"(unverified: {sch['unverified_reason']})")
    lines.append("  - Risk checks: " + ", ".join(loc["risk_checks"]))
    lines += ["", "Key questions to ask:"] + [f"  - {q}" for q in p["key_questions"]]
    lines += ["", "Red flags:"] + [f"  - {r}" for r in p["red_flags"]]
    lines += ["", "Due diligence (all categories):"]
    lines += [f"  - {d['item']}: {d['check']}" for d in p["due_diligence"]["property"] + p["due_diligence"]["financial"]]
    for cat, items in p["due_diligence"]["by_category"].items():
        lines.append(f"  {cat.replace('_', ' ').title()}:")
        lines += [f"    - {d['item']}: {d['check']}" for d in items]
    lines += ["", "Trade-offs between categories:"]
    for cat, notes in p["category_notes"].items():
        lines.append(f"  {cat.replace('_', ' ').title()}:")
        lines += [f"    - {n}" for n in notes]
    lines += ["", "Sibling skills to run for this area:"] + [f"  - {r['skill']}: {r['use']}" for r in p["related_skills"]]
    return "\n".join(lines)


def plan_summary(plan: dict) -> str:
    o, loan = plan["option"], plan["loan"]
    lines = [f"{o['name']} ({o['category'].replace('_', ' ')}) at {_m(o['price'])}: {plan['verdict'].upper()}",
             f"Loan {_m(loan['amount'])} ({loan['type'].upper()}, {loan['tenure_years']} years, LTV {Decimal(loan['ltv']) * 100:.0f}%), "
             f"instalment {_m(loan['monthly_instalment'])}/month at {Decimal(loan['rate']) * 100:.2f}%.",
             "", "Cash and CPF at each stage:"]
    for e in plan["timeline"]:
        if e["kind"] == "milestone":
            lines.append(f"  {e['date']}  {e['label']}")
        else:
            lines.append(f"  {e['date']}  {e['label']}: cash {_m(e['cash'])}, CPF {_m(e['cpf'])}"
                         + (f", loan drawn {_m(e['loan_drawn'])}" if Decimal(e["loan_drawn"]) > 0 else ""))
    up = plan["upfront"]
    lines += ["", f"Minimum up front ({up['through']}): cash {_m(up['cash'])}, CPF {_m(up['cpf'])}.",
              f"Renovation and furnishing (cash): {_m(plan['move_in_costs']['cash'])}.",
              f"Household cash {_m(plan['cash_check']['household_cash'])}; needed to move in {_m(plan['cash_check']['cash_needed_to_move_in'])}; "
              f"left {_m(plan['cash_check']['cash_left_after_move_in'])}."]
    ceiling = plan["affordability_ceiling"]
    lines.append("Affordability ceiling (largest loan the stress-tested TDSR/MSR room allows): "
                 f"{_m(ceiling['max_loan'])}"
                 + (f", i.e. a price of about {_m(ceiling['max_price'])} at LTV {Decimal(ceiling['ltv']) * 100:.0f}%"
                    if ceiling["max_price"] is not None else "") + ".")
    lines += ["", f"Monthly commitment once instalments start: {_m(plan['steady_monthly_commitment'])} "
              "(instalment + maintenance + property tax + insurance)."]
    lines += ["", "Bank stress test:"]
    for c in plan["checks"]:
        ratio = f"ratio {Decimal(c['ratio']) * 100:.1f}%" if c["ratio"] is not None else "ratio n/a (no income supplied)"
        lines.append(f"  {c['name']}: {'pass' if c['pass'] else 'FAIL'} at {Decimal(c['stress_rate']) * 100:.2f}% stress rate, "
                     f"{ratio} vs limit {Decimal(c['limit']) * 100:.0f}% "
                     f"(stressed instalment {_m(c['stressed_instalment'])}).")
    if Decimal(plan["grants"]["ehg"]) > 0:
        lines.append(f"Enhanced CPF Housing Grant counted: {_m(plan['grants']['ehg'])} (credited to CPF).")
    lines += [f"  Note: {n}" for n in plan["grants"]["notes"]]
    lines += ["", "Year-by-year (base assumptions; low/base/high are assumptions, not forecasts):"]
    for y, h in plan["horizon"].items():
        lines.append(f"  Year {y}: paid cash {_m(h['cash'])} + CPF {_m(h['cpf'])}; loan left {_m(h['loan_balance'])}; "
                     f"equity built {_m(h['equity_built'])}; CPF accrued interest {_m(h['cpf_accrued_interest'])}.")
    sc = plan["scenarios"]["interest"]
    lines.append("  Instalment at interest low/base/high: " + " / ".join(f"{_m(sc[k]['monthly_instalment'])}" for k in ("low", "base", "high")))
    lines += [f"WARNING: {w}" for w in plan["warnings"]]
    lines += _unverified(plan["unverified_assumptions"])
    return "\n".join(lines)


def compare_summary(cmp: dict) -> str:
    lines = ["Side by side:"]
    for o in cmp["options"]:
        lines.append(f"  {o['name']} ({_m(o['price'])}) - {o['verdict']}")
        lines.append(f"    Up front: cash {_m(o['upfront_cash'])}, CPF {_m(o['upfront_cpf'])}; move-in costs {_m(o['move_in_costs_cash'])}")
        lines.append(f"    Monthly: commitment {_m(o['monthly_total_commitment'])}, cash after CPF {_m(o['monthly_cash_outflow'])}"
                     + (f" (incl. lifestyle {_m(o['lifestyle_monthly'])})" if Decimal(o["lifestyle_monthly"]) > 0 else ""))
        for a in o["lifestyle_addons"]:
            lines.append(f"      - {a['label']} x{a['count']}: {_m(a['monthly'])}/month [{a['price_source']}, {a['operating_status']}]")
        for n in ("5", "10", "15"):
            t = o["tco"][n]
            lines.append(f"    {n}-year cost of occupancy {_m(t['total'])} (interest {_m(t['interest'])}, upkeep {_m(t['maintenance_tax_insurance'])}, "
                         f"duties/fees/fit-out {_m(t['duties_fees_and_fit_out'])}, lifestyle {_m(t['lifestyle_addons'])}, "
                         f"opportunity cost {_m(t['opportunity_cost'])}); equity built {_m(o['equity_built'][n])}")
    lines += ["", "Break-even:"]
    for b in cmp["break_even"]:
        be = b["breakeven_monthly_lifestyle"]
        lines.append(f"  {b['reading']}")
        lines.append(f"    Break-even lifestyle spend per month on {b['cheaper_option']}: {_m(be['monthly_commitment'])} on total commitment, "
                     f"{_m(be['monthly_cash'])} on cash outflow; on 5/10/15-year cost {_m(be['tco']['5'])} / {_m(be['tco']['10'])} / {_m(be['tco']['15'])}.")
        lines.append("    Your add-ons " + ("close" if b["addons_close_commitment_gap"] else "do not close") +
                     f" the monthly gap (headroom {_m(b['headroom_monthly'])}).")
    a = cmp["assumptions"]
    lines += ["", f"Opportunity cost assumed at {Decimal(a['opportunity_cost_assumption']['cash']) * 100:.1f}% (cash) and "
              f"{Decimal(a['opportunity_cost_assumption']['cpf']) * 100:.1f}% (CPF) a year; override it in the scenario.",
              a["monthly_basis"]]
    lines += [f"WARNING: {w}" for w in cmp["warnings"]]
    return "\n".join(lines)


def _unverified(items: list) -> list:
    if not items:
        return []
    return ["", "Unverified inputs used (confirm before relying on them):"] + [f"  - {i['item']}: {i['reason']}" for i in items]


def with_disclaimer(text: str) -> str:
    return f"{text}\n\n{DISCLAIMER}"
