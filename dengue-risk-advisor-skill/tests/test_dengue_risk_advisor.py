"""Tests for dengue_risk_advisor.py. Stdlib unittest, no real network."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
API_FILE = SCRIPTS / "singapore_api.py"
SCRIPT_FILE = SCRIPTS / "dengue_risk_advisor.py"


def _import_api():
    spec = importlib.util.spec_from_file_location("singapore_api", API_FILE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_script(api):
    spec = importlib.util.spec_from_file_location("dengue_risk_advisor", SCRIPT_FILE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _import_api()
        cls.mod = _import_script(cls.api)

    def setUp(self):
        sys.modules["singapore_api"] = self.api


class TestClusterCountWithin(_Base):

    def test_empty(self):
        self.assertEqual(self.mod.cluster_count_within([], 1.35, 103.82), 0)

    def test_one_within(self):
        records = [{"lat": 1.3505, "lon": 103.821}]
        self.assertEqual(self.mod.cluster_count_within(records, 1.35, 103.82), 1)

    def test_one_outside(self):
        records = [{"lat": 1.5, "lon": 104.0}]
        self.assertEqual(self.mod.cluster_count_within(records, 1.35, 103.82), 0)

    def test_missing_latlon_skipped(self):
        records = [{"town": "Bedok"}, {"lat": 0, "lon": 0}, {"lat": 1.35, "lon": 103.82}]
        self.assertEqual(self.mod.cluster_count_within(records, 1.35, 103.82), 1)

    def test_non_dict_skipped(self):
        records = [None, "bad", {"lat": 1.35, "lon": 103.82}]
        self.assertEqual(self.mod.cluster_count_within(records, 1.35, 103.82), 1)


class TestTownCentroid(_Base):

    def test_no_records_falls_back_to_sg_centre(self):
        self.assertEqual(self.mod._town_centroid("Nowhere", []), (1.3521, 103.8198))

    def test_matching_records_averaged(self):
        records = [
            {"town": "Bedok", "lat": 1.3, "lon": 103.9},
            {"town": "Bedok", "lat": 1.4, "lon": 104.0},
            {"town": "Tampines", "lat": 1.5, "lon": 105.0},
        ]
        lat, lon = self.mod._town_centroid("Bedok", records)
        self.assertAlmostEqual(lat, 1.35, places=4)
        self.assertAlmostEqual(lon, 103.95, places=4)

    def test_case_insensitive(self):
        records = [{"town": "BEDOK", "lat": 1.3, "lon": 103.9}]
        lat, lon = self.mod._town_centroid("bedok", records)
        self.assertEqual(lat, 1.3)
        self.assertEqual(lon, 103.9)


class TestRainfallTo7D(_Base):

    def test_positive(self):
        self.assertEqual(self.mod._rainfall_to_mm_7d(3.0), 21.0)

    def test_none(self):
        self.assertIsNone(self.mod._rainfall_to_mm_7d(None))

    def test_string_raises_returns_none(self):
        self.assertIsNone(self.mod._rainfall_to_mm_7d("not a number"))

    def test_zero_clamped(self):
        self.assertEqual(self.mod._rainfall_to_mm_7d(0), 0.0)
        self.assertEqual(self.mod._rainfall_to_mm_7d(-1), 0.0)


class TestHistorical7D(_Base):

    def test_normal(self):
        records = [{"rainfall_mm": 100.0 + i} for i in range(24)]
        avg, std = self.mod._historical_mm_7d(records)
        self.assertAlmostEqual(avg, 111.5 * 7 / 30, places=4)
        self.assertGreater(std, 0)

    def test_insufficient_months_returns_none(self):
        records = [{"rainfall_mm": 100.0} for _ in range(11)]
        self.assertEqual(self.mod._historical_mm_7d(records), (None, None))

    def test_empty(self):
        self.assertEqual(self.mod._historical_mm_7d([]), (None, None))

    def test_non_numeric_skipped(self):
        records = [{"rainfall_mm": "bad"}, {"rainfall_mm": None}, {"rainfall_mm": 50.0}]
        records += [{"rainfall_mm": 50.0} for _ in range(12)]
        avg, std = self.mod._historical_mm_7d(records)
        self.assertIsNotNone(avg)
        self.assertAlmostEqual(avg, 50.0 * 7 / 30, places=4)

    def test_value_field_accepted(self):
        records = [{"value": 60.0} for _ in range(24)]
        avg, _ = self.mod._historical_mm_7d(records)
        self.assertAlmostEqual(avg, 60.0 * 7 / 30, places=4)


class TestIsAboveAverage(_Base):

    def test_clearly_above(self):
        self.assertTrue(self.mod.is_above_average_rain(50, 20, 5))

    def test_clearly_below(self):
        self.assertFalse(self.mod.is_above_average_rain(5, 20, 5))

    def test_equal_means_not_above(self):
        self.assertFalse(self.mod.is_above_average_rain(25, 20, 5))

    def test_none_forecast(self):
        self.assertIsNone(self.mod.is_above_average_rain(None, 20, 5))

    def test_none_avg(self):
        self.assertIsNone(self.mod.is_above_average_rain(50, None, 5))

    def test_none_std_treated_as_zero(self):
        self.assertTrue(self.mod.is_above_average_rain(21, 20, None))


class TestRiskScore(_Base):

    def test_zero(self):
        self.assertEqual(self.mod.risk_score(0, False), 0)

    def test_clusters_only(self):
        self.assertEqual(self.mod.risk_score(2, False), 2)

    def test_rain_only(self):
        self.assertEqual(self.mod.risk_score(0, True), 3)

    def test_both(self):
        self.assertEqual(self.mod.risk_score(2, True), 5)

    def test_negative_clamped(self):
        self.assertEqual(self.mod.risk_score(-1, False), 0)


class TestRiskTier(_Base):

    def test_low(self):
        self.assertEqual(self.mod.risk_tier(0, False), "low")

    def test_moderate_1_cluster(self):
        self.assertEqual(self.mod.risk_tier(1, False), "moderate")

    def test_moderate_2_clusters(self):
        self.assertEqual(self.mod.risk_tier(2, False), "moderate")

    def test_moderate_above_avg(self):
        self.assertEqual(self.mod.risk_tier(0, True), "moderate")

    def test_elevated(self):
        self.assertEqual(self.mod.risk_tier(3, True), "elevated")

    def test_3_no_rain_is_moderate(self):
        self.assertEqual(self.mod.risk_tier(3, False), "moderate")

    def test_high(self):
        self.assertEqual(self.mod.risk_tier(5, False), "high")

    def test_high_with_rain(self):
        self.assertEqual(self.mod.risk_tier(7, True), "high")

    def test_unknown_when_rain_unknown(self):
        self.assertEqual(self.mod.risk_tier(0, None), "unknown")


class TestPsiTier(_Base):

    def test_good(self):
        self.assertEqual(self.mod._psi_tier(0), "good")
        self.assertEqual(self.mod._psi_tier(50), "good")

    def test_moderate(self):
        self.assertEqual(self.mod._psi_tier(51), "moderate")
        self.assertEqual(self.mod._psi_tier(100), "moderate")

    def test_unhealthy(self):
        self.assertEqual(self.mod._psi_tier(101), "unhealthy")
        self.assertEqual(self.mod._psi_tier(200), "unhealthy")

    def test_hazardous(self):
        self.assertEqual(self.mod._psi_tier(201), "hazardous")
        self.assertEqual(self.mod._psi_tier(500), "hazardous")

    def test_none(self):
        self.assertEqual(self.mod._psi_tier(None), "unknown")


class TestPsiNational(_Base):

    def test_normal(self):
        env = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 38}}}]}
        self.assertEqual(self.mod._psi_national(env), 38.0)

    def test_missing(self):
        env = {"items": [{"readings": {"psi_twenty_four_hourly": {}}}]}
        self.assertIsNone(self.mod._psi_national(env))

    def test_empty_items(self):
        self.assertIsNone(self.mod._psi_national({"items": []}))

    def test_non_dict(self):
        self.assertIsNone(self.mod._psi_national(None))
        self.assertIsNone(self.mod._psi_national("bad"))


class TestRecommendation(_Base):

    def test_low(self):
        self.assertIn("Low risk", self.mod._recommendation("low", "good"))

    def test_moderate(self):
        self.assertIn("Moderate risk", self.mod._recommendation("moderate", "good"))

    def test_elevated(self):
        self.assertIn("Elevated risk", self.mod._recommendation("elevated", "good"))

    def test_high(self):
        self.assertIn("High risk", self.mod._recommendation("high", "good"))

    def test_unknown(self):
        self.assertIn("Insufficient", self.mod._recommendation("unknown", "good"))

    def test_unhealthy_psi_appended(self):
        msg = self.mod._recommendation("low", "unhealthy")
        self.assertIn("unhealthy", msg.lower())
        self.assertIn("Air", msg)

    def test_hazardous_psi_appended(self):
        msg = self.mod._recommendation("low", "hazardous")
        self.assertIn("Air", msg)


class TestRainfallCurrent(_Base):

    def test_standard(self):
        env = {"items": [{"readings": {"rainfall": 3.5}}]}
        self.assertEqual(self.mod._rainfall_current_mm(env), 3.5)

    def test_value_key(self):
        env = {"items": [{"readings": {"value": 2.0}}]}
        self.assertEqual(self.mod._rainfall_current_mm(env), 2.0)

    def test_data_array(self):
        env = {"items": [{"data": [{"rainfall": 1.5}]}]}
        self.assertEqual(self.mod._rainfall_current_mm(env), 1.5)

    def test_no_data(self):
        self.assertIsNone(self.mod._rainfall_current_mm({}))
        self.assertIsNone(self.mod._rainfall_current_mm({"items": []}))

    def test_string_in_readings_returns_none(self):
        env = {"items": [{"readings": {"rainfall": "bad"}}]}
        self.assertIsNone(self.mod._rainfall_current_mm(env))


class TestAssess(_Base):

    def test_low_scenario(self):
        with patch.object(self.mod, "_town_centroid", return_value=(1.35, 103.82)):
            with patch.object(self.api, "fetch_dengue_clusters", return_value={
                "result": {"records": []}
            }):
                with patch.object(self.api, "fetch_nea_historical_rainfall", return_value={
                    "result": {"records": [{"rainfall_mm": 80.0} for _ in range(24)]}
                }):
                    with patch.object(self.api, "fetch_rainfall", return_value={
                        "items": [{"readings": {"rainfall": 1.0}}]
                    }):
                        with patch.object(self.api, "fetch_psi", return_value={
                            "items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]
                        }):
                            r = self.mod.assess("Bedok", "jog", "2026-06-28")
        self.assertEqual(r["risk_tier"], "low")
        self.assertEqual(r["dengue_clusters_nearby"], 0)
        self.assertIn("Low risk", r["recommendation"])

    def test_elevated_scenario(self):
        clusters = [{"town": "Bedok", "lat": 1.3505, "lon": 103.821}] * 3
        with patch.object(self.api, "fetch_dengue_clusters", return_value={
            "result": {"records": clusters}
        }):
            with patch.object(self.api, "fetch_nea_historical_rainfall", return_value={
                "result": {"records": [{"rainfall_mm": 30.0} for _ in range(24)]}
            }):
                with patch.object(self.api, "fetch_rainfall", return_value={
                    "items": [{"readings": {"rainfall": 20.0}}]
                }):
                    with patch.object(self.api, "fetch_psi", return_value={
                        "items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]
                    }):
                        r = self.mod.assess("Bedok", "jog", "2026-06-28")
        self.assertEqual(r["risk_tier"], "elevated")
        self.assertGreaterEqual(r["dengue_clusters_nearby"], 3)
        self.assertTrue(r["rainfall_forecast_mm_7d"] > r["rainfall_history_avg_mm_7d"])

    def test_high_scenario(self):
        clusters = [{"town": "Bedok", "lat": 1.3505, "lon": 103.821}] * 5
        with patch.object(self.api, "fetch_dengue_clusters", return_value={
            "result": {"records": clusters}
        }):
            with patch.object(self.api, "fetch_nea_historical_rainfall", return_value={
                "result": {"records": [{"rainfall_mm": 30.0} for _ in range(24)]}
            }):
                with patch.object(self.api, "fetch_rainfall", return_value={
                    "items": [{"readings": {"rainfall": 5.0}}]
                }):
                    with patch.object(self.api, "fetch_psi", return_value={
                        "items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]
                    }):
                        r = self.mod.assess("Bedok", "jog", "2026-06-28")
        self.assertEqual(r["risk_tier"], "high")
        self.assertGreaterEqual(r["dengue_clusters_nearby"], 5)

    def test_insufficient_history_uses_unknown_tier(self):
        with patch.object(self.api, "fetch_dengue_clusters", return_value={
            "result": {"records": []}
        }):
            with patch.object(self.api, "fetch_nea_historical_rainfall", return_value={
                "result": {"records": [{"rainfall_mm": 30.0} for _ in range(6)]}
            }):
                with patch.object(self.api, "fetch_rainfall", return_value={
                    "items": [{"readings": {"rainfall": 5.0}}]
                }):
                    with patch.object(self.api, "fetch_psi", return_value={
                        "items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]
                    }):
                        r = self.mod.assess("Bedok", "jog", "2026-06-28")
        self.assertEqual(r["risk_tier"], "unknown")
        self.assertIsNone(r["rainfall_history_avg_mm_7d"])

    def test_psi_unhealthy_appends_air_warning(self):
        with patch.object(self.api, "fetch_dengue_clusters", return_value={
            "result": {"records": []}
        }):
            with patch.object(self.api, "fetch_nea_historical_rainfall", return_value={
                "result": {"records": [{"rainfall_mm": 80.0} for _ in range(24)]}
            }):
                with patch.object(self.api, "fetch_rainfall", return_value={
                    "items": [{"readings": {"rainfall": 1.0}}]
                }):
                    with patch.object(self.api, "fetch_psi", return_value={
                        "items": [{"readings": {"psi_twenty_four_hourly": {"national": 150}}}]
                    }):
                        r = self.mod.assess("Bedok", "jog", "2026-06-28")
        self.assertIn("Air", r["recommendation"])


class TestModuleImport(_Base):

    def test_public_surface(self):
        for name in ["assess", "risk_tier", "risk_score", "cluster_count_within",
                     "is_above_average_rain", "_rainfall_to_mm_7d", "_historical_mm_7d",
                     "_psi_tier", "_psi_national", "_recommendation", "_town_centroid"]:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(self.mod, name, None)))


if __name__ == "__main__":
    unittest.main()
