"""Public property-package smoke check requiring no local developer workspace."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestPropertyDistribution(unittest.TestCase):
    def test_exported_case_template_runs_without_development_inputs(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "package_property_advisor.py"),
                 "--output-dir", str(root / "export")],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(export.returncode, 0, export.stdout + export.stderr)
            with zipfile.ZipFile(root / "export" / "property-advisor-skill.skill") as archive:
                self.assertFalse(any("development" in Path(name).parts for name in archive.namelist()))
                archive.extractall(root / "installed")
            skill = root / "installed" / "property-advisor-skill"
            # When
            execution = subprocess.run(
                [sys.executable, str(skill / "scripts" / "advisor_cli.py"), "--case",
                 str(skill / "assets" / "case-template.json"), "--format", "json"],
                cwd=root, env={"HOME": str(root), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, check=False, timeout=30,
            )
            # Then
            self.assertEqual(execution.returncode, 0, execution.stdout + execution.stderr)
            self.assertEqual(json.loads(execution.stdout)["audit"]["errors"], [])
