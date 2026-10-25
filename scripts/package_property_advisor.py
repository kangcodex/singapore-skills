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
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
NAME: Final = "property-advisor-skill"


class PackageError(Exception):
    """A source or output path cannot be packaged safely."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class Options(argparse.Namespace):
    output_dir: Path


def export_skill(output: Path) -> tuple[Path, Path]:
    """Copy tracked runtime resources and archive them under the skill name."""
    skill = ROOT / "skills" / NAME
    patterns = ("SKILL.md", "LICENSE", ".env.example", "assets/case-template.json",
                "scripts/*.py", "references/*.md", "references/*.json")
    listing = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "-z", "--",
         *(f":(glob)skills/{NAME}/{pattern}" for pattern in patterns)],
        cwd=ROOT, capture_output=True, check=True,
    )
    sources = [ROOT / os.fsdecode(path) for path in listing.stdout.split(b"\0") if path]
    destination = output / NAME
    archive_path = output / f"{NAME}.skill"
    if destination.exists() or archive_path.exists():
        raise PackageError(output, "Output already exists; choose a fresh --output-dir")
    for source in sources:
        current = ROOT
        for part in source.relative_to(ROOT).parts:
            current /= part
            if current.is_symlink():
                raise PackageError(current, "Symlinked runtime resources are not exported")
    output.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            relative = source.relative_to(skill)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            archive.write(target, (Path(NAME) / relative).as_posix())
    return destination, archive_path


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
