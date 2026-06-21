#!/usr/bin/env python3
"""
CDC Voucher Locator — standalone helper script.
Called by the agent skill. Caches data to ~/.hermes/cache/cdc-vouchers/
"""
import gzip, json, os, re, sys, urllib.request, urllib.error, urllib.parse
from math import radians, sin, cos, sqrt, asin
from datetime import datetime, timezone
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────
CDN_BASE = "https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere"
FILES = {
    "hawkers": {"url": f"{CDN_BASE}/data.gzip?v=2", "local": "data.gzip"},
    "supermarkets": {"url": f"{CDN_BASE}/data_supermarket.json?v=2", "local": "data_supermarket.json"},
}
CACHE_DIR = Path.home() / ".hermes" / "cache" / "cdc-vouchers"
DEFAULT_RADIUS = 500      # metres
MIN_RESULTS = 5           # if any category has fewer, expand
MAX_RADIUS = 1000         # cap at 1km auto-expand

# ── Food keywords (Mode B) ─────────────────────────────────────────
FOOD_KW = [
    "food","noodle","rice","chicken","fish","soup","restaurant","cafe",
    "bakery","grill","curry","kopi","coffee","tea","dessert","ice cream",
    "snack","prata","roti","cake","kitchen","bistro","bbq","ban mian",
    "porridge","laksa","mee","hokkien","pizza","burger","seafood",
    "steamboat","sushi","ramen","dim sim","catering","stall","food house",
    "roasted","roast","drink","drinks","mixed rice","vegetarian",
    "western","tomyam","fishball","bak kut teh","yong tau foo",
    "rojak","muffin","pancake","donut","waffle","nasi","ayam","soto",
    "goreng","sambal","telur","kueh","餐","饭","面","水","菜","鸡","鱼",
    "汤","包","饼","糕","咖啡","茶","冰","热",
]
NOT_FOOD = [
    "beauty","salon","hair","nail","spa","facial","mobile",
    "phone","electronics","dental","clinic","pharmacy","tcm",
    "optical","fashion","furniture","hardware","laundry",
    "printing","tailor","jewellery","gift","watch","shoe",
    "repair","plumbing","training","tuition","insurance",
]

# ── Sub-category rules (Mode A generic) ────────────────────────────
SUPERMARKET_NAMES = [
    "ntuc fairprice","giant","sheng siong","cold storage",
    "ang mo supermarket","prime supermarket","hao mart",
    "u star","shengsiong",
]

CAT_RULES = [
    ("🍽 F&B / Dining", [
        "food","noodle","chicken rice","fish soup","bak kut teh",
        "restaurant","cafe","bakery","grill","curry","dim sum",
        "kopi","tea","coffee","dessert","ice cream","prata","roti",
        "cake","kitchen","bistro","bbq","brew","ban mian","porridge",
        "laksa","mee","pizza","burger","seafood","steamboat","sushi",
        "ramen","catering","nasi","ayam","goreng","kueh","rojak",
        "餐","饭","面","水","菜","鸡","鱼","汤","包","饼","糕",
    ]),
    ("💇 Beauty & Personal Care", [
        "beauty","salon","hair","nail","spa","facial","barber",
        "lash","brow","makeup","manicure","pedicure","waxing",
        "cosmetic","perfume","fragrance","grooming","aesthetic",
    ]),
    ("🏥 Health & Medical", [
        "dental","clinic","tcm","physician","pharmacy","medical",
        "optical","dentist","physio","hearing","therapeutic",
        "wellness","nursing","therapy","中药","中医","诊疗",
    ]),
    ("🛍 Shopping & Retail", [
        "fashion","apparel","boutique","tailor","jewellery","jewelry",
        "gift","mobile","phone","electronics","computer","dollar",
        "mart","minimart","grocery","fruit","vegetable","supermarket",
        "fresh","watch","shoes","bag","accessory","sport","toy",
        "book","stationery","provision","convenience","trading",
        "服装","鞋","手机","超市",
    ]),
    ("🏠 Home & Living", [
        "furniture","home","kitchen","hardware","household",
        "renovation","curtain","lighting","appliance","bedding",
        "linen","carpet","tile","paint","家具","五金","家装",
    ]),
    ("⚡ Services", [
        "laundry","printing","travel","insurance","tuition",
        "learning","repair","service","transport","logistics",
        "education","photocopy","alteration","plumbing",
        "training","workshop","courier","delivery",
        "服务","洗衣","打印",
    ]),
]

# ── Helpers ─────────────────────────────────────────────────────────

from singapore_api import haversine_m  # noqa: E402  (shared via sync script)

def clean_addr(a):
    return a.rstrip(';').replace(';', ', ')

def is_food(name):
    """Check if merchant name is food-related (Mode B)."""
    nl = name.lower()
    for nf in NOT_FOOD:
        if nf in nl:
            return False
    for kw in FOOD_KW:
        if kw in nl:
            return True
    return False

def categorize(name):
    """Categorize merchant name into sub-category (Mode A generic)."""
    nl = name.lower()
    for sn in SUPERMARKET_NAMES:
        if sn in nl:
            return "🏪 Supermarkets"
    for cat, keywords in CAT_RULES:
        if any(k in nl for k in keywords):
            return cat
    return "🗂 Other"

# ── Data fetching with caching ──────────────────────────────────────

def get_last_modified(url):
    """Fetch Last-Modified header without downloading full body."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.headers.get("Last-Modified")
    except Exception:
        return None

def fetch_data():
    """Download data files only if cache is stale or missing."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    for key, info in FILES.items():
        local_path = CACHE_DIR / info["local"]
        last_mod = get_last_modified(info["url"])

        download = True
        if local_path.exists():
            # Check if live file has same last-modified
            cached_mod = (local_path.stat().st_mtime)
            if last_mod:
                try:
                    live_dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                    cached_dt = datetime.fromtimestamp(cached_mod, tz=timezone.utc)
                    if live_dt <= cached_dt:
                        download = False
                except ValueError:
                    pass  # parse failed, re-download to be safe

        if download:
            print(f"  Downloading {key}...", file=sys.stderr)
            urllib.request.urlretrieve(info["url"], local_path)

        # Read
        if info["local"].endswith(".gz") or info["local"].endswith(".gzip"):
            with gzip.open(local_path, "rt") as f:
                results[key] = json.load(f)
        else:
            with open(local_path) as f:
                results[key] = json.load(f)

    return results

# ── Geocoding ───────────────────────────────────────────────────────

def geocode(query):
    """Resolve a place name / postal code to (lat, lon, postal, address)."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={encoded}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return None, f"Geocode failed: {e}"

    results = data.get("results", [])
    if not results:
        return None, "No geocoding results found"

    # Prefer exact match on building name if one matches query
    ql = query.lower()
    for r in results:
        building = r.get("BUILDING", "").lower()
        if ql in building or building in ql:
            return (
                float(r["LATITUDE"]),
                float(r["LONGITUDE"]),
                r["POSTAL"],
                r["ADDRESS"],
            )

    # Fallback: first result
    r = results[0]
    return (
        float(r["LATITUDE"]),
        float(r["LONGITUDE"]),
        r.get("POSTAL", ""),
        r["ADDRESS"],
    )

# ── Main lookup ─────────────────────────────────────────────────────

def lookup(query, mode="A", radius=DEFAULT_RADIUS):
    """
    Main entry point.
    mode: A=generic, B=food, C=supermarkets, D=budget meal
    Returns dict with all data for the agent to format.
    """
    # 1. Geocode
    geo = geocode(query)
    if geo[0] is None:
        return {"error": geo[1]}

    lat, lon, postal, address = geo

    # 2. Fetch data
    data = fetch_data()

    last_updated = data["hawkers"].get("lastUpdated", data["supermarkets"].get("lastUpdated", ""))

    # 3. Filter hawkers by distance
    hawker_results = []
    for loc in data["hawkers"]["locations"]:
        d = haversine_m(lat, lon, loc["LAT"], loc["LON"])
        if d is not None and d <= radius:
            hawker_results.append((d, loc))

    # 4. Filter supermarkets by distance
    super_results = []
    for loc in data["supermarkets"]["locations"]:
        d = haversine_m(lat, lon, loc["LAT"], loc["LON"])
        if d is not None and d <= radius:
            super_results.append((d, loc))

    # 5. Auto-expand radius if too few results
    actual_radius = radius
    if mode in ("A", "B", "D"):
        count = len(hawker_results)
        if mode == "B":
            count = sum(1 for _, l in hawker_results if is_food(l["name"]))
        if count < MIN_RESULTS and radius < MAX_RADIUS:
            new_radius = min(MAX_RADIUS, radius * 2)
            # Re-check for hawkers
            new_h = []
            for loc in data["hawkers"]["locations"]:
                d = haversine_m(lat, lon, loc["LAT"], loc["LON"])
                if d is not None and d <= new_radius:
                    new_h.append((d, loc))
            hawker_results = new_h
            # Re-check for supermarkets
            new_s = []
            for loc in data["supermarkets"]["locations"]:
                d = haversine_m(lat, lon, loc["LAT"], loc["LON"])
                if d is not None and d <= new_radius:
                    new_s.append((d, loc))
            super_results = new_s
            actual_radius = new_radius

    hawker_results.sort(key=lambda x: x[0])
    super_results.sort(key=lambda x: x[0])

    # 6. Build output
    result = {
        "location": address,
        "postal": postal,
        "lat": lat,
        "lon": lon,
        "last_updated": last_updated,
        "radius": actual_radius,
        "mode": mode,
        "supermarkets": [{"name": l["name"], "address": clean_addr(l["address"]), "dist_m": d} for d, l in super_results],
    }

    if mode == "C":
        # Supermarkets only
        return result

    # Process hawkers
    budget_meal = []
    if mode == "B":
        # Food only
        food_results = [(d, l) for d, l in hawker_results if is_food(l["name"])]
        budget_meal = [(d, l) for d, l in food_results if l.get("filters", {}).get("secondary", {}).get("budgetmeal")]
        result["food_places"] = [{"name": l["name"], "address": clean_addr(l["address"]), "dist_m": d, "budget": l.get("filters", {}).get("secondary", {}).get("budgetmeal", False)} for d, l in food_results]
    elif mode == "D":
        # Budget meal only
        budget_meal = [(d, l) for d, l in hawker_results if l.get("filters", {}).get("secondary", {}).get("budgetmeal")]
        result["budget_meal"] = [{"name": l["name"], "address": clean_addr(l["address"]), "dist_m": d} for d, l in budget_meal]
    else:
        # Mode A: generic — sub-categorize
        budget_meal = [(d, l) for d, l in hawker_results if l.get("filters", {}).get("secondary", {}).get("budgetmeal")]
        cats = {}
        for d, l in hawker_results:
            cat = categorize(l["name"])
            if cat not in cats:
                cats[cat] = []
            cats[cat].append({"name": l["name"], "address": clean_addr(l["address"]), "dist_m": d})
        result["hawker_categories"] = cats
        result["budget_meal"] = [{"name": l["name"], "address": clean_addr(l["address"]), "dist_m": d} for d, l in budget_meal]

    result["budget_meal_count"] = len(budget_meal)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: cdc_voucher_locator.py '<query>' [mode=A|B|C|D] [radius=500]"}))
        sys.exit(1)

    query = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "A"
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_RADIUS

    result = lookup(query, mode, radius)
    print(json.dumps(result, indent=2))