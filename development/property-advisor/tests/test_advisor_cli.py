"""Drive the actual CLI, including error paths and a cross-category record."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CLI = SKILL / "scripts" / "advisor_cli.py"


class TestAdvisorCLI(unittest.TestCase):
    def test_cross_category_record_is_audited_and_returned(self) -> None:
        # Given / When
        result = subprocess.run([sys.executable, str(CLI), "--case", str(FIXTURES / "cases" / "example-case.json"), "--format", "json"], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["audit"]["errors"], [])
        self.assertEqual({item["category"] for item in report["case"]["properties"]}, {"hdb", "ec", "private_non_landed", "landed"})
        self.assertEqual(report["audit"]["verified_fits"], [])

    def test_markdown_renders_recommendation_and_unknown_costs(self) -> None:
        # Given / When
        result = subprocess.run([sys.executable, str(CLI), "--case", str(FIXTURES / "cases" / "example-case.json")], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Investigate H1", result.stdout)
        self.assertIn("**Affordability:** unknown", result.stdout)
        self.assertIn("**Complete:** False", result.stdout)
        self.assertNotIn('"recommendations":', result.stdout)

    def test_incompatible_price_basis_exits_two_with_json_error(self) -> None:
        # Given / When
        result = subprocess.run([sys.executable, str(CLI), "--calculate", "premium", "--asking", "2000000", "--asking-unit", "total", "--baseline", "2000", "--baseline-unit", "psf"], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 2)
        self.assertIn("area", json.loads(result.stdout)["error"])
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_case_file_is_not_a_success(self) -> None:
        # Given / When
        result = subprocess.run([sys.executable, str(CLI), "--case", str(SKILL / "assets" / "does-not-exist.json")], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))

    def test_empty_subtotal_is_incomplete(self) -> None:
        # Given / When
        result = subprocess.run([sys.executable, str(CLI), "--calculate", "subtotal", "--components", "{}"], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["complete"])

    def test_legacy_entry_point_routes_the_new_case_workflow(self) -> None:
        # Given / When
        legacy = SKILL / "scripts" / "property_advisor.py"
        result = subprocess.run([sys.executable, str(legacy), "--case", str(FIXTURES / "cases" / "example-case.json"), "--format", "json"], capture_output=True, text=True, check=False)
        # Then
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["case"]["schema_version"], "3.0")

    def test_focused_fixtures_execute_through_the_real_cli(self) -> None:
        examples = {"question": "questions", "requirements": "checks", "location": "assessments", "amenities": "items", "documents": "effective_claims", "comfort": "rooms", "funding": "strategies", "loan_plan": "timeline", "cost_comparison": "options", "exit": "equity_before_costs", "comparables": "selected", "scenarios": "scenarios", "search": "rejected", "watch": "specification"}
        for kind, output_key in examples.items():
            with self.subTest(kind=kind):
                result = subprocess.run([sys.executable, str(CLI), "--assess", kind, "--input", str(FIXTURES / "assessments" / f"{kind}.json"), "--format", "json"], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)[output_key])

    def test_question_led_case_executes_bound_assessments(self) -> None:
        result = subprocess.run([sys.executable, str(CLI), "--case", str(FIXTURES / "cases" / "question-led-case.json"), "--format", "json"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["audit"]["errors"], [])
        self.assertEqual(payload["case"]["assessment_results"]["constraints"]["assessment"]["status"], "passes_supplied_constraints")

    def test_focused_assessment_missing_input_is_a_real_error(self) -> None:
        result = subprocess.run([sys.executable, str(CLI), "--assess", "funding", "--format", "json"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--input", result.stderr)

    def test_incompatible_cli_context_arguments_are_not_silently_ignored(self) -> None:
        result = subprocess.run([sys.executable, str(CLI), "--calculate", "subtotal", "--previous-case", str(SKILL / "assets" / "case-template.json")], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
