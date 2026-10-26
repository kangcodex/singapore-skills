"""Policy tables + rule calculators for the agent mode.

Every figure is read from references/policy-tables.json (dated, sourced). A policy
change is a data edit. Money is Decimal throughout.
"""
import json
from decimal import Decimal
from pathlib import Path

from agent_money import D, ZERO, whole_dollars_down
from advisor_records import JSONValue

POLICY_PATH = Path(__file__).resolve().parent.parent / "references" / "policy-tables.json"
STATUSES = ("verified", "unverified")


def load_policy(path=None) -> dict:
    with open(path or POLICY_PATH, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def validate_policy(policy: dict) -> list:
    """Return a list of problems; empty means every item is dated and sourced."""
    errors = []
    for name, item in policy.get("items", {}).items():
        if not item.get("as_of"):
            errors.append(f"{name}: missing as_of")
        if not str(item.get("source_url", "")).startswith("https://"):
            errors.append(f"{name}: missing https source_url")
        status = item.get("status")
        if status not in STATUSES:
            errors.append(f"{name}: status must be one of {STATUSES}")
        if status == "unverified" and not item.get("unverified_reason"):
            errors.append(f"{name}: unverified without unverified_reason")
    return errors


def unverified_items(policy: dict) -> list:
    """Include nested applicability uncertainty, retaining its full field path."""
    def walk(value: JSONValue | Decimal, path: str) -> list[tuple[str, str]]:
        found = []
        if isinstance(value, dict):
            if value.get("status") == "unverified":
                found.append((path, str(value.get("unverified_reason", "Verification is unresolved"))))
            for name, child in value.items():
                if isinstance(child, (dict, list)):
                    found.extend(walk(child, f"{path}.{name}"))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found.extend(walk(child, f"{path}.{index}"))
        return found
    return [item for name, value in policy["items"].items() for item in walk(value, name)]


def _item(policy: dict, name: str) -> dict:
    return policy["items"][name]


def _tiered(amount: Decimal, tiers: list) -> Decimal:
    """Marginal tiers of {width, rate}; width None = unbounded remainder."""
    remaining, total = D(amount), ZERO
    for tier in tiers:
        if remaining <= 0:
            break
        slab = remaining if tier["width"] is None else min(remaining, D(tier["width"]))
        total += slab * D(tier["rate"])
        remaining -= slab
    return total


def bsd(price: Decimal, policy: dict) -> Decimal:
    return whole_dollars_down(_tiered(price, _item(policy, "bsd")["tiers"]))


def absd(price: Decimal, buyers: list, policy: dict) -> Decimal:
    """ABSD on the full price at the highest rate among joint buyers."""
    rates = _item(policy, "absd")["rates"]
    top = ZERO
    for b in buyers:
        count = min(int(b.get("existing_properties", 0)) + 1, 3)
        top = max(top, D(rates[b["residency"]][str(count)]))
    return whole_dollars_down(D(price) * top)


def property_tax(annual_value: Decimal, policy: dict) -> Decimal:
    return whole_dollars_down(_tiered(annual_value, _item(policy, "property_tax_owner_occupier")["tiers"]))


def max_tenure_years(is_hdb: bool, policy: dict) -> int:
    return _item(policy, "ltv_bank")["max_tenure_years"]["hdb" if is_hdb else "non_hdb"]


def ltv_limit(outstanding_loans: int, tenure_years: int, loan_end_age: int,
              is_hdb: bool, policy: dict) -> tuple:
    """(max LTV, minimum cash down payment as fraction of price) for a bank loan."""
    item = _item(policy, "ltv_bank")
    row = item["by_outstanding_loans"][str(min(int(outstanding_loans), 2))]
    key = "hdb" if is_hdb else "non_hdb"
    lower = (tenure_years > item["lower_ltv_if_tenure_over_years"][key]
             or loan_end_age > item["lower_ltv_if_loan_ends_after_age"])
    prefix = "lower" if lower else "standard"
    return D(row[f"{prefix}_ltv"]), D(row[f"{prefix}_min_cash"])


def stress_rate(rate: Decimal, is_hdb_loan: bool, policy: dict) -> Decimal:
    item = _item(policy, "stress_rate")
    floor = item["hdb_loan_assessment_floor"] if is_hdb_loan else item["floor"]
    return max(D(rate), D(floor))


def _ratio_check(limit: Decimal, numerator: Decimal, income: Decimal) -> dict:
    income = D(income)
    if income <= 0:
        return {"pass": False, "ratio": None, "limit": limit}
    ratio = (numerator / income).quantize(Decimal("0.0001"))
    return {"pass": numerator / income <= limit, "ratio": ratio, "limit": limit}


def tdsr_check(income: Decimal, other_debts: Decimal, instalment: Decimal, policy: dict) -> dict:
    return _ratio_check(D(_item(policy, "tdsr")["max_ratio"]), D(other_debts) + D(instalment), income)


def msr_check(income: Decimal, instalment: Decimal, policy: dict) -> dict:
    return _ratio_check(D(_item(policy, "msr")["max_ratio"]), D(instalment), income)


def ehg(avg_monthly_income: Decimal, policy: dict) -> Decimal:
    item = _item(policy, "ehg")
    if D(avg_monthly_income) > D(item["income_ceiling"]):
        return ZERO
    for row in item["table"]:
        if D(avg_monthly_income) <= D(row["up_to"]):
            return D(row["grant"])
    return ZERO
