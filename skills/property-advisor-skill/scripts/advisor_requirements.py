"""Bounded semantic constraints over typed, sourced facts; no arbitrary expressions."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Final, Literal, assert_never

from advisor_calculations import amount
from advisor_records import CaseError, JSONValue, Record, record, rows, strings

Outcome = Literal["pass", "fail", "unknown", "not_applicable"]


class Kind(StrEnum):
    ALL = "all"
    ANY = "any"
    AGE = "age"
    READY = "ready_by"
    DATE_WINDOW = "date_window"
    NUMBER = "number"
    MEMBER = "one_of"
    WHEN = "when"
    PREFERENCE = "preference"


@dataclass(frozen=True, slots=True)
class Check:
    result: Outcome
    reason: str
    used_fields: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def as_record(self) -> Record:
        return {"result": self.result, "reason": self.reason, "used_fields": list(self.used_fields), "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True, slots=True)
class Window:
    first: date
    last: date


def date_window(value: JSONValue) -> Window:
    """Preserve year/month precision and explicit earliest/latest intervals."""
    try:
        match value:
            case dict() as data:
                first, last = date.fromisoformat(str(data["earliest"])), date.fromisoformat(str(data["latest"]))
                if first > last:
                    raise CaseError("date", "earliest exceeds latest")
                return Window(first, last)
            case str() as label:
                match len(label):
                    case 4:
                        return Window(date(int(label), 1, 1), date(int(label), 12, 31))
                    case 7:
                        year, month = map(int, label.split("-"))
                        return Window(date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1]))
                    case _:
                        point = date.fromisoformat(label)
                        return Window(point, point)
            case _:
                raise CaseError("date", "expected ISO date, month, year or date window")
    except (ValueError, KeyError) as exc:
        raise CaseError("date", "invalid date or interval") from exc


def exact_date(value: JSONValue) -> date:
    window = date_window(value)
    if window.first != window.last:
        raise CaseError("reference_date", "an exact date is required")
    return window.first


def fact(facts: Record, field: str) -> Record:
    value = facts.get(field)
    return {"state": "unknown", "value": None} if value is None else record(value, field)


def _observed(data: Record) -> bool:
    return data.get("state") == "known" and data.get("value") is not None


def _check(result: Outcome, reason: str, fields: list[str], facts: Record) -> Check:
    refs = {ref for field in fields for ref in strings(fact(facts, field).get("evidence_ids", []), "fact.evidence_ids")}
    return Check(result, reason, tuple(fields), tuple(sorted(refs)))


def _group(kind: Kind, children: list[Check]) -> Check:
    values = [child.result for child in children if child.result != "not_applicable"]
    result: Outcome = "unknown"
    if values:
        match kind:
            case Kind.ALL:
                result = "fail" if "fail" in values else "unknown" if "unknown" in values else "pass"
            case Kind.ANY:
                result = "pass" if "pass" in values else "unknown" if "unknown" in values else "fail"
            case _:
                raise CaseError("group", "only all/any are group operators")
    return Check(result, "; ".join(child.reason for child in children) or "No applicable conditions", tuple(sorted({field for child in children for field in child.used_fields})), tuple(sorted({ref for child in children for ref in child.evidence_ids})))


CONVERSIONS: Final = {("sqm", "sqft"): Decimal(1) / Decimal("0.09290304"), ("sqft", "sqm"): Decimal("0.09290304"), ("km", "m"): Decimal(1000), ("m", "km"): Decimal("0.001"), ("hours", "min"): Decimal(60), ("min", "hours"): Decimal(1) / 60}


def _number(condition: Record, data: Record) -> tuple[Outcome, str]:
    target_unit, observed_unit = str(condition.get("unit") or ""), str(data.get("unit") or "")
    if not target_unit:
        raise CaseError("condition.unit", "numeric conditions require explicit units")
    if condition.get("basis") is not None and condition["basis"] != data.get("basis"):
        return "unknown", "Measurement bases differ; no inferred conversion of usable/land/strata area or routed distance"
    factor = Decimal(1) if target_unit == observed_unit else CONVERSIONS.get((observed_unit, target_unit))
    if factor is None:
        return "unknown", "Units are incompatible or unverified"
    value = data["value"]
    match value:
        case dict() as interval:
            low = amount(str(interval["min"])) * factor if interval.get("min") is not None else None
            high = amount(str(interval["max"])) * factor if interval.get("max") is not None else None
        case str() | int() | float():
            low = amount(str(value)) * factor
            high = None if data.get("price_kind") in ("starting", "indicative_starting") else low
        case _:
            return "unknown", "Numeric value is unavailable"
    if low is not None and high is not None and low > high:
        raise CaseError("fact.value", "numeric interval is reversed")
    target = amount(str(condition.get("value")))
    match condition.get("op"):
        case "min":
            result = "pass" if low is not None and low >= target else "fail" if high is not None and high < target else "unknown"
        case "max":
            result = "pass" if high is not None and high <= target else "fail" if low is not None and low > target else "unknown"
        case "eq":
            result = "pass" if low == high == target else "fail" if (low is not None and low > target) or (high is not None and high < target) else "unknown"
        case _:
            raise CaseError("condition.op", "expected min, max or eq")
    return result, "Compared compatible sourced value/interval; no favorable default for a missing bound"


def evaluate(condition: Record, facts: Record, reference: date, *, _depth: int = 0) -> Check:
    """Evaluate normalized requirements; confidence/authority remain a separate gate."""
    if _depth > 12:
        raise CaseError("condition", "condition nesting exceeds twelve levels")
    try:
        kind = Kind(str(condition.get("kind")))
    except ValueError as exc:
        raise CaseError("condition.kind", "unsupported condition kind") from exc
    match kind:
        case Kind.ALL | Kind.ANY:
            return _group(kind, [evaluate(child, facts, reference, _depth=_depth + 1) for child in rows(condition.get("conditions"), "conditions")])
        case Kind.WHEN:
            applicability = evaluate(record(condition.get("if"), "condition.if"), facts, reference, _depth=_depth + 1)
            match applicability.result:
                case "pass":
                    result = evaluate(record(condition.get("then"), "condition.then"), facts, reference, _depth=_depth + 1)
                    return Check(result.result, result.reason, tuple(sorted(set(applicability.used_fields + result.used_fields))), tuple(sorted(set(applicability.evidence_ids + result.evidence_ids))))
                case "fail":
                    return Check("not_applicable", "Explicit applicability condition is false", applicability.used_fields, applicability.evidence_ids)
                case "unknown" | "not_applicable":
                    return Check("unknown", "Applicability is unresolved", applicability.used_fields, applicability.evidence_ids)
                case unreachable:
                    assert_never(unreachable)
        case Kind.AGE:
            fields = ["completion_status", "actual_top"]
            status = fact(facts, "completion_status")
            if not _observed(status):
                return _check("unknown", "Completion status is unknown", fields, facts)
            match status["value"]:
                case "uncompleted" | "under_construction" | "planned":
                    allowed = condition.get("include_uncompleted") is True
                    return _check("pass" if allowed else "fail", "Future-home age branch; occupancy must be evaluated separately", ["completion_status"], facts)
                case "completed":
                    data = fact(facts, "actual_top")
                    if not _observed(data):
                        return _check("unknown", "Actual TOP is not established", fields, facts)
                    window = date_window(data["value"])
                    as_of = exact_date(condition["reference_date"]) if "reference_date" in condition else reference
                    try:
                        years = int(str(condition["max_years"]))
                        if years < 0:
                            raise CaseError("max_years", "must be nonnegative")
                        year = as_of.year - years
                        cutoff = as_of.replace(year=year, day=min(as_of.day, calendar.monthrange(year, as_of.month)[1]))
                    except (ValueError, KeyError) as exc:
                        raise CaseError("max_years", "invalid age/reference date") from exc
                    result: Outcome = "unknown"
                    if window.first <= reference and window.first <= as_of:
                        # Completed status constrains a partial current-year date to today;
                        # an explicit future actual date remains conflicting, not negative age.
                        last = min(window.last, reference, as_of)
                        result = "pass" if window.first >= cutoff else "fail" if last < cutoff else "unknown"
                    return _check(result, "Actual-date interval evaluated at the explicit reference date", fields, facts)
                case _:
                    return _check("unknown", "Completion status conflicts or is unsupported", fields, facts)
        case Kind.READY:
            field = str(condition.get("field") or "occupancy_date")
            data = fact(facts, field)
            if not _observed(data):
                return _check("unknown", "Practical occupancy is unknown; expected TOP is not substituted", [field], facts)
            window, deadline = date_window(data["value"]), exact_date(condition.get("date"))
            result = "pass" if window.last <= deadline else "fail" if window.first > deadline else "unknown"
            return _check(result, "Practical occupancy window checked against deadline", [field], facts)
        case Kind.DATE_WINDOW:
            field = str(condition.get("field") or "")
            data = fact(facts, field)
            if not field or not _observed(data):
                return _check("unknown", "Date field/precision is unknown", [field] if field else [], facts)
            observed = date_window(data["value"])
            first = date_window(condition.get("earliest")).first
            last = date_window(condition.get("latest")).last
            if first > last:
                raise CaseError("condition", "date window is reversed")
            result = "pass" if first <= observed.first <= observed.last <= last else "fail" if observed.last < first or observed.first > last else "unknown"
            return _check(result, "Compared the explicit inclusive calendar/date window, not rolling age", [field], facts)
        case Kind.NUMBER | Kind.MEMBER | Kind.PREFERENCE:
            field = str(condition.get("field") or "")
            if not field:
                raise CaseError("condition.field", "field is required")
            data = fact(facts, field)
            if kind == Kind.PREFERENCE:
                return _check("not_applicable", "Preference has no hard cutoff; rank only with appropriate known inputs", [field], facts)
            if not _observed(data):
                return _check("unknown", f"{field} is unknown/conflicting", [field], facts)
            if kind == Kind.MEMBER:
                result = "pass" if data["value"] in strings(condition.get("values"), "condition.values") else "fail"
                return _check(result, "Compared the explicit allowed values", [field], facts)
            result, reason = _number(condition, data)
            return _check(result, reason, [field], facts)
        case unreachable:
            assert_never(unreachable)
