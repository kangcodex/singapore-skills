"""SG Home Chef — Singapore home-cooking concierge helpers.

Stdlib-only. No network. Given a dish + 3 user params (skill level, sourcing
track, dietary, time budget, servings), validates the mandatory parameters,
applies the 3-tier skill-level strategy, picks a sourcing track, normalises
the ingredient list against the SG-localized dictionary, and returns a
combined strategy the agent uses to write the recipe brief. The LLM does
the subjective work (naming the right technique, the right wok, the right
finish); this script is the deterministic safety net.

Usage:
    python3 sg_home_chef.py --dish "Sambal Kang Kong" --skill-level beginner \
        --sourcing-track supermarket --servings 2 --time-budget 30 \
        --dietary halal --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- enums ----

SKILL_LEVELS = ("beginner", "intermediate", "advanced")
SOURCING_TRACKS = ("supermarket", "wet-market")
DIETARY = ("none", "halal", "vegetarian", "vegan", "no-beef", "no-pork", "gluten-free")

# Singapore-origin cooking baseline
SG_KITCHEN_BASELINE = {
    "stove": "Gas / induction hob common in HDB. Wok burner ideally 15k+ BTU equivalent.",
    "pantry_staples_typical": ["Light soy sauce", "Dark soy sauce (sweet, for colouring)", "Sesame oil", "White pepper", "Sugar", "Salt", "Cooking oil (neutral)"],
    "units_metric": True,
    "measuring_typical": ["g", "ml", "tbsp", "tsp", "pieces"],
}

# Maximum time budget in minutes per skill tier — informs how much to simplify
TIME_BUDGET_DEFAULT = 45
TIME_BUDGET_BEGINNER_MAX = 30
TIME_BUDGET_INTERMEDIATE_MAX = 60
TIME_BUDGET_ADVANCED_MAX = 240


# ------------------------------------------------- skill-level strategy -----

_SKILL_STRATEGY: dict[str, dict] = {
    "beginner": {
        "label": "Beginner (new to the dish or to the technique)",
        "equipment": ["Non-stick pan or wok", "Spatula / wooden spoon", "Knife + board", "Small prep bowls"],
        "technique_complexity": "One-pan or quick-stir-fry. Use ready-made rempah / pastes (Prima Taste, Tean's, homemade shortcut). Skip wok hei.",
        "time_minutes": "15-30",
        "active_minutes": "10-20",
        "ingredient_strategy": "Pre-prepared rempah paste, pre-minced garlic/ginger, supermarket cut vegetables, pre-washed greens, bottled sauces. Avoid raw spice grinding.",
        "common_mistakes_to_avoid": ["Overcooking greens to mush", "Adding sauce too early and burning sugar", "Wok too crowded", "Oil not hot enough before garlic"],
        "visual_milestones": [
            "Oil shimmering before garlic hits the pan",
            "Garlic/shallot just turning pale gold (not brown)",
            "Greens just wilted, still bright green",
            "Sauce coats leaves but pools at edges (not dry, not soupy)",
        ],
        "aroma_milestones": [
            "Sharp garlic + shallot fragrance at the 30s mark",
            "Sweet-savory sambal/soy fragrance once paste is in",
        ],
        "wok_hei_required": False,
        "fermentation_required": False,
        "manual_grinding_required": False,
        "rempah_shortcut_ok": True,
    },
    "intermediate": {
        "label": "Intermediate (can multitask, knows timing)",
        "equipment": ["Carbon-steel wok (preferred) or non-stick", "Spatula + ladle", "Sharp knife + board", "Small mortar (optional)"],
        "technique_complexity": "Tumis (slow sauté of rempah) before main ingredients. Multi-stage timing. 2-3 active pans OK.",
        "time_minutes": "30-60",
        "active_minutes": "20-40",
        "ingredient_strategy": "Fresh rempah from wet market OR pre-made paste. Fresh aromatics (shallots, garlic, ginger). Whole dried shrimp / belacan for depth.",
        "common_mistakes_to_avoid": ["Tumis too fast — rempah burns before aromatics release", "Adding greens to cold wok", "Soy sauce on high heat (caramelises, then burns)", "Not pre-heating the wok"],
        "visual_milestones": [
            "Tumis rempah oil splits from paste (small bubbles around edges)",
            "Paste deepens 1-2 shades darker",
            "Greens added after aromatics are deeply fragrant",
            "Final gloss from oil sheen on surface",
        ],
        "aroma_milestones": [
            "Cooked-down shallot + garlic fragrance at the 2-3 min tumis mark",
            "Belacan / dried shrimp scent (if used) released into the oil",
            "Caramelised soy + sugar at the final deglaze",
        ],
        "wok_hei_required": False,
        "fermentation_required": False,
        "manual_grinding_required": False,
        "rempah_shortcut_ok": True,
    },
    "advanced": {
        "label": "Advanced (pursuing authenticity — wok hei, fermentation, manual grinding)",
        "equipment": ["Carbon-steel wok (well-seasoned)", "Wok spatula + ladle", "Heavy cleaver / Chinese chef's knife", "Stone mortar & pestle", "Steaming setup (bamboo or metal)", "Optional: fermentation crock"],
        "technique_complexity": "Manual grinding of fresh rempah. Wok hei via high-BTU burner + double-toss. Optional fermentation (tempeh, shrimp paste, vinegar).",
        "time_minutes": "60-240",
        "active_minutes": "45-120",
        "ingredient_strategy": "Fresh rempah from wet market (Tekka, Tiong Bahru, Geylang Serai for Malay). Belacan toasted dry. Shaoxing wine deglaze. Premium dark soy (Tai Hua, Kwong Cheong Thye).",
        "common_mistakes_to_avoid": ["Wok not hot enough — you get stew, not stir-fry", "Over-grinding rempah into paste (releases bitter oils)", "Shaoxing too early — alcohol evaporates without flavour lift", "Sauces added in wrong order — sugar/soy last"],
        "visual_milestones": [
            "Rempah paste freshly ground is wet and aromatic (not powdery)",
            "Wok just smoking before first ingredient hits",
            "Wok hei visible — wisps of flame / smoke curling off ingredients",
            "Final dish has glossy sheen without pooling oil",
        ],
        "aroma_milestones": [
            "Just-ground rempah releases essential oils within 30s",
            "Belacan toasted dry for 10-15s releases deep umami",
            "Wok hei carries caramelised-char fragrance across the kitchen",
            "Shaoxing deglaze opens with a sharp alcohol lift, then sweetens",
        ],
        "wok_hei_required": True,
        "fermentation_required": False,
        "manual_grinding_required": True,
        "rempah_shortcut_ok": False,
    },
}


# ------------------------------------------------- sourcing tracks ----------

_SOURCING_STRATEGY: dict[str, dict] = {
    "supermarket": {
        "label": "Supermarket (NTUC FairPrice, Sheng Siong, Cold Storage)",
        "where_to_buy": "Nearest NTUC FairPrice / Sheng Siong / Cold Storage. For rempah pastes: Prima Taste, Tean's, Woh Hup, Ayam Brand.",
        "how_to_talk_to_vendor": "Self-service. Read labels. Check 'product of Singapore/Malaysia/Thailand' for rempah authenticity.",
        "ingredient_format": "Pre-washed, pre-cut, packed. Rempah comes as bottled paste. Aromatics sold loose (shallots, garlic, ginger) or pre-minced in tubs.",
        "units": "Retail: per 100g, per piece, per bottle, per pack.",
        "price_band": "Mid. NTUC house brand cheapest; imported / artisanal higher.",
        "advantages": ["Predictable stock", "Air-con", "Card payment", "One-stop"],
        "disadvantages": ["Lower freshness for herbs", "Less variety of regional items", "Rempah pastes are convenience, not authenticity"],
    },
    "wet-market": {
        "label": "Wet market (Tekka, Tiong Bahru, Geylang Serai, Chinatown Complex)",
        "where_to_buy": "Tekka Centre (Little India), Tiong Bahru Market, Geylang Serai Market, Chinatown Complex Market, AMK Hub market, Toa Payoh Lorong 8.",
        "how_to_talk_to_vendor": "Conversational Malay / Hokkien / Teochew / Cantonese. 'Bawang merah berapa satu kilo?' 'Cili padi — pedas ke tidak?' Vendors appreciate the question.",
        "ingredient_format": "Loose, weighed on the spot. Fresh rempah pounded to order (Geylang Serai / Tekka). Belacan by the block.",
        "units": "Kilo (1/2 kg, 1/4 kg), pieces (biji), ikat (bunch). Cash preferred for small purchases.",
        "price_band": "Lower per kg for fresh produce. Higher for premium fish / specific cuts.",
        "advantages": ["Peak freshness", "Specific cultivar / variety you can't get in supermarkets", "Rempah pounded to order", "Cultural connection"],
        "disadvantages": ["Closes early (often 12pm-6pm)", "Cash-heavy", "Less predictable stock", "Language barrier possible"],
    },
}


# ------------------------------------------- ingredient localization -------

# Each entry: canonical English key -> {sg_name, malay, chinese, supermarket_sku, wet_market_request, common_substitutes, dietary_flags}
_INGREDIENT_DICT: dict[str, dict] = {
    "shallot": {
        "sg_name": "Shallot",
        "malay": "Bawang Merah",
        "chinese": "红葱头 (Hong Cong Tau)",
        "supermarket_sku": "Loose, NTUC produce. Typically sold in 100g net bags.",
        "wet_market_request": "'Bawang merah satu quarter kilo' (Malay) or '红葱头四分之一公斤' (Hokkien/Teochew).",
        "common_substitutes": ["Red onion (milder, sweeter — works in a pinch but not authentic)", "Pearl onion (for pickles only)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "garlic": {
        "sg_name": "Garlic",
        "malay": "Bawang Putih",
        "chinese": "蒜头 (Suan Tau)",
        "supermarket_sku": "Loose, in 100g bags. Pre-minced garlic in tubs (cold chain).",
        "wet_market_request": "'Bawang putih' (Malay) — usually sold beside shallots.",
        "common_substitutes": ["Pre-minced garlic in jar (loses sharpness)", "Garlic powder (last resort)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "ginger": {
        "sg_name": "Ginger (old)",
        "malay": "Halia Tua",
        "chinese": "老姜 (Lao Jiang)",
        "supermarket_sku": "Loose, by piece or 100g.",
        "wet_market_request": "'Halia tua satu potong' (Malay) — ask for older ginger (drier, more pungent).",
        "common_substitutes": ["Young ginger (less pungent, not equivalent)", "Galangal (different flavour — see below)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "galangal": {
        "sg_name": "Galangal",
        "malay": "Lengkuas",
        "chinese": "南姜 (Nan Jiang)",
        "supermarket_sku": "Loose, by piece. Pre-sliced frozen galangal in 200g packs (less aromatic).",
        "wet_market_request": "'Lengkuas' (Malay) — distinctive pinkish-cream rings inside.",
        "common_substitutes": ["Ginger (NOT a true substitute — flavour is sharper, more piney)", "Frozen galangal paste (last resort)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "lemongrass": {
        "sg_name": "Lemongrass",
        "malay": "Serai",
        "chinese": "香茅 (Xiang Mao)",
        "supermarket_sku": "Loose, sold by the stalk (1-2 stalks per bunch).",
        "wet_market_request": "'Serai dua batang' (Malay) — choose firm, pale-green stalks.",
        "common_substitutes": ["Lemon zest + bay leaf (very approximate)", "Lemongrass paste in tube (loses brightness)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "turmeric": {
        "sg_name": "Turmeric (fresh)",
        "malay": "Kunyit Hidup",
        "chinese": "黄姜 (Huang Jiang)",
        "supermarket_sku": "Loose, by piece. Often sold beside ginger.",
        "wet_market_request": "'Kunyit hidup' (Malay) — small, knobbly, deep-orange inside.",
        "common_substitutes": ["Ground turmeric (1 tsp per 2 cm fresh)", "Frozen fresh turmeric (NTUC frozen section)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "candlenut": {
        "sg_name": "Candlenut",
        "malay": "Buah Keras",
        "chinese": "石栗 (Shi Li) / 芫茜果 (rare)",
        "supermarket_sku": "Loose, by weight. Sometimes sold as 'candlenut / kemiri'.",
        "wet_market_request": "'Buah keras' (Malay) — waxy, creamy, looks like a small macadamia.",
        "common_substitutes": ["Macadamia nut (closest in texture; neutral flavour)", "Cashew (creamier, sweeter — changes profile)", "Raw almond (works in a pinch)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "belacan": {
        "sg_name": "Shrimp paste (block)",
        "malay": "Belacan",
        "chinese": "虾酱 (Xia Jiang)",
        "supermarket_sku": "Small blocks in cellophane. Brands: Khong Guan, Lee Brand, Baba's.",
        "wet_market_request": "'Belacan sebuku' (Malay) — smell-check first; should be pungent, not ammoniac.",
        "common_substitutes": ["Thai shrimp paste (Kapi) — slightly different fermentation, OK substitute", "Fish sauce (loses the dry-toasted depth; not a true substitute)"],
        "dietary_flags": ["halal", "gluten-free"],
    },
    "dark_soy": {
        "sg_name": "Dark soy sauce (sweet)",
        "malay": "Kicap Manis",
        "chinese": "老抽 (Lao Chou) — for sweet dark",
        "supermarket_sku": "Bottled. Brands: Tai Hua, Kwong Cheong Thye, Lee Kum Kee (Premium dark sweet).",
        "wet_market_request": "Not applicable — packaged only.",
        "common_substitutes": ["Light soy + 1/2 tsp sugar per tbsp (approximation)", "Sweet kecap manis (Indonesian — slightly different)"],
        "dietary_flags": ["vegetarian", "vegan", "halal"],
    },
    "light_soy": {
        "sg_name": "Light soy sauce",
        "malay": "Kicap Masin",
        "chinese": "生抽 (Sheng Chou)",
        "supermarket_sku": "Bottled. Brands: Tai Hua, Kikkoman, Pearl River Bridge.",
        "wet_market_request": "Not applicable — packaged only.",
        "common_substitutes": ["Tamari (Japanese — similar salt, deeper body)", "Maggi seasoning (Hawaii / Filipino variant — different profile)"],
        "dietary_flags": ["vegetarian", "vegan", "halal"],
    },
    "fish_sauce": {
        "sg_name": "Fish sauce",
        "malay": "Kicap Ikan",
        "chinese": "鱼露 (Yu Lu)",
        "supermarket_sku": "Bottled. Brands: Tiparos, Three Crabs, Squid Brand.",
        "wet_market_request": "Not applicable — packaged only.",
        "common_substitutes": ["Thai nam pla (similar)", "Vegetarian fish sauce (mushroom-based, OK for vegan)"],
        "dietary_flags": ["halal", "gluten-free"],
    },
    "calamansi": {
        "sg_name": "Calamansi lime",
        "malay": "Limau Kasturi",
        "chinese": "小青柑 (Xiao Qing Gan) / 酸柑 (Suan Gan)",
        "supermarket_sku": "Small plastic punnets. Imported from Malaysia / Thailand.",
        "wet_market_request": "'Limau kasturi' (Malay) — golf-ball sized, thin skin.",
        "common_substitutes": ["Lime (sub, more acidic — use 2/3 quantity)", "Lemon (last resort, much more sour)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "kangkung": {
        "sg_name": "Water spinach / Kang Kong",
        "malay": "Kangkung",
        "chinese": "空心菜 (Kong Xin Cai)",
        "supermarket_sku": "Pre-washed, pre-bagged, cold chain. Common brands: Pasar, Farm Fresh.",
        "wet_market_request": "'Kangkung seikat' (Malay) — pick the smaller leaves for sweeter flavour.",
        "common_substitutes": ["Morning glory (same plant, different name)", "Spinach (much milder, cooks faster)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "chicken": {
        "sg_name": "Chicken (whole or parts)",
        "malay": "Ayam",
        "chinese": "鸡 (Ji)",
        "supermarket_sku": "Whole chilled, packed. Halal-certified: Jannah, Saffa, Marrybrown (in NTUC).",
        "wet_market_request": "'Ayam seekor' (whole) or 'dua paha ayam' (2 thighs). Halal stalls: ask for 'ayam halal'.",
        "common_substitutes": ["Free-range chicken (more flavour, less fat)", "Corn-fed (sweeter, more yellow fat)"],
        "dietary_flags": ["halal"],
    },
    "pork": {
        "sg_name": "Pork",
        "malay": "Babi / Daging Babi",
        "chinese": "猪肉 (Zhu Rou)",
        "supermarket_sku": "Cold chain, NTUC. Halal-certified alternatives in dedicated section (none for pork).",
        "wet_market_request": "'Babi satu kilo' (Malay) or '猪肉一公斤' (Hokkien/Teochew). Some wet markets are non-halal-certified — confirm before purchase.",
        "common_substitutes": ["Chicken thigh (leaner, different flavour)", "Beef shin (richer, different texture)"],
        "dietary_flags": ["no-pork-substitute"],
    },
    "coconut_milk": {
        "sg_name": "Coconut milk",
        "malay": "Santan",
        "chinese": "椰浆 (Ye Jiang)",
        "supermarket_sku": "Tetra-pak cartons: Ayam, Kara, Thai Choice. 200ml / 400ml / 1L.",
        "wet_market_request": "Not typical — some markets sell fresh-pressed santan but it's rare.",
        "common_substitutes": ["Freshly grated coconut + warm water (closer to fresh santan, more work)", "Coconut cream (thicker, for richer dishes)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "rice": {
        "sg_name": "Rice (jasmine)",
        "malay": "Beras Wangi",
        "chinese": "香米 (Xiang Mi)",
        "supermarket_sku": "5kg / 10kg bags. Brands: Royal Umbrella, Sunwhite, Aroma.",
        "wet_market_request": "Some markets sell loose rice but supermarkets dominate.",
        "common_substitutes": ["Basmati (less sticky)", "Calrose (shorter grain, slightly sticky — closer to nasi lemak)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
    "shaoxing_wine": {
        "sg_name": "Shaoxing cooking wine",
        "malay": "—",
        "chinese": "绍兴酒 (Shao Xing Jiu)",
        "supermarket_sku": "Bottled. Brands: Pagoda, Pearl River Bridge, Shaoxing Hua Diao.",
        "wet_market_request": "Not typical — packaged only.",
        "common_substitutes": ["Dry sherry (closest substitute)", "Japanese mirin (sweeter, different profile)", "Chicken stock + 1 tsp rice vinegar (non-alcoholic)"],
        "dietary_flags": ["vegetarian"],
    },
    "sambal_paste": {
        "sg_name": "Sambal paste (chilli)",
        "malay": "Sambal",
        "chinese": "辣椒酱 (La Jiao Jiang)",
        "supermarket_sku": "Bottled: Prima Taste, Tean's, Ayam Brand. Pre-made in jars.",
        "wet_market_request": "'Sambal satu botol' or 'Sambal tumis sebungkus' (fresh tumis sambal — Tekka / Geylang Serai).",
        "common_substitutes": ["Fresh cili padi + shallots + belacan pounded to order (Geylang Serai)", "Sambal olek (raw — different profile, no oil separation)"],
        "dietary_flags": ["vegetarian", "vegan", "halal", "gluten-free"],
    },
}


# ------------------------------------------------- recipe templates ---------

# A small starter library of common SG / SE Asian home-cooking dishes
# (so the script can do basic ingredient-list planning and not require the
# agent to invent recipes from scratch).
_RECIPE_TEMPLATES: dict[str, dict] = {
    "sambal kang kong": {
        "category": "vegetable",
        "dietary": ["vegetarian", "halal"],
        "servings_per_ingredient_unit": 2,
        "core_ingredients": ["kangkung", "garlic", "shallot", "sambal_paste", "light_soy", "calamansi"],
        "skill_notes": {
            "beginner": "Use pre-washed kangkung, pre-minced garlic, Prima Taste sambal paste. One-pan, 8-10 min.",
            "intermediate": "Fresh rempah: pound shallot + garlic + cili padi. Tumis 2 min. Add kangkung.",
            "advanced": "Belacan toasted dry first. Manual grind cili padi + shallot + garlic. Wok hei finish. Shaoxing deglaze.",
        },
    },
    "hainanese chicken rice": {
        "category": "chicken",
        "dietary": ["halal"],
        "servings_per_ingredient_unit": 4,
        "core_ingredients": ["chicken", "rice", "ginger", "garlic", "light_soy", "coconut_milk", "calamansi"],
        "skill_notes": {
            "beginner": "Use pre-minced garlic-ginger, NTUC chicken. Skip pandan (or use pandan paste). Use chicken stock cube for rice.",
            "intermediate": "Pound garlic + ginger. Toast rice in chicken fat. Poach chicken low-and-slow 45 min.",
            "advanced": "Manually pound rempah. Toast rice with chicken fat. Render fat from skin separately. Make dipping sauces from scratch.",
        },
    },
    "roti prata": {
        "category": "bread",
        "dietary": ["vegetarian", "halal"],
        "servings_per_ingredient_unit": 2,
        "core_ingredients": ["wheat flour", "ghee", "salt", "sugar", "water", "egg"],
        "skill_notes": {
            "beginner": "Skip the dough from scratch — buy ready-made prata from nearest Indian grocer (frozen section). Pan-fry with ghee.",
            "intermediate": "Make the dough the night before. Rest 8h. Stretch and flip.",
            "advanced": "Hand-stretch with the slap technique. Layer ghee and flip to 64+ layers. Serve with fish or egg curry.",
        },
    },
    "laksa": {
        "category": "noodle soup",
        "dietary": ["halal"],
        "servings_per_ingredient_unit": 4,
        "core_ingredients": ["rice vermicelli", "coconut_milk", "lemongrass", "galangal", "belacan", "shallot", "garlic", "fish_sauce", "prawns", "bean sprouts"],
        "skill_notes": {
            "beginner": "Use ready-made laksa paste (Prima Taste). Coconut milk from carton. Pre-cooked prawns.",
            "intermediate": "Toast belacan. Pound rempah from scratch (or use paste + fresh aromatics). Build broth 30 min.",
            "advanced": "Manual grind full rempah. Render prawn shells for broth depth. Layer chilli oil separately.",
        },
    },
    "char kway teow": {
        "category": "noodle stir-fry",
        "dietary": ["halal"],
        "servings_per_ingredient_unit": 2,
        "core_ingredients": ["flat rice noodles", "prawns", "chinese sausage", "egg", "bean sprouts", "garlic", "light_soy", "dark_soy", "fish_sauce", "chilli paste"],
        "skill_notes": {
            "beginner": "Use pre-soaked rice noodles. Pre-cooked prawns. Bottled chilli paste.",
            "intermediate": "Fresh flat noodles (kway teow). Hot wok, fast toss. Multi-stage timing (noodles first, then egg, then veg).",
            "advanced": "Wok hei essential. Cockles (see hum) if available. Render pork fat for depth. High-BTU burner.",
        },
    },
    "bak kut teh": {
        "category": "pork soup",
        "dietary": ["no-pork-substitute"],
        "servings_per_ingredient_unit": 4,
        "core_ingredients": ["pork ribs", "garlic", "light_soy", "dark_soy", "pepper", "star anise"],
        "skill_notes": {
            "beginner": "Use pre-made bak kut teh spice packet (from NTUC). Skip the pre-toasting step. Slow-cook 90 min.",
            "intermediate": "Toast whole spices dry first. Use pork ribs with bone + skin. Skim foam carefully. 2-hour simmer.",
            "advanced": "Two-stage broth: bones first, ribs second. White pepper (Singapore style) or herbal (Klang style) — pick one and commit.",
        },
    },
}


# ----------------------------------------------- contradictions / warnings --

# Watch-out combinations — these should warn (not block).
# Each entry: (skill_level, sourcing_track, warning_message). None = wildcard.
_CONTRADICTION_WATCHES = [
    ("beginner", "wet-market",
     "Beginner + wet-market may be overwhelming — vendors expect you to know what you want. Start supermarket, graduate to wet market once you can name 5+ ingredients in Malay/Hokkien/Teochew."),
    ("advanced", "supermarket",
     "Advanced + supermarket may not yield authentic rempah. Use wet market for fresh-pounded rempah, belacan, and specific cultivars."),
    (None, "wet-market",
     "Wet market closes early (often 12pm-6pm). Confirm timing before you go — arriving after 3pm risks the rempah stall being closed."),
]


# ---------------------------------------------------------------- helpers --

def _resolve_skill_level(raw) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    if s in SKILL_LEVELS:
        return s
    aliases = {
        "newbie": "beginner", "easy": "beginner", "noob": "beginner", "first-time": "beginner",
        "mid": "intermediate", "medium": "intermediate", "ok": "intermediate",
        "expert": "advanced", "pro": "advanced", "hawker-style": "advanced", "restaurant-quality": "advanced",
    }
    return aliases.get(s)


def _resolve_sourcing(raw) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    if s in SOURCING_TRACKS:
        return s
    aliases = {
        "ntuc": "supermarket", "sheng siong": "supermarket", "cold storage": "supermarket", "giant": "supermarket",
        "market": "wet-market", "wetmarket": "wet-market", "wet market": "wet-market",
        "tekka": "wet-market", "tiong bahru": "wet-market", "geylang serai": "wet-market",
    }
    return aliases.get(s)


def _resolve_dietary(raw) -> str:
    if not raw:
        return "none"
    s = raw.strip().lower()
    if s in DIETARY:
        return s
    return "none"


def _normalise_dish(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in _RECIPE_TEMPLATES:
        return s
    for key in _RECIPE_TEMPLATES:
        if key in s or s in key:
            return key
    return s


def _parse_servings(raw) -> int:
    if not raw:
        return 2
    try:
        n = int(raw)
        return max(1, min(n, 20))
    except (ValueError, TypeError):
        return 2


def _parse_time_budget(raw) -> int:
    if not raw:
        return TIME_BUDGET_DEFAULT
    try:
        n = int(raw)
        return max(5, min(n, 240))
    except (ValueError, TypeError):
        return TIME_BUDGET_DEFAULT


def check_params(dish, skill_level, sourcing_track, dietary, servings, time_budget):
    """Return (params_complete: bool, missing_params: list[str], errors: list[str])."""
    missing = []
    errors = []

    if not dish or not dish.strip():
        missing.append("dish")

    if not skill_level:
        missing.append("skill-level")
    elif skill_level not in SKILL_LEVELS:
        errors.append(f"invalid skill-level '{skill_level}' — must be one of {SKILL_LEVELS}")

    if not sourcing_track:
        missing.append("sourcing-track")
    elif sourcing_track not in SOURCING_TRACKS:
        errors.append(f"invalid sourcing-track '{sourcing_track}' — must be one of {SOURCING_TRACKS}")

    if dietary not in DIETARY:
        errors.append(f"invalid dietary '{dietary}' — must be one of {DIETARY}")

    if servings < 1:
        errors.append(f"invalid servings '{servings}' — must be 1-20")

    if time_budget < 5:
        errors.append(f"invalid time-budget '{time_budget}' — must be 5-240 minutes")

    return (len(missing) == 0 and len(errors) == 0, missing, errors)


def detect_contradictions(skill_level, sourcing_track, dietary):
    warnings = []
    for sl, src, msg in _CONTRADICTION_WATCHES:
        if sl is not None and skill_level != sl:
            continue
        if src is not None and sourcing_track != src:
            continue
        warnings.append(msg)
    return warnings


def build_warnings(dish, skill_level, sourcing_track, dietary, time_budget):
    warnings = []
    if skill_level == "beginner" and time_budget > TIME_BUDGET_BEGINNER_MAX:
        warnings.append(
            f"Beginner + {time_budget} min budget is tight. Recommend a 15-30 min recipe "
            f"or downgrade to {TIME_BUDGET_BEGINNER_MAX} min target."
        )
    if skill_level == "advanced" and time_budget < 45:
        warnings.append(
            "Advanced + <45 min leaves no time for manual grinding or wok hei. "
            "Either upgrade time budget to 60+ min, or accept that wok hei will be limited."
        )
    if sourcing_track == "wet-market" and not _dish_uses_rempah(dish):
        warnings.append(
            "Wet market is overkill if the dish doesn't need fresh aromatics — supermarket is faster."
        )
    if dietary in ("halal", "no-pork", "no-beef") and _dish_uses_pork(dish):
        warnings.append(
            f"Dish '{dish}' typically uses pork. Substituting chicken thigh or beef shin — confirm with the user."
        )
    if dietary in ("vegetarian", "vegan") and _dish_uses_meat(dish):
        warnings.append(
            f"Dish '{dish}' is not vegetarian. Recommend a vegetable variant or sub tofu / tempeh — confirm with the user."
        )
    warnings.extend(detect_contradictions(skill_level, sourcing_track, dietary))
    return warnings


def _dish_uses_rempah(dish) -> bool:
    if not dish:
        return False
    template = _RECIPE_TEMPLATES.get(dish)
    if template:
        return True  # all starter recipes need aromatics
    # Heuristic: any Asian dish name implies rempah
    return True


def _dish_uses_pork(dish) -> bool:
    if not dish:
        return False
    s = dish.lower()
    if "pork" in s or "babi" in s or "bak kut teh" in s:
        return True
    template = _RECIPE_TEMPLATES.get(dish)
    if template and "pork" in template.get("core_ingredients", []):
        return True
    return False


def _dish_uses_meat(dish) -> bool:
    if not dish:
        return False
    template = _RECIPE_TEMPLATES.get(dish)
    if template:
        meat_ingredients = {"chicken", "pork", "prawns"}
        return any(ing in meat_ingredients for ing in template.get("core_ingredients", []))
    return False


def build_skill_strategy(skill_level):
    return _SKILL_STRATEGY.get(skill_level) if skill_level else None


def build_sourcing_strategy(sourcing_track):
    return _SOURCING_STRATEGY.get(sourcing_track) if sourcing_track else None


def lookup_ingredient(name: str) -> dict | None:
    """Return the ingredient dictionary entry for a given key (case-insensitive)."""
    if not name:
        return None
    return _INGREDIENT_DICT.get(name.strip().lower())


def build_ingredient_substitutions(dish, dietary, skill_level) -> list[dict]:
    """Return a list of substitution / localisation dicts for the dish's ingredients."""
    if not dish:
        return []
    template = _RECIPE_TEMPLATES.get(dish)
    if not template:
        return []
    subs = []
    for ing_key in template.get("core_ingredients", []):
        entry = _INGREDIENT_DICT.get(ing_key)
        if not entry:
            continue
        sub = {
            "ingredient": ing_key,
            "sg_name": entry["sg_name"],
            "malay": entry.get("malay", ""),
            "chinese": entry.get("chinese", ""),
            "supermarket_sku": entry.get("supermarket_sku", ""),
            "wet_market_request": entry.get("wet_market_request", ""),
        }
        if dietary in ("vegetarian", "vegan") and "halal" not in entry.get("dietary_flags", []):
            if entry.get("common_substitutes"):
                sub["dietary_substitute"] = entry["common_substitutes"][0]
        if dietary == "halal" and ing_key == "pork":
            sub["dietary_substitute"] = "Chicken thigh (halal-certified)"
        if skill_level == "beginner" and not entry.get("dietary_flags"):
            pass
        subs.append(sub)
    return subs


def build_milestones(skill_level, dish) -> list[dict]:
    """Return the visual + aroma milestones for the chosen skill level + dish."""
    if not skill_level:
        return []
    strategy = _SKILL_STRATEGY.get(skill_level, {})
    visual = strategy.get("visual_milestones", [])
    aroma = strategy.get("aroma_milestones", [])
    combined = []
    for v in visual:
        combined.append({"type": "visual", "milestone": v})
    for a in aroma:
        combined.append({"type": "aroma", "milestone": a})
    return combined


def build_recipe_blueprint(dish, skill_level, sourcing_track, servings, dietary, time_budget) -> dict:
    """Compose a small recipe blueprint the agent fills in with subjective detail."""
    template = _RECIPE_TEMPLATES.get(dish, {})
    servings_per_unit = template.get("servings_per_ingredient_unit", 2)
    scale = servings / servings_per_unit
    ingredients = []
    for ing_key in template.get("core_ingredients", []):
        entry = _INGREDIENT_DICT.get(ing_key, {})
        ingredients.append({
            "key": ing_key,
            "label": entry.get("sg_name", ing_key.title()),
            "scale": scale,
        })
    return {
        "dish": dish,
        "category": template.get("category", "uncategorised"),
        "servings": servings,
        "scale": round(scale, 2),
        "ingredient_count": len(ingredients),
        "ingredients": ingredients,
        "skill_note": template.get("skill_notes", {}).get(skill_level, ""),
        "dietary_flags": template.get("dietary", []),
    }


def build_report(args) -> dict:
    """Compose the JSON report the agent consumes."""
    dish_raw = args.dish or ""
    dish = _normalise_dish(dish_raw)
    skill_level = _resolve_skill_level(getattr(args, "skill_level", None))
    sourcing_track = _resolve_sourcing(getattr(args, "sourcing_track", None))
    dietary = _resolve_dietary(getattr(args, "dietary", None))
    servings = _parse_servings(getattr(args, "servings", None))
    time_budget = _parse_time_budget(getattr(args, "time_budget", None))

    params_complete, missing, errors = check_params(
        dish_raw, skill_level, sourcing_track, dietary, servings, time_budget
    )

    warnings = build_warnings(dish, skill_level, sourcing_track, dietary, time_budget)
    skill_strategy = build_skill_strategy(skill_level)
    sourcing_strategy = build_sourcing_strategy(sourcing_track)
    ingredient_subs = build_ingredient_substitutions(dish, dietary, skill_level)
    milestones = build_milestones(skill_level, dish)
    recipe = build_recipe_blueprint(dish, skill_level, sourcing_track, servings, dietary, time_budget)

    return {
        "origin": "Singapore (HDB / condo kitchen)",
        "dish": dish or None,
        "dish_raw": dish_raw or None,
        "skill_level": skill_level,
        "sourcing_track": sourcing_track,
        "dietary": dietary,
        "servings": servings,
        "time_budget_minutes": time_budget,
        "skill_strategy": skill_strategy,
        "sourcing_strategy": sourcing_strategy,
        "ingredient_substitutions": ingredient_subs,
        "milestones": milestones,
        "recipe_blueprint": recipe,
        "params_complete": params_complete,
        "missing_params": missing,
        "errors": errors,
        "warnings": warnings,
    }


# ------------------------------------------------------------------- CLI ----

def main(argv=None):
    p = argparse.ArgumentParser(
        description="SG Home Chef — Singapore home-cooking concierge helpers (3 skill tiers + 2 sourcing tracks).",
    )
    p.add_argument("--dish", help="The dish to cook, e.g. 'Sambal Kang Kong' or 'Laksa'.")
    p.add_argument("--skill-level", help="Cook's skill level (beginner / intermediate / advanced).")
    p.add_argument("--sourcing-track", help="Where to source ingredients (supermarket / wet-market).")
    p.add_argument("--dietary", help="Dietary preference (none / halal / vegetarian / vegan / no-beef / no-pork / gluten-free).")
    p.add_argument("--servings", help="Number of servings (1-20).")
    p.add_argument("--time-budget", help="Total time budget in minutes (5-240).")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = p.parse_args(argv)

    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["params_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
