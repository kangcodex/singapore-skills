"""Check install-time resource links and the machine-consumed eval contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "property-advisor-skill"


class TestSkillAssets(unittest.TestCase):
    def test_local_markdown_resource_links_resolve(self) -> None:
        # Given
        files = [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]
        # When
        missing: list[str] = []
        for path in files:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                local = target.split("#", 1)[0]
                if not (path.parent / local).is_file():
                    missing.append(f"{path.name}: {local}")
        # Then
        self.assertEqual(missing, [])

    def test_eval_ids_expectations_and_fixed_inputs_are_complete(self) -> None:
        # Given
        eval_dir = Path(__file__).resolve().parents[1] / "evals"
        # When
        for filename, ids in (("evals.json", [1, 2, 3, 4, 5]), ("question-led-evals.json", [101, 102, 103, 104, 105])):
            with self.subTest(filename=filename):
                document = json.loads((eval_dir / filename).read_text(encoding="utf-8"))
                # Then
                self.assertEqual(document["skill_name"], "property-advisor-skill")
                self.assertEqual([item["id"] for item in document["evals"]], ids)
                for item in document["evals"]:
                    self.assertTrue(item["prompt"] and item["expected_output"] and item["expectations"])
                    for path in item["files"]:
                        self.assertTrue((eval_dir / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
