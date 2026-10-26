#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# python3 scripts/package_property_advisor.py [--output-dir PATH]
# Or: uv run scripts/package_property_advisor.py [--output-dir PATH]
# Requires a Git checkout; exports tracked runtime files from the working tree.
# ──────────────────
"""Export the standalone property skill without development or local casework."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

if __package__:
    from .package_skills import PackageError, export_skill as _export_skill
else:
    from package_skills import PackageError, export_skill as _export_skill

ROOT: Final = Path(__file__).resolve().parent.parent
NAME: Final = "property-advisor-skill"


class Options(argparse.Namespace):
    output_dir: Path


def export_skill(output: Path) -> tuple[Path, Path]:
    """Copy tracked runtime resources and archive them under the skill name."""
    return _export_skill(NAME, output)


def main() -> int:
    """Build a clean folder and ZIP-format .skill archive from this checkout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    options = parser.parse_args(namespace=Options())
    try:
        directory, archive = export_skill(options.output_dir)
    except (OSError, subprocess.CalledProcessError, PackageError) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1
    print(f"Runtime folder: {directory}")
    print(f"Import archive: {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
