"""Small stdlib JSON boundary for portable case records; no new dependencies."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import NoReturn, TypeAlias

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
Record: TypeAlias = dict[str, JSONValue]


class CaseError(ValueError):
    """A malformed case cannot be safely audited or rendered."""

    def __init__(self, field: str, detail: str) -> None:
        self.field = field
        self.detail = detail
        super().__init__(f"{field}: {detail}")


def choice(value: JSONValue, allowed: set[str]) -> bool:
    """Malformed non-string enum values must not cause unhashable-value crashes."""
    return isinstance(value, str) and value in allowed


def parse_json(text: str) -> JSONValue:
    """Reject nonstandard/nonfinite JSON numbers at the input boundary."""
    def invalid_constant(value: str) -> NoReturn:
        raise CaseError("JSON number", f"nonfinite value {value}")

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            invalid_constant(value)
        return number

    value: JSONValue = json.loads(text, parse_constant=invalid_constant, parse_float=finite_float)
    return value


def record(value: JSONValue, field: str) -> Record:
    """Narrow a decoded JSON object at a named boundary."""
    if not isinstance(value, dict):
        raise CaseError(field, "expected an object")
    return value


def rows(value: JSONValue, field: str) -> list[Record]:
    """Parse an array of record objects without dropping malformed entries."""
    if not isinstance(value, list):
        raise CaseError(field, "expected an array")
    return [record(item, field) for item in value]


def strings(value: JSONValue, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CaseError(field, "expected an array of strings")
    return [str(item) for item in value]


def read_case(path: Path) -> Record:
    """Load a user-selected JSON case; never follow paths contained in the case."""
    raw = parse_json(path.read_text(encoding="utf-8"))
    return record(raw, "case")
