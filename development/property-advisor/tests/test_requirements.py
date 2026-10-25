"""Semantic constraints, rather than self-declared pass labels."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
sys.path.insert(0, str(SKILL / "scripts"))


class TestRequirements(unittest.TestCase):
    def setUp(self) -> None:
        from advisor_requirements import evaluate
        self.evaluate = evaluate
        self.as_of = date(2026, 10, 24)

    def test_recent_or_future_age_policy_has_separate_timing(self) -> None:
        cases = [("completed", "2018-01-01", "fail"), ("completed", "2024-01-01", "pass"), ("uncompleted", None, "pass"), ("completed", "2021", "unknown"), ("completed", "2021-10-24", "pass"), ("completed", "2030-01-01", "unknown")]
        for status, top, expected in cases:
            facts = {"completion_status": {"state": "known", "value": status, "evidence_ids": ["e1"]}, "actual_top": {"state": "known" if top else "unknown", "value": top, "evidence_ids": ["e1"]}}
            with self.subTest(status=status, top=top):
                result = self.evaluate({"kind": "age", "max_years": 5, "include_uncompleted": True}, facts, self.as_of)
                self.assertEqual(result.result, expected)

    def test_ready_by_does_not_substitute_expected_top_for_occupancy(self) -> None:
        # Given / When
        result = self.evaluate({"kind": "ready_by", "date": "2028-06-01"}, {"expected_top": {"state": "known", "value": "2028-01-01"}}, self.as_of)
        # Then
        self.assertEqual(result.result, "unknown")

    def test_future_age_pass_cannot_offset_deadline_failure(self) -> None:
        facts = {"completion_status": {"state": "known", "value": "uncompleted"}, "occupancy_date": {"state": "known", "value": "2030-01-01"}}
        # When
        result = self.evaluate({"kind": "all", "conditions": [{"kind": "age", "max_years": 5, "include_uncompleted": True}, {"kind": "ready_by", "date": "2028-01-01"}]}, facts, self.as_of)
        # Then
        self.assertEqual(result.result, "fail")

    def test_reference_date_changes_actual_age(self) -> None:
        facts = {"completion_status": {"state": "known", "value": "completed"}, "actual_top": {"state": "known", "value": "2022-01-01"}}
        # When
        result = self.evaluate({"kind": "age", "max_years": 5, "reference_date": "2028-10-24"}, facts, self.as_of)
        # Then
        self.assertEqual(result.result, "fail")

    def test_calendar_year_window_is_distinct_from_rolling_age(self) -> None:
        facts = {"actual_top": {"state": "known", "value": "2021"}}
        result = self.evaluate({"kind": "date_window", "field": "actual_top", "earliest": "2021-01-01", "latest": "2026-12-31"}, facts, self.as_of)
        self.assertEqual(result.result, "pass")

    def test_completed_current_year_does_not_require_a_future_anniversary(self) -> None:
        facts = {"completion_status": {"state": "known", "value": "completed"}, "actual_top": {"state": "known", "value": "2026"}}
        result = self.evaluate({"kind": "age", "max_years": 5}, facts, self.as_of)
        self.assertEqual(result.result, "pass")

    def test_future_reference_does_not_authenticate_future_actual_top(self) -> None:
        facts = {"completion_status": {"state": "known", "value": "completed"}, "actual_top": {"state": "known", "value": "2027-01-01"}}
        result = self.evaluate({"kind": "age", "max_years": 5, "reference_date": "2028-10-24"}, facts, self.as_of)
        self.assertEqual(result.result, "unknown")

    def test_strata_area_cannot_satisfy_internal_area_limit(self) -> None:
        # Given / When
        result = self.evaluate({"kind": "number", "field": "area", "op": "min", "value": "950", "unit": "sqft", "basis": "net_internal"}, {"area": {"state": "known", "value": "1000", "unit": "sqft", "basis": "strata"}}, self.as_of)
        # Then
        self.assertEqual(result.result, "unknown")

    def test_compatible_area_units_are_converted(self) -> None:
        # Given / When
        result = self.evaluate({"kind": "number", "field": "area", "op": "min", "value": "950", "unit": "sqft", "basis": "net_internal"}, {"area": {"state": "known", "value": "100", "unit": "sqm", "basis": "net_internal", "evidence_ids": ["plan"]}}, self.as_of)
        # Then
        self.assertEqual(result.result, "pass")
        self.assertEqual(result.evidence_ids, ("plan",))

    def test_haversine_is_not_routed_walk(self) -> None:
        result = self.evaluate({"kind": "number", "field": "mrt_walk", "op": "max", "value": "600", "unit": "m", "basis": "routed_walk"}, {"mrt_walk": {"state": "known", "value": "400", "unit": "m", "basis": "straight_line"}}, self.as_of)
        self.assertEqual(result.result, "unknown")

    def test_starting_price_does_not_prove_a_maximum_budget_fit(self) -> None:
        result = self.evaluate({"kind": "number", "field": "price", "op": "max", "value": "2100000", "unit": "SGD"}, {"price": {"state": "known", "value": {"min": "2050000", "max": None}, "unit": "SGD"}}, self.as_of)
        self.assertEqual(result.result, "unknown")

    def test_preference_does_not_invent_a_distance_cutoff(self) -> None:
        result = self.evaluate({"kind": "preference", "field": "mrt_walk", "direction": "lower"}, {"mrt_walk": {"state": "known", "value": "800", "unit": "m"}}, self.as_of)
        self.assertEqual(result.result, "not_applicable")

    def test_invalid_operator_is_rejected_at_boundary(self) -> None:
        from advisor_records import CaseError
        with self.assertRaises(CaseError):
            self.evaluate({"kind": "python_eval", "code": "1+1"}, {}, self.as_of)


class TestSemanticCaseAudit(unittest.TestCase):
    def test_declared_age_pass_cannot_hide_a_2010_top(self) -> None:
        from advisor_case import audit_case
        from advisor_records import read_case
        case = read_case(SKILL / "assets" / "case-template.json")
        case["research_date"] = "2026-10-24"
        case["buyer_brief"] = {"requirements": [{"id": "age", "priority": "hard", "state": "confirmed", "condition": {"kind": "age", "max_years": 5}}]}
        case["properties"] = [{"id": "p1", "category": "private_non_landed", "facts": {"completion_status": {"state": "known", "value": "completed", "evidence_ids": ["e1"]}, "actual_top": {"state": "known", "value": "2010-01-01", "evidence_ids": ["e1"]}}}]
        case["evidence"] = [{"id": "e1", "source": "fixture://TOP2010", "kind": "official_particulars", "scope": "project", "property_id": "p1", "confidence": "verified", "extraction_status": "completed", "retrieved_at": "2026-10-24"}]
        case["candidates"] = [{"id": "c1", "property_id": "p1", "fit": "verified", "availability": "confirmed", "checks": [{"requirement_id": "age", "result": "pass", "evidence_ids": ["e1"]}]}]
        result = audit_case(case)
        self.assertTrue(any("semantic" in error for error in result.errors))
        self.assertNotIn("c1", result.verified_fits)


if __name__ == "__main__":
    unittest.main()
