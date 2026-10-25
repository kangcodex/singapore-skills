"""Whitelisted assessments and immutable, case-referenced recomputation."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from typing import Final

from advisor_comfort import assess_comfort
from advisor_documents import assess_documents
from advisor_funding import funding_plan, net_exit
from advisor_finance import assess_cost_comparison, assess_loan_plan
from advisor_location import assess_amenities, assess_location
from advisor_market import assess_comparables, assess_scenarios
from advisor_questions import question_plan, watch_specification
from advisor_records import CaseError, JSONValue, Record, record, rows
from advisor_screening import assess_requirements, combined_facts
from advisor_search import assess_search

ASSESSORS: Final[dict[str, Callable[[Record], Record]]] = {"question": question_plan, "requirements": assess_requirements, "location": assess_location, "amenities": assess_amenities, "documents": assess_documents, "comfort": assess_comfort, "funding": funding_plan, "loan_plan": assess_loan_plan, "cost_comparison": assess_cost_comparison, "exit": net_exit, "comparables": assess_comparables, "scenarios": assess_scenarios, "search": assess_search, "watch": watch_specification}
ENGINE_VERSION: Final = "question-led-1"
INPUT_FIELDS: Final = {
    "question": {"kind", "kinds", "known_inputs", "request"},
    "requirements": {"requirements", "facts", "as_of"},
    "location": {"as_of", "origin_id", "limits", "routes"},
    "amenities": {"as_of", "cohort", "items"},
    "documents": {"as_of", "candidate_id", "property_id", "documents", "claims"},
    "comfort": {"household", "layout", "future_scenarios"},
    "funding": {"currency", "as_of", "funds", "events", "recurring", "strategy", "compare_strategies", "allow_assumed_receipts", "monthly_cash_limit"},
    "loan_plan": {"start_date", "buyers", "household", "option", "assumptions", "town"},
    "cost_comparison": {"start_date", "buyers", "household", "options", "assumptions", "town"},
    "exit": {"sale_price", "loan_redemption", "selling_costs", "cpf_principal_refund", "cpf_accrued_refund"},
    "comparables": {"as_of", "subject", "observations", "area_tolerance_pct", "window_start"},
    "scenarios": {"entry_price", "years", "scenarios", "nonrecoverable_costs", "fixed_selling_costs", "selling_cost_rate_decimal"},
    "search": {"as_of", "coverage", "requirements", "candidates", "evidence"},
    "watch": {"explicit_request", "targets", "triggers", "expiry", "frequency", "channel", "as_of"},
}


def assess(kind: str, data: Record) -> Record:
    try:
        handler = ASSESSORS[kind]
    except KeyError as exc:
        raise CaseError("assessment.kind", "unsupported assessment") from exc
    unmapped = set(data) - INPUT_FIELDS[kind] - {"example_notice", "metadata", "notes"}
    if unmapped:
        raise CaseError("assessment.input", "Unmapped inputs would be ignored: " + ", ".join(sorted(unmapped)))
    return handler(data)


def resolve_pointer(case: Record, pointer: str) -> JSONValue:
    """Read a case JSON Pointer, never an external path, file or executable expression."""
    if not pointer.startswith("/"):
        raise CaseError("input_ref", "expected a case JSON Pointer beginning with /")
    current: JSONValue = case
    for part in pointer[1:].split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        match current:
            case dict() as mapping:
                if token == "value" and "state" in mapping and mapping["state"] not in ("known", "confirmed"):
                    return None
                if token not in mapping:
                    raise CaseError("input_ref", f"case field not found: {pointer}")
                current = mapping[token]
            case list() as sequence:
                if not token.isdecimal() or int(token) >= len(sequence):
                    raise CaseError("input_ref", f"invalid list index: {pointer}")
                current = sequence[int(token)]
            case _:
                raise CaseError("input_ref", f"cannot traverse scalar: {pointer}")
    return deepcopy(current)


def _set_pointer(parameters: Record, pointer: str, value: JSONValue) -> None:
    """Set an existing nested input slot; no path is interpreted as a file."""
    tokens = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    current: JSONValue = parameters
    for token in tokens[:-1]:
        match current:
            case dict() as mapping:
                if token not in mapping:
                    raise CaseError("input_refs", "nested target must already exist")
                current = mapping[token]
            case list() as sequence:
                if not token.isdecimal() or int(token) >= len(sequence):
                    raise CaseError("input_refs", "invalid nested target index")
                current = sequence[int(token)]
            case _:
                raise CaseError("input_refs", "cannot traverse scalar target")
    token = tokens[-1]
    match current:
        case dict() as mapping:
            if token not in mapping:
                raise CaseError("input_refs", "nested target must already exist")
            mapping[token] = value
        case list() as sequence:
            if not token.isdecimal() or int(token) >= len(sequence):
                raise CaseError("input_refs", "invalid nested target index")
            sequence[int(token)] = value
        case _:
            raise CaseError("input_refs", "cannot set scalar target")


def _fingerprint(value: JSONValue) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _changes(previous: JSONValue, current: JSONValue, path: str = "") -> list[str]:
    if type(previous) is type(current) and previous == current:
        return []
    if isinstance(previous, dict) and isinstance(current, dict):
        result: list[str] = []
        for key in sorted(previous.keys() | current.keys()):
            child = f"{path}/{key.replace('~', '~0').replace('/', '~1')}"
            result.extend(_changes(previous.get(key), current.get(key), child))
        return result
    return [path or "/"]


def _inputs_snapshot(case: Record) -> Record:
    result = deepcopy({key: value for key, value in case.items() if key not in {"assessment_results", "candidate_facts", "change_summary", "constraint_assessments", "history", "version", "supersedes", "recommendations", "summary", "summary_status"}})
    requirements = rows(record(result.get("buyer_brief"), "buyer_brief").get("requirements"), "requirements")
    if any(item.get("condition") is not None for item in requirements):
        for candidate in rows(result.get("candidates"), "candidates"):
            if candidate.get("fit") == "rejected" and candidate.get("rejection_origin") != "computed_constraints":
                candidate["manual_exclusion"] = True
            for field in ("computed_requirement_assessment", "checks", "rejection_origin", "fit"):
                candidate.pop(field, None)
    return result


def evaluate_case(source: Record, previous: Record | None = None) -> Record:
    """Compute current semantic checks/analyses without overwriting input or prior files."""
    case = deepcopy(source)
    brief = record(case.get("buyer_brief"), "buyer_brief")
    requirements = rows(brief.get("requirements"), "requirements")
    properties = {str(item.get("id")): item for item in rows(case.get("properties"), "properties")}
    candidate_facts: Record = {}
    for candidate in rows(case.get("candidates"), "candidates"):
        identity = str(candidate.get("id") or "")
        facts = combined_facts(properties.get(str(candidate.get("property_id")), {}), candidate)
        candidate_facts[identity] = facts
        if any(requirement.get("condition") is not None for requirement in requirements):
            result = assess_requirements({"as_of": case.get("research_date"), "requirements": requirements, "facts": facts})
            candidate["computed_requirement_assessment"] = result
            candidate["checks"] = rows(result["checks"], "checks")
            if result["status"] == "fails_supplied_constraints":
                candidate["fit"] = "rejected"
                candidate["rejection_origin"] = "computed_constraints"
            elif result["status"] == "conditional" and candidate.get("fit") == "verified":
                candidate["fit"] = "conditional"
            elif candidate.get("rejection_origin") == "computed_constraints":
                candidate["fit"] = "conditional"
                candidate.pop("rejection_origin", None)
    # rows() preserves record references, but callers' source is protected by deepcopy.
    case["candidate_facts"] = candidate_facts
    results: Record = {}
    case["assessment_results"] = results
    ids: set[str] = set()
    for request in rows(case.get("analysis_requests", []), "analysis_requests"):
        identity = str(request.get("id") or "")
        if not identity or identity in ids:
            raise CaseError("analysis_request.id", "nonempty unique ids required")
        ids.add(identity)
        kind = str(request.get("kind") or "")
        parameters = deepcopy(record(request.get("input", {}), "analysis.input"))
        refs = record(request.get("input_refs", {}), "analysis.input_refs")
        for field, pointer in sorted(refs.items(), key=lambda item: (item[0].startswith("/"), item[0].count("/"), item[0])):
            if not isinstance(pointer, str):
                raise CaseError("input_ref", "pointer must be a string")
            resolved = resolve_pointer(case, pointer)
            if field.startswith("/"):
                _set_pointer(parameters, field, resolved)
            else:
                parameters[field] = resolved
        result = assess(kind, parameters)
        results[identity] = {"kind": kind, "engine_version": ENGINE_VERSION, "input_fingerprint": _fingerprint({"engine": ENGINE_VERSION, "kind": kind, "input": parameters}), "input_refs": refs, "input_scope": "current_case_references" if refs else "snapshot_only", "assessment": result}
    if previous is not None:
        paths = _changes(_inputs_snapshot(previous), _inputs_snapshot(source))
        old_results = record(previous.get("assessment_results", {}), "previous assessment_results")
        changed = [identity for identity, value in results.items() if old_results.get(identity) != value]
        case["change_summary"] = {"changed_input_paths": paths, "recomputed_assessments": list(results), "changed_assessments": changed, "superseded_version": previous.get("version"), "snapshot_warnings": [identity for identity, value in results.items() if record(value, identity).get("input_scope") == "snapshot_only" and paths], "reason": "Results were recomputed from current referenced inputs; prior records were not overwritten. Snapshot-only inputs need explicit refresh if case facts changed."}
        if paths:
            if previous.get("summary") and source.get("summary") == previous.get("summary"):
                case["summary_status"] = "superseded_pending_reassessment"
            old_recommendations = {str(item.get("id")): item for item in rows(previous.get("recommendations", []), "recommendations")}
            for recommendation in rows(case.get("recommendations", []), "recommendations"):
                if old_recommendations.get(str(recommendation.get("id"))) == recommendation:
                    recommendation["status"] = "superseded_pending_reassessment"
    return case
