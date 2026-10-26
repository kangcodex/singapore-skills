"""Audit case invariants. This checks records, not the truth of their sources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

from advisor_records import CaseError, Record, choice, read_case as read_case, record, rows, strings
from advisor_screening import combined_facts, requirement_check, verified_support
from advisor_revisions import revision_problems

ENTITIES: Final = ("properties", "candidates", "evidence", "comparables", "cost_scenarios", "recommendations", "policy_assessments", "source_access", "history")
CATEGORIES: Final = {"hdb", "ec", "private_non_landed", "landed"}
CONFIDENCE: Final = {"verified", "corroborated", "indicative", "assumed", "conflicting", "unavailable"}


@dataclass(frozen=True, slots=True)
class Audit:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    verified_fits: tuple[str, ...]


def audit_case(case: Record, previous: Record | None = None) -> Audit:
    """Fail closed on hard constraints, unsupported claims and broken provenance."""
    errors: list[str] = []
    warnings: list[str] = []
    fits: list[str] = []
    if case.get("schema_version") != "3.0":
        errors.append("schema_version must be 3.0")
    version = case.get("version")
    if not isinstance(case.get("case_id"), str) or not case.get("case_id") or type(version) is not int or int(str(version)) < 1:
        errors.append("case_id and positive integer version are required")
        return Audit(tuple(errors), (), ())
    try:
        research_date = date.fromisoformat(str(case.get("research_date")))
    except ValueError as exc:
        raise CaseError("research_date", "expected ISO date") from exc
    brief = record(case.get("buyer_brief"), "buyer_brief")
    search = record(case.get("search_brief"), "search_brief")
    if not search.get("coverage"):
        errors.append("search_brief.coverage is required")
    groups = {name: rows(case.get(name), name) for name in ENTITIES}
    indexes: dict[str, dict[str, Record]] = {}
    for name, entries in groups.items():
        index: dict[str, Record] = {}
        for entry in entries:
            raw_id = entry.get("id")
            identity = str(raw_id or "")
            if not isinstance(raw_id, str) or not identity or identity in index:
                errors.append(f"{name}: missing or duplicate id {identity!r}")
            index[identity] = entry
        indexes[name] = index
    evidence = indexes["evidence"]
    for identity, claim in evidence.items():
        if not choice(claim.get("confidence"), CONFIDENCE) or not claim.get("source") or not claim.get("scope") or not claim.get("kind"):
            errors.append(f"evidence {identity}: source, kind, scope and confidence required")
        try:
            retrieved = date.fromisoformat(str(claim.get("retrieved_at")))
            if retrieved > research_date:
                errors.append(f"evidence {identity}: retrieved after research_date")
        except ValueError:
            errors.append(f"evidence {identity}: invalid retrieval date")

    def support(entry: Record) -> list[Record]:
        refs = strings(entry.get("evidence_ids", []), "evidence_ids")
        for ref in refs:
            if ref not in evidence:
                errors.append(f"unknown evidence reference {ref}")
        return [evidence[ref] for ref in refs if ref in evidence]

    requirements = rows(brief.get("requirements"), "requirements")
    requirement_map = {str(item.get("id")): item for item in requirements}
    hard = {str(item.get("id")) for item in requirements if item.get("priority") == "hard"}
    requirement_ids = {str(item.get("id")) for item in requirements}
    if len(requirement_ids) != len(requirements):
        errors.append("duplicate requirement id")
    for requirement in requirements:
        if not requirement.get("id") or not choice(requirement.get("priority"), {"hard", "strong", "flexible"}) or not choice(requirement.get("state"), {"confirmed", "assumed", "unknown"}):
            errors.append("requirement needs id, priority and knowledge state")
    for prop in groups["properties"]:
        if not choice(prop.get("category"), CATEGORIES):
            errors.append(f"property {prop.get('id')}: unknown category")
    for candidate in groups["candidates"]:
        candidate_error_start = len(errors)
        identity = str(candidate.get("id") or "")
        if str(candidate.get("property_id")) not in indexes["properties"]:
            errors.append(f"candidate {identity}: unknown property_id")
        checks = rows(candidate.get("checks"), "checks")
        facts = combined_facts(indexes["properties"].get(str(candidate.get("property_id")), {}), candidate)
        passed: set[str] = set()
        active_hard = 0
        seen: set[str] = set()
        invalid_checks = False
        for check in checks:
            supporting = support(check)
            requirement_id = str(check.get("requirement_id"))
            if requirement_id in seen or requirement_id not in requirement_ids:
                errors.append(f"candidate {identity}: duplicate or unknown requirement check {requirement_id}")
                invalid_checks = True
            seen.add(requirement_id)
            if not choice(check.get("result"), {"pass", "fail", "unknown", "not_applicable"}):
                errors.append(f"candidate {identity}: invalid check result")
            if choice(check.get("result"), {"pass", "not_applicable"}) and supporting and all(choice(item.get("confidence"), {"verified", "corroborated"}) and item.get("extraction_status") == "completed" for item in supporting):
                requirement = requirement_map.get(requirement_id)
                if requirement is not None and requirement.get("priority") == "hard":
                    try:
                        semantic = requirement_check(requirement, facts, research_date)
                    except ValueError as exc:
                        errors.append(f"candidate {identity}: semantic condition invalid: {exc}")
                        continue
                    if semantic.result != check.get("result") or not semantic.evidence_ids:
                        errors.append(f"candidate {identity}: semantic hard constraint {requirement_id} is {semantic.result} or lacks fact provenance")
                        continue
                    if not set(semantic.evidence_ids).issubset(strings(check.get("evidence_ids", []), "evidence_ids")):
                        errors.append(f"candidate {identity}: semantic fact evidence is absent from declared support")
                        continue
                    if not verified_support(list(semantic.evidence_ids), evidence, identity, str(candidate.get("property_id")), research_date):
                        errors.append(f"candidate {identity}: semantic evidence is stale, hypothetical or belongs to another property/home")
                        continue
                    active_hard += semantic.result == "pass"
                passed.add(str(check.get("requirement_id")))
        if candidate.get("fit") == "verified":
            if not hard.issubset(passed) or not hard or not active_hard or invalid_checks:
                errors.append(f"candidate {identity}: hard constraint missing, failed or unsupported")
        if not choice(candidate.get("fit"), {"verified", "conditional", "stretch", "rejected"}):
            errors.append(f"candidate {identity}: invalid fit state")
        if not choice(candidate.get("availability"), {"confirmed", "quoted", "listed", "application", "allocated", "selectable", "unknown", "withdrawn"}):
            errors.append(f"candidate {identity}: explicit availability state required")
        if candidate.get("availability") == "withdrawn" and candidate.get("fit") == "verified":
            errors.append(f"candidate {identity}: withdrawn home cannot be a verified fit")
        if candidate.get("fit") == "verified" and len(errors) == candidate_error_start:
            fits.append(identity)
    for name in ("comparables", "cost_scenarios", "policy_assessments"):
        for entry in groups[name]:
            support(entry)
    for recommendation in groups["recommendations"]:
        candidate_id = str(recommendation.get("candidate_id") or "")
        if candidate_id and candidate_id not in indexes["candidates"]:
            errors.append(f"recommendation: unknown candidate {candidate_id}")
        for claim in rows(recommendation.get("claims", []), "claims"):
            supporting = support(claim)
            usable = [item for item in supporting if choice(item.get("confidence"), {"verified", "corroborated"}) and item.get("extraction_status") == "completed"]
            kind = claim.get("kind")
            if not choice(kind, {"exact_value", "view", "eligibility", "redevelopment", "layout", "scenario", "inference"}):
                errors.append(f"unknown recommendation claim kind {kind}")
            if kind == "exact_value":
                quotes = [item for item in usable if choice(item.get("kind"), {"quotation", "transaction", "valuation"}) and choice(item.get("scope"), {"unit", "parcel"}) and item.get("candidate_id") == candidate_id]
                comps = [item for item in groups["comparables"] if item.get("candidate_id") == candidate_id and any(source.get("kind") == "transaction" and source.get("extraction_status") == "completed" and choice(source.get("confidence"), {"verified", "corroborated"}) for source in support(item))]
                if not quotes or not comps:
                    errors.append("exact_value requires identified home price and matched comparables")
            if choice(kind, {"view", "eligibility", "redevelopment", "layout"}):
                required = {"view": "view", "eligibility": "official_rule", "redevelopment": "planning_decision", "layout": "floor_plan"}[str(kind)]
                matching = [item for item in usable if item.get("kind") == required]
                if kind == "view":
                    matching = [item for item in matching if choice(item.get("scope"), {"unit", "parcel"}) and candidate_id and item.get("candidate_id") == candidate_id]
                if not matching:
                    errors.append(f"{kind} requires usable {required} evidence")
    if not groups["candidates"]:
        warnings.append("No candidates: research/discovery is pending or no match was found; do not invent a shortlist.")
    if not groups["recommendations"]:
        warnings.append("No recommendation yet; complete the human-readable decision before publication.")
    if previous is not None:
        errors.extend(revision_problems(case, previous))
        prior_version = previous.get("version")
        if type(prior_version) is not int:
            errors.append("previous case version must be an integer")
        elif case.get("case_id") != previous.get("case_id") or int(str(version)) <= int(str(prior_version)):
            errors.append("revision must preserve case_id and increase version")
        if case.get("supersedes") != previous.get("version") or not groups["history"]:
            errors.append("revision requires supersedes and explicit change history")
    return Audit(tuple(errors), tuple(warnings), tuple(fits))
