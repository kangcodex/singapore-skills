# ADR-003: Local markdown issue tracker (`.issues/`) instead of GitHub Issues

## Status
Accepted

## Date
2026-06-15 (initially) — confirmed 2026-06-22

## Context

The repo publishes 10+ self-contained skills. Each skill ships in its
own subdirectory with SKILL.md, references/, scripts/, tests/. The
work to build these skills is tracked as **vertical slices** (tracer
bullets) — a slice is end-to-end through schema / API / script / tests
/ docs and is demoable on its own.

The vertical-slice work needs an issue tracker that:

1. Lives in the repo (so a clone includes the work history).
2. Supports dependency links between slices (`S09a blocked by S08`).
3. Supports a matching PRD per slice (each issue has a problem
   statement, solution, user stories, test plan).
4. Works without an external account / CI / API key.

GitHub Issues satisfies (1) (in-repo), (2) (via cross-references), and
(3) (via issue templates), but not (4) (requires GitHub auth + a
remote). Also, every issue-PRD pair would have to live in two
different UIs (Issues tab + repo files), and the agent working the
slices would have to alternate between bash and web UIs.

## Decision

Use a **local markdown issue tracker** in `.issues/`:

```
.issues/
├── INDEX.md          # table of all issues + dep graph + log
├── README.md         # convention docs
├── S00-shared-api-client.md
├── S01a-smart-commuter-core.md
├── ...
└── prds/
    ├── PRD-S00-shared-api-client.md
    ├── PRD-S01a-smart-commuter-core.md
    └── ...
```

Each issue is a markdown file with frontmatter
`{id, title, status, labels, blocked_by}` and body sections
{Parent, What to build, Acceptance criteria, Blocked by}. Each PRD
adds `prd: true` + sections {Problem Statement, Solution, User Stories,
Implementation Decisions, Testing Decisions, Out of Scope, Further
Notes}.

Completed work moves to `docs/archive/{issue,prd}/` (S25-26).

## Alternatives Considered

### GitHub Issues only
- Pros: Standard, well-known, integrates with PRs.
- Cons: No local view of all issues; agent must use `gh` CLI;
  dual-track (issues live on the website, PRDs would live in files).
- Rejected: friction for an agent working in this repo.

### Linear / Jira / Shortcut
- Pros: Powerful trackers with dependencies, labels, etc.
- Cons: External SaaS; requires an account; data lives outside the repo.
- Rejected: out of scope; this is a personal / open-source project.

### `bd` (beads) or other CLI issue trackers
- Pros: Local file storage, dependency links.
- Cons: Yet another tool to learn; doesn't render as nicely in PRs
  or web views.
- Rejected: the markdown convention is already familiar to anyone
  who's read a GitHub issue, and renders directly in `gh pr`,
  `cat`, and any markdown viewer.

## Consequences

- **Pos:** Zero external dependencies. A fresh `git clone` includes
  the full work history.
- **Pos:** Single tool to read & write: any text editor + `cat` /
  `ls`. No web UI to log in to.
- **Pos:** The agent can split a design into vertical slices, write
  them as markdown files, and immediately start implementing — no
  handoff to a tracker UI.
- **Pos:** PRDs sit next to their issues on the filesystem, so a code
  reviewer can see both in one terminal.
- **Pos:** Archive is a folder move (`mv .issues/S*.md docs/archive/issue/`)
  — fully auditable as a single commit.
- **Neg:** No web UI for browsing. A user has to `cat .issues/INDEX.md`
  to see the work queue.
- **Neg:** The convention is local to this repo. A new contributor
  must read `.issues/README.md` once.
- **Neg:** No automation around `blocked_by` — the dep graph is
  rendered as ASCII in INDEX.md but isn't enforced by tooling.

## Convention

- **ID format:** `S##[a-z]` (e.g. `S08`, `S09a`, `S10b`). Lowercase
  letters distinguish vertical slices in the same issue family.
- **Status:** `ready` (no blockers) | `blocked` (waiting on others) |
  `done` (implemented + tested + verified).
- **Labels:** `m0-foundation` (canonical client), `m1-skill` (skill
  core), `m2-skill` (skill extensions), `m2-refs` (docs), `m3-refs`
  (final polish).
- **Archive:** when status flips to `done`, the issue + matching PRD
  are moved to `docs/archive/{issue,prd}/` and the INDEX.md log gets
  a dated entry.
