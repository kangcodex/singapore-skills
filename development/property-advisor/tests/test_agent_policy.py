"""Policy tables + calculators for the agent mode (no network, Decimal only).

Run: python3 -m unittest discover -s development/property-advisor/tests
"""
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_money as am  # noqa: E402
import agent_policy as ap  # noqa: E402

POLICY = ap.load_policy()


class TestMoney(unittest.TestCase):
    def test_pmt_known_value(self):
        self.assertEqual(am.monthly_payment(D("1000000"), D("0.03"), 30), D("4216.04"))

    def test_pmt_zero_rate(self):
        self.assertEqual(am.monthly_payment(D("120000"), D("0"), 10), D("1000.00"))

    def test_balance_after_full_term_is_zero(self):
        self.assertEqual(am.loan_balance(D("500000"), D("0.035"), 25, 25 * 12), D("0.00"))

    def test_balance_after_zero_months_is_principal(self):
        self.assertEqual(am.loan_balance(D("500000"), D("0.035"), 25, 0), D("500000.00"))

    def test_no_floats_returned(self):
        self.assertIsInstance(am.monthly_payment(D("1"), D("0.03"), 1), D)


class TestPolicyFile(unittest.TestCase):
    def test_every_item_is_dated_and_sourced(self):
        self.assertEqual(ap.validate_policy(POLICY), [])

    def test_validator_flags_missing_as_of(self):
        bad = {"items": {"x": {"source_url": "https://a.gov.sg", "status": "verified"}}}
        self.assertTrue(any("as_of" in e for e in ap.validate_policy(bad)))

    def test_validator_flags_unverified_without_reason(self):
        bad = {"items": {"x": {"as_of": "2026-01-01", "source_url": "https://a.gov.sg", "status": "unverified"}}}
        self.assertTrue(any("unverified_reason" in e for e in ap.validate_policy(bad)))

    def test_no_float_in_loaded_policy(self):
        def walk(o):
            if isinstance(o, float):
                self.fail("float in policy")
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(POLICY)

    def test_unverified_items_listed(self):
        names = {n for n, _ in ap.unverified_items(POLICY)}
        self.assertIn("hdb_loan", names)
        self.assertNotIn("bsd", names)


class TestPolicySourcesDoc(unittest.TestCase):
    def test_every_policy_item_is_documented(self):
        doc = (SKILL_DIR / "references" / "policy-sources.md").read_text()
        for name in POLICY["items"]:
            self.assertIn(f"`{name}`", doc, name)


class TestStampDuty(unittest.TestCase):
    def test_bsd_tier_boundaries(self):
        cases = {
            "180000": "1800", "360000": "5400", "1000000": "24600",
            "1500000": "44600", "3000000": "119600", "3500000": "149600",
            "600000": "12600",
        }
        for price, duty in cases.items():
            self.assertEqual(ap.bsd(D(price), POLICY), D(duty), price)

    def test_bsd_rounds_down_to_dollar(self):
        self.assertEqual(ap.bsd(D("180001.99"), POLICY), D("1800"))

    def test_absd_by_profile(self):
        sc = lambda n: [{"residency": "sc", "existing_properties": n}]
        self.assertEqual(ap.absd(D("1500000"), sc(0), POLICY), D("0"))
        self.assertEqual(ap.absd(D("1500000"), sc(1), POLICY), D("300000"))
        self.assertEqual(ap.absd(D("1500000"), sc(2), POLICY), D("450000"))
        self.assertEqual(ap.absd(D("1500000"), sc(5), POLICY), D("450000"))
        self.assertEqual(ap.absd(D("1000000"), [{"residency": "spr", "existing_properties": 0}], POLICY), D("50000"))
        self.assertEqual(ap.absd(D("1000000"), [{"residency": "foreigner", "existing_properties": 0}], POLICY), D("600000"))

    def test_absd_joint_buyers_use_highest_rate(self):
        buyers = [{"residency": "sc", "existing_properties": 0},
                  {"residency": "spr", "existing_properties": 0}]
        self.assertEqual(ap.absd(D("1000000"), buyers, POLICY), D("50000"))

    def test_property_tax_owner_occupier(self):
        self.assertEqual(ap.property_tax(D("12000"), POLICY), D("0"))
        self.assertEqual(ap.property_tax(D("20000"), POLICY), D("320"))
        self.assertEqual(ap.property_tax(D("50000"), POLICY), D("1720"))


class TestLoanLimits(unittest.TestCase):
    def test_ltv_standard_and_lower(self):
        self.assertEqual(ap.ltv_limit(0, 30, 60, False, POLICY), (D("0.75"), D("0.05")))
        self.assertEqual(ap.ltv_limit(0, 31, 60, False, POLICY), (D("0.55"), D("0.10")))
        self.assertEqual(ap.ltv_limit(0, 25, 66, False, POLICY), (D("0.55"), D("0.10")))
        self.assertEqual(ap.ltv_limit(0, 25, 60, True, POLICY), (D("0.75"), D("0.05")))
        self.assertEqual(ap.ltv_limit(0, 26, 60, True, POLICY), (D("0.55"), D("0.10")))

    def test_ltv_with_existing_loans(self):
        self.assertEqual(ap.ltv_limit(1, 30, 60, False, POLICY), (D("0.45"), D("0.25")))
        self.assertEqual(ap.ltv_limit(2, 30, 60, False, POLICY), (D("0.35"), D("0.25")))
        self.assertEqual(ap.ltv_limit(4, 35, 60, False, POLICY), (D("0.15"), D("0.25")))

    def test_max_tenure(self):
        self.assertEqual(ap.max_tenure_years(True, POLICY), 30)
        self.assertEqual(ap.max_tenure_years(False, POLICY), 35)

    def test_tdsr_boundary(self):
        ok = ap.tdsr_check(D("10000"), D("1000"), D("4500"), POLICY)
        self.assertTrue(ok["pass"])
        self.assertEqual(ok["ratio"], D("0.5500"))
        self.assertFalse(ap.tdsr_check(D("10000"), D("1000"), D("4501"), POLICY)["pass"])

    def test_msr_boundary(self):
        self.assertTrue(ap.msr_check(D("10000"), D("3000"), POLICY)["pass"])
        self.assertFalse(ap.msr_check(D("10000"), D("3001"), POLICY)["pass"])

    def test_stress_rate_floor(self):
        self.assertEqual(ap.stress_rate(D("0.025"), False, POLICY), D("0.04"))
        self.assertEqual(ap.stress_rate(D("0.05"), False, POLICY), D("0.05"))
        self.assertEqual(ap.stress_rate(D("0.026"), True, POLICY), D("0.03"))

    def test_zero_income_does_not_divide(self):
        self.assertFalse(ap.tdsr_check(D("0"), D("0"), D("100"), POLICY)["pass"])


class TestGrants(unittest.TestCase):
    def test_ehg_tiers(self):
        self.assertEqual(ap.ehg(D("1500"), POLICY), D("120000"))
        self.assertEqual(ap.ehg(D("1501"), POLICY), D("110000"))
        self.assertEqual(ap.ehg(D("8000"), POLICY), D("20000"))
        self.assertEqual(ap.ehg(D("9000"), POLICY), D("5000"))
        self.assertEqual(ap.ehg(D("9001"), POLICY), D("0"))


if __name__ == "__main__":
    unittest.main()
