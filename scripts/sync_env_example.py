#!/usr/bin/env python3
"""
scripts/sync_env_example.py — keep per-skill .env.example copies in sync.

The canonical file lives at the repo root: ./.env.example
Per-skill copies live at:           skills/<skill>/.env.example

Each per-skill copy is byte-identical to the canonical — there is no header
to append because .env.example is read by other tools (e.g. `direnv`,
`dotenv`) and any comment we prepend would be confusing to a user who runs
`cp .env.example .env` and edits.

Usage:
    python3 scripts/sync_env_example.py             # copy to all skills
    python3 scripts/sync_env_example.py --check     # exit 1 if any copy is stale
    python3 scripts/sync_env_example.py --dry-run   # show what would change

Add a new skill to SKILL_FOLDERS when you create a new skills/<skill>/ folder.
This list MUST match scripts/sync_singapore_api.py (consumed by CI).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / ".env.example"
SKILLS_DIR = REPO_ROOT / "skills"

SKILL_FOLDERS = [
    "cdc-voucher-locator-skill",
    "smart-commuter-skill",
    "resale-property-advisor-skill",
    "weekend-planner-skill",
    "mrt-rerouter-skill",
    "dengue-risk-advisor-skill",
    "hawker-discover-skill",
]


def per_skill_path(skill_folder):
    return SKILLS_DIR / skill_folder / ".env.example"


def sync(skill_folder, body, *, dry_run):
    target = per_skill_path(skill_folder)
    if target.exists() and target.read_text(encoding="utf-8") == body:
        return False
    if not dry_run:
        target.write_text(body, encoding="utf-8")
    return True


def main(argv):
    args = set(argv[1:])
    check_only = "--check" in args
    dry_run = "--dry-run" in args

    if not CANONICAL.exists():
        print("ERROR: canonical .env.example not found at %s" % CANONICAL, file=sys.stderr)
        return 2

    body = CANONICAL.read_text(encoding="utf-8")
    changed, missing = [], []

    for skill in SKILL_FOLDERS:
        if not (SKILLS_DIR / skill).is_dir():
            missing.append(skill)
            continue
        if sync(skill, body, dry_run=dry_run or check_only):
            changed.append(skill)

    if missing:
        print("NOTE: %d skill folder(s) not yet created (will be skipped):" % len(missing))
        for s in missing:
            print("  - skills/%s" % s)

    if check_only:
        if changed:
            print("STALE: %d per-skill .env.example out of sync:" % len(changed))
            for s in changed:
                print("  - skills/%s/.env.example" % s)
            print("Run: python3 scripts/sync_env_example.py")
            return 1
        ok_count = len(SKILL_FOLDERS) - len(missing)
        print("OK: all %d per-skill .env.example match canonical." % ok_count)
        return 0

    if dry_run:
        if changed:
            print("Would update %d per-skill .env.example:" % len(changed))
            for s in changed:
                print("  - skills/%s/.env.example" % s)
        else:
            print("All per-skill .env.example already match.")
        return 0

    if changed:
        print("Synced %d per-skill .env.example: %s" % (len(changed), ", ".join(changed)))
    else:
        print("All per-skill .env.example already match.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
