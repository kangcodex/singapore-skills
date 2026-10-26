# singapore-skills

A collection of agent skills for Singapore-specific lookups. Each skill bundles a Python helper script plus reference docs so the agent (Claude Code, Codex, OpenCode, Cursor, etc.) can answer Singapore-context questions without making things up.

## Skills in this repo

| Skill | Folder | What it does |
|-------|--------|--------------|
| `cdc-voucher-locator-skill` | [`skills/cdc-voucher-locator-skill/`](skills/cdc-voucher-locator-skill/) | Find CDC Voucher-accepting merchants near any Singapore location. Filters by intent (food / supermarket / budget meal / generic). |
| `smart-commuter-skill` | [`skills/smart-commuter-skill/`](skills/smart-commuter-skill/) | Car driver rerouting — pick the right HDB carpark, swap to alternates when full, plus live traffic and thunderstorm advisories. |
| `property-advisor-skill` | [`skills/property-advisor-skill/`](skills/property-advisor-skill/) | Household-led housing decisions across HDB, EC, private flats/condos and landed: research/discovery, policy/liveability, matched prices, costs and versioned case audits. Includes offline `--mode agent` buyer profiles, cash/CPF timelines and scenario comparisons with lifestyle add-ons. Public sources plus uploads; stdlib helpers. |
| `weekend-planner-skill` | [`skills/weekend-planner-skill/`](skills/weekend-planner-skill/) | Family-friendly weekend activity planner — pivots to indoor ActiveSG when UV≥11 or PSI≥101, swaps hawker centres during cleaning windows. |
| `mrt-rerouter-skill` | [`skills/mrt-rerouter-skill/`](skills/mrt-rerouter-skill/) | Cross-island MRT + bus routing with PSI/walk-leg downgrades and LTA traffic-image-driven bus-leg penalties. |
| `dengue-risk-advisor-skill` | [`skills/dengue-risk-advisor-skill/`](skills/dengue-risk-advisor-skill/) | Outdoor activity dengue-risk tier (low / moderate / elevated / high) from NEA cluster density + 7-day rainfall forecast vs. 5-year history. |
| `hawker-discover-skill` | [`skills/hawker-discover-skill/`](skills/hawker-discover-skill/) | Hawker centre finder — composes the CDC voucher locator via subprocess, then filters to centres that are **open today**. |
| `agent-match-skill` | [`skills/agent-match-skill/`](skills/agent-match-skill/) | Look up CEA-registered property salespersons by name or registration number. Filter to a postcode sector; attach track-record (closed-deal count by town + flat type) from CEA monthly transaction records. |
| `rental-yield-calculator-skill` | [`skills/rental-yield-calculator-skill/`](skills/rental-yield-calculator-skill/) | Estimate gross + net rental yield on a private condo purchase. Combines URA Private Resi Trans (buy baseline) with URA Rentals Non-Landed (rent series) and an 8-quarter trend block. |
| `air-quality-advisor-skill` | [`skills/air-quality-advisor-skill/`](skills/air-quality-advisor-skill/) | "Should I go for a run right now?" — combines current PSI / PM2.5 / UV (NEA realtime) with a 4-day forecast and a 5-band health advisory. |
| `overseas-trip-planner-skill` | [`skills/overseas-trip-planner-skill/`](skills/overseas-trip-planner-skill/) | Day-by-day overseas trip concierge for Singapore-origin travelers — persona matrix (solo / family / couple), daylight cutoff, transit buffer math, hyper-local dish enforcement, "Skip the Trap" section. |
| `sg-fruit-price-tracker-skill` | [`skills/sg-fruit-price-tracker-skill/`](skills/sg-fruit-price-tracker-skill/) | Cron-driven weekly fruit price tracker — Cold Storage via stdlib urllib + aria-label regex, FairPrice via web_search, Sheng Siong flagged unavailable. CSV / JSON output, rolling 7-day retention, 70+ keyword blocklist. |
| `sg-home-chef-skill` | [`skills/sg-home-chef-skill/`](skills/sg-home-chef-skill/) | Singapore home chef — turns any dish request into a 3-tier recipe brief (beginner one-pan, intermediate tumis, advanced wok hei) calibrated to HDB-cookout-kitchen reality. Bilingual SG ingredient dictionary (Malay + Chinese), 2 sourcing tracks (supermarket vs wet market), dietary filters (halal/vegetarian/vegan/gluten-free), culinary milestones (visual + aroma, not timers). |

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
npx skills add https://github.com/kangcodex/singapore-skills/tree/main/skills/cdc-voucher-locator-skill
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

# Export tracked runtime files, excluding local caches and workings
python3 scripts/package_skills.py --skill cdc-voucher-locator-skill --output-dir dist/local

# Copy the clean export into your agent's skills directory
mkdir -p ~/.claude/skills
cp -r dist/local/cdc-voucher-locator-skill ~/.claude/skills/cdc-voucher-locator-skill
```

For other agents, the destination paths differ — see the [vercel-labs/skills supported agents list](https://github.com/vercel-labs/skills#supported-agents).

### Runtime-only distribution

All 13 skill folders contain installed instructions, runtime scripts, reference
knowledge/data and output assets. The entire `development/` workspace, including
individual-skill tests, synthetic fixtures and eval prompts, is local-only,
untracked and ignored. Existing local files are preserved; fresh clones do not
contain them. Published package checks remain self-contained under `tests/`.
See the [per-skill audit](docs/skill-distribution.md).

```bash
python3 scripts/package_skills.py --output-dir dist/all-skills
python3 scripts/package_skills.py --skill sg-home-chef-skill --output-dir dist/chef
```

Each export includes the MIT license. Use a fresh output directory for subsequent
builds. The exporter reads tracked runtime paths only; `.gitignore` is not an
installer filter. Hawker discovery invokes the CDC sibling skill, so selecting
hawker also exports CDC: co-install both folders under the same skills directory.
The ten bundled shared API clients remain necessary for standalone imports.

## Usage: `property-advisor-skill`

The [advisor workflow](skills/property-advisor-skill/SKILL.md) handles focused
questions as well as housing searches across HDB, EC, private flats/condos and
landed. Native tools obtain actual property/document/route evidence; stdlib helpers
screen supplied facts, reconcile documents, assess household functions and compare
dated cash/CPF funding/scenarios. See the
[input reference](skills/property-advisor-skill/references/assessment-inputs.md).

```bash
python3 skills/property-advisor-skill/scripts/advisor_cli.py \
  --case skills/property-advisor-skill/assets/case-template.json --format json
```

The empty template is an import/record smoke check, not completed advice. Create
actual inputs from the bundled input reference and case template. Source/route/OCR
access and official eligibility/approval are not implied by a passed calculation.

### Property advisor distribution

`skills/property-advisor-skill/` contains only the runtime: `SKILL.md`, `scripts/`,
`references/` (including loaded policy/profile JSON), `assets/case-template.json`,
`.env.example` and `LICENSE`. Tests, eval definitions and demo scenarios under
`development/property-advisor/` are local-only and excluded from Git. The runtime
and published package smoke check do not depend on that workspace.

For a clean local folder or importable `.skill` ZIP:

```bash
python3 scripts/package_property_advisor.py
# dist/property-advisor-skill/       — copy or install this folder
# dist/property-advisor-skill.skill  — import this ZIP-format skill
```

Use a fresh `--output-dir PATH` for another build. The exporter includes tracked
runtime files only, excluding untracked/local workings even when they are inside
the checkout. The `npx skills` installer copies subdirectories rather than using
`.gitignore` as a package filter; use the clean export for local imports. GitHub
installs select the runtime-only skill folder directly.

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
python3 skills/cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py "Ang Mo Kio Hub" B 500
```

Arguments: `query`, `mode` (A|B|C|D), `radius_m` (default 500).

Output is JSON — pipe through `jq` for a quick look:

```bash
python3 skills/cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py "Tiong Bahru" C | jq '.supermarkets[:3]'
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

See [`skills/cdc-voucher-locator-skill/SKILL.md`](skills/cdc-voucher-locator-skill/SKILL.md) for the full workflow (caching, geocoding, pitfalls, official URL params).

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
├── singapore_api.py                 # canonical shared client
├── scripts/                        # exporters and canonical-file sync tools
├── skills/<name>/                  # 13 runtime-only installed skills
│   ├── SKILL.md
│   ├── scripts/                    # entry point and required bundled dependencies
│   ├── references/                 # optional agent knowledge and runtime JSON
│   └── assets/                     # optional reusable output templates
├── development/<short-name>/       # ignored local workspace, absent in fresh clones
├── tests/                          # shared-client, distribution and API integration checks
├── docs/                           # maintained project documentation
└── dist/                           # ignored clean folders and .skill archives
```

Each per-skill `scripts/singapore_api.py` and `.env.example` is generated by the
two sync scripts in `scripts/`. They are **not** edited by hand — edit the
canonical file at the repo root and re-run the sync. See "Adding a new skill"
below.

## Testing

Published checks under `tests/` cover the shared client, clean distribution and
optional API integrations. Package checks do not require a local developer
workspace. Individual-skill regression suites and evals under `development/`
are deliberately local-only and cannot be reproduced from a fresh clone alone.

```bash
# Run published package checks, including isolated imports
make test-skills

# Run the broader local suite only when development/ is present
make test-local

# Individual local suites (not included in Git)
python3 -m unittest discover -s development/property-advisor/tests
python3 -m unittest discover -s development/sg-home-chef/tests
python3 -m pytest tests/test_skill_distribution.py tests/test_property_distribution.py
```

Behavioral eval prompts are local-only under `development/<short-name>/evals/`.
Use actual native outputs for grading. `make test-local` fails explicitly if the
workspace is absent; the smaller published package suite is not a substitute for
the full local regression/evaluation corpus.

## Chaining skills together

Some user queries need **more than one skill in sequence** — e.g. "Plan my
Saturday" is weekend-planner (S03a) + dengue-risk-advisor (S05a) + mrt-rerouter
(S04a). The pattern, the trigger-words table, the cache-key convention, and
"do not orchestrate" negative examples live in
[`docs/ORCHESTRATION.md`](docs/ORCHESTRATION.md).

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

Keep local tests/evals outside the runtime folder in ignored `development/<short-name>/`.
Add the skill's entry point to the distribution test and verify its clean export
without repository-side imports. Declare any sibling-skill dependency in the
exporter and documentation.

## License

MIT — see [`LICENSE`](LICENSE).
