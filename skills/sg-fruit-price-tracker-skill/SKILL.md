---
name: sg-fruit-price-tracker-skill
description: "Track seasonal fruit prices across Singapore supermarkets — FairPrice (NTUC), Cold Storage, and Sheng Siong. Captures product name, weight, price SGD, original/promo price, star rating, review count, and source URL for lychees, peaches, strawberries, plums. Emits a CSV (default) or JSON (--json) report with rolling 7-day retention. Use this skill whenever the user mentions tracking, monitoring, scraping, or comparing fruit prices at SG supermarkets, asks for a weekly grocery price report, wants to know if strawberries are on promo at FairPrice, or wants to set up a recurring price check. Also triggers for cron-driven 'Saturday morning fruit prices' jobs. Does NOT trigger for general grocery shopping, recipe planning, or non-fruit produce."
---

# SG Fruit Price Tracker

Track seasonal fruit prices across 3 Singapore supermarkets. Stdlib-only. Built to be run from a cron job (no shell pipes, no `curl | python3`).

## Target fruits

| Fruit       | Keywords                          | Notes                                       |
|-------------|-----------------------------------|---------------------------------------------|
| Lychees 🍒    | `lychee`, `lychees`               | Peak Jun-Jul (SG season)                    |
| Peaches 🍑    | `peach`, `peaches`                | Imported; price-sensitive to AUD/USD         |
| Strawberries 🍓 | `strawberry`, `strawberries`   | Year-round but expensive Dec-Feb            |
| Plums 🟣      | `plum`, `plums`                   | Japanese / Korean imports, May-Aug peak     |

## Retailers

| Retailer     | Status | Method                                              | Notes                                       |
|--------------|--------|-----------------------------------------------------|---------------------------------------------|
| **FairPrice** (NTUC)  | ✅  | web_search via SearXNG (no scraping)         | JSON of `(name, price, promo, store, url)`  |
| **Cold Storage**       | ✅  | `urllib.request` + aria-label regex           | Bundled `scripts/fruit_price_tracker.py`     |
| **Sheng Siong**        | ❌  | Meteor SPA — not extractable                 | Logged as `unavailable: meteor_spa`         |

**Do not attempt to scrape Sheng Siong.** Their site is a single-page Meteor app; the products live in a JS bundle, not in the HTML. Attempting to scrape returns an empty result and wastes a request. Log it as `unavailable` and move on.

## Data collected per product

```json
{
  "retailer": "cold_storage",
  "name": "Strawberries (USA) 250g",
  "weight_g": 250,
  "price_sgd": 6.95,
  "original_price_sgd": 8.95,
  "promo": true,
  "rating": 4.3,
  "review_count": 47,
  "url": "https://coldstorage.com.sg/...",
  "scraped_at": "2026-06-29T09:00:00+08:00"
}
```

Only `name` and `price_sgd` are mandatory. Everything else is optional — if the page doesn't show it, the field is `null` (not the string `"null"`).

## Output formats

| Format | When | How |
|--------|------|-----|
| **CSV** (default) | Recurring weekly snapshots | `python3 scripts/fruit_price_tracker.py --csv > fruit-prices-YYYY-MM-DD.csv` |
| **JSON** | Piping into a Slack/Discord webhook, or programmatic diffing | `python3 scripts/fruit_price_tracker.py --json` |

The CSV columns are: `retailer, name, weight_g, price_sgd, original_price_sgd, promo, rating, review_count, url, scraped_at`.

## Storage layout

```
~/cron/output/fairprice-tracker/
├── fruit-prices-2026-06-27.csv
├── fruit-prices-2026-06-20.csv
├── ...                            # rolling 7 files
└── fruit-prices-2026-05-30.csv    # oldest, deleted by cleanup
```

Rolling 7-file cleanup is the script's job — it deletes anything older than 7 days after a successful write. **Don't** keep more than 7 days; CSV bloat slows down diff tools.

## Cron configuration

```cron
# Saturday 9am SGT
0 9 * * 6  cd /home/user && python3 /path/to/sg-fruit-price-tracker-skill/scripts/fruit_price_tracker.py --csv > ~/cron/output/fairprice-tracker/fruit-prices-$(date +\%Y-\%m-\%d).csv 2>>~/cron/log/fruit-tracker.err
```

The `> ~/cron/output/.../fruit-prices-$(date +\%Y-\%m-\%d).csv` filename pattern ensures one file per run, even if the run is late. The 7-day cleanup runs inside the script *after* the new file is written.

**Cron-safe constraints** (these are why the script uses `urllib.request`, not `curl | python3`):

1. No shell pipes inside the script (cron shells don't always honour them)
2. No `subprocess` calls to other CLIs (use stdlib `urllib.request` for HTTP)
3. No interactive prompts — every input is a CLI flag
4. Exit codes: 0 = success, 1 = all-retailers-failed, 2 = partial-failure (some retailers OK)

## Helper script — `scripts/fruit_price_tracker.py`

Standalone Cold Storage scraper. Stdlib only.

```bash
python3 scripts/fruit_price_tracker.py --fruit lychee          # one fruit
python3 scripts/fruit_price_tracker.py --all                   # all 4 target fruits
python3 scripts/fruit_price_tracker.py --json                  # JSON instead of CSV
python3 scripts/fruit_price_tracker.py --retailer cold_storage # explicit retailer
python3 scripts/fruit_price_tracker.py --offline              # use cache only (no network)
```

Exit codes:

| Code | Meaning                                                   |
|------|-----------------------------------------------------------|
| 0    | All requested retailers returned data                     |
| 1    | All requested retailers failed (network / parse error)    |
| 2    | Partial success — some retailers OK, others failed        |

### Caching

- Cache dir: `~/.hermes/cache/sg-fruit-prices/`
- One HTML file per `(retailer, query)` tuple
- TTL: 3600s (1 hour) — Cold Storage's product list updates slowly
- `--offline` mode reads from cache only; never touches the network. Useful for re-runs after a partial failure.

### Blocklist (70+ keywords)

The script applies a **fresh-fruit blocklist** to filter out products that mention the fruit but are not the actual fruit. Examples:

```
juice, drink, yoghurt, snack, candy, jam, dried, canned, frozen,
tea, wine, soap, shampoo, lotion, cream, perfume, candle, balm,
supplement, vitamin, detergent, cleaner, flavoured, cake, cookie,
wafer, pudding, gel, gummy, ...
```

The full list lives at the top of `scripts/fruit_price_tracker.py`. **When in doubt, exclude.** False positives (a real fruit accidentally blocked) are recoverable; false negatives (yoghurt-with-fruit-in-the-name sneaking through) pollute the price report.

### Price validation

`$0.50 ≤ price_sgd ≤ $200`. Anything outside that range is dropped silently. Rationale:

- `< $0.50` is a bundle / multi-pack misread
- `> $200` is a bulk case (e.g. 5kg) or a weight mismatch — handle separately

If the regex captures a price, but it's outside the band, the product is excluded from the output. Don't log it as a price — log it as a "parse anomaly" if the user wants debug output (`--verbose`).

## Workflow

1. **Pick the retailer** — start with Cold Storage (deterministic, scrapable). FairPrice is a fallback via `web_search` if Cold Storage returns nothing.
2. **Build the search query** — `<fruit_keyword> cold storage` (or just the fruit name — the script handles URL construction).
3. **Fetch the search results page** — `urllib.request` with a 10s timeout and the cache layer.
4. **Parse product cards** — `aria-label="<product name>"` followed by 1-2 prices (promo + regular).
5. **Apply blocklist** — drop anything that smells like processed food, drinks, toiletries.
6. **Validate prices** — drop anything outside `$0.50–$200`.
7. **Deduplicate** — by normalized name (lowercase, strip whitespace, strip weight).
8. **Emit** — CSV to stdout (default) or JSON (`--json`).
9. **Cleanup** — delete CSV files older than 7 days from the output dir.

## Extraction rules (in detail)

Cold Storage renders each product card with:

```html
<div class="product-card">
  <a href="/product/..." aria-label="Strawberries (USA) 250g">Strawberries</a>
  <div class="price">
    <span class="was">$8.95</span>
    <span class="now">$6.95</span>
  </div>
  <div class="rating" data-rating="4.3" data-reviews="47">★★★★☆</div>
</div>
```

The regex is:

```python
# 1. Find the aria-label
NAME_RE = re.compile(r'aria-label="([^"]+)"')
# 2. Find prices within 200 chars of the aria-label
PRICE_RE = re.compile(r'\$\s*(\d+(?:\.\d{1,2})?)')
# 3. The first 2 prices after each name are (promo, regular) — order is fragile
```

If the regex captures only 1 price, it's treated as the regular price (not a promo). If 0 prices, drop the product.

## Pitfalls (hardening notes)

1. **SearXNG may go down.** The script's `urllib.request` calls have a 10s timeout and catch `URLError`. On failure, the script logs `unavailable: searxng_down` and continues with whatever retailers did respond.
2. **aria-label ordering is fragile on page layout changes.** If the regex returns 0 products, do **not** invent prices from elsewhere on the page — that's how phantom products get into the CSV. Log the page count and exit with partial-failure.
3. **`curl | python3` is blocked in cron.** Use the script directly. The script uses `urllib.request` for all HTTP — no shell, no subprocess.
4. **Sheng Siong Meteor SPA** — not extractable. Logged as `unavailable: meteor_spa` and skipped.
5. **FairPrice web_search via SearXNG is best-effort** — it can return stale data, wrong currency, or unparseable snippets. Validate every record before writing to CSV.
6. **Concurrent runs** — if two cron jobs fire within the same minute, the second one's CSV write can clobber the first. Use a per-run filename (`fruit-prices-YYYY-MM-DD-HHMM.csv`) if there's any risk of overlap, or use `flock`.
7. **Cyrillic / Chinese fruit names** — Cold Storage renders product names in English with a SKU number; ignore the SKUs. The blocklist must include `sku` and other irrelevant tokens.

## When the agent triggers this skill

Match any of these intents:

- **"track [fruit] prices at [retailer]"** — single-fruit, single-retailer
- **"weekly [fruit] price report"** — all 4 fruits, all 3 retailers, one CSV
- **"compare strawberry prices across FairPrice and Cold Storage"** — single-fruit, multi-retailer
- **"set up a Saturday morning fruit price check"** — cron setup
- **"what's the cheapest lychee in SG this week"** — single-fruit, all retailers
- **"add a fruit price tracker to my crontab"** — installation

Do **not** trigger for:

- "Plan my weekly groceries" (use `singapore_api.py` or `hawker-discover-skill`)
- "Find me a recipe using lychees" (off-topic)
- "What's the weather like" (use `air-quality-advisor-skill`)

## Hardening

- **Stdlib only.** No `requests`, no `bs4`, no `pandas`. Cron can't `pip install`.
- **No shell pipes inside the script.** All HTTP via `urllib.request`.
- **No subprocess.** The script is a single Python process.
- **No interactive prompts.** All inputs are CLI flags.
- **Determinism:** cache hits produce byte-identical output. Cache misses depend only on the network.
- **Exit codes are non-zero on partial failure** — so cron can alert via mail.
- **CSV with header row** — easier for diff tools.
- **All HTTP timeouts:** 10s connect, 30s read. Failed requests log `unavailable: <reason>` and continue.
- **Blocklist is over-inclusive by design** — better to miss a real fruit than to admit a juice pack.

## Data sources

| Source                    | Purpose                                | Where                                |
|---------------------------|----------------------------------------|--------------------------------------|
| Cold Storage product pages | Product name, price, rating, URL      | `urllib.request` (no API)            |
| FairPrice via web_search   | Fallback for missing Cold Storage data | SearXNG JSON                         |
| Blocklist keywords         | Filter non-fruit products              | `scripts/fruit_price_tracker.py`     |
| Cache layer                | Avoid re-fetching within 1 hour        | `~/.hermes/cache/sg-fruit-prices/`   |

## Testing

Smoke tests at `tests/test_fruit_price_tracker.py` cover pure helpers (blocklist matching, price validation, regex extraction, dedup, CSV output, cache TTL) using canned HTML fixtures — no network. Run with:

```bash
python3 -m unittest discover -s skills/sg-fruit-price-tracker-skill/tests -v
```

## Evals

Realistic test prompts at `evals/evals.json`. The grader at `evals/grade.py` runs the script with canned HTML and checks the output. Run with:

```bash
python3 skills/sg-fruit-price-tracker-skill/evals/grade.py
```
