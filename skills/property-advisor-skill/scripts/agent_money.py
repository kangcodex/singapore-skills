"""Decimal money helpers for the agent mode. Stdlib only; no floats.

Loan maths: level monthly payment and outstanding balance, rounded to cents.
"""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
CENT = Decimal("0.01")


def D(value) -> Decimal:
    """Coerce int/str/Decimal to Decimal. Floats are rejected on purpose."""
    if isinstance(value, float):
        raise TypeError("floats are not allowed for money values; pass str or Decimal")
    return value if isinstance(value, Decimal) else Decimal(str(value))


def cents(value: Decimal) -> Decimal:
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def whole_dollars_down(value: Decimal) -> Decimal:
    """Stamp duties are rounded down to the nearest dollar."""
    return D(value).quantize(Decimal("1"), rounding=ROUND_DOWN)


def _level_payment(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    n = years * 12
    r = annual_rate / 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def monthly_payment(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    if principal <= 0 or years <= 0:
        return cents(ZERO)
    return cents(_level_payment(D(principal), D(annual_rate), years))


def loan_balance(principal: Decimal, annual_rate: Decimal, years: int, months_paid: int) -> Decimal:
    """Outstanding principal after `months_paid` level payments."""
    principal, annual_rate = D(principal), D(annual_rate)
    n = years * 12
    if principal <= 0 or months_paid >= n:
        return cents(ZERO)
    pay = _level_payment(principal, annual_rate, years)
    r = annual_rate / 12
    if r == 0:
        bal = principal - pay * months_paid
    else:
        growth = (1 + r) ** months_paid
        bal = principal * growth - pay * (growth - 1) / r
    return cents(max(bal, ZERO))
