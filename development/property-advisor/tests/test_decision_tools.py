"""Regression tests for evidence-bound, cross-category decision helpers."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))


class TestCalculations(unittest.TestCase):
    def setUp(self) -> None:
        import advisor_calculations
        self.math = advisor_calculations

    def test_total_price_is_normalized_only_with_area(self) -> None:
        # Given / When
        premium = self.math.price_premium("2000000", "total", "2000", "psf", "1000")
        # Then
        self.assertEqual(premium, Decimal("0"))

    def test_missing_area_cannot_become_a_premium(self) -> None:
        # Given / When / Then
        with self.assertRaises(self.math.CalculationError):
            self.math.price_premium("2000000", "total", "2000", "psf")

    def test_land_and_strata_denominators_cannot_be_compared(self) -> None:
        # Given / When / Then
        with self.assertRaises(self.math.CalculationError):
            self.math.price_premium("2000", "land_psf", "1800", "psf")

    def test_subtotal_preserves_excluded_unknown_costs(self) -> None:
        # Given / When
        result = self.math.cost_total({"price": "2850000", "bsd": "112100", "legal": None})
        # Then
        self.assertEqual(result["subtotal"], "2962100.00")
        self.assertFalse(result["complete"])
        self.assertEqual(result["excluded"], ["legal"])

    def test_no_known_cost_is_unknown_rather_than_a_zero_subtotal(self) -> None:
        result = self.math.cost_total({"price": None, "duty": None})
        self.assertIsNone(result["subtotal"])
        self.assertFalse(result["complete"])

    def test_zero_rate_mortgage(self) -> None:
        # Given / When
        result = self.math.monthly_payment("120000", "0", 10)
        # Then
        self.assertEqual(result, Decimal("1000.00"))

    def test_interest_bearing_mortgage_reference_payment(self) -> None:
        # Given / When
        result = self.math.monthly_payment("100000", "4", 30)
        # Then: standard nominal-monthly amortization reference value.
        self.assertEqual(result, Decimal("477.42"))

    def test_nonfinite_money_is_rejected(self) -> None:
        for value in ("NaN", "Infinity", "-1"):
            with self.subTest(value=value), self.assertRaises(self.math.CalculationError):
                self.math.monthly_payment(value, "4", 25)

    def test_gapped_trend_has_no_qoq_or_yoy(self) -> None:
        # Given / When
        result = self.math.trend_block([
            {"qtr": "2024-Q1", "value": 100}, {"qtr": "2026-Q1", "value": 120},
        ], "value", as_of=date(2026, 10, 23))
        # Then
        self.assertIsNone(result["qoq_pct"])
        self.assertIsNone(result["yoy_pct"])

    def test_trend_sorts_and_excludes_current_quarter(self) -> None:
        # Given / When
        result = self.math.trend_block([
            {"qtr": "2026-Q4", "value": 999}, {"qtr": "2026-Q3", "value": 110},
            {"qtr": "2026-Q2", "value": 100},
        ], "value", as_of=date(2026, 10, 23))
        # Then
        self.assertEqual(result["qoq_pct"], 10.0)
        self.assertEqual(result["last_8_quarters"][-1]["qtr"], "2026-Q3")

    def test_duplicate_quarter_does_not_become_two_periods(self) -> None:
        # Given / When / Then
        with self.assertRaises(self.math.CalculationError):
            self.math.trend_block([
                {"qtr": "2026-Q1", "value": 100}, {"qtr": "2026-Q1", "value": 120},
            ], "value")


class TestCaseAudit(unittest.TestCase):
    def setUp(self) -> None:
        import advisor_case
        self.case = advisor_case
        self.template = SKILL / "assets" / "case-template.json"

    def test_empty_case_remains_valid_but_no_match(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertEqual(result.errors, ())
        self.assertEqual(result.verified_fits, ())
        self.assertTrue(result.warnings)

    def test_hard_failure_cannot_be_verified_fit(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["buyer_brief"] = {"requirements": [{"id": "r1", "priority": "hard", "value": "3 bedrooms", "state": "confirmed"}]}
        case["candidates"] = [{"id": "u1", "property_id": "p1", "fit": "verified", "checks": [{"requirement_id": "r1", "result": "fail", "evidence_ids": []}]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("hard constraint" in error for error in result.errors))

    def test_unsupported_unit_value_claim_is_rejected(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["recommendations"] = [{"id": "rec1", "candidate_id": "u1", "claims": [{"kind": "exact_value", "evidence_ids": []}]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("exact_value" in error for error in result.errors))

    def test_unknown_evidence_reference_is_rejected(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["recommendations"] = [{"id": "rec1", "candidate_id": None, "claims": [{"kind": "layout", "evidence_ids": ["invented"]}]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("invented" in error for error in result.errors))

    def test_revision_must_explicitly_supersede_previous_record(self) -> None:
        # Given
        previous = self.case.read_case(self.template)
        current = self.case.read_case(self.template)
        current["version"] = 2
        # When
        result = self.case.audit_case(current, previous)
        # Then
        self.assertTrue(any("supersedes" in error for error in result.errors))

    def test_contradictory_checks_cannot_pass_a_hard_requirement(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["buyer_brief"] = {"requirements": [{"id": "r1", "priority": "hard", "value": 3, "state": "confirmed"}]}
        case["properties"] = [{"id": "p1", "category": "hdb"}]
        case["evidence"] = [{"id": "e1", "source": "fixture://plan", "kind": "floor_plan", "scope": "unit", "confidence": "verified", "retrieved_at": "2026-10-23", "extraction_status": "completed"}]
        case["candidates"] = [{"id": "u1", "property_id": "p1", "fit": "verified", "availability": "confirmed", "checks": [
            {"requirement_id": "r1", "result": "pass", "evidence_ids": ["e1"]},
            {"requirement_id": "r1", "result": "fail", "evidence_ids": ["e1"]},
        ]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(result.errors)
        self.assertNotIn("u1", result.verified_fits)

    def test_project_panorama_cannot_support_exact_home_view(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["evidence"] = [{"id": "e1", "source": "fixture://panorama", "kind": "view", "scope": "project", "confidence": "verified", "retrieved_at": "2026-10-23", "extraction_status": "completed"}]
        case["recommendations"] = [{"id": "rec1", "candidate_id": None, "claims": [{"kind": "view", "evidence_ids": ["e1"]}]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("view" in error for error in result.errors))

    def test_invalid_enum_type_is_reported_without_a_crash(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["properties"] = [{"id": "p1", "category": ["hdb"]}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("category" in error for error in result.errors))

    def test_missing_candidate_id_is_reported_without_key_error(self) -> None:
        # Given
        case = self.case.read_case(self.template)
        case["candidates"] = [{"property_id": "p1", "fit": "conditional", "availability": "unknown", "checks": []}]
        # When
        result = self.case.audit_case(case)
        # Then
        self.assertTrue(any("id" in error for error in result.errors))

    def test_nonfinite_json_is_rejected(self) -> None:
        # Given
        from advisor_records import CaseError, parse_json
        # When / Then
        for number in ("NaN", "Infinity", "1e9999"):
            with self.subTest(number=number), self.assertRaises(CaseError):
                parse_json('{"value":' + number + '}')

    def test_confirmed_hard_requirement_removal_needs_user_change_history(self) -> None:
        previous = self.case.read_case(self.template)
        previous["buyer_brief"]["requirements"] = [{"id": "budget", "priority": "hard", "state": "confirmed", "value": "Maximum2m"}]
        current = self.case.read_case(self.template)
        current["version"] = 2
        current["supersedes"] = 1
        current["history"] = [{"id": "h2", "reason": "Generic refresh"}]
        result = self.case.audit_case(current, previous)
        self.assertTrue(any("user change history" in error for error in result.errors))

    def test_changed_wording_cannot_reuse_an_unreviewed_old_predicate(self) -> None:
        import copy
        previous = self.case.read_case(self.template)
        previous["buyer_brief"]["requirements"] = [{"id": "budget", "priority": "hard", "state": "confirmed", "value": "Maximum2m", "condition": {"kind": "number", "field": "price", "op": "max", "value": "2000000", "unit": "SGD"}}]
        current = copy.deepcopy(previous)
        current["version"] = 2
        current["supersedes"] = 1
        current["history"] = [{"id": "h2", "source_kind": "user", "changed_requirement_ids": ["budget"], "reason": "Budget changed"}]
        current["buyer_brief"]["requirements"][0]["value"] = "Maximum1.8m"
        result = self.case.audit_case(current, previous)
        self.assertTrue(any("normalization" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
