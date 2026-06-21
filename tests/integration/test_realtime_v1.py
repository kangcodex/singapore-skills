"""
Integration tests for the NEA / LTA v1 real-time fetchers.

These hit the live api.data.gov.sg endpoints (v2 by default since the key
is set, with v1 fallback). Cache is per-test tmp dir so each test makes one
network call.

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


def _load_fresh_module(tmp_cache_root):
    spec = importlib.util.spec_from_file_location("singapore_api", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = module
    with patch.dict(os.environ, {"HERMES_CACHE_ROOT": str(tmp_cache_root)}):
        spec.loader.exec_module(module)
    return module


def _has_data(out):
    if not isinstance(out, dict) or not out:
        return False
    for key in ("items", "data", "metadata"):
        v = out.get(key)
        if isinstance(v, dict) and v:
            return True
        if isinstance(v, list) and v:
            return True
    return bool(out)


class TestV1Environment(unittest.TestCase):
    """NEA v1 environment endpoints (also reachable on v2 via the helper)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.api = _load_fresh_module(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_psi_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_psi()))

    def test_pm25_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_pm25()))

    def test_uv_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_uv()))

    def test_two_hour_forecast_returns_data(self):
        out = self.api.fetch_two_hour_forecast()
        self.assertIn("items", out)
        self.assertGreater(len(out["items"]), 0)

    def test_twenty_four_hour_forecast_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_twenty_four_hour_forecast()))

    def test_four_day_forecast_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_four_day_forecast()))

    def test_rainfall_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_rainfall()))

    def test_temperature_returns_data(self):
        self.assertTrue(_has_data(self.api.fetch_temperature()))


if __name__ == "__main__":
    unittest.main()
