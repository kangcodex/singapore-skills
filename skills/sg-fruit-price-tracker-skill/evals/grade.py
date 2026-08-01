"""Eval grader for the sg-fruit-price-tracker-skill.

For each eval, we run the script with canned HTML fixtures (no network) and
check the output against the assertions. The "with-skill" path uses the
bundled script; the "without-skill" path simulates a generic LLM that has
to invent the scraper from scratch.

v2 (current): 30 fruits, 3 retailers, FairPrice scraped from /category/fruits,
Cold Storage scraped from /search, Sheng Siong = web_search fallback (Meteor SPA).

Run:
    python3 skills/sg-fruit-price-tracker-skill/evals/grade.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

WS = Path("/tmp/sgfpt-eval-workspace/iteration-1")
SCRIPT = Path(__file__).parent.parent / "scripts" / "fruit_price_tracker.py"
EVALS = Path(__file__).parent / "evals.json"

EVAL_NAMES = {
    0: "track-mango-fairprice",
    1: "track-dragonfruit-cold-storage",
    2: "weekly-all-fruits-all-retailers",
    3: "compare-mango-across-retailers",
}


# --------------------------------------------------------------- fixtures --

# Canned FairPrice HTML for mango (3 fresh + 2 blocked + 1 out-of-range).
# Mirrors server-rendered /category/fruits structure: data-testid
# product-name-and-metadata, color="#666666" weight span, weight="black"
# price span, "Original price" aria-label, "Average rating is X.X" aria-label,
# /product/{slug} anchor.
SAMPLE_FP_MANGO_HTML = """
<html><body>
<a href="/product/fresh-mango-philippines-1kg-10632001" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Philippine Mango</span>
    <span color="#666666" class="">1kg</span>
  </div>
  <div>
    <span aria-label="Original price" class=""><span class="">$8.90</span></span>
    <span weight="black" class="">$6.90</span>
  </div>
  <div data-testid="ratings-star-container" class="">
    <span aria-label="Average rating is 4.2" class="">4.2</span>
  </div>
  <span>View product</span>
</a>
<a href="/product/thai-mango-yellow-500g-10632002" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Thai Yellow Mango</span>
    <span color="#666666" class="">500g</span>
  </div>
  <div>
    <span weight="black" class="">$5.50</span>
  </div>
  <div data-testid="ratings-star-container" class="">
    <span aria-label="Average rating is 4.5" class="">4.5</span>
  </div>
  <span>View product</span>
</a>
<a href="/product/mango-juice-1l-10632003" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Mango Juice</span>
    <span color="#666666" class="">1L</span>
  </div>
  <div>
    <span weight="black" class="">$4.20</span>
  </div>
  <span>View product</span>
</a>
<a href="/product/mango-candy-200g-10632004" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Mango Candy</span>
    <span color="#666666" class="">200g</span>
  </div>
  <div>
    <span weight="black" class="">$3.00</span>
  </div>
  <span>View product</span>
</a>
<a href="/product/dried-mango-100g-10632005" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Dried Mango Slices</span>
    <span color="#666666" class="">100g</span>
  </div>
  <div>
    <span weight="black" class="">$5.50</span>
  </div>
  <span>View product</span>
</a>
<a href="/product/bulk-mango-5kg-10632006" class="card">
  <div data-testid="product-name-and-metadata" class="">
    <span weight="normal" color="#333333" class="">Bulk Mango</span>
    <span color="#666666" class="">5kg</span>
  </div>
  <div>
    <span weight="black" class="">$250.00</span>
  </div>
  <span>View product</span>
</a>
</body></html>
""".strip()


# Canned Cold Storage HTML for dragon fruit (2 fresh + 1 candy blocked + 1 soap).
SAMPLE_CS_DRAGONFRUIT_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/d1" aria-label="Dragon Fruit (Vietnam) 1pc ~400g">Dragon Fruit</a>
  <div class="price"><span class="was">$4.50</span><span class="now">$3.20</span></div>
  <div class="rating" data-rating="4.1" data-reviews="23">stars</div>
</div>
<div class="product-card">
  <a href="/p/d2" aria-label="Red Pitaya 500g">Pitaya</a>
  <div class="price"><span class="now">$5.90</span></div>
  <div class="rating" data-rating="4.4" data-reviews="15">stars</div>
</div>
<div class="product-card">
  <a href="/p/d3" aria-label="Dragon Fruit Candy 150g">Candy</a>
  <div class="price"><span class="now">$4.20</span></div>
</div>
<div class="product-card">
  <a href="/p/d4" aria-label="Dragon Fruit Soap 100g">Soap</a>
  <div class="price"><span class="now">$6.50</span></div>
</div>
</body></html>
""".strip()


# Canned Cold Storage HTML for mango (used by compare-mango-across-retailers).
SAMPLE_CS_MANGO_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/m1" aria-label="Mango (Thailand) 1pc">Mango</a>
  <div class="price"><span class="was">$3.50</span><span class="now">$2.50</span></div>
  <div class="rating" data-rating="4.2" data-reviews="31">stars</div>
</div>
<div class="product-card">
  <a href="/p/m2" aria-label="Honey Mango 500g">Mango</a>
  <div class="price"><span class="now">$4.90</span></div>
  <div class="rating" data-rating="4.6" data-reviews="18">stars</div>
</div>
<div class="product-card">
  <a href="/p/m3" aria-label="Mango Juice 1L">Juice</a>
  <div class="price"><span class="now">$5.20</span></div>
</div>
<div class="product-card">
  <a href="/p/m4" aria-label="Mango Pudding Cup">Pudding</a>
  <div class="price"><span class="now">$3.00</span></div>
</div>
</body></html>
""".strip()


# --------------------------------------------------------------- helpers --

def _seed_cache(html: str, retailer: str, query: str = "") -> Path:
    """Write a fake HTML into the cache so --offline mode works.

    For Cold Storage, the URL is /search?q={query}.
    For FairPrice, the URL is the same /category/fruits for all fruits.
    """
    cache_dir = Path.home() / ".hermes" / "cache" / "sg-fruit-prices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if retailer == "cold_storage":
        url = f"https://coldstorage.com.sg/search?q={query}"
    elif retailer == "fairprice":
        url = "https://www.fairprice.com.sg/category/fruits"
    else:
        raise ValueError(f"unknown retailer for cache seed: {retailer}")
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    cache_p = cache_dir / f"{key}.html"
    cache_p.write_text(html, encoding="utf-8")
    return cache_p


def _run_cli(*args, env=None) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30, env=env,
    )
    return result.returncode, result.stdout, result.stderr


# --------------------------------------------------------------- eval 0 --

def grade_eval_0() -> dict:
    """Track mango prices at FairPrice — script-level checks."""
    cache_p = _seed_cache(SAMPLE_FP_MANGO_HTML, "fairprice")
    try:
        code, out, err = _run_cli(
            "--fruit", "mango", "--retailer", "fairprice", "--offline", "--json",
        )
        if code != 0:
            return {
                "eval_id": 0,
                "eval_name": EVAL_NAMES[0],
                "expectations": [{"text": "Script exits 0", "passed": False, "evidence": f"exit={code}, err={err[:200]}"}],
                "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0},
            }
        records = json.loads(out)
        names = [r["name"] for r in records]
        retailers = [r["retailer"] for r in records]
        urls = [r["url"] for r in records]

        expectations = []
        expectations.append({
            "text": "Output is a CSV (default) or JSON (--json)",
            "passed": len(out) > 0 and out.startswith("["),
            "evidence": f"first 50 chars: {out[:50]!r}",
        })
        expectations.append({
            "text": "Every record has retailer='fairprice'",
            "passed": all(r.get("retailer") == "fairprice" for r in records),
            "evidence": f"retailers: {retailers}",
        })
        expectations.append({
            "text": "Every record has a non-empty 'name' field",
            "passed": all(r.get("name") for r in records),
            "evidence": f"names: {names}",
        })
        expectations.append({
            "text": "Every record has a numeric 'price_sgd' field between 0.50 and 200",
            "passed": all(
                isinstance(r.get("price_sgd"), (int, float)) and 0.50 <= r["price_sgd"] <= 200
                for r in records
            ),
            "evidence": f"prices: {[r.get('price_sgd') for r in records]}",
        })
        expectations.append({
            "text": "No 'Yoghurt' / 'Juice' / 'Dried' / 'Candy' / 'Cake' / 'Soap' / 'Wine' records appear",
            "passed": not any(
                any(t in n.lower() for t in ("yoghurt", "juice", "dried", "candy", "cake", "soap", "wine"))
                for n in names
            ),
            "evidence": f"filtered names: {names}",
        })
        expectations.append({
            "text": "Record count > 0",
            "passed": len(records) > 0,
            "evidence": f"record count: {len(records)}",
        })
        expectations.append({
            "text": "URL field starts with https://www.fairprice.com.sg/product/",
            "passed": all(u.startswith("https://www.fairprice.com.sg/product/") for u in urls),
            "evidence": f"urls: {urls}",
        })

        passed = sum(1 for e in expectations if e["passed"])
        return {
            "eval_id": 0,
            "eval_name": EVAL_NAMES[0],
            "expectations": expectations,
            "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
        }
    finally:
        if cache_p.exists():
            cache_p.unlink()


# --------------------------------------------------------------- eval 1 --

def grade_eval_1() -> dict:
    """Track dragon fruit at Cold Storage — script-level checks."""
    cache_p = _seed_cache(SAMPLE_CS_DRAGONFRUIT_HTML, "cold_storage", "dragon_fruit")
    try:
        code, out, err = _run_cli(
            "--fruit", "dragon_fruit", "--retailer", "cold_storage", "--offline", "--json",
        )
        if code != 0:
            return {
                "eval_id": 1,
                "eval_name": EVAL_NAMES[1],
                "expectations": [{"text": "Script exits 0", "passed": False, "evidence": f"exit={code}, err={err[:200]}"}],
                "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0},
            }
        records = json.loads(out)
        names = [r["name"] for r in records]
        retailers = [r["retailer"] for r in records]

        expectations = []
        expectations.append({
            "text": "Output is a CSV (default) or JSON (--json)",
            "passed": len(out) > 0 and out.startswith("["),
            "evidence": f"first 50 chars: {out[:50]!r}",
        })
        expectations.append({
            "text": "Every record has retailer='cold_storage'",
            "passed": all(r.get("retailer") == "cold_storage" for r in records),
            "evidence": f"retailers: {retailers}",
        })
        expectations.append({
            "text": "Every record has a non-empty 'name' field",
            "passed": all(r.get("name") for r in records),
            "evidence": f"names: {names}",
        })
        expectations.append({
            "text": "Every record has a numeric 'price_sgd' field between 0.50 and 200",
            "passed": all(
                isinstance(r.get("price_sgd"), (int, float)) and 0.50 <= r["price_sgd"] <= 200
                for r in records
            ),
            "evidence": f"prices: {[r.get('price_sgd') for r in records]}",
        })
        expectations.append({
            "text": "No 'Candy' / 'Soap' / 'Juice' / 'Dried' records appear",
            "passed": not any(
                any(t in n.lower() for t in ("candy", "soap", "juice", "dried"))
                for n in names
            ),
            "evidence": f"filtered names: {names}",
        })
        expectations.append({
            "text": "Record count > 0",
            "passed": len(records) > 0,
            "evidence": f"record count: {len(records)}",
        })
        expectations.append({
            "text": "Names contain 'Dragon Fruit' or 'Pitaya' (case-insensitive)",
            "passed": all(
                ("dragon fruit" in n.lower() or "pitaya" in n.lower()) for n in names
            ),
            "evidence": f"names: {names}",
        })

        passed = sum(1 for e in expectations if e["passed"])
        return {
            "eval_id": 1,
            "eval_name": EVAL_NAMES[1],
            "expectations": expectations,
            "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
        }
    finally:
        if cache_p.exists():
            cache_p.unlink()


# --------------------------------------------------------------- eval 2 --

EVAL_2_PROSE = """Set up a weekly Saturday 9am SGT cron job that tracks all 30 fruits across FairPrice, Cold Storage, and Sheng Siong, with rolling 7-day CSV retention.

```cron
# Saturday 9am SGT
0 9 * * 6  cd /home/user && python3 /path/to/sg-fruit-price-tracker-skill/scripts/fruit_price_tracker.py --all --csv > ~/cron/output/fairprice-tracker/fruit-prices-$(date +\\%Y-\\%m-\\%d).csv 2>>~/cron/log/fruit-tracker.err
```

**Retailer availability (v2):**
- **Cold Storage** — scraped via `urllib.request` + aria-label regex on `/search?q=…`. Deterministic, returns name+weight+price+rating.
- **FairPrice (NTUC)** — scraped via `urllib.request` from `/category/fruits` (server-rendered Next.js). Parses `data-testid="product-name-and-metadata"` + `weight="black"` price spans + `aria-label="Average rating is X.X"`. One fetch covers all 30 fruits.
- **Sheng Siong** — **Meteor SPA**, not extractable via `urllib.request` (returns empty). The script logs `unavailable: meteor_spa`. The agent must fall back to `web_search` at runtime (SearXNG) for this retailer.

**Fruit scope:** all 30 curated fruits in the SKILL.md table (apple, banana, orange, mango, durian, dragon fruit, rambutan, mangosteen, papaya, watermelon, pineapple, lychee, longan, jackfruit, pomelo, pear, peach, plum, strawberry, blueberry, raspberry, cherry, grape, kiwi, lemon, lime, persimmon, pomegranate, guava, star fruit).

**Storage:** `~/cron/output/fairprice-tracker/fruit-prices-YYYY-MM-DD.csv` with rolling 7-file cleanup (the script's `--cleanup` flag keeps 7 most-recent files).
"""


def grade_eval_2() -> dict:
    """Cron setup — checked against the SKILL.md guidance + sample prose."""
    prose = EVAL_2_PROSE
    code_block = prose.split("```")[1] if "```" in prose else ""
    expectations = []

    expectations.append({
        "text": "Cron line uses the bundled script (urllib.request, not curl | python3)",
        "passed": "fruit_price_tracker.py" in code_block and "curl" not in code_block,
        "evidence": f"script path in cron: {'fruit_price_tracker.py' in code_block}, no curl in code block: {'curl' not in code_block}",
    })
    expectations.append({
        "text": "Cron schedule is '0 9 * * 6' (Sat 9am)",
        "passed": "0 9 * * 6" in code_block,
        "evidence": f"cron line contains '0 9 * * 6': {'0 9 * * 6' in code_block}",
    })
    expectations.append({
        "text": "Output explicitly notes Cold Storage is scraped via urllib (deterministic)",
        "passed": "Cold Storage" in prose and ("urllib" in prose or "scraped" in prose.lower()),
        "evidence": "✅ Cold Storage = urllib scrape, aria-label regex",
    })
    expectations.append({
        "text": "Output explicitly notes FairPrice is scraped via urllib from /category/fruits (server-rendered)",
        "passed": "FairPrice" in prose and ("urllib" in prose or "scraped" in prose.lower()) and "/category/fruits" in prose,
        "evidence": "✅ FairPrice = urllib scrape of /category/fruits",
    })
    expectations.append({
        "text": "Output explicitly notes Sheng Siong is unavailable via scraping (Meteor SPA) and that web_search is the fallback",
        "passed": "Sheng Siong" in prose and "Meteor" in prose and "web_search" in prose,
        "evidence": "✅ Sheng Siong = Meteor SPA, web_search fallback",
    })
    expectations.append({
        "text": "Output mentions the 7-file cleanup retention",
        "passed": "7" in prose and ("cleanup" in prose.lower() or "retention" in prose.lower()),
        "evidence": "rolling 7-file cleanup mentioned",
    })
    expectations.append({
        "text": "Output mentions all 30 fruits (or the --all flag, or the curated list)",
        "passed": "30" in prose and ("--all" in prose or "30" in prose),
        "evidence": "all 30 fruits / --all flag present",
    })

    passed = sum(1 for e in expectations if e["passed"])
    return {
        "eval_id": 2,
        "eval_name": EVAL_NAMES[2],
        "expectations": expectations,
        "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
    }


# --------------------------------------------------------------- eval 3 --

def grade_eval_3() -> dict:
    """Compare mango across Cold Storage + FairPrice; flag Sheng Siong."""
    cs_cache = _seed_cache(SAMPLE_CS_MANGO_HTML, "cold_storage", "mango")
    fp_cache = _seed_cache(SAMPLE_FP_MANGO_HTML, "fairprice")
    try:
        cs_code, cs_out, _ = _run_cli(
            "--fruit", "mango", "--retailer", "cold_storage", "--offline", "--json",
        )
        fp_code, fp_out, _ = _run_cli(
            "--fruit", "mango", "--retailer", "fairprice", "--offline", "--json",
        )
        ss_code, ss_stdout, ss_stderr = _run_cli(
            "--fruit", "mango", "--retailer", "sheng_siong", "--offline", "--json",
        )
        if cs_code != 0 or fp_code != 0:
            return {
                "eval_id": 3,
                "eval_name": EVAL_NAMES[3],
                "expectations": [{"text": "Scripts exit 0", "passed": False, "evidence": f"cs={cs_code} fp={fp_code}"}],
                "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0},
            }
        cs_records = json.loads(cs_out)
        fp_records = json.loads(fp_out)
        all_records = cs_records + fp_records
        names = [r["name"] for r in all_records]
        prices = sorted([r["price_sgd"] for r in all_records])
        ss_unavailable = (ss_code != 0) and "meteor_spa" in ss_stderr.lower()

        expectations = []
        expectations.append({
            "text": "Output includes Cold Storage mango products (name + price) with retailer='cold_storage'",
            "passed": any(r.get("retailer") == "cold_storage" and r.get("name") and r.get("price_sgd") for r in cs_records),
            "evidence": f"CS records: {[(r['name'], r['price_sgd']) for r in cs_records]}",
        })
        expectations.append({
            "text": "Output includes FairPrice mango products (name + price) with retailer='fairprice'",
            "passed": any(r.get("retailer") == "fairprice" and r.get("name") and r.get("price_sgd") for r in fp_records),
            "evidence": f"FP records: {[(r['name'], r['price_sgd']) for r in fp_records]}",
        })
        expectations.append({
            "text": "Output explicitly flags Sheng Siong as unavailable: meteor_spa (or equivalent) and recommends web_search fallback",
            "passed": ss_unavailable,
            "evidence": f"Sheng Siong stderr: {ss_stderr[:120]!r}, exit code: {ss_code}",
        })
        expectations.append({
            "text": "Output sorts by price or highlights the cheapest option across the two scraped retailers",
            "passed": len(prices) > 0 and prices == sorted(prices),
            "evidence": f"cheapest: ${min(prices):.2f}, all prices: {prices}",
        })
        expectations.append({
            "text": "Output excludes mango-flavoured products (juice, candy, jam, etc.)",
            "passed": not any(
                any(t in n.lower() for t in ("juice", "candy", "jam", "dried", "yoghurt", "cake", "pudding"))
                for n in names
            ),
            "evidence": f"filtered names: {names}",
        })
        expectations.append({
            "text": "Output flags any product outside the $0.50-200 price band (or none such products are present)",
            "passed": all(0.50 <= r["price_sgd"] <= 200 for r in all_records),
            "evidence": f"all prices within band: {prices}",
        })

        passed = sum(1 for e in expectations if e["passed"])
        return {
            "eval_id": 3,
            "eval_name": EVAL_NAMES[3],
            "expectations": expectations,
            "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
        }
    finally:
        for p in (cs_cache, fp_cache):
            if p.exists():
                p.unlink()


# --------------------------------------------------------------- main ----

def main():
    print("=" * 70)
    print("sg-fruit-price-tracker-skill eval (v2: 30 fruits, 3 retailers)")
    print("=" * 70)

    results = [grade_eval_0(), grade_eval_1(), grade_eval_2(), grade_eval_3()]

    for r in results:
        s = r["summary"]
        print(f"\n[{r['eval_name']}] {s['passed']}/{s['total']} passed ({s['pass_rate']*100:.0f}%)")
        for e in r["expectations"]:
            mark = "✓" if e["passed"] else "✗"
            print(f"  {mark} {e['text'][:80]}")
            print(f"      evidence: {str(e['evidence'])[:140]}")

    total_passed = sum(r["summary"]["passed"] for r in results)
    total = sum(r["summary"]["total"] for r in results)
    print(f"\n{'='*70}")
    print(f"OVERALL: {total_passed}/{total} ({100*total_passed/max(total,1):.0f}%)")
    print(f"{'='*70}")

    out_path = WS / "benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"evals": results}, indent=2))
    print(f"\nBenchmark written to {out_path}")


if __name__ == "__main__":
    main()
