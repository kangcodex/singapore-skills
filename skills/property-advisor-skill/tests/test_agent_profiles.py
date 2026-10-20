"""Buyer profiles as data (no network)."""
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_profiles as pr  # noqa: E402

CATEGORIES = {"new_launch_condo", "resale_condo", "resale_hdb", "ec"}


class TestProfileData(unittest.TestCase):
    def test_three_profiles_plus_multigen_variant(self):
        self.assertEqual(set(pr.profile_ids()), {"dink", "first_home_couple", "family_of_five"})
        self.assertIn("multigen", pr.variants("family_of_five"))

    def test_every_profile_has_required_sections(self):
        for pid in pr.profile_ids():
            p = pr.build_profile(pid)
            for key in ("label", "priorities", "shortlist", "location", "key_questions",
                        "red_flags", "due_diligence", "related_skills"):
                self.assertTrue(p[key], f"{pid}.{key}")

    def test_shortlist_ranked_and_uses_known_categories(self):
        for pid in pr.profile_ids():
            ranks = [s["rank"] for s in pr.build_profile(pid)["shortlist"]]
            self.assertEqual(ranks, sorted(ranks))
            for s in pr.build_profile(pid)["shortlist"]:
                self.assertIn(s["category"], CATEGORIES)
                self.assertTrue(s["why"])

    def test_due_diligence_covers_every_shortlisted_category(self):
        p = pr.build_profile("dink")
        for s in p["shortlist"]:
            self.assertIn(s["category"], p["due_diligence"]["by_category"])
        self.assertTrue(p["due_diligence"]["property"])
        self.assertTrue(p["due_diligence"]["financial"])

    def test_dink_leads_with_condo_and_family_with_hdb(self):
        self.assertEqual(pr.build_profile("dink")["shortlist"][0]["category"], "resale_condo")
        self.assertEqual(pr.build_profile("family_of_five")["shortlist"][0]["category"], "resale_hdb")

    def test_multigen_variant_overrides_shortlist_and_flat_types(self):
        p = pr.build_profile("family_of_five", variant="multigen")
        top = p["shortlist"][0]
        self.assertIn("MULTI-GEN", top["flat_types"])
        self.assertGreater(len(p["priorities"]), len(pr.build_profile("family_of_five")["priorities"]))
        self.assertGreater(len(p["red_flags"]), len(pr.build_profile("family_of_five")["red_flags"]))

    def test_private_segments_expand_to_existing_mode_args(self):
        p = pr.build_profile("dink")
        cond = next(s for s in p["shortlist"] if s["category"] == "resale_condo")
        self.assertEqual([x["segment"] for x in cond["segments"]], ["rcr", "ocr"])
        self.assertEqual(cond["segments"][0]["valuation_args"], {"mode": "private", "region": "rest_central"})
        hdb = next(s for s in p["shortlist"] if s["category"] == "resale_hdb")
        self.assertEqual(hdb["valuation_args"]["mode"], "hdb")

    def test_family_location_flags_school_distance_as_unverified(self):
        sch = pr.build_profile("family_of_five")["location"]["schools"]
        self.assertEqual(sch["status"], "unverified")
        self.assertTrue(sch["unverified_reason"])

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError):
            pr.build_profile("nope")


if __name__ == "__main__":
    unittest.main()
