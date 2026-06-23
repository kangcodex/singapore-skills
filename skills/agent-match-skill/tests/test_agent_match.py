"""Tests for agent-match-skill (S10b MVP + S10c extensions)."""
import json
import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _load_module():
    import importlib
    m = importlib.import_module("agent_match")
    importlib.reload(m)
    return m


def _cea_rows():
    """Two active salespersons; one with reg_no prefix, one with name fragment."""
    return [
        {"registration_no": "R012345X", "name": "Alice Tan", "status": "active", "agency": "ERA Realty"},
        {"registration_no": "R067890Z", "name": "Alice Wong", "status": "active", "agency": "PropNex"},
    ]


class TestAgentMatchName(unittest.TestCase):

    def test_name_hit_returns_two_matches(self):
        m = _load_module()
        with patch.object(m, "fetch_cea_salesperson", return_value=_cea_rows()):
            out = m.lookup("Alice")
        self.assertEqual(out["query"], "Alice")
        self.assertEqual(out["match_count"], 2)
        self.assertEqual(out["matches"][0]["registration_no"], "R012345X")
        self.assertEqual(out["matches"][0]["name"], "Alice Tan")
        self.assertEqual(out["matches"][0]["agency"], "ERA Realty")

    def test_name_no_match_returns_zero(self):
        m = _load_module()
        with patch.object(m, "fetch_cea_salesperson", return_value=[]):
            out = m.lookup("Nonexistent Person")
        self.assertEqual(out["match_count"], 0)
        self.assertEqual(out["matches"], [])


class TestAgentMatchRegNo(unittest.TestCase):

    def test_reg_no_exact_hit(self):
        m = _load_module()
        with patch.object(m, "fetch_cea_salesperson", return_value=[_cea_rows()[0]]):
            out = m.lookup("R012345X")
        self.assertEqual(out["match_count"], 1)
        self.assertEqual(out["matches"][0]["registration_no"], "R012345X")


class TestAgentMatchEmptyQuery(unittest.TestCase):

    def test_empty_query_rejected(self):
        m = _load_module()
        with patch.object(m, "fetch_cea_salesperson", return_value=[]) as mock_cea:
            # main() with no args — exactly one of --name/--registration-no required
            from io import StringIO
            captured = StringIO()
            with patch("sys.stdout", captured):
                rc = m.main([])
        self.assertEqual(rc, 0)
        body = json.loads(captured.getvalue())
        self.assertIn("error", body)
        # The mock shouldn't be called because we error out before any network
        self.assertEqual(mock_cea.call_count, 0)


class TestPostcodeFilter(unittest.TestCase):

    def test_postcode_sector_extraction(self):
        m = _load_module()
        self.assertEqual(m.postcode_sector("570123"), "57")
        self.assertEqual(m.postcode_sector("  123456"), "12")
        self.assertEqual(m.postcode_sector("AB1234"), "")

    def test_postcode_in_result_adds_location_block(self):
        m = _load_module()
        result = {"query": "Alice", "matches": [], "match_count": 0}
        with patch.object(m, "geocode", return_value=("Bishan", 1.3508, 103.8494, "570123")):
            out = m.with_postcode(result, "570123")
        self.assertIn("location", out)
        self.assertEqual(out["location"]["postcode"], "570123")
        self.assertEqual(out["location"]["sector"], "57")
        self.assertEqual(out["location"]["geocoded_address"], "Bishan")

    def test_postcode_invalid_raises(self):
        m = _load_module()
        result = {"query": "Alice", "matches": [], "match_count": 0}
        with self.assertRaises(ValueError):
            m.with_postcode(result, "12345")  # only 5 digits
        with self.assertRaises(ValueError):
            m.with_postcode(result, "AB1234")  # not digits


class TestTrackRecord(unittest.TestCase):

    def _trans_rows(self):
        return [
            {"salesperson_reg_no": "R012345X", "transaction_date": "2025-11-15", "town": "bishan", "flat_type": "5-ROOM"},
            {"salesperson_reg_no": "R012345X", "transaction_date": "2025-09-20", "town": "bishan", "flat_type": "5-ROOM"},
            {"salesperson_reg_no": "R067890Z", "transaction_date": "2025-08-01", "town": "bishan", "flat_type": "5-ROOM"},
        ]

    def test_track_record_counts_per_reg_no(self):
        m = _load_module()
        result = {
            "query": "Alice",
            "matches": [
                {"registration_no": "R012345X", "name": "Alice Tan", "status": "active", "agency": "ERA"},
                {"registration_no": "R067890Z", "name": "Alice Wong", "status": "active", "agency": "PropNex"},
            ],
            "match_count": 2,
        }
        with patch.object(m, "fetch_cea_transaction_records", return_value=self._trans_rows()):
            out = m.with_track_record(result, "bishan", "5-ROOM")
        self.assertEqual(out["matches"][0]["track_record"]["closed_in_town"], 2)
        self.assertEqual(out["matches"][0]["track_record"]["last_deal_date"], "2025-11-15")
        self.assertEqual(out["matches"][1]["track_record"]["closed_in_town"], 1)
        self.assertEqual(out["matches"][1]["track_record"]["last_deal_date"], "2025-08-01")

    def test_track_record_no_matches_returns_zeros(self):
        m = _load_module()
        result = {
            "query": "Bob",
            "matches": [{"registration_no": "R999999Z", "name": "Bob", "status": "active", "agency": "X"}],
            "match_count": 1,
        }
        with patch.object(m, "fetch_cea_transaction_records", return_value=[]):
            out = m.with_track_record(result, "bishan", "5-ROOM")
        self.assertEqual(out["matches"][0]["track_record"]["closed_in_town"], 0)
        self.assertIsNone(out["matches"][0]["track_record"]["last_deal_date"])


class TestAgentMatchCLI(unittest.TestCase):

    def test_cli_name_hit(self):
        m = _load_module()
        from io import StringIO
        captured = StringIO()
        with patch.object(m, "fetch_cea_salesperson", return_value=_cea_rows()), \
             patch("sys.stdout", captured):
            rc = m.main(["--name", "Alice"])
        self.assertEqual(rc, 0)
        body = json.loads(captured.getvalue())
        self.assertEqual(body["query"], "Alice")
        self.assertEqual(body["match_count"], 2)

    def test_cli_error_on_both_name_and_reg_no(self):
        m = _load_module()
        from io import StringIO
        captured = StringIO()
        with patch("sys.stdout", captured):
            rc = m.main(["--name", "Alice", "--registration-no", "R012345X"])
        self.assertEqual(rc, 0)
        body = json.loads(captured.getvalue())
        self.assertIn("error", body)

    def test_cli_with_postcode_and_track_record(self):
        m = _load_module()
        from io import StringIO
        captured = StringIO()
        with patch.object(m, "fetch_cea_salesperson", return_value=_cea_rows()), \
             patch.object(m, "fetch_cea_transaction_records", return_value=[
                 {"salesperson_reg_no": "R012345X", "transaction_date": "2025-11-15", "town": "bishan", "flat_type": "5-ROOM"},
             ]), \
             patch.object(m, "geocode", return_value=("Bishan", 1.3508, 103.8494, "570123")), \
             patch("sys.stdout", captured):
            rc = m.main(["--name", "Alice", "--postcode", "570123", "--town", "BISHAN", "--flat-type", "5-ROOM"])
        self.assertEqual(rc, 0)
        body = json.loads(captured.getvalue())
        self.assertIn("location", body)
        self.assertEqual(body["location"]["sector"], "57")
        self.assertEqual(body["matches"][0]["track_record"]["closed_in_town"], 1)


class TestModuleImport(unittest.TestCase):

    def test_public_names_importable(self):
        m = _load_module()
        for n in ["lookup", "with_postcode", "with_track_record", "postcode_sector", "main"]:
            with self.subTest(name=n):
                self.assertTrue(callable(getattr(m, n)), "%s not callable" % n)


if __name__ == "__main__":
    unittest.main()
