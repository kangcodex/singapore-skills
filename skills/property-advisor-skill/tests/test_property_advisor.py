"""
Smoke tests for property_advisor.py (v2 — 5 modes, unified output, CEA verify).

Pattern follows tests/test_singapore_api.py:
  - Load the script via importlib.util.spec_from_file_location
  - Patch all upstream fetchers via unittest.mock
  - All 5 modes (hdb / private / rental / ec / investment) tested end-to-end
  - No top-level network call allowed

Run: python3 -m unittest discover -s skills/property-advisor-skill/tests
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_DIR / "scripts" / "property_advisor.py"
SCRIPTS_DIR = SKILL_DIR / "scripts"


def _load_module():
    # Make `from singapore_api import ...` resolve in the per-skill scripts/ dir.
    scripts_path = str(SCRIPTS_DIR)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("property_advisor", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Shared mock data ───────────────────────────────────────────────────

def _hdb_csv():
    return (
        "month,town,flat_type,resale_price,_x,_y\n"
        "2025-12,bishan,5-ROOM,700000,30000,39000\n"
        "2025-11,bishan,5-ROOM,710000,30050,39020\n"
        "2025-10,bishan,5-ROOM,690000,29900,38900\n"
        "2025-09,bishan,5-ROOM,680000,30100,39100\n"
    )


def _ura_envelope():
    return {
        "result": {
            "records": [
                {"_x": 30100, "_y": 39100, "lu_desc": "Proposed MRT Station", "mpro_use": ""},
                {"_x": 30200, "_y": 39200, "lu_desc": "Primary School", "mpro_use": ""},
            ]
        }
    }


def _rainfall_records():
    return [
        {"total_rainfall_mm": "180"} for _ in range(60)
    ]


def _private_records():
    return [
        {"qtr": f"202{i}-Q1", "median_psf": 1400 + i * 50, "sale_count": 100 - i * 5}
        for i in range(8)
    ]


def _rental_records():
    return [
        {"qtr": f"202{i}-Q1", "median_rent_psf_pm": 4.5 + i * 0.1, "sale_count": 50}
        for i in range(8)
    ]


def _ec_sales_records():
    return [
        {"qtr": f"202{i}-Q1", "median_psf": 1100 + i * 30, "sale_count": 80}
        for i in range(8)
    ]


def _ec_position_records():
    return []


def _pipeline_records():
    return [
        {"series": "In Planning", "qtr": "2026-Q1", "value": 5000.0},
        {"series": "In Planning", "qtr": "2025-Q4", "value": 4500.0},
        {"series": "Under Construction", "qtr": "2026-Q1", "value": 8000.0},
        {"series": "Under Construction", "qtr": "2025-Q4", "value": 7500.0},
    ]


def _unsold_records():
    return [
        {"quarter": "2026-Q1", "unsold_units": 4200},
        {"quarter": "2025-Q4", "unsold_units": 4100},
    ]


def _vacancy_records():
    return [
        {"series": "Vacant", "qtr": "2026-Q1", "value": 6800.0},
        {"series": "Available", "qtr": "2026-Q1", "value": 25000.0},
    ]


def _cea_records():
    return [
        {"registration_no": "R012345X", "name": "Alice Tan", "status": "active", "agency": "ERA"},
    ]


# ── v1 tests (preserved verbatim, just renamed) ────────────────────────

class TestPremiumMath(unittest.TestCase):

    def test_premium_pct_normal(self):
        m = _load_module()
        self.assertAlmostEqual(m.premium_pct(720000, 700000), 2.8571428, places=4)

    def test_premium_pct_zero_baseline(self):
        m = _load_module()
        self.assertEqual(m.premium_pct(720000, 0), 0.0)

    def test_premium_pct_asking_below_baseline(self):
        m = _load_module()
        self.assertAlmostEqual(m.premium_pct(680000, 700000), -2.8571428, places=4)


class TestToFloat(unittest.TestCase):

    def test_string_with_commas(self):
        m = _load_module()
        self.assertEqual(m.to_float("1,234,567"), 1234567.0)

    def test_string_without_commas(self):
        m = _load_module()
        self.assertEqual(m.to_float("1234.5"), 1234.5)

    def test_int(self):
        m = _load_module()
        self.assertEqual(m.to_float(100), 100.0)

    def test_none(self):
        m = _load_module()
        self.assertIsNone(m.to_float(None))

    def test_invalid(self):
        m = _load_module()
        self.assertIsNone(m.to_float("n/a"))


class TestHdbFilter(unittest.TestCase):

    def test_cluster_average_3_records(self):
        m = _load_module()
        self.assertAlmostEqual(m.cluster_average([
            {"resale_price": "600000"},
            {"resale_price": "700000"},
            {"resale_price": "800000"},
        ]), 700000.0)

    def test_cluster_average_skips_empty_prices(self):
        m = _load_module()
        self.assertAlmostEqual(m.cluster_average([
            {"resale_price": "600000"},
            {"resale_price": ""},
            {"resale_price": "900000"},
        ]), 750000.0)

    def test_cluster_average_empty(self):
        m = _load_module()
        self.assertIsNone(m.cluster_average([]))

    def test_hdb_records_filters_by_month(self):
        m = _load_module()
        rows = [
            {"month": "2025-12", "resale_price": "700000"},
            {"month": "2025-11", "resale_price": "690000"},
            {"month": "2025-06", "resale_price": "650000"},
        ]
        with patch.object(m, "fetch_dataset_rows", return_value=rows), \
             patch.object(m, "HDB_RESALE_DATASET_ID", "fake-id"):
            out = m.fetch_hdb_records("BISHAN", "5-ROOM", "2025-10")
        self.assertEqual(len(out), 2)
        self.assertEqual([r["month"] for r in out], ["2025-12", "2025-11"])


class TestUraAmenities(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_future_amenities_uses_centroid(self):
        with patch.object(self.m, "cluster_centroid_easting_northing", return_value=(30000, 39000)), \
             patch.object(self.m, "fetch_ura_master_plan", return_value=_ura_envelope()):
            out = self.m.future_amenities("BISHAN", [{"_x": 30000, "_y": 39000}])
        self.assertIn("MRT", out)
        self.assertIn("primary_school", out)

    def test_future_amenities_empty_ura_result(self):
        with patch.object(self.m, "cluster_centroid_easting_northing", return_value=(30000, 39000)), \
             patch.object(self.m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = self.m.future_amenities("BISHAN", [{"_x": 30000, "_y": 39000}])
        self.assertEqual(out, [])

    def test_future_amenities_geocode_fallback(self):
        with patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=("bishan", 1.3699, 103.8522, "123456")), \
             patch.object(self.m, "fetch_ura_master_plan", return_value=_ura_envelope()):
            out = self.m.future_amenities("BISHAN", [])
        self.assertIn("MRT", out)

    def test_future_amenities_geocode_failure(self):
        with patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=None):
            out = self.m.future_amenities("BISHAN", [])
        self.assertEqual(out, [])


class TestRainfallClassification(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_above_average(self):
        # 24mo recent all high (200) + 5yr includes low (100) -> above-average
        with patch.object(self.m, "fetch_nea_historical_rainfall",
                          return_value=[{"total_rainfall_mm": str(v)} for v in
                                       [200] * 24 + [100] * 36]):
            out = self.m.rainfall_history()
        self.assertEqual(out["classification"], "above-average")

    def test_typical(self):
        with patch.object(self.m, "fetch_nea_historical_rainfall",
                          return_value=[{"total_rainfall_mm": str(150)} for _ in range(60)]):
            out = self.m.rainfall_history()
        self.assertEqual(out["classification"], "typical")

    def test_below_average(self):
        with patch.object(self.m, "fetch_nea_historical_rainfall",
                          return_value=[{"total_rainfall_mm": str(v)} for v in
                                       [50] * 24 + [200] * 36]):
            out = self.m.rainfall_history()
        self.assertEqual(out["classification"], "below-average")

    def test_empty_records(self):
        with patch.object(self.m, "fetch_nea_historical_rainfall", return_value=[]):
            out = self.m.rainfall_history()
        self.assertEqual(out["classification"], "unknown")


class TestVerdictMatrix(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_fair(self):
        self.assertEqual(self.m.verdict(710000, 700000, ["MRT"], "typical"), "fair")

    def test_premium_justified_with_uplift(self):
        # 7% premium + 2 amenities + typical -> premium justified
        self.assertEqual(self.m.verdict(750000, 700000, ["MRT", "primary_school"], "typical"),
                         "premium justified")

    def test_above_market_no_uplift(self):
        # 7% premium + 0 amenities -> above market
        self.assertEqual(self.m.verdict(750000, 700000, [], "typical"), "above market")

    def test_above_market_rain_above_avg(self):
        self.assertEqual(self.m.verdict(750000, 700000, ["MRT", "primary_school"], "above-average"),
                         "above market")

    def test_premium_justified_high_premium_strong_uplift(self):
        # 12% premium + 2 amenities + typical -> premium justified
        self.assertEqual(self.m.verdict(784000, 700000, ["MRT", "primary_school"], "typical"),
                         "premium justified")


class TestAssess(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_full_report(self):
        with patch.object(self.m, "fetch_dataset_rows", return_value=[
            {"month": "2025-12", "town": "bishan", "flat_type": "5-ROOM", "resale_price": "700000"},
        ]), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=(30000, 39000)), \
             patch.object(self.m, "fetch_ura_master_plan", return_value=_ura_envelope()), \
             patch.object(self.m, "fetch_nea_historical_rainfall",
                          return_value=[{"total_rainfall_mm": "150"} for _ in range(60)]), \
             patch.object(self.m, "HDB_RESALE_DATASET_ID", "fake-id"):
            out = self.m.assess_hdb("BISHAN", "5-ROOM", "2025-10", 720000)
        self.assertEqual(out["town"], "BISHAN")
        self.assertEqual(out["verdict"], "fair")
        self.assertEqual(out["cluster_avg"], 700000.0)
        self.assertIn("trend", out)
        self.assertIn("location", out)
        self.assertIn("ura_context", out)
        self.assertIsNone(out["cea_verification"])

    def test_unknown_flat_type_raises(self):
        m = _load_module()
        with self.assertRaises(ValueError):
            m.assess_hdb("BISHAN", "INVALID", "2025-10", 720000)

    def test_no_hdb_records_raises(self):
        m = _load_module()
        with patch.object(m, "fetch_dataset_rows", return_value=[]), \
             patch.object(m, "HDB_RESALE_DATASET_ID", "fake-id"):
            with self.assertRaises(ValueError):
                m.assess_hdb("BISHAN", "5-ROOM", "2025-10", 720000)


class TestRecommendation(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_fair_mentions_inspection(self):
        out = self.m.recommendation("fair", 700000, 710000, ["MRT"], "typical")
        self.assertIn("inspection", out.lower())

    def test_above_market_mentions_negotiate(self):
        out = self.m.recommendation("above market", 700000, 800000, [], "typical")
        self.assertIn("negotiate", out.lower())

    def test_premium_justified_mentions_amenities(self):
        out = self.m.recommendation("premium justified", 700000, 750000, ["MRT", "school"], "typical")
        self.assertIn("amenities", out.lower())


class TestModuleImport(unittest.TestCase):

    def test_public_names_importable(self):
        m = _load_module()
        for n in [
            "assess_hdb", "assess_private", "assess_rental", "assess_ec",
            "assess_investment", "trend_block", "sparkline",
            "investment_overlay_for", "cea_verification", "location_block",
        ]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n)), "%s not callable" % n)


# ── v2 tests: new modes, unified output, CEA verify ───────────────────

class TestSparkline(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_sparkline_8_bins_for_8_values(self):
        out = self.m.sparkline([1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(len(out), 8)
        for ch in out:
            self.assertIn(ch, self.m.SPARKLINE_BINS)

    def test_sparkline_monotonic_increasing(self):
        out = self.m.sparkline([0, 100, 200, 300, 400, 500, 600, 700])
        # First char must be lowest, last char must be highest
        self.assertEqual(out[0], self.m.SPARKLINE_BINS[0])
        self.assertEqual(out[-1], self.m.SPARKLINE_BINS[-1])

    def test_sparkline_flat_series(self):
        out = self.m.sparkline([5, 5, 5, 5, 5, 5, 5, 5])
        self.assertEqual(out, self.m.SPARKLINE_BINS[0] * 8)

    def test_sparkline_empty(self):
        self.assertEqual(self.m.sparkline([]), "")


class TestTrendBlock(unittest.TestCase):

    def test_trend_block_qoq_yoy_computed(self):
        m = _load_module()
        records = [{"qtr": "2024-Q%d" % i, "value": float(100 + i * 5)} for i in range(1, 9)]
        out = m.trend_block(records, "value", "qtr", 8)
        self.assertEqual(len(out["last_8_quarters"]), 8)
        self.assertEqual(len(out["sparkline"]), 8)
        # Last value = 140, previous = 135 -> qoq = 3.7%
        self.assertAlmostEqual(out["qoq_pct"], 3.7, places=1)
        # Last value = 140, 4-from-last = 120 -> yoy = 16.7%
        self.assertAlmostEqual(out["yoy_pct"], 16.7, places=1)

    def test_trend_block_empty_records(self):
        m = _load_module()
        out = m.trend_block([], "value", "qtr", 8)
        self.assertEqual(out["last_8_quarters"], [])
        self.assertEqual(out["qoq_pct"], 0.0)
        self.assertEqual(out["yoy_pct"], 0.0)
        self.assertEqual(out["sparkline"], "")


class TestHdbModeV2(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_hdb_mode_unified_output_shape(self):
        with patch.object(self.m, "fetch_dataset_rows", return_value=[
            {"month": f"2025-{m:02d}", "town": "bishan", "flat_type": "5-ROOM",
             "resale_price": str(700000 + m * 1000), "_x": 30000, "_y": 39000}
            for m in range(1, 13)
        ]), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=(30000, 39000)), \
             patch.object(self.m, "fetch_ura_master_plan", return_value=_ura_envelope()), \
             patch.object(self.m, "fetch_nea_historical_rainfall",
                          return_value=[{"total_rainfall_mm": "150"} for _ in range(60)]), \
             patch.object(self.m, "HDB_RESALE_DATASET_ID", "fake-id"):
            out = self.m.assess_hdb("BISHAN", "5-ROOM", "2025-01-01", 720000)
        self.assertEqual(out["mode"], "hdb")
        self.assertIn("trend", out)
        self.assertIn("last_8_quarters", out["trend"])
        self.assertIn("qoq_pct", out["trend"])
        self.assertIn("yoy_pct", out["trend"])
        self.assertIn("sparkline", out["trend"])
        self.assertIn("location", out)
        self.assertIn("town", out["location"])
        self.assertIn("ura_context", out)
        self.assertIn("future_amenities_within_1km", out["ura_context"])
        self.assertIsNone(out["cea_verification"])


class TestPrivateMode(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_private_mode_unified_output_shape(self):
        with patch.object(self.m, "fetch_ura_private_resi_trans", return_value=_private_records()), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=None), \
             patch.object(self.m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = self.m.assess_private("BISHAN", "whole_sg", "2024-01-01", 1800)
        self.assertEqual(out["mode"], "private")
        self.assertEqual(out["as_of_quarter"], "2027-Q1")
        self.assertIn("cluster_median_psf", out)
        self.assertIn("trend", out)
        self.assertIn("location", out)
        self.assertIn("ura_context", out)
        self.assertIsNone(out["cea_verification"])

    def test_private_mode_invalid_region_raises(self):
        # The fetcher should have raised; the assessor passes through.
        m = _load_module()
        with patch.object(m, "fetch_ura_private_resi_trans",
                          side_effect=ValueError("region 'narnia' not in [...]")):
            with self.assertRaises(ValueError):
                m.assess_private("BISHAN", "narnia", "2024-01-01", 1800)


class TestRentalMode(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_rental_mode_unified_output_shape(self):
        with patch.object(self.m, "fetch_ura_rentals", return_value=_rental_records()), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=None), \
             patch.object(self.m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = self.m.assess_rental("BISHAN", "outside_central", "2024-01-01", 6.0)
        self.assertEqual(out["mode"], "rental")
        self.assertEqual(out["as_of_quarter"], "2027-Q1")
        self.assertIn("cluster_median_psf", out)
        self.assertIn("trend", out)
        self.assertIn("location", out)
        self.assertIsNone(out["cea_verification"])


class TestEcMode(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_ec_mode_unified_output_shape(self):
        with patch.object(self.m, "fetch_ura_ec_sales", return_value=_ec_sales_records()), \
             patch.object(self.m, "fetch_ura_ec_position", return_value=_ec_position_records()), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=None), \
             patch.object(self.m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = self.m.assess_ec("BUKIT_BATOK", "2024-01-01", 1200)
        self.assertEqual(out["mode"], "ec")
        self.assertIn("cluster_median_psf", out)
        self.assertIn("trend", out)
        self.assertIn("location", out)
        self.assertIsNone(out["cea_verification"])


class TestInvestmentOverlay(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_investment_mode_populates_overlay(self):
        with patch.object(self.m, "fetch_ura_private_resi_trans", return_value=_private_records()), \
             patch.object(self.m, "fetch_singstat_supply_pipeline", return_value=_pipeline_records()), \
             patch.object(self.m, "fetch_ura_unsold_private_resi", return_value=_unsold_records()), \
             patch.object(self.m, "fetch_singstat_vacancy", return_value=_vacancy_records()), \
             patch.object(self.m, "cluster_centroid_easting_northing", return_value=None), \
             patch.object(self.m, "geocode", return_value=None), \
             patch.object(self.m, "fetch_ura_master_plan", return_value={"result": {"records": []}}):
            out = self.m.assess_investment(
                "BISHAN", "5-ROOM", "2024-01-01", 1800,
                property_mode="private", region="whole_sg",
            )
        self.assertEqual(out["mode"], "investment")
        self.assertEqual(out["property_mode"], "private")
        self.assertIn("investment_overlay", out)
        ovl = out["investment_overlay"]
        self.assertIn("supply_signal", ovl)
        self.assertIn(ovl["supply_signal"], ("tight", "balanced", "surplus"))
        self.assertIn("supply_pipeline_units", ovl)
        self.assertIn("unsold_units", ovl)
        self.assertIn("trailing_4q_demand", ovl)
        self.assertIn("supply_ratio", ovl)
        # With pipeline (13000) + unsold (4200) = 17200, trailing 4Q demand from
        # _private_records: 100, 95, 90, 85, 80, 75, 70, 65 -> last 4 = 70,75,80,85 = 310
        # ratio = 17200/310 ~= 55.5 -> surplus
        self.assertEqual(ovl["supply_signal"], "surplus")


class TestCeaVerification(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_cea_verification_populated(self):
        with patch.object(self.m, "fetch_cea_salesperson", return_value=_cea_records()):
            out = self.m.cea_verification("R012345X")
        self.assertIsNotNone(out)
        self.assertEqual(out["registration_no"], "R012345X")
        self.assertEqual(out["name"], "Alice Tan")
        self.assertEqual(out["status"], "active")
        self.assertEqual(out["agency"], "ERA")

    def test_cea_verification_none_for_empty_query(self):
        m = _load_module()
        self.assertIsNone(m.cea_verification(""))
        self.assertIsNone(m.cea_verification(None))

    def test_cea_verification_none_for_no_match(self):
        with patch.object(self.m, "fetch_cea_salesperson", return_value=[]):
            out = self.m.cea_verification("nobody")
        self.assertIsNone(out)

    def test_cea_verification_failure_returns_none(self):
        with patch.object(self.m, "fetch_cea_salesperson", side_effect=RuntimeError("network down")):
            out = self.m.cea_verification("R012345X")
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
