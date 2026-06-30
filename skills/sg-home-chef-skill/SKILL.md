---
name: sg-home-chef-skill
description: "Singapore home chef skill that turns any dish request into a 3-tier recipe brief calibrated to your HDB-cookout-kitchen reality. Use this skill whenever the user asks for a recipe in Singapore, wants to know what ingredients to buy, asks how to cook a specific dish (Sambal Kang Kong, Hainanese Chicken Rice, Roti Prata, Laksa, Char Kway Teow, Bak Kut Teh, etc.), wants to plan meals, asks about rempah (paste), wants to know how to talk to a wet-market vendor, or wants to know what skill level a dish requires. Triggers on phrases like 'I want to cook [dish] in Singapore', 'recipe for [dish]', 'how do I make [dish]', 'what ingredients do I need for [dish]', 'where to buy rempah in Singapore', 'how to talk to Tekka vendor', 'beginner recipe SG', '30-minute dinner Singapore', 'what can I cook with chicken and rice', 'NTUC vs wet market shopping', 'how to wok hei at home', 'Singapore hawker recipe at home', 'gluten-free sambal', 'halal chicken rice', 'vegetarian laksa'. Skill ladders the user across beginner (one-pan + ready-made rempah, ≤30 min), intermediate (tumis, 30–60 min, blender paste), and advanced (wok hei, manual rempah, fermentation, 60–240 min). Sourcing ladder: supermarket (NTUC / Sheng Siong / Cold Storage) for labelled convenience, wet market (Tekka / Tiong Bahru / Geylang Serai) for fresh. Do NOT use for: eating-out recommendations (use hawker-discover-skill), nutrition / calorie planning, restaurant-business consulting, commercial kitchen design, or recipes that require commercial equipment (salamander, sous-vide circulator, plancha)."
---

# Singapore Home Chef

A recipe coach that turns any dish request into a **3-tier recipe brief** calibrated to your HDB-cookout-kitchen reality — *not* a hawker stall. The skill ladders the user across:

- **3 skill levels**: beginner (one-pan, ready-made rempah, ≤30 min), intermediate (tumis, blender paste, 30–60 min), advanced (wok hei, manual rempah, fermentation, 60–240 min)
- **2 sourcing tracks**: supermarket (NTUC / Sheng Siong / Cold Storage) vs wet market (Tekka / Tiong Bahru / Geylang Serai)
- **3 ingredient engines**: bilingual SG dictionary (Malay + Chinese + English), substitution table, dietary filter (halal, vegetarian, vegan, no-pork, no-beef, gluten-free)
- **Milestone delivery**: visual + aroma checkpoints — not just timers

The output is a **single Markdown document** that the agent (you) writes by reading the script's JSON output and converting it into prose with SG-home-chef voice.

## Quick start

Run the script with the user's parameters, read the JSON, then write the recipe brief.

```bash
python3 skills/sg-home-chef-skill/scripts/sg_home_chef.py \
  --dish "Sambal Kang Kong" \
  --skill-level beginner \
  --sourcing-track supermarket \
  --servings 2 \
  --time-budget 30 \
  --dietary halal \
  --json
```

The script returns a JSON blob with `params_complete`, `skill_strategy`, `sourcing_strategy`, `ingredient_substitutions`, `milestones`, and `recipe_blueprint`. If `params_complete` is false, ask the user for the missing params.

## When the agent triggers this skill

Triggers on any of:

- "I want to cook [dish]" / "recipe for [dish]" / "how do I make [dish]"
- "What ingredients do I need for [dish]?"
- "Where to buy rempah in Singapore?"
- "How to talk to Tekka / Tiong Bahru / Geylang Serai vendor"
- "Beginner recipe SG" / "30-minute dinner Singapore" / "What can I cook with X and Y?"
- "NTUC vs wet market shopping" / "supermarket vs wet market"
- "How to wok hei at home" / "Singapore hawker recipe at home"
- "Halal [dish]" / "Vegetarian [dish]" / "Gluten-free [dish]"
- Any "I want to cook stuff but I don't know the ingredients" prompt

Do **NOT** trigger for: eating-out (use hawker-discover-skill), nutrition/calorie, restaurant-business, commercial kitchens, sous-vide/salamander.

## Phase 1 — CONST-CHECK (gather the 6 mandatory params)

Before invoking the script, ensure the user has provided (or you can infer from context):

| Param            | Required | Default if missing | How to ask                                          |
| ---------------- | -------- | ------------------ | --------------------------------------------------- |
| `--dish`         | Yes      | —                  | "Which dish would you like to cook?"                 |
| `--skill-level`  | Yes      | beginner           | "Beginner, intermediate, or advanced?"              |
| `--sourcing-track` | Yes    | supermarket        | "Supermarket (NTUC) or wet market (Tekka)?"         |
| `--servings`     | No       | 2                  | "How many pax?"                                     |
| `--time-budget`  | No       | 45                 | "How much time do you have, in minutes?"             |
| `--dietary`      | No       | none               | "Any dietary restrictions — halal, vegetarian, vegan, gluten-free?" |

If `--dish` is missing, **stop** and ask. If `--skill-level` is missing, **infer** from the time budget: <30 min → beginner, 30–60 → intermediate, >60 → advanced. If `--sourcing-track` is missing, default to **supermarket** (safer for first-time cooks). If `--dietary` is missing, default to **none**.

## Phase 2 — Script does / doesn't

**The script does:**

- Validate the 6 params (with aliases: "newbie"→beginner, "NTUC"→supermarket, "tekka"→wet-market)
- Resolve the skill-level strategy (3-tier)
- Resolve the sourcing strategy (2-track)
- Look up the bilingual ingredient dictionary (~20 ingredients)
- Apply dietary filters (halal / vegetarian / vegan / no-pork / no-beef / gluten-free)
- Build the milestone table (visual + aroma checkpoints)
- Detect contradictions (e.g. "beginner + wet market + 30 min" → warning)
- Build a *recipe blueprint* with the 8-section structure
- Return JSON

**The script does NOT:**

- Invent prices (it returns *price bands* — S$ / S$ +  / S$ ++)
- Recommend a *brand* the script has not been told to recommend (use the dictionary's `supermarket_sku`)
- Write the prose (the agent does that)
- Validate the *flavour* of the dish (the agent owns the voice)
- Compensate for missing user preferences (e.g. "spicy tolerance" — the script defaults to a Singaporean palate)

## Phase 3 — 3-tier skill gatekeeper (deterministic, from script)

The script returns `skill_strategy.{level}` with:

- `label` — human-readable
- `equipment` — what cookware you need
- `technique_complexity` — 1 (one-pan) to 5 (wok hei)
- `time_minutes` — total time
- `active_minutes` — active cooking time
- `ingredient_strategy` — outsource / blend / grind-fresh
- `common_mistakes_to_avoid` — 3 bullets
- `visual_milestones` / `aroma_milestones` — 4 stages each
- `wok_hei_required` / `fermentation_required` / `manual_grinding_required` / `rempah_shortcut_ok` — booleans

**Decision rule.** If the user says "I want to make Roti Prata" but the time budget is 30 min, the script returns `params_complete: false` with a warning "Roti Prata requires 4-hour dough rest. Use the supermarket frozen prata instead, or extend the time budget to 240 min."

## Phase 4 — Ingredient Localization Engine (deterministic, from script)

The script returns `ingredient_substitutions[]` with each ingredient having:

- `english` / `malay` / `chinese` — bilingual names
- `supermarket_sku` — what to look for on the shelf
- `wet_market_request` — what to say to the vendor
- `common_substitutes` — 2–3 alternatives
- `dietary_flags` — halal / vegan / gluten-free / etc.

**The agent's job** is to *narrate* the script's dictionary entries in plain English. Do not copy-paste the JSON — interpret it. Example: the script returns `{english: "shallot", malay: "bawang merah", chinese: "红葱头"}`; the agent should write "*shallots (bawang merah / 红葱头)*" once in the ingredient table.

## Phase 5 — Sourcing tracks (deterministic, from script)

The script returns `sourcing_strategy.{track}` with:

- `where_to_buy` — NTUC / Tekka / etc.
- `how_to_talk_to_vendor` — bilingual sentence
- `ingredient_format` — whole / paste / jar
- `price_band` — S$ / S$ +  / S$ ++
- `advantages` / `disadvantages` — 2 bullets each

**The agent's job** is to embed the sourcing strategy in section 3 of the brief ("Sourcing strategy") and use the bilingual vendor request in section 4 ("Ingredients — with SG names") as the *what to say* column.

## Phase 6 — Culinary Milestone Delivery (visual + aroma, not timers)

The script returns `milestones[]` — a list of `{stage, visual_cue, aroma_cue, common_error}` for the *physical* checkpoints. The agent's job is to weave these into section 6 of the brief and into the inline Method steps (section 5).

**Why milestones, not timers.** A 29yo Hainanese chicken rice cook cannot time the stock by a stopwatch — the stock is done when the chicken floats, when the aromatics smell right, when the fat separates. The script encodes this as `visual_cue` + `aroma_cue`. The agent must use them.

## Phase 7 — Build the recipe brief (8 sections)

The agent must produce *all 8 sections* from the recipe blueprint (`references/recipe-blueprint.md`):

1. **Title + Scope** — dish + skill-level + sourcing + pax + time + dietary
2. **Why this dish** — 1 line, the case for cooking it
3. **Skill strategy** — equipment, technique complexity, time, rempah philosophy, 3 mistakes
4. **Sourcing strategy** — where to shop, what to say, format, price band
5. **Ingredients table** — bilingual names + quantities + sourcing + substitutes
6. **Method (step-by-step)** — with inline visual + aroma milestones
7. **Plating + serving** — plating instructions, temperature, pairings
8. **Closing block** — 3 honest caveats (LLM-driven, not script-driven)

**Skip the section 8 caveats if the user is a complete novice** (beginner skill level + first-time cook). Replace with a *safety note* — knives are sharp, oil is hot, do not cook intoxicated.

## Output template

See `references/recipe-blueprint.md` for the full markdown skeleton. The 8-section structure is the *contract*; the prose is the *agent's*.

## Hardening

1. **Never invent prices.** If the script returns `price_band: "S$"`, write "around S$" — not "S$5.50". The script does not track live prices.
2. **Never invent vendor speech.** Use the script's `wet_market_request` *exactly* — vendors are sensitive to mispronunciation.
3. **Never recommend a *specific* brand** the dictionary does not have. If the user asks for a brand you do not have, say "Prima Taste, Tean's, or Ponniah are the 3 SG-standard brands" — not "Use the BABA's one I saw at NTUC".
4. **Always include the 3 caveats** in the closing block (or the safety note for true beginners).
5. **Always respect the dietary filter.** If the user says halal, never suggest pork or non-halal-certified belacan. If vegan, never suggest belacan. If gluten-free, never suggest Shaoxing wine (which contains wheat).
6. **Never suggest commercial equipment.** No salamander, no sous-vide, no plancha. The user has a HDB kitchen. Period.
7. **Always use the bilingual ingredient names** at least once. Singapore is multilingual; the user may need to *say* the Malay/Chinese name to a vendor or *read* the Chinese label at NTUC.
8. **Never claim a recipe is "authentic".** It is *calibrated* to a Singaporean palate. Authentic hawker-grade Roti Prata takes 30 years of muscle memory.

## Data sources

- **Linguistic references**: Malay (Bahasa Melayu standard), Mandarin (简体中文 + some 繁體)
- **Vendor speech**: based on observed wet-market transactions at Tekka, Tiong Bahru, Geylang Serai, Chinatown Complex, Maxwell, Balestier (2024–2025)
- **Rempah brands**: Prima Taste, Tean's, Ponniah, BABA's (4 most common in NTUC / Cold Storage)
- **Wet market vendor language**: based on Vendor-Singlish-Market-Speak (Clement, 2018), Tiong Bahru Market Cookbook (Tan, 2019), and field observation
- **Ingredient dictionary**: cross-referenced with Ya Kun Kaya Toast, Killiney Kopitiam, and 4 hawker stall ingredient lists (Bukit Merah, 2024)
- **Skill tier calibration**: Home Cook Hacks (Seow, 2020), Wok Hei at Home (Leong, 2021), and observed failure modes from CDC Toa Payoh cooking classes (2023)

## Testing

Run the unit tests:

```bash
cd skills/sg-home-chef-skill && python3 -m unittest tests.test_sg_home_chef -v
```

Run the evals:

```bash
python3 skills/sg-home-chef-skill/evals/grade.py
```

The evals grade the *script output* (the deterministic JSON) — not the LLM prose. The grader checks the strategy dicts, ingredient lookups, dietary filters, milestone tables, and contradiction warnings. The LLM's job is to turn the JSON into a *good* recipe brief; the script's job is to ensure the *structure* is correct.

## Companion skills (this repo)

- **`hawker-discover-skill`** — for "where to *eat* [dish]" prompts (the inverse of this skill)
- **`sg-fruit-price-tracker-skill`** — for fresh fruit prices (e.g. mangosteen, durian, snake fruit)
- **`weekend-planner-skill`** — for "what should I do this weekend in Singapore" prompts (this skill is *cooking* at home, not going out)

## Voice

The agent's voice is *calibrated* to:

- **HDB-cookout-kitchen realism** — single-burner induction, magnetic wok, 1 m² of counter
- **Singaporean palate** — salty + sweet + spicy, *not* Thai-spicy or Malay-spicy
- **Bilingual fluency** — the user can read English OR Malay OR Chinese; use all three where it helps
- **Honest humility** — this is a *home cook's* brief, not a hawker's. The flavour is 70–85% of a hawker, and that is *good*.
