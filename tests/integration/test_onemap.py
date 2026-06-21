"""
Integration tests for OneMap geocoding (cdc-voucher-locator skill).

`geocode(query)` resolves a place name or postal code to (lat, lon, postal,
address) via https://www.onemap.gov.sg/api/common/elastic/search.

Run:  python3 -m unittest discover -s tests/integration
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "cdc-voucher-locator-skill"
    / "scripts"
    / "cdc_voucher_locator.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("cdc_voucher_locator", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["cdc_voucher_locator"] = module
    spec.loader.exec_module(module)
    return module


class TestOneMapGeocode(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = _load_module()

    def test_geocode_known_place_returns_coords(self):
        result = self.api.geocode("Singapore Post Centre")
        self.assertIsNotNone(result[0], f"geocode failed: {result}")
        lat, lon, postal, address = result
        self.assertIsInstance(lat, float)
        self.assertIsInstance(lon, float)
        self.assertTrue(1.0 < lat < 2.0, f"lat out of range: {lat}")
        self.assertTrue(103.0 < lon < 104.5, f"lon out of range: {lon}")

    def test_geocode_postal_code_returns_coords(self):
        result = self.api.geocode("238859")
        self.assertIsNotNone(result[0], f"geocode failed: {result}")
        lat, lon, postal, address = result
        self.assertEqual(postal, "238859")
        self.assertIsInstance(lat, float)

    def test_geocode_garbage_returns_none_with_error(self):
        result = self.api.geocode("ZZZ_NOSUCH_PLACE_XYZ_9999")
        self.assertIsNone(result[0])
        self.assertIsNotNone(result[1], "expected an error message string")


if __name__ == "__main__":
    unittest.main()
