"""Tests for mrt-rerouter-skill. Stdlib unittest only. All fetchers mocked."""

import importlib.util
import os
import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "mrt_rerouter.py"


def _load_skill_api():
    api_path = SKILL_DIR / "scripts" / "singapore_api.py"
    spec = importlib.util.spec_from_file_location("singapore_api", api_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_script(api_mod):
    spec = importlib.util.spec_from_file_location("mrt_rerouter", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _MRTRerouterBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _load_skill_api()
        cls.script = _load_script(cls.api)


class TestFindNearestStation(_MRTRerouterBase):

    def test_finds_bishan_for_bishan_coords(self):
        code, walk = self.script.find_nearest_station(1.3508, 103.8494)
        self.assertEqual(code, "NS17")

    def test_returns_none_when_far_from_any_station(self):
        code, walk = self.script.find_nearest_station(1.0, 103.0)
        self.assertIsNone(code)
        self.assertIsNone(walk)

    def test_returns_walk_minutes_rounded(self):
        code, walk = self.script.find_nearest_station(1.3520, 103.8494)
        self.assertEqual(code, "NS17")
        self.assertIsInstance(walk, int)


class TestMrtDataHelpers(_MRTRerouterBase):

    def test_disruption_flag_string_true(self):
        self.assertTrue(self.script.mrt_data_has_disruption({"Disruption": {"status": "active"}}))

    def test_disruption_flag_inside_items(self):
        self.assertTrue(self.script.mrt_data_has_disruption(
            {"items": [{"NextTrain": [], "Disruption": {"status": "active"}}]}
        ))

    def test_status_lowercase_delayed(self):
        self.assertTrue(self.script.mrt_data_has_disruption({"Status": "delayed"}))

    def test_error_envelope_not_treated_as_disruption(self):
        self.assertFalse(self.script.mrt_data_has_disruption({"error": "key_unset"}))

    def test_normal_no_disruption(self):
        self.assertFalse(self.script.mrt_data_has_disruption({"items": [{"NextTrain": []}]}))

    def test_non_dict_is_not_disruption(self):
        self.assertFalse(self.script.mrt_data_has_disruption(None))


class TestNextTrainMin(_MRTRerouterBase):

    def test_numeric_eta_returned_as_float(self):
        mrt = {"items": [{"NextTrain": [{"EstimatedArrival": 4.0}]}]}
        self.assertEqual(self.script.next_train_min(mrt), 4.0)

    def test_empty_next_train_returns_none(self):
        self.assertIsNone(self.script.next_train_min({"items": [{"NextTrain": []}]}))

    def test_missing_items_returns_none(self):
        self.assertIsNone(self.script.next_train_min({"result": {"records": []}}))

    def test_garbage_eta_string_returns_none(self):
        mrt = {"items": [{"NextTrain": [{"EstimatedArrival": "not-a-date"}]}]}
        self.assertIsNone(self.script.next_train_min(mrt))


class TestIsHeavyRain(_MRTRerouterBase):

    def test_matches_heavy_thundery_showers(self):
        self.assertTrue(self.script.is_heavy_rain({"items": [{"forecast": "Heavy thundery showers"}]}))

    def test_matches_heavy_rain(self):
        self.assertTrue(self.script.is_heavy_rain({"items": [{"forecast": "Heavy rain"}]}))

    def test_fair_weather_not_heavy(self):
        self.assertFalse(self.script.is_heavy_rain({"items": [{"forecast": "Fair"}]}))

    def test_empty_items_not_heavy(self):
        self.assertFalse(self.script.is_heavy_rain({"items": []}))

    def test_non_dict_not_heavy(self):
        self.assertFalse(self.script.is_heavy_rain(None))


class TestPsiNational(_MRTRerouterBase):

    def test_reads_national_value(self):
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 142}}}]}
        self.assertEqual(self.script.psi_national(psi), 142)

    def test_unhealthy_threshold(self):
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 101}}}]}
        self.assertEqual(self.script.psi_national(psi), 101)

    def test_missing_national_returns_none(self):
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {}}}]}
        self.assertIsNone(self.script.psi_national(psi))

    def test_empty_items_returns_none(self):
        self.assertIsNone(self.script.psi_national({"items": []}))

    def test_string_national_cast(self):
        psi = {"items": [{"readings": {"psi_twenty_four_hourly": {"national": "85"}}}]}
        self.assertEqual(self.script.psi_national(psi), 85)


class TestBuildMrtRoutes(_MRTRerouterBase):

    def test_no_route_when_missing_station(self):
        self.assertEqual(self.script.build_mrt_routes(None, "NS22", {}, 5, 5), [])

    def test_builds_route_with_normal_mrt_data(self):
        mrt = {"items": [{"NextTrain": [{"EstimatedArrival": 3.0}]}]}
        r = self.script.build_mrt_routes("NS17", "CG2", mrt, 5, 5)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["mode"], "mrt+walk")
        self.assertEqual(r[0]["verdict"], "normal")
        self.assertGreater(r[0]["eta_min"], 0)

    def test_disruption_flagged(self):
        mrt = {"Disruption": {"status": "active"},
               "items": [{"NextTrain": [{"EstimatedArrival": 3.0}]}]}
        r = self.script.build_mrt_routes("NS17", "CG2", mrt, 5, 5)
        self.assertEqual(r[0]["verdict"], "disrupted")
        self.assertIn("MRT line disrupted", r[0]["disruptions"])


class TestBuildBusRoutes(_MRTRerouterBase):

    def test_no_route_when_no_bus_data(self):
        self.assertEqual(self.script.build_bus_routes(1.3, 103.8, 1.3, 103.9, None), [])

    def test_builds_route_from_bus_data(self):
        bus = {"items": [{"NextBus": [{"EstimatedArrival": 12.0}]}]}
        r = self.script.build_bus_routes(1.3, 103.8, 1.3, 103.9, bus)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["mode"], "bus")
        self.assertEqual(r[0]["eta_min"], 12.0)


class TestApplyDowngrades(_MRTRerouterBase):

    def setUp(self):
        self.routes = [
            {"mode": "mrt+walk", "eta_min": 40.0, "walk_m": 600, "verdict": "normal", "disruptions": []},
            {"mode": "bus", "eta_min": 50.0, "walk_m": 0, "verdict": "normal", "disruptions": []},
        ]

    def test_no_downgrade_when_all_clear(self):
        out = self.script.apply_downgrades(self.routes, psi_value=50, heavy_rain=False, slow_camera=False)
        self.assertEqual(out[0]["eta_min"], 40.0)
        self.assertEqual(out[1]["eta_min"], 50.0)

    def test_psi_101_adds_5_min_to_long_walk(self):
        out = self.script.apply_downgrades(self.routes, psi_value=101, heavy_rain=False, slow_camera=False)
        self.assertEqual(out[0]["eta_min"], 45.0)
        self.assertEqual(out[1]["eta_min"], 50.0)

    def test_heavy_rain_adds_10_min_to_bus(self):
        out = self.script.apply_downgrades(self.routes, psi_value=50, heavy_rain=True, slow_camera=False)
        self.assertEqual(out[0]["eta_min"], 40.0)
        self.assertEqual(out[1]["eta_min"], 60.0)

    def test_slow_camera_adds_10_min_to_bus(self):
        out = self.script.apply_downgrades(self.routes, psi_value=50, heavy_rain=False, slow_camera=True,
                                           bus_segment_lat=1.3, bus_segment_lon=103.8)
        self.assertEqual(out[0]["eta_min"], 40.0)
        self.assertEqual(out[1]["eta_min"], 60.0)

    def test_cumulative_psi_plus_rain(self):
        out = self.script.apply_downgrades(self.routes, psi_value=110, heavy_rain=True, slow_camera=True,
                                           bus_segment_lat=1.3, bus_segment_lon=103.8)
        self.assertEqual(out[0]["eta_min"], 45.0)
        self.assertEqual(out[1]["eta_min"], 70.0)

    def test_psi_under_threshold_does_not_penalise_walk(self):
        routes = [{"mode": "mrt+walk", "eta_min": 30.0, "walk_m": 500, "verdict": "normal", "disruptions": []}]
        out = self.script.apply_downgrades(routes, psi_value=100, heavy_rain=False, slow_camera=False)
        self.assertEqual(out[0]["eta_min"], 30.0)

    def test_psi_penalty_adds_disruption_string(self):
        routes = [{"mode": "mrt+walk", "eta_min": 30.0, "walk_m": 500, "verdict": "normal", "disruptions": []}]
        out = self.script.apply_downgrades(routes, psi_value=130, heavy_rain=False, slow_camera=False)
        self.assertEqual(out[0]["eta_min"], 35.0)
        self.assertTrue(any("PSI" in d for d in out[0]["disruptions"]))


class TestRankRoutes(_MRTRerouterBase):

    def test_sort_by_eta_ascending(self):
        routes = [
            {"mode": "bus", "eta_min": 60.0, "verdict": "normal"},
            {"mode": "mrt+walk", "eta_min": 30.0, "verdict": "normal"},
        ]
        out = self.script.rank_routes(routes)
        self.assertEqual(out[0]["mode"], "mrt+walk")

    def test_disrupted_route_pushed_last(self):
        routes = [
            {"mode": "mrt+walk", "eta_min": 10.0, "verdict": "disrupted"},
            {"mode": "bus", "eta_min": 50.0, "verdict": "normal"},
        ]
        out = self.script.rank_routes(routes)
        self.assertEqual(out[0]["mode"], "bus")
        self.assertEqual(out[-1]["verdict"], "disrupted")


class TestBuildRecommendation(_MRTRerouterBase):

    def test_picks_first_normal_route(self):
        routes = [
            {"mode": "mrt+walk", "eta_min": 30.0, "verdict": "normal"},
            {"mode": "bus", "eta_min": 50.0, "verdict": "disrupted"},
        ]
        rec = self.script.build_recommendation(routes, "A", "B")
        self.assertIn("mrt+walk", rec)
        self.assertIn("30", rec)

    def test_disrupted_route_only_picks_it(self):
        routes = [{"mode": "mrt+walk", "eta_min": 30.0, "verdict": "disrupted"}]
        rec = self.script.build_recommendation(routes, "A", "B")
        self.assertIn("mrt+walk", rec)

    def test_empty_routes_yields_fallback(self):
        rec = self.script.build_recommendation([], "A", "B")
        self.assertIn("No viable route", rec)


class TestAssess(_MRTRerouterBase):

    def setUp(self):
        self._env = os.environ.copy()
        os.environ.pop("DATA_GOV_SG_API_KEY", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _stub_all(self, mrt_data=None, bus_data=None, traffic=None, weather=None, psi=None,
                  geocode=None):
        stack = ExitStack()
        geocode_ret = geocode or (1.3508, 103.8494, "Bishan", "579700")
        stack.enter_context(patch.object(self.api, "geocode", return_value=geocode_ret))
        stack.enter_context(patch.object(self.api, "fetch_lta_bus_arrival", return_value=bus_data or
                                        {"items": [{"NextBus": [{"EstimatedArrival": 12.0}]}]}))
        stack.enter_context(patch.object(self.api, "fetch_lta_traffic_images", return_value=traffic or {"items": []}))
        stack.enter_context(patch.object(self.api, "fetch_two_hour_forecast", return_value=weather or
                                        {"items": [{"forecast": "Fair"}]}))
        stack.enter_context(patch.object(self.api, "fetch_psi", return_value=psi or
                                        {"items": [{"readings": {"psi_twenty_four_hourly": {"national": 50}}}]}))
        if "DATA_GOV_SG_API_KEY" in os.environ:
            stack.enter_context(patch.object(self.api, "fetch_lta_mrt_arrival", return_value=mrt_data or
                                            {"items": [{"NextTrain": [{"EstimatedArrival": 3.0}]}]}))
        return stack

    def test_full_report_with_key_set(self):
        os.environ["DATA_GOV_SG_API_KEY"] = "test_key"
        with self._stub_all(mrt_data={"items": [{"NextTrain": [{"EstimatedArrival": 3.0}]}]}):
            out = self.script.assess("Bishan MRT", "Changi Airport", origin_station="NS17", dest_station="CG2")
        self.assertEqual(out["origin"], "Bishan MRT")
        self.assertGreater(len(out["routes"]), 0)
        self.assertIn("recommendation", out)

    def test_mrt_omitted_when_key_unset(self):
        with self._stub_all():
            out = self.script.assess("Bishan MRT", "Changi Airport", origin_station="NS17", dest_station="CG2")
        self.assertEqual(len(out["routes"]), 1)
        self.assertEqual(out["routes"][0]["mode"], "bus")
        self.assertIn("DATA_GOV_SG_API_KEY unset", out.get("note", ""))

    def test_psi_101_adds_walk_penalty_with_long_walk(self):
        os.environ["DATA_GOV_SG_API_KEY"] = "test_key"
        with self._stub_all(
            geocode=(1.3470, 103.8490, "Bishan South", "579700"),
            psi={"items": [{"readings": {"psi_twenty_four_hourly": {"national": 120}}}]},
            mrt_data={"items": [{"NextTrain": [{"EstimatedArrival": 25.0}]}]},
        ):
            out = self.script.assess("Bishan South", "Changi Airport")
        mrt_routes = [r for r in out["routes"] if r["mode"] == "mrt+walk"]
        self.assertGreater(len(mrt_routes), 0, "no mrt+walk route emitted")
        mrt_route = mrt_routes[0]
        self.assertGreater(mrt_route["walk_m"], 200)
        self.assertTrue(any("PSI" in d for d in mrt_route["disruptions"]))

    def test_heavy_rain_triggers_bus_penalty(self):
        os.environ["DATA_GOV_SG_API_KEY"] = "test_key"
        with self._stub_all(weather={"items": [{"forecast": "Heavy thundery showers"}]}):
            out = self.script.assess("Bishan MRT", "Changi Airport", origin_station="NS17", dest_station="CG2")
        bus_route = next(r for r in out["routes"] if r["mode"] == "bus")
        self.assertGreater(bus_route["eta_min"], 12.0)
        self.assertTrue(any("Heavy rain" in d for d in bus_route["disruptions"]))


class TestModuleImport(_MRTRerouterBase):

    def test_public_surface(self):
        for n in ["assess", "build_mrt_routes", "build_bus_routes", "apply_downgrades",
                  "rank_routes", "build_recommendation", "find_nearest_station",
                  "is_heavy_rain", "psi_national", "mrt_data_has_disruption"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(self.script, n, None)), "%s missing" % n)


if __name__ == "__main__":
    unittest.main()
