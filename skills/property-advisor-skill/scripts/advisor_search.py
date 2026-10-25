"""Bounded supplied-inventory funnel with explicit unknowns and deduplication."""
from __future__ import annotations

from advisor_records import CaseError, Record, record, rows, strings
from advisor_requirements import exact_date
from advisor_screening import assess_requirements, verified_support


def assess_search(data: Record) -> Record:
    if not data.get("coverage"):
        raise CaseError("coverage", "declare the accessible inventory boundary")
    identities: set[str] = set()
    units: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    duplicates: list[Record] = []
    suspected: list[Record] = []
    conditional: list[Record] = []
    rejected: list[Record] = []
    matches: list[Record] = []
    evidence = {str(item.get("id")): item for item in rows(data.get("evidence", []), "evidence")}
    as_of = exact_date(data.get("as_of"))
    for candidate in rows(data.get("candidates"), "candidates"):
        identity = str(candidate.get("id") or "")
        if not identity or identity in identities:
            raise CaseError("candidate.id", "nonempty unique ids required")
        identities.add(identity)
        key = str(candidate.get("unit_key") or "")
        if key and candidate.get("identity_status") == "confirmed":
            if key in units:
                duplicates.append({"id": identity, "same_as": units[key], "reason": "Same supplied confirmed unit key"})
                continue
            units[key] = identity
        fingerprint = str(candidate.get("listing_fingerprint") or "")
        if fingerprint:
            if fingerprint in fingerprints:
                suspected.append({"id": identity, "possibly_same_as": fingerprints[fingerprint]})
            fingerprints[fingerprint] = identity
        assessment = assess_requirements({"requirements": data.get("requirements", []), "facts": record(candidate.get("facts", {}), "facts"), "as_of": data.get("as_of")})
        item = {**candidate, "requirement_assessment": assessment}
        if candidate.get("availability") == "withdrawn" or assessment["status"] == "fails_supplied_constraints":
            rejected.append(item)
        elif assessment["status"] == "passes_supplied_constraints":
            matches.append(item)
            refs = [ref for check in rows(assessment["checks"], "checks") if check.get("priority") == "hard" for ref in strings(check.get("evidence_ids", []), "evidence_ids")]
            refs += strings(candidate.get("availability_evidence_ids", []), "availability_evidence_ids")
            policy_refs = strings(candidate.get("policy_evidence_ids", []), "policy_evidence_ids")
            reviewed = bool(policy_refs) and bool(candidate.get("availability_evidence_ids")) and verified_support(refs + policy_refs, evidence, identity, str(candidate.get("property_id")), as_of)
            item["source_support_reviewed"] = reviewed
            if candidate.get("availability") != "confirmed" or candidate.get("policy_status") != "pass" or not reviewed:
                conditional.append(item)
        else:
            conditional.append(item)
    verified = [item for item in matches if item.get("availability") == "confirmed" and item.get("policy_status") == "pass" and item.get("source_support_reviewed") is True]
    return {"coverage": data["coverage"], "distinct_candidate_count": len(identities) - len(duplicates), "matches_supplied_constraints": matches, "verified_available_fits": verified, "conditional": conditional, "rejected": rejected, "duplicates": duplicates, "suspected_duplicates": suspected, "status": "no_match" if not matches and not conditional else "bounded_shortlist", "relaxations_adopted": [], "limitations": ["No live or whole-market search was performed by this helper", "Identity/policy/source review declarations require actual evidence; passing supplied constraints does not prove affordability or exact-unit value", "No hard constraint was silently relaxed; promising unknowns remain conditional and rejected near-matches retain reasons"]}
