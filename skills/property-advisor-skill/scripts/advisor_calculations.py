"""Unit-aware calculations; rules and source selection remain explicit inputs."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, TypedDict

from singapore_api import sparkline

PriceUnit = Literal["total", "psf", "monthly", "psf_month", "land_psf", "built_psf"]
Observation = dict[str, str | int | float | None]


class CalculationError(ValueError):
    """An input cannot support the requested calculation."""

    def __init__(self, operation: str, detail: str) -> None:
        self.operation = operation
        self.detail = detail
        super().__init__(f"{operation}: {detail}")


class CostTotal(TypedDict):
    subtotal: str | None
    complete: bool
    excluded: list[str]


class QuarterValue(TypedDict):
    qtr: str
    value: float


class Trend(TypedDict):
    last_8_quarters: list[QuarterValue]
    qoq_pct: float | None
    yoy_pct: float | None
    sparkline: str


def amount(raw: str | int | float | Decimal) -> Decimal:
    """Parse a finite, nonnegative quantity without binary money arithmetic."""
    try:
        value = Decimal(str(raw))
    except InvalidOperation as exc:
        raise CalculationError("amount", "expected a decimal number") from exc
    if not value.is_finite() or value < 0:
        raise CalculationError("amount", "expected a finite nonnegative number")
    return value


def price_premium(
    asking: str, asking_unit: PriceUnit, baseline: str, baseline_unit: PriceUnit,
    area_sqft: str | None = None,
) -> Decimal:
    """Compare compatible prices; total-to-PSF conversion requires known area."""
    ask, base = amount(asking), amount(baseline)
    if asking_unit != baseline_unit:
        if (asking_unit, baseline_unit) not in {("total", "psf"), ("monthly", "psf_month")}:
            raise CalculationError("premium", "incompatible area or price bases")
        if area_sqft is None or amount(area_sqft) == 0:
            raise CalculationError("premium", "known positive area is required")
        ask /= amount(area_sqft)
    if base == 0:
        raise CalculationError("premium", "baseline must be positive")
    return (ask - base) / base * 100


def cost_total(components: dict[str, str | None]) -> CostTotal:
    """Subtotal supplied components; missing components remain excluded, not zero."""
    missing = [key for key, value in components.items() if value is None]
    known = [amount(value) for value in components.values() if value is not None]
    total = sum(known, Decimal(0))
    return {"subtotal": str(total.quantize(Decimal("0.01"))) if known else None, "complete": bool(components) and not missing, "excluded": missing}


def monthly_payment(principal: str, annual_rate_pct: str, years: int) -> Decimal:
    """Level-payment illustration, not an underwriting or CPF eligibility result."""
    if not 1 <= years <= 50:
        raise CalculationError("mortgage", "years must be between 1 and 50")
    loan, rate = amount(principal), amount(annual_rate_pct) / 1200
    months = years * 12
    payment = loan / months if rate == 0 else loan * rate / (1 - (1 + rate) ** -months)
    return payment.quantize(Decimal("0.01"))


def trend_block(
    records: list[Observation], value_key: str = "value", qtr_key: str = "qtr",
    n_periods: int = 8, *, as_of: date | None = None,
) -> Trend:
    """Use completed calendar quarters only; missing periods never become zero growth."""
    if n_periods < 1:
        raise CalculationError("trend", "n_periods must be positive")
    now = as_of or date.today()
    current = now.year * 4 + (now.month - 1) // 3
    periods: dict[int, QuarterValue] = {}
    for row in records:
        label = str(row.get(qtr_key) or row.get("quarter") or "")
        matched = re.fullmatch(r"(\d{4})-Q([1-4])", label)
        if matched is None:
            raise CalculationError("trend", f"invalid quarter {label!r}")
        period = int(matched[1]) * 4 + int(matched[2]) - 1
        if period >= current:
            continue
        raw = row.get(value_key)
        if raw is None:
            continue
        if period in periods:
            raise CalculationError("trend", f"aggregate duplicate quarter {label} first")
        periods[period] = {"qtr": label, "value": float(amount(raw))}
    ordered = sorted(periods)[-n_periods:]
    series = [periods[key] for key in ordered]

    def change(offset: int) -> float | None:
        if not ordered:
            return None
        prior = periods.get(ordered[-1] - offset)
        if prior is None or prior["value"] == 0:
            return None
        return round((series[-1]["value"] / prior["value"] - 1) * 100, 1)

    return {"last_8_quarters": series, "qoq_pct": change(1), "yoy_pct": change(4), "sparkline": sparkline([row["value"] for row in series])}
