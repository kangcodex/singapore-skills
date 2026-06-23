"""Tests for rental-yield-calculator-skill (S11a MVP)."""
import json
import os
import sys
import unittest
from unittest.mock import patch

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _load_module():
    import importlib
    if "rental_yield" in sys.modules:
        del sys.modules["rental_yield"]
    if "singapore_api" in sys.modules and sys.modules["singapore_api"].__file__ and SCRIPTS_DIR not in sys.modules["singapore_api"].__file__:
        del sys.modules["singapore_api"]
    return importlib.import_module("rental_yield")


def _ura_envelope():
    return {"result": {"records": [
        {"_x": 30000, "_y": 39000, "lu_desc": "Proposed MRT Station"},
        {"_x": 30100, "_y": 39100, "lu_desc": "Primary School"},
    ]}}


def _rental_records():
    """8 quarters of rentals, last row is the latest."""
    return [
        {"qtr": "2024-Q%d" % i, "property_type": "Non-Landed", "median_rent_psf_pm": 2.0 + i * 0.1, "median_rent": 4500 + i * 50}
        for i in range(1, 5)
    ] + [
        {"qtr": "2025-Q%d" % i, "property_type": "Non-Landed", "median_rent_psf_pm": 2.5 + i * 0.1, "median_rent": 5000 + i * 50}
        for i in range(1, 5)
    ]


def _private_trans_records():
    return [
        {"qtr": "2025-Q1", "property_type": "Non-Landed", "median_psf": 1500, "sale_count": 100},
        {"qtr": "2025-Q2", "property_type": "Non-Landed", "median_psf": 1520, "sale_count": 110},
    ]


class TestYieldCalculation(unittest.TestCase):

    def test_gross_yield_for_private_condo(self):
        m = _load_module()
        # Re-resolve singapore_api to the fresh copy bound to m. The module-
        # level `import singapore_api` at the top of this file is cached
        # from a prior test (which may have loaded a different per-skill
        # copy); after _load_module, m uses the rental-yield per-skill copy.
        import importlib
        sa = importlib.import_module("singapore_api")
        # Geocode point placed close to URA features at SVY21 (30000, 39000)
        # which converts to WGS84 ~(1.3699, 103.8522).
        with patch.object(m, "fetch_ura_rentals", return_value=_rental_records()), \
             patch.object(m, "fetch_ura_private_resi_trans", return_value=_private_trans_records()), \
             patch.object(sa, "geocode", return_value=("District 9", 1.3699, 103.8522, "238859")), \
             patch.object(m, "fetch_ura_master_plan", return_value=_ura_envelope()):
            out = m.calculate(1500000, "District 9", "whole_sg", "Non-Landed", "2025-01")
        # Last rent row: median_rent = 5000 + 4*50 = 5200
        self.assertEqual(out["monthly_rent_estimate"], 5200.0)
        self.assertEqual(out["annual_rent_estimate"], 62400.0)
        # gross = 62400 / 1500000 * 100 = 4.16
        self.assertAlmostEqual(out["gross_yield_pct"], 4.16, places=2)
        # net = 4.16 * 0.85 = 3.536
        self.assertAlmostEqual(out["net_yield_pct"], 3.54, places=2)
        self.assertIn("MRT", out["ura_context"]["future_amenities_within_1km"])

    def test_hdb_town_uses_same_pipeline(self):
        m = _load_module()
        with patch.object(m, "fetch_ura_rentals", return_value=_rental_records()), \
             patch.object(m, "fetch_ura_private_resi_trans", return_value=_private_trans_records()), \
             patch.object(m, "geocode", return_value=("Bishan", 1.3508, 103.8494, "570123")), \
             patch.object(m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = m.calculate(800000, "BISHAN", "outside_central", "Non-Landed", "2025-01")
        # Asking 800k, rent 5200/mth = 62400/yr = 7.8% gross
        self.assertAlmostEqual(out["gross_yield_pct"], 7.8, places=1)
        self.assertEqual(out["region"], "outside_central")
        self.assertEqual(out["ura_context"]["future_amenities_within_1km"], [])


class TestMissingRentData(unittest.TestCase):

    def test_empty_rentals_returns_zero_yield(self):
        m = _load_module()
        with patch.object(m, "fetch_ura_rentals", return_value=[]), \
             patch.object(m, "fetch_ura_private_resi_trans", return_value=_private_trans_records()), \
             patch.object(m, "geocode", return_value=("District 9", 1.305, 103.835, "238859")):
            out = m.calculate(1500000, "District 9", "whole_sg", "Non-Landed", "2025-01")
        self.assertEqual(out["monthly_rent_estimate"], 0.0)
        self.assertEqual(out["annual_rent_estimate"], 0.0)
        self.assertEqual(out["gross_yield_pct"], 0.0)
        self.assertEqual(out["net_yield_pct"], 0.0)
        self.assertEqual(out["trend"]["last_8_quarters"], [])


class TestURAContext(unittest.TestCase):

    def test_no_amenities_in_envelope(self):
        m = _load_module()
        with patch.object(m, "fetch_ura_rentals", return_value=_rental_records()), \
             patch.object(m, "fetch_ura_private_resi_trans", return_value=_private_trans_records()), \
             patch.object(m, "geocode", return_value=("Tuas", 1.32, 103.66, "638xxx")), \
             patch.object(m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = m.calculate(900000, "Tuas", "outside_central", "Non-Landed", "2025-01")
        self.assertEqual(out["ura_context"]["future_amenities_within_1km"], [])


class TestGeocodeFailure(unittest.TestCase):

    def test_geocode_failure_does_not_crash(self):
        m = _load_module()
        with patch.object(m, "fetch_ura_rentals", return_value=_rental_records()), \
             patch.object(m, "fetch_ura_private_resi_trans", return_value=_private_trans_records()), \
             patch.object(m, "geocode", side_effect=ValueError("no results")), \
             patch.object(m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = m.calculate(1200000, "Unknown Town", "whole_sg", "Non-Landed", "2025-01")
        # Should still return a result with unknown location fields
        self.assertEqual(out["location"]["planning_area"], "unknown")
        self.assertEqual(out["location"]["region"], "unknown")
        # URA context should be empty (no lat/lon)
        self.assertEqual(out["ura_context"]["future_amenities_within_1km"], [])


class TestRegionValidation(unittest.TestCase):

    def test_invalid_region_raises(self):
        m = _load_module()
        with self.assertRaises(ValueError):
            m.calculate(1500000, "D9", "narnia", "Non-Landed", "2025-01")


class TestModuleImport(unittest.TestCase):

    def test_public_names_importable(self):
        m = _load_module()
        for n in ["calculate", "main", "trend_block", "location_block", "ura_context", "NET_DEDUCTION", "SPARKLINE_BINS"]:
            with self.subTest(name=n):
                self.assertTrue(getattr(m, n, None) is not None, "%s missing" % n)


if __name__ == "__main__":
    unittest.main()
