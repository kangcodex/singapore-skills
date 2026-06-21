"""
Local-only tests for the auth-headers surface in singapore_api.

Verifies the headers attached to dataset poll/initiate and v2 real-time
calls, plus the API key / require_api_key helpers. No network.

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
    spec.loader.exec_module(module)
    return module


class _EnvCtx:
    def __init__(self, env, tmp_cache_root):
        base = {"HERMES_CACHE_ROOT": str(tmp_cache_root)}
        base.update(env)
        self._cm = patch.dict(os.environ, base, clear=True)
        spec = importlib.util.spec_from_file_location("singapore_api", SCRIPT_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["singapore_api"] = module
        self._cm.__enter__()
        spec.loader.exec_module(module)
        self._module = module

    def __enter__(self):
        return self._module

    def __exit__(self, *args):
        self._cm.__exit__(*args)


def _load_in_env(env, tmp_cache_root):
    return _EnvCtx(env, tmp_cache_root)


class TestAuthHeaders(unittest.TestCase):

    def test_dataset_headers_always_has_user_agent(self):
        with _load_in_env({}, tempfile.mkdtemp()) as api:
            h = api._dataset_headers()
            self.assertEqual(h["User-Agent"], api.USER_AGENT)
            self.assertEqual(h["Content-Type"], "application/json")

    def test_dataset_headers_includes_x_api_key_when_set(self):
        with _load_in_env(
            {"DATA_GOV_SG_API_KEY": "v2:fake_key_for_test"}, tempfile.mkdtemp()
        ) as api:
            h = api._dataset_headers()
            self.assertEqual(h["x-api-key"], "v2:fake_key_for_test")

    def test_dataset_headers_omits_x_api_key_when_unset(self):
        with _load_in_env({}, tempfile.mkdtemp()) as api:
            h = api._dataset_headers()
            self.assertNotIn("x-api-key", h)

    def test_api_key_returns_none_when_unset(self):
        with _load_in_env({}, tempfile.mkdtemp()) as api:
            self.assertIsNone(api._api_key())

    def test_api_key_returns_value_when_set(self):
        with _load_in_env(
            {"DATA_GOV_SG_API_KEY": "abc"}, tempfile.mkdtemp()
        ) as api:
            self.assertEqual(api._api_key(), "abc")

    def test_require_api_key_raises_when_unset(self):
        with _load_in_env({}, tempfile.mkdtemp()) as api:
            with self.assertRaises(RuntimeError) as ctx:
                api.require_api_key()
            self.assertIn("DATA_GOV_SG_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
