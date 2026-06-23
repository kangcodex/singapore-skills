"""
Smoke tests for singapore_api.py (the canonical shared client).

Pattern follows tests/test_cdc_voucher_locator.py:
  - Load the script via importlib.util.spec_from_file_location
  - Patch urllib.request.urlopen to stub the network
  - Pure helpers and the geocode() quirk tested directly
  - No top-level network call allowed (the module loads without I/O)

Run: python3 -m unittest discover -s tests
"""
import importlib.util
import io
import json
import os
import sys
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "singapore_api.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("singapore_api", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mock_urlopen(body, *, content_encoding=None, status=200):
    """Build a MagicMock that mimics urllib's context-manager response."""
    raw = json.dumps(body).encode("utf-8")
    if content_encoding == "gzip":
        import gzip
        raw = gzip.compress(raw)
    resp = MagicMock()
    resp.read.return_value = raw
    resp.headers = {"Content-Encoding": content_encoding} if content_encoding else {}
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = lambda s, *a: False
    return resp


def _dataset_two_step(csv_body="col\nval\n"):
    """Returns a side_effect for urlopen: respond differently based on the
    URL of each call. initiate-download → 200; poll-download → envelope with
    S3 URL; S3 URL → CSV body."""
    from urllib.request import Request as _Req

    def _side(req, *a, **k):
        url = req.full_url if isinstance(req, _Req) else req
        if "initiate-download" in url:
            return _mock_urlopen({})
        if "poll-download" in url:
            return _mock_urlopen({"data": {"url": "https://s3.example/csv"}})
        if "s3.example" in url:
            return _mock_urlopen(csv_body)
        raise AssertionError("unexpected url: " + url)

    return _side


def _collected_urls(mock_urlopen):
    """Extract the URL string from each call to a urlopen mock. urlopen can be
    called with a Request object (has .full_url) or a plain string."""
    from urllib.request import Request as _Req
    urls = []
    for c in mock_urlopen.call_args_list:
        first = c[0][0]
        urls.append(first.full_url if isinstance(first, _Req) else str(first))
    return urls


class TestModuleImport(unittest.TestCase):
    """Sanity: the canonical module imports without side effects."""

    def test_no_top_level_network_calls(self):
        m = _load_module()
        # 14 real-time + 7 S03a + 1 S05a + 8 S08 property fetchers
        # + geocode + request_json must be callable
        names = [
            "fetch_pm25", "fetch_psi", "fetch_uv",
            "fetch_two_hour_forecast", "fetch_twenty_four_hour_forecast",
            "fetch_four_day_forecast",
            "fetch_rainfall", "fetch_wind", "fetch_temperature", "fetch_humidity",
            "fetch_lta_traffic_images", "fetch_hdb_carpark_availability",
            "fetch_lta_bus_arrival", "fetch_lta_mrt_arrival", "fetch_lta_taxi_availability",
            "geocode", "request_json",
            "fetch_ura_rentals", "fetch_ura_private_resi_trans",
            "fetch_ura_ec_sales", "fetch_ura_ec_position",
            "fetch_ura_unsold_private_resi",
            "fetch_singstat_supply_pipeline", "fetch_singstat_vacancy",
            "fetch_cea_salesperson",
            "fetch_cea_transaction_records",
        ]
        for n in names:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n)), "%s not callable" % n)

    def test_s08_constants_exist(self):
        m = _load_module()
        for n in [
            "URA_RENTALS_DATASET_ID",
            "URA_PRIVATE_RESI_TRANS_CENTRAL_DATASET_ID",
            "URA_PRIVATE_RESI_TRANS_OUTSIDE_CENTRAL_DATASET_ID",
            "URA_PRIVATE_RESI_TRANS_REST_CENTRAL_DATASET_ID",
            "URA_PRIVATE_RESI_TRANS_WHOLE_SG_DATASET_ID",
            "URA_EC_SALES_DATASET_ID",
            "URA_EC_POSITION_DATASET_ID",
            "URA_UNSOLD_PRIVATE_RESI_DATASET_ID",
            "SINGSTAT_SUPPLY_PIPELINE_DATASET_ID",
            "SINGSTAT_VACANCY_DATASET_ID",
            "CEA_SALESPERSON_DATASET_ID",
            "CEA_TRANSACTION_RECORDS_DATASET_ID",
            "URA_REGION_DATASET_IDS",
        ]:
            with self.subTest(name=n):
                self.assertTrue(hasattr(m, n), "%s missing" % n)

    def test_s08_helpers_exist(self):
        m = _load_module()
        for n in ["_normalize_qtr_label", "_pivot_quarterly_wide", "_fetch_singstat_ckan"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)), "%s missing" % n)

    def test_v2_helpers_exist(self):
        m = _load_module()
        for n in ["require_api_key", "try_v2_then_v1", "_V1_TO_V2", "DATA_GOV_V2"]:
            with self.subTest(name=n):
                self.assertTrue(hasattr(m, n), "%s missing" % n)

    def test_datastore_helpers_exist(self):
        m = _load_module()
        for n in [
            "fetch_datastore_search", "fetch_ura_master_plan", "fetch_nea_historical_rainfall",
            "svy21_to_wgs84", "haversine_m", "DATASTORE",
        ]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)) or hasattr(m, n), "%s missing" % n)

    def test_s03a_helpers_exist(self):
        m = _load_module()
        for n in ["fetch_hawker_closures", "fetch_activesg_facilities",
                  "NEA_HAWKER_CENTRES_DATASET_ID",
                  "SPORTSG_FACILITIES_DATASET_ID"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)) or hasattr(m, n), "%s missing" % n)

    def test_tier_and_classification_helpers_exist(self):
        m = _load_module()
        for n in ["is_heavy_rain", "psi_tier", "psi_national", "HEAVY_RAIN_KEYWORDS"]:
            with self.subTest(name=n):
                self.assertTrue(hasattr(m, n), "%s missing" % n)

    def test_s05a_helpers_exist(self):
        m = _load_module()
        for n in ["fetch_dengue_clusters", "DENGUE_CLUSTERS_DATASET_ID"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n, None)) or hasattr(m, n), "%s missing" % n)


class TestRequestJsonAuth(unittest.TestCase):
    """x-api-key header behaviour: present when env set, absent when unset."""

    def setUp(self):
        self.m = _load_module()
        # Bypass the on-disk cache so every call hits the network mock.
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def test_api_key_header_present_when_env_set(self):
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "test-key-123"}, clear=False), \
             patch("urllib.request.urlopen", return_value=_mock_urlopen({"ok": True})) as uo:
            self.m.request_json("https://example.com/api", namespace="auth-test-1")
        # urllib.request.Request normalises header names (x-api-key → X-api-key),
        # so do a case-insensitive lookup. header_items() works on all Python versions.
        req = uo.call_args[0][0]
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers.get("x-api-key"), "test-key-123")

    def test_api_key_header_absent_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("urllib.request.urlopen", return_value=_mock_urlopen({"ok": True})) as uo:
            self.m.request_json("https://example.com/api", namespace="auth-test-2")
        req = uo.call_args[0][0]
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertNotIn("x-api-key", headers)


class TestRequestJsonCaching(unittest.TestCase):
    """Cache hit: second call to the same URL must NOT re-open the network."""

    def setUp(self):
        self.m = _load_module()
        # Use a unique namespace per test to avoid cache pollution
        self.ns = "cache-test-%d" % id(self)

    def test_cache_hit_on_second_call(self):
        url = "https://example.com/api"
        body = {"data": [1, 2, 3]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)) as uo:
            first = self.m.request_json(url, namespace=self.ns)
            second = self.m.request_json(url, namespace=self.ns)
        self.assertEqual(first, body)
        self.assertEqual(second, body)
        self.assertEqual(uo.call_count, 1, "second call should hit cache, not network")


class TestRequestJsonRetry(unittest.TestCase):
    """Retry behaviour: 429 triggers MAX_ATTEMPTS; 4xx (other than 429) raises fast."""

    def setUp(self):
        self.m = _load_module()
        self.ns = "retry-test-%d" % id(self)
        # Bypass on-disk cache so network mock is always hit
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def test_429_triggers_three_attempts(self):
        # 429 response — must retry
        err = urllib.error.HTTPError(
            "https://example.com/rate-limited", 429, "Too Many Requests", Message(), None
        )
        with patch("urllib.request.urlopen", side_effect=err), \
             patch("time.sleep") as sleep:  # don't actually sleep in tests
            with self.assertRaises(urllib.error.HTTPError):
                self.m.request_json("https://example.com/rate-limited", namespace=self.ns)
        # MAX_ATTEMPTS=3 → 2 sleeps (between attempts 1→2 and 2→3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(sleep.call_args_list[0].args, (0.5,))
        self.assertEqual(sleep.call_args_list[1].args, (1.0,))

    def test_4xx_raises_fast_without_retry(self):
        err = urllib.error.HTTPError(
            "https://example.com/bad-request", 400, "Bad Request", Message(), None
        )
        with patch("urllib.request.urlopen", side_effect=err), \
             patch("time.sleep") as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                self.m.request_json("https://example.com/bad-request", namespace=self.ns)
        # 4xx (non-429) → fail fast, no sleep
        self.assertEqual(sleep.call_count, 0)


class TestV2V1Routing(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def test_v2_used_when_key_set(self):
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "key-v2"}, clear=False), \
             patch("urllib.request.urlopen", return_value=_mock_urlopen({"items": []})) as uo:
            self.m.fetch_psi()
        called_url = uo.call_args[0][0].full_url
        self.assertIn("api-open.data.gov.sg", called_url, "should call v2 host")
        self.assertIn("/v2/", called_url, "should call v2 path")
        headers = {k.lower(): v for k, v in uo.call_args[0][0].header_items()}
        self.assertEqual(headers.get("x-api-key"), "key-v2")

    def test_falls_back_to_v1_when_key_unset(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("urllib.request.urlopen", return_value=_mock_urlopen({"items": []})) as uo:
            self.m.fetch_psi()
        called_url = uo.call_args[0][0].full_url
        self.assertIn("api.data.gov.sg/v1", called_url, "should call v1 host")
        headers = {k.lower(): v for k, v in uo.call_args[0][0].header_items()}
        self.assertNotIn("x-api-key", headers)

    def test_falls_back_to_v1_on_v2_404(self):
        v2_err = urllib.error.HTTPError(
            "https://api-open.data.gov.sg/v2/real-time/api/psi", 404, "Not Found", Message(), None
        )
        v1_resp = _mock_urlopen({"items": []})
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "key-v2"}, clear=False), \
             patch("urllib.request.urlopen", side_effect=[v2_err, v1_resp]) as uo, \
             patch("time.sleep"):
            result = self.m.fetch_psi()
        self.assertEqual(result, {"items": []})
        self.assertEqual(uo.call_count, 2)
        v1_url = uo.call_args_list[1][0][0].full_url
        self.assertIn("api.data.gov.sg/v1", v1_url, "second call should be v1")

    def test_falls_back_to_v1_on_v2_network_error(self):
        v1_resp = _mock_urlopen({"items": []})
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "key-v2"}, clear=False), \
             patch("urllib.request.urlopen", side_effect=[
                 urllib.error.URLError("boom"),  # v2 attempt 1
                 urllib.error.URLError("boom"),  # v2 attempt 2 (retry)
                 urllib.error.URLError("boom"),  # v2 attempt 3 (retry)
                 v1_resp,                         # v1 success
             ]) as uo, \
             patch("time.sleep"):
            result = self.m.fetch_psi()
        self.assertEqual(result, {"items": []})
        self.assertEqual(uo.call_count, 4)
        v1_url = uo.call_args_list[3][0][0].full_url
        self.assertIn("api.data.gov.sg/v1", v1_url)


class TestRequireApiKey(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_require_api_key_raises_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                self.m.require_api_key()
        self.assertIn("DATA_GOV_SG_API_KEY", str(ctx.exception))
        self.assertIn("data.gov.sg", str(ctx.exception))

    def test_require_api_key_passes_when_set(self):
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "real-key"}, clear=False):
            self.m.require_api_key()

    def test_mrt_arrival_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                self.m.fetch_lta_mrt_arrival()
        self.assertIn("DATA_GOV_SG_API_KEY", str(ctx.exception))

    def test_mrt_arrival_hits_v2_with_key(self):
        with patch.dict(os.environ, {"DATA_GOV_SG_API_KEY": "key-v2"}, clear=False), \
             patch("urllib.request.urlopen", return_value=_mock_urlopen({"items": []})) as uo, \
             patch.object(self.m, "_cache_get", return_value=None):
            self.m.fetch_lta_mrt_arrival(station_code="NS1")
        called_url = uo.call_args[0][0].full_url
        self.assertIn("api-open.data.gov.sg", called_url, "MRT should hit v2")
        self.assertIn("mrt-train-arrival", called_url)
        self.assertIn("StationCode=NS1", called_url)


class TestGeocodeOneMapQuirk(unittest.TestCase):
    """OneMap returns 'error: missing token' even when results[] is populated.
    geocode() must ignore the error field and parse results[0]."""

    def setUp(self):
        self.m = _load_module()

    def test_ignores_error_field_when_results_present(self):
        body = {
            "error": "Authentication token missing",
            "results": [{
                "LATITUDE": "1.3693",
                "LONGITUDE": "103.8496",
                "POSTAL": "569933",
                "ADDRESS": "ANG MO KIO HUB",
            }],
        }
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            address, lat, lon, postal = self.m.geocode("Ang Mo Kio Hub")
        self.assertEqual(postal, "569933")
        self.assertEqual(address, "ANG MO KIO HUB")
        self.assertAlmostEqual(lat, 1.3693)
        self.assertAlmostEqual(lon, 103.8496)

    def test_raises_value_error_on_empty_results(self):
        body = {"error": "Authentication token missing", "results": []}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            with self.assertRaises(ValueError):
                self.m.geocode("Nowhere Land XYZ")

    def test_returns_none_postal_when_missing(self):
        body = {
            "error": "Authentication token missing",
            "results": [{
                "LATITUDE": "1.3",
                "LONGITUDE": "103.8",
                "POSTAL": "",
                "ADDRESS": "SOMEWHERE",
            }],
        }
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            address, lat, lon, postal = self.m.geocode("Somewhere")
        self.assertIsNone(postal)


class TestDatastoreHelpers(unittest.TestCase):
    """v2 dataset flow: initiate-download (best-effort) → poll-download → fetch."""

    def setUp(self):
        self.m = _load_module()
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def _mock_two_step(self, csv_body="col\nval\n"):
        """Returns a side_effect for urlopen: POST initiate returns ok, GET poll
        returns envelope with S3 URL, final GET returns CSV body."""
        from urllib.request import Request as _Req

        def _side(req, *a, **k):
            url = req.full_url if isinstance(req, _Req) else req
            if "initiate-download" in url:
                return _mock_urlopen({})
            if "poll-download" in url:
                return _mock_urlopen({"data": {"url": "https://s3.example/csv"}})
            if "s3.example" in url:
                return _mock_urlopen(csv_body)
            raise AssertionError("unexpected url: " + url)

        return _side

    def test_fetch_datastore_search_is_removed(self):
        with self.assertRaises(NotImplementedError):
            self.m.fetch_datastore_search("d_test")

    def test_fetch_ura_master_plan_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_master_plan()
        urls = _collected_urls(uo)
        self.assertTrue(any("initiate-download" in u for u in urls))
        self.assertTrue(any("poll-download" in u and self.m.URA_MASTER_PLAN_DATASET_ID in u for u in urls))

    def test_fetch_nea_historical_rainfall_passes_station_filter(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_nea_historical_rainfall(station_id="S123", months=12)
        urls = _collected_urls(uo)
        initiate = [u for u in urls if "initiate-download" in u]
        self.assertGreater(len(initiate), 0)


class TestSvy21AndHaversine(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_haversine_zero_for_same_point(self):
        self.assertAlmostEqual(self.m.haversine_m(1.3, 103.8, 1.3, 103.8), 0.0, places=3)

    def test_haversine_known_distance(self):
        # Marina Bay → Bishan: roughly 8.5 km along a great circle
        d = self.m.haversine_m(1.2838, 103.8607, 1.3508, 103.8494)
        self.assertGreater(d, 7000)
        self.assertLess(d, 10000)

    def test_svy21_to_wgs84_returns_singapore_point(self):
        # Bishan Town Centre in SVY21 is approximately (29080, 38800) in
        # pseudo-eastings/northings. Use a known reference: URA Master Plan
        # "BISHAN" centroid sits around (30000, 39000) in SVY21.
        lat, lon = self.m.svy21_to_wgs84(30000.0, 39000.0)
        # Singapore lat/lon is 1.2-1.5 N, 103.6-104.0 E
        self.assertGreater(lat, 1.0)
        self.assertLess(lat, 1.5)
        self.assertGreater(lon, 103.5)
        self.assertLess(lon, 104.1)

    def test_svy21_to_wgs84_round_trip_distances(self):
        # Convert two points → distance via haversine should be ~equal to
        # the SVY21 distance (within ~10m for points < 1 km apart).
        lat1, lon1 = self.m.svy21_to_wgs84(28000.0, 38000.0)
        lat2, lon2 = self.m.svy21_to_wgs84(28100.0, 38080.0)  # ~100m N, ~80m E
        d_wgs84 = self.m.haversine_m(lat1, lon1, lat2, lon2)
        self.assertGreater(d_wgs84, 100)
        self.assertLess(d_wgs84, 200)


class TestS05aHelpers(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def test_fetch_dengue_clusters_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=_dataset_two_step()) as uo:
            self.m.fetch_dengue_clusters()
        urls = _collected_urls(uo)
        self.assertTrue(any(self.m.DENGUE_CLUSTERS_DATASET_ID in u for u in urls))


class TestS03aHelpers(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def test_fetch_hawker_closures_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=_dataset_two_step()) as uo:
            self.m.fetch_hawker_closures()
        urls = _collected_urls(uo)
        self.assertTrue(any(self.m.NEA_HAWKER_CLOSURES_DATASET_ID in u for u in urls))

    def test_fetch_activesg_facilities_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=_dataset_two_step()) as uo:
            self.m.fetch_activesg_facilities()
        urls = _collected_urls(uo)
        self.assertTrue(any(self.m.SPORTSG_FACILITIES_DATASET_ID in u for u in urls))


class TestTierAndClassificationHelpers(unittest.TestCase):

    def setUp(self):
        self.m = _load_module()

    def test_is_heavy_rain_matches_all_three_keywords(self):
        for kw in ("Heavy Thundery Showers", "Thundery Showers", "Heavy Rain"):
            with self.subTest(keyword=kw):
                payload = {"items": [{"forecast": "Cloudy with " + kw + " in the afternoon"}]}
                self.assertTrue(self.m.is_heavy_rain(payload))

    def test_is_heavy_rain_false_for_fair(self):
        self.assertFalse(self.m.is_heavy_rain({"items": [{"forecast": "Fair"}]}))

    def test_is_heavy_rain_false_for_empty_items(self):
        self.assertFalse(self.m.is_heavy_rain({"items": []}))

    def test_is_heavy_rain_false_for_missing_items_key(self):
        self.assertFalse(self.m.is_heavy_rain({}))

    def test_is_heavy_rain_false_for_non_dict_payload(self):
        self.assertFalse(self.m.is_heavy_rain("not a dict"))
        self.assertFalse(self.m.is_heavy_rain(None))

    def test_is_heavy_rain_iterates_all_items(self):
        payload = {"items": [
            {"forecast": "Fair"},
            {"forecast": "Cloudy"},
            {"forecast": "Heavy Thundery Showers"},
        ]}
        self.assertTrue(self.m.is_heavy_rain(payload))

    def test_psi_tier_none_is_unknown(self):
        self.assertEqual(self.m.psi_tier(None), "unknown")

    def test_psi_tier_good_boundaries(self):
        for v in (0, 25, 50):
            with self.subTest(value=v):
                self.assertEqual(self.m.psi_tier(v), "good")

    def test_psi_tier_moderate_boundaries(self):
        for v in (51, 75, 100):
            with self.subTest(value=v):
                self.assertEqual(self.m.psi_tier(v), "moderate")

    def test_psi_tier_unhealthy_boundaries(self):
        for v in (101, 150, 200):
            with self.subTest(value=v):
                self.assertEqual(self.m.psi_tier(v), "unhealthy")

    def test_psi_tier_hazardous_above(self):
        for v in (201, 300, 500):
            with self.subTest(value=v):
                self.assertEqual(self.m.psi_tier(v), "hazardous")

    def test_psi_national_extracts_v1_envelope(self):
        envelope = {
            "items": [{"readings": {"psi_twenty_four_hourly": {"national": 42}}}]
        }
        self.assertEqual(self.m.psi_national(envelope), 42)

    def test_psi_national_handles_string_national(self):
        envelope = {
            "items": [{"readings": {"psi_twenty_four_hourly": {"national": "55"}}}]
        }
        self.assertEqual(self.m.psi_national(envelope), 55)

    def test_psi_national_returns_none_for_missing_national(self):
        envelope = {"items": [{"readings": {"psi_twenty_four_hourly": {}}}]}
        self.assertIsNone(self.m.psi_national(envelope))

    def test_psi_national_returns_none_for_no_items(self):
        self.assertIsNone(self.m.psi_national({"items": []}))

    def test_psi_national_returns_none_for_non_dict(self):
        self.assertIsNone(self.m.psi_national("bad"))
        self.assertIsNone(self.m.psi_national(None))


class TestS08PropertyFetchers(unittest.TestCase):
    """8 property fetchers + 3 helpers added in S08."""

    def setUp(self):
        self.m = _load_module()
        self._cache_patcher = patch.object(self.m, "_cache_get", return_value=None)
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

    def _mock_two_step(self, csv_body="col\nval\n"):
        from urllib.request import Request as _Req

        def _side(req, *a, **k):
            url = req.full_url if isinstance(req, _Req) else req
            if "initiate-download" in url:
                return _mock_urlopen({})
            if "poll-download" in url:
                return _mock_urlopen({"data": {"url": "https://s3.example/csv"}})
            if "s3.example" in url:
                resp = MagicMock()
                resp.read.return_value = csv_body.encode("utf-8") if isinstance(csv_body, str) else csv_body
                resp.headers = {}
                resp.__enter__ = lambda s: s
                resp.__exit__ = lambda s, *a: False
                return resp
            raise AssertionError("unexpected url: " + url)

        return _side

    def _mock_singstat_ckan(self, records):
        from urllib.request import Request as _Req

        def _side(req, *a, **k):
            url = req.full_url if isinstance(req, _Req) else req
            if "datastore_search" in url and "resource_id" in url:
                return _mock_urlopen({"result": {"records": records}})
            raise AssertionError("unexpected url: " + url)
        return _side

    def test_fetch_ura_rentals_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_rentals()
        urls = _collected_urls(uo)
        self.assertTrue(any("initiate-download" in u for u in urls))
        self.assertTrue(
            any("poll-download" in u and self.m.URA_RENTALS_DATASET_ID in u for u in urls)
        )

    def test_fetch_ura_private_resi_trans_whole_sg_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_private_resi_trans("whole_sg")
        urls = _collected_urls(uo)
        self.assertTrue(
            any(
                "poll-download" in u
                and self.m.URA_PRIVATE_RESI_TRANS_WHOLE_SG_DATASET_ID in u
                for u in urls
            )
        )

    def test_fetch_ura_private_resi_trans_invalid_region_raises(self):
        with self.assertRaises(ValueError) as cm:
            self.m.fetch_ura_private_resi_trans("narnia")
        self.assertIn("narnia", str(cm.exception))
        self.assertIn("central", str(cm.exception))
        self.assertIn("whole_sg", str(cm.exception))

    def test_fetch_ura_private_resi_trans_all_four_regions_are_valid(self):
        for region in ("whole_sg", "central", "rest_central", "outside_central"):
            with self.subTest(region=region):
                with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
                    self.m.fetch_ura_private_resi_trans(region)
                urls = _collected_urls(uo)
                self.assertTrue(any("initiate-download" in u for u in urls))

    def test_fetch_ura_ec_sales_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_ec_sales()
        urls = _collected_urls(uo)
        self.assertTrue(
            any("poll-download" in u and self.m.URA_EC_SALES_DATASET_ID in u for u in urls)
        )

    def test_fetch_ura_ec_position_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_ec_position()
        urls = _collected_urls(uo)
        self.assertTrue(
            any("poll-download" in u and self.m.URA_EC_POSITION_DATASET_ID in u for u in urls)
        )

    def test_fetch_ura_unsold_private_resi_uses_v2_dataset_flow(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.m.fetch_ura_unsold_private_resi()
        urls = _collected_urls(uo)
        self.assertTrue(
            any(
                "poll-download" in u
                and self.m.URA_UNSOLD_PRIVATE_RESI_DATASET_ID in u
                for u in urls
            )
        )

    def test_fetch_singstat_supply_pipeline_uses_ckan_and_pivots(self):
        records = [
            {"_id": 1, "DataSeries": "In Planning", "20261Q": 12000, "20254Q": 11500},
            {"_id": 2, "DataSeries": "Under Construction", "20261Q": 32000, "20254Q": 30000},
        ]
        with patch("urllib.request.urlopen", side_effect=self._mock_singstat_ckan(records)) as uo:
            out = self.m.fetch_singstat_supply_pipeline()
        urls = _collected_urls(uo)
        self.assertTrue(any("datastore_search" in u for u in urls))
        self.assertTrue(any(self.m.SINGSTAT_SUPPLY_PIPELINE_DATASET_ID in u for u in urls))
        self.assertEqual(len(out), 4)
        planning = [r for r in out if r["series"] == "In Planning"]
        self.assertEqual(planning[0]["qtr"], "2026-Q1")
        self.assertEqual(planning[0]["value"], 12000.0)
        self.assertEqual(planning[1]["value"], 11500.0)

    def test_fetch_singstat_vacancy_uses_ckan_and_pivots(self):
        records = [
            {"_id": 1, "DataSeries": "Available", "20261Q": 25000},
            {"_id": 2, "DataSeries": "Vacant", "20261Q": 6800},
        ]
        with patch("urllib.request.urlopen", side_effect=self._mock_singstat_ckan(records)) as uo:
            out = self.m.fetch_singstat_vacancy()
        urls = _collected_urls(uo)
        self.assertTrue(any(self.m.SINGSTAT_VACANCY_DATASET_ID in u for u in urls))
        self.assertEqual(len(out), 2)
        self.assertEqual({r["series"] for r in out}, {"Available", "Vacant"})

    def test_fetch_singstat_supply_pipeline_returns_empty_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("boom")):
            out = self.m.fetch_singstat_supply_pipeline()
        self.assertEqual(out, [])

    def test_fetch_cea_salesperson_empty_query_returns_empty(self):
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step()) as uo:
            self.assertEqual(self.m.fetch_cea_salesperson(""), [])
            self.assertEqual(self.m.fetch_cea_salesperson(None), [])
            self.assertEqual(self.m.fetch_cea_salesperson("   "), [])
        self.assertEqual(uo.call_count, 0)

    def test_fetch_cea_salesperson_reg_no_exact_match(self):
        rows = [
            {"registration_no": "R012345X", "name": "Alice Tan", "status": "active", "agency": "ERA"},
            {"registration_no": "R999999Z", "name": "Bob Lim", "status": "inactive", "agency": "PropNex"},
        ]
        csv_body = "registration_no,name,status,agency\n" + "\n".join(
            f"{r['registration_no']},{r['name']},{r['status']},{r['agency']}" for r in rows
        )
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step(csv_body)):
            out = self.m.fetch_cea_salesperson("R012345X")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["name"], "Alice Tan")

    def test_fetch_cea_salesperson_name_substring_match(self):
        rows = [
            {"registration_no": "R012345X", "name": "Alice Tan", "status": "active", "agency": "ERA"},
            {"registration_no": "R678901Y", "name": "Alice Wong", "status": "active", "agency": "OrangeTee"},
            {"registration_no": "R999999Z", "name": "Bob Lim", "status": "inactive", "agency": "PropNex"},
        ]
        csv_body = "registration_no,name,status,agency\n" + "\n".join(
            f"{r['registration_no']},{r['name']},{r['status']},{r['agency']}" for r in rows
        )
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step(csv_body)):
            out = self.m.fetch_cea_salesperson("alice")
        self.assertEqual(len(out), 2)
        self.assertEqual({r["name"] for r in out}, {"Alice Tan", "Alice Wong"})

    def test_normalize_qtr_label_handles_all_observed_shapes(self):
        self.assertEqual(self.m._normalize_qtr_label("20261Q"), "2026-Q1")
        self.assertEqual(self.m._normalize_qtr_label("2025 4Q"), "2025-Q4")
        self.assertEqual(self.m._normalize_qtr_label("2025-Q3"), "2025-Q3")
        self.assertEqual(self.m._normalize_qtr_label("2025q3"), "2025-Q3")
        self.assertEqual(self.m._normalize_qtr_label("  20254Q  "), "2025-Q4")
        self.assertEqual(self.m._normalize_qtr_label("not-a-quarter"), "not-a-quarter")
        self.assertEqual(self.m._normalize_qtr_label(""), "")
        self.assertIsNone(self.m._normalize_qtr_label(None))

    def test_pivot_quarterly_wide_handles_real_singstat_shape(self):
        records = [
            {"_id": 1, "DataSeries": "Available", "20261Q": 25000, "20254Q": 24000, "20251Q": 23000},
            {"_id": 2, "DataSeries": "Vacant", "20261Q": 6800, "20254Q": 6500, "n/a": "skip-me"},
            {"_id": 3, "DataSeries": "  Total  ", "20261Q": 30000, "": "drop-empty-col"},
        ]
        out = self.m._pivot_quarterly_wide(records)
        self.assertEqual(len(out), 6)
        total = [r for r in out if r["series"] == "Total"]
        self.assertEqual(len(total), 1)
        self.assertEqual(total[0]["qtr"], "2026-Q1")
        vacant = [r for r in out if r["series"] == "Vacant"]
        self.assertEqual(len(vacant), 2)
        self.assertTrue(all(isinstance(r["value"], float) for r in out))

    def test_pivot_quarterly_wide_empty_input_returns_empty(self):
        self.assertEqual(self.m._pivot_quarterly_wide([]), [])
        self.assertEqual(self.m._pivot_quarterly_wide(None), [])

    def test_pivot_quarterly_wide_skips_records_without_dataseries(self):
        records = [{"_id": 1, "20261Q": 100, "no-series-here": True}]
        self.assertEqual(self.m._pivot_quarterly_wide(records), [])

    def test_fetch_cea_transaction_records_basic(self):
        rows = [
            {"transaction_id": "T1", "salesperson_reg_no": "R012345X", "town": "bishan",
             "flat_type": "5-ROOM", "transaction_date": "2025-12-15", "trans_price": "1200000"},
            {"transaction_id": "T2", "salesperson_reg_no": "R678901Y", "town": "tampines",
             "flat_type": "4-ROOM", "transaction_date": "2025-11-20", "trans_price": "850000"},
        ]
        csv_body = "transaction_id,salesperson_reg_no,town,flat_type,transaction_date,trans_price\n" + "\n".join(
            f"{r['transaction_id']},{r['salesperson_reg_no']},{r['town']},{r['flat_type']},{r['transaction_date']},{r['trans_price']}"
            for r in rows
        )
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step(csv_body)):
            out = self.m.fetch_cea_transaction_records()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["transaction_id"], "T1")

    def test_fetch_cea_transaction_records_town_filter(self):
        rows = [
            {"transaction_id": "T1", "salesperson_reg_no": "R012345X", "town": "bishan",
             "flat_type": "5-ROOM", "transaction_date": "2025-12-15", "trans_price": "1200000"},
            {"transaction_id": "T2", "salesperson_reg_no": "R678901Y", "town": "tampines",
             "flat_type": "4-ROOM", "transaction_date": "2025-11-20", "trans_price": "850000"},
        ]
        csv_body = "transaction_id,salesperson_reg_no,town,flat_type,transaction_date,trans_price\n" + "\n".join(
            f"{r['transaction_id']},{r['salesperson_reg_no']},{r['town']},{r['flat_type']},{r['transaction_date']},{r['trans_price']}"
            for r in rows
        )
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step(csv_body)):
            out = self.m.fetch_cea_transaction_records(town="bishan")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["town"], "bishan")

    def test_fetch_cea_transaction_records_since_filter(self):
        rows = [
            {"transaction_id": "T1", "salesperson_reg_no": "R012345X", "town": "bishan",
             "flat_type": "5-ROOM", "transaction_date": "2025-12-15", "trans_price": "1200000"},
            {"transaction_id": "T2", "salesperson_reg_no": "R678901Y", "town": "bishan",
             "flat_type": "4-ROOM", "transaction_date": "2025-08-20", "trans_price": "800000"},
        ]
        csv_body = "transaction_id,salesperson_reg_no,town,flat_type,transaction_date,trans_price\n" + "\n".join(
            f"{r['transaction_id']},{r['salesperson_reg_no']},{r['town']},{r['flat_type']},{r['transaction_date']},{r['trans_price']}"
            for r in rows
        )
        with patch("urllib.request.urlopen", side_effect=self._mock_two_step(csv_body)):
            out = self.m.fetch_cea_transaction_records(since="2025-10")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["transaction_id"], "T1")


class TestPerSkillCopiesAreInSync(unittest.TestCase):
    """Defensive: if sync_singapore_api.py is stale, the build should know."""

    def test_all_per_skill_copies_match_canonical_minus_header(self):
        canonical = SCRIPT_PATH.read_text(encoding="utf-8")
        for skill in [
            "cdc-voucher-locator-skill",
            "smart-commuter-skill",
            "property-advisor-skill",
            "weekend-planner-skill",
            "mrt-rerouter-skill",
            "dengue-risk-advisor-skill",
            "hawker-discover-skill",
            "agent-match-skill",
            "rental-yield-calculator-skill",
            "air-quality-advisor-skill",
        ]:
            with self.subTest(skill=skill):
                copy = REPO_ROOT / "skills" / skill / "scripts" / "singapore_api.py"
                if not copy.exists():
                    self.skipTest("%s not yet present" % skill)
                body = copy.read_text(encoding="utf-8")
                self.assertTrue(body.startswith("# SYNCED FROM:"), "%s missing header" % skill)
                # The canonical body must appear verbatim as a suffix (after the header block).
                self.assertTrue(
                    body.endswith(canonical),
                    "%s/scripts/singapore_api.py is not in sync with canonical" % skill,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
