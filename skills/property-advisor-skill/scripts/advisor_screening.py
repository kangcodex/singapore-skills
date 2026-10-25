"""Shared requirement screening and property/candidate fact reconciliation."""
from __future__ import annotations

from datetime import date

from advisor_records import CaseError, Record, choice, record, rows, strings
from advisor_requirements import Check, evaluate, exact_date


def combined_facts(prop: Record, candidate: Record) -> Record:
    facts = dict(record(prop.get("facts", {}), "property.facts"))
    for key, value in record(candidate.get("facts", {}), "candidate.facts").items():
        previous = facts.get(key)
        if previous is not None and previous != value:
            old, new = record(previous, key), record(value, key)
            if old.get("state") == "known" and new.get("state") == "known" and old.get("value") != new.get("value"):
                facts[key] = {"state": "conflicting", "value": None, "evidence_ids": sorted(set(strings(old.get("evidence_ids", []), "evidence_ids") + strings(new.get("evidence_ids", []), "evidence_ids")))}
                continue
        facts[key] = value
    return facts


def requirement_check(requirement: Record, facts: Record, as_of: date) -> Check:
    if requirement.get("state") != "confirmed":
        return Check("unknown", "Requirement meaning/value is not confirmed")
    if requirement.get("condition") is None:
        return Check("unknown", "Normalize the original requirement into an explicit condition first")
    return evaluate(record(requirement["condition"], "condition"), facts, as_of)


def verified_support(refs: list[str], evidence: dict[str, Record], candidate_id: str, property_id: str, as_of: date) -> bool:
    if not refs:
        return False
    for ref in refs:
        source = evidence.get(ref)
        if source is None or not choice(source.get("confidence"), {"verified", "corroborated"}) or source.get("extraction_status") != "completed":
            return False
        if source.get("kind") in ("scenario", "inference", "marketing"):
            return False
        if not source.get("retrieved_at") or exact_date(source["retrieved_at"]) > as_of:
            return False
        if source.get("valid_until") and exact_date(source["valid_until"]) < as_of:
            return False
        if source.get("candidate_id") is not None and source["candidate_id"] != candidate_id:
            return False
        if source.get("property_id") is not None and source["property_id"] != property_id:
            return False
        if source.get("scope") in ("unit", "parcel") and source.get("candidate_id") != candidate_id:
            return False
    return True


def assess_requirements(data: Record) -> Record:
    requirements = rows(data.get("requirements"), "requirements")
    facts = record(data.get("facts"), "facts")
    as_of = exact_date(data.get("as_of"))
    results: list[Record] = []
    seen: set[str] = set()
    for requirement in requirements:
        identity = str(requirement.get("id") or "")
        if not identity or identity in seen:
            raise CaseError("requirements", "requirement ids must be unique and nonempty")
        seen.add(identity)
        check = requirement_check(requirement, facts, as_of)
        results.append({"requirement_id": identity, "priority": requirement.get("priority"), **check.as_record()})
    hard = [row for row in results if row["priority"] == "hard"]
    active = [row for row in hard if row["result"] != "not_applicable"]
    status = "fails_supplied_constraints" if any(row["result"] == "fail" for row in hard) else "conditional" if not active or any(row["result"] == "unknown" for row in hard) else "passes_supplied_constraints"
    return {"status": status, "checks": results, "limitations": ["Semantic results use supplied facts; independent evidence confidence, eligibility, availability and affordability remain separate"]}
