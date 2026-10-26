"""Function-first household assessment over sourced plans, never a sqft/person rule."""
from __future__ import annotations

from advisor_records import CaseError, Record, record, rows, strings


def _one(household: Record, layout: Record) -> Record:
    groups = strings(household.get("sleeping_groups", []), "sleeping_groups")
    rooms = rows(layout.get("rooms", []), "rooms")
    proven, possible = 0, 0
    room_results: list[Record] = []
    furniture_unknown = False
    room_ids: set[str] = set()
    for room in rooms:
        identity = str(room.get("id") or "")
        if not identity or identity in room_ids:
            raise CaseError("room.id", "unique room ids are required; do not count repeated plan variants as extra rooms")
        room_ids.add(identity)
        is_candidate = room.get("kind") in ("bedroom", "study", "flex")
        if not is_candidate:
            continue
        facts = [room.get("approved_bedroom"), room.get("common_access"), room.get("enclosed"), room.get("window")]
        status = "unknown"
        if any(value is False for value in facts):
            status = "fail"
        elif all(value is True for value in facts) and room.get("source"):
            status = "pass"
            proven += 1
        if status != "fail":
            possible += 1
        dimensions = room.get("dimensions_m")
        furniture_ok = room.get("furniture_fit") == "verified" and isinstance(dimensions, dict) and dimensions.get("width") is not None and dimensions.get("length") is not None and bool(room.get("source"))
        if status != "fail" and not furniture_ok:
            furniture_unknown = True
        room_results.append({"id": room.get("id"), "sleeping_room_result": status, "furniture_clearance": "supplied_verified_with_dimensions" if furniture_ok else "unknown_or_illustrative", "reason": "Access/enclosure/windows/approved use and source checked; no automatic study conversion"})
    sleeping: str = "unknown"
    if groups and proven >= len(groups):
        sleeping = "pass"
    elif groups and rooms and possible < len(groups) and layout.get("rooms_complete") is True:
        sleeping = "fail"
    bathrooms = rows(layout.get("bathrooms", []), "bathrooms")
    full = sum(item.get("kind") == "full" and bool(item.get("source")) for item in bathrooms) if bathrooms else None
    wc = sum(item.get("kind") == "wc" and bool(item.get("source")) for item in bathrooms) if bathrooms else None
    minimum = household.get("min_full_bathrooms")
    bathroom_fit = "not_applicable" if minimum is None else "unknown" if full is None else "pass" if full >= int(str(minimum)) else "fail" if layout.get("bathrooms_complete") is True else "unknown"
    feature_checks: list[Record] = []
    for name, required in record(household.get("required_features", {}), "required_features").items():
        feature = record(record(layout.get("features", {}), "features").get(name, {"state": "unknown"}), name)
        state = "unknown" if feature.get("state") != "known" or not feature.get("source") else "pass" if feature.get("value") == required else "fail"
        feature_checks.append({"feature": name, "result": state})
    failed = sleeping == "fail" or bathroom_fit == "fail" or any(item["result"] == "fail" for item in feature_checks)
    complete = sleeping == "pass" and not furniture_unknown and bathroom_fit != "unknown" and all(item["result"] == "pass" for item in feature_checks) and layout.get("functional_review_complete") is True
    return {"overall_fit": "fail" if failed else "passes_supplied_function_checks" if complete else "conditional", "sleeping_fit": sleeping, "required_sleeping_groups": len(groups) if groups else None, "proven_sleeping_rooms": proven if rooms else None, "rooms": room_results, "full_bathrooms": full, "service_wc": wc, "bathroom_fit": bathroom_fit, "feature_checks": feature_checks, "net_internal_area": layout.get("net_internal_area"), "missing_inputs": ["Agreed sleeping/sharing groups"] if not groups else [], "limitations": ["No headcount-to-area rule or inferred net/usable efficiency", "Clearances, storage, work/privacy, laundry/cooking, circulation and approved use require matching source evidence; a partial sleeping check is not whole-home certification"]}


def assess_comfort(data: Record) -> Record:
    household = record(data.get("household"), "household")
    layout = record(data.get("layout"), "layout")
    result = _one(household, layout)
    future: list[Record] = []
    for scenario in rows(data.get("future_scenarios", []), "future_scenarios"):
        if not scenario.get("id"):
            raise CaseError("future_scenario.id", "explicit scenario identity required")
        assessment = _one(record(scenario.get("household"), "future household"), layout)
        future.append({"id": scenario["id"], "hard": scenario.get("hard") is True, "assessment": assessment})
        if scenario.get("hard") is True:
            if assessment["overall_fit"] == "fail":
                result["overall_fit"] = "fail"
            elif assessment["overall_fit"] == "conditional" and result["overall_fit"] != "fail":
                result["overall_fit"] = "conditional"
    result["future_scenarios"] = future
    return result
