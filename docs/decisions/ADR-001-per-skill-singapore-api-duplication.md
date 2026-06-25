# ADR-001: Per-skill `singapore_api.py` duplication

## Status
Accepted

## Date
2026-06-20 (originally) — confirmed 2026-06-22

## Context

Each skill in this repo is published as a self-contained unit via the
[`vercel-labs/skills`](https://github.com/vercel-labs/skills) install
pattern. Users install with `npx skills add kangcodex/singapore-skills --skill X`
and the installed skill must work **without** depending on the parent repo
or any other sibling skill.

The canonical `singapore_api.py` (at the repo root) provides shared
fetchers for NEA / URA / CEA / SINGSTAT / HDB / OneMap / etc. — currently
~1,170 lines. Every skill imports from it.

## Decision

Each skill ships its **own copy** of `singapore_api.py` in
`scripts/singapore_api.py`. The copies are kept in sync with the canonical
via `scripts/sync_singapore_api.py` (which prepends a `SYNCED FROM <repo>
<hash> <date>` header).

Total disk cost: 10 per-skill copies × ~44 KB = **~445 KB of duplicated
code** (≈0.1% of a typical agent context budget).

## Alternatives Considered

### Single shared import path
- Pros: Zero duplication, single source of truth.
- Cons: Requires every installed skill to also install the parent repo;
  breaks `npx skills add --skill X` (per-skill install is the whole point);
  couples skill releases.
- Rejected: violates the install contract.

### Install script that copies the file
- Pros: Single source.
- Cons: Adds a post-install step (slower, more fragile, harder to verify
  in CI); the skill no longer works on a fresh clone without running the
  script first.
- Rejected: violates the "drop in and run" property.

### Compile / freeze the shared client as a vendored wheel
- Pros: Smaller disk footprint (`.whl` is much smaller than source).
- Cons: Hides bugs in the binary; harder for users to read or patch;
  adds a build step.
- Rejected: stdlib-only is a hard project constraint; no build step.

## Consequences

- **Pos:** Skills are self-contained; `npx skills add --skill X` works
  for any single skill; the codebase has no shared state at install time.
- **Pos:** The `SYNCED FROM` header lets humans see drift if the sync
  script hasn't been run in a while.
- **Pos:** The sync script (with `diff`-based verification in
  `tests/test_singapore_api.py::TestPerSkillCopiesAreInSync`) catches
  forgotten syncs in CI.
- **Neg:** ~445 KB of disk overhead. Acceptable.
- **Neg:** A change to the canonical must be followed by a sync run.
  This is enforced by the `TestPerSkillCopiesAreInSync` test, which fails
  in CI if any copy is out of date.
- **Neg:** When two skills need the same helper (e.g. `sparkline`),
  the temptation is to duplicate. ADR-005 documents how we avoided that
  with the v2 consolidation (helpers live in the canonical, copied by
  the sync).
