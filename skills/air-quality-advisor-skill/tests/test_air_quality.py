#!/usr/bin/env python3
"""Smoke tests for air_quality.py — all network paths mocked."""

import os
import sys
import unittest
from unittest.mock import patch

# Make per-skill scripts/ importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(_HERE, "..", "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def _load_module():
    import importlib
    if "air_quality" in sys.modules:
        del sys.modules["air_quality"]
    return importlib.import_module("air_quality")


def _psi_payload(national=42, west=45, east=39, central=40, north=42, south=44):
    return {
        "items": [
            {"region": "national", "reading": {"psi_twenty_four_hourly": {"national": national}}},
            {"region": "west", "reading": {"psi_twenty_four_hourly": {"national": west}}},
            {"region": "east", "reading": {"psi_twenty_four_hourly": {"national": east}}},
            {"region": "central", "reading": {"psi_twenty_four_hourly": {"national": central}}},
            {"region": "north", "reading": {"psi_twenty_four_hourly": {"national": north}}},
            {"region": "south", "reading": {"psi_twenty_four_hourly": {"national": south}}},
        ]
    }


def _pm25_payload(national=12):
    return {
        "items": [
            {"region": "national", "reading": {"pm25_one_hourly": {"national": national}}}
        ]
    }


def _uv_payload(value=6):
    return {"items": [{"index": [{"value": value}]}]}


def _forecast_payload():
    return {
        "items": [
            {
                "timestamp": "2026-06-22T00:00:00+08:00",
                "forecasts": [
                    {"area": "Bishan", "forecast": "Afternoon thundery showers"},
                    {"area": "Bishan", "temperature": {"low": 25, "high": 33}},
                    {"area": "Bishan", "humidity": {"low": 60, "high": 95}},
                    {"area": "Bishan", "wind": {"speed": {"low": 5, "high": 15}}},
                ],
            },
            {
                "timestamp": "2026-06-23T00:00:00+08:00",
                "forecasts": [
                    {"area": "Bishan", "forecast": "Partly cloudy"},
                    {"area": "Bishan", "temperature": {"low": 26, "high": 34}},
                ],
            },
        ]
    }


class TestLocationResolution(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_address_location(self):
        with patch.object(self.m, "geocode",
                          return_value=("Bishan Park", 1.3615, 103.8485, "579783")):
            out = self.m._resolve_location(self.m.argparse.Namespace(
                location="Bishan Park", postcode=None))
        self.assertEqual(out["source"], "address")
        self.assertEqual(out["address"], "Bishan Park")
        self.assertEqual(out["lat"], 1.3615)
        self.assertEqual(out["lon"], 103.8485)

    def test_postcode_location(self):
        with patch.object(self.m, "geocode",
                          return_value=("Bishan", 1.3508, 103.8494, "570123")):
            out = self.m._resolve_location(self.m.argparse.Namespace(
                location=None, postcode="570123"))
        self.assertEqual(out["source"], "postcode")
        self.assertEqual(out["postcode"], "570123")

    def test_lat_lon_location(self):
        out = self.m._resolve_location(self.m.argparse.Namespace(
            location="1.3508,103.8494", postcode=None))
        self.assertEqual(out["source"], "lat,lon")
        self.assertEqual(out["lat"], 1.3508)
        self.assertEqual(out["lon"], 103.8494)

    def test_postcode_validation(self):
        with self.assertRaises(ValueError):
            self.m._resolve_location(self.m.argparse.Namespace(
                location=None, postcode="12345"))  # only 5 digits


class TestClassification(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_psi_good(self):
        out = self.m._classify_psi(42)
        self.assertEqual(out["band"], "good")
        self.assertIn("outdoor", out["advisory"].lower())

    def test_psi_unhealthy(self):
        out = self.m._classify_psi(180)
        self.assertEqual(out["band"], "unhealthy")
        self.assertIn("sensitive", out["advisory"].lower())

    def test_psi_hazardous(self):
        out = self.m._classify_psi(350)
        self.assertEqual(out["band"], "hazardous")
        self.assertIn("avoid", out["advisory"].lower())

    def test_uv_extreme(self):
        out = self.m._classify_uv(12)
        self.assertEqual(out["band"], "extreme")
        self.assertIn("protect", out["advisory"].lower())

    def test_uv_low(self):
        out = self.m._classify_uv(3)
        self.assertEqual(out["band"], "low")


class TestHealthAdvisory(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_worst_band_wins(self):
        # good + good + extreme → extreme wins
        out = self.m._health_advisory("good", "good", "extreme")
        self.assertIn("extreme", out.lower())

    def test_all_good(self):
        out = self.m._health_advisory("good", "good", "low")
        self.assertIn("good", out.lower())

    def test_all_hazardous(self):
        out = self.m._health_advisory("hazardous", "hazardous", "extreme")
        self.assertIn("avoid", out.lower())


class TestForecastSummary(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_forecast_groups_by_date(self):
        out = self.m._forecast_summary(_forecast_payload())
        self.assertEqual(len(out), 2)
        self.assertIn("date", out[0])
        self.assertIn("forecast", out[0])
        self.assertIn("temperature_low_c", out[0])
        self.assertIn("temperature_high_c", out[0])
        self.assertEqual(out[0]["temperature_low_c"], 25)
        self.assertEqual(out[0]["temperature_high_c"], 33)

    def test_forecast_empty(self):
        out = self.m._forecast_summary({"items": []})
        self.assertEqual(out, [])


class TestAssess(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_assess_all_good(self):
        loc = {"source": "address", "address": "Bishan", "lat": 1.35, "lon": 103.85, "postcode": None}
        with patch.object(self.m, "fetch_psi", return_value=_psi_payload(national=42)), \
             patch.object(self.m, "fetch_pm25", return_value=_pm25_payload(national=12)), \
             patch.object(self.m, "fetch_uv", return_value=_uv_payload(value=5)), \
             patch.object(self.m, "fetch_four_day_forecast", return_value=_forecast_payload()):
            out = self.m.assess(loc)
        self.assertEqual(out["current"]["psi"]["value"], 42)
        self.assertEqual(out["current"]["psi"]["band"], "good")
        self.assertEqual(out["current"]["pm25"]["value"], 12)
        self.assertEqual(out["current"]["uv"]["value"], 5)
        self.assertEqual(out["current"]["uv"]["band"], "moderate")
        self.assertIn("health_advisory", out)
        self.assertEqual(len(out["forecast"]["next_4_days"]), 2)
        self.assertEqual(out["location"]["source"], "address")

    def test_assess_all_hazardous(self):
        loc = {"source": "lat,lon", "address": None, "lat": 1.3, "lon": 103.8, "postcode": None}
        with patch.object(self.m, "fetch_psi", return_value=_psi_payload(national=320)), \
             patch.object(self.m, "fetch_pm25", return_value=_pm25_payload(national=200)), \
             patch.object(self.m, "fetch_uv", return_value=_uv_payload(value=12)), \
             patch.object(self.m, "fetch_four_day_forecast", return_value={"items": []}):
            out = self.m.assess(loc)
        self.assertEqual(out["current"]["psi"]["band"], "hazardous")
        self.assertEqual(out["current"]["pm25"]["band"], "very_unhealthy")
        self.assertEqual(out["current"]["uv"]["band"], "extreme")
        # Worst band across all three drives health_advisory
        self.assertIn("avoid", out["health_advisory"].lower())


class TestModuleImport(unittest.TestCase):

    def test_public_names_importable(self):
        m = _load_module()
        for n in ["assess", "main", "_classify_psi", "_classify_uv",
                  "_health_advisory", "_resolve_location", "HEALTH_BANDS", "UV_BANDS"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n)) or hasattr(m, n),
                                "%s not present" % n)


class TestNoTopLevelNetwork(unittest.TestCase):

    def test_no_network_at_import(self):
        with patch("urllib.request.urlopen") as uo:
            for k in list(sys.modules):
                if k == "air_quality":
                    del sys.modules[k]
            import importlib
            importlib.import_module("air_quality")
        self.assertEqual(uo.call_count, 0)


if __name__ == "__main__":
    unittest.main()
