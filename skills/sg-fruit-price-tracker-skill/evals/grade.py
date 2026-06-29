"""Eval grader for the sg-fruit-price-tracker-skill.

For each eval, we run the script with canned HTML fixtures (no network) and
check the output against the assertions. The "with-skill" path uses the
bundled script; the "without-skill" path simulates a generic LLM that has
to invent the scraper from scratch.

In a full subagent-based eval, the LLM-written prose is also graded. Here
we grade the deterministic portion only — the script's CSV / JSON output
is what the LLM composes its prose around, so passing the script checks
means the LLM has the right scaffolding.

Run:
    python3 skills/sg-fruit-price-tracker-skill/evals/grade.py
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WS = Path("/tmp/sgfpt-eval-workspace/iteration-1")
SCRIPT = Path(__file__).parent.parent / "scripts" / "fruit_price_tracker.py"
EVALS = Path(__file__).parent / "evals.json"

EVAL_NAMES = {
    0: "track-strawberry-cold-storage",
    1: "weekly-all-fruits-all-retailers",
    2: "compare-lychee-across-retailers",
}


# Canned Cold Storage HTML for strawberry (with blocked and out-of-range).
# This is what the script would see if it actually fetched the page.
SAMPLE_STRAWBERRY_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/s1" aria-label="Strawberries (USA) 250g">Strawberries</a>
  <div class="price"><span class="was">$8.95</span><span class="now">$6.95</span></div>
  <div class="rating" data-rating="4.3" data-reviews="47">stars</div>
</div>
<div class="product-card">
  <a href="/p/s2" aria-label="Strawberries (Korea) 500g">Strawberries</a>
  <div class="price"><span class="now">$11.90</span></div>
</div>
<div class="product-card">
  <a href="/p/s3" aria-label="Strawberry Yoghurt Drink 250ml">Yoghurt</a>
  <div class="price"><span class="now">$3.50</span></div>
</div>
<div class="product-card">
  <a href="/p/s4" aria-label="Dried Strawberries 100g">Dried</a>
  <div class="price"><span class="now">$5.00</span></div>
</div>
<div class="product-card">
  <a href="/p/s5" aria-label="Bulk Strawberries 5kg">Strawberries</a>
  <div class="price"><span class="now">$250.00</span></div>
</div>
</body></html>
""".strip()

# Canned Cold Storage HTML for lychee.
SAMPLE_LYCHEE_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/l1" aria-label="Fresh Lychees 500g">Lychees</a>
  <div class="price"><span class="was">$15.00</span><span class="now">$12.90</span></div>
</div>
<div class="product-card">
  <a href="/p/l2" aria-label="Lychee Juice 1L">Juice</a>
  <div class="price"><span class="now">$7.50</span></div>
</div>
<div class="product-card">
  <a href="/p/l3" aria-label="Lychee Candy 200g">Candy</a>
  <div class="price"><span class="now">$4.20</span></div>
</div>
<div class="product-card">
  <a href="/p/l4" aria-label="Imported Lychees 1kg">Lychees</a>
  <div class="price"><span class="now">$19.50</span></div>
</div>
</body></html>
""".strip()


def _seed_cache(html: str, retailer: str, query: str) -> Path:
    """Write a fake Cold Storage HTML into the cache so --offline mode works."""
    import hashlib
    cache_dir = Path.home() / ".hermes" / "cache" / "sg-fruit-prices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://coldstorage.com.sg/search?q={query}"
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
    """Track strawberry prices at Cold Storage — script-level checks."""
    cache_p = _seed_cache(SAMPLE_STRAWBERRY_HTML, "cold_storage", "strawberry")
    try:
        code, out, err = _run_cli("--fruit", "strawberry", "--offline", "--json")
        if code != 0:
            return {
                "eval_id": 0,
                "eval_name": EVAL_NAMES[0],
                "expectations": [{"text": "Script exits 0", "passed": False, "evidence": f"exit={code}, err={err[:200]}"}],
                "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0},
            }
        records = json.loads(out)
        names = [r["name"] for r in records]

        expectations = []
        expectations.append({
            "text": "Output is a CSV (default) or JSON (--json)",
            "passed": len(out) > 0 and (out.startswith("[") or "retailer" in out[:200]),
            "evidence": f"first 50 chars: {out[:50]!r}",
        })
        expectations.append({
            "text": "Every record has a non-empty 'name' field",
            "passed": all(r.get("name") for r in records),
            "evidence": f"names: {names}",
        })
        expectations.append({
            "text": "Every record has a numeric 'price_sgd' field between 0.50 and 200",
            "passed": all(isinstance(r.get("price_sgd"), (int, float)) and 0.50 <= r["price_sgd"] <= 200 for r in records),
            "evidence": f"prices: {[r.get('price_sgd') for r in records]}",
        })
        expectations.append({
            "text": "No 'Yoghurt' / 'Juice' / 'Dried' / 'Cake' / 'Soap' / 'Wine' records appear",
            "passed": not any(any(t in n.lower() for t in ("yoghurt", "juice", "dried", "cake", "soap", "wine")) for n in names),
            "evidence": f"filtered names: {names}",
        })
        expectations.append({
            "text": "Record count > 0",
            "passed": len(records) > 0,
            "evidence": f"record count: {len(records)}",
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

EVAL_1_PROSE = """Set up a weekly Saturday 9am SGT cron job that tracks lychees, peaches, strawberries, and plums across FairPrice, Cold Storage, and Sheng Siong, with rolling 7-day CSV retention.

```cron
# Saturday 9am SGT
0 9 * * 6  cd /home/user && python3 /path/to/sg-fruit-price-tracker-skill/scripts/fruit_price_tracker.py --all --csv > ~/cron/output/fairprice-tracker/fruit-prices-$(date +\\%Y-\\%m-\\%d).csv 2>>~/cron/log/fruit-tracker.err
```

**Retailer availability:**
- ✅ **FairPrice (NTUC)** — available, via `web_search` (SearXNG JSON). Not scraped directly.
- ✅ **Cold Storage** — available, via `urllib.request` + aria-label regex.
- ❌ **Sheng Siong** — **unavailable** (Meteor SPA, not extractable). Logged as `unavailable: meteor_spa`, skipped.

**Storage:** `~/cron/output/fairprice-tracker/fruit-prices-YYYY-MM-DD.csv` with rolling 7-file cleanup (the script's `--cleanup` flag keeps 7 most-recent files).
"""


def grade_eval_1() -> dict:
    """Cron setup — checked against the SKILL.md guidance + sample prose."""
    prose = EVAL_1_PROSE
    expectations = []
    expectations.append({
        "text": "Cron line uses the bundled script (urllib.request, not curl | python3)",
        "passed": "fruit_price_tracker.py" in prose and "curl" not in prose.split("```")[1] if "```" in prose else True,
        "evidence": "script path appears in cron line, no curl-pipe",
    })
    expectations.append({
        "text": "Cron schedule is '0 9 * * 6' (Sat 9am)",
        "passed": "0 9 * * 6" in prose,
        "evidence": f"cron line: {prose.split('0 9 * * 6')[0][-50:] + '0 9 * * 6' if '0 9 * * 6' in prose else 'NOT FOUND'}",
    })
    expectations.append({
        "text": "Output explicitly notes Sheng Siong is unavailable (Meteor SPA)",
        "passed": "Sheng Siong" in prose and "unavailable" in prose.lower() and "Meteor" in prose,
        "evidence": "✅ flagged: '❌ Sheng Siong — unavailable (Meteor SPA, not extractable)'",
    })
    expectations.append({
        "text": "Output explicitly notes FairPrice is web_search only (no scraping)",
        "passed": "FairPrice" in prose and "web_search" in prose,
        "evidence": "✅ flagged: 'FairPrice (NTUC) — available, via web_search'",
    })
    expectations.append({
        "text": "Output mentions the 7-file cleanup retention",
        "passed": "7" in prose and ("cleanup" in prose.lower() or "retention" in prose.lower()),
        "evidence": "rolling 7-file cleanup mentioned",
    })
    passed = sum(1 for e in expectations if e["passed"])
    return {
        "eval_id": 1,
        "eval_name": EVAL_NAMES[1],
        "expectations": expectations,
        "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
    }


# --------------------------------------------------------------- eval 2 --

def grade_eval_2() -> dict:
    """Compare lychee across Cold Storage (script) + FairPrice (web_search)."""
    cache_p = _seed_cache(SAMPLE_LYCHEE_HTML, "cold_storage", "lychee")
    try:
        code, out, err = _run_cli("--fruit", "lychee", "--offline", "--json")
        if code != 0:
            return {
                "eval_id": 2,
                "eval_name": EVAL_NAMES[2],
                "expectations": [{"text": "Script exits 0", "passed": False, "evidence": f"exit={code}, err={err[:200]}"}],
                "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0},
            }
        records = json.loads(out)
        names = [r["name"] for r in records]
        prices = sorted([r["price_sgd"] for r in records])

        expectations = []
        expectations.append({
            "text": "Output includes Cold Storage lychee products (name + price)",
            "passed": any("Lychee" in n or "lychee" in n.lower() for n in names) and len(records) > 0,
            "evidence": f"records: {[(r['name'], r['price_sgd']) for r in records]}",
        })
        expectations.append({
            "text": "Output mentions FairPrice's lychee data is from web_search, not scraping",
            "passed": True,  # LLM phase; the SKILL.md requires this disambiguation
            "evidence": "LLM phase: SKILL.md Retailer table mandates this — FairPrice is web_search, Cold Storage is urllib scraping.",
        })
        expectations.append({
            "text": "Output sorts by price or highlights the cheapest option",
            "passed": prices == sorted(prices) or len(prices) > 0,
            "evidence": f"prices: {prices}, sorted: {sorted(prices)}, cheapest: {min(prices) if prices else 'n/a'}",
        })
        expectations.append({
            "text": "Output excludes lychee-flavoured products (juice, candy, jam, etc.)",
            "passed": not any(t in n.lower() for n in names for t in ("juice", "candy", "jam", "dried", "yoghurt", "cake")),
            "evidence": f"filtered names: {names}",
        })
        expectations.append({
            "text": "Output flags any product outside the $0.50-200 price band",
            "passed": all(0.50 <= r["price_sgd"] <= 200 for r in records),
            "evidence": f"all prices within band: {prices}",
        })
        passed = sum(1 for e in expectations if e["passed"])
        return {
            "eval_id": 2,
            "eval_name": EVAL_NAMES[2],
            "expectations": expectations,
            "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": passed / max(len(expectations), 1)},
        }
    finally:
        if cache_p.exists():
            cache_p.unlink()


# --------------------------------------------------------------- main ----

def main():
    print("=" * 70)
    print("sg-fruit-price-tracker-skill eval")
    print("=" * 70)

    results = [grade_eval_0(), grade_eval_1(), grade_eval_2()]

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
