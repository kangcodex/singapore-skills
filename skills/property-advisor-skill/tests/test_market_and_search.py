"""Matched evidence, scenarios and attainable search outcomes."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestMarket(unittest.TestCase):
    def test_selection_keeps_unknown_area_pending_and_wrong_units_out(self) -> None:
        from advisor_market import assess_comparables
        base = {"kind": "transaction", "property_id": "p", "bedrooms": 3, "area_sqft": "1000", "area_basis": "strata", "price": "1850000", "date": "2026-08-01", "source": "fixture://transaction", "retrieved_at": "2026-10-24"}
        rows = [{**base, "id": "t1"}, {**base, "id": "t2", "area_sqft": None}, {**base, "id": "t3", "area_basis": "land"}, {**base, "id": "t4", "kind": "asking"}, {**base, "id": "t5", "bedrooms": 1}]
        result = assess_comparables({"as_of": "2026-10-24", "subject": {"property_id": "p", "bedrooms": 3, "area_sqft": "1000", "area_basis": "strata", "price": "1900000", "price_kind": "asking"}, "observations": rows})
        self.assertEqual([row["id"] for row in result["selected"]], ["t1"])
        self.assertEqual([row["id"] for row in result["pending"]], ["t2"])
        self.assertEqual(len(result["excluded"]), 3)
        self.assertIsNone(result["fair_value"])

    def test_negative_appreciation_is_an_assumption_not_a_forecast(self) -> None:
        from advisor_market import assess_scenarios
        result = assess_scenarios({"entry_price": "1000000", "years": [1], "scenarios": [{"id": "down", "annual_rate_decimal": "-0.02", "rationale": "User downside stress, not predicted", "evidence_ids": []}]})
        self.assertEqual(result["scenarios"][0]["values"]["1"], "980000.00")
        self.assertEqual(result["status"], "assumptions_not_forecast")

    def test_duplicate_transactions_do_not_inflate_sample(self) -> None:
        from advisor_market import assess_comparables
        row = {"kind": "transaction", "property_id": "p", "bedrooms": 3, "area_sqft": "1000", "area_basis": "strata", "price": "1800000", "date": "2026-08-01", "source": "fixture://one", "retrieved_at": "2026-10-24", "transaction_key": "same-underlying-record"}
        result = assess_comparables({"as_of": "2026-10-24", "subject": {"property_id": "p", "bedrooms": 3, "area_sqft": "1000", "area_basis": "strata"}, "observations": [{**row, "id": "a"}, {**row, "id": "b"}]})
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(len(result["duplicates"]), 1)


class TestSearch(unittest.TestCase):
    def test_hard_failure_unknown_and_duplicate_are_not_silent_fits(self) -> None:
        from advisor_search import assess_search
        requirement = {"id": "rooms", "priority": "hard", "state": "confirmed", "condition": {"kind": "number", "field": "bedrooms", "op": "min", "value": "3", "unit": "count"}}
        rows = [{"id": "a", "property_id": "p", "unit_key": "p:01-01", "identity_status": "confirmed", "availability": "listed", "facts": {"bedrooms": {"state": "known", "value": 3, "unit": "count"}}}, {"id": "b", "property_id": "p", "unit_key": "p:01-01", "identity_status": "confirmed", "availability": "listed", "facts": {"bedrooms": {"state": "known", "value": 3, "unit": "count"}}}, {"id": "c", "property_id": "q", "availability": "listed", "facts": {"bedrooms": {"state": "known", "value": 2, "unit": "count"}}}, {"id": "d", "property_id": "r", "availability": "unknown", "facts": {}}]
        result = assess_search({"as_of": "2026-10-24", "requirements": [requirement], "candidates": rows, "coverage": "fixed pack only"})
        self.assertEqual(result["distinct_candidate_count"], 3)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["rejected"][0]["id"], "c")
        self.assertIn("d", [item["id"] for item in result["conditional"]])
        self.assertEqual(result["verified_available_fits"], [])


if __name__ == "__main__":
    unittest.main()
