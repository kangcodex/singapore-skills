"""Financial regressions from the question-led design spikes."""
from __future__ import annotations

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill" / "scripts"))
import agent_cashflow as cf  # noqa: E402
import agent_policy as ap  # noqa: E402
from advisor_records import Record  # noqa: E402


def scenario(category: str = "resale_condo") -> Record:
    return {"start_date": "2026-11-01", "buyers": [{"age": 32, "residency": "sc", "existing_properties": 0, "outstanding_loans": 0, "monthly_income": "30000", "cpf_oa": "300000", "cpf_oa_monthly": "2000"}], "household": {"cash": "500000", "other_monthly_debts": "0"}, "option": {"name": "Synthetic fixture", "category": category, "price": "1500000", "loan": {"type": "bank", "tenure_years": 25}, "renovation": "0", "furnishing": "0"}}


class TestFinanceRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ap.load_policy()

    def test_zero_cpf_applies_to_fees_and_monthly_instalments(self) -> None:
        # Given
        value = scenario()
        value["option"]["cpf_usable_pct"] = "0"
        value["assumptions"] = {"cpf_pays_fees": True}
        # When
        result = cf.plan(value, self.policy)
        # Then
        self.assertTrue(all(Decimal(row["cpf"]) == 0 for row in result["timeline"]))
        self.assertTrue(all(Decimal(row["cpf_paid"]) == 0 for row in result["monthly_schedule_full"]))

    def test_prorated_usage_is_a_cumulative_property_limit(self) -> None:
        # Given
        value = scenario()
        value["option"]["cpf_usable_pct"] = "0.1"
        # When
        result = cf.plan(value, self.policy)
        # Then
        self.assertLessEqual(Decimal(result["horizon"]["15"]["cpf_used_for_property"]), Decimal("150000"))

    def test_nested_policy_uncertainty_reaches_the_plan(self) -> None:
        # Given / When
        result = cf.plan(scenario(), self.policy)
        # Then
        self.assertIn("absd.joint_buyer_rule", {item["item"] for item in result["unverified_assumptions"]})

    def test_property_count_does_not_substitute_for_outstanding_loans(self) -> None:
        # Given
        value = scenario()
        value["buyers"][0]["existing_properties"] = 1
        del value["buyers"][0]["outstanding_loans"]
        # When
        result = cf.plan(value, self.policy)
        # Then
        self.assertEqual(result["loan"]["ltv"], "0.75")
        self.assertIn("outstanding_loans", " ".join(result["warnings"]))
        self.assertNotEqual(result["verdict"], "affordable")

    def test_completed_resale_ec_does_not_get_construction_payments(self) -> None:
        # Given
        value = scenario("ec")
        value["option"].update({"purchase_route": "resale", "ec_msr_applicable": False})
        # When
        result = cf.plan(value, self.policy)
        # Then
        self.assertNotIn("foundation", {item["stage"] for item in result["timeline"]})
        self.assertEqual({item["name"] for item in result["checks"]}, {"TDSR"})

    def test_actual_progressive_schedule_controls_top_and_occupancy(self) -> None:
        # Given
        value = scenario("new_launch_condo")
        stages = [("booking", "2026-11-01", "0.05"), ("sp_signing", "2026-12-01", "0.15"), ("foundation", "2027-03-01", "0.30"), ("top", "2028-06-01", "0.35"), ("csc", "2028-12-01", "0.15")]
        value["option"]["payment_schedule"] = [{"id": identity, "date": day, "pct": pct, "cash_only": identity == "booking"} for identity, day, pct in stages]
        value["option"]["milestones"] = {"move_in": "2028-09-01", "stamp_duty": "2026-12-15"}
        value["option"]["move_in_deadline"] = "2028-08-01"
        # When
        result = cf.plan(value, self.policy)
        # Then
        by_stage = {item["stage"]: item for item in result["timeline"]}
        self.assertEqual(by_stage["top"]["date"], "2028-06-01")
        self.assertEqual(by_stage["stamp_duty"]["date"], "2026-12-15")
        self.assertEqual(by_stage["move_in"]["date"], "2028-09-01")
        self.assertEqual(result["timing_check"]["result"], "fail")

    def test_incompatible_top_metadata_is_not_silently_ignored(self) -> None:
        # Given
        value = scenario("new_launch_condo")
        value["option"]["expected_top_date"] = "2028-06-01"
        # When / Then
        with self.assertRaisesRegex(ValueError, "payment_schedule"):
            cf.plan(value, self.policy)

    def test_invalid_cpf_fraction_does_not_reach_simulation(self) -> None:
        for fraction in ("-0.1", "1.1", "NaN"):
            value = copy.deepcopy(scenario())
            value["option"]["cpf_usable_pct"] = fraction
            with self.subTest(fraction=fraction), self.assertRaises(ValueError):
                cf.plan(value, self.policy)

    def test_lowest_cost_label_does_not_choose_a_known_infeasible_home(self) -> None:
        from agent_advisor import _lowest_tco
        result = _lowest_tco({"options": [{"name": "cheap", "verdict": "not affordable", "requirement_status": "fail", "tco": {"10": {"total": "10"}}}, {"name": "feasible", "verdict": "affordable", "requirement_status": "pass", "tco": {"10": {"total": "20"}}}]})
        self.assertIn("feasible", result)
        self.assertNotIn("cheap", result)

    def test_different_valuation_requires_actual_loan_and_cash_parameters(self) -> None:
        value = scenario()
        value["option"]["valuation"] = "1400000"
        with self.assertRaisesRegex(ValueError, "valuation"):
            cf.plan(value, self.policy)

    def test_nonfinite_and_negative_purchase_prices_are_rejected(self) -> None:
        for price in ("NaN", "-1", "0"):
            value = scenario()
            value["option"]["price"] = price
            with self.subTest(price=price), self.assertRaises(ValueError):
                cf.plan(value, self.policy)

    def test_duty_uses_higher_supplied_market_value_not_just_asking(self) -> None:
        value = scenario()
        value["option"]["market_value"] = "1600000"
        result = cf.plan(value, self.policy)
        duty = next(item for item in result["timeline"] if item["stage"] == "stamp_duty")
        self.assertEqual(duty["cash"], "49600.00")


if __name__ == "__main__":
    unittest.main()
