"""Dated liquidity, funding restrictions and exit reconciliation."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestFunding(unittest.TestCase):
    def setUp(self) -> None:
        from advisor_funding import funding_plan, net_exit
        self.funding = funding_plan
        self.exit = net_exit
        self.funds = [{"id": "cash", "kind": "cash", "balance": "100000", "reserve": "20000"}, {"id": "cpf", "kind": "cpf", "balance": "50000", "reserve": "10000", "usable_cap": "50000"}]

    def test_late_proceeds_do_not_fund_an_earlier_payment(self) -> None:
        # Given
        events = [{"id": "deposit", "date": "2026-11-01", "kind": "payment", "amount": "5000", "allowed_funds": ["cash"]}, {"id": "completion", "date": "2026-11-05", "kind": "payment", "amount": "145000", "allowed_funds": ["cash", "cpf"]}, {"id": "sale", "date": "2026-12-01", "kind": "receipt", "amount": "100000", "fund": "cash", "status": "confirmed"}]
        # When
        result = self.funding({"funds": self.funds, "events": events, "strategy": "cpf_first"})
        # Then
        self.assertEqual(result["status"], "shortfall")
        self.assertEqual(result["first_shortfall"]["date"], "2026-11-05")
        self.assertEqual(result["total_unfunded"], "30000.00")

    def test_strategies_use_identical_facts_and_expose_later_cash_need(self) -> None:
        events = [{"id": "flex", "date": "2026-11-01", "kind": "payment", "amount": "90000", "allowed_funds": ["cash", "cpf"]}, {"id": "cash_bill", "date": "2026-11-10", "kind": "payment", "amount": "15000", "allowed_funds": ["cash"]}]
        # When
        result = self.funding({"funds": self.funds, "events": events, "compare_strategies": True})
        # Then
        self.assertEqual(result["strategies"]["cash_first"]["total_unfunded"], "15000.00")
        self.assertEqual(result["strategies"]["cpf_first"]["total_unfunded"], "0.00")

    def test_zero_cpf_cap_applies_to_every_event(self) -> None:
        funds = copy.deepcopy(self.funds)
        funds[1]["usable_cap"] = "0"
        events = [{"id": "deposit", "date": "2026-11-01", "kind": "payment", "amount": "10000", "allowed_funds": ["cash", "cpf"]}, {"id": "monthly", "date": "2026-12-01", "kind": "payment", "amount": "5334.88", "allowed_funds": ["cash", "cpf"]}]
        result = self.funding({"funds": funds, "events": events})
        self.assertTrue(all(row["allocation"].get("cpf", "0.00") == "0.00" for row in result["timeline"]))

    def test_unconfirmed_receipt_is_not_spendable_money(self) -> None:
        events = [{"id": "grant", "date": "2026-11-01", "kind": "receipt", "amount": "100000", "fund": "cash", "status": "unconfirmed"}, {"id": "bill", "date": "2026-11-02", "kind": "payment", "amount": "100000", "allowed_funds": ["cash"]}]
        result = self.funding({"funds": self.funds, "events": events})
        self.assertEqual(result["status"], "conditional")
        self.assertEqual(result["total_unfunded"], "20000.00")

    def test_same_day_unknown_order_is_not_invented(self) -> None:
        events = [{"id": "cash_in", "date": "2026-11-01", "kind": "receipt", "amount": "100000", "fund": "cash", "status": "confirmed"}, {"id": "bill", "date": "2026-11-01", "kind": "payment", "amount": "150000", "allowed_funds": ["cash"]}]
        result = self.funding({"funds": self.funds, "events": events})
        self.assertEqual(result["status"], "unknown")
        self.assertIn("order", " ".join(result["limitations"]))

    def test_later_order_uncertainty_does_not_hide_an_already_proven_shortfall(self) -> None:
        events = [{"id": "early_bill", "date": "2026-11-01", "kind": "payment", "amount": "100000", "allowed_funds": ["cash"]}, {"id": "in", "date": "2026-11-02", "kind": "receipt", "amount": "100000", "fund": "cash", "status": "confirmed"}, {"id": "later_bill", "date": "2026-11-02", "kind": "payment", "amount": "50000", "allowed_funds": ["cash"]}]
        result = self.funding({"funds": self.funds, "events": events})
        self.assertEqual(result["status"], "shortfall")
        self.assertEqual(result["first_shortfall"]["date"], "2026-11-01")
        self.assertEqual(result["total_unfunded"], "20000.00")

    def test_cash_only_obligation_cannot_use_cpf(self) -> None:
        events = [{"id": "bill", "date": "2026-11-01", "kind": "payment", "amount": "100000", "allowed_funds": ["cash"]}]
        result = self.funding({"funds": self.funds, "events": events})
        self.assertEqual(result["total_unfunded"], "20000.00")

    def test_exit_equity_is_not_spendable_cash(self) -> None:
        result = self.exit({"sale_price": "2000000", "loan_redemption": "1200000", "selling_costs": "50000", "cpf_principal_refund": "350000", "cpf_accrued_refund": "30000"})
        self.assertEqual(result["equity_before_costs"], "800000.00")
        self.assertEqual(result["cash_after_supplied_refunds"], "370000.00")

    def test_missing_refund_is_unknown_not_zero(self) -> None:
        result = self.exit({"sale_price": "2000000", "loan_redemption": "1200000", "selling_costs": "50000"})
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["cash_after_supplied_refunds"])

    def test_recurring_net_income_shock_changes_runway_and_monthly_comfort(self) -> None:
        data = {"funds": [{"id": "cash", "kind": "cash", "balance": "5000", "reserve": "1000"}], "allow_assumed_receipts": True, "monthly_cash_limit": "2000", "recurring": [{"id": "salary", "start": "2026-11-01", "months": 4, "kind": "receipt", "amount": "5000", "fund": "cash", "status": "assumed", "changes": [{"from_month": 2, "amount": "0"}]}, {"id": "living", "start": "2026-11-05", "months": 4, "kind": "payment", "amount": "3000", "allowed_funds": ["cash"]}]}
        result = self.funding(data)
        self.assertEqual(result["total_unfunded"], "3000.00")
        self.assertEqual(result["first_shortfall"]["date"], "2027-02-05")
        self.assertEqual(result["comfort_status"], "fail")
        self.assertEqual(result["status"], "conditional")


if __name__ == "__main__":
    unittest.main()
