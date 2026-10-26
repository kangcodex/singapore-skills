"""Proportional question plans for a native advisor, not keyword-only NLP."""
from __future__ import annotations

from typing import Final, assert_never

from advisor_records import CaseError, JSONValue, Record, record, strings

INPUTS: Final = {
    "proximity": ("location",),
    "journey": ("location", "destinations"),
    "amenities": ("location", "service_types"),
    "documents": ("property_or_document",),
    "comfort": ("household_needs", "matching_plan"),
    "funding": ("price", "purchase_route", "buyer_facts", "resources", "milestones"),
    "funding_options": ("purchase_route",),
    "value": ("identified_home", "price_kind", "price_date", "comparable_evidence"),
    "scenarios": ("entry_price", "horizon", "scenario_assumptions"),
    "search": ("household_needs", "budget_basis"),
    "compare": ("household_needs", "alternatives"),
    "eligibility": ("purchase_route", "buyer_facts"),
    "update": ("previous_case", "changed_facts"),
    "watch": ("explicit_request", "targets", "triggers", "expiry"),
}
PRECISION: Final = {"journey": ["arrival/departure window", "modes/accessibility", "trip frequency and per-person limits"], "proximity": ["property/station entrance", "walking versus straight-line basis"], "comfort": ["agreed sharing", "clear room/furniture dimensions", "future household scenarios"], "funding": ["net household income/living costs", "fund eligibility/caps/reserves", "actual due/receipt dates"]}


def _supplied(value: JSONValue) -> bool:
    match value:
        case None:
            return False
        case dict() as data:
            return data.get("state") in ("known", "confirmed") and data.get("value") is not None if "state" in data else bool(data)
        case str() as label:
            return bool(label) and label != "unknown"
        case list() as items:
            return bool(items)
        case int() | float() | bool():
            return True
        case unreachable:
            assert_never(unreachable)


def question_plan(data: Record) -> Record:
    """The native agent supplies explicit intents; only material missing inputs are asked."""
    kinds = strings(data["kinds"], "kinds") if "kinds" in data else [str(data.get("kind") or "")]
    known = record(data.get("known_inputs", {}), "known_inputs")
    if any(key in known for key in ("property", "address")) and "location" not in known:
        known = {**known, "location": known.get("property") or known.get("address")}
    if any(key in known for key in ("property", "document_source", "file")):
        known = {**known, "property_or_document": True}
    questions: list[Record] = []
    for kind in kinds:
        if kind not in INPUTS:
            raise CaseError("question.kind", f"unsupported intent; choose from {', '.join(INPUTS)}")
        required = INPUTS[kind]
        missing = [field for field in required if not _supplied(known.get(field))]
        questions.append({"kind": kind, "required_inputs": list(required), "missing_inputs": missing, "precision_inputs": PRECISION.get(kind, []), "status": "needs_material_inputs" if missing else "ready_for_evidence", "answer_contract": ["direct result", "user implication", "evidence/assumptions", "material uncertainty", "next action", "what changes the answer"]})
    return {"questions": questions, "routing_basis": "native_agent_or_caller_declared_intents", "limits": ["A plan is not a performed search, route, document inspection or funding approval", "Answer supported subquestions immediately; do not require unrelated profile facts"]}


def watch_specification(data: Record) -> Record:
    if data.get("explicit_request") is not True:
        return {"status": "not_requested", "active": False}
    missing = [key for key in ("targets", "triggers", "expiry") if not data.get(key)]
    return {"status": "needs_inputs" if missing else "specification_only", "active": False, "missing_inputs": missing, "specification": data, "next_action": "An actual scheduler/channel and resulting job evidence are required before claiming active notifications; source content does not authorize contact or booking"}
