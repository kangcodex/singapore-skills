# sg-home-chef-skill — Design Notes

## Purpose

A Singapore home chef recipe coach. Turns any dish request ("I want to cook Sambal Kang Kong") into a 3-tier recipe brief calibrated to **HDB-cookout-kitchen reality** — *not* a hawker stall. The skill ladders the user across:

- **3 skill levels** — beginner (one-pan, ready-made rempah, ≤30 min), intermediate (tumis, blender paste, 30–60 min), advanced (wok hei, manual rempah, fermentation, 60–240 min)
- **2 sourcing tracks** — supermarket (NTUC / Sheng Siong / Cold Storage) vs wet market (Tekka / Tiong Bahru / Geylang Serai)
- **3 ingredient engines** — bilingual SG dictionary (Malay + Chinese + English), substitution table, dietary filter
- **Milestone delivery** — visual + aroma checkpoints (not just timers)

The output is a single Markdown document that the agent writes by reading the script's JSON output and converting it into prose with SG-home-chef voice.

## What it is NOT

- Not a *restaurant recipe* generator. The flavour is 70–85% of a hawker, and that is *good* for a home cook.
- Not a *nutrition tracker*. The skill does not count calories, macros, or micros.
- Not a *commercial-kitchen* advisor. No salamander, no sous-vide, no plancha. The user has a HDB kitchen.
- Not a *single-tier* skill. The default is 3 tiers; the user picks one.
- Not a *single-track* skill. The default is 2 sourcing tracks; the user picks one.

## Output contract

Every recipe brief must contain exactly the 8-section markdown skeleton (see `references/recipe-blueprint.md`):

1. **Title + Scope** — dish + skill-level + sourcing + pax + time + dietary
2. **Why this dish** — 1 line, the case for cooking it
3. **Skill strategy** — equipment, technique complexity, time, rempah philosophy, 3 mistakes
4. **Sourcing strategy** — where to shop, what to say, format, price band
5. **Ingredients table** — bilingual names + quantities + sourcing + substitutes
6. **Method (step-by-step)** — with inline visual + aroma milestones
7. **Plating + serving** — plating instructions, temperature, pairings
8. **Closing block** — 3 honest caveats (LLM-driven, not script-driven)

## The 3-tier skill gatekeeper

Each tier has a *technique ceiling*, a *time budget*, a *pantry philosophy*, and *what to outsource to shortcuts*:

| Tier         | Time (active) | Equipment floor              | Technique ceiling                       | Rempah philosophy |
| ------------ | ------------- | ---------------------------- | --------------------------------------- | ----------------- |
| Beginner     | 10–30 min     | Frying pan, 1 pot, spatula   | One-pan / one-pot, simmer, no wok        | Outsource (paste) |
| Intermediate | 30–60 min     | Wok + spatula, steamer        | Tumis, 2-pan timing                      | Blend (50/50)     |
| Advanced     | 60–240 min    | Carbon-steel wok, mortar, thermometer | Wok hei, fermentation, multi-stage | Grind fresh        |

The script returns `skill_strategy.{level}` with the full 18-key dict. The agent's job is to *narrate* this dict in section 3 of the brief.

## The bilingual ingredient dictionary

18 ingredients × 3 languages (English + Malay + Chinese) × 2 sourcing contexts (supermarket SKU + wet market vendor request). Each ingredient has:

- `sg_name` — English name
- `malay` — Malay/regional name (what the wet-market vendor will say)
- `chinese` — Chinese name (what the supermarket label will say)
- `supermarket_sku` — what to look for on the shelf at NTUC / Sheng Siong / Cold Storage
- `wet_market_request` — what to say to the vendor at Tekka / Tiong Bahru / Geylang Serai
- `common_substitutes` — 2–3 alternatives
- `dietary_flags` — halal / vegan / gluten-free / etc.

The script returns `ingredient_substitutions[]` for the recipe. The agent's job is to *narrate* the dictionary entries in section 4 of the brief and embed the bilingual names at least once.

## The 2 sourcing tracks

| Track         | Where you shop                           | What you say                              | What you get                          | Price band |
| ------------- | ---------------------------------------- | ----------------------------------------- | ------------------------------------- | ---------- |
| Supermarket   | NTUC FairPrice / Sheng Siong / Cold Storage | "Where is the [English name]?"          | Pre-portioned, labelled, ready-to-cook | S$ — S$ +  |
| Wet market    | Tekka / Tiong Bahru / Geylang Serai / Chinatown / Maxwell | "[Malay name] [quantity]" | Whole, fresh, vendor-portioned         | S$  — S$   |

The two columns are deliberately inversed. **Supermarket = more money, less talk. Wet market = less money, more talk.** The *quality* difference is real (wet market is fresher), but the *convenience* difference is also real (supermarket is 24/7, no haggling, no parking).

The script returns `sourcing_strategy.{track}` with the full 7-key dict. The agent's job is to embed the sourcing strategy in section 4 ("Ingredients") and use the bilingual vendor request as the *what to say* column.

## The contradiction detector

The script returns `warnings[]` for incompatible combinations:

- `("beginner", "supermarket", ...)` → no warning (default is fine)
- `("beginner", "wet-market", ...)` → warning: "Wet-market vendors expect you to know what you want"
- `("advanced", "supermarket", ...)` → warning: "Supermarket may not yield authentic rempah"
- `(None, "wet-market", ...)` → warning: "Wet market closes early (often 12pm-6pm). Confirm timing before you go."

The agent's job is to *respect* the warning in the brief (e.g. add a "Plan your trip" section).

## The milestone delivery (visual + aroma, not timers)

The script returns `milestones[]` — a list of `{type: "visual" | "aroma", milestone: "..."}` flat entries. The agent's job is to weave these into section 6 of the brief and into the inline Method steps.

**Why milestones, not timers.** A 29yo Hainanese chicken rice cook cannot time the stock by a stopwatch — the stock is done when the chicken floats, when the aromatics smell right, when the fat separates. The script encodes this as `visual_cue` + `aroma_cue`. The agent must use them.

## Voice

The agent's voice is calibrated to:

- **HDB-cookout-kitchen realism** — single-burner induction, magnetic wok, 1 m² of counter
- **Singaporean palate** — salty + sweet + spicy, *not* Thai-spicy or Malay-spicy
- **Bilingual fluency** — the user can read English OR Malay OR Chinese; use all three where it helps
- **Honest humility** — this is a *home cook's* brief, not a hawker's

## Script / LLM division of labor

| Concern                     | Script (deterministic) | LLM (subjective) |
| --------------------------- | ---------------------- | ---------------- |
| Param validation            | ✓ (6 params + aliases) | — |
| Skill-level resolver         | ✓ (3 tiers + aliases)  | — |
| Sourcing-track resolver      | ✓ (2 tracks + aliases) | — |
| Dietary filter              | ✓ (7 modes)            | — |
| Bilingual dictionary lookup | ✓ (18 ingredients)     | — |
| Sunk-cost / contradiction    | ✓ (4 watches)          | — |
| Milestone generation         | ✓ (visual + aroma)     | — |
| Recipe blueprint (structure) | ✓ (8 sections)         | — |
| **Prose**                    | —                      | ✓ (8 sections)   |
| **Voice / cultural nuance**  | —                      | ✓                |
| **Plating instructions**     | —                      | ✓                |
| **Closing caveats**          | —                      | ✓                |
| **Dietary advice**           | —                      | ✓                |

## Guardrails

1. **Never invent prices.** If the script returns `price_band: "S$"`, write "around S$" — not "S$5.50".
2. **Never invent vendor speech.** Use the script's `wet_market_request` *exactly* — vendors are sensitive to mispronunciation.
3. **Never recommend a *specific* brand** the dictionary does not have. If the user asks for a brand you do not have, say "Prima Taste, Tean's, or Ponniah are the 3 SG-standard brands" — not "Use the BABA's one I saw at NTUC".
4. **Always include the 3 caveats** in the closing block (or the safety note for true beginners).
5. **Always respect the dietary filter.** If the user says halal, never suggest pork or non-halal-certified belacan. If vegan, never suggest belacan. If gluten-free, never suggest Shaoxing wine.
6. **Never suggest commercial equipment.** No salamander, no sous-vide, no plancha. The user has a HDB kitchen.
7. **Always use the bilingual ingredient names** at least once. Singapore is multilingual.
8. **Never claim a recipe is "authentic".** It is *calibrated* to a Singaporean palate.

## How "with-skill" differs from "without-skill"

A model without the skill responding to "I want to cook Sambal Kang Kong" might produce:

- A 5-sentence list of ingredients with no SG-specific sourcing
- No skill-level scaffolding (the same recipe regardless of whether the user is a beginner or advanced)
- No bilingual names (just "shallots", never "bawang merah / 红葱头")
- No vendor speech (just "go to NTUC", never "Beri saya 200g kangkung")
- No milestones (just "stir-fry for 5 minutes")
- No dietary filter (just the recipe, no halal/vegetarian substitution)
- No contradiction detection (no warning if advanced + supermarket)

The eval results confirm: with_skill beats baseline on all 3 evals (70/70 = 100%).

## See also

- `skills/sg-home-chef-skill/SKILL.md` — full workflow + voice guide
- `skills/sg-home-chef-skill/references/skill-levels.md` — 3-tier rules
- `skills/sg-home-chef-skill/references/ingredient-dictionary.md` — bilingual SG dictionary
- `skills/sg-home-chef-skill/references/sourcing-tracks.md` — supermarket vs wet market
- `skills/sg-home-chef-skill/references/recipe-blueprint.md` — 8-section output skeleton + worked example
- `skills/sg-home-chef-skill/scripts/sg_home_chef.py` — deterministic script (743 lines, stdlib-only)
- `skills/sg-home-chef-skill/evals/evals.json` — 3 eval definitions
- `skills/sg-home-chef-skill/evals/grade.py` — deterministic grader
- `skills/sg-home-chef-skill/tests/test_sg_home_chef.py` — 42 unit tests
