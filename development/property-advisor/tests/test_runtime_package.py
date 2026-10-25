"""Verify the archive users import, without repository-side runtime dependencies."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[3]
SKILL: Final = ROOT / "skills" / "property-advisor-skill"
FIXTURES: Final = Path(__file__).resolve().parents[1] / "fixtures"
PACKAGER: Final = ROOT / "scripts" / "package_property_advisor.py"
NAME: Final = "property-advisor-skill"


def build(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PACKAGER), "--output-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
    )


class TestRuntimePackage(unittest.TestCase):
    def test_export_contains_runtime_and_license_but_no_development_or_untracked_files(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory, tempfile.NamedTemporaryFile(
            mode="w", prefix="export-probe-", suffix=".md", dir=SKILL / "references",
        ) as probe:
            probe.write("Untracked local material must not be distributed.")
            probe.flush()
            output = Path(directory)
            # When
            result = build(output)
            # Then
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(output / f"{NAME}.skill") as archive:
                paths = {Path(name).relative_to(NAME) for name in archive.namelist()}
                self.assertTrue({Path("SKILL.md"), Path("LICENSE"), Path(".env.example"), Path("assets/case-template.json")} <= paths)
                self.assertEqual(archive.read(f"{NAME}/LICENSE"), (ROOT / "LICENSE").read_bytes())
            self.assertFalse(any({"tests", "evals", "examples", "workings", "cases", "__pycache__"} & set(path.parts) for path in paths))
            self.assertNotIn(Path("references") / Path(probe.name).name, paths)
            self.assertEqual({path for path in paths if path.parts[0] == "assets"}, {Path("assets/case-template.json")})

    def test_extracted_archive_runs_every_assessment_cases_and_offline_advice(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = build(root / "export")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(root / "export" / f"{NAME}.skill") as archive:
                archive.extractall(root / "installed")
            installed = root / "installed" / NAME
            inputs = sorted((FIXTURES / "assessments").glob("*.json"))
            self.assertEqual(len(inputs), 14)
            commands: list[tuple[str, ...]] = [
                ("advisor_cli.py", "--assess", path.stem, "--input", str(path), "--format", "json")
                for path in inputs
            ]
            commands.extend([
                ("advisor_cli.py", "--case", str(installed / "assets" / "case-template.json"), "--format", "json"),
                ("advisor_cli.py", "--case", str(FIXTURES / "cases" / "question-led-case.json"), "--format", "json"),
                ("property_advisor.py", "--mode", "agent", "--task", "advise", "--scenario", str(FIXTURES / "legacy-scenarios" / "dink-couple.json")),
            ])
            for script, *arguments in commands:
                with self.subTest(arguments=arguments):
                    # When: no PYTHONPATH, user credentials or original skill cwd.
                    execution = subprocess.run(
                        [sys.executable, str(installed / "scripts" / script), *arguments],
                        cwd=root, env={"HOME": str(root), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                        capture_output=True, text=True, check=False, timeout=30,
                    )
                    # Then
                    self.assertEqual(execution.returncode, 0, execution.stdout + execution.stderr)
                    self.assertNotIn("error", json.loads(execution.stdout))

    def test_existing_export_is_preserved(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            existing = output / NAME
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_text("Existing export", encoding="utf-8")
            # When
            result = build(output)
            # Then
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "Existing export")


if __name__ == "__main__":
    unittest.main()
