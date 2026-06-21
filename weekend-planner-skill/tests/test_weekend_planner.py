"""Smoke tests for weekend_planner.py — pure helpers + mocked network."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPT = _SKILL_DIR / "scripts" / "weekend_planner.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("weekend_planner", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_singapore_api():
    """Load the per-skill singapore_api.py and register it in sys.modules.

    Without the sys.modules registration, the script's `import singapore_api`
    triggers a second load and the test's `patch.object(self.api, ...)` lands
    on a module the script never sees.
    """
    spec = importlib.util.spec_from_file_location(
        "singapore_api", _SKILL_DIR / "scripts" / "singapore_api.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = mod
    spec.loader.exec_module(mod)
    return mod


def _stub_fetch(name, value):
    def _inner(*args, **kwargs):
        return value
    _inner.__name__ = name
    return _inner


class TestPsiTier(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_tier_boundaries(self):
        for v, expected in [(0, "good"), (50, "good"), (51, "moderate"),
                            (100, "moderate"), (101, "unhealthy"),
                            (200, "unhealthy"), (201, "hazardous"), (500, "hazardous")]:
            with self.subTest(v=v):
                self.assertEqual(self.m.psi_tier(v), expected)

    def test_tier_none_is_unknown(self):
        self.assertEqual(self.m.psi_tier(None), "unknown")


class TestUvTier(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_tier_boundaries(self):
        for v, expected in [(0, "low"), (2, "low"), (3, "moderate"),
                            (5, "moderate"), (6, "high"), (7, "high"),
                            (8, "very_high"), (10, "very_high"),
                            (11, "extreme"), (15, "extreme")]:
            with self.subTest(v=v):
                self.assertEqual(self.m.uv_tier(v), expected)

    def test_tier_none_is_unknown(self):
        self.assertEqual(self.m.uv_tier(None), "unknown")


class TestTwoHourAreaMatch(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_picks_exact_substring(self):
        recs = [{"area": "Bukit Timah"}, {"area": "West"}, {"area": "City"}]
        self.assertEqual(self.m._two_hour_area_match(recs, "Bukit Timah Road")["area"], "Bukit Timah")

    def test_picks_when_address_in_area(self):
        recs = [{"area": "City"}, {"area": "West"}]
        self.assertEqual(self.m._two_hour_area_match(recs, "Downtown City")["area"], "City")

    def test_falls_back_to_central(self):
        recs = [{"area": "West"}, {"area": "Central"}, {"area": "East"}]
        self.assertEqual(self.m._two_hour_area_match(recs, "Tampines")["area"], "Central")

    def test_falls_back_to_first(self):
        recs = [{"area": "West"}, {"area": "East"}]
        self.assertEqual(self.m._two_hour_area_match(recs, "Tampines")["area"], "West")

    def test_empty(self):
        self.assertIsNone(self.m._two_hour_area_match([], "Bishan"))


class TestHawkerHelpers(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_find_hawker_case_insensitive(self):
        recs = [{"name": "Adam Road Food Centre"}, {"name": "Tiong Bahru Market"}]
        self.assertEqual(self.m.find_hawker("adam road", recs)["name"], "Adam Road Food Centre")

    def test_find_hawker_no_match(self):
        self.assertIsNone(self.m.find_hawker("nonexistent", [{"name": "X"}]))

    def test_find_hawker_empty_name(self):
        self.assertIsNone(self.m.find_hawker("", [{"name": "X"}]))
        self.assertIsNone(self.m.find_hawker(None, [{"name": "X"}]))

    def test_is_hawker_closed_within_window(self):
        rec = {"next_closure_start": "2026-06-15", "next_closure_end": "2026-06-25"}
        from datetime import date
        self.assertTrue(self.m.is_hawker_closed(rec, today=date(2026, 6, 20)))

    def test_is_hawker_closed_outside_window(self):
        rec = {"next_closure_start": "2026-06-15", "next_closure_end": "2026-06-25"}
        from datetime import date
        self.assertFalse(self.m.is_hawker_closed(rec, today=date(2026, 7, 1)))

    def test_is_hawker_closed_missing_dates(self):
        self.assertFalse(self.m.is_hawker_closed({}))
        self.assertFalse(self.m.is_hawker_closed({"next_closure_start": "2026-06-15"}))

    def test_is_hawker_closed_non_dict(self):
        self.assertFalse(self.m.is_hawker_closed(None))

    def test_nearest_open_hawker_sorted_by_distance(self):
        recs = [
            {"name": "Far", "lat": 1.305, "lon": 103.842,
             "next_closure_start": "2026-12-01", "next_closure_end": "2026-12-15"},
            {"name": "Near", "lat": 1.301, "lon": 103.836,
             "next_closure_start": "2026-12-01", "next_closure_end": "2026-12-15"},
        ]
        from datetime import date
        result = self.m.nearest_open_hawker(1.3, 103.835, recs, today=date(2026, 6, 20))
        self.assertEqual(result[0]["name"], "Near")
        self.assertEqual(len(result), 2)

    def test_nearest_open_hawker_skips_closed(self):
        recs = [
            {"name": "Closed", "lat": 1.301, "lon": 103.836,
             "next_closure_start": "2026-06-01", "next_closure_end": "2026-06-30"},
            {"name": "Open Near", "lat": 1.303, "lon": 103.84,
             "next_closure_start": "2026-12-01", "next_closure_end": "2026-12-15"},
        ]
        from datetime import date
        result = self.m.nearest_open_hawker(1.3, 103.835, recs, today=date(2026, 6, 20))
        names = [r["name"] for r in result]
        self.assertIn("Open Near", names)
        self.assertNotIn("Closed", names)


class TestNearestIndoor(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_picks_nearest_indoor(self):
        recs = [
            {"name": "Outdoor Stadium", "lat": 1.301, "lon": 103.836, "indoor": False},
            {"name": "Far Indoor Hall", "lat": 1.4, "lon": 103.9, "indoor": True},
            {"name": "Near Indoor Hall", "lat": 1.302, "lon": 103.837, "indoor": True},
        ]
        result = self.m.nearest_indoor_active_sg(1.3, 103.835, recs)
        self.assertEqual(result["name"], "Near Indoor Hall")

    def test_no_indoor_returns_none(self):
        recs = [{"name": "X", "lat": 1.3, "lon": 103.8, "indoor": False}]
        self.assertIsNone(self.m.nearest_indoor_active_sg(1.3, 103.8, recs))

    def test_too_far_returns_none(self):
        recs = [{"name": "Far", "lat": 1.5, "lon": 104.0, "indoor": True}]
        self.assertIsNone(self.m.nearest_indoor_active_sg(1.3, 103.8, recs))

    def test_empty_records(self):
        self.assertIsNone(self.m.nearest_indoor_active_sg(1.3, 103.8, []))


class TestBuildRecommendation(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_uv_extreme_with_indoor_pivot(self):
        rec = self.m.build_recommendation(30, 12, "Fair", "outdoors", None, [], {"name": "Bedok Sports Hall"})
        self.assertIn("UV 12", rec)
        self.assertIn("Bedok Sports Hall", rec)

    def test_uv_extreme_no_indoor(self):
        rec = self.m.build_recommendation(30, 12, "Fair", "outdoors", None, [], None)
        self.assertIn("postpone", rec)

    def test_psi_unhealthy_with_indoor(self):
        rec = self.m.build_recommendation(150, 5, "Fair", "outdoors", None, [],
                                          {"name": "Jurong Indoor Hall"})
        self.assertIn("unhealthy", rec)
        self.assertIn("Jurong Indoor Hall", rec)

    def test_psi_unhealthy_no_indoor(self):
        rec = self.m.build_recommendation(150, 5, "Fair", "outdoors", None, [], None)
        self.assertIn("postpone", rec)

    def test_heavy_rain_with_open_hawker(self):
        hawker = {"name": "Adam Road", "lat": 1.3, "lon": 103.8,
                  "next_closure_start": "2026-12-01", "next_closure_end": "2026-12-15"}
        from datetime import date
        rec = self.m.build_recommendation(30, 4, "Heavy Thundery Showers", "makan", hawker, [], None)
        self.assertIn("Heavy rain", rec)
        self.assertIn("Adam Road", rec)

    def test_hawker_closed_with_alternate(self):
        from datetime import date
        closed_hawker = {"name": "Bishan", "lat": 1.3, "lon": 103.835,
                         "next_closure_start": "2026-06-15", "next_closure_end": "2026-06-25"}
        alternate = {"name": "Tiong Bahru", "lat": 1.301, "lon": 103.836}
        # Bypass the date check by passing today inside the closure window
        rec = self.m.build_recommendation(30, 4, "Fair", "makan", closed_hawker, [alternate], None)
        # The recommendation only fires if the hawker is closed; build_recommendation
        # checks is_hawker_closed which uses date.today() by default, so this won't
        # fire with a future-dated closure. Test the path with a current-dated closure.
        current_closed = {"name": "Bishan", "lat": 1.3, "lon": 103.835,
                          "next_closure_start": "2020-01-01", "next_closure_end": "2030-01-01"}
        rec2 = self.m.build_recommendation(30, 4, "Fair", "makan", current_closed, [alternate], None)
        self.assertIn("closed", rec2)
        self.assertIn("Tiong Bahru", rec2)

    def test_moderate_psi_for_outdoor(self):
        rec = self.m.build_recommendation(80, 5, "Fair", "outdoors", None, [], None)
        self.assertIn("moderate", rec.lower())

    def test_all_good(self):
        rec = self.m.build_recommendation(30, 4, "Fair", "general", None, [], None)
        self.assertIn("good", rec.lower())


class TestAssess(unittest.TestCase):

    def setUp(self):
        self.api = _import_singapore_api()
        self.m = _load_module()

    def _patch_all(self, geo, psi, uv, forecast, hawker, activesg):
        return [
            patch.object(self.api, "geocode", return_value=geo),
            patch.object(self.api, "fetch_psi", return_value=psi),
            patch.object(self.api, "fetch_uv", return_value=uv),
            patch.object(self.api, "fetch_two_hour_forecast", return_value=forecast),
            patch.object(self.api, "fetch_hawker_closures", return_value=hawker),
            patch.object(self.api, "fetch_activesg_facilities", return_value=activesg),
        ]

    def _enter(self, patches):
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])

    def test_full_report_minimal(self):
        geo = (1.3508, 103.8494, "Bishan MRT", "579837")
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]}
        uv = {"items": [{"index": 4}]}
        forecast = {"items": [{"forecasts": [{"area": "Central", "forecast": "Fair"}]}]}
        hawker = {"result": {"records": []}}
        activesg = {"result": {"records": []}}
        self._enter(self._patch_all(geo, psi, uv, forecast, hawker, activesg))
        result = self.m.assess("Bishan", "general", "Saturday")
        self.assertEqual(result["psi"]["tier"], "good")
        self.assertEqual(result["uv"]["tier"], "moderate")
        self.assertIn("proceed", result["recommendation"].lower())

    def test_uv_extreme_pivots_to_indoor(self):
        geo = (1.3508, 103.8494, "Bishan", "579837")
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]}
        uv = {"items": [{"index": 12}]}
        forecast = {"items": [{"forecasts": [{"area": "Central", "forecast": "Fair"}]}]}
        hawker = {"result": {"records": []}}
        activesg = {"result": {"records": [
            {"name": "Indoor Hall", "lat": 1.351, "lon": 103.85, "indoor": True}
        ]}}
        self._enter(self._patch_all(geo, psi, uv, forecast, hawker, activesg))
        result = self.m.assess("Bishan", "outdoors", "Saturday noon")
        self.assertEqual(result["uv"]["tier"], "extreme")
        self.assertIn("Indoor Hall", result["recommendation"])

    def test_unresolvable_geocode_raises(self):
        with patch.object(self.api, "geocode", return_value=(None, None, None, None)):
            with self.assertRaises(ValueError):
                self.m.assess("Bishan", "general", "Saturday")

    def test_hawker_closed_pivots_to_alternate(self):
        geo = (1.3508, 103.8494, "Bishan", "579837")
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 30}}}]}
        uv = {"items": [{"index": 4}]}
        forecast = {"items": [{"forecasts": [{"area": "Central", "forecast": "Fair"}]}]}
        hawker = {"result": {"records": [
            {"name": "Bishan Hawker", "lat": 1.3508, "lon": 103.8494,
             "next_closure_start": "2020-01-01", "next_closure_end": "2030-01-01"},
            {"name": "Tiong Bahru", "lat": 1.352, "lon": 103.85,
             "next_closure_start": "2030-01-01", "next_closure_end": "2030-01-15"},
        ]}}
        activesg = {"result": {"records": []}}
        self._enter(self._patch_all(geo, psi, uv, forecast, hawker, activesg))
        result = self.m.assess("Bishan Hawker", "makan", "Saturday")
        self.assertEqual(len(result["hawker_closures"]), 1)
        self.assertTrue(result["hawker_closures"][0]["closed_now"])
        self.assertIn("Tiong Bahru", result["recommendation"])

    def test_psi_national_handles_missing_national(self):
        geo = (1.3, 103.8, "X", "000000")
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {}}}]}
        uv = {"items": [{}]}
        forecast = {"items": [{}]}
        hawker = {"result": {"records": []}}
        activesg = {"result": {"records": []}}
        self._enter(self._patch_all(geo, psi, uv, forecast, hawker, activesg))
        result = self.m.assess("X", "general", "Saturday")
        self.assertEqual(result["psi"]["national"], None)
        self.assertEqual(result["psi"]["tier"], "unknown")


class TestModuleImport(unittest.TestCase):

    def test_public_surface(self):
        m = _load_module()
        for n in ["psi_tier", "uv_tier", "find_hawker", "is_hawker_closed",
                  "nearest_indoor_active_sg", "nearest_open_hawker", "assess", "main"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)), "%s missing" % n)


if __name__ == "__main__":
    unittest.main()
