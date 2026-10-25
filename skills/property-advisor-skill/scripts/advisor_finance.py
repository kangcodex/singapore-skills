"""Explicit bridge to legacy financial scenarios, with their limitations intact."""
from __future__ import annotations

import agent_cashflow
import agent_compare
import agent_policy
from advisor_records import CaseError, Record, record, rows


def _scenario(data: Record, multiple: bool) -> None:
    if not data.get("start_date"):
        raise CaseError("start_date", "dated scenario start required")
    buyers = rows(data.get("buyers"), "buyers")
    if not buyers:
        raise CaseError("buyers", "buyer facts required for underwriting scenarios")
    for buyer in buyers:
        if any(buyer.get(field) is None for field in ("age", "residency", "monthly_income")):
            raise CaseError("buyers", "age, residency and monthly income are material to this loan scenario")
    options = rows(data.get("options"), "options") if multiple else [record(data.get("option"), "option")]
    for option in options:
        if option.get("category") not in agent_cashflow.CATEGORIES:
            raise CaseError("option.category", "Use explicit supplied funding events for new-HDB/landed or other unsupported default models; do not relabel them as a condo")
        if option.get("price") is None:
            raise CaseError("option.price", "price required")


def assess_loan_plan(data: Record) -> Record:
    _scenario(data, False)
    return agent_cashflow.plan(data, agent_policy.load_policy())


def assess_cost_comparison(data: Record) -> Record:
    _scenario(data, True)
    result = agent_compare.compare(data, agent_policy.load_policy())
    result["scope"] = "Modelled costs only; financial/household/timing failures must be gated before a recommendation; actual dates and funding balances require the event ledger"
    return result
