#!/usr/bin/env python3
"""Hawker + CDC Voucher + Open-Now Locator.

Calls cdc-voucher-locator-skill as a subprocess (rather than importing it)
so each skill stays self-contained on `npx skills add --skill X` install.
Subprocess result is intersected with NEA's hawker-centre closure list to
add per-merchant `open_now` and `next_closure` fields.
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import singapore_api

# ── Config ─────────────────────────────────────────────────────────
SKILL_DIR = Path(__file__).resolve().parent
CDC_SCRIPT = (
    SKILL_DIR.parent.parent
    / "cdc-voucher-locator-skill"
    / "scripts"
    / "cdc_voucher_locator.py"
)
DEFAULT_RADIUS = 500
HAWKER_MATCH_RADIUS_M = 50

# ── Pure helpers (inlined; pure logic, not API code) ───────────────

def _haversine_m(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return round(R * c)


# Inlined from cdc_voucher_locator.py. These are pure-string-classification
# helpers, not API code. They are duplicated here so hawker-discover works
# when the CDC script is not importable (e.g. installed in isolation).
# A parity test (test_helpers_match_cdc) keeps them in sync.
_FOOD_KW = [
    "food", "noodle", "rice", "chicken", "fish", "soup", "restaurant", "cafe",
    "bakery", "grill", "curry", "kopi", "coffee", "tea", "dessert", "ice cream",
    "snack", "prata", "roti", "cake", "kitchen", "bistro", "bbq", "ban mian",
    "porridge", "laksa", "mee", "hokkien", "pizza", "burger", "seafood",
    "steamboat", "sushi", "ramen", "dim sim", "catering", "stall", "food house",
    "roasted", "roast", "drink", "drinks", "mixed rice", "vegetarian",
    "western", "tomyam", "fishball", "bak kut teh", "yong tau foo",
    "rojak", "muffin", "pancake", "donut", "waffle", "nasi", "ayam", "soto",
    "goreng", "sambal", "telur", "kueh", "餐", "饭", "面", "水", "菜", "鸡", "鱼",
    "汤", "包", "饼", "糕", "咖啡", "茶", "冰", "热",
]
_NOT_FOOD = [
    "beauty", "salon", "hair", "nail", "spa", "facial", "mobile",
    "phone", "electronics", "dental", "clinic", "pharmacy", "tcm",
    "optical", "fashion", "furniture", "hardware", "laundry",
    "printing", "tailor", "jewellery", "gift", "watch", "shoe",
    "repair", "plumbing", "training", "tuition", "insurance",
]
_SUPERMARKET_NAMES = [
    "ntuc fairprice", "giant", "sheng siong", "cold storage",
    "ang mo supermarket", "prime supermarket", "hao mart",
    "u star", "shengsiong",
]
_CAT_RULES = [
    ("🍽 F&B / Dining", [
        "food", "noodle", "chicken rice", "fish soup", "bak kut teh",
        "restaurant", "cafe", "bakery", "grill", "curry", "dim sum",
        "kopi", "tea", "coffee", "dessert", "ice cream", "prata", "roti",
        "cake", "kitchen", "bistro", "bbq", "brew", "ban mian", "porridge",
        "laksa", "mee", "pizza", "burger", "seafood", "steamboat", "sushi",
        "ramen", "catering", "nasi", "ayam", "goreng", "kueh", "rojak",
        "餐", "饭", "面", "水", "菜", "鸡", "鱼", "汤", "包", "饼", "糕",
    ]),
    ("💇 Beauty & Personal Care", [
        "beauty", "salon", "hair", "nail", "spa", "facial", "barber",
        "lash", "brow", "makeup", "manicure", "pedicure", "waxing",
        "cosmetic", "perfume", "fragrance", "grooming", "aesthetic",
    ]),
    ("🏥 Health & Medical", [
        "dental", "clinic", "tcm", "physician", "pharmacy", "medical",
        "optical", "dentist", "physio", "hearing", "therapeutic",
        "wellness", "nursing", "therapy", "中药", "中医", "诊疗",
    ]),
    ("🛍 Shopping & Retail", [
        "fashion", "apparel", "boutique", "tailor", "jewellery", "jewelry",
        "gift", "mobile", "phone", "electronics", "computer", "dollar",
        "mart", "minimart", "grocery", "fruit", "vegetable", "supermarket",
        "fresh", "watch", "shoes", "bag", "accessory", "sport", "toy",
        "book", "stationery", "provision", "convenience", "trading",
        "服装", "鞋", "手机", "超市",
    ]),
    ("🏠 Home & Living", [
        "furniture", "home", "kitchen", "hardware", "household",
        "renovation", "curtain", "lighting", "appliance", "bedding",
        "linen", "carpet", "tile", "paint", "家具", "五金", "家装",
    ]),
    ("⚡ Services", [
        "laundry", "printing", "travel", "insurance", "tuition",
        "learning", "repair", "service", "transport", "logistics",
        "education", "photocopy", "alteration", "plumbing",
        "training", "workshop", "courier", "delivery",
        "服务", "洗衣", "打印",
    ]),
]


def is_food(name):
    """Mirrors cdc_voucher_locator.is_food. Parity tested."""
    nl = name.lower()
    for nf in _NOT_FOOD:
        if nf in nl:
            return False
    for kw in _FOOD_KW:
        if kw in nl:
            return True
    return False


def categorize(name):
    """Mirrors cdc_voucher_locator.categorize. Parity tested."""
    nl = name.lower()
    for sn in _SUPERMARKET_NAMES:
        if sn in nl:
            return "🏪 Supermarkets"
    for cat, keywords in _CAT_RULES:
        if any(k in nl for k in keywords):
            return cat
    return "🗂 Other"


# ── CDC subprocess + NEA intersection ──────────────────────────────

def invoke_cdc(query, mode, radius):
    """Run cdc_voucher_locator.py as a subprocess and parse its JSON output.

    Returns the parsed JSON dict, or a dict with key "error" on any failure.
    """
    proc = subprocess.run(
        ["python3", str(CDC_SCRIPT), query, mode, str(radius)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return {"error": "CDC lookup failed (exit %d): %s" % (proc.returncode, proc.stderr.strip())}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"error": "CDC returned invalid JSON: %s" % e}


def _is_closed_today(start, end, today_iso):
    if not start or not end:
        return False
    return start <= today_iso <= end


def attach_closure(merchants, hawker_centre_records, today_iso=None):
    """For each merchant, find the closest NEA hawker centre by haversine
    (within HAWKER_MATCH_RADIUS_M) and attach open_now + next_closure.

    Merchants with no nearby NEA centre get open_now=None (unknown).
    """
    if today_iso is None:
        today_iso = date.today().isoformat()
    annotated = []
    for m in merchants:
        mlat = m.get("LAT")
        mlon = m.get("LON")
        if mlat is None or mlon is None:
            m["open_now"] = None
            m["next_closure"] = None
            annotated.append(m)
            continue
        best = None
        for hc in hawker_centre_records:
            try:
                hclat = float(hc.get("lat", 0))
                hclon = float(hc.get("lon", 0))
            except (TypeError, ValueError):
                continue
            d = _haversine_m(mlat, mlon, hclat, hclon)
            if d is not None and d <= HAWKER_MATCH_RADIUS_M:
                if best is None or d < best[0]:
                    best = (d, hc)
        if best is not None:
            _, hc = best
            cs = hc.get("next_closure_start")
            ce = hc.get("next_closure_end")
            closed = _is_closed_today(cs, ce, today_iso)
            m["open_now"] = not closed
            m["next_closure"] = (
                {"start": cs, "end": ce, "reason": hc.get("closure_reason")}
                if cs and ce else None
            )
        else:
            m["open_now"] = None
            m["next_closure"] = None
        annotated.append(m)
    return annotated


def _extract_merchants_by_mode(cdc, mode):
    """Pull the merchant list out of CDC's mode-specific output shape."""
    if mode == "B":
        return list(cdc.get("food_places", []))
    if mode == "D":
        return list(cdc.get("budget_meal", []))
    if mode == "A":
        out = []
        for cat, items in cdc.get("hawker_categories", {}).items():
            for it in items:
                it["_category"] = cat
                out.append(it)
        return out
    return []


def assess(query, mode="A", radius=DEFAULT_RADIUS, _today_iso=None):
    """Public entry point: invoke CDC, intersect with NEA, return annotated JSON."""
    if mode == "C":
        return {"error": "Mode C is not applicable to hawker centres"}
    cdc = invoke_cdc(query, mode, radius)
    if "error" in cdc:
        return {
            "query": query,
            "mode": mode,
            "radius_m": radius,
            "results": [],
            "error": cdc["error"],
        }
    envelope = singapore_api.fetch_hawker_closures()
    records = (
        envelope.get("result", {}).get("records", [])
        if isinstance(envelope, dict) else []
    )
    merchants = _extract_merchants_by_mode(cdc, mode)
    annotated = attach_closure(merchants, records, _today_iso)
    return {
        "query": query,
        "postal": cdc.get("postal"),
        "location": cdc.get("location"),
        "mode": mode,
        "radius_m": cdc.get("radius", radius),
        "last_updated": cdc.get("last_updated"),
        "results": [
            {
                "name": m.get("name"),
                "address": m.get("address"),
                "distance_m": m.get("dist_m"),
                "category": m.get("_category"),
                "open_now": m.get("open_now"),
                "next_closure": m.get("next_closure"),
            }
            for m in annotated
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find hawker food that accepts CDC vouchers AND is open right now (not in quarterly cleaning)."
    )
    parser.add_argument("query", help="Postal code, town, or address in Singapore")
    parser.add_argument("mode", nargs="?", default="A", choices=["A", "B", "C", "D"],
                        help="Lookup mode: A=any, B=food, C=supermarket (N/A for hawkers), D=health")
    parser.add_argument("radius", nargs="?", type=int, default=DEFAULT_RADIUS, help="Search radius in metres")
    args = parser.parse_args(argv[1:] if argv else None)
    print(json.dumps(assess(args.query, args.mode, args.radius), indent=2))


if __name__ == "__main__":
    main()
