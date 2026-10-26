"""Property-specific schedule parsing for the legacy financial scenario engine."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from advisor_calculations import amount
from advisor_records import CaseError, JSONValue, Record, record, rows


@dataclass(frozen=True, slots=True)
class Stage:
    identity: str
    label: str
    when: date
    amount: Decimal
    cash_only: bool


def add_months(start: date, months: int) -> date:
    year_delta, month = divmod(start.month - 1 + months, 12)
    year = start.year + year_delta
    return start.replace(year=year, month=month + 1, day=min(start.day, calendar.monthrange(year, month + 1)[1]))


def day(value: JSONValue, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise CaseError(field, "expected an exact ISO date") from exc


def milestone(option: Record, name: str, default: date) -> date:
    values = record(option.get("milestones", {}), "milestones")
    supplied = values.get(name)
    if supplied is None and name == "top":
        supplied = option.get("expected_top_date")
    return default if supplied is None else day(supplied, f"milestones.{name}")


def progressive_stages(option: Record, defaults: list[Record], start: date, price: Decimal) -> list[Stage]:
    """Use supplied exact schedule or explicit illustrative defaults, never ignore TOP."""
    supplied = option.get("payment_schedule")
    source = rows(supplied, "payment_schedule") if supplied is not None else defaults
    result: list[Stage] = []
    identities: set[str] = set()
    for entry in source:
        identity = str(entry.get("id") or "")
        if not identity or identity in identities:
            raise CaseError("payment_schedule", "stage ids must be nonempty and unique")
        identities.add(identity)
        default = day(entry["date"], "stage.date") if "date" in entry else add_months(start, int(str(entry.get("month_offset", "0"))))
        when = milestone(option, identity, default)
        value = amount(str(entry["amount"])) if "amount" in entry else (price * amount(str(entry["pct"]))).quantize(Decimal("0.01"))
        result.append(Stage(identity, str(entry.get("label") or identity.replace("_", " ")), when, value, entry.get("cash_only", False) is True))
    if not {"booking", "sp_signing", "top", "csc"}.issubset(identities):
        raise CaseError("payment_schedule", "booking, sp_signing, top and csc stages are required")
    if result[0].when < start or any(a.when > b.when for a, b in zip(result, result[1:])):
        raise CaseError("payment_schedule", "dates must be chronological; supply actual stage dates when overriding TOP")
    difference = price - sum((stage.amount for stage in result), Decimal(0))
    if difference and all("amount" not in entry for entry in source) and abs(difference) <= Decimal("0.01") * len(source):
        last = result[-1]
        result[-1] = Stage(last.identity, last.label, last.when, last.amount + difference, last.cash_only)
    if sum((stage.amount for stage in result), Decimal(0)) != price:
        raise CaseError("payment_schedule", "stage amounts must reconcile exactly to purchase price")
    if option.get("expected_top_date") is not None:
        top = next(stage for stage in result if stage.identity == "top")
        if top.when != day(option["expected_top_date"], "expected_top_date"):
            raise CaseError("payment_schedule", "TOP metadata conflicts with supplied schedule")
    return result
