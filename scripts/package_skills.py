#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# python3 scripts/package_skills.py [--skill NAME] [--output-dir PATH]
# Or: uv run scripts/package_skills.py [--skill NAME] [--output-dir PATH]
# Requires Git; exports tracked runtime files from the working tree.
# ──────────────────
"""Export runtime-only skill folders and ZIP-format .skill archives."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Final, Sequence

ROOT: Final = Path(__file__).resolve().parent.parent


class PackageError(Exception):
    """A source or output path cannot be packaged safely."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class Options(argparse.Namespace):
    skill: list[str] | None
    output_dir: Path


def tracked_files() -> tuple[Path, ...]:
    """List source-controlled skill resources without reading local workings."""
    listing = subprocess.run(["git", "ls-files", "-z", "--", "LICENSE", "skills"],
                             cwd=ROOT, capture_output=True, check=True)
    return tuple(Path(os.fsdecode(path)) for path in listing.stdout.split(b"\0") if path)


def skill_names(paths: Sequence[Path]) -> list[str]:
    return sorted(path.parent.name for path in paths if len(path.parts) == 3 and path.name == "SKILL.md")


def is_runtime(relative: Path) -> bool:
    """Keep package resources, excluding developer directories and real env files."""
    if relative.as_posix() in {"SKILL.md", "LICENSE", ".env.example"}:
        return True
    return (relative.parts[0] in {"scripts", "references", "assets"}
            and not {"tests", "evals", "__pycache__"}.intersection(relative.parts)
            and relative.name != ".env")


def export_skill(name: str, output: Path) -> tuple[Path, Path]:
    """Export one tracked skill; keep sibling dependencies as separate packages."""
    paths = tracked_files()
    if name not in skill_names(paths):
        raise PackageError(ROOT / "skills", f"Unknown tracked skill: {name}")
    prefix = Path("skills") / name
    sources = [(path.relative_to(prefix), ROOT / path) for path in paths
               if path.is_relative_to(prefix) and is_runtime(path.relative_to(prefix))]
    if not any(relative == Path("LICENSE") for relative, _ in sources):
        sources.append((Path("LICENSE"), ROOT / "LICENSE"))
    destination = output / name
    archive_path = output / f"{name}.skill"
    if destination.exists() or archive_path.exists():
        raise PackageError(output, "Output already exists; choose a fresh --output-dir")
    for _, source in sources:
        current = ROOT
        for part in source.relative_to(ROOT).parts:
            current /= part
            if current.is_symlink():
                raise PackageError(current, "Symlinked runtime resources are not exported")
    output.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, source in sources:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            archive.write(target, (Path(name) / relative).as_posix())
    return destination, archive_path


def main(argv: Sequence[str] | None = None) -> int:
    """Export selected skills, or every tracked skill when none is selected."""
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        available = skill_names(tracked_files())
        parser.add_argument("--skill", choices=available, action="append")
        parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
        options = parser.parse_args(argv, namespace=Options())
        selected = list(dict.fromkeys(options.skill or available))
        # Hawker invokes the CDC sibling script; export its companion for co-installation.
        if "hawker-discover-skill" in selected and "cdc-voucher-locator-skill" not in selected:
            selected.append("cdc-voucher-locator-skill")
        for name in selected:
            directory, archive = export_skill(name, options.output_dir)
            print(f"Runtime folder: {directory}")
            print(f"Import archive: {archive}")
    except (OSError, subprocess.CalledProcessError, PackageError) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
