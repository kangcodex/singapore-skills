"""Cash-flow engine for the agent mode.

plan(scenario, policy) -> dict. Inputs: one purchase option, the buyers, household cash
and debts. Outputs: a dated cash/CPF timeline, month-by-month commitments, the
TDSR/MSR checks, upfront cash and CPF, and cumulative cost and equity at year 1/5/10/15
for low/base/high interest-rate and appreciation assumptions.

All money is Decimal; the result is JSON-safe (money rendered as strings).
Simplifications are listed in notes.simplifications of the result.
"""
import json
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from math import ceil
from pathlib import Path

import agent_money as am
import agent_policy as ap
from agent_money import D, ZERO, cents

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "references" / "default-assumptions.json"
CATEGORIES = ("resale_hdb", "resale_condo", "new_launch_condo", "ec")
PROGRESSIVE = ("new_launch_condo", "ec")
HORIZON_MONTHS = 15 * 12

SIMPLIFICATIONS = [
    "Valuation is assumed equal to the price; cash-over-valuation is not modelled.",
    "Stamp duties, legal fees and fit-out are paid in cash unless assumptions.cpf_pays_fees is set.",
    "Monthly CPF OA inflow is the user-supplied cpf_oa_monthly; CPF pays instalments first until the valuation limit is reached.",
    "New launches: interest-only on the drawn balance until CSC, then level instalments over the tenure.",
    "CPF accrued interest counts whole years elapsed.",
    "Variable income haircut is not applied; supply stable monthly income.",
]


def load_assumptions(path=None) -> dict:
    with open(path or ASSUMPTIONS_PATH, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def _merge(base: dict, over: dict) -> dict:
    out = deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return d.replace(year=d.year + y, month=m + 1, day=min(d.day, 28))


def _month_index(start: date, d: date) -> int:
    return (d.year - start.year) * 12 + d.month - start.month


def _s(x) -> str:
    return str(cents(x)) if isinstance(x, Decimal) else str(x)


class _Ctx:
    """Resolved inputs shared by every simulation of one option."""

    def __init__(self, scenario: dict, policy: dict, assumptions: dict):
        self.policy = policy
        self.a = _merge(load_assumptions() if assumptions is None else assumptions,
                        scenario.get("assumptions"))
        opt = scenario["option"]
        self.cat = opt["category"]
        if self.cat not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        self.name = opt.get("name", self.cat)
        self.price = D(opt["price"])
        self.start = date.fromisoformat(scenario["start_date"])
        self.buyers = scenario["buyers"]
        hh = scenario.get("household", {})
        self.cash = D(hh.get("cash", "0"))
        self.debts = D(hh.get("other_monthly_debts", "0"))
        self.income = sum((D(b["monthly_income"]) for b in self.buyers), ZERO)
        self.cpf0 = sum((D(b.get("cpf_oa", "0")) for b in self.buyers), ZERO)
        self.inflow = sum((D(b.get("cpf_oa_monthly", "0")) for b in self.buyers), ZERO)
        self.is_hdb = self.cat == "resale_hdb"
        self.progressive = self.cat in PROGRESSIVE
        self.cpf_pct = D(opt.get("cpf_usable_pct", "1"))
        self.cpf_cap = D(opt.get("valuation", opt["price"])).min(self.price)
        self.first_timer = bool(opt.get("first_timer", False))
        self.opt = opt
        self.notes, self.warnings = [], []
        self._loan()
        self._grants()
        self._lease_check()

    def pol(self, name):
        return self.policy["items"][name]

    def _loan(self):
        loan = self.opt.get("loan", {})
        self.loan_type = loan.get("type", "bank")
        self.tenure = int(loan.get("tenure_years", 25 if self.loan_type == "hdb" else 30))
        if self.loan_type == "hdb":
            if not self.is_hdb:
                raise ValueError("an HDB loan is only available for resale_hdb")
            h = self.pol("hdb_loan")
            self.max_ltv, self.min_cash_pct = D(h["ltv"]), D(h["min_cash_down_payment"])
            self.fixed_rate = D(h["rate"])
            cap = h["max_tenure_years"]
        else:
            self.fixed_rate = None
            outstanding = max(int(b.get("outstanding_loans", b.get("existing_properties", 0))) for b in self.buyers)
            end_age = max(int(b["age"]) for b in self.buyers) + self.tenure
            self.max_ltv, self.min_cash_pct = ap.ltv_limit(outstanding, self.tenure, end_age, self.is_hdb, self.policy)
            cap = ap.max_tenure_years(self.is_hdb, self.policy)
        if self.tenure > cap:
            raise ValueError(f"tenure {self.tenure}y exceeds the {cap}y cap for this loan")
        self.ltv = D(loan.get("ltv", self.max_ltv)).min(self.max_ltv)
        self.loan_amount = cents(D(loan["amount"])) if "amount" in loan else cents(self.price * self.ltv)
        self.loan_amount = min(self.loan_amount, cents(self.price * self.max_ltv))
        self.down_total = cents(self.price - self.loan_amount)
        self.min_cash_total = cents(self.price * self.min_cash_pct)

    def _grants(self):
        self.grant_ehg, self.grant_notes = ZERO, []
        if not (self.is_hdb and self.first_timer):
            return
        if not any(b["residency"] == "sc" for b in self.buyers):
            self.grant_notes.append("EHG needs at least one Singapore Citizen")
            return
        ceiling = D(self.pol("ehg")["income_ceiling"])
        if self.income > ceiling:
            self.grant_notes.append(f"household income {_s(self.income)} is above the EHG income ceiling {ceiling}; no EHG")
            return
        self.grant_ehg = ap.ehg(self.income, self.policy)
        self.grant_notes.append("Family Grant and Proximity Housing Grant amounts are unverified in policy-tables.json and not applied; confirm with HDB")

    def _lease_check(self):
        lease = self.opt.get("remaining_lease_years")
        if lease is None:
            return
        youngest = min(int(b["age"]) for b in self.buyers)
        cover = self.pol("cpf_usage")["lease_cover_to_age"]
        if youngest + int(lease) < cover and "cpf_usable_pct" not in self.opt:
            self.warnings.append(
                f"Lease runs to youngest buyer age {youngest + int(lease)}, below {cover}: CPF usage and HDB loan will be pro-rated. "
                "Rule not modelled (unverified); set option.cpf_usable_pct from the CPF/HDB calculator.")


def _fees(ctx: _Ctx) -> dict:
    f = ctx.pol("legal_valuation_fees")["by_category"][ctx.cat]
    return {"legal_and_other": D(f["legal"]) + D(f["other"]) + D(f["valuation"])}


def _build_events(ctx: _Ctx) -> list:
    """Dated stages. Money fields are requests: down/stage events are split cash/CPF/loan in simulate()."""
    ev = []
    start = ctx.start
    add = lambda **k: ev.append(k)
    duties = ap.bsd(ctx.price, ctx.policy)
    absd = ap.absd(ctx.price, ctx.buyers, ctx.policy)
    legal = _fees(ctx)["legal_and_other"]
    reno = D(ctx.opt.get("renovation", ctx.a["renovation"][ctx.cat]))
    furn = D(ctx.opt.get("furnishing", ctx.a["furnishing"][ctx.cat]))
    weeks = int(ctx.a["fit_out_weeks"])
    if not ctx.progressive:
        if ctx.is_hdb:
            o = ctx.pol("hdb_resale_otp")
            opt_fee = min(D(o["option_fee_max"]), ctx.down_total)
            ex_fee = min(D(o["deposit_max"]) - opt_fee, ctx.down_total - opt_fee)
            ex_days, comp_days = int(o["option_period_days"]), int(o["completion_within_weeks"]) * 7
        else:
            o = ctx.pol("private_resale_otp")
            opt_fee = min(cents(ctx.price * D(o["option_fee_pct"])), ctx.down_total)
            ex_fee = min(cents(ctx.price * D(o["exercise_payment_pct"])), ctx.down_total - opt_fee)
            ex_days, comp_days = int(o["exercise_days"]), int(o["completion_weeks"]) * 7
        ex_date = start + timedelta(days=ex_days)
        comp_date = ex_date + timedelta(days=comp_days)
        c_month = _month_index(start, comp_date)
        add(stage="option_fee", label="Option fee", date=start, month=0, kind="down", amount=opt_fee, cash_only=True)
        add(stage="exercise", label="Exercise of option", date=ex_date, month=_month_index(start, ex_date), kind="down", amount=ex_fee, cash_only=True)
        add(stage="completion_down_payment", label="Balance of down payment at completion", date=comp_date, month=c_month, kind="down", amount=ctx.down_total - opt_fee - ex_fee, cash_only=False)
        duty_month, duty_date, loan_month, tail_month, tail_date = c_month, comp_date, c_month, c_month, comp_date
        complete_month = c_month
    else:
        sched = ctx.pol("new_launch_progressive")["stages"]
        for st in sched:
            d = _add_months(start, st["month_offset"])
            add(stage=st["id"], label=st["label"], date=d, month=st["month_offset"], kind="stage",
                amount=cents(ctx.price * D(st["pct"])), cash_only=bool(st.get("cash_only")))
        sp = next(e for e in ev if e["stage"] == "sp_signing")
        duty_month, duty_date = sp["month"], sp["date"]
        top = next(e for e in ev if e["stage"] == "top")
        csc = next(e for e in ev if e["stage"] == "csc")
        loan_month, complete_month = csc["month"], csc["month"]
        tail_month, tail_date = top["month"], top["date"]
    add(stage="stamp_duty", label="Buyer's stamp duty (BSD)", date=duty_date, month=duty_month, kind="duty", amount=duties, cash_only=True)
    if absd > 0:
        add(stage="absd", label="Additional buyer's stamp duty (ABSD)", date=duty_date, month=duty_month, kind="duty", amount=absd, cash_only=True)
    add(stage="legal_and_other_fees", label="Legal, valuation and other fees", date=duty_date, month=duty_month, kind="fee", amount=legal, cash_only=True)
    move_in = tail_month + ceil(weeks * 7 / 30) + (1 if ctx.progressive else 0)
    if reno > 0:
        add(stage="renovation", label="Renovation", date=tail_date, month=tail_month, kind="fit_out", amount=reno, cash_only=True)
    if furn > 0:
        add(stage="furnishing", label="Furnishing and move-in", date=_add_months(start, move_in), month=move_in, kind="fit_out", amount=furn, cash_only=True)
    ctx.loan_month, ctx.move_in, ctx.complete_month = loan_month, move_in, complete_month
    ev.append(dict(stage="move_in", label="Move in", date=_add_months(start, move_in), month=move_in, kind="milestone", amount=ZERO, cash_only=True))
    ev.sort(key=lambda e: (e["month"], e["date"]))
    return ev


def _stress(ctx: _Ctx, base_rate: Decimal) -> dict:
    hdb_loan = ctx.loan_type == "hdb"
    rate = ap.stress_rate(ctx.fixed_rate if hdb_loan else base_rate, hdb_loan, ctx.policy)
    pmt = am.monthly_payment(ctx.loan_amount, rate, ctx.tenure)
    checks = []
    if ctx.loan_type == "bank":
        c = ap.tdsr_check(ctx.income, ctx.debts, pmt, ctx.policy)
        checks.append({"name": "TDSR", **c})
    if ctx.is_hdb or ctx.cat == "ec":
        c = ap.msr_check(ctx.income, pmt, ctx.policy)
        checks.append({"name": "MSR", **c})
    return [{"name": c["name"], "pass": c["pass"], "ratio": _s(c["ratio"]) if c["ratio"] is not None else None,
             "limit": str(c["limit"]), "stress_rate": str(rate), "stressed_instalment": _s(pmt),
             "monthly_income": _s(ctx.income), "other_debts": _s(ctx.debts)} for c in checks]


def _simulate(ctx: _Ctx, events: list, rate: Decimal, appreciation: Decimal) -> dict:
    rate = ctx.fixed_rate if ctx.loan_type == "hdb" else rate
    horizon = HORIZON_MONTHS
    cpf_rate = D(ctx.pol("cpf_accrued_interest")["rate"])
    grant_month = ctx.complete_month
    pool = ctx.cpf0
    used_property = ZERO
    cash_only_down = sum((e["amount"] for e in events if e["kind"] in ("down", "stage") and e["cash_only"]), ZERO)
    extra_cash_left = max(ZERO, ctx.min_cash_total - cash_only_down)
    down_left = ctx.down_total
    drawn = ZERO
    bal = ZERO
    pmt_full = am.monthly_payment(ctx.loan_amount, rate, ctx.tenure)
    by_month = {}
    for e in events:
        by_month.setdefault(e["month"], []).append(e)
    out_events, cpf_draws = [], []
    rows = []
    cum = {"cash": ZERO, "cpf": ZERO, "interest": ZERO, "principal": ZERO, "fixed": ZERO, "fees": ZERO}
    snapshots = {}
    av = D(ctx.opt["annual_value"]) if "annual_value" in ctx.opt else cents(ctx.price * D(ctx.a["annual_value_pct_of_price"][ctx.cat]))
    maint = D(ctx.opt.get("monthly_maintenance", ctx.a["monthly_maintenance"][ctx.cat]))
    insur = D(ctx.opt.get("monthly_insurance", ctx.a["monthly_insurance"][ctx.cat]))
    tax_m = cents(ap.property_tax(av, ctx.policy) / 12)
    cpf_pays_fees = bool(ctx.a.get("cpf_pays_fees", False))
    amort_started = False
    for m in range(0, horizon + 1):
        if m > 0:
            pool += ctx.inflow
        if m == grant_month and ctx.grant_ehg > 0:
            pool += ctx.grant_ehg
        for e in by_month.get(m, []):
            amt, cash, cpf, loan = e["amount"], ZERO, ZERO, ZERO
            if e["kind"] in ("down", "stage"):
                if e["kind"] == "stage":
                    down_part = min(amt, down_left)
                    loan = amt - down_part
                else:
                    down_part = amt
                down_left -= down_part
                if e["cash_only"]:
                    cash = down_part
                else:
                    forced = min(down_part, extra_cash_left)
                    extra_cash_left -= forced
                    cpf_cap_left = max(ZERO, ctx.cpf_cap - used_property)
                    cpf = min(down_part - forced, pool * ctx.cpf_pct if ctx.cpf_pct < 1 else pool, cpf_cap_left)
                    cash = down_part - cpf
                drawn += loan
            elif e["kind"] in ("duty", "fee", "fit_out") and cpf_pays_fees and e["kind"] != "fit_out":
                cpf = min(amt, pool)
                cash = amt - cpf
            else:
                cash = amt
            pool -= cpf
            used_property += cpf if e["kind"] in ("down", "stage") else ZERO
            if cpf:
                cpf_draws.append((m, cpf))
            cum["cash"] += cash
            cum["cpf"] += cpf
            if e["kind"] in ("duty", "fee", "fit_out"):
                cum["fees"] += cash + cpf
            out_events.append({**{k: e[k] for k in ("stage", "label", "kind", "month")}, "date": e["date"].isoformat(),
                               "cash": _s(cash), "cpf": _s(cpf), "loan_drawn": _s(loan),
                               **({"stage_amount": _s(amt)} if e["kind"] == "stage" or e["kind"] == "down" else {}),
                               **({"cpf_grant_credit": _s(ctx.grant_ehg)} if e["stage"] == "completion_down_payment" and ctx.grant_ehg > 0 else {})})
        # monthly obligations
        row = None
        if m >= 1:
            ptype, inst, interest, principal = None, ZERO, ZERO, ZERO
            if ctx.progressive:
                if drawn > 0 and m < ctx.loan_month:
                    interest = cents(drawn * rate / 12)
                    inst, ptype = interest, "interest_only"
                elif m > ctx.loan_month:
                    if not amort_started:
                        bal, amort_started = drawn, True
                    ptype = "instalment"
            elif m > ctx.loan_month:
                if not amort_started:
                    bal, amort_started = ctx.loan_amount, True
                ptype = "instalment"
            if ptype == "instalment" and bal > 0:
                interest = cents(bal * rate / 12)
                inst = min(pmt_full, bal + interest)
                principal = inst - interest
                bal -= principal
            maintenance = maint if m >= ctx.move_in else ZERO
            tax = tax_m if m >= ctx.move_in else ZERO
            ins = insur if m >= ctx.move_in else ZERO
            cap_left = max(ZERO, ctx.cpf_cap - used_property)
            cpf_paid = min(inst, pool, cap_left) if inst > 0 else ZERO
            cash_paid = inst - cpf_paid
            pool -= cpf_paid
            used_property += cpf_paid
            if cpf_paid:
                cpf_draws.append((m, cpf_paid))
            other = maintenance + tax + ins
            cum["cash"] += cash_paid + other
            cum["cpf"] += cpf_paid
            cum["interest"] += interest
            cum["principal"] += principal
            cum["fixed"] += other
            row = {"month": m, "date": _add_months(ctx.start, m).strftime("%Y-%m"), "payment_type": ptype or "none",
                   "instalment": _s(inst), "cpf_paid": _s(cpf_paid), "cash_paid": _s(cash_paid),
                   "maintenance": _s(maintenance), "property_tax": _s(tax), "insurance": _s(ins),
                   "total_commitment": _s(inst + other), "total_cash_outflow": _s(cash_paid + other)}
            rows.append(row)
        if m in (12, 60, 120, 180):
            n = m // 12
            value = cents(ctx.price * (1 + appreciation) ** n)
            loan_bal = bal if amort_started else drawn
            accrued = sum((amt * ((1 + cpf_rate) ** ((m - k) // 12) - 1) for k, amt in cpf_draws), ZERO)
            snapshots[str(n)] = {
                "cash": _s(cum["cash"]), "cpf": _s(cum["cpf"]), "total_outflow": _s(cum["cash"] + cum["cpf"]),
                "interest_paid": _s(cum["interest"]), "principal_repaid": _s(cum["principal"]),
                "maintenance_tax_insurance": _s(cum["fixed"]), "duties_fees_and_fit_out": _s(cum["fees"]),
                "loan_balance": _s(loan_bal), "property_value": _s(value),
                "equity_value": _s(value - loan_bal),
                "equity_built": _s(value - ctx.price + cum["principal"]),
                "cpf_used_for_property": _s(used_property), "cpf_accrued_interest": _s(accrued),
            }
    return {"events": out_events, "rows": rows, "snapshots": snapshots, "pmt": pmt_full,
            "cpf_pool_end": pool, "events_raw": by_month}


def _sum_events(events: list, field: str, pred=lambda e: True) -> Decimal:
    return sum((D(e[field]) for e in events if pred(e)), ZERO)


def plan(scenario: dict, policy: dict, assumptions: dict = None) -> dict:
    ctx = _Ctx(scenario, policy, assumptions)
    events = _build_events(ctx)
    a = ctx.a
    base_rate = D(a["interest_rate"]["base"])
    base = _simulate(ctx, events, base_rate, D(a["appreciation"]["base"]))
    timeline = base["events"]
    upfront_cut = ctx.complete_month if not ctx.progressive else next(e["month"] for e in events if e["stage"] == "sp_signing")
    up = [e for e in timeline if e["kind"] in ("down", "stage", "duty", "fee") and e["month"] <= upfront_cut]
    upfront = {"cash": _s(_sum_events(up, "cash")), "cpf": _s(_sum_events(up, "cpf")),
               "through": "completion" if not ctx.progressive else "S&P signing (first 20% + duties + fees)"}
    fit = [e for e in timeline if e["kind"] == "fit_out"]
    move_in_costs = {"cash": _s(_sum_events(fit, "cash")), "cpf": _s(_sum_events(fit, "cpf"))}
    construction = [e for e in timeline if e["kind"] == "stage" and e["month"] > upfront_cut]
    steady = next((r for r in base["rows"] if r["payment_type"] == "instalment" and r["month"] >= ctx.move_in), base["rows"][-1])
    checks = _stress(ctx, base_rate)
    total_cash_need = _sum_events(timeline, "cash", lambda e: e["month"] <= ctx.move_in)
    gap = max(ZERO, total_cash_need - ctx.cash)
    buffer_months = int(a["min_buffer_months"])
    commit = D(steady["total_commitment"])
    left = ctx.cash - total_cash_need
    all_pass = all(c["pass"] for c in checks)
    worst = max((D(c["ratio"]) for c in checks if c["ratio"] is not None), default=ZERO)
    if not all_pass or gap > 0:
        verdict = "not affordable"
    elif worst > D(a["stretch_tdsr_ratio"]) or left < commit * buffer_months:
        verdict = "stretch"
    else:
        verdict = "affordable"
    interest, appr = {}, {}
    for k in ("low", "base", "high"):
        r = base if k == "base" else _simulate(ctx, events, D(a["interest_rate"][k]), D(a["appreciation"]["base"]))
        interest[k] = {"rate": str(a["interest_rate"][k] if ctx.loan_type == "bank" else ctx.fixed_rate),
                       "monthly_instalment": _s(r["pmt"]), "horizon": r["snapshots"]}
        g = base if k == "base" else _simulate(ctx, events, base_rate, D(a["appreciation"][k]))
        appr[k] = {"annual_appreciation": str(a["appreciation"][k]), "horizon": g["snapshots"]}
    return {
        "option": {"name": ctx.name, "category": ctx.cat, "price": _s(ctx.price), "start_date": ctx.start.isoformat()},
        "verdict": verdict,
        "loan": {"type": ctx.loan_type, "amount": _s(ctx.loan_amount), "ltv": str(ctx.ltv), "max_ltv": str(ctx.max_ltv),
                 "tenure_years": ctx.tenure, "rate": str(ctx.fixed_rate if ctx.loan_type == "hdb" else base_rate),
                 "monthly_instalment": _s(base["pmt"]), "min_cash_down_payment": _s(ctx.min_cash_total)},
        "checks": checks,
        "timeline": timeline,
        "upfront": upfront,
        "down_payment": {"cash": _s(_sum_events(timeline, "cash", lambda e: e["kind"] in ("down", "stage"))),
                         "cpf": _s(_sum_events(timeline, "cpf", lambda e: e["kind"] in ("down", "stage")))},
        "construction_payments": [{k: e[k] for k in ("stage", "date", "cash", "cpf", "loan_drawn")} for e in construction],
        "move_in_costs": move_in_costs,
        "move_in_month": ctx.move_in,
        "monthly_schedule": base["rows"][:int(a["schedule_months"])],
        "monthly_schedule_full": base["rows"],
        "steady_monthly_commitment": steady["total_commitment"],
        "horizon": base["snapshots"],
        "scenarios": {"status": "assumption", "note": "Low/base/high are user-overridable assumptions, not forecasts.",
                      "interest": interest, "appreciation": appr},
        "grants": {"ehg": _s(ctx.grant_ehg), "notes": ctx.grant_notes},
        "cash_check": {"household_cash": _s(ctx.cash), "cash_needed_to_move_in": _s(total_cash_need), "gap": _s(gap),
                       "cash_left_after_move_in": _s(left)},
        "affordability_ceiling": _affordability_ceiling(ctx),
        "warnings": ctx.warnings,
        "unverified_assumptions": [{"item": n, "reason": r} for n, r in ap.unverified_items(ctx.policy)
                                   if n in _used_items(ctx)],
        "notes": {"simplifications": SIMPLIFICATIONS},
    }


def _used_items(ctx: _Ctx) -> set:
    used = {"legal_valuation_fees", "cpf_accrued_interest", "absd"}
    if ctx.loan_type == "hdb":
        used.add("hdb_loan")
    if ctx.progressive:
        used.add("new_launch_progressive")
    if not ctx.progressive and not ctx.is_hdb:
        used.add("private_resale_otp")
    if ctx.cat == "ec":
        used.add("ec_mop")
    if ctx.is_hdb:
        used.add("hdb_mop")
        if ctx.first_timer:
            used.update(("family_grant_resale", "proximity_housing_grant", "income_ceilings"))
    return used


def _affordability_ceiling(ctx: _Ctx) -> dict:
    """Largest loan (and price at the allowed LTV) whose stress-tested instalment fits the TDSR/MSR room."""
    hdb_loan = ctx.loan_type == "hdb"
    rate = ap.stress_rate(ctx.fixed_rate if hdb_loan else D(ctx.a["interest_rate"]["base"]), hdb_loan, ctx.policy)
    rooms = []
    if ctx.loan_type == "bank":
        rooms.append(D(ctx.pol("tdsr")["max_ratio"]) * ctx.income - ctx.debts)
    if ctx.is_hdb or ctx.cat == "ec":
        rooms.append(D(ctx.pol("msr")["max_ratio"]) * ctx.income)
    room = max(ZERO, min(rooms))
    n, r = ctx.tenure * 12, rate / 12
    loan = room * (1 - (1 + r) ** -n) / r if r else room * n
    return {"stress_rate": str(rate), "monthly_instalment_room": _s(room), "max_loan": _s(loan),
            "max_price": _s(loan / ctx.ltv) if ctx.ltv else None, "ltv": str(ctx.ltv)}


def max_affordable(scenario: dict, policy: dict, assumptions: dict = None) -> dict:
    return _affordability_ceiling(_Ctx(scenario, policy, assumptions))
