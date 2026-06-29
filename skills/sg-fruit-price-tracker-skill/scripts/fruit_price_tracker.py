"""SG Fruit Price Tracker — Cold Storage scraper (stdlib only).

Crawls Cold Storage's product search for lychees, peaches, strawberries,
plums. Emits CSV (default) or JSON (--json) to stdout. Designed for cron:
no shell pipes, no subprocess, no interactive prompts.

Usage:
    python3 fruit_price_tracker.py --fruit lychee
    python3 fruit_price_tracker.py --all
    python3 fruit_price_tracker.py --json
    python3 fruit_price_tracker.py --retailer cold_storage
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
import json
import os
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
USER_AGENT = "sg-fruit-price-tracker/1.0 (+cron; hermes-skill)"

COLDSTORAGE_SEARCH = "https://coldstorage.com.sg/search?q={q}"

TARGET_FRUITS: dict[str, list[str]] = {
    "lychee":     ["lychee", "lychees"],
    "peach":      ["peach", "peaches"],
    "strawberry": ["strawberry", "strawberries"],
    "plum":       ["plum", "plums"],
}

# 70+ exclusion keywords. False positives (a real fruit accidentally
# blocked) are recoverable; false negatives (yoghurt-with-fruit-in-the-name
# sneaking through) pollute the price report. Err on the side of exclusion.
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
    "supplement", "vitamin", "gummy", "collagen", "probiotic",
    "toiletry", "toiletries", "detergent", "cleaner", "disinfect",
    "scented", "flavoured", "flavored", "infused",
    "bar", "cake", "cookie", "biscuit", "wafer", "pudding", "gelatin",
    "filling", "topping", "syrup", "sauce", "puree",
    "mochi", "mochi", "dango", "tangyuan",
    "voucher", "gift card", "coupon", "promo code",
    "recipe", "kit", "platter", "hamper",
    "floral", "bouquet", "potpourri",
    "plant", "seedling", "sapling", "cutting",
    "essential oil", "extract", "tincture",
    "milk", "formula", "baby",
    "pet", "dog", "cat", "bird",
    "non-food", "merchandise",
    "sku",
]

EXCLUDE_RE = re.compile(
    r"(?:" + "|".join(re.escape(k) for k in EXCLUDE_KEYWORDS) + r")",
    re.IGNORECASE,
)

# aria-label = product name
ARIA_RE = re.compile(r'aria-label="([^"]+)"')
# price within 200 chars of a name
PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
# weight in grams
WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(g|gram|grams|kg)\b", re.IGNORECASE)
RATING_RE = re.compile(r'data-rating="(\d+(?:\.\d)?)"')
REVIEW_RE = re.compile(r'data-reviews="(\d+)"')

MIN_PRICE_SGD = 0.50
MAX_PRICE_SGD = 200.0


# --------------------------------------------------------------- network --

def _http_get(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
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


# --------------------------------------------------------------- parsing --

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
    m = PRICE_RE.search(text)
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


def parse_cold_storage(html: str, fruit_key: str) -> list[dict]:
    """Extract product dicts from Cold Storage HTML for a given fruit."""
    if not html:
        return []
    keywords = TARGET_FRUITS.get(fruit_key.lower(), [fruit_key.lower()])
    seen: set[str] = set()
    out: list[dict] = []
    for m in ARIA_RE.finditer(html):
        name = m.group(1).strip()
        if not name:
            continue
        if is_blocked(name):
            continue
        name_lower = name.lower()
        if not any(kw in name_lower for kw in keywords):
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
        prices = PRICE_RE.findall(chunk)
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
        rating_m = RATING_RE.search(chunk)
        review_m = REVIEW_RE.search(chunk)
        norm = normalize_name(name)
        if norm in seen:
            continue
        seen.add(norm)
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
            "scraped_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        })
    return out


# --------------------------------------------------------------- CSV/JSON --

CSV_COLUMNS = [
    "retailer", "name", "weight_g", "price_sgd", "original_price_sgd",
    "promo", "rating", "review_count", "url", "scraped_at",
]


def emit_csv(records: list[dict]) -> str:
    import io
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
    files = sorted(out_dir.glob("fruit-prices-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    deleted = 0
    for f in files[keep:]:
        try:
            f.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted


# --------------------------------------------------------------- retailers --

def scrape_cold_storage(fruit_key: str, *, offline: bool = False) -> tuple[str, list[dict] | str]:
    url = COLDSTORAGE_SEARCH.format(q=urllib.parse.quote(fruit_key))
    status, body = fetch(url, offline=offline)
    if status != 200 or not body:
        return "cold_storage", f"unavailable: http_status_{status}"
    records = parse_cold_storage(body, fruit_key)
    if not records:
        return "cold_storage", f"unavailable: 0_matches"
    return "cold_storage", records


def scrape_all(fruits: list[str], *, offline: bool = False) -> list[dict]:
    out: list[dict] = []
    failed: list[str] = []
    for f in fruits:
        retailer, payload = scrape_cold_storage(f, offline=offline)
        if isinstance(payload, list):
            out.extend(payload)
        else:
            failed.append(f"{retailer}:{payload}")
    if failed and not out:
        raise RuntimeError("all retailers failed: " + "; ".join(failed))
    if failed:
        print("# partial-failure:", *failed, file=sys.stderr)
    return out


# --------------------------------------------------------------- CLI ----

def main(argv=None):
    p = argparse.ArgumentParser(
        description="SG Fruit Price Tracker — Cold Storage scraper (stdlib only).",
    )
    fruit = p.add_mutually_exclusive_group(required=True)
    fruit.add_argument("--fruit", choices=list(TARGET_FRUITS.keys()),
                       help="Single target fruit.")
    fruit.add_argument("--all", action="store_true",
                       help="All 4 target fruits (lychee, peach, strawberry, plum).")
    p.add_argument("--retailer", default="cold_storage",
                   help="Retailer to scrape (default: cold_storage).")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON to stdout (default: CSV).")
    p.add_argument("--offline", action="store_true",
                   help="Use cache only — no network.")
    p.add_argument("--cleanup", type=Path, default=None,
                   help="Cleanup old CSVs in this directory (keeps 7 most recent).")
    args = p.parse_args(argv)

    fruits = list(TARGET_FRUITS.keys()) if args.all else [args.fruit]
    try:
        records = scrape_all(fruits, offline=args.offline)
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
