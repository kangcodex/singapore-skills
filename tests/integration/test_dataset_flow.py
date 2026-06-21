"""
Integration tests for the data.gov.sg Collection/Dataset download flow.

These tests hit the live api-open.data.gov.sg endpoints (1 call per dataset,
per test file, since CACHE_ROOT is monkey-patched to a tmp dir per-file).

Prerequisites:
    DATA_GOV_SG_API_KEY must be set in the env (from .env at repo root).

Run:  python3 -m unittest discover -s tests/integration
"""
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "singapore_api.py"


def _load_fresh_module(tmp_cache_root):
    """Reload singapore_api with a clean cache root for this test file."""
    spec = importlib.util.spec_from_file_location("singapore_api", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["singapore_api"] = module
    with patch.dict(os.environ, {"HERMES_CACHE_ROOT": str(tmp_cache_root)}):
        spec.loader.exec_module(module)
    return module


class TestDatasetFlow(unittest.TestCase):
    """Tracer bullet: HDB Resale flat prices. Documents: docs/api/HDB.md."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.api = _load_fresh_module(self._tmp.name)
        if not os.environ.get("DATA_GOV_SG_API_KEY"):
            self.skipTest("DATA_GOV_SG_API_KEY not set — skipping live test")

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetch_dataset_rows_hdb_resale_returns_csv_rows(self):
        """HDB.md line 143: Resale Flat Prices (monthly) dataset
        d_8b84c4ee58e3cfc0ece0d773c8ca6abc returns CSV with month,town,
        flat_type,resale_price columns."""
        rows = self.api.fetch_dataset_rows(
            "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
        )
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0, "expected at least one resale row")
        first = rows[0]
        for col in ("month", "town", "flat_type", "resale_price"):
            self.assertIn(col, first, f"missing column {col!r} in {list(first)}")

    def test_fetch_dataset_geojson_ura_master_plan_returns_features(self):
        """URA Master Plan 2019 land use layer (GeoJSON) returns a
        FeatureCollection with at least one feature. Verifies the geojson
        variant of the dataset flow."""
        fc = self.api.fetch_dataset_geojson(
            "d_90d86daa5bfaa371668b84fa5f01424f"
        )
        self.assertEqual(fc.get("type"), "FeatureCollection")
        features = fc.get("features", [])
        self.assertGreater(len(features), 0, "expected at least one feature")
        first = features[0]
        self.assertIn("geometry", first)
        self.assertIn("properties", first)

    def test_dataset_flow_caches_second_call(self):
        """After the first fetch, a second call to the same dataset should
        hit the cache and not make a fresh network round-trip.

        We mock urllib.request.urlopen and assert it is only called once
        across two fetch_dataset_rows() calls for the same dataset."""
        import unittest.mock as mock

        ds = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
        first = self.api.fetch_dataset_rows(ds)
        self.assertGreater(len(first), 0, "first fetch returned no rows")

        with mock.patch(
            "urllib.request.urlopen", side_effect=AssertionError("network called")
        ) as m:
            second = self.api.fetch_dataset_rows(ds)
        m.assert_not_called()
        self.assertEqual(len(first), len(second))

    def test_fetch_dataset_geojson_sportsg_returns_features(self):
        """SportSG sport facilities (GeoJSON) — used by weekend-planner as
        the indoor pivot when UV ≥ 11. d_9b87bab59d036a60fad2a91530e10773
        returns a FeatureCollection with at least one facility."""
        fc = self.api.fetch_dataset_geojson(
            "d_9b87bab59d036a60fad2a91530e10773"
        )
        self.assertEqual(fc.get("type"), "FeatureCollection")
        features = fc.get("features", [])
        self.assertGreater(len(features), 0, "expected at least one facility")


if __name__ == "__main__":
    unittest.main()
