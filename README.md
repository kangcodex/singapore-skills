# singapore-skills

A collection of agent skills for Singapore-specific lookups. Each skill bundles a Python helper script plus reference docs so the agent (Claude Code, Codex, OpenCode, Cursor, etc.) can answer Singapore-context questions without making things up.

## Skills in this repo

| Skill | Folder | What it does |
|-------|--------|--------------|
| `cdc-voucher-locator-skill` | [`cdc-voucher-locator-skill/`](cdc-voucher-locator-skill/) | Find CDC Voucher-accepting merchants near any Singapore location. Filters by intent (food / supermarket / budget meal / generic). |

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
├── README.md                       # this file
├── LICENSE
├── cdc-voucher-locator-skill/      # the skill
│   ├── SKILL.md                    # frontmatter + workflow for the agent
│   ├── scripts/
│   │   └── cdc_voucher_locator.py  # stdlib-only helper
│   └── references/
│       ├── cdc-data-format.md
│       ├── cdc-url-params.md
│       └── onemap-api.md
└── tests/
    └── test_cdc_voucher_locator.py # smoke tests (pure fns + mocked network)
```

## Testing

Smoke tests use stdlib `unittest` — no extra dependencies:

```bash
python3 -m unittest discover -s tests
```

Or with `pytest`:

```bash
pip install pytest
pytest tests/
```

The suite covers:
- Pure helpers: `haversine_m`, `clean_addr`, `is_food`, `categorize`
- Caching: `fetch_data()` skips download when CDN `Last-Modified` is older than cache
- Geocoding: OneMap's quirky `"error: missing token"` response (data is still in `results[]`)
- Module surface: public functions exist and are callable

Network-dependent paths are mocked so the suite passes in offline / sandboxed environments.

## Adding a new skill

Each skill lives in its own folder with a `SKILL.md` (frontmatter + workflow). See the [vercel-labs/skills](https://github.com/vercel-labs/skills) repo and the [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) collection for reference patterns.

Skeleton:

```text
your-skill-name/
├── SKILL.md            # name + description frontmatter, then workflow
├── scripts/            # optional — stdlib Python preferred
└── references/         # optional — load into context as needed
```

Then `npx skills add kangcodex/singapore-skills` will pick it up.

## License

MIT — see [`LICENSE`](LICENSE).
