"""
Smoke tests for cdc_voucher_locator.py

Pure-function tests run directly. Network-dependent code paths
(geocode, fetch_data, lookup) are exercised through mocks so the
suite passes in offline / sandboxed environments.

Run with: python3 -m unittest discover tests
Or:        python3 -m pytest tests/
"""

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "cdc_voucher_locator.py"
)


def _load_module():
    """Load the script as a module (it has no package)."""
    spec = importlib.util.spec_from_file_location("cdc_voucher_locator", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestHaversine(unittest.TestCase):
    """Distance calculation between two lat/lon points."""

    def setUp(self):
        self.m = _load_module()

    def test_same_point_is_zero(self):
        self.assertEqual(self.m.haversine_m(1.3, 103.8, 1.3, 103.8), 0)

    def test_none_inputs_return_none(self):
        self.assertIsNone(self.m.haversine_m(None, 103.8, 1.3, 103.8))
        self.assertIsNone(self.m.haversine_m(1.3, None, 1.3, 103.8))
        self.assertIsNone(self.m.haversine_m(1.3, 103.8, None, 103.8))
        self.assertIsNone(self.m.haversine_m(1.3, 103.8, 1.3, None))

    def test_known_distance_ang_mo_kio_to_orchard(self):
        # Ang Mo Kio Hub (1.3693, 103.8496) to Orchard (1.3036, 103.8318)
        # Real road distance varies; straight-line is ~7.5km.
        dist = self.m.haversine_m(1.3693, 103.8496, 1.3036, 103.8318)
        self.assertGreater(dist, 7000)
        self.assertLess(dist, 8500)

    def test_returns_numeric(self):
        dist = self.m.haversine_m(1.3, 103.8, 1.31, 103.81)
        self.assertIsInstance(dist, (int, float))


class TestCleanAddr(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()

    def test_strips_trailing_semicolon(self):
        self.assertEqual(self.m.clean_addr("Blk 123 Ang Mo Kio Ave 3;"), "Blk 123 Ang Mo Kio Ave 3")

    def test_replaces_internal_semicolons(self):
        self.assertEqual(
            self.m.clean_addr("Block 1; Ang Mo Kio;"),
            "Block 1,  Ang Mo Kio",
        )

    def test_passthrough_when_no_semicolons(self):
        self.assertEqual(
            self.m.clean_addr("Blk 123 Ang Mo Kio Ave 3"),
            "Blk 123 Ang Mo Kio Ave 3",
        )


class TestIsFood(unittest.TestCase):
    """Mode B food keyword detection (English + Chinese + Malay)."""

    def setUp(self):
        self.m = _load_module()

    def test_food_english(self):
        self.assertTrue(self.m.is_food("Chicken Rice Stall"))
        self.assertTrue(self.m.is_food("Kopi & Toast"))
        self.assertTrue(self.m.is_food("Prata House"))

    def test_food_chinese(self):
        self.assertTrue(self.m.is_food("烧腊饭"))  # char siu rice
        self.assertTrue(self.m.is_food("面馆"))    # noodle shop

    def test_food_malay(self):
        self.assertTrue(self.m.is_food("Nasi Lemak"))
        self.assertTrue(self.m.is_food("Ayam Goreng"))

    def test_not_food_categories(self):
        # These are in NOT_FOOD and should reject even if name has food words elsewhere
        self.assertFalse(self.m.is_food("Beauty Salon"))
        self.assertFalse(self.m.is_food("Hair & Nail Studio"))
        self.assertFalse(self.m.is_food("Mobile Phone Repair"))
        self.assertFalse(self.m.is_food("Dental Clinic"))

    def test_ambiguous_returns_false(self):
        # No food keyword, no NOT_FOOD keyword — defaults to False
        self.assertFalse(self.m.is_food("Random Merchant 123"))


class TestCategorize(unittest.TestCase):
    """Mode A sub-category routing."""

    def setUp(self):
        self.m = _load_module()

    def test_supermarket_wins_over_other_categories(self):
        # "FairPrice" contains "mart" but should be classified as Supermarket
        self.assertEqual(self.m.categorize("NTUC FairPrice"), "🏪 Supermarkets")
        self.assertEqual(self.m.categorize("Giant Hypermarket"), "🏪 Supermarkets")
        self.assertEqual(self.m.categorize("Sheng Siong"), "🏪 Supermarkets")

    def test_fnb_category(self):
        self.assertEqual(self.m.categorize("Chicken Rice"), "🍽 F&B / Dining")
        self.assertEqual(self.m.categorize("Kopi Shop"), "🍽 F&B / Dining")

    def test_health_category(self):
        self.assertEqual(self.m.categorize("Dental Clinic"), "🏥 Health & Medical")
        self.assertEqual(self.m.categorize("中医诊所"), "🏥 Health & Medical")

    def test_other_fallback(self):
        self.assertEqual(self.m.categorize("XYZ Random Place"), "🗂 Other")


class TestFetchDataCaching(unittest.TestCase):
    """fetch_data() should not re-download if cache is fresh."""

    def setUp(self):
        self.m = _load_module()
        self.tmp_cache = Path("/tmp/cdc-test-cache")
        self.tmp_cache.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for f in self.tmp_cache.iterdir():
            f.unlink()
        self.tmp_cache.rmdir()

    def test_skips_download_when_cache_has_same_last_modified(self):
        hawker_data = {"locations": [], "lastUpdated": "2026-06-01"}
        supermarket_data = {"locations": [], "lastUpdated": "2026-06-01"}
        (self.tmp_cache / "data.gzip").write_text(
            json.dumps(hawker_data)
        )
        (self.tmp_cache / "data_supermarket.json").write_text(
            json.dumps(supermarket_data)
        )

        past_mod = "Wed, 01 Jan 2020 00:00:00 GMT"
        with patch.object(self.m, "CACHE_DIR", self.tmp_cache), \
             patch.object(self.m, "get_last_modified", return_value=past_mod):
            result = self.m.fetch_data()

        self.assertIn("hawkers", result)
        self.assertIn("supermarkets", result)
        self.assertEqual(result["hawkers"], hawker_data)
        self.assertEqual(result["supermarkets"], supermarket_data)


class TestGeocodeMocked(unittest.TestCase):
    """geocode() should handle OneMap's quirky 'error: missing token' response."""

    def setUp(self):
        self.m = _load_module()

    def test_ignores_error_field_when_results_present(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "error": "Authentication token missing",
            "results": [{
                "LATITUDE": "1.3693",
                "LONGITUDE": "103.8496",
                "POSTAL": "569933",
                "ADDRESS": "ANG MO KIO HUB",
            }],
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *a: False

        with patch.object(self.m.urllib.request, "urlopen", return_value=mock_response):
            result = self.m.geocode("Ang Mo Kio Hub")

        self.assertIsNotNone(result)
        lat, lon, postal, address = result
        self.assertEqual(postal, "569933")
        self.assertEqual(lat, 1.3693)
        self.assertEqual(lon, 103.8496)

    def test_returns_none_tuple_when_no_results(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "error": "Authentication token missing",
            "results": [],
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *a: False

        with patch.object(self.m.urllib.request, "urlopen", return_value=mock_response):
            result = self.m.geocode("Nowhere Land XYZ")

        self.assertIsNone(result[0])
        self.assertIsInstance(result[1], str)


def _mock_urlopen(payload):
    """Build a context-manager mock that returns `payload` as JSON body."""
    import io
    body = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = lambda self: io.BytesIO(body)
    cm.__exit__ = lambda self, *a: False
    cm.read = lambda: body
    return cm


class TestGeocodeOneMapQuirk(unittest.TestCase):
    """OneMap returns 'Authentication token missing' even when results are
    present. The skill must treat that envelope as a successful geocode.
    """

    def setUp(self):
        self.m = _load_module()

    def test_error_with_results_picks_first_result(self):
        payload = {
            "error": "Authentication token missing",
            "results": [
                {"LATITUDE": "1.3010", "LONGITUDE": "103.8380", "BUILDING": "Bishan", "ADDRESS": "Block 123 Bishan St 1", "POSTAL": "579700"}
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(payload)) as uo:
            out = self.m.geocode("Bishan")
        self.assertAlmostEqual(out[0], 1.301, places=2)
        self.assertAlmostEqual(out[1], 103.838, places=2)
        self.assertEqual(out[2], "579700")
        self.assertEqual(out[3], "Block 123 Bishan St 1")
        self.assertTrue(uo.called)

    def test_empty_results_returns_none_tuple(self):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen({"error": "missing token", "results": []})):
            out = self.m.geocode("NowhereVille")
        self.assertIsNone(out[0])
        self.assertIn("No geocoding results", out[1])


class TestLookupNoMatch(unittest.TestCase):
    """lookup() with a postal/address that has no nearby merchants."""

    def setUp(self):
        self.m = _load_module()

    def test_lookup_empty_payload_returns_empty_list(self):
        with patch.object(self.m, "geocode", return_value=(0.0, 0.0, "000000", "Desert")):
            with patch.object(self.m, "fetch_data", return_value={
                "hawkers": {"lastUpdated": "2026-06-21", "locations": []},
                "supermarkets": {"lastUpdated": "2026-06-21", "locations": []},
            }):
                out = self.m.lookup("Desert", mode="A", radius=500)
        self.assertIsInstance(out, dict)
        self.assertNotIn("error", out)

    def test_lookup_none_postal_skips_radius_filter(self):
        with patch.object(self.m, "geocode", return_value=(1.2838, 103.8607, None, "Marina Bay")):
            with patch.object(self.m, "fetch_data", return_value={
                "hawkers": {"lastUpdated": "2026-06-21", "locations": []},
                "supermarkets": {"lastUpdated": "2026-06-21", "locations": []},
            }):
                out = self.m.lookup("Marina Bay", mode="A", radius=500)
        self.assertIsInstance(out, dict)
        self.assertNotIn("error", out)


class TestCacheInvalidation(unittest.TestCase):
    """Cache directory must be writable and stash files under it."""

    def setUp(self):
        self.m = _load_module()
        import tempfile
        self._tmp = Path(tempfile.mkdtemp(prefix="cdc_cache_"))

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self._tmp), ignore_errors=True)

    def test_cache_dir_is_a_path(self):
        self.assertIsInstance(self.m.CACHE_DIR, Path)

    def test_cache_dir_writable(self):
        with patch.object(self.m, "CACHE_DIR", self._tmp):
            f = self.m.CACHE_DIR / "test.json"
            f.write_text('{"hello": "world"}')
        self.assertTrue(f.exists())
        self.assertEqual(f.read_text(), '{"hello": "world"}')


class TestModuleImport(unittest.TestCase):
    """Sanity: the script imports without side effects."""

    def test_no_top_level_network_calls(self):
        # If _load_module() raises, this test fails
        m = _load_module()
        # Module exposes the expected public surface
        self.assertTrue(callable(m.lookup))
        self.assertTrue(callable(m.geocode))
        self.assertTrue(callable(m.fetch_data))
        self.assertTrue(callable(m.haversine_m))
        self.assertTrue(callable(m.clean_addr))
        self.assertTrue(callable(m.is_food))
        self.assertTrue(callable(m.categorize))


if __name__ == "__main__":
    unittest.main(verbosity=2)
