"""Validate supplied route/amenity evidence without inventing a live provider."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from advisor_calculations import amount
from advisor_records import CaseError, Record, rows, strings
from advisor_requirements import evaluate, exact_date


def evidence_problem(item: Record, as_of: date) -> str | None:
    if not item.get("source") or not item.get("retrieved_at"):
        return "Source and retrieval date are required"
    if item.get("access_status") in ("blocked", "partial", "unavailable", "not_attempted"):
        return "Access/extraction is incomplete"
    if exact_date(item["retrieved_at"]) > as_of:
        return "Evidence retrieval is after the assessment date"
    if item.get("valid_until") is not None and exact_date(item["valid_until"]) < as_of:
        return "Evidence validity has expired"
    return None


def _route_check(route: Record, limit: Record, as_of: date) -> Record:
    problem = evidence_problem(route, as_of)
    horizon = str(limit.get("horizon") or "current")
    if route.get("horizon") != horizon:
        problem = "Current and future networks are not interchangeable"
    if horizon == "current" and route.get("service_status") != "operating":
        problem = "Current operation is not established"
    if horizon == "future" and route.get("service_status") not in ("planned", "operating"):
        problem = "Future service status is not established"
    if limit.get("allowed_modes") is not None:
        modes = strings(limit["allowed_modes"], "allowed_modes")
        mode = route.get("mode")
        if mode not in modes:
            problem = "Requested transport mode is missing or mismatched"
    if limit.get("travel_window") is not None and route.get("travel_window") != limit["travel_window"]:
        problem = "Requested day/time window does not match this journey observation"
    if limit.get("allowed_primary_lines") is not None:
        lines = strings(limit["allowed_primary_lines"], "allowed_primary_lines")
        if route.get("primary_line") not in lines:
            return {"route_id": route.get("id"), "result": "fail" if route.get("primary_line") else "unknown", "reason": "Primary access line is outside/unknown for the stated requirement; transfer lines are separate", "horizon": horizon}
    if problem:
        return {"route_id": route.get("id"), "result": "unknown", "reason": problem, "horizon": horizon}
    checks: list[Record] = []
    if limit.get("max_walk_m") is not None:
        routed = route.get("measurement") == "routed_walk" and route.get("endpoint_scope") == "entrance_to_entrance"
        facts = {"walk": {"state": "known" if routed and route.get("distance_m") is not None else "unknown", "value": route.get("distance_m"), "unit": "m", "basis": "routed_walk", "evidence_ids": [str(route.get("id") or "route")]}}
        checks.append(evaluate({"kind": "number", "field": "walk", "op": "max", "value": limit["max_walk_m"], "unit": "m", "basis": "routed_walk"}, facts, as_of).as_record())
    if limit.get("max_walk_minutes") is not None:
        routed = route.get("measurement") == "routed_walk" and route.get("endpoint_scope") == "entrance_to_entrance"
        facts = {"walk_time": {"state": "known" if routed and route.get("minutes") is not None else "unknown", "value": route.get("minutes"), "unit": "min", "basis": "routed_walk"}}
        checks.append(evaluate({"kind": "number", "field": "walk_time", "op": "max", "value": limit["max_walk_minutes"], "unit": "min", "basis": "routed_walk"}, facts, as_of).as_record())
    if limit.get("max_minutes") is not None:
        whole = route.get("measurement") == "whole_journey" and route.get("endpoint_scope") == "door_to_destination"
        facts = {"journey": {"state": "known" if whole and route.get("minutes") is not None else "unknown", "value": route.get("minutes"), "unit": "min", "basis": "door_to_destination"}}
        checks.append(evaluate({"kind": "number", "field": "journey", "op": "max", "value": limit["max_minutes"], "unit": "min", "basis": "door_to_destination"}, facts, as_of).as_record())
    result = "fail" if any(row["result"] == "fail" for row in checks) else "unknown" if not checks or any(row["result"] == "unknown" for row in checks) else "pass"
    return {"route_id": route.get("id"), "result": result, "checks": checks, "reason": "Checked supplied route, not a claim that no faster alternative exists", "horizon": horizon, "observation": route}


def assess_location(data: Record) -> Record:
    as_of = exact_date(data.get("as_of"))
    origin = data.get("origin_id")
    if not origin:
        raise CaseError("origin_id", "resolve the property/entrance identity first")
    routes = rows(data.get("routes", []), "routes")
    assessments: list[Record] = []
    for limit in rows(data.get("limits", []), "limits"):
        if not limit.get("destination_id"):
            raise CaseError("limit.destination_id", "resolved destination identity required")
        relevant = [route for route in routes if route.get("origin_id") == origin and route.get("destination_id") == limit.get("destination_id")]
        checked = [_route_check(route, limit, as_of) for route in relevant]
        result = "pass" if any(row["result"] == "pass" for row in checked) else "fail" if checked and all(row["result"] == "fail" for row in checked) else "unknown"
        assessments.append({"destination_id": limit.get("destination_id"), "horizon": limit.get("horizon", "current"), "result": result, "routes": checked, "reason": "No matching usable route" if not checked else "Per-destination constraints are not averaged away"})
    return {"assessments": assessments, "observations": routes, "status": "fails_supplied_route_limits" if any(row["result"] == "fail" for row in assessments) else "conditional" if not assessments or any(row["result"] == "unknown" for row in assessments) else "passes_supplied_route_limits", "limitations": ["No live search/routing call was made by this helper; supplied metadata is not independently authenticated", "Arrival ETA/straight-line geometry are not door-to-door journey or walking evidence; future results remain scenarios", "Actual provider coverage, time window, frequency and accessibility evidence remain part of the native research workflow"]}


def assess_amenities(data: Record) -> Record:
    as_of = exact_date(data.get("as_of"))
    results: list[Record] = []
    for item in rows(data.get("items", []), "items"):
        problem = evidence_problem(item, as_of)
        status = "unknown" if problem else str(item.get("operating_status") or "unknown")
        band = None
        if item.get("kind") == "primary_school" and not problem:
            method = item.get("official_distance_method")
            applicable = bool(method) and item.get("method_verified") is True and item.get("distance_basis") == "official_method" and item.get("cohort") == data.get("cohort") and data.get("cohort") is not None and bool(item.get("address_basis"))
            if applicable and item.get("distance_m") is not None:
                distance = amount(str(item["distance_m"]))
                band = "within1km" if distance <= Decimal(1000) else "within2km" if distance <= Decimal(2000) else "beyond2km"
        results.append({"id": item.get("id"), "kind": item.get("kind"), "status": status, "official_distance_band": band, "evidence": item, "limitation": problem or "Operating/service availability and official distance are different from admission, guaranteed access or future value"})
    return {"items": results, "admission_guaranteed": False, "scope": "supplied dated service/method evidence only; no centroid-based school eligibility"}
