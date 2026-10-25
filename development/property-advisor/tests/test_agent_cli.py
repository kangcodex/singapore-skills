"""Agent-mode CLI, uniform output shape and plain-language summary (no network)."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_advisor as aa  # noqa: E402

UNIFORM_KEYS = {"mode", "town", "since", "asking", "verdict", "premium_pct", "trend",
                "location", "ura_context", "cea_verification"}
BUYERS = [{"age": a, "residency": "sc", "existing_properties": 0, "monthly_income": "7000",
           "cpf_oa": "150000", "cpf_oa_monthly": "1300"} for a in (33, 31)]
OPT_HDB = {"name": "4-room HDB", "category": "resale_hdb", "price": "650000",
           "loan": {"type": "hdb", "tenure_years": 25},
           "lifestyle_addons": [{"id": "virgin_active_long_termer", "count": 2}]}
OPT_CONDO = {"name": "OCR resale condo", "category": "resale_condo", "price": "1500000",
             "loan": {"type": "bank", "tenure_years": 30}}


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = aa.main(argv)
    return code, out.getvalue()


def scenario_file(**kw):
    s = {"start_date": "2026-11-01", "buyers": BUYERS,
         "household": {"cash": "400000", "other_monthly_debts": "0"}}
    s.update(kw)
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(s, f)
    f.close()
    return f.name


class TestAgentCli(unittest.TestCase):
    def test_profile_task_uniform_shape_and_summary(self):
        code, text = run(["--task", "profile", "--profile", "dink"])
        res = json.loads(text)
        self.assertEqual(code, 0)
        self.assertTrue(UNIFORM_KEYS <= set(res))
        self.assertEqual(res["mode"], "agent")
        self.assertEqual(res["task"], "profile")
        self.assertEqual(res["agent"]["profile"]["shortlist"][0]["category"], "resale_condo")
        self.assertIn("shortlist", res["summary"].lower())

    def test_disclaimer_present_everywhere(self):
        for argv in (["--task", "profile", "--profile", "first_home_couple"],
                     ["--task", "plan", "--scenario", scenario_file(option=OPT_HDB)],
                     ["--task", "compare", "--scenario", scenario_file(options=[OPT_CONDO, OPT_HDB])]):
            res = json.loads(run(argv)[1])
            self.assertIn("not financial or legal advice", res["disclaimer"].lower())
            for who in ("HDB", "bank", "lawyer"):
                self.assertIn(who, res["disclaimer"])
            self.assertIn("not financial or legal advice", res["summary"].lower())

    def test_plan_task_reports_cash_per_stage(self):
        res = json.loads(run(["--task", "plan", "--scenario", scenario_file(option=OPT_HDB)])[1])
        self.assertEqual(res["asking"], "650000.00")
        stages = {e["stage"] for e in res["agent"]["plan"]["timeline"]}
        self.assertTrue({"option_fee", "exercise", "completion_down_payment", "stamp_duty"} <= stages)
        for line in ("Option fee", "stamp duty", "Monthly"):
            self.assertIn(line.lower(), res["summary"].lower())

    def test_plan_reports_affordability_ceiling(self):
        res = json.loads(run(["--task", "plan", "--scenario", scenario_file(option=OPT_HDB)])[1])
        ceiling = res["agent"]["plan"]["affordability_ceiling"]
        self.assertGreater(float(ceiling["max_loan"]), 0)
        self.assertGreater(float(ceiling["max_price"]), float(ceiling["max_loan"]))
        self.assertIn("Affordability ceiling", res["summary"])

    def test_plan_zero_income_renders_instead_of_crashing(self):
        buyers = [{**b, "monthly_income": "0"} for b in BUYERS]
        code, text = run(["--task", "plan", "--scenario",
                          scenario_file(option=OPT_HDB, buyers=buyers)])
        res = json.loads(text)
        self.assertEqual(code, 0)
        self.assertNotIn("error", res)
        self.assertIn("ratio n/a", res["summary"])
        for c in res["agent"]["plan"]["checks"]:
            self.assertIsNone(c["ratio"])
            self.assertFalse(c["pass"])

    def test_compare_task_reports_break_even(self):
        res = json.loads(run(["--task", "compare", "--scenario", scenario_file(options=[OPT_CONDO, OPT_HDB])])[1])
        self.assertTrue(res["agent"]["comparison"]["break_even"])
        self.assertIn("break-even", res["summary"].lower())
        self.assertIn("Virgin Active", res["summary"])

    def test_advise_task_combines_profile_and_comparison(self):
        f = scenario_file(profile="dink", options=[OPT_CONDO, OPT_HDB])
        res = json.loads(run(["--task", "advise", "--scenario", f])[1])
        self.assertIn("profile", res["agent"])
        self.assertIn("comparison", res["agent"])
        self.assertIn("Key questions", res["summary"])
        self.assertIn("Red flags", res["summary"])

    def test_summary_only_prints_plain_text(self):
        code, text = run(["--task", "profile", "--profile", "family_of_five", "--variant", "multigen", "--summary-only"])
        self.assertFalse(text.lstrip().startswith("{"))
        self.assertIn("multi-generation", text.lower())

    def test_errors_follow_repo_convention(self):
        code, text = run(["--task", "profile", "--profile", "nope"])
        self.assertEqual(code, 0)
        self.assertIn("error", json.loads(text))
        code, text = run(["--task", "plan"])
        self.assertIn("error", json.loads(text))

    def test_unverified_inputs_are_surfaced_in_summary(self):
        res = json.loads(run(["--task", "plan", "--scenario", scenario_file(option=OPT_HDB)])[1])
        self.assertIn("unverified", res["summary"].lower())

    def test_no_network(self):
        with patch("socket.socket", side_effect=AssertionError("network used")):
            run(["--task", "compare", "--scenario", scenario_file(options=[OPT_CONDO, OPT_HDB])])


class TestScenarioFixtures(unittest.TestCase):
    def test_each_profile_example_runs_end_to_end(self):
        for name in ("dink-couple", "first-home-couple", "family-of-five"):
            path = FIXTURES / "legacy-scenarios" / f"{name}.json"
            res = json.loads(run(["--task", "advise", "--scenario", str(path)])[1])
            self.assertNotIn("error", res, name)
            self.assertEqual(res["agent"]["profile"]["profile_id"], json.loads(path.read_text())["profile"])
            self.assertGreaterEqual(len(res["agent"]["comparison"]["options"]), 2)


class TestPropertyAdvisorDelegation(unittest.TestCase):
    def _load(self):
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        spec = importlib.util.spec_from_file_location("property_advisor_for_agent", SCRIPTS_DIR / "property_advisor.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_mode_agent_delegates_without_network_and_other_modes_unchanged(self):
        pa = self._load()
        out = io.StringIO()
        with patch("socket.socket", side_effect=AssertionError("network used")), contextlib.redirect_stdout(out):
            pa.main(["--mode", "agent", "--task", "profile", "--profile", "dink"])
        self.assertEqual(json.loads(out.getvalue())["mode"], "agent")
        with self.assertRaises(SystemExit):  # existing argparse still demands its required flags
            with contextlib.redirect_stderr(io.StringIO()):
                pa.main(["--mode", "hdb"])


if __name__ == "__main__":
    unittest.main()
