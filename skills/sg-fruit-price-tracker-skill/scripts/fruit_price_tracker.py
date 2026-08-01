"""SG Fruit Price Tracker — Cold Storage + FairPrice scraper (stdlib only).

Crawls 30 common + exotic fruits across:
  - Cold Storage (https://coldstorage.com.sg/) — aria-label regex on search pages
  - FairPrice (https://www.fairprice.com.sg/) — HTML parse on /category/fruits
  - Sheng Siong (https://shengsiong.com.sg/) — Meteor SPA, logged as unavailable
    (the agent should fall back to web_search at runtime for that retailer)

Emits CSV (default) or JSON (--json) to stdout. Stdlib only. No subprocess.
No shell pipes. Cron-safe.

Usage:
    python3 fruit_price_tracker.py --all
    python3 fruit_price_tracker.py --fruit mango
    python3 fruit_price_tracker.py --retailer fairprice --fruit apple
    python3 fruit_price_tracker.py --json
    python3 fruit_price_tracker.py --offline

Exit codes:
    0 = all requested retailers returned data
    1 = all requested retailers failed
    2 = partial success (some OK, some failed)
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"

CACHE_DIR = Path.home() / ".hermes" / "cache" / "sg-fruit-prices"
CACHE_TTL_SECONDS = 3600
HTTP_TIMEOUT_SECONDS = 10
USER_AGENT = "sg-fruit-price-tracker/2.0 (+cron; hermes-skill)"

COLDSTORAGE_SEARCH = "https://coldstorage.com.sg/search?q={q}"
FAIRPRICE_FRUITS_CATEGORY = "https://www.fairprice.com.sg/category/fruits"

# 30 curated fruits: common + exotic. Each maps to search keywords.
TARGET_FRUITS: dict[str, list[str]] = {
    "apple":          ["apple", "fuji", "gala", "granny"],
    "banana":         ["banana", "cavendish"],
    "orange":         ["orange", "mandarin", "valencia"],
    "mango":          ["mango", "susu", "harum manis"],
    "durian":         ["durian", "musang king", "mao shan"],
    "dragon_fruit":   ["dragon fruit", "pitaya"],
    "rambutan":       ["rambutan"],
    "mangosteen":     ["mangosteen"],
    "papaya":         ["papaya", "pawpaw"],
    "watermelon":     ["watermelon", "seedless"],
    "pineapple":      ["pineapple", "md2"],
    "lychee":         ["lychee", "lychees"],
    "longan":         ["longan"],
    "jackfruit":      ["jackfruit", "nangka"],
    "pomelo":         ["pomelo", "limau bali"],
    "pear":           ["pear", "ya li", "crystal"],
    "peach":          ["peach", "donut peach"],
    "plum":           ["plum", "japanese plum"],
    "strawberry":     ["strawberry", "strawberries"],
    "blueberry":      ["blueberry", "blueberries"],
    "raspberry":      ["raspberry", "raspberries"],
    "cherry":         ["cherry", "cherries"],
    "grape":          ["grape", "grapes", "kyoho"],
    "kiwi":           ["kiwi", "kiwifruit", "zespri"],
    "lemon":          ["lemon", "meyer"],
    "lime":           ["lime", "limau nipis"],
    "persimmon":      ["persimmon", "fuyu"],
    "pomegranate":    ["pomegranate"],
    "guava":          ["guava", "jambu"],
    "star_fruit":     ["star fruit", "carambola"],
}

RETAILERS = ("cold_storage", "fairprice", "sheng_siong")

# 70+ exclusion keywords. False positives (real fruit blocked) are recoverable;
# false negatives (yoghurt-with-fruit in the name sneaking through) pollute
# the report. Err on the side of exclusion.
EXCLUDE_KEYWORDS = [
    "juice", "drink", "beverage", "soda", "soft drink", "energy drink",
    "yoghurt", "yogurt", "kefir", "lassi",
    "snack", "candy", "chocolate", "gummy", "jelly", "marshmallow",
    "jam", "preserve", "spread", "marmalade", "compote",
    "dried", "candied", "crystallised", "freeze-dried",
    "canned", "tinned", "jar", "bottled",
    "frozen", "frosted", "iced", "ice",
    "tea", "tisane", "infusion", "kombucha",
    "wine", "liqueur", "spirit", "sake", "soju", "cider", "mead",
    "soap", "shampoo", "conditioner", "lotion", "cream", "serum",
    "perfume", "cologne", "candle", "diffuser", "sachet",
    "lip balm", "lip butter", "face", "skin", "hair", "body",
    "mask", "scrub", "exfoliat", "toner", "mist", "splash",
    "supplement", "vitamin", "collagen", "probiotic",
    "toiletry", "toiletries", "detergent", "cleaner", "disinfect",
    "scented", "flavoured", "flavored", "infused",
    "bar", "cake", "cookie", "biscuit", "wafer", "pudding", "gelatin",
    "filling", "topping", "syrup", "sauce", "puree",
    "mochi", "dango", "tangyuan",
    "voucher", "gift card", "coupon", "promo code",
    "recipe", "kit", "platter", "hamper",
    "floral", "bouquet", "potpourri",
    "plant", "seedling", "sapling", "cutting",
    "essential oil", "extract", "tincture",
    "milk", "formula", "baby",
    "pet", "dog", "cat", "bird",
    "non-food", "merchandise",
    "sku",
    "cider vinegar", "capsule", "tablet",
]

EXCLUDE_RE = re.compile(
    r"(?:" + "|".join(re.escape(k) for k in EXCLUDE_KEYWORDS) + r")",
    re.IGNORECASE,
)

# -- Cold Storage regexes --
CS_ARIA_RE = re.compile(r'aria-label="([^"]+)"')
CS_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
CS_RATING_RE = re.compile(r'data-rating="(\d+(?:\.\d)?)"')
CS_REVIEW_RE = re.compile(r'data-reviews="(\d+)"')

# -- FairPrice regexes --
# Product URL slug: /product/{slug}-{id}
FP_PRODUCT_RE = re.compile(r'href="/product/([a-z0-9-]+)"')
# Product name: inside data-testid="product-name-and-metadata"
FP_NAME_RE = re.compile(
    r'data-testid="product-name-and-metadata"[^>]*>.*?'
    r'<span[^>]*weight="normal"[^>]*>([^<]+)</span>',
    re.DOTALL,
)
# Weight: next sibling span with color #666666
FP_WEIGHT_RE = re.compile(
    r'product-name-and-metadata"[^>]*>.*?'
    r'<span[^>]*color="#666666"[^>]*>([^<]+)</span>',
    re.DOTALL,
)
# Price: span with weight="black" containing $X.XX
FP_PRICE_RE = re.compile(
    r'<span[^>]*weight="black"[^>]*>\$\s*(\d+(?:\.\d{1,2})?)</span>'
)
# Original price (promo): aria-label="Original price" + $X.XX nearby
FP_ORIGINAL_PRICE_RE = re.compile(
    r'aria-label="Original price"[^<]*<[^>]+>\$\s*(\d+(?:\.\d{1,2})?)</span>'
)
# Rating: aria-label="Average rating is X.X"
FP_RATING_RE = re.compile(r'aria-label="Average rating is (\d+(?:\.\d)?)"')

WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(g|gram|grams|kg)\b", re.IGNORECASE)

MIN_PRICE_SGD = 0.50
MAX_PRICE_SGD = 200.0


# --------------------------------------------------------------- network --

def _http_get(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                text = body.decode("utf-8", errors="replace")
            except Exception:
                text = body.decode("latin-1", errors="replace")
            return resp.status, text
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError as e:
        return 0, f"URLError: {e.reason}"
    except (TimeoutError, OSError) as e:
        return 0, f"network error: {e}"


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _cache_path(url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_cache_key(url)}.html"


def _cache_is_fresh(path: Path, ttl: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl


def fetch(url: str, *, offline: bool = False, ttl: int = CACHE_TTL_SECONDS) -> tuple[int, str]:
    """Fetch a URL, using a 1-hour disk cache. Returns (status, html)."""
    cache_p = _cache_path(url)
    if _cache_is_fresh(cache_p, ttl):
        try:
            return 200, cache_p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    if offline:
        if cache_p.exists():
            return 200, cache_p.read_text(encoding="utf-8", errors="replace")
        return 0, "offline mode + no cache"
    status, body = _http_get(url)
    if status == 200 and body:
        try:
            cache_p.write_text(body, encoding="utf-8")
        except OSError:
            pass
    return status, body


# --------------------------------------------------------------- helpers --

def normalize_name(name: str) -> str:
    n = name.lower()
    n = WEIGHT_RE.sub("", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def is_blocked(name: str) -> bool:
    return bool(EXCLUDE_RE.search(name))


def parse_price(text: str) -> float | None:
    if not text:
        return None
    m = CS_PRICE_RE.search(text)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except (ValueError, AttributeError):
        return None
    if v < MIN_PRICE_SGD or v > MAX_PRICE_SGD:
        return None
    return round(v, 2)


def parse_weight(name: str) -> int | None:
    m = WEIGHT_RE.search(name)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    grams = n * 1000 if unit.startswith("kg") else n
    return int(grams)


def fruit_matches(name: str, fruit_keys: list[str]) -> bool:
    """Check if a product name matches any of the given fruit keys."""
    n = name.lower()
    for k in fruit_keys:
        for kw in TARGET_FRUITS.get(k, [k]):
            if kw in n:
                return True
    return False


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------- Cold Storage --

def parse_cold_storage(html: str, fruit_keys: list[str]) -> list[dict]:
    """Extract product dicts from Cold Storage HTML for the given fruit keys."""
    if not html:
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for m in CS_ARIA_RE.finditer(html):
        name = m.group(1).strip()
        if not name:
            continue
        if is_blocked(name):
            continue
        if not fruit_matches(name, fruit_keys):
            continue
        start = m.end()
        first_close = html.find("</div>", start)
        if first_close != -1:
            second_close = html.find("</div>", first_close + 6)
            if second_close != -1 and second_close - start < 500:
                end = second_close + 6
            else:
                end = min(len(html), start + 250)
        else:
            end = min(len(html), start + 250)
        chunk = html[start:end]
        prices = CS_PRICE_RE.findall(chunk)
        if not prices:
            continue
        price_vals: list[float] = []
        for p in prices[:2]:
            try:
                v = float(p)
            except (ValueError, TypeError):
                continue
            if MIN_PRICE_SGD <= v <= MAX_PRICE_SGD:
                price_vals.append(round(v, 2))
        if not price_vals:
            continue
        promo = False
        original = None
        price_sgd = price_vals[0]
        if len(price_vals) >= 2 and price_vals[1] < price_vals[0]:
            promo = True
            original = price_vals[0]
            price_sgd = price_vals[1]
        rating_m = CS_RATING_RE.search(chunk)
        review_m = CS_REVIEW_RE.search(chunk)
        norm = normalize_name(name)
        if norm in seen:
            continue
        seen.add(norm)
        fruit_key = fruit_keys[0] if fruit_keys else ""
        out.append({
            "retailer": "cold_storage",
            "name": name,
            "weight_g": parse_weight(name),
            "price_sgd": price_sgd,
            "original_price_sgd": original,
            "promo": promo,
            "rating": float(rating_m.group(1)) if rating_m else None,
            "review_count": int(review_m.group(1)) if review_m else None,
            "url": COLDSTORAGE_SEARCH.format(q=urllib.parse.quote(fruit_key)),
            "scraped_at": now_iso(),
        })
    return out


# --------------------------------------------------------------- FairPrice --

def parse_fairprice(html: str, fruit_keys: list[str]) -> list[dict]:
    """Extract product dicts from FairPrice /category/fruits HTML."""
    if not html or 'data-testid="product-name-and-metadata"' not in html:
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for m in FP_PRODUCT_RE.finditer(html):
        slug = m.group(1)
        anchor_end = m.end()
        # Walk forward up to 1500 chars to find the product card content.
        end = min(len(html), anchor_end + 1500)
        chunk = html[anchor_end:end]
        name_m = FP_NAME_RE.search(chunk)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        if not name or is_blocked(name):
            continue
        if not fruit_matches(name, fruit_keys):
            continue
        weight_m = FP_WEIGHT_RE.search(chunk)
        weight_str = weight_m.group(1).strip() if weight_m else None
        weight_g = parse_weight(weight_str) if weight_str else None
        # Find prices in this card. First $X.XX = current price; if there's
        # an "Original price" aria-label, the price inside it is the was-price.
        prices = FP_PRICE_RE.findall(chunk)
        if not prices:
            continue
        price_vals: list[float] = []
        for p in prices[:2]:
            try:
                v = float(p)
            except (ValueError, TypeError):
                continue
            if MIN_PRICE_SGD <= v <= MAX_PRICE_SGD:
                price_vals.append(round(v, 2))
        if not price_vals:
            continue
        original_m = FP_ORIGINAL_PRICE_RE.search(chunk)
        original = None
        promo = False
        price_sgd = price_vals[0]
        if original_m:
            try:
                original = round(float(original_m.group(1)), 2)
                if MIN_PRICE_SGD <= original <= MAX_PRICE_SGD and original > price_sgd:
                    promo = True
            except (ValueError, TypeError):
                original = None
        rating_m = FP_RATING_RE.search(chunk)
        norm = normalize_name(name)
        if norm in seen:
            continue
        seen.add(norm)
        out.append({
            "retailer": "fairprice",
            "name": name,
            "weight_g": weight_g,
            "price_sgd": price_sgd,
            "original_price_sgd": original,
            "promo": promo,
            "rating": float(rating_m.group(1)) if rating_m else None,
            "review_count": None,  # FairPrice doesn't expose review count in HTML
            "url": f"https://www.fairprice.com.sg/product/{slug}",
            "scraped_at": now_iso(),
        })
    return out


# --------------------------------------------------------------- Sheng Siong --

def scrape_sheng_siong() -> list[dict]:
    """Sheng Siong is a Meteor SPA. urllib returns empty. Always unavailable."""
    return []


# --------------------------------------------------------------- retailers --

def scrape_cold_storage(fruit_keys: list[str], *, offline: bool = False) -> tuple[str, list[dict] | str]:
    fruit_key = fruit_keys[0] if fruit_keys else ""
    url = COLDSTORAGE_SEARCH.format(q=urllib.parse.quote(fruit_key))
    status, body = fetch(url, offline=offline)
    if status != 200 or not body:
        return "cold_storage", f"unavailable: http_status_{status}"
    records = parse_cold_storage(body, fruit_keys)
    if not records:
        return "cold_storage", "unavailable: 0_matches"
    return "cold_storage", records


def scrape_fairprice(fruit_keys: list[str], *, offline: bool = False) -> tuple[str, list[dict] | str]:
    """FairPrice: one category-page fetch covers all 30 fruits. Filter by fruit_keys."""
    status, body = fetch(FAIRPRICE_FRUITS_CATEGORY, offline=offline)
    if status != 200 or not body:
        return "fairprice", f"unavailable: http_status_{status}"
    records = parse_fairprice(body, fruit_keys)
    if not records:
        return "fairprice", "unavailable: 0_matches_or_unrendered"
    return "fairprice", records


def scrape_sheng_siong_wrapper(fruit_keys: list[str]) -> tuple[str, list[dict] | str]:
    """Sheng Siong is a Meteor SPA. urllib can't extract. Always unavailable.
    The agent should run web_search at runtime and inject results separately."""
    _ = fruit_keys
    return "sheng_siong", "unavailable: meteor_spa"


def scrape_all(
    fruit_keys: list[str],
    *,
    retailers: list[str] | None = None,
    offline: bool = False,
) -> list[dict]:
    retailers = retailers or list(RETAILERS)
    out: list[dict] = []
    failed: list[str] = []
    for r in retailers:
        if r == "cold_storage":
            retailer, payload = scrape_cold_storage(fruit_keys, offline=offline)
        elif r == "fairprice":
            retailer, payload = scrape_fairprice(fruit_keys, offline=offline)
        elif r == "sheng_siong":
            retailer, payload = scrape_sheng_siong_wrapper(fruit_keys)
        else:
            continue
        if isinstance(payload, list):
            out.extend(payload)
        else:
            failed.append(f"{retailer}:{payload}")
    if failed and not out:
        raise RuntimeError("all retailers failed: " + "; ".join(failed))
    if failed:
        print("# partial-failure:", *failed, file=sys.stderr)
    return out


# --------------------------------------------------------------- CSV/JSON --

CSV_COLUMNS = [
    "retailer", "name", "weight_g", "price_sgd", "original_price_sgd",
    "promo", "rating", "review_count", "url", "scraped_at",
]


def emit_csv(records: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in records:
        w.writerow(r)
    return buf.getvalue()


def emit_json(records: list[dict]) -> str:
    return json.dumps(records, indent=2, ensure_ascii=False)


# --------------------------------------------------------------- cleanup --

def cleanup_old_csvs(out_dir: Path, keep: int = 7) -> int:
    """Delete CSV files older than the newest `keep` files."""
    if not out_dir.exists():
        return 0
    files = sorted(
        out_dir.glob("fruit-prices-*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    deleted = 0
    for f in files[keep:]:
        try:
            f.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted


# --------------------------------------------------------------- CLI ----

def main(argv=None):
    p = argparse.ArgumentParser(
        description="SG Fruit Price Tracker — Cold Storage + FairPrice scraper (stdlib only).",
    )
    fruit = p.add_mutually_exclusive_group(required=True)
    fruit.add_argument(
        "--fruit", choices=list(TARGET_FRUITS.keys()),
        help="Single target fruit (one of 30 curated).",
    )
    fruit.add_argument(
        "--all", action="store_true",
        help="All 30 target fruits.",
    )
    p.add_argument(
        "--retailer", default="all",
        help="Comma-sep retailers: cold_storage,fairprice,sheng_siong (default: all).",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit JSON to stdout (default: CSV).",
    )
    p.add_argument(
        "--offline", action="store_true",
        help="Use cache only — no network.",
    )
    p.add_argument(
        "--cleanup", type=Path, default=None,
        help="Cleanup old CSVs in this directory (keeps 7 most recent).",
    )
    args = p.parse_args(argv)

    if args.all:
        fruits = list(TARGET_FRUITS.keys())
    else:
        fruits = [args.fruit]

    if args.retailer == "all":
        retailers = list(RETAILERS)
    else:
        retailers = [r.strip() for r in args.retailer.split(",") if r.strip()]
        for r in retailers:
            if r not in RETAILERS:
                print(f"# unknown retailer: {r}", file=sys.stderr)
                return 1

    try:
        records = scrape_all(fruits, retailers=retailers, offline=args.offline)
    except RuntimeError as e:
        print(f"# error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(emit_json(records))
    else:
        print(emit_csv(records), end="")

    if args.cleanup is not None:
        deleted = cleanup_old_csvs(args.cleanup, keep=7)
        if deleted:
            print(f"# cleanup: deleted {deleted} old CSV(s)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
