"""Traceable comparable metadata screens and disclosed scenarios, not forecasts."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from statistics import median

from advisor_calculations import amount, price_premium, trend_block
from advisor_location import evidence_problem
from advisor_records import CaseError, Record, record, rows, strings
from advisor_requirements import date_window, exact_date
from agent_schedule import add_months


def assess_comparables(data: Record) -> Record:
    as_of = exact_date(data.get("as_of"))
    subject = record(data.get("subject"), "subject")
    required = ("property_id", "bedrooms", "area_sqft", "area_basis")
    missing = [key for key in required if subject.get(key) is None]
    if missing:
        return {"status": "unknown", "missing_inputs": missing, "fair_value": None, "selected": [], "pending": [], "excluded": []}
    target_area = amount(str(subject["area_sqft"]))
    if not target_area:
        raise CaseError("subject.area_sqft", "area must be positive")
    tolerance = amount(str(data.get("area_tolerance_pct", "10"))) / 100
    cutoff = exact_date(data["window_start"]) if data.get("window_start") else add_months(as_of, -24)
    selected: list[Record] = []
    pending: list[Record] = []
    excluded: list[Record] = []
    cross_project: list[Record] = []
    duplicates: list[Record] = []
    seen_ids: set[str] = set()
    transaction_keys: set[str] = set()
    for raw in rows(data.get("observations", []), "observations"):
        observation = dict(raw)
        identity = str(observation.get("id") or "")
        if not identity or identity in seen_ids:
            raise CaseError("observation.id", "unique ids required")
        seen_ids.add(identity)
        transaction_key = str(observation.get("transaction_key") or "")
        if transaction_key and transaction_key in transaction_keys:
            duplicates.append({**observation, "reason": "Same supplied underlying transaction key"})
            continue
        reason = evidence_problem(observation, as_of)
        if reason:
            pending.append({**observation, "reason": reason})
            continue
        if observation.get("kind") != "transaction":
            excluded.append({**observation, "reason": "Asking/quotation/scenario is not a completed transaction"})
            continue
        if any(observation.get(key) is None for key in ("property_id", "bedrooms", "area_sqft", "area_basis", "price", "date")):
            pending.append({**observation, "reason": "Missing comparable fact, not a zero or automatic match"})
            continue
        if observation["bedrooms"] != subject["bedrooms"] or observation["area_basis"] != subject["area_basis"]:
            excluded.append({**observation, "reason": "Bedroom/measurement basis mismatch"})
            continue
        observed = date_window(observation["date"])
        if observed.first > as_of or observed.last < cutoff:
            excluded.append({**observation, "reason": "Outside the declared evidence window"})
            continue
        if observed.first < cutoff <= observed.last:
            pending.append({**observation, "reason": "Date precision straddles the window boundary"})
            continue
        area = amount(str(observation["area_sqft"]))
        if not area or abs(area / target_area - 1) > tolerance:
            excluded.append({**observation, "reason": "Area outside declared tolerance"})
            continue
        price = amount(str(observation["price"]))
        observation["calculated_psf"] = str((price / area).quantize(Decimal("0.01")))
        if observation["property_id"] != subject["property_id"]:
            cross_project.append({**observation, "reason": "Separate cross-project control; explicit adjustments required"})
            continue
        mismatched = [key for key in ("tenure", "sale_type", "category") if subject.get(key) is not None and observation.get(key) != subject[key]]
        if mismatched:
            pending.append({**observation, "reason": "Missing/different matching attributes: " + ", ".join(mismatched)})
            continue
        selected.append(observation)
        if transaction_key:
            transaction_keys.add(transaction_key)
    psfs = [Decimal(str(item["calculated_psf"])) for item in selected]
    selected_median = median(psfs) if psfs else None
    premium = None
    if selected_median and subject.get("price") is not None:
        premium = str(price_premium(str(subject["price"]), "total", str(selected_median), "psf", str(target_area)))
    periods: dict[str, list[Decimal]] = defaultdict(list)
    for observation in selected:
        first = date_window(observation["date"]).first
        periods[f"{first.year}-Q{(first.month - 1) // 3 + 1}"].append(Decimal(str(observation["calculated_psf"])))
    quarterly = [{"qtr": period, "value": str(median(values))} for period, values in sorted(periods.items())]
    trend = trend_block(quarterly, "value", as_of=as_of)
    return {"status": "metadata_crosscheck_only" if selected else "insufficient_evidence", "selection_criteria": {"window_start": cutoff.isoformat(), "as_of": as_of.isoformat(), "area_tolerance_pct": str(tolerance * 100)}, "sample_size": len(selected), "selected": selected, "pending": pending, "excluded": excluded, "cross_project_controls": cross_project, "duplicates": duplicates, "selected_unadjusted_median_psf": str(selected_median) if selected_median else None, "asking_premium_to_selected_sample_pct": premium, "fair_value": None, "trend": dict(trend), "quarter_samples": {key: len(value) for key, value in periods.items()}, "limitations": ["Selection is based on supplied metadata; floor/stack/layout/condition and adjustment quality still need review", "Sample median is not whole-project median, formal valuation or matched-unit appreciation", "Price kind/terms, exact identity and availability limit negotiation conclusions; missing samples are not zero transactions"]}


def assess_scenarios(data: Record) -> Record:
    price = amount(str(data.get("entry_price")))
    years_raw = data.get("years", [1, 5, 10, 15])
    if not isinstance(years_raw, list) or not years_raw or any(type(year) is not int or not 1 <= year <= 50 for year in years_raw):
        raise CaseError("years", "integer horizons between one and fifty required")
    results: list[Record] = []
    ids: set[str] = set()
    for scenario in rows(data.get("scenarios"), "scenarios"):
        identity = str(scenario.get("id") or "")
        if not identity or identity in ids:
            raise CaseError("scenario.id", "nonempty unique ids required")
        ids.add(identity)
        try:
            rate = Decimal(str(scenario.get("annual_rate_decimal")))
        except InvalidOperation as exc:
            raise CaseError("annual_rate_decimal", "a decimal rate is required") from exc
        if not rate.is_finite() or rate < -1:
            raise CaseError("annual_rate_decimal", "finite rate not below minus one required")
        values: Record = {str(year): str((price * (1 + rate) ** year).quantize(Decimal("0.01"))) for year in years_raw}
        results.append({"id": identity, "annual_rate_decimal": str(rate), "values": values, "rationale": scenario.get("rationale"), "evidence_ids": strings(scenario.get("evidence_ids", []), "evidence_ids"), "status": "assumed_with_rationale" if scenario.get("rationale") else "assumed_without_rationale"})
    break_even = None
    if data.get("nonrecoverable_costs") is not None and data.get("fixed_selling_costs") is not None and data.get("selling_cost_rate_decimal") is not None:
        rate = amount(str(data["selling_cost_rate_decimal"]))
        if rate >= 1:
            raise CaseError("selling_cost_rate_decimal", "must be below one")
        break_even = str(((price + amount(str(data["nonrecoverable_costs"])) + amount(str(data["fixed_selling_costs"]))) / (1 - rate)).quantize(Decimal("0.01")))
    return {"status": "assumptions_not_forecast", "scenarios": results, "break_even_price_on_supplied_cost_basis": break_even, "limitations": ["Nearby transactions do not automatically set growth rates or probabilities; justify thesis/counter-thesis and downside/flat/base/upside inputs", "Future value is not net sale cash; debt, applicable exit costs and CPF refunds need separate reconciliation", "Do not double-count principal/refunds as nonrecoverable costs; construction periods, rent assumptions and opportunity-cost basis must be explicit"]}
