"""Expand explicit monthly household assumptions into dated funding events."""
from __future__ import annotations

from copy import deepcopy

from advisor_records import CaseError, Record, rows
from advisor_requirements import exact_date
from agent_schedule import add_months


def cash_events(data: Record) -> list[Record]:
    events = deepcopy(rows(data.get("events", []), "events"))
    for recurring in rows(data.get("recurring", []), "recurring"):
        identity = str(recurring.get("id") or "")
        months = recurring.get("months")
        if not identity or type(months) is not int or not 1 <= months <= 600:
            raise CaseError("recurring", "id and one to600 explicit monthly periods required")
        start = exact_date(recurring.get("start"))
        changes: dict[int, Record] = {}
        for change in rows(recurring.get("changes", []), "changes"):
            position = change.get("from_month")
            if type(position) is not int or not 1 <= position <= months or position in changes:
                raise CaseError("from_month", "unique one-based month within schedule required")
            changes[position] = change
        current = {key: value for key, value in recurring.items() if key not in {"start", "months", "changes"}}
        for index in range(months):
            if index + 1 in changes:
                current.update({key: value for key, value in changes[index + 1].items() if key != "from_month"})
            events.append({**current, "id": f"{identity}:{index + 1}", "date": add_months(start, index).isoformat(), "recurring": True})
    return events
