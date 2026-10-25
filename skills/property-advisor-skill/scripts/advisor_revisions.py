"""Protect confirmed requirements while allowing explicitly sourced user revisions."""
from __future__ import annotations

import json

from advisor_records import Record, record, rows, strings


def revision_problems(current: Record, previous: Record) -> list[str]:
    old = rows(record(previous.get("buyer_brief"), "previous buyer_brief").get("requirements"), "previous requirements")
    new = {str(item.get("id")): item for item in rows(record(current.get("buyer_brief"), "buyer_brief").get("requirements"), "requirements")}
    approved: set[str] = set()
    for entry in rows(current.get("history"), "history"):
        if entry.get("source_kind") == "user" and entry.get("reason"):
            approved.update(strings(entry.get("changed_requirement_ids", []), "changed_requirement_ids"))
    errors: list[str] = []
    for requirement in old:
        if requirement.get("state") != "confirmed":
            continue
        identity = str(requirement.get("id"))
        replacement = new.get(identity)
        changed = replacement is None
        if replacement is not None:
            keys = ("value", "original_text", "priority", "state", "condition")
            changed_keys = [key for key in keys if json.dumps(requirement.get(key), sort_keys=True) != json.dumps(replacement.get(key), sort_keys=True)]
            # First-time explicit normalization of unchanged confirmed wording is additive.
            first_normalization = changed_keys == ["condition"] and requirement.get("condition") is None
            changed = bool(changed_keys) and not first_normalization
            wording_changed = any(key in changed_keys for key in ("value", "original_text"))
            if wording_changed and requirement.get("condition") is not None and requirement.get("condition") == replacement.get("condition") and replacement.get("normalization_reconfirmed") is not True:
                errors.append(f"requirement {identity}: changed wording needs normalization review; an old predicate cannot silently remain")
        if changed and identity not in approved:
            errors.append(f"requirement {identity}: confirmed requirement change/removal needs explicit user change history")
    return errors
