"""Smoke tests for the Overseas Trip Planner script.

Pure-stdlib, no network. Covers the full 5-dim preference model:
  - Month parsing (YYYY-MM, YYYY/MM, MM, month name, garbage)
  - Sunset lookup (known city, alias, unknown city, missing month)
  - Cutoff math (sunset - 60 min, edge cases, unknown)
  - Transit buffer (30% applied, zero, negative base)
  - Heavy-transit flag (boundary at 180 min)
  - Param validation (missing, invalid, complete) for all 8 params
  - Companion / Style / Pace / Accommodation / Rhythm strategies
  - Contradiction detection (auto-flagged combinations)
  - Backwards-compat with --persona and --budget aliases
  - Full CLI integration (returns 0 when complete, 2 when missing)
  - Determinism

Run:
    python3 -m unittest discover -s skills/overseas-trip-planner-skill/tests -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
SCRIPT = SCRIPTS / "trip_concierge.py"


def _import_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import trip_concierge  # type: ignore
    return trip_concierge


# --------------------------------------------------------------- month parse --

class ParseMonthTests(unittest.TestCase):
    def test_iso_year_month(self):
        m = _import_module()
        self.assertEqual(m.parse_month("2026-11"), 11)
        self.assertEqual(m.parse_month("2026-01"), 1)
        self.assertEqual(m.parse_month("2026-12"), 12)

    def test_slash_year_month(self):
        m = _import_module()
        self.assertEqual(m.parse_month("2026/11"), 11)
        self.assertEqual(m.parse_month("2026/3"), 3)

    def test_bare_month_number(self):
        m = _import_module()
        self.assertEqual(m.parse_month("7"), 7)
        self.assertEqual(m.parse_month("12"), 12)

    def test_month_name(self):
        m = _import_module()
        self.assertEqual(m.parse_month("November"), 11)
        self.assertEqual(m.parse_month("january"), 1)
        self.assertEqual(m.parse_month("Sept"), 9)
        self.assertEqual(m.parse_month("november 2026"), None)

    def test_invalid(self):
        m = _import_module()
        self.assertIsNone(m.parse_month(""))
        self.assertIsNone(m.parse_month(None))
        self.assertIsNone(m.parse_month("2026-13"))
        self.assertIsNone(m.parse_month("0"))
        self.assertIsNone(m.parse_month("13"))
        self.assertIsNone(m.parse_month("not-a-month"))


# --------------------------------------------------------------- sunset ----

class SunsetLookupTests(unittest.TestCase):
    def test_known_city_known_month(self):
        m = _import_module()
        self.assertEqual(m.lookup_sunset("Tokyo", 11), "16:25")
        self.assertEqual(m.lookup_sunset("Kyoto", 6), "19:10")
        self.assertEqual(m.lookup_sunset("Hokkaido", 1), "16:30")

    def test_alias_resolution(self):
        m = _import_module()
        self.assertEqual(m.lookup_sunset("東京", 5), "18:45")
        self.assertEqual(m.lookup_sunset("京都", 11), "16:40")
        self.assertEqual(m.lookup_sunset("TYO", 11), "16:25")
        self.assertEqual(m.lookup_sunset("HK", 6), "19:15")
        self.assertEqual(m.lookup_sunset("KL", 6), "19:15")
        self.assertEqual(m.lookup_sunset("Bali", 6), "17:55")
        self.assertEqual(m.lookup_sunset("ubud", 6), "17:55")
        self.assertEqual(m.lookup_sunset("Bombay", 6), "19:25")

    def test_case_insensitive(self):
        m = _import_module()
        self.assertEqual(m.lookup_sunset("TOKYO", 11), "16:25")
        self.assertEqual(m.lookup_sunset("tokyo", 11), "16:25")
        self.assertEqual(m.lookup_sunset("Tokyo", 11), "16:25")

    def test_unknown_city_returns_unknown(self):
        m = _import_module()
        self.assertEqual(m.lookup_sunset("Atlantis", 6), "unknown")
        self.assertEqual(m.lookup_sunset("", 6), "unknown")
        self.assertEqual(m.lookup_sunset("Singapore", 1), "19:15")


# --------------------------------------------------------------- cutoff ----

class CutoffTests(unittest.TestCase):
    def test_basic_subtraction(self):
        m = _import_module()
        self.assertEqual(m.cutoff_from_sunset("17:00"), "16:00")
        self.assertEqual(m.cutoff_from_sunset("16:25"), "15:25")
        self.assertEqual(m.cutoff_from_sunset("19:10"), "18:10")

    def test_wraps_midnight(self):
        m = _import_module()
        self.assertEqual(m.cutoff_from_sunset("00:30"), "23:30")

    def test_unknown_passthrough(self):
        m = _import_module()
        self.assertEqual(m.cutoff_from_sunset("unknown"), "unknown")
        self.assertEqual(m.cutoff_from_sunset(""), "unknown")
        self.assertEqual(m.cutoff_from_sunset(None), "unknown")

    def test_malformed_passthrough(self):
        m = _import_module()
        self.assertEqual(m.cutoff_from_sunset("garbage"), "unknown")
        self.assertEqual(m.cutoff_from_sunset("25:00"), "unknown")


# --------------------------------------------------------------- buffer ----

class TransitBufferTests(unittest.TestCase):
    def test_30_percent_added(self):
        m = _import_module()
        self.assertEqual(m.apply_transit_buffer(100), 130)
        self.assertEqual(m.apply_transit_buffer(60), 78)
        self.assertEqual(m.apply_transit_buffer(90), 117)

    def test_zero(self):
        m = _import_module()
        self.assertEqual(m.apply_transit_buffer(0), 0)

    def test_negative_clamped_to_zero(self):
        m = _import_module()
        self.assertEqual(m.apply_transit_buffer(-50), 0)

    def test_rounding(self):
        m = _import_module()
        self.assertEqual(m.apply_transit_buffer(7), 9)
        self.assertEqual(m.apply_transit_buffer(13), 17)


# --------------------------------------------------------------- heavy ----

class HeavyTransitTests(unittest.TestCase):
    def test_boundary(self):
        m = _import_module()
        self.assertFalse(m.is_heavy_transit(180))
        self.assertTrue(m.is_heavy_transit(181))
        self.assertTrue(m.is_heavy_transit(240))
        self.assertFalse(m.is_heavy_transit(120))
        self.assertFalse(m.is_heavy_transit(0))


# --------------------------------------------------------------- params ----

def _all_args(m, destination="Kyoto", month="2026-11", transport="public",
              companion="couple", style="cultural", pace="moderate",
              accommodation="premium", rhythm="early-starts", persona=None, budget=None):
    """Build a Namespace mimicking argparse output."""
    return m.argparse.Namespace(
        destination=destination,
        month=month,
        transport=transport,
        companion=companion,
        style=style,
        pace=pace,
        accommodation=accommodation,
        rhythm=rhythm,
        persona=persona,
        budget=budget,
    )


class ParamCheckTests(unittest.TestCase):
    def test_all_present(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "cultural", "moderate", "premium", "early-starts", "public"
        )
        self.assertTrue(ok)
        self.assertEqual(missing, [])
        self.assertEqual(errors, [])

    def test_all_missing(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            None, None, None, None, None, None, None, None
        )
        self.assertFalse(ok)
        # destination, month, companion, style, pace, accommodation, rhythm all missing
        for key in ("destination", "month", "companion", "style", "pace", "accommodation", "rhythm"):
            self.assertIn(key, missing)
        self.assertEqual(errors, [])

    def test_partial_missing(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", None, "couple", "cultural", "moderate", "premium", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertEqual(missing, ["month"])
        self.assertEqual(errors, [])

    def test_invalid_transport(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "cultural", "moderate", "premium", "early-starts", "spaceship"
        )
        self.assertFalse(ok)
        self.assertIn("invalid transport 'spaceship'", errors[0])

    def test_invalid_companion(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "wizard", "cultural", "moderate", "premium", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertIn("invalid companion 'wizard'", errors[0])

    def test_invalid_style(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "luxurious", "moderate", "premium", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertIn("invalid style 'luxurious'", errors[0])

    def test_invalid_pace(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "cultural", "frantic", "premium", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertIn("invalid pace 'frantic'", errors[0])

    def test_invalid_accommodation(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "cultural", "moderate", "platinum", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertIn("invalid accommodation 'platinum'", errors[0])

    def test_invalid_rhythm(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "Tokyo", 11, "couple", "cultural", "moderate", "premium", "noon-only", "public"
        )
        self.assertFalse(ok)
        self.assertIn("invalid rhythm 'noon-only'", errors[0])

    def test_blank_destination_is_missing(self):
        m = _import_module()
        ok, missing, errors = m.check_params(
            "   ", 11, "solo", "cultural", "moderate", "premium", "early-starts", "public"
        )
        self.assertFalse(ok)
        self.assertIn("destination", missing)


# --------------------------------------------------- 5-dim strategy builders --

class CompanionStrategyTests(unittest.TestCase):
    def test_solo(self):
        m = _import_module()
        s = m.build_companion_strategy("solo")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Solo traveler")
        self.assertEqual(s["daily_activity_cap_hours"], 8)
        self.assertIn("walkable", s["lodging"].lower())
        self.assertTrue(s["single_supplement"])

    def test_couple(self):
        m = _import_module()
        s = m.build_companion_strategy("couple")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Couple (romantic)")
        self.assertEqual(s["daily_activity_cap_hours"], 9)
        self.assertIn("emotional arc", s["pacing"])

    def test_family(self):
        m = _import_module()
        s = m.build_companion_strategy("family")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Family with children")
        self.assertEqual(s["daily_activity_cap_hours"], 5)
        self.assertIn("One Big Event", s["pacing"])

    def test_friends(self):
        m = _import_module()
        s = m.build_companion_strategy("friends")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Group of friends")
        self.assertEqual(s["daily_activity_cap_hours"], 10)
        self.assertIn("maximize", s["pacing"].lower())

    def test_elderly(self):
        m = _import_module()
        s = m.build_companion_strategy("elderly")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Elderly traveler (60+)")
        self.assertEqual(s["daily_activity_cap_hours"], 4)
        self.assertIn("step-free", s["transit"].lower())

    def test_unknown(self):
        m = _import_module()
        self.assertIsNone(m.build_companion_strategy("wizard"))
        self.assertIsNone(m.build_companion_strategy(None))
        self.assertIsNone(m.build_companion_strategy(""))


class StyleStrategyTests(unittest.TestCase):
    def test_cultural(self):
        m = _import_module()
        s = m.build_style_strategy("cultural")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Cultural immersion")
        self.assertIn("Temples", s["what_to_prioritize"])
        self.assertIn("Top 10", s["what_to_skip"])

    def test_classic(self):
        m = _import_module()
        s = m.build_style_strategy("classic")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Classic / must-see")
        self.assertIn("Mid-day", s["what_to_skip"])

    def test_nature(self):
        m = _import_module()
        s = m.build_style_strategy("nature")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Nature / outdoors")
        self.assertIn("Parks", s["what_to_prioritize"])

    def test_cityscape(self):
        m = _import_module()
        s = m.build_style_strategy("cityscape")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "City / urban")
        self.assertIn("Architecture", s["what_to_prioritize"])

    def test_historical(self):
        m = _import_module()
        s = m.build_style_strategy("historical")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Historical / heritage")
        self.assertIn("Ruins", s["what_to_prioritize"])

    def test_unknown(self):
        m = _import_module()
        self.assertIsNone(m.build_style_strategy("luxurious"))
        self.assertIsNone(m.build_style_strategy(None))


class PaceStrategyTests(unittest.TestCase):
    def test_ambitious(self):
        m = _import_module()
        s = m.build_pace_strategy("ambitious")
        self.assertIsNotNone(s)
        self.assertIn("8-10h", s["activity_hours_per_day"])
        self.assertIn("2-3", s["anchors_per_day"])

    def test_moderate(self):
        m = _import_module()
        s = m.build_pace_strategy("moderate")
        self.assertIsNotNone(s)
        self.assertIn("6-8h", s["activity_hours_per_day"])

    def test_relaxed(self):
        m = _import_module()
        s = m.build_pace_strategy("relaxed")
        self.assertIsNotNone(s)
        self.assertIn("4-6h", s["activity_hours_per_day"])
        self.assertIn("90 min", s["transit_willingness"])

    def test_unknown(self):
        m = _import_module()
        self.assertIsNone(m.build_pace_strategy("frantic"))


class AccommodationStrategyTests(unittest.TestCase):
    def test_comfort(self):
        m = _import_module()
        s = m.build_accommodation_strategy("comfort")
        self.assertIsNotNone(s)
        self.assertIn("3-4*", s["label"])
        self.assertIn("central location", s["amenities_priority"])

    def test_premium(self):
        m = _import_module()
        s = m.build_accommodation_strategy("premium")
        self.assertIsNotNone(s)
        self.assertIn("4-5*", s["label"])

    def test_luxury(self):
        m = _import_module()
        s = m.build_accommodation_strategy("luxury")
        self.assertIsNotNone(s)
        self.assertIn("5*", s["label"])
        self.assertIn("signature", s["hotel_class"].lower())

    def test_unknown(self):
        m = _import_module()
        self.assertIsNone(m.build_accommodation_strategy("platinum"))


class RhythmStrategyTests(unittest.TestCase):
    def test_early_starts(self):
        m = _import_module()
        s = m.build_rhythm_strategy("early-starts")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Early starts")
        self.assertIn("06:30", s["morning"])
        self.assertIn("21:00", s["evening"])

    def test_late_nights(self):
        m = _import_module()
        s = m.build_rhythm_strategy("late-nights")
        self.assertIsNotNone(s)
        self.assertEqual(s["label"], "Late nights")
        self.assertIn("09:30", s["morning"])
        self.assertIn("24:00", s["evening"])

    def test_unknown(self):
        m = _import_module()
        self.assertIsNone(m.build_rhythm_strategy("noon-only"))


# --------------------------------------------------- contradiction detection --

class ContradictionTests(unittest.TestCase):
    def test_family_ambitious(self):
        m = _import_module()
        warnings = m.detect_contradictions("family", "ambitious", "early-starts")
        self.assertTrue(any("Family + ambitious" in w for w in warnings))

    def test_family_late_nights(self):
        m = _import_module()
        warnings = m.detect_contradictions("family", "moderate", "late-nights")
        self.assertTrue(any("Family + late-nights" in w for w in warnings))

    def test_elderly_ambitious(self):
        m = _import_module()
        warnings = m.detect_contradictions("elderly", "ambitious", "early-starts")
        self.assertTrue(any("Elderly + ambitious" in w for w in warnings))

    def test_elderly_late_nights(self):
        m = _import_module()
        warnings = m.detect_contradictions("elderly", "relaxed", "late-nights")
        self.assertTrue(any("Elderly + late-nights" in w for w in warnings))

    def test_friends_early_starts(self):
        m = _import_module()
        warnings = m.detect_contradictions("friends", "moderate", "early-starts")
        self.assertTrue(any("Friends + early-starts" in w for w in warnings))

    def test_no_contradiction(self):
        m = _import_module()
        warnings = m.detect_contradictions("couple", "moderate", "early-starts")
        self.assertEqual(warnings, [])

    def test_solo_late_nights_flagged_for_safety(self):
        m = _import_module()
        warnings = m.detect_contradictions("solo", "moderate", "late-nights")
        self.assertTrue(any("Solo + late-nights" in w for w in warnings))


# --------------------------------------------------------------- warnings --

class WarningTests(unittest.TestCase):
    def test_winter_warning(self):
        m = _import_module()
        ws = m.build_warnings("Tokyo", 12, "public", "16:30", "15:30")
        self.assertTrue(any("Winter" in w for w in ws))
        self.assertTrue(any("16:30" in w for w in ws))

    def test_summer_warning(self):
        m = _import_module()
        ws = m.build_warnings("Bangkok", 7, "public", "18:50", "17:50")
        self.assertTrue(any("monsoon" in w.lower() or "peak" in w.lower() for w in ws))

    def test_shoulder_warning(self):
        m = _import_module()
        ws = m.build_warnings("Kyoto", 11, "public", "16:40", "15:40")
        self.assertTrue(any("Shoulder" in w or "peak" in w.lower() for w in ws))

    def test_selfdrive_warning(self):
        m = _import_module()
        ws = m.build_warnings("Hokkaido", 1, "self-drive", "16:30", "15:30")
        self.assertTrue(any("30% buffer" in w for w in ws))

    def test_no_selfdrive_no_buffer_warning(self):
        m = _import_module()
        ws = m.build_warnings("Tokyo", 5, "public", "18:45", "17:45")
        self.assertFalse(any("30% buffer" in w for w in ws))

    def test_unknown_destination_warning(self):
        m = _import_module()
        ws = m.build_warnings("Atlantis", 6, "public", "unknown", "unknown")
        self.assertTrue(any("not in the bundled" in w for w in ws))

    def test_contradiction_warning_passthrough(self):
        m = _import_module()
        ws = m.build_warnings("Tokyo", 11, "public", "16:25", "15:25",
                              companion="family", pace="ambitious", rhythm="early-starts")
        self.assertTrue(any("Family + ambitious" in w for w in ws))


# --------------------------------------------------------------- report ----

class BuildReportTests(unittest.TestCase):
    def test_complete_report(self):
        m = _import_module()
        args = _all_args(m)
        r = m.build_report(args)
        self.assertTrue(r["params_complete"])
        self.assertEqual(r["missing_params"], [])
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["sunset_local"], "16:40")
        self.assertEqual(r["cutoff_local"], "15:40")
        self.assertEqual(r["month_resolved"], 11)
        self.assertEqual(r["preferences"]["companion"], "couple")
        self.assertEqual(r["preferences"]["style"], "cultural")
        self.assertEqual(r["preferences"]["pace"], "moderate")
        self.assertEqual(r["preferences"]["accommodation"], "premium")
        self.assertEqual(r["preferences"]["rhythm"], "early-starts")
        self.assertEqual(r["preference_strategy"]["companion"]["label"], "Couple (romantic)")
        self.assertEqual(r["preference_strategy"]["style"]["label"], "Cultural immersion")
        self.assertEqual(r["preference_strategy"]["pace"]["label"], "Moderate / balanced")
        self.assertEqual(r["preference_strategy"]["accommodation"]["label"], "Premium (4-5* boutique / design)")
        self.assertEqual(r["preference_strategy"]["rhythm"]["label"], "Early starts")
        self.assertEqual(r["origin"], "Singapore (Changi)")
        self.assertIn("16:40", r["warnings"][0])

    def test_incomplete_report(self):
        m = _import_module()
        args = m.argparse.Namespace(
            destination=None, month=None, transport=None,
            companion=None, style=None, pace=None,
            accommodation=None, rhythm=None, persona=None, budget=None,
        )
        r = m.build_report(args)
        self.assertFalse(r["params_complete"])
        for key in ("destination", "month", "companion", "style", "pace", "accommodation", "rhythm"):
            self.assertIn(key, r["missing_params"])
        self.assertEqual(r["sunset_local"], "unknown")
        self.assertEqual(r["cutoff_local"], "unknown")
        self.assertIsNone(r["preference_strategy"]["companion"])

    def test_self_drive_warning_present(self):
        m = _import_module()
        args = _all_args(m, destination="Hokkaido", month="2026-12", transport="self-drive",
                          companion="couple", pace="moderate")
        r = m.build_report(args)
        self.assertTrue(r["params_complete"])
        warnings_text = " ".join(r["warnings"])
        self.assertIn("30% buffer", warnings_text)
        self.assertIn("Winter", warnings_text)
        self.assertIn("16:05", warnings_text)

    def test_unknown_destination_handled(self):
        m = _import_module()
        args = _all_args(m, destination="Atlantis", month="2026-06")
        r = m.build_report(args)
        self.assertTrue(r["params_complete"])
        self.assertEqual(r["sunset_local"], "unknown")
        warnings_text = " ".join(r["warnings"])
        self.assertIn("not in the bundled", warnings_text)

    def test_elderly_relaxed_no_contradiction(self):
        m = _import_module()
        args = _all_args(m, companion="elderly", pace="relaxed", rhythm="early-starts")
        r = m.build_report(args)
        warnings_text = " ".join(r["warnings"])
        self.assertNotIn("Elderly + ambitious", warnings_text)
        self.assertNotIn("Elderly + late-nights", warnings_text)

    def test_elderly_ambitious_flagged(self):
        m = _import_module()
        args = _all_args(m, companion="elderly", pace="ambitious", rhythm="early-starts")
        r = m.build_report(args)
        warnings_text = " ".join(r["warnings"])
        self.assertIn("Elderly + ambitious", warnings_text)


# ---------------------------------------------------- backwards compatibility --

class BackwardsCompatTests(unittest.TestCase):
    def test_persona_alias_resolves_to_companion(self):
        m = _import_module()
        self.assertEqual(m._resolve_companion("family"), "family")
        self.assertEqual(m._resolve_companion("solo"), "solo")
        self.assertEqual(m._resolve_companion("elderly"), "elderly")
        self.assertEqual(m._resolve_companion("friends"), "friends")

    def test_budget_alias_resolves_to_accommodation(self):
        m = _import_module()
        self.assertEqual(m._resolve_accommodation("backpacker"), "comfort")
        self.assertEqual(m._resolve_accommodation("mid"), "premium")
        self.assertEqual(m._resolve_accommodation("luxury"), "luxury")
        # New canonical names also work
        self.assertEqual(m._resolve_accommodation("comfort"), "comfort")
        self.assertEqual(m._resolve_accommodation("premium"), "premium")

    def test_invalid_alias_returns_none(self):
        m = _import_module()
        self.assertIsNone(m._resolve_companion("wizard"))
        self.assertIsNone(m._resolve_accommodation("platinum"))

    def test_report_uses_deprecated_persona(self):
        m = _import_module()
        args = m.argparse.Namespace(
            destination="Kyoto", month="2026-11", transport="public",
            companion=None, style="cultural", pace="moderate",
            accommodation="premium", rhythm="early-starts",
            persona="family", budget=None,
        )
        r = m.build_report(args)
        self.assertTrue(r["params_complete"])
        self.assertEqual(r["preferences"]["companion"], "family")

    def test_report_uses_deprecated_budget(self):
        m = _import_module()
        args = m.argparse.Namespace(
            destination="Kyoto", month="2026-11", transport="public",
            companion="couple", style="cultural", pace="moderate",
            accommodation=None, rhythm="early-starts",
            persona=None, budget="backpacker",
        )
        r = m.build_report(args)
        self.assertTrue(r["params_complete"])
        self.assertEqual(r["preferences"]["accommodation"], "comfort")


# --------------------------------------------------------------- CLI -----

class CLITests(unittest.TestCase):
    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode, result.stdout, result.stderr

    def test_cli_complete(self):
        code, out, err = self._run(
            "--destination", "Kyoto", "--month", "2026-11",
            "--transport", "public",
            "--companion", "couple", "--style", "cultural", "--pace", "moderate",
            "--accommodation", "premium", "--rhythm", "early-starts",
        )
        self.assertEqual(code, 0, msg=err)
        report = json.loads(out)
        self.assertTrue(report["params_complete"])
        self.assertEqual(report["sunset_local"], "16:40")
        self.assertEqual(report["preferences"]["companion"], "couple")
        self.assertEqual(report["preferences"]["style"], "cultural")

    def test_cli_missing_returns_2(self):
        code, out, err = self._run("--destination", "Kyoto")
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertFalse(report["params_complete"])
        for key in ("month", "transport", "companion", "style", "pace", "accommodation", "rhythm"):
            self.assertIn(key, report["missing_params"])

    def test_cli_invalid_companion(self):
        code, out, err = self._run(
            "--destination", "Tokyo", "--month", "2026-11", "--transport", "public",
            "--companion", "wizard",
            "--style", "cultural", "--pace", "moderate",
            "--accommodation", "premium", "--rhythm", "early-starts",
        )
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertIn("companion", report["missing_params"])
        self.assertFalse(report["params_complete"])

    def test_cli_alias(self):
        code, out, err = self._run(
            "--destination", "東京", "--month", "2026-05", "--transport", "mixed",
            "--companion", "family", "--style", "classic", "--pace", "ambitious",
            "--accommodation", "premium", "--rhythm", "early-starts",
        )
        self.assertEqual(code, 0, msg=err)
        report = json.loads(out)
        self.assertEqual(report["sunset_local"], "18:45")
        self.assertEqual(report["preference_strategy"]["companion"]["label"], "Family with children")

    def test_cli_friends_elderly(self):
        code, out, err = self._run(
            "--destination", "Taipei", "--month", "2026-09", "--transport", "public",
            "--companion", "friends", "--style", "cityscape", "--pace", "ambitious",
            "--accommodation", "comfort", "--rhythm", "late-nights",
        )
        self.assertEqual(code, 0, msg=err)
        report = json.loads(out)
        self.assertEqual(report["preference_strategy"]["companion"]["label"], "Group of friends")
        # Friends + early-starts is the contradiction; late-nights is safe.
        warnings_text = " ".join(report["warnings"])
        self.assertNotIn("Friends + early-starts", warnings_text)

    def test_cli_backwards_compat_persona(self):
        code, out, err = self._run(
            "--destination", "Kyoto", "--month", "2026-11", "--transport", "public",
            "--persona", "couple",  # deprecated alias
            "--style", "cultural", "--pace", "moderate",
            "--accommodation", "premium", "--rhythm", "early-starts",
        )
        self.assertEqual(code, 0, msg=err)
        report = json.loads(out)
        self.assertEqual(report["preferences"]["companion"], "couple")

    def test_cli_backwards_compat_budget(self):
        code, out, err = self._run(
            "--destination", "Kyoto", "--month", "2026-11", "--transport", "public",
            "--companion", "couple", "--style", "cultural", "--pace", "moderate",
            "--budget", "backpacker",  # deprecated alias
            "--rhythm", "early-starts",
        )
        self.assertEqual(code, 0, msg=err)
        report = json.loads(out)
        self.assertEqual(report["preferences"]["accommodation"], "comfort")

    def test_cli_no_args_returns_2(self):
        code, out, err = self._run()
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertFalse(report["params_complete"])


# --------------------------------------------------------------- determinism --

class DeterminismTests(unittest.TestCase):
    def test_same_inputs_same_output(self):
        m = _import_module()
        r1 = m.build_report(_all_args(m))
        r2 = m.build_report(_all_args(m))
        self.assertEqual(r1, r2)

    def test_does_not_use_time_or_random(self):
        src = SCRIPT.read_text()
        self.assertNotIn("time.time()", src)
        self.assertNotIn("random.", src)
        self.assertNotIn("os.urandom", src)


if __name__ == "__main__":
    unittest.main()
