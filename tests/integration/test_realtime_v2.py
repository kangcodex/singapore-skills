"""
Integration tests for v2-only / transport fetchers.

MRT train arrival is v2-only; bus arrival + taxi availability work on both
v1 and v2. require_api_key() is unit-tested without the key set.

Run:  python3 -m unittest discover -s tests/integration
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "singapore_api.py"


def _load_fresh_module(tmp_cache_root, env_extra=None):
    spec = importlib.util.spec_from_file_location("singapore_api", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = module
    env = {"HERMES_CACHE_ROOT": str(tmp_cache_root)}
    if env_extra:
        env.update(env_extra)
    with patch.dict(os.environ, env, clear=True):
        spec.loader.exec_module(module)
    return module


def _has_real_data(out):
    """True only when the response carries a non-empty items/data/metadata
    list or dict. Empty `items: []` is NOT real data."""
    if not isinstance(out, dict) or not out:
        return False
    for key in ("items", "data", "metadata", "features"):
        v = out.get(key)
        if isinstance(v, dict) and v:
            return True
        if isinstance(v, list) and len(v) > 0:
            return True
    return False


def _has_lta_key():
    """LTA DataMall key (separate from DATA_GOV_SG_API_KEY). When unset,
    MRT and bus arrival tests are skipped — v1 has no MRT data and v2
    requires this key."""
    return bool(os.environ.get("LTA_DATA_MALL_API_KEY"))


class TestV2Transport(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.api = _load_fresh_module(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_mrt_arrival_returns_data(self):
        if not _has_lta_key():
            self.skipTest("LTA_DATA_MALL_API_KEY not set; MRT data requires it")
        out = self.api.fetch_lta_mrt_arrival("NS1")
        self.assertTrue(_has_real_data(out))

    def test_bus_arrival_returns_data(self):
        if not _has_lta_key():
            self.skipTest("LTA_DATA_MALL_API_KEY not set; bus arrival requires it")
        out = self.api.fetch_lta_bus_arrival(bus_stop_code="01012")
        self.assertTrue(_has_real_data(out))

    def test_taxi_availability_returns_data(self):
        out = self.api.fetch_lta_taxi_availability()
        self.assertTrue(_has_real_data(out))


class TestRequireApiKey(unittest.TestCase):

    def test_require_api_key_raises_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            api = _load_fresh_module(tempfile.mkdtemp())
            with self.assertRaises(RuntimeError) as ctx:
                api.require_api_key()
            self.assertIn("DATA_GOV_SG_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
