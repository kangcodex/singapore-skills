"""Alternatives comparison for the agent mode.

compare(scenario, policy) runs agent_cashflow.plan for every option, prices optional
lifestyle add-ons (e.g. a gym membership for an HDB option), and reports up-front cash,
monthly outflow, total cost of occupancy at 5/10/15 years, equity built and the monthly
lifestyle spend that closes the cash-flow gap to the costlier option.
"""
import json
from decimal import Decimal
from itertools import combinations
from pathlib import Path

import agent_cashflow as cf
from agent_money import D, ZERO, cents

CATALOG_PATH = Path(__file__).resolve().parent.parent / "references" / "lifestyle-addons.json"
HORIZONS = ("5", "10", "15")
WEEKS_PER_MONTH = Decimal("52") / Decimal("12")


def load_catalog(path=None) -> dict:
    with open(path or CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def validate_catalog(catalog: dict) -> list:
    errors = []
    for name, item in catalog.get("items", {}).items():
        if not item.get("as_of"):
            errors.append(f"{name}: missing as_of")
        if not str(item.get("source_url", "")).startswith("https://"):
            errors.append(f"{name}: missing https source_url")
        if item.get("operating", {}).get("status") not in ("verified", "unverified"):
            errors.append(f"{name}: operating.status must be verified or unverified")
        if item.get("price_basis") not in ("weekly", "monthly"):
            errors.append(f"{name}: price_basis must be weekly or monthly")
    return errors


def price_addon(spec: dict, catalog: dict = None) -> dict:
    """Monthly cost of one add-on line: user override > catalog default."""
    catalog = catalog or load_catalog()
    count = int(spec.get("count", 1))
    if "id" in spec:
        if spec["id"] not in catalog["items"]:
            raise ValueError(f"unknown add-on id {spec['id']!r}; choose from {sorted(catalog['items'])}")
        item = catalog["items"][spec["id"]]
        label, status = item["label"], item["operating"]["status"]
        source, as_of = item["source_url"], item["as_of"]
        per_person = item.get("per_person", True)
    else:
        item, label, status, source, as_of, per_person = None, spec["label"], "user_supplied", None, None, True
    if "monthly" in spec:
        unit, price_source = D(spec["monthly"]), "user_override"
    elif item is not None and item.get("price") is not None:
        raw = D(item["price"])
        unit = raw * WEEKS_PER_MONTH if item["price_basis"] == "weekly" else raw
        price_source = "catalog_default"
    else:
        raise ValueError(f"add-on {spec.get('id')!r} has no verified default price; supply monthly")
    members = count if per_person else 1
    return {"id": spec.get("id"), "label": label, "count": members, "monthly": str(cents(unit * members)),
            "unit_monthly": str(cents(unit)), "price_source": price_source,
            "operating_status": status, "source_url": source, "as_of": as_of}


def _opportunity_cost(down: dict, years: int, rates: dict) -> Decimal:
    return (D(down["cash"]) * ((1 + D(rates["cash"])) ** years - 1)
            + D(down["cpf"]) * ((1 + D(rates["cpf"])) ** years - 1))


def _option_summary(name: str, plan: dict, addons: list, rates: dict) -> dict:
    addon_monthly = sum((D(a["monthly"]) for a in addons), ZERO)
    steady = next(r for r in plan["monthly_schedule_full"]
                  if r["payment_type"] == "instalment" and r["month"] >= plan["move_in_month"])
    commit = D(steady["total_commitment"])
    cash_out = D(steady["total_cash_outflow"])
    tco = {}
    for n in HORIZONS:
        h = plan["horizon"][n]
        months = max(0, int(n) * 12 - plan["move_in_month"])
        parts = {
            "interest": D(h["interest_paid"]),
            "maintenance_tax_insurance": D(h["maintenance_tax_insurance"]),
            "duties_fees_and_fit_out": D(h["duties_fees_and_fit_out"]),
            "lifestyle_addons": addon_monthly * months,
            "opportunity_cost": _opportunity_cost(plan["down_payment"], int(n), rates),
        }
        tco[n] = {**{k: str(cents(v)) for k, v in parts.items()}, "total": str(cents(sum(parts.values(), ZERO))),
                  "appreciation_gain": str(cents(D(h["property_value"]) - D(plan["option"]["price"])))}
    return {
        "name": name, "category": plan["option"]["category"], "price": plan["option"]["price"],
        "verdict": plan["verdict"],
        "requirement_status": plan["option"].get("requirement_status", "unknown"),
        "timing_result": plan.get("timing_check", {}).get("result", "unknown"),
        "upfront_cash": plan["upfront"]["cash"], "upfront_cpf": plan["upfront"]["cpf"],
        "move_in_costs_cash": plan["move_in_costs"]["cash"],
        "monthly_instalment": steady["instalment"],
        "monthly_total_commitment": str(cents(commit + addon_monthly)),
        "monthly_cash_outflow": str(cents(cash_out + addon_monthly)),
        "monthly_total_commitment_ex_lifestyle": str(cents(commit)),
        "monthly_cash_outflow_ex_lifestyle": str(cents(cash_out)),
        "lifestyle_monthly": str(cents(addon_monthly)),
        "lifestyle_addons": addons,
        "tco": tco,
        "equity_built": {n: plan["horizon"][n]["equity_built"] for n in HORIZONS},
        "checks": plan["checks"],
        "_move_in_month": plan["move_in_month"],
    }


def _break_even(a: dict, b: dict) -> dict:
    """a is cheaper (ex-lifestyle) than b: monthly lifestyle spend on a that closes the gap to b."""
    gap_commit = D(b["monthly_total_commitment_ex_lifestyle"]) - D(a["monthly_total_commitment_ex_lifestyle"])
    gap_cash = D(b["monthly_cash_outflow_ex_lifestyle"]) - D(a["monthly_cash_outflow_ex_lifestyle"])
    tco_be = {}
    for n in HORIZONS:
        months = max(1, int(n) * 12 - a["_move_in_month"])
        a_ex = D(a["tco"][n]["total"]) - D(a["tco"][n]["lifestyle_addons"])
        gap = D(b["tco"][n]["total"]) - D(b["tco"][n]["lifestyle_addons"]) - a_ex
        tco_be[n] = str(cents(max(ZERO, gap) / months))
    addons = D(a["lifestyle_monthly"])
    return {
        "cheaper_option": a["name"], "costlier_option": b["name"],
        "monthly_commitment_gap": str(cents(gap_commit)),
        "monthly_cash_outflow_gap": str(cents(gap_cash)),
        "breakeven_monthly_lifestyle": {"monthly_commitment": str(cents(max(ZERO, gap_commit))),
                                        "monthly_cash": str(cents(max(ZERO, gap_cash))), "tco": tco_be},
        "addons_monthly": str(cents(addons)),
        "addons_close_commitment_gap": addons >= gap_commit,
        "headroom_monthly": str(cents(gap_commit - addons)),
        "reading": (f"{a['name']} stays cheaper per month until lifestyle spend passes {cents(max(ZERO, gap_commit))} "
                    f"(you are budgeting {cents(addons)})."),
    }


def compare(scenario: dict, policy: dict, assumptions: dict = None, catalog: dict = None) -> dict:
    options = scenario["options"]
    if len(options) < 2:
        raise ValueError("compare needs at least two options")
    catalog = catalog or load_catalog()
    merged = None
    summaries, warnings = [], []
    for opt in options:
        sub = {k: v for k, v in scenario.items() if k != "options"}
        opt = dict(opt)
        specs = opt.pop("lifestyle_addons", [])
        sub["option"] = opt
        plan = cf.plan(sub, policy, assumptions)
        if merged is None:
            merged = cf._merge(cf.load_assumptions() if assumptions is None else assumptions, scenario.get("assumptions"))
        addons = [price_addon(s, catalog) for s in specs]
        for a in addons:
            if a["operating_status"] == "unverified":
                warnings.append(f"{opt.get('name', opt['category'])}: add-on {a['id']} operator/price unverified; confirm before relying on it")
        summaries.append(_option_summary(opt.get("name", opt["category"]), plan, addons, merged["opportunity_cost"]))
        summaries[-1]["_plan_warnings"] = plan["warnings"]
    warnings += [w for s in summaries for w in s["_plan_warnings"]]
    breaks = []
    for x, y in combinations(summaries, 2):
        lo, hi = sorted((x, y), key=lambda s: D(s["monthly_total_commitment_ex_lifestyle"]))
        breaks.append(_break_even(lo, hi))
    for s in summaries:
        s.pop("_move_in_month"), s.pop("_plan_warnings")
    return {
        "options": summaries,
        "break_even": breaks,
        "assumptions": {
            "opportunity_cost_assumption": {**{k: str(merged["opportunity_cost"][k]) for k in ("cash", "cpf")},
                                            "status": "assumption",
                                            "note": "Annual forgone return on the down payment; override via assumptions.opportunity_cost."},
            "monthly_basis": "Monthly figures are the first full-instalment month after move-in. Cash outflow nets off what CPF OA pays, which depends on the CPF balance and monthly inflow you supplied and may fall over time; the total commitment is CPF-independent.",
            "tco_definition": "interest + maintenance/conservancy + property tax + insurance + duties/fees/fit-out + lifestyle add-ons + opportunity cost of the down payment; principal repaid is equity, not cost",
            "interest_rate": {k: str(merged["interest_rate"][k]) for k in ("low", "base", "high")},
            "appreciation": {k: str(merged["appreciation"][k]) for k in ("low", "base", "high")},
        },
        "warnings": warnings,
    }
