"""Check the actual distributable folders, independent of the repository cwd."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
PACKAGER: Final = ROOT / "scripts" / "package_skills.py"
ENTRY_POINTS: Final = {
    "agent-match-skill": "agent_match.py",
    "air-quality-advisor-skill": "air_quality.py",
    "cdc-voucher-locator-skill": "cdc_voucher_locator.py",
    "dengue-risk-advisor-skill": "dengue_risk_advisor.py",
    "hawker-discover-skill": "hawker_discover.py",
    "mrt-rerouter-skill": "mrt_rerouter.py",
    "overseas-trip-planner-skill": "trip_concierge.py",
    "property-advisor-skill": "advisor_cli.py",
    "rental-yield-calculator-skill": "rental_yield.py",
    "sg-fruit-price-tracker-skill": "fruit_price_tracker.py",
    "sg-home-chef-skill": "sg_home_chef.py",
    "smart-commuter-skill": "smart_commuter.py",
    "weekend-planner-skill": "weekend_planner.py",
}


class TestSkillDistribution(unittest.TestCase):
    def test_property_exporter_retains_its_module_api(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            # When
            result = subprocess.run(
                [sys.executable, "-c", "import sys; from pathlib import Path; "
                 "from scripts.package_property_advisor import export_skill; "
                 "export_skill(Path(sys.argv[1]))", directory],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
            )
            # Then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(directory) / "property-advisor-skill" / "SKILL.md").is_file())
            self.assertTrue((Path(directory) / "property-advisor-skill.skill").is_file())

    def test_retained_behavioral_packets_have_real_prompts_and_inputs(self) -> None:
        # Given
        for name in ("overseas-trip-planner", "sg-fruit-price-tracker", "sg-home-chef"):
            directory = ROOT / "development" / name / "evals"
            # When
            packet = json.loads((directory / "evals.json").read_text(encoding="utf-8"))
            # Then
            with self.subTest(skill=name):
                self.assertEqual(packet["skill_name"], name + "-skill")
                self.assertTrue(packet["evals"])
                ids = [case["id"] for case in packet["evals"]]
                self.assertEqual(len(ids), len(set(ids)))
                for case in packet["evals"]:
                    self.assertTrue(case["prompt"] and case["expected_output"] and case["expectations"])
                    for path in case["files"]:
                        self.assertTrue((directory / path).is_file(), path)

    def test_all_archives_contain_runtime_only_and_import_in_isolation(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # When
            export = subprocess.run([sys.executable, str(PACKAGER), "--output-dir", str(root / "exports")],
                                    cwd=ROOT, capture_output=True, text=True, check=False, timeout=30)
            # Then
            self.assertEqual(export.returncode, 0, export.stdout + export.stderr)
            self.assertEqual({path.stem for path in (root / "exports").glob("*.skill")}, set(ENTRY_POINTS))
            for name, entry in ENTRY_POINTS.items():
                with self.subTest(skill=name), zipfile.ZipFile(root / "exports" / f"{name}.skill") as archive:
                    paths = {Path(path).relative_to(name) for path in archive.namelist()}
                    self.assertTrue({Path("SKILL.md"), Path("LICENSE"), Path("scripts") / entry} <= paths)
                    self.assertFalse(any({"tests", "evals", "workings", "__pycache__"} & set(path.parts) for path in paths))
                    self.assertEqual(archive.read(f"{name}/LICENSE"), (ROOT / "LICENSE").read_bytes())
                    archive.extractall(root / "installed")
                    script = root / "installed" / name / "scripts" / entry
                    imported = subprocess.run(
                        [sys.executable, "-S", "-c",
                         "import runpy,sys; from pathlib import Path; "
                         "sys.path.insert(0,str(Path(sys.argv[1]).parent)); "
                         "runpy.run_path(sys.argv[1],run_name='_shipping_import_')", str(script)],
                        cwd=root, env={"HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
                        capture_output=True, text=True, check=False, timeout=15,
                    )
                    self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)

    def test_hawker_selection_exports_its_cdc_companion(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # When
            result = subprocess.run([sys.executable, str(PACKAGER), "--skill", "hawker-discover-skill",
                                     "--output-dir", str(root)], cwd=ROOT, capture_output=True,
                                    text=True, check=False, timeout=30)
            # Then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({path.stem for path in root.glob("*.skill")}, {"hawker-discover-skill", "cdc-voucher-locator-skill"})

    def test_unknown_skill_is_rejected_without_creating_an_export(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unused"
            # When
            result = subprocess.run([sys.executable, str(PACKAGER), "--skill", "../outside",
                                     "--output-dir", str(output)], cwd=ROOT, capture_output=True,
                                    text=True, check=False, timeout=30)
            # Then
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid choice", result.stderr)
            self.assertFalse(output.exists())
