"""Chronological funding over supplied eligible funds/events, not policy inference."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from advisor_calculations import amount
from advisor_cash_events import cash_events
from advisor_records import CaseError, JSONValue, Record, rows, strings
from advisor_requirements import exact_date


class FundKind(StrEnum):
    CASH = "cash"
    CPF = "cpf"
    LOAN = "loan"


@dataclass(frozen=True, slots=True)
class Fund:
    identity: str
    kind: FundKind
    balance: Decimal
    reserve: Decimal
    cap: Decimal | None


def money(value: JSONValue, field: str) -> Decimal:
    result = amount(str(value))
    if result != result.quantize(Decimal("0.01")):
        raise CaseError(field, "SGD amounts must have cent precision")
    return result


def _funds(entries: list[Record]) -> tuple[dict[str, Fund], list[str]]:
    funds: dict[str, Fund] = {}
    limitations: list[str] = []
    for entry in entries:
        if entry.get("currency", "SGD") != "SGD":
            raise CaseError("fund.currency", "cross-currency funding requires an explicit external conversion")
        identity = str(entry.get("id") or "")
        if not identity or identity in funds:
            raise CaseError("funds", "fund ids must be unique and nonempty")
        try:
            kind = FundKind(str(entry.get("kind")))
        except ValueError as exc:
            raise CaseError("fund.kind", "expected cash, cpf or loan") from exc
        if "reserve" not in entry:
            limitations.append(f"{identity}: reserve not supplied; zero used only as a conditional scenario")
        cap = money(entry["usable_cap"], "usable_cap") if entry.get("usable_cap") is not None else None
        if kind == FundKind.CPF and cap is None:
            limitations.append(f"{identity}: CPF usable cap is unknown; no CPF allocation is allowed until supplied")
            cap = Decimal(0)
        funds[identity] = Fund(identity, kind, money(entry.get("balance"), "fund.balance"), money(entry.get("reserve", "0"), "fund.reserve"), cap)
    return funds, limitations


def _one_plan(data: Record, strategy: str) -> Record:
    entries = rows(data.get("funds"), "funds")
    events = cash_events(data)
    if strategy not in {"cash_first", "cpf_first", "preserve_cash", "preserve_cpf"}:
        raise CaseError("strategy", "expected cash_first, cpf_first, preserve_cash or preserve_cpf")
    if data.get("currency", "SGD") != "SGD":
        raise CaseError("currency", "currency conversion is not implicit")
    missing = [f"events[{index}].{field}" for index, event in enumerate(events) for field in ("date", "amount") if event.get(field) is None]
    if not entries or not events or missing:
        return {"status": "unknown", "missing_inputs": missing or ["nonempty funds and events"], "timeline": [], "limitations": ["Exact funding needs dated, quantified obligations and resources"], "scenario_only": True}
    funds, limitations = _funds(entries)
    balances = {identity: fund.balance for identity, fund in funds.items()}
    used = {identity: Decimal(0) for identity in funds}
    ids: set[str] = set()
    grouped: dict[str, list[Record]] = defaultdict(list)
    for event in events:
        identity = str(event.get("id") or "")
        if not identity or identity in ids:
            raise CaseError("events", "event ids must be unique and nonempty")
        ids.add(identity)
        grouped[exact_date(event["date"]).isoformat()].append(event)
    if data.get("as_of") is not None and any(exact_date(day) < exact_date(data["as_of"]) for day in grouped):
        return {"status": "unknown", "timeline": [], "limitations": ["Events precede the opening-balance date; current resources cannot be spent retroactively. Supply the historical opening balances or remove already-paid history."], "scenario_only": True}
    cash_first = strategy in {"cash_first", "preserve_cpf"}
    priority = {FundKind.LOAN: 0, FundKind.CASH: 1 if cash_first else 2, FundKind.CPF: 2 if cash_first else 1}
    order = sorted(funds, key=lambda identity: (priority[funds[identity].kind], identity))
    timeline: list[Record] = []
    total_gap = Decimal(0)
    first_gap: Record | None = None
    uncertain_receipts: list[str] = []
    assumed_receipts: list[str] = []
    monthly_cash: dict[str, Decimal] = defaultdict(Decimal)
    unfunded_non_cash_recurring = False
    opening_gap = sum((max(Decimal(0), fund.reserve - fund.balance) for fund in funds.values()), Decimal(0))

    def allocate(identity: str, requested: Decimal) -> Decimal:
        fund = funds[identity]
        available = max(Decimal(0), balances[identity] - fund.reserve)
        if fund.cap is not None:
            available = min(available, max(Decimal(0), fund.cap - used[identity]))
        paid = min(requested, available)
        balances[identity] -= paid
        used[identity] += paid
        return paid

    for day, day_events in sorted(grouped.items()):
        if len(day_events) > 1:
            sequence = [event.get("sequence") for event in day_events]
            if any(type(value) is not int for value in sequence) or len(set(str(value) for value in sequence)) != len(sequence):
                status = "conditional" if limitations or uncertain_receipts or assumed_receipts else "shortfall" if total_gap or opening_gap else "unknown"
                return {"status": status, "blocked_date": day, "timeline": timeline, "first_shortfall": first_gap, "total_unfunded": str(total_gap.quantize(Decimal("0.01"))), "limitations": [*limitations, "Same-day receipt/payment order is unknown; supply unique integer sequence values. Earlier demonstrated shortfalls are retained."], "scenario_only": True}
            day_events = sorted(day_events, key=lambda event: int(str(event["sequence"])))
        for event in day_events:
            identity, value = str(event["id"]), money(event["amount"], "event.amount")
            match event.get("kind"):
                case "receipt":
                    target = str(event.get("fund") or "")
                    if target not in funds:
                        raise CaseError("event.fund", "unknown receiving fund")
                    assumed = event.get("status") == "assumed" and data.get("allow_assumed_receipts") is True
                    confirmed = event.get("status") == "confirmed" or assumed
                    if assumed:
                        assumed_receipts.append(identity)
                    if confirmed:
                        balances[target] += value
                    else:
                        uncertain_receipts.append(identity)
                    timeline.append({"id": identity, "date": day, "kind": "receipt", "credited": str(value if confirmed else Decimal(0)), "receipt_status": "included_scenario_assumption" if assumed else "supplied_confirmed" if confirmed else "not_spendable_unconfirmed", "allocation": {}, "balances": {key: str(balance.quantize(Decimal("0.01"))) for key, balance in balances.items()}})
                case "payment":
                    allowed = strings(event.get("allowed_funds"), "allowed_funds")
                    if not allowed or any(fund not in funds for fund in allowed):
                        raise CaseError("allowed_funds", "explicit known eligible fund ids are required")
                    min_cash = money(event.get("minimum_cash", "0"), "minimum_cash")
                    if min_cash > value:
                        raise CaseError("minimum_cash", "cannot exceed the obligation")
                    paid = {key: Decimal(0) for key in allowed}
                    mandatory_left = min_cash
                    for fund_id in order:
                        if fund_id in allowed and funds[fund_id].kind == FundKind.CASH:
                            draw = allocate(fund_id, mandatory_left)
                            mandatory_left -= draw
                            paid[fund_id] += draw
                    remaining = value - min_cash
                    for fund_id in order:
                        if fund_id in allowed:
                            draw = allocate(fund_id, remaining)
                            remaining -= draw
                            paid[fund_id] += draw
                    unfunded = remaining + mandatory_left
                    total_gap += unfunded
                    if event.get("recurring") is True:
                        cash_allowed = any(funds[key].kind == FundKind.CASH for key in allowed)
                        monthly_cash[day[:7]] += sum((paid[key] for key in paid if funds[key].kind == FundKind.CASH), Decimal(0)) + (unfunded if cash_allowed else Decimal(0))
                        unfunded_non_cash_recurring = unfunded_non_cash_recurring or bool(unfunded and not cash_allowed)
                    if unfunded and first_gap is None:
                        first_gap = {"id": identity, "date": day, "amount": str(unfunded.quantize(Decimal("0.01")))}
                    if sum(paid.values(), Decimal(0)) + unfunded != value:
                        raise CaseError("allocation", "payment conservation failed")
                    timeline.append({"id": identity, "date": day, "kind": "payment", "amount": str(value), "allocation": {key: str(draw.quantize(Decimal("0.01"))) for key, draw in paid.items()}, "unfunded": str(unfunded.quantize(Decimal("0.01"))), "balances": {key: str(balance.quantize(Decimal("0.01"))) for key, balance in balances.items()}})
                case _:
                    raise CaseError("event.kind", "expected receipt or payment")
    status = "shortfall" if total_gap or opening_gap else "funded_under_supplied_inputs"
    if limitations or assumed_receipts or (uncertain_receipts and total_gap):
        status = "conditional"
    comfort = "not_assessed"
    if data.get("monthly_cash_limit") is not None:
        limit = money(data["monthly_cash_limit"], "monthly_cash_limit")
        comfort = "fail" if any(value > limit for value in monthly_cash.values()) else "pass_under_supplied_scenario"
        if unfunded_non_cash_recurring and comfort != "fail":
            comfort = "unknown_non_cash_obligation_unfunded"
        elif not monthly_cash:
            comfort = "unknown_no_recurring_obligations_marked"
    return {"status": status, "strategy": strategy, "allocation_order": order, "timeline": timeline, "first_shortfall": first_gap, "total_unfunded": str(total_gap.quantize(Decimal("0.01"))), "opening_reserve_gap": str(opening_gap.quantize(Decimal("0.01"))), "funds_used": {key: str(value.quantize(Decimal("0.01"))) for key, value in used.items()}, "unconfirmed_receipts": uncertain_receipts, "assumed_receipts_included": assumed_receipts, "recurring_monthly_cash_need": {key: str(value.quantize(Decimal("0.01"))) for key, value in monthly_cash.items()}, "comfort_status": comfort, "limitations": [*limitations, "Supplied eligibility/dates are not independently verified; unfilled obligations remain liabilities, later receipts do not erase a historical shortfall; no automatic bridge/repayment optimization", "Monthly recurrence preserves calendar day/clamps month end, not payroll/business-day certainty. Assumed receipts are included only by explicit opt-in and keep results conditional."], "scenario_only": True}


def funding_plan(data: Record) -> Record:
    """Simulate supplied fund eligibility/reserves; never infer statutory CPF rights."""
    if data.get("compare_strategies") is True:
        return {"strategies": {strategy: _one_plan(data, strategy) for strategy in ("cash_first", "cpf_first")}, "scenario_only": True}
    return _one_plan(data, str(data.get("strategy") or "cpf_first"))


def net_exit(data: Record) -> Record:
    """Reconcile supplied exit/refund amounts; shortfall treatment requires rules."""
    required = ("sale_price", "loan_redemption", "selling_costs", "cpf_principal_refund", "cpf_accrued_refund")
    missing = [field for field in required if data.get(field) is None]
    if missing:
        return {"status": "unknown", "missing_inputs": missing, "cash_after_supplied_refunds": None}
    sale, debt, costs, principal, interest = (money(data[field], field) for field in required)
    cash = sale - debt - costs - principal - interest
    return {"status": "scenario" if cash >= 0 else "conditional_shortfall_rules_required", "equity_before_costs": str((sale - debt).quantize(Decimal("0.01"))), "cpf_refund": str((principal + interest).quantize(Decimal("0.01"))), "cash_after_supplied_refunds": str(cash.quantize(Decimal("0.01"))), "limitations": ["Refund/tax/shortfall treatment depends on applicable facts; supplied equity is not free cash, and no negative refund is silently clamped"]}
