"""Evidence-bound focused answers, documents and family functions."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestFocusedEvidence(unittest.TestCase):
    def test_mrt_question_does_not_require_financial_intake(self) -> None:
        from advisor_questions import question_plan
        result = question_plan({"kinds": ["proximity"], "known_inputs": {"location": "Fixture Road"}})
        self.assertEqual(result["questions"][0]["missing_inputs"], [])
        self.assertNotIn("income", result["questions"][0]["required_inputs"])

    def test_unknown_location_wrapper_is_still_missing_information(self) -> None:
        from advisor_questions import question_plan
        result = question_plan({"kinds": ["proximity"], "known_inputs": {"location": {"state": "unknown", "value": None}}})
        self.assertEqual(result["questions"][0]["missing_inputs"], ["location"])

    def test_mixed_question_preserves_the_answerable_location_part(self) -> None:
        from advisor_questions import question_plan
        result = question_plan({"kinds": ["proximity", "funding"], "known_inputs": {"location": "FixtureHome"}})
        self.assertEqual(result["questions"][0]["missing_inputs"], [])
        self.assertTrue(result["questions"][1]["missing_inputs"])

    def test_straight_line_is_not_a_walk_constraint_pass(self) -> None:
        from advisor_location import assess_location
        result = assess_location({"as_of": "2026-10-24", "origin_id": "home", "limits": [{"destination_id": "station", "max_walk_m": "600"}], "routes": [{"id": "r1", "origin_id": "home", "destination_id": "station", "measurement": "straight_line", "distance_m": "400", "source": "fixture://map", "retrieved_at": "2026-10-24", "horizon": "current", "service_status": "operating"}]})
        self.assertEqual(result["assessments"][0]["result"], "unknown")

    def test_actual_entrance_route_can_be_compared(self) -> None:
        from advisor_location import assess_location
        result = assess_location({"as_of": "2026-10-24", "origin_id": "home", "limits": [{"destination_id": "station", "max_walk_m": "600"}], "routes": [{"id": "r1", "origin_id": "home", "destination_id": "station", "measurement": "routed_walk", "endpoint_scope": "entrance_to_entrance", "distance_m": "550", "source": "fixture://walk-route", "retrieved_at": "2026-10-24", "horizon": "current", "service_status": "operating"}]})
        self.assertEqual(result["assessments"][0]["result"], "pass")

    def test_walk_time_uses_a_supplied_route_not_a_distance_conversion(self) -> None:
        from advisor_location import assess_location
        result = assess_location({"as_of": "2026-10-24", "origin_id": "home", "limits": [{"destination_id": "station", "max_walk_minutes": "8"}], "routes": [{"id": "r1", "origin_id": "home", "destination_id": "station", "measurement": "routed_walk", "endpoint_scope": "entrance_to_entrance", "minutes": "7", "source": "fixture://walk-route", "retrieved_at": "2026-10-24", "horizon": "current", "service_status": "operating"}]})
        self.assertEqual(result["assessments"][0]["result"], "pass")

    def test_next_train_arrival_cannot_prove_a_journey_limit(self) -> None:
        from advisor_location import assess_location
        result = assess_location({"as_of": "2026-10-24", "origin_id": "home", "limits": [{"destination_id": "work", "max_minutes": "30"}], "routes": [{"id": "r1", "origin_id": "home", "destination_id": "work", "measurement": "arrival_only", "minutes": "5", "source": "fixture://arrival", "retrieved_at": "2026-10-24", "horizon": "current", "service_status": "operating"}]})
        self.assertEqual(result["assessments"][0]["result"], "unknown")

    def test_future_route_is_not_current_access(self) -> None:
        from advisor_location import assess_location
        result = assess_location({"as_of": "2026-10-24", "origin_id": "home", "limits": [{"destination_id": "station", "max_walk_m": "600"}], "routes": [{"id": "r1", "origin_id": "home", "destination_id": "station", "measurement": "routed_walk", "endpoint_scope": "entrance_to_entrance", "distance_m": "400", "source": "fixture://plan", "retrieved_at": "2026-10-24", "horizon": "future", "service_status": "planned"}]})
        self.assertEqual(result["assessments"][0]["result"], "unknown")

    def test_closed_amenity_and_unverified_school_band_remain_distinct(self) -> None:
        from advisor_location import assess_amenities
        result = assess_amenities({"as_of": "2026-10-24", "cohort": "2028", "items": [{"id": "a1", "kind": "groceries", "operating_status": "closed", "source": "fixture://closure", "retrieved_at": "2026-10-24"}, {"id": "s1", "kind": "primary_school", "distance_m": "500", "distance_basis": "straight_line", "source": "fixture://map", "retrieved_at": "2026-10-24"}]})
        self.assertEqual(result["items"][0]["status"], "closed")
        self.assertIsNone(result["items"][1]["official_distance_band"])

    def test_claimed_method_without_verification_cannot_certify_school_band(self) -> None:
        from advisor_location import assess_amenities
        result = assess_amenities({"as_of": "2026-10-24", "cohort": "2028", "items": [{"id": "s1", "kind": "primary_school", "distance_m": "500", "official_distance_method": "agent says official", "cohort": "2028", "address_basis": "some map centroid", "source": "fixture://listing", "retrieved_at": "2026-10-24"}]})
        self.assertIsNone(result["items"][0]["official_distance_band"])


class TestDocumentAndComfort(unittest.TestCase):
    def test_matrix_disclaimer_prevents_unit_quote(self) -> None:
        from advisor_documents import assess_documents
        result = assess_documents({"documents": [{"id": "d1", "version": "A", "source": "fixture://brochure", "pages": 2, "price_disclaimer": "Not actual prices", "extraction_status": "text_only"}], "claims": [{"id": "c1", "document_id": "d1", "page": 1, "key": "price", "value": "2000000", "price_kind": "quotation", "scope": "project"}]})
        self.assertEqual(result["claims"][0]["price_kind"], "scenario")
        self.assertFalse(result["exact_unit_quote_supported"])

    def test_explicit_revision_supersedes_old_fact(self) -> None:
        from advisor_documents import assess_documents
        result = assess_documents({"documents": [{"id": "old", "version": "A", "source": "fixture://old", "pages": 2, "extraction_status": "text_only"}, {"id": "new", "version": "B", "source": "fixture://new", "pages": 2, "supersedes": ["old"], "extraction_status": "text_only"}], "claims": [{"id": "a", "document_id": "old", "page": 1, "key": "expected_top", "value": "2029", "scope": "project"}, {"id": "b", "document_id": "new", "page": 1, "key": "expected_top", "value": "2030", "scope": "project"}]})
        self.assertEqual(result["effective_claims"]["project:expected_top"]["value"], "2030")
        self.assertEqual(result["superseded_claim_ids"], ["a"])

    def test_unresolved_versions_do_not_pick_a_favorable_fact(self) -> None:
        from advisor_documents import assess_documents
        result = assess_documents({"documents": [{"id": "a", "source": "fixture://a", "pages": 1}, {"id": "b", "source": "fixture://b", "pages": 1}], "claims": [{"id": "a1", "document_id": "a", "page": 1, "key": "bedrooms", "value": 3, "scope": "layout"}, {"id": "b1", "document_id": "b", "page": 1, "key": "bedrooms", "value": 2, "scope": "layout"}]})
        self.assertEqual(result["effective_claims"]["layout:bedrooms"]["state"], "conflicting")

    def test_old_or_other_unit_quote_cannot_be_promoted_to_current_support(self) -> None:
        from advisor_documents import assess_documents
        result = assess_documents({"as_of": "2026-10-24", "candidate_id": "home", "documents": [{"id": "d1", "source": "fixture://quote", "pages": 1, "extraction_status": "completed"}], "claims": [{"id": "q", "document_id": "d1", "page": 1, "key": "price", "value": "2000000", "price_kind": "quotation", "scope": "unit", "candidate_id": "other", "quoted_at": "2020-01-01", "valid_until": "2020-01-10"}]})
        self.assertFalse(result["exact_unit_quote_supported"])

    def test_same_unit_current_dated_quote_can_be_identified(self) -> None:
        from advisor_documents import assess_documents
        result = assess_documents({"as_of": "2026-10-24", "candidate_id": "home", "documents": [{"id": "d1", "source": "fixture://quote", "pages": 1, "extraction_status": "completed"}], "claims": [{"id": "q", "document_id": "d1", "page": 1, "key": "price", "value": "2000000", "price_kind": "quotation", "scope": "unit", "candidate_id": "home", "quoted_at": "2026-10-24", "valid_until": "2026-10-25"}]})
        self.assertTrue(result["exact_unit_quote_supported"])

    def test_master_access_study_and_wc_do_not_become_bedroom_and_full_bath(self) -> None:
        from advisor_comfort import assess_comfort
        rooms = [{"id": identity, "kind": "bedroom", "approved_bedroom": True, "common_access": True, "enclosed": True, "window": True, "source": "fixture://plan"} for identity in ("master", "child1")]
        rooms += [{"id": "study", "kind": "study", "common_access": False, "source": "fixture://plan"}]
        result = assess_comfort({"household": {"sleeping_groups": ["parents", "child1", "child2"], "min_full_bathrooms": 3}, "layout": {"rooms_complete": True, "bathrooms_complete": True, "rooms": rooms, "bathrooms": [{"kind": "full", "source": "fixture://plan"}, {"kind": "full", "source": "fixture://plan"}, {"kind": "wc", "source": "fixture://plan"}]}})
        self.assertEqual(result["sleeping_fit"], "fail")
        self.assertEqual(result["full_bathrooms"], 2)
        self.assertEqual(result["service_wc"], 1)

    def test_agreed_sharing_changes_sleeping_fit_not_unknown_furniture(self) -> None:
        from advisor_comfort import assess_comfort
        rooms = [{"id": identity, "kind": "bedroom", "approved_bedroom": True, "common_access": True, "enclosed": True, "window": True, "source": "fixture://plan"} for identity in ("master", "children")]
        result = assess_comfort({"household": {"sleeping_groups": ["parents", "children_agreed_to_share"]}, "layout": {"rooms": rooms, "bathrooms": []}})
        self.assertEqual(result["sleeping_fit"], "pass")
        self.assertEqual(result["overall_fit"], "conditional")

    def test_partial_room_extraction_is_not_proof_of_insufficient_bedrooms(self) -> None:
        from advisor_comfort import assess_comfort
        result = assess_comfort({"household": {"sleeping_groups": ["parents", "child1", "child2"]}, "layout": {"rooms_complete": False, "rooms": [{"id": "one", "kind": "bedroom", "approved_bedroom": True, "common_access": True, "enclosed": True, "window": True, "source": "fixture://partial"}]}})
        self.assertEqual(result["sleeping_fit"], "unknown")

    def test_duplicate_plan_room_ids_cannot_inflate_bedroom_count(self) -> None:
        from advisor_comfort import assess_comfort
        from advisor_records import CaseError
        room = {"id": "same-room", "kind": "bedroom", "approved_bedroom": True, "common_access": True, "enclosed": True, "window": True, "source": "fixture://plan"}
        with self.assertRaises(CaseError):
            assess_comfort({"household": {"sleeping_groups": ["a", "b", "c"]}, "layout": {"rooms": [room, room, room]}})


if __name__ == "__main__":
    unittest.main()
