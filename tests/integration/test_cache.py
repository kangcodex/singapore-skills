"""
Local-only tests for the cache layer in singapore_api.

Verifies round-trip persistence and that corrupt cache files are treated as
misses. No network calls.

Run:  python3 -m unittest discover -s tests/integration
"""
import importlib.util
import json
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


class TestCache(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.api = _load_fresh_module(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cache_round_trip(self):
        payload = {"hello": "world", "n": 42}
        self.api._cache_put("ns", "k1", payload)
        loaded = self.api._cache_get("ns", "k1")
        self.assertEqual(loaded, payload)

    def test_cache_miss_returns_none(self):
        self.assertIsNone(self.api._cache_get("ns", "absent"))

    def test_corrupt_cache_returns_none(self):
        cache_dir = Path(self._tmp.name) / "ns"
        cache_dir.mkdir(parents=True, exist_ok=True)
        bad_file = cache_dir / "deadbeef.json"
        bad_file.write_text("{not valid json,,,")
        self.assertIsNone(self.api._cache_get("ns", "deadbeef"))

    def test_cache_namespaces_isolated(self):
        self.api._cache_put("ns-a", "k", {"a": 1})
        self.api._cache_put("ns-b", "k", {"b": 2})
        self.assertEqual(self.api._cache_get("ns-a", "k"), {"a": 1})
        self.assertEqual(self.api._cache_get("ns-b", "k"), {"b": 2})


if __name__ == "__main__":
    unittest.main()
