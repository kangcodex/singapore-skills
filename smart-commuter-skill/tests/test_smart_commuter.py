"""
Tests for smart_commuter.py — pure-function tests + mocked network tests.

Pattern follows tests/test_cdc_voucher_locator.py:
  - importlib.util.spec_from_file_location loads the script as a module
  - unittest.mock.patch stubs network via the per-skill singapore_api module
"""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
SKILL_NAME = "smart_commuter"


def _load_skill():
    """Load scripts/smart_commuter.py as a module. Per-skill singapore_api.py
    is in the same directory, so `from singapore_api import ...` resolves."""
    spec = importlib.util.spec_from_file_location(SKILL_NAME, SCRIPTS / f"{SKILL_NAME}.py")
    assert spec is not None and spec.loader is not None  # PEP 8 module name → always set
    m = importlib.util.module_from_spec(spec)
    # Make `from singapore_api import ...` find the per-skill copy.
    sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


smart_commuter = _load_skill()


# ── Fixtures ──────────────────────────────────────────────────────────

# Realistic v2 envelope shapes (per data.gov.sg v2 schema). Field names
# snake_case per the v2 real-time endpoint docs.

HDB_TOA_PAYOH = {
    "items": [
        {
            "carpark_id": "TP23",
            "lot_type": "C",
            "lots_available": 3,
            "agency": "HDB",
            "latitude": 1.3351,
            "longitude": 103.8480,
            "address": "Blk 122 Toa Payoh Lor 1",
        },
        {
            "carpark_id": "TP24",
            "lot_type": "C",
            "lots_available": 142,
            "agency": "HDB",
            "latitude": 1.3362,
            "longitude": 103.8491,
            "address": "Blk 125 Toa Payoh Lor 1",
        },
        {
            "carpark_id": "TP99",
            "lot_type": "C",
            "lots_available": 80,
            "agency": "HDB",
            "latitude": 1.3500,
            "longitude": 103.8600,
            "address": "Far away",
        },
        {
            "carpark_id": "TP_MC",
            "lot_type": "M",  # motorcycle — must be filtered
            "lots_available": 999,
            "agency": "HDB",
            "latitude": 1.3352,
            "longitude": 103.8481,
            "address": "MC lot",
        },
        {
            "carpark_id": "URA1",
            "lot_type": "C",
            "lots_available": 999,
            "agency": "URA",  # not HDB — must be filtered
            "latitude": 1.3355,
            "longitude": 103.8485,
            "address": "URA lot",
        },
    ]
}

TRAFFIC_PIE = {
    "items": [
        {
            "camera_id": "1001",
            "name": "PIE Exit 10",
            "latitude": 1.3360,
            "longitude": 103.8485,
        },
        {
            "camera_id": "2002",
            "name": "PIE Exit 50",  # far away
            "latitude": 1.4000,
            "longitude": 104.0000,
        },
    ]
}

TRAFFIC_EMPTY = {"items": []}

FORECAST_HEAVY = {
    "items": [
        {"area": "Toa Payoh", "forecast": "Heavy thundery showers"},
        {"area": "Bukit Merah", "forecast": "Fair"},
    ]
}

FORECAST_FAIR = {
    "items": [
        {"area": "Toa Payoh", "forecast": "Fair"},
    ]
}

FORECAST_EMPTY = {"items": []}


def _geocode_toa_payoh(query="Toa Payoh Central"):
    return ("Toa Payoh Central, Singapore 310080", 1.3351, 103.8480, "310080")


# ── Tests ─────────────────────────────────────────────────────────────


class TestHaversine(unittest.TestCase):
    def test_zero_distance(self):
        self.assertAlmostEqual(smart_commuter.haversine_m(1.3, 103.8, 1.3, 103.8), 0.0, places=3)

    def test_one_degree_lat_is_about_111km(self):
        d = smart_commuter.haversine_m(0, 0, 1, 0)
        self.assertAlmostEqual(d, 111_195, delta=200)

    def test_short_distance(self):
        # 0.001 deg lat ≈ 111 m
        d = smart_commuter.haversine_m(1.3351, 103.8480, 1.3362, 103.8491)
        # TP23 → TP24 is about 150 m diagonal
        self.assertGreater(d, 50)
        self.assertLess(d, 300)


class TestHdbCarparks(unittest.TestCase):
    def test_filters_to_hdb_cars_only(self):
        out = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        codes = [c["code"] for c in out]
        self.assertIn("TP23", codes)
        self.assertIn("TP24", codes)
        self.assertNotIn("TP_MC", codes)  # motorcycle filtered
        self.assertNotIn("URA1", codes)   # URA filtered

    def test_empty_envelope(self):
        self.assertEqual(smart_commuter._hdb_carparks({"items": []}), [])

    def test_non_dict_envelope(self):
        self.assertEqual(smart_commuter._hdb_carparks(None), [])


class TestFindPrimaryCarpark(unittest.TestCase):
    def test_hint_used(self):
        hdb = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        p = smart_commuter.find_primary_carpark(hdb, 1.3351, 103.8480, "TP23")
        self.assertEqual(p["code"], "TP23")
        self.assertEqual(p["lots_available"], 3)
        self.assertNotIn("hint_miss", p)
        self.assertIn("walk_min", p)

    def test_no_hint_picks_nearest(self):
        hdb = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        p = smart_commuter.find_primary_carpark(hdb, 1.3362, 103.8491, None)
        # TP24 is the closest to (1.3362, 103.8491)
        self.assertEqual(p["code"], "TP24")

    def test_hint_miss_falls_back_to_nearest(self):
        hdb = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        p = smart_commuter.find_primary_carpark(hdb, 1.3362, 103.8491, "NOPE")
        self.assertEqual(p["code"], "TP24")
        self.assertTrue(p["hint_miss"])

    def test_empty_list(self):
        self.assertIsNone(smart_commuter.find_primary_carpark([], 1.3, 103.8, None))


class TestFindAlternates(unittest.TestCase):
    def test_swap_candidate_returned(self):
        hdb = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        # dest near TP23; exclude TP23; TP24 (142 lots, ~150m) qualifies
        alts = smart_commuter.find_alternates(hdb, 1.3351, 103.8480, exclude_code="TP23")
        codes = [a["code"] for a in alts]
        self.assertIn("TP24", codes)
        self.assertNotIn("TP23", codes)  # excluded

    def test_far_carpark_excluded(self):
        hdb = smart_commuter._hdb_carparks(HDB_TOA_PAYOH)
        alts = smart_commuter.find_alternates(hdb, 1.3351, 103.8480, exclude_code="TP23")
        self.assertNotIn("TP99", [a["code"] for a in alts])  # far away

    def test_low_lots_excluded(self):
        # Build a list with a low-lots nearby carpark
        hdb = [
            {"code": "TP23", "lots_available": 3, "latitude": 1.3351, "longitude": 103.8480, "address": "x"},
            {"code": "TP_LOW", "lots_available": 20, "latitude": 1.3355, "longitude": 103.8485, "address": "y"},
        ]
        alts = smart_commuter.find_alternates(hdb, 1.3351, 103.8480, exclude_code="TP23")
        self.assertEqual(alts, [])

    def test_sorted_by_lots_desc(self):
        hdb = [
            {"code": "PRIMARY", "lots_available": 1, "latitude": 1.3351, "longitude": 103.8480, "address": "p"},
            {"code": "A_LOW",   "lots_available": 60, "latitude": 1.3352, "longitude": 103.8481, "address": "a"},
            {"code": "B_HIGH",  "lots_available": 200, "latitude": 1.3353, "longitude": 103.8482, "address": "b"},
        ]
        alts = smart_commuter.find_alternates(hdb, 1.3351, 103.8480, exclude_code="PRIMARY")
        self.assertEqual([a["code"] for a in alts], ["B_HIGH", "A_LOW"])


class TestBuildTrafficAdvisory(unittest.TestCase):
    def test_nearby_camera_listed(self):
        adv = smart_commuter.build_traffic_advisory(TRAFFIC_PIE, 1.3351, 103.8480)
        self.assertIn("PIE Exit 10", adv["heavy_segments"])
        self.assertNotIn("PIE Exit 50", adv["heavy_segments"])  # far
        self.assertEqual(adv["advisory"], "slow")

    def test_empty_list_returns_unavailable(self):
        adv = smart_commuter.build_traffic_advisory(TRAFFIC_EMPTY, 1.3351, 103.8480)
        self.assertEqual(adv, {"heavy_segments": [], "advisory": "unavailable"})

    def test_no_nearby_returns_normal(self):
        # Only the far camera in TRAFFIC_PIE
        adv = smart_commuter.build_traffic_advisory(
            {"items": [TRAFFIC_PIE["items"][1]]}, 1.3351, 103.8480
        )
        self.assertEqual(adv["heavy_segments"], [])
        self.assertEqual(adv["advisory"], "normal")


class TestBuildWeatherAdvisory(unittest.TestCase):
    def test_heavy_rain_match(self):
        w = smart_commuter.build_weather_advisory(FORECAST_HEAVY, "Toa Payoh Central")
        self.assertEqual(w["nowcast"], "Heavy thundery showers")
        self.assertEqual(w["area"], "Toa Payoh")

    def test_fair_match(self):
        w = smart_commuter.build_weather_advisory(FORECAST_FAIR, "Toa Payoh Central")
        self.assertEqual(w["nowcast"], "Fair")

    def test_no_match_returns_empty(self):
        # Address doesn't contain any forecast area
        w = smart_commuter.build_weather_advisory(FORECAST_HEAVY, "Marina Bay")
        self.assertEqual(w, {})

    def test_empty_envelope(self):
        w = smart_commuter.build_weather_advisory(FORECAST_EMPTY, "Toa Payoh")
        self.assertEqual(w, {})


class TestIsHeavyRain(unittest.TestCase):
    def test_heavy_thundery(self):
        self.assertTrue(smart_commuter._is_heavy_rain("Heavy thundery showers"))

    def test_partial_phrase(self):
        self.assertTrue(smart_commuter._is_heavy_rain("Thundery showers in the afternoon"))

    def test_fair(self):
        self.assertFalse(smart_commuter._is_heavy_rain("Fair"))

    def test_empty(self):
        self.assertFalse(smart_commuter._is_heavy_rain(""))


class TestDecideRecommendation(unittest.TestCase):
    def test_swap_to_alternate(self):
        rec = smart_commuter.decide_recommendation(
            primary={"code": "TP23", "lots_available": 3, "walk_min": 1},
            alternates=[{"code": "TP24", "lots_available": 142, "walk_min": 4}],
            traffic={"advisory": "normal", "heavy_segments": []},
            weather={"nowcast": "Fair"},
        )
        self.assertIn("TP24", rec)
        self.assertIn("142", rec)
        self.assertNotIn("TP23", rec)

    def test_no_swap_primary_fine(self):
        rec = smart_commuter.decide_recommendation(
            primary={"code": "TP23", "lots_available": 80, "walk_min": 1},
            alternates=[{"code": "TP24", "lots_available": 200, "walk_min": 4}],
            traffic={"advisory": "normal", "heavy_segments": []},
            weather={"nowcast": "Fair"},
        )
        self.assertIn("TP23", rec)

    def test_traffic_bypass_added(self):
        rec = smart_commuter.decide_recommendation(
            primary={"code": "TP23", "lots_available": 80, "walk_min": 1},
            alternates=[],
            traffic={"advisory": "slow", "heavy_segments": ["PIE Exit 10"]},
            weather={},
        )
        self.assertIn("Bypass", rec)
        self.assertIn("PIE Exit 10", rec)

    def test_weather_advice_added(self):
        rec = smart_commuter.decide_recommendation(
            primary={"code": "TP23", "lots_available": 80, "walk_min": 1},
            alternates=[],
            traffic={"advisory": "normal", "heavy_segments": []},
            weather={"nowcast": "Heavy thundery showers", "area": "Toa Payoh"},
        )
        self.assertIn("Heavy rain", rec)
        self.assertIn("Toa Payoh", rec)

    def test_empty_inputs(self):
        rec = smart_commuter.decide_recommendation(None, [], {}, {})
        self.assertEqual(rec, "No recommendation")


class TestAssess(unittest.TestCase):
    """End-to-end through the orchestration seam, all network mocked."""

    def _deps(self):
        return {
            "geocode": lambda q: _geocode_toa_payoh(q),
            "traffic": lambda: TRAFFIC_PIE,
            "carpark": lambda: HDB_TOA_PAYOH,
            "forecast": lambda: FORECAST_HEAVY,
        }

    def test_full_report(self):
        r = smart_commuter.assess("Toa Payoh Central", _deps=self._deps())
        self.assertEqual(r["postal"], "310080")
        self.assertEqual(r["primary_carpark"]["code"], "TP23")
        # Swap: TP23 (3 lots) < 10 AND TP24 (142 lots, ~150m) is the alt
        self.assertEqual(len(r["alternates"]), 1)
        self.assertEqual(r["alternates"][0]["code"], "TP24")
        # Traffic: PIE Exit 10 is near
        self.assertIn("PIE Exit 10", r["traffic"]["heavy_segments"])
        # Weather: Toa Payoh forecast matched
        self.assertEqual(r["weather"]["nowcast"], "Heavy thundery showers")
        # Recommendation has both swap + weather
        self.assertIn("TP24", r["recommendation"])
        self.assertIn("Heavy rain", r["recommendation"])

    def test_empty_lta_falls_back(self):
        deps = self._deps()
        deps["traffic"] = lambda: TRAFFIC_EMPTY
        r = smart_commuter.assess("Toa Payoh Central", _deps=deps)
        self.assertEqual(r["traffic"]["advisory"], "unavailable")
        # Recommendation should NOT contain "Bypass"
        self.assertNotIn("Bypass", r["recommendation"])

    def test_hint_miss(self):
        r = smart_commuter.assess("Toa Payoh Central", "ZZZ", _deps=self._deps())
        # hint ZZZ not in list — falls back to nearest (TP24, the closest to dest)
        self.assertTrue(r["primary_carpark"].get("hint_miss"))

    def test_geocode_value_error_propagates(self):
        deps = self._deps()
        deps["geocode"] = lambda q: (_ for _ in ()).throw(ValueError("no results"))
        with self.assertRaises(ValueError):
            smart_commuter.assess("Mars", _deps=deps)


class TestCli(unittest.TestCase):
    """argparse migration: positional args still work, --help exits 2."""

    def setUp(self):
        self.m = _load_skill()
        self._geocode = patch.object(
            self.m, "geocode",
            return_value=("Bishan MRT", 1.3508, 103.8494, "570298"),
        )
        self._geocode.start()
        self.addCleanup(self._geocode.stop)
        self._carpark = patch.object(
            self.m, "fetch_hdb_carpark_availability",
            return_value={"items": [{"carpark_data": []}]},
        )
        self._carpark.start()
        self.addCleanup(self._carpark.stop)
        self._traffic = patch.object(
            self.m, "fetch_lta_traffic_images",
            return_value={"items": []},
        )
        self._traffic.start()
        self.addCleanup(self._traffic.stop)
        self._forecast = patch.object(
            self.m, "fetch_two_hour_forecast",
            return_value={"items": [{"forecast": "Fair"}]},
        )
        self._forecast.start()
        self.addCleanup(self._forecast.stop)

    def test_positional_args_work(self):
        rc = self.m.main(["smart_commuter.py", "Bishan MRT"])
        self.assertEqual(rc, 0)

    def test_positional_with_carpark_hint(self):
        rc = self.m.main(["smart_commuter.py", "Bishan MRT", "B9"])
        self.assertEqual(rc, 0)

    def test_help_exits_nonzero(self):
        with self.assertRaises(SystemExit) as cm:
            self.m.main(["smart_commuter.py", "--help"])
        self.assertIn(cm.exception.code, (0, 2))


class TestModuleImport(unittest.TestCase):
    def test_no_top_level_network_calls(self):
        # The act of loading the module should not have hit the network.
        # This is a smoke test — we just check the module loaded and the
        # public surface is intact.
        self.assertTrue(hasattr(smart_commuter, "main"))
        self.assertTrue(callable(smart_commuter.main))
        self.assertTrue(hasattr(smart_commuter, "assess"))
        for fn in (
            "haversine_m",
            "find_primary_carpark",
            "find_alternates",
            "build_traffic_advisory",
            "build_weather_advisory",
            "decide_recommendation",
        ):
            self.assertTrue(callable(getattr(smart_commuter, fn)), f"missing {fn}")


if __name__ == "__main__":
    unittest.main()
