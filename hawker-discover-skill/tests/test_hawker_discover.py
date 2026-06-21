"""Tests for hawker-discover-skill. All network paths mocked."""
import importlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILL_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = SKILL_DIR.parent / "scripts" / "hawker_discover.py"
API_PATH = SKILL_DIR.parent / "scripts" / "singapore_api.py"


def _load_api():
    spec = importlib.util.spec_from_file_location("singapore_api", API_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_skill():
    spec = importlib.util.spec_from_file_location("hawker_discover", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cdc_json(mode="A", postal="560123", hawker_categories=None, food_places=None, budget_meal=None):
    base = {
        "location": "Ang Mo Kio Ave 3",
        "postal": postal,
        "lat": 1.3693,
        "lon": 103.8494,
        "last_updated": "2026-06-21T08:00:00+08:00",
        "radius": 500,
        "mode": mode,
        "supermarkets": [],
    }
    if mode == "A":
        base["hawker_categories"] = hawker_categories or {
            "🍽 F&B / Dining": [
                {"name": "Ah Lim Chicken Rice", "address": "Blk 123 AMK Ave 3", "dist_m": 210, "LAT": 1.3694, "LON": 103.8495},
            ]
        }
        base["budget_meal"] = []
    elif mode == "B":
        base["food_places"] = food_places or [
            {"name": "Ah Lim Chicken Rice", "address": "Blk 123 AMK Ave 3", "dist_m": 210, "LAT": 1.3694, "LON": 103.8495, "budget": True},
        ]
        base["budget_meal"] = []
    elif mode == "D":
        base["budget_meal"] = budget_meal or [
            {"name": "Cheap Eats", "address": "Blk 456 AMK Ave 4", "dist_m": 320, "LAT": 1.3700, "LON": 103.8490},
        ]
    return base


def _proc(returncode, stdout, stderr=""):
    cp = MagicMock()
    cp.returncode = returncode
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


def _nea(records):
    return {"success": True, "result": {"records": records, "total": len(records)}}


class TestPureHelpers(unittest.TestCase):

    def setUp(self):
        self.m = _load_skill()

    def test_haversine_zero(self):
        self.assertEqual(self.m._haversine_m(1.3, 103.8, 1.3, 103.8), 0)

    def test_haversine_handles_none(self):
        self.assertIsNone(self.m._haversine_m(None, 103.8, 1.3, 103.8))

    def test_haversine_short_distance(self):
        d = self.m._haversine_m(1.3694, 103.8495, 1.3695, 103.8496)
        self.assertGreater(d, 0)
        self.assertLess(d, 30)

    def test_is_food_positive(self):
        self.assertTrue(self.m.is_food("Ah Lim Chicken Rice"))

    def test_is_food_negative(self):
        self.assertFalse(self.m.is_food("Some Hair Salon"))

    def test_categorize_food(self):
        self.assertIn("F&B", self.m.categorize("Good Noodle House"))

    def test_categorize_falls_back_to_other(self):
        self.assertEqual(self.m.categorize("Totally Random Thing XYZ"), "🗂 Other")


class TestInvokeCdc(unittest.TestCase):

    def setUp(self):
        self.m = _load_skill()

    def test_invokes_subprocess(self):
        with patch("subprocess.run", return_value=_proc(0, json.dumps(_cdc_json()))) as run:
            self.m.invoke_cdc("AMK Hub", "A", 500)
        self.assertEqual(run.call_count, 1)
        args = run.call_args[0][0]
        self.assertEqual(args[0], "python3")
        self.assertTrue(str(args[1]).endswith("cdc_voucher_locator.py"))
        self.assertEqual(args[2], "AMK Hub")
        self.assertEqual(args[3], "A")
        self.assertEqual(args[4], "500")

    def test_parses_json(self):
        with patch("subprocess.run", return_value=_proc(0, json.dumps(_cdc_json(postal="560999")))):
            result = self.m.invoke_cdc("AMK", "A", 500)
        self.assertEqual(result["postal"], "560999")

    def test_returns_error_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=_proc(1, "", "boom")):
            result = self.m.invoke_cdc("AMK", "A", 500)
        self.assertIn("error", result)
        self.assertIn("boom", result["error"])

    def test_returns_error_on_bad_json(self):
        with patch("subprocess.run", return_value=_proc(0, "{not json")):
            result = self.m.invoke_cdc("AMK", "A", 500)
        self.assertIn("error", result)
        self.assertIn("invalid JSON", result["error"])


class TestAttachClosure(unittest.TestCase):

    def setUp(self):
        self.m = _load_skill()

    def test_attaches_open_now_true_when_not_in_window(self):
        merchants = [{"name": "Ah Lim", "LAT": 1.3694, "LON": 103.8495}]
        nea = [{
            "name": "AMK Central",
            "lat": 1.3694, "lon": 103.8495,
            "next_closure_start": "2099-01-01",
            "next_closure_end": "2099-01-14",
            "closure_reason": "Quarterly Cleaning",
        }]
        with patch("singapore_api.fetch_hawker_closures", return_value=_nea(nea)):
            out = self.m.attach_closure(merchants, nea, "2026-06-21")
        self.assertTrue(out[0]["open_now"])
        self.assertEqual(out[0]["next_closure"]["start"], "2099-01-01")

    def test_attaches_open_now_false_when_in_window(self):
        merchants = [{"name": "X", "LAT": 1.3694, "LON": 103.8495}]
        nea = [{
            "name": "AMK Central", "lat": 1.3694, "lon": 103.8495,
            "next_closure_start": "2026-06-15", "next_closure_end": "2026-06-28",
            "closure_reason": "Quarterly Cleaning",
        }]
        out = self.m.attach_closure(merchants, nea, "2026-06-21")
        self.assertFalse(out[0]["open_now"])
        self.assertEqual(out[0]["next_closure"]["end"], "2026-06-28")

    def test_no_match_yields_none(self):
        merchants = [{"name": "X", "LAT": 1.3694, "LON": 103.8495}]
        nea = [{"name": "Far", "lat": 1.400, "lon": 104.000,
                "next_closure_start": "2099-01-01", "next_closure_end": "2099-01-14"}]
        out = self.m.attach_closure(merchants, nea, "2026-06-21")
        self.assertIsNone(out[0]["open_now"])
        self.assertIsNone(out[0]["next_closure"])

    def test_handles_missing_lat_lon(self):
        merchants = [{"name": "X"}]
        out = self.m.attach_closure(merchants, [], "2026-06-21")
        self.assertIsNone(out[0]["open_now"])

    def test_no_closure_recorded_yields_null(self):
        merchants = [{"name": "X", "LAT": 1.3694, "LON": 103.8495}]
        nea = [{"name": "Y", "lat": 1.3694, "lon": 103.8495}]  # no closure dates
        out = self.m.attach_closure(merchants, nea, "2026-06-21")
        self.assertTrue(out[0]["open_now"])  # no closure = open
        self.assertIsNone(out[0]["next_closure"])


class TestAssess(unittest.TestCase):

    def setUp(self):
        self.api = _load_api()
        self.m = _load_skill()

    def test_mode_c_returns_documented_error(self):
        result = self.m.assess("AMK", "C", 500)
        self.assertEqual(result["error"], "Mode C is not applicable to hawker centres")

    def test_full_report_mode_a(self):
        cdc = _cdc_json(mode="A")
        nea = [{
            "name": "AMK Central", "lat": 1.3694, "lon": 103.8495,
            "next_closure_start": "2099-01-01", "next_closure_end": "2099-01-14",
        }]
        with patch("subprocess.run", return_value=_proc(0, json.dumps(cdc))):
            with patch("singapore_api.fetch_hawker_closures", return_value=_nea(nea)):
                result = self.m.assess("AMK", "A", 500, _today_iso="2026-06-21")
        self.assertEqual(result["query"], "AMK")
        self.assertEqual(result["mode"], "A")
        self.assertEqual(len(result["results"]), 1)
        r = result["results"][0]
        self.assertEqual(r["name"], "Ah Lim Chicken Rice")
        self.assertTrue(r["open_now"])
        self.assertIsNotNone(r["next_closure"])
        self.assertEqual(r["category"], "🍽 F&B / Dining")

    def test_full_report_mode_b(self):
        cdc = _cdc_json(mode="B")
        nea = [{
            "name": "AMK Central", "lat": 1.3694, "lon": 103.8495,
            "next_closure_start": "2026-06-15", "next_closure_end": "2026-06-28",
        }]
        with patch("subprocess.run", return_value=_proc(0, json.dumps(cdc))):
            with patch("singapore_api.fetch_hawker_closures", return_value=_nea(nea)):
                result = self.m.assess("AMK", "B", 500, _today_iso="2026-06-21")
        self.assertEqual(len(result["results"]), 1)
        self.assertFalse(result["results"][0]["open_now"])

    def test_full_report_mode_d(self):
        cdc = _cdc_json(mode="D")
        nea = [{
            "name": "AMK Central", "lat": 1.3700, "lon": 103.8490,
            "next_closure_start": "2099-01-01", "next_closure_end": "2099-01-14",
        }]
        with patch("subprocess.run", return_value=_proc(0, json.dumps(cdc))):
            with patch("singapore_api.fetch_hawker_closures", return_value=_nea(nea)):
                result = self.m.assess("AMK", "D", 500, _today_iso="2026-06-21")
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["results"][0]["open_now"])

    def test_cdc_error_propagates(self):
        with patch("subprocess.run", return_value=_proc(1, "", "boom")):
            result = self.m.assess("AMK", "A", 500)
        self.assertIn("error", result)
        self.assertEqual(result["query"], "AMK")
        self.assertEqual(result["results"], [])

    def test_empty_hawker_records(self):
        cdc = _cdc_json(mode="A")
        with patch("subprocess.run", return_value=_proc(0, json.dumps(cdc))):
            with patch("singapore_api.fetch_hawker_closures", return_value=_nea([])):
                result = self.m.assess("AMK", "A", 500, _today_iso="2026-06-21")
        self.assertEqual(len(result["results"]), 1)
        self.assertIsNone(result["results"][0]["open_now"])


class TestHelperParityWithCdc(unittest.TestCase):
    """The pure helpers (FOOD_KW, NOT_FOOD, CAT_RULES, is_food, categorize)
    are duplicated in this skill. This test loads the CDC script and asserts
    that the two implementations agree on a sample of merchant names.

    Catches drift if CDC's list changes and the inlined copy is forgotten.
    """

    CDC_PATH = SKILL_DIR.parent.parent / "cdc-voucher-locator-skill" / "scripts" / "cdc_voucher_locator.py"

    def setUp(self):
        if not self.CDC_PATH.exists():
            self.skipTest("CDC skill not present at %s" % self.CDC_PATH)
        spec = importlib.util.spec_from_file_location("_cdc_ref", self.CDC_PATH)
        assert spec is not None and spec.loader is not None
        self.cdc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cdc)
        self.mine = _load_skill()

    def test_is_food_agrees_on_samples(self):
        samples = [
            "Ah Lim Chicken Rice",
            "Some Hair Salon",
            "Tiong Bahru Bak Kut Teh",
            "Mama Cafe",
            "Random Gadget Store",
        ]
        for s in samples:
            with self.subTest(name=s):
                self.assertEqual(
                    self.mine.is_food(s), self.cdc.is_food(s),
                    "is_food drift for %r" % s,
                )

    def test_categorize_agrees_on_samples(self):
        samples = [
            "Ah Lim Chicken Rice",
            "Some Hair Salon",
            "NTUC FairPrice",
            "Random Gadget Store",
            "Furniture Mall",
        ]
        for s in samples:
            with self.subTest(name=s):
                self.assertEqual(
                    self.mine.categorize(s), self.cdc.categorize(s),
                    "categorize drift for %r" % s,
                )


class TestCli(unittest.TestCase):
    """argparse migration: positional args still work, mode choices enforced."""

    def setUp(self):
        self.m = _load_skill()
        self._cdc = patch.object(
            self.m, "invoke_cdc",
            return_value={"results": [], "error": None},
        )
        self._cdc.start()
        self.addCleanup(self._cdc.stop)
        self._hawker = patch.object(
            self.m.singapore_api, "fetch_hawker_closures",
            return_value={"success": True, "result": {"records": []}},
        )
        self._hawker.start()
        self.addCleanup(self._hawker.stop)

    def test_positional_args_work(self):
        out = self.m.main(["hawker_discover.py", "Ang Mo Kio Hub"])
        self.assertIsNone(out)

    def test_positional_with_mode(self):
        out = self.m.main(["hawker_discover.py", "Bishan", "B"])
        self.assertIsNone(out)

    def test_positional_with_mode_and_radius(self):
        out = self.m.main(["hawker_discover.py", "Bishan", "B", "1000"])
        self.assertIsNone(out)

    def test_invalid_mode_exits_nonzero(self):
        with self.assertRaises(SystemExit) as cm:
            self.m.main(["hawker_discover.py", "Bishan", "Z"])
        self.assertEqual(cm.exception.code, 2)


class TestModuleImport(unittest.TestCase):

    def test_public_surface(self):
        m = _load_skill()
        for n in ["assess", "invoke_cdc", "attach_closure", "is_food", "categorize"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)), "%s missing" % n)


if __name__ == "__main__":
    unittest.main()
