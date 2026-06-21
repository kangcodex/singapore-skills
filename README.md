# singapore-skills

A collection of agent skills for Singapore-specific lookups. Each skill bundles a Python helper script plus reference docs so the agent (Claude Code, Codex, OpenCode, Cursor, etc.) can answer Singapore-context questions without making things up.

## Skills in this repo

| Skill | Folder | What it does |
|-------|--------|--------------|
| `cdc-voucher-locator-skill` | [`cdc-voucher-locator-skill/`](cdc-voucher-locator-skill/) | Find CDC Voucher-accepting merchants near any Singapore location. Filters by intent (food / supermarket / budget meal / generic). |
| `smart-commuter-skill` | [`smart-commuter-skill/`](smart-commuter-skill/) | Car driver rerouting — pick the right HDB carpark, swap to alternates when full, plus live traffic and thunderstorm advisories. |
| `resale-property-advisor-skill` | [`resale-property-advisor-skill/`](resale-property-advisor-skill/) | "Is this asking price fair?" — compares against HDB resale cluster average, lists nearby URA future amenities, flags above-average rainfall. |
| `weekend-planner-skill` | [`weekend-planner-skill/`](weekend-planner-skill/) | Family-friendly weekend activity planner — pivots to indoor ActiveSG when UV≥11 or PSI≥101, swaps hawker centres during cleaning windows. |
| `mrt-rerouter-skill` | [`mrt-rerouter-skill/`](mrt-rerouter-skill/) | Cross-island MRT + bus routing with PSI/walk-leg downgrades and LTA traffic-image-driven bus-leg penalties. |
| `dengue-risk-advisor-skill` | [`dengue-risk-advisor-skill/`](dengue-risk-advisor-skill/) | Outdoor activity dengue-risk tier (low / moderate / elevated / high) from NEA cluster density + 7-day rainfall forecast vs. 5-year history. |
| `hawker-discover-skill` | [`hawker-discover-skill/`](hawker-discover-skill/) | Hawker centre finder — composes the CDC voucher locator via subprocess, then filters to centres that are **open today**. |

## Install

This repo follows the [vercel-labs/skills](https://github.com/vercel-labs/skills) install pattern. The `skills` CLI works with **OpenCode, Claude Code, Codex, Cursor**, and [68 other agents](https://github.com/vercel-labs/skills#supported-agents).

### Install all skills from this repo

```bash
npx skills add kangcodex/singapore-skills
```

### Install a single skill

```bash
# Specific skill
npx skills add kangcodex/singapore-skills --skill cdc-voucher-locator-skill

# Direct subpath (works for any agent that resolves GitHub tree URLs)
npx skills add https://github.com/kangcodex/singapore-skills/tree/main/cdc-voucher-locator-skill
```

### Install for a specific agent only

```bash
# Claude Code
npx skills add kangcodex/singapore-skills -a claude-code

# OpenCode
npx skills add kangcodex/singapore-skills -a opencode

# Codex
npx skills add kangcodex/singapore-skills -a codex
```

### Install globally (across all your projects)

```bash
npx skills add kangcodex/singapore-skills -g
```

### Non-interactive (CI / scripts)

```bash
npx skills add kangcodex/singapore-skills -a claude-code -y
```

The CLI prompts you to choose between **symlink** (recommended — single source of truth, easy updates) or **copy** (independent copies per agent) on first run. Use `-y` to skip the prompt.

## Manual / local install

If you can't or don't want to use the `npx skills` CLI:

```bash
# Clone the repo
git clone https://github.com/kangcodex/singapore-skills.git
cd singapore-skills

# Copy the skill into your agent's skills directory
mkdir -p ~/.claude/skills
cp -r cdc-voucher-locator-skill ~/.claude/skills/
```

For other agents, the destination paths differ — see the [vercel-labs/skills supported agents list](https://github.com/vercel-labs/skills#supported-agents).

## Usage: `cdc-voucher-locator-skill`

Once installed, the agent triggers the skill automatically when the user asks things like:

- "Where can I use CDC vouchers near Ang Mo Kio Hub?"
- "Find hawker food near me that accepts CDC vouchers"
- "Supermarkets near Bishan that take CDC vouchers"
- "Cheap budget meals in Toa Payoh with CDC vouchers"

### The four modes

The agent picks a mode from the user's wording, then runs the bundled script:

| Mode | Trigger words | What it shows |
|------|---------------|---------------|
| **A** — Generic | default, "CDC vouchers near X" | Supermarkets + hawker/heartland sub-categorized (F&B, Beauty, Health, Retail, Home, Services, Other) + Budget Meal |
| **B** — Food | "food", "eat", "makan", "dine" | Only food merchants, sorted by recommendation (with web research for ⭐ ratings) |
| **C** — Supermarkets | "supermarket", "grocery", "groceries" | Only supermarkets, sorted by distance |
| **D** — Budget Meal | "budget", "cheap", "affordable" | Only budget-meal tagged merchants |

### Running the script directly

The skill bundles a standalone Python script — no `pip install` required, only stdlib:

```bash
python3 cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py "Ang Mo Kio Hub" B 500
```

Arguments: `query`, `mode` (A|B|C|D), `radius_m` (default 500).

Output is JSON — pipe through `jq` for a quick look:

```bash
python3 cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py "Tiong Bahru" C | jq '.supermarkets[:3]'
```

### Sample report (Mode B, food)

```
=== CDC Voucher Food: Ang Mo Kio Hub (S569933) ===
📅 2026-06-20 | 📏 500m

🍽 Top Food Picks (sorted by recommendation)

⭐⭐⭐⭐⭐ Ah Lim Chicken Rice — Blk 123 Ang Mo Kio Ave 3 (210m)
   Famous for silky poached chicken
⭐⭐⭐⭐ Teck Kee Hokkien Mee — Ang Mo Kio Ave 6 (380m)
   Wok hei charred noodles
⭐⭐⭐⭐ Soon Huat Bak Kut Teh — Ang Mo Kio St 52 (450m)
   Peppery pork rib soup
```

See [`cdc-voucher-locator-skill/SKILL.md`](cdc-voucher-locator-skill/SKILL.md) for the full workflow (caching, geocoding, pitfalls, official URL params).

## How it works

```
┌──────────────┐    intent match    ┌──────────────────────┐
│ User query   │ ──────────────────▶│ Agent triggers skill │
└──────────────┘                    └──────────┬───────────┘
                                              │ run script
                                              ▼
                    ┌──────────────────────────────────────────────┐
                    │ cdc_voucher_locator.py                        │
                    │   1. Geocode via OneMap (free, no auth)       │
                    │   2. Fetch CDC data from GoWhere CDN (cached) │
                    │   3. Haversine filter within radius          │
                    │   4. Auto-expand 500m → 1km if < 5 results   │
                    │   5. Categorize / filter by mode             │
                    └──────────────────────┬───────────────────────┘
                                           │ JSON
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Agent formats report                         │
                    │   Mode B: web-research ⭐ ratings            │
                    │   Mode A/C/D: distance-sorted list           │
                    └──────────────────────────────────────────────┘
```

Cache lives at `~/.hermes/cache/cdc-vouchers/` (only re-downloads when the CDN's `Last-Modified` header changes).

## Project layout

```
singapore-skills/
├── README.md                          # this file
├── LICENSE
├── singapore_api.py                   # canonical shared client (14 fetchers + geocode)
├── .env.example                       # canonical DATA_GOV_SG_API_KEY template
├── scripts/
│   ├── sync_singapore_api.py          # copies the canonical to <skill>/scripts/singapore_api.py
│   └── sync_env_example.py            # copies the canonical to <skill>/.env.example
├── tests/
│   └── test_singapore_api.py          # tests for the canonical shared client (33 tests)
├── docs/
│   └── ORCHESTRATION.md               # chained-tool pattern guide (plan-my-Saturday example)
├── cdc-voucher-locator-skill/         # skill #1
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── cdc_voucher_locator.py
│   │   └── singapore_api.py           # SYNCED FROM ../singapore_api.py
│   ├── .env.example                   # SYNCED FROM ../.env.example
│   ├── references/                    # cdc-data-format.md, cdc-url-params.md, onemap-api.md
│   └── tests/
│       └── test_cdc_voucher_locator.py # 20 smoke tests
├── smart-commuter-skill/              # skill #2
│   └── ... (same shape, 35 tests, 3 references)
├── resale-property-advisor-skill/     # skill #3 (31 tests, 3 references)
├── weekend-planner-skill/             # skill #4 (36 tests, 3 references)
├── mrt-rerouter-skill/                # skill #5 (45 tests, 3 references)
├── dengue-risk-advisor-skill/         # skill #6 (64 tests, 3 references)
└── hawker-discover-skill/             # skill #7 (25 tests, 2 references)
```

Each per-skill `scripts/singapore_api.py` and `.env.example` is generated by the
two sync scripts in `scripts/`. They are **not** edited by hand — edit the
canonical file at the repo root and re-run the sync. See "Adding a new skill"
below.

## Testing

Smoke tests use stdlib `unittest` — no extra dependencies. **Each skill has its
own `tests/` directory** (so the suite stays self-contained when a single skill
is installed via `npx skills add --skill <name>`). The repo-root `tests/`
covers only the **canonical shared client** (`singapore_api.py`).

```bash
# Run the shared-client suite
python3 -m unittest discover -s tests

# Run a per-skill suite
python3 -m unittest discover -s cdc-voucher-locator-skill/tests
python3 -m unittest discover -s smart-commuter-skill/tests
python3 -m unittest discover -s resale-property-advisor-skill/tests
python3 -m unittest discover -s weekend-planner-skill/tests
python3 -m unittest discover -s mrt-rerouter-skill/tests
python3 -m unittest discover -s dengue-risk-advisor-skill/tests
python3 -m unittest discover -s hawker-discover-skill/tests

# Or with pytest (same shape)
pip install pytest
pytest cdc-voucher-locator-skill/tests/
```

Test counts (as of 2026-06-21):

| Suite                                  | Tests |
| -------------------------------------- | ----- |
| `tests/test_singapore_api.py`          | 33    |
| `cdc-voucher-locator-skill/tests/`     | 20    |
| `smart-commuter-skill/tests/`          | 35    |
| `resale-property-advisor-skill/tests/` | 31    |
| `weekend-planner-skill/tests/`         | 36    |
| `mrt-rerouter-skill/tests/`            | 45    |
| `dengue-risk-advisor-skill/tests/`     | 64    |
| `hawker-discover-skill/tests/`         | 25    |
| **Total**                              | **289** |

Network-dependent paths are mocked so the suite passes in offline / sandboxed
environments. The pure helpers and the network seam are both covered.

## Chaining skills together

Some user queries need **more than one skill in sequence** — e.g. "Plan my
Saturday" is weekend-planner (S03a) + dengue-risk-advisor (S05a) + mrt-rerouter
(S04a). The pattern, the trigger-words table, the cache-key convention, and
"do not orchestrate" negative examples live in
[`docs/ORCHESTRATION.md`](docs/ORCHESTRATION.md).

## Project layout

```
singapore-skills/
├── README.md                          # this file
├── LICENSE
├── singapore_api.py                   # canonical shared client (14 fetchers + geocode)
├── .env.example                       # canonical DATA_GOV_SG_API_KEY template
├── scripts/
│   ├── sync_singapore_api.py          # copies the canonical to <skill>/scripts/singapore_api.py
│   └── sync_env_example.py            # copies the canonical to <skill>/.env.example
├── tests/
│   └── test_singapore_api.py          # tests for the canonical shared client (33 tests)
├── docs/
│   └── ORCHESTRATION.md               # chained-tool pattern guide (plan-my-Saturday example)
├── cdc-voucher-locator-skill/         # skill #1
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── cdc_voucher_locator.py
│   │   └── singapore_api.py           # SYNCED FROM ../singapore_api.py
│   ├── .env.example                   # SYNCED FROM ../.env.example
│   ├── references/                    # cdc-data-format.md, cdc-url-params.md, onemap-api.md
│   └── tests/
│       └── test_cdc_voucher_locator.py # 20 smoke tests
├── smart-commuter-skill/              # skill #2
│   └── ... (same shape, 35 tests, 3 references)
├── resale-property-advisor-skill/     # skill #3 (31 tests, 3 references)
├── weekend-planner-skill/             # skill #4 (36 tests, 3 references)
├── mrt-rerouter-skill/                # skill #5 (45 tests, 3 references)
├── dengue-risk-advisor-skill/         # skill #6 (64 tests, 3 references)
└── hawker-discover-skill/             # skill #7 (25 tests, 2 references)
```

Each per-skill `scripts/singapore_api.py` and `.env.example` is generated by the
two sync scripts in `scripts/`. They are **not** edited by hand — edit the
canonical file at the repo root and re-run the sync. See "Adding a new skill"
below.

## Adding a new skill

Each skill lives in its own folder with a `SKILL.md` (frontmatter + workflow). See the [vercel-labs/skills](https://github.com/vercel-labs/skills) repo and the [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) collection for reference patterns.

Skeleton:

```text
your-skill-name/
├── SKILL.md            # name + description frontmatter, then workflow
├── scripts/            # stdlib Python preferred
│   ├── singapore_api.py     # COPY of the canonical client (see below)
│   └── your_skill.py
└── references/         # optional — load into context as needed
```

### Shared API client + sync

Every skill that calls data.gov.sg, OneMap, or any LTA endpoint imports from
`singapore_api.py` — a stdlib-only shared client at the repo root. The skill
ships its own **byte-identical copy** of this file at
`scripts/singapore_api.py` so the skill is self-contained on install (no
symlink, no monorepo assumption).

**Workflow when you add or change a fetch function:**

1. Edit the canonical `singapore_api.py` at the repo root.
2. Run `python3 scripts/sync_singapore_api.py` — this copies the file to
   every skill's `scripts/singapore_api.py` and stamps a `## SYNCED FROM`
   header (source path + last-synced SHA256) on each copy.
3. Run `python3 scripts/sync_singapore_api.py --check` in CI to fail the
   build if any copy is stale.

### Shared `.env.example` + sync

The data.gov.sg v2 endpoints require `DATA_GOV_SG_API_KEY` for higher rate
limits (v1 still works without it). The repo ships a canonical
[`.env.example`](.env.example) at the root, and a copy at every
`<skill>/.env.example` — generated by `scripts/sync_env_example.py` (same
modes: default, `--check`, `--dry-run` as the API sync).

Workflow when you change the env schema:

1. Edit the canonical `.env.example` at the repo root.
2. Run `python3 scripts/sync_env_example.py` to copy it to every skill.
3. Run `python3 scripts/sync_env_example.py --check` in CI to fail on drift.

For the user: `cp .env.example .env` and add their key. The canonical
client reads `DATA_GOV_SG_API_KEY` at call time and falls back to anonymous
calls when unset, so the skill works without a key for trial runs.

Then `npx skills add kangcodex/singapore-skills` will pick it up.

## License

MIT — see [`LICENSE`](LICENSE).
