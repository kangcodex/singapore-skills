#!/usr/bin/env python3
"""Smoke tests for resale-property-advisor-skill. Stdlib only.

Run:
    python3 -m unittest discover -s resale-property-advisor-skill/tests -v
"""

import importlib.util
import json
import os
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_DIR = SKILL_DIR / "scripts"
SCRIPT = SCRIPT_DIR / "resale_property_advisor.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_module():
    spec = importlib.util.spec_from_file_location("resale_property_advisor", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hdb_record(town, flat_type, month, price, x=None, y=None):
    r = {"town": town.lower(), "flat_type": flat_type, "month": month, "resale_price": str(price)}
    if x is not None:
        r["_x"] = x
    if y is not None:
        r["_y"] = y
    return r


def _ura_feature(lu_desc, x, y):
    return {"lu_desc": lu_desc, "_x": x, "_y": y}


class TestPremiumMath(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_premium_pct_above(self):
        self.assertAlmostEqual(self.m.premium_pct(720000, 700000), 2.85714, places=3)

    def test_premium_pct_below(self):
        self.assertAlmostEqual(self.m.premium_pct(680000, 700000), -2.85714, places=3)

    def test_premium_pct_zero_baseline_returns_zero(self):
        self.assertEqual(self.m.premium_pct(720000, 0), 0.0)


class TestToFloat(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_string_with_commas(self):
        self.assertEqual(self.m.to_float("1,234,567.89"), 1234567.89)

    def test_string_no_commas(self):
        self.assertEqual(self.m.to_float("685000.00"), 685000.0)

    def test_int_passthrough(self):
        self.assertEqual(self.m.to_float(685000), 685000.0)

    def test_none_returns_none(self):
        self.assertIsNone(self.m.to_float(None))

    def test_invalid_returns_none(self):
        self.assertIsNone(self.m.to_float("not a number"))


class TestHdbFilter(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_cluster_average_with_three_records(self):
        records = [
            _hdb_record("bishan", "5-ROOM", "2025-12", 600000),
            _hdb_record("bishan", "5-ROOM", "2026-01", 700000),
            _hdb_record("bishan", "5-ROOM", "2026-02", 800000),
        ]
        self.assertAlmostEqual(self.m.cluster_average(records), 700000.0)

    def test_cluster_average_skips_string_prices(self):
        records = [
            _hdb_record("bishan", "5-ROOM", "2025-12", 600000),
            _hdb_record("bishan", "5-ROOM", "2026-01", ""),
            _hdb_record("bishan", "5-ROOM", "2026-02", 800000),
        ]
        self.assertAlmostEqual(self.m.cluster_average(records), 700000.0)

    def test_cluster_average_empty(self):
        self.assertIsNone(self.m.cluster_average([]))

    def test_hdb_records_filters_by_month(self):
        envelope = {"result": {"records": [
            _hdb_record("bishan", "5-ROOM", "2025-11", 500000),
            _hdb_record("bishan", "5-ROOM", "2025-12", 600000),
            _hdb_record("bishan", "5-ROOM", "2026-01", 700000),
        ], "total": 3}}
        with patch.object(self.m, "fetch_datastore_search", return_value=envelope) as fds:
            out = self.m.fetch_hdb_records("bishan", "5-ROOM", "2025-12-01")
        self.assertEqual(len(out), 2)
        prices = [self.m.to_float(r["resale_price"]) for r in out]
        self.assertIn(600000, prices)
        self.assertIn(700000, prices)


class TestUraAmenties(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_future_amenities_from_centroid(self):
        # 2-km spaced URA features with 1 in each of: school, healthcare, MRT
        envelope = {"result": {"records": [
            _ura_feature("PRIMARY SCHOOL", 30000, 39000),  # near centroid
            _ura_feature("HOSPITAL", 30100, 39100),         # ~140m away
            _ura_feature("MRT STATION", 50000, 60000),      # ~25 km away, exclude
            _ura_feature("INDUSTRIAL", 50000, 60000),       # exclude
        ], "total": 4}}
        records = [_hdb_record("bishan", "5-ROOM", "2025-12", 700000, x=30000, y=39000)]
        with patch.object(self.m, "fetch_ura_master_plan", return_value=envelope):
            amenities = self.m.future_amenities("bishan", records)
        self.assertIn("primary_school", amenities)
        self.assertIn("healthcare", amenities)
        self.assertNotIn("MRT", amenities)
        self.assertNotIn("industrial", amenities)

    def test_future_amenities_empty_ura_result(self):
        envelope = {"result": {"records": [], "total": 0}}
        with patch.object(self.m, "fetch_ura_master_plan", return_value=envelope):
            amenities = self.m.future_amenities("bishan", [])
        self.assertEqual(amenities, [])

    def test_future_amenities_falls_back_to_geocode_when_no_centroid(self):
        envelope = {"result": {"records": [_ura_feature("PRIMARY SCHOOL", 29000, 38100)], "total": 1}}
        with patch.object(self.m, "fetch_ura_master_plan", return_value=envelope), \
             patch.object(self.m, "geocode", return_value=("Bishan MRT", 1.3508, 103.8494, "579999")), \
             patch.object(self.m, "svy21_to_wgs84", return_value=(1.3508, 103.8494)):
            amenities = self.m.future_amenities("bishan", [])
        self.assertIn("primary_school", amenities)


class TestRainfallClassification(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_rainfall_above_average(self):
        records = []
        for i in range(24):
            records.append({"total_rainfall_mm": 250.0})
        for i in range(36):
            records.append({"total_rainfall_mm": 150.0})
        envelope = {"result": {"records": records, "total": 60}}
        with patch.object(self.m, "fetch_nea_historical_rainfall", return_value=envelope):
            r = self.m.rainfall_history()
        self.assertEqual(r["classification"], "above-average")

    def test_rainfall_typical(self):
        records = [{"total_rainfall_mm": 170.0}] * 60
        envelope = {"result": {"records": records, "total": 60}}
        with patch.object(self.m, "fetch_nea_historical_rainfall", return_value=envelope):
            r = self.m.rainfall_history()
        self.assertEqual(r["classification"], "typical")

    def test_rainfall_below_average(self):
        records = [{"total_rainfall_mm": 100.0}] * 24 + [{"total_rainfall_mm": 200.0}] * 36
        envelope = {"result": {"records": records, "total": 60}}
        with patch.object(self.m, "fetch_nea_historical_rainfall", return_value=envelope):
            r = self.m.rainfall_history()
        self.assertEqual(r["classification"], "below-average")

    def test_rainfall_empty(self):
        envelope = {"result": {"records": [], "total": 0}}
        with patch.object(self.m, "fetch_nea_historical_rainfall", return_value=envelope):
            r = self.m.rainfall_history()
        self.assertEqual(r["classification"], "unknown")


class TestVerdictMatrix(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_fair_low_premium(self):
        self.assertEqual(self.m.verdict(710000, 700000, ["MRT"], "typical"), "fair")

    def test_premium_justified_with_uplift(self):
        v = self.m.verdict(750000, 700000, ["MRT", "primary_school"], "typical")
        self.assertEqual(v, "premium justified")

    def test_above_market_no_uplift(self):
        v = self.m.verdict(750000, 700000, ["MRT"], "typical")
        self.assertEqual(v, "above market")

    def test_above_market_when_rain_above_avg(self):
        v = self.m.verdict(740000, 700000, ["MRT", "primary_school"], "above-average")
        self.assertEqual(v, "above market")

    def test_premium_justified_high_premium_with_strong_uplift(self):
        v = self.m.verdict(790000, 700000, ["MRT", "primary_school", "healthcare"], "typical")
        self.assertEqual(v, "premium justified")


class TestAssess(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_assess_full_report(self):
        hdb = {"result": {"records": [
            _hdb_record("bishan", "5-ROOM", "2025-12", 700000, x=30000, y=39000),
            _hdb_record("bishan", "5-ROOM", "2026-01", 710000, x=30000, y=39000),
        ], "total": 2}}
        ura = {"result": {"records": [
            _ura_feature("PRIMARY SCHOOL", 30050, 39050),
            _ura_feature("MRT STATION", 30100, 39100),
        ], "total": 2}}
        rain = {"result": {"records": [{"total_rainfall_mm": 170.0}] * 60, "total": 60}}
        with patch.object(self.m, "fetch_datastore_search", return_value=hdb), \
             patch.object(self.m, "fetch_ura_master_plan", return_value=ura), \
             patch.object(self.m, "fetch_nea_historical_rainfall", return_value=rain):
            result = self.m.assess("bishan", "5-ROOM", "2025-12-01", 720000)
        self.assertEqual(result["town"], "BISHAN")
        self.assertEqual(result["flat_type"], "5-ROOM")
        self.assertEqual(result["cluster_avg"], 705000.0)
        self.assertAlmostEqual(result["premium_pct"], 2.1, places=1)
        self.assertIn(result["verdict"], {"fair", "premium justified", "above market"})
        self.assertIn("MRT", result["future_amenities"])
        self.assertIn("primary_school", result["future_amenities"])
        self.assertEqual(result["rainfall_history"]["classification"], "typical")
        self.assertIn("Asking $720,000", result["recommendation"])

    def test_assess_raises_on_unknown_flat_type(self):
        with self.assertRaises(ValueError):
            self.m.assess("bishan", "99-ROOM", "2025-12-01", 720000)

    def test_assess_raises_on_empty_hdb(self):
        hdb = {"result": {"records": [], "total": 0}}
        with patch.object(self.m, "fetch_datastore_search", return_value=hdb):
            with self.assertRaises(ValueError):
                self.m.assess("bishan", "5-ROOM", "2025-12-01", 720000)


class TestRecommendation(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_recommendation_fair_mentions_inspection(self):
        r = self.m.recommendation("fair", 700000, 720000, ["MRT"], "typical")
        self.assertIn("valuation inspection", r)

    def test_recommendation_above_market_mentions_negotiate(self):
        r = self.m.recommendation("above market", 700000, 750000, ["MRT"], "typical")
        self.assertIn("Negotiate down", r)

    def test_recommendation_premium_justified_mentions_amenities(self):
        r = self.m.recommendation("premium justified", 700000, 750000, ["MRT", "primary_school"], "typical")
        self.assertIn("MRT", r)
        self.assertIn("primary_school", r)


class TestModuleImport(unittest.TestCase):

    def test_no_top_level_network(self):
        # If we can import without exceptions and the public surface is there, the
        # module is import-safe. Network would have raised at load time.
        m = _load_module()
        for name in ("assess", "verdict", "premium_pct", "cluster_average", "future_amenities", "rainfall_history", "main"):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(m, name)))


if __name__ == "__main__":
    unittest.main()
