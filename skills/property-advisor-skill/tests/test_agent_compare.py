"""Alternatives comparison + lifestyle add-ons (no network, Decimal only)."""
import json
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_compare as cmp  # noqa: E402
import agent_policy as ap  # noqa: E402

POLICY = ap.load_policy()


def _buyers():
    return [{"age": a, "residency": "sc", "existing_properties": 0, "monthly_income": "7000",
             "cpf_oa": "150000", "cpf_oa_monthly": "1300"} for a in (33, 31)]


def _scn(addons=None, hdb_addons_override=None):
    hdb = {"name": "4-room HDB", "category": "resale_hdb", "price": "650000",
           "loan": {"type": "hdb", "tenure_years": 25}, "lifestyle_addons": addons or []}
    condo = {"name": "OCR resale condo", "category": "resale_condo", "price": "1500000",
             "loan": {"type": "bank", "tenure_years": 30}}
    return {"start_date": "2026-11-01", "buyers": _buyers(),
            "household": {"cash": "400000", "other_monthly_debts": "0"},
            "options": [condo, hdb]}


class TestAddons(unittest.TestCase):
    def test_catalog_entries_are_dated_sourced_and_flag_operating_status(self):
        self.assertEqual(cmp.validate_catalog(cmp.load_catalog()), [])

    def test_validator_rejects_missing_operating_status(self):
        bad = {"items": {"x": {"label": "x", "as_of": "2026-01-01", "source_url": "https://a.sg",
                               "price_basis": "monthly", "price": "1", "operating": {}}}}
        self.assertTrue(cmp.validate_catalog(bad))

    def test_weekly_price_converts_to_monthly(self):
        a = cmp.price_addon({"id": "virgin_active_long_termer", "count": 1})
        self.assertEqual(a["monthly"], "329.33")  # 76 * 52 / 12

    def test_member_count_scales_after_conversion(self):
        a = cmp.price_addon({"id": "virgin_active_long_termer", "count": 2})
        self.assertEqual(a["monthly"], "658.67")

    def test_user_override_wins_and_is_marked(self):
        a = cmp.price_addon({"id": "virgin_active_long_termer", "count": 2, "monthly": "250"})
        self.assertEqual(a["monthly"], "500.00")
        self.assertEqual(a["price_source"], "user_override")

    def test_unverified_operator_is_flagged(self):
        a = cmp.price_addon({"id": "activesg_gym_peak_pass", "count": 1})
        self.assertEqual(a["operating_status"], "unverified")

    def test_missing_default_requires_user_price(self):
        with self.assertRaises(ValueError):
            cmp.price_addon({"id": "bbq_pit_equivalent"})
        self.assertEqual(cmp.price_addon({"id": "bbq_pit_equivalent", "monthly": "40"})["monthly"], "40.00")

    def test_unknown_addon_and_custom_addon(self):
        with self.assertRaises(ValueError):
            cmp.price_addon({"id": "nope"})
        a = cmp.price_addon({"label": "Private pool club", "monthly": "120"})
        self.assertEqual(a["monthly"], "120.00")
        self.assertEqual(a["operating_status"], "user_supplied")


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.res = cmp.compare(_scn(), POLICY)
        self.by = {o["name"]: o for o in self.res["options"]}

    def test_requires_two_options(self):
        s = _scn()
        s["options"] = s["options"][:1]
        with self.assertRaises(ValueError):
            cmp.compare(s, POLICY)

    def test_side_by_side_fields(self):
        for o in self.res["options"]:
            for k in ("upfront_cash", "upfront_cpf", "monthly_total_commitment",
                      "monthly_cash_outflow", "tco", "equity_built", "verdict"):
                self.assertIn(k, o)
            self.assertEqual(set(o["tco"]), {"5", "10", "15"})

    def test_tco_components_sum_and_include_explicit_opportunity_cost(self):
        t = self.by["OCR resale condo"]["tco"]["10"]
        parts = ("interest", "maintenance_tax_insurance", "duties_fees_and_fit_out",
                 "lifestyle_addons", "opportunity_cost")
        self.assertEqual(sum((D(t[p]) for p in parts), D("0")), D(t["total"]))
        self.assertGreater(D(t["opportunity_cost"]), D("0"))
        self.assertIn("opportunity_cost_assumption", self.res["assumptions"])

    def test_zero_opportunity_rate_zeroes_the_line(self):
        s = _scn()
        s["assumptions"] = {"opportunity_cost": {"cash": "0", "cpf": "0"}}
        t = {o["name"]: o for o in cmp.compare(s, POLICY)["options"]}["4-room HDB"]["tco"]["5"]
        self.assertEqual(D(t["opportunity_cost"]), D("0"))

    def test_condo_costs_more_than_hdb_monthly_and_upfront(self):
        c, h = self.by["OCR resale condo"], self.by["4-room HDB"]
        self.assertGreater(D(c["monthly_total_commitment"]), D(h["monthly_total_commitment"]))
        self.assertGreater(D(c["upfront_cash"]), D(h["upfront_cash"]))

    def test_addons_raise_hdb_cost_and_tco(self):
        plain = cmp.compare(_scn(), POLICY)
        with_a = cmp.compare(_scn([{"id": "virgin_active_long_termer", "count": 2}]), POLICY)
        h0 = {o["name"]: o for o in plain["options"]}["4-room HDB"]
        h1 = {o["name"]: o for o in with_a["options"]}["4-room HDB"]
        self.assertEqual(D(h1["lifestyle_monthly"]), D("658.67"))
        self.assertEqual(D(h1["monthly_total_commitment"]) - D(h0["monthly_total_commitment"]), D("658.67"))
        self.assertGreater(D(h1["tco"]["10"]["total"]), D(h0["tco"]["10"]["total"]))

    def test_breakeven_closes_gap_exactly(self):
        res = cmp.compare(_scn(), POLICY)
        be = res["break_even"][0]
        self.assertEqual(be["cheaper_option"], "4-room HDB")
        self.assertEqual(be["costlier_option"], "OCR resale condo")
        gap = D(be["monthly_commitment_gap"])
        self.assertGreater(gap, D("0"))
        # inject the break-even as a custom monthly add-on: the commitment gap closes to ~0
        s = _scn([{"label": "break-even spend", "monthly": be["breakeven_monthly_lifestyle"]["monthly_commitment"]}])
        again = cmp.compare(s, POLICY)
        a = {o["name"]: o for o in again["options"]}
        diff = D(a["OCR resale condo"]["monthly_total_commitment"]) - D(a["4-room HDB"]["monthly_total_commitment"])
        self.assertLessEqual(abs(diff), D("0.01"))

    def test_breakeven_reports_tco_horizons_and_headroom(self):
        s = _scn([{"id": "virgin_active_long_termer", "count": 2}])
        be = cmp.compare(s, POLICY)["break_even"][0]
        for n in ("5", "10", "15"):
            self.assertIn(n, be["breakeven_monthly_lifestyle"]["tco"])
        self.assertIn("addons_monthly", be)
        self.assertIsInstance(be["addons_close_commitment_gap"], bool)

    def test_summary_lists_unverified_addons(self):
        s = _scn([{"id": "activesg_gym_peak_pass", "count": 2}])
        res = cmp.compare(s, POLICY)
        self.assertTrue(any("activesg_gym_peak_pass" in w for w in res["warnings"]))

    def test_json_safe(self):
        json.dumps(cmp.compare(_scn([{"id": "virgin_active_long_termer", "count": 2}]), POLICY))


if __name__ == "__main__":
    unittest.main()
