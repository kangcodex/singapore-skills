"""Real assessment dispatch and changed-case dependency execution."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
sys.path.insert(0, str(SKILL / "scripts"))


class TestWorkflow(unittest.TestCase):
    def test_case_references_use_current_facts_and_recompute_on_update(self) -> None:
        from advisor_records import read_case
        from advisor_workflow import evaluate_case
        previous = read_case(SKILL / "assets" / "case-template.json")
        previous["research_date"] = "2026-10-24"
        previous["buyer_brief"]["requirements"] = [{"id": "price", "priority": "hard", "state": "confirmed", "condition": {"kind": "number", "field": "price", "op": "max", "value": "2000000", "unit": "SGD"}}]
        previous["properties"] = [{"id": "p", "category": "private_non_landed"}]
        previous["candidates"] = [{"id": "c", "property_id": "p", "fit": "conditional", "availability": "listed", "checks": [], "facts": {"price": {"state": "known", "value": "1900000", "unit": "SGD"}}}]
        previous["analysis_requests"] = [{"id": "screen", "kind": "requirements", "input_refs": {"requirements": "/buyer_brief/requirements", "facts": "/candidate_facts/c", "as_of": "/research_date"}}]
        old = evaluate_case(previous)
        current = copy.deepcopy(previous)
        current["version"] = 2
        current["supersedes"] = 1
        current["history"] = [{"id": "h2", "reason": "New quotation"}]
        current["candidates"][0]["facts"]["price"]["value"] = "2200000"
        # When
        new = evaluate_case(current, old)
        # Then
        self.assertEqual(old["assessment_results"]["screen"]["assessment"]["status"], "passes_supplied_constraints")
        self.assertEqual(new["assessment_results"]["screen"]["assessment"]["status"], "fails_supplied_constraints")
        self.assertEqual(new["candidates"][0]["fit"], "rejected")
        self.assertIn("screen", new["change_summary"]["recomputed_assessments"])
        self.assertEqual(previous["candidates"][0]["facts"]["price"]["value"], "1900000")

    def test_input_pointer_is_not_a_file_loader(self) -> None:
        from advisor_records import CaseError
        from advisor_workflow import resolve_pointer
        with self.assertRaises(CaseError):
            resolve_pointer({"x": "value"}, "file:///not-a-case-field")

    def test_watch_specification_does_not_create_active_notifications(self) -> None:
        from advisor_workflow import assess
        result = assess("watch", {"explicit_request": True, "targets": ["c"], "triggers": [{"max_price": "1800000"}], "expiry": "2026-12-31"})
        self.assertFalse(result["active"])
        self.assertEqual(result["status"], "specification_only")

    def test_computed_case_metadata_is_not_a_material_input_change(self) -> None:
        from advisor_records import read_case
        from advisor_workflow import evaluate_case
        case = read_case(SKILL / "assets" / "case-template.json")
        case["buyer_brief"]["requirements"] = [{"id": "r", "priority": "hard", "state": "confirmed", "condition": {"kind": "number", "field": "bedrooms", "op": "min", "value": "3", "unit": "count"}}]
        case["properties"] = [{"id": "p", "category": "hdb"}]
        case["candidates"] = [{"id": "c", "property_id": "p", "fit": "conditional", "availability": "listed", "checks": [], "facts": {}}]
        old = evaluate_case(case)
        result = evaluate_case(case, old)
        self.assertEqual(result["change_summary"]["changed_input_paths"], [])

    def test_unchanged_advice_is_retired_after_material_facts_change(self) -> None:
        from advisor_records import read_case
        from advisor_workflow import evaluate_case
        previous = read_case(SKILL / "assets" / "case-template.json")
        previous["summary"] = "Old advice based on old facts"
        previous["recommendations"] = [{"id": "rec", "candidate_id": None, "action": "Continue old route", "claims": []}]
        current = copy.deepcopy(previous)
        current["buyer_brief"]["unknowns"] = ["New ownership fact must be checked"]
        result = evaluate_case(current, previous)
        self.assertEqual(result["summary_status"], "superseded_pending_reassessment")
        self.assertEqual(result["recommendations"][0]["status"], "superseded_pending_reassessment")

    def test_nested_input_reference_links_exit_proceeds_to_a_funding_event(self) -> None:
        from advisor_records import read_case
        from advisor_workflow import evaluate_case
        case = read_case(SKILL / "assets" / "case-template.json")
        case["exit_inputs"] = {"sale_price": "2000000", "loan_redemption": "1200000", "selling_costs": "50000", "cpf_principal_refund": "350000", "cpf_accrued_refund": "30000"}
        case["analysis_requests"] = [{"id": "exit", "kind": "exit", "input_refs": {key: f"/exit_inputs/{key}" for key in case["exit_inputs"]}}, {"id": "funding", "kind": "funding", "input": {"funds": [{"id": "cash", "kind": "cash", "balance": "0", "reserve": "0"}], "events": [{"id": "proceeds", "date": "2026-11-01", "kind": "receipt", "amount": None, "fund": "cash", "status": "confirmed"}, {"id": "bill", "date": "2026-11-02", "kind": "payment", "amount": "100000", "allowed_funds": ["cash"]}]}, "input_refs": {"/events/0/amount": "/assessment_results/exit/assessment/cash_after_supplied_refunds"}}]
        result = evaluate_case(case)
        self.assertEqual(result["assessment_results"]["funding"]["assessment"]["total_unfunded"], "0.00")

    def test_reference_does_not_strip_unknown_state_into_a_known_scalar(self) -> None:
        from advisor_workflow import resolve_pointer
        self.assertIsNone(resolve_pointer({"fact": {"state": "unknown", "value": "2030"}}, "/fact/value"))


if __name__ == "__main__":
    unittest.main()
