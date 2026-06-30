#!/usr/bin/env python3
"""Smoke tests for sg-home-chef-skill.

Mirrors the overseas-trip-planner-skill/tests/test_trip_concierge.py pattern:
- Stdlib unittest only
- Module imported via importlib
- CLI tests use subprocess
- Determinism check
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "sg_home_chef.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("sg_home_chef", SCRIPT)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class SkillLevelResolutionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_canonical_levels(self):
        for level in ("beginner", "intermediate", "advanced"):
            self.assertEqual(self.m._resolve_skill_level(level), level)

    def test_aliases_known(self):
        # Aliases that the script's alias dict maps
        self.assertEqual(self.m._resolve_skill_level("newbie"), "beginner")
        self.assertEqual(self.m._resolve_skill_level("mid"), "intermediate")
        self.assertEqual(self.m._resolve_skill_level("expert"), "advanced")
        self.assertEqual(self.m._resolve_skill_level("pro"), "advanced")

    def test_case_insensitive(self):
        self.assertEqual(self.m._resolve_skill_level("Beginner"), "beginner")
        self.assertEqual(self.m._resolve_skill_level("ADVANCED"), "advanced")

    def test_unknown_returns_none(self):
        # Script returns None for unknown aliases (caller decides what to do)
        self.assertIsNone(self.m._resolve_skill_level("guru"))


class SourcingResolutionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_canonical_tracks(self):
        self.assertEqual(self.m._resolve_sourcing("supermarket"), "supermarket")
        self.assertEqual(self.m._resolve_sourcing("wet-market"), "wet-market")

    def test_aliases(self):
        self.assertEqual(self.m._resolve_sourcing("ntuc"), "supermarket")
        self.assertEqual(self.m._resolve_sourcing("tekka"), "wet-market")
        self.assertEqual(self.m._resolve_sourcing("tiong bahru"), "wet-market")


class DietaryResolutionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_canonical(self):
        for d in ("none", "halal", "vegetarian", "vegan", "no-beef", "no-pork", "gluten-free"):
            self.assertEqual(self.m._resolve_dietary(d), d)

    def test_unknown_returns_none(self):
        # Script returns "none" (default) for unknown dietary
        self.assertEqual(self.m._resolve_dietary("halal-certified"), "none")
        self.assertEqual(self.m._resolve_dietary(""), "none")


class DishNormalizationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_lowercases_and_strips(self):
        self.assertEqual(self.m._normalise_dish("  Sambal Kang Kong "), "sambal kang kong")

    def test_canonical_substrings(self):
        # "Laksa" matches the "laksa" recipe template
        self.assertEqual(self.m._normalise_dish("Laksa"), "laksa")
        self.assertEqual(self.m._normalise_dish("Roti Prata"), "roti prata")


class SkillStrategyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_beginner_strategy(self):
        s = self.m._SKILL_STRATEGY["beginner"]
        self.assertTrue(s["rempah_shortcut_ok"])
        self.assertFalse(s["wok_hei_required"])
        self.assertFalse(s["manual_grinding_required"])
        self.assertIn("time_minutes", s)
        self.assertIn("visual_milestones", s)
        self.assertIn("aroma_milestones", s)

    def test_intermediate_strategy(self):
        s = self.m._SKILL_STRATEGY["intermediate"]
        self.assertFalse(s["wok_hei_required"])
        self.assertGreaterEqual(len(s["visual_milestones"]), 3)

    def test_advanced_strategy(self):
        s = self.m._SKILL_STRATEGY["advanced"]
        self.assertTrue(s["wok_hei_required"])
        self.assertTrue(s["manual_grinding_required"])


class IngredientDictionaryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_ingredient_dict_size(self):
        # Script has 19 ingredients (sambal_paste, calamansi, etc.)
        self.assertGreaterEqual(len(self.m._INGREDIENT_DICT), 18)

    def test_required_keys(self):
        for key, entry in self.m._INGREDIENT_DICT.items():
            for k in ("sg_name", "malay", "chinese", "supermarket_sku", "wet_market_request"):
                self.assertIn(k, entry, f"ingredient '{key}' missing key '{k}'")

    def test_kangkung(self):
        e = self.m._INGREDIENT_DICT["kangkung"]
        self.assertEqual(e["malay"], "Kangkung")
        self.assertIn("\u7a7a\u5fc3\u83dc", e["chinese"])

    def test_calamansi(self):
        e = self.m._INGREDIENT_DICT["calamansi"]
        self.assertEqual(e["malay"], "Limau Kasturi")

    def test_chicken(self):
        e = self.m._INGREDIENT_DICT["chicken"]
        self.assertEqual(e["malay"], "Ayam")

    def test_lookup_ingredient_returns_inner_dict(self):
        # lookup_ingredient returns the inner dict (sg_name, malay, ...)
        result = self.m.lookup_ingredient("kangkung")
        self.assertIsNotNone(result)
        self.assertIn("malay", result)
        self.assertEqual(result["malay"], "Kangkung")


class ParamValidationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_minimal_valid(self):
        params_complete, missing, errors = self.m.check_params(
            "Sambal Kang Kong", "beginner", "supermarket", "none", 2, 30
        )
        self.assertTrue(params_complete)
        self.assertEqual(missing, [])
        self.assertEqual(errors, [])

    def test_missing_dish(self):
        params_complete, missing, errors = self.m.check_params(
            "", "beginner", "supermarket", "none", 2, 30
        )
        self.assertFalse(params_complete)
        self.assertIn("dish", missing)

    def test_missing_skill_level(self):
        params_complete, missing, errors = self.m.check_params(
            "Laksa", "", "supermarket", "none", 2, 30
        )
        self.assertFalse(params_complete)
        self.assertIn("skill-level", missing)

    def test_missing_sourcing_track(self):
        params_complete, missing, errors = self.m.check_params(
            "Laksa", "beginner", "", "none", 2, 30
        )
        self.assertFalse(params_complete)
        self.assertIn("sourcing-track", missing)


class ContradictionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_beginner_supermarket_no_warning(self):
        warnings = self.m.detect_contradictions("beginner", "supermarket", "none")
        self.assertEqual(warnings, [])

    def test_advanced_supermarket_warns(self):
        warnings = self.m.detect_contradictions("advanced", "supermarket", "none")
        self.assertGreater(len(warnings), 0)

    def test_advanced_wet_market_only_timing_warning(self):
        warnings = self.m.detect_contradictions("advanced", "wet-market", "none")
        self.assertEqual(len(warnings), 1)
        self.assertIn("wet market", warnings[0].lower())


class DietaryFilterTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_halal_excludes_pork(self):
        subs = self.m.build_ingredient_substitutions("sambal kang kong", "halal", "beginner")
        ingredient_names = [s["ingredient"] for s in subs]
        self.assertNotIn("pork", ingredient_names)

    def test_vegetarian_excludes_pork_and_belacan(self):
        subs = self.m.build_ingredient_substitutions("sambal kang kong", "vegetarian", "beginner")
        ingredient_names = [s["ingredient"] for s in subs]
        self.assertNotIn("pork", ingredient_names)
        self.assertNotIn("belacan", ingredient_names)


class BuildReportTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_full_report_beginner(self):
        a = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        report = self.m.build_report(a)
        self.assertEqual(report["skill_level"], "beginner")
        self.assertEqual(report["sourcing_track"], "supermarket")
        self.assertTrue(report["params_complete"])
        self.assertIn("skill_strategy", report)
        self.assertIn("sourcing_strategy", report)
        self.assertIn("ingredient_substitutions", report)
        self.assertIn("milestones", report)
        self.assertIn("recipe_blueprint", report)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["errors"], [])

    def test_full_report_advanced_vegetarian(self):
        a = argparse.Namespace(
            dish="Roti Prata",
            skill_level="advanced",
            sourcing_track="wet-market",
            dietary="vegetarian",
            servings=4,
            time_budget=240,
            json=False,
        )
        report = self.m.build_report(a)
        self.assertEqual(report["skill_level"], "advanced")
        self.assertEqual(report["sourcing_track"], "wet-market")
        self.assertEqual(report["dietary"], "vegetarian")
        # Advanced strategy always says wok_hei_required + manual_grinding_required
        self.assertTrue(report["skill_strategy"]["wok_hei_required"])
        self.assertTrue(report["skill_strategy"]["manual_grinding_required"])


class MilestoneTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def _report(self):
        a = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        return self.m.build_report(a)

    def test_milestones_have_visual_and_aroma(self):
        ms = self._report()["milestones"]
        self.assertGreaterEqual(len(ms), 3)
        types = {m["type"] for m in ms}
        self.assertIn("visual", types)
        self.assertIn("aroma", types)

    def test_milestones_are_flat_dicts(self):
        for m in self._report()["milestones"]:
            self.assertIn("type", m)
            self.assertIn("milestone", m)
            self.assertIsInstance(m["type"], str)
            self.assertIsInstance(m["milestone"], str)


class RecipeBlueprintTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_blueprint_is_dict(self):
        a = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        bp = self.m.build_report(a)["recipe_blueprint"]
        self.assertIsInstance(bp, dict)
        self.assertIn("dish", bp)
        self.assertIn("ingredient_count", bp)
        self.assertIn("ingredients", bp)
        self.assertIn("skill_note", bp)
        self.assertIn("dietary_flags", bp)

    def test_blueprint_ingredient_count_consistent(self):
        a = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        bp = self.m.build_report(a)["recipe_blueprint"]
        self.assertEqual(bp["ingredient_count"], len(bp["ingredients"]))
        self.assertGreater(bp["ingredient_count"], 0)


class CLITests(unittest.TestCase):

    def _run(self, *args, expect_rc=0):
        cmd = [sys.executable, str(SCRIPT), *args]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, expect_rc,
                         f"rc={res.returncode} stdout={res.stdout!r} stderr={res.stderr!r}")
        return res

    def test_minimal_valid(self):
        res = self._run("--dish", "Sambal Kang Kong",
                        "--skill-level", "beginner",
                        "--sourcing-track", "supermarket",
                        "--servings", "2",
                        "--time-budget", "30",
                        "--dietary", "halal",
                        "--json")
        report = json.loads(res.stdout)
        self.assertTrue(report["params_complete"])
        self.assertEqual(report["skill_level"], "beginner")

    def test_missing_dish_returns_2(self):
        res = self._run("--dish", "",
                        "--skill-level", "beginner",
                        "--sourcing-track", "supermarket",
                        "--json",
                        expect_rc=2)
        report = json.loads(res.stdout)
        self.assertFalse(report["params_complete"])
        self.assertIn("dish", report["missing_params"])

    def test_alias_resolution(self):
        res = self._run("--dish", "Laksa",
                        "--skill-level", "newbie",
                        "--sourcing-track", "ntuc",
                        "--json")
        report = json.loads(res.stdout)
        self.assertEqual(report["skill_level"], "beginner")
        self.assertEqual(report["sourcing_track"], "supermarket")

    def test_intermediate_wet_market(self):
        res = self._run("--dish", "Hainanese Chicken Rice",
                        "--skill-level", "intermediate",
                        "--sourcing-track", "wet-market",
                        "--servings", "4",
                        "--time-budget", "60",
                        "--json")
        report = json.loads(res.stdout)
        self.assertEqual(report["skill_level"], "intermediate")
        self.assertEqual(report["sourcing_track"], "wet-market")
        self.assertEqual(report["servings"], 4)
        self.assertEqual(report["time_budget_minutes"], 60)


class DeterminismTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _import_module()

    def test_no_random_imports(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import random", src)
        self.assertNotIn("from random", src)

    def test_no_time_module_used(self):
        src = SCRIPT.read_text(encoding="utf-8")
        # time module should not be used in the data path
        self.assertNotIn("time.time(", src)
        self.assertNotIn("time.sleep", src)

    def test_no_os_urandom(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("os.urandom", src)

    def test_same_args_same_output(self):
        a1 = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        a2 = argparse.Namespace(
            dish="Sambal Kang Kong",
            skill_level="beginner",
            sourcing_track="supermarket",
            dietary="none",
            servings=2,
            time_budget=30,
            json=False,
        )
        self.assertEqual(self.m.build_report(a1), self.m.build_report(a2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
