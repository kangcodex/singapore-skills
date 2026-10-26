---
name: sg-fruit-price-tracker-skill
description: "Track and compare fresh-fruit prices at Singapore supermarkets: FairPrice, Cold Storage and Sheng Siong. Use for fruit-price lookups, promotions, weekly reports or recurring monitoring, including mango, durian, dragon fruit/pitaya, lychee and the other curated fruits. The bundled stdlib scraper handles Cold Storage and FairPrice; native search is the best-effort fallback for Sheng Siong. Emits CSV/JSON with product, weight, price and source fields, excludes non-fruit products and supports retained-file cleanup. Not for recipes, eating-out recommendations or general non-fruit shopping."
---

# SG Fruit Price Tracker

Track fruit prices across 3 Singapore supermarkets. Stdlib-only (no `requests`, no `bs4`, no `pip`). Designed to be run from a cron job — no shell pipes, no `subprocess` calls, no interactive prompts.

## Target fruits (30)

Curated for SG supermarkets. Common first, exotic after. Each entry: canonical name + search keywords.

| # | Fruit          | Keywords                              | Notes                                       |
|---|----------------|---------------------------------------|---------------------------------------------|
| 1 | Apple          | `apple`, `fuji`, `gala`, `granny`     | Year-round                                  |
| 2 | Banana         | `banana`, `cavendish`                 | Year-round                                  |
| 3 | Orange         | `orange`, `mandarin`, `valencia`      | Year-round                                  |
| 4 | Mango          | `mango`, `susu`, `harum manis`        | Peak Mar-Jul                                |
| 5 | Durian         | `durian`, `musang king`, `mao shan`   | Peak Jun-Aug (seasonal)                     |
| 6 | Dragon fruit   | `dragon fruit`, `pitaya`              | Year-round                                  |
| 7 | Rambutan       | `rambutan`                            | Peak Jun-Sep                                |
| 8 | Mangosteen     | `mangosteen`                          | Peak Jun-Aug                                |
| 9 | Papaya         | `papaya`, `pawpaw`                    | Year-round                                  |
| 10| Watermelon     | `watermelon`, `seedless`              | Peak Apr-Sep                                |
| 11| Pineapple      | `pineapple`, `md2`                    | Year-round                                  |
| 12| Lychee         | `lychee`, `lychees`                   | Peak Jun-Jul                                |
| 13| Longan         | `longan`                              | Peak Jul-Sep                                |
| 14| Jackfruit      | `jackfruit`, `nangka`                 | Year-round                                  |
| 15| Pomelo         | `pomelo`, `limau bali`                | Year-round                                  |
| 16| Pear           | `pear`, `ya li`, `crystal`            | Year-round                                  |
| 17| Peach          | `peach`, `donut peach`                | Peak May-Sep                                |
| 18| Plum           | `plum`, `japanese plum`               | Peak May-Aug                                |
| 19| Strawberry     | `strawberry`, `strawberries`          | Year-round, expensive Dec-Feb               |
| 20| Blueberry      | `blueberry`, `blueberries`            | Year-round                                  |
| 21| Raspberry      | `raspberry`, `raspberries`            | Year-round, expensive                       |
| 22| Cherry         | `cherry`, `cherries`                  | Peak Dec-Feb (imported)                     |
| 23| Grape          | `grape`, `grapes`, `kyoho`            | Year-round                                  |
| 24| Kiwi           | `kiwi`, `kiwifruit`, `zespri`         | Year-round                                  |
| 25| Lemon          | `lemon`, `meyer`                      | Year-round                                  |
| 26| Lime           | `lime`, `limau nipis`                 | Year-round                                  |
| 27| Persimmon      | `persimmon`, `fuyu`                   | Peak Oct-Jan                                |
| 28| Pomegranate    | `pomegranate`                         | Peak Sep-Jan                                |
| 29| Guava          | `guava`, `jambu`                      | Year-round                                  |
| 30| Star fruit     | `star fruit`, `carambola`             | Year-round                                  |

## Retailers

| Retailer               | Status | Method                                         | Notes                                    |
|------------------------|--------|------------------------------------------------|------------------------------------------|
| **Cold Storage**       | ✅     | `urllib.request` + aria-label regex            | Direct HTML scrape, deterministic        |
| **FairPrice** (NTUC)   | ✅     | `urllib.request` + HTML parse (data-testid)    | Server-rendered category page, no API    |
| **Sheng Siong**        | ⚠️     | `web_search` (Meteor SPA fallback)             | Agent-invoked at runtime, best-effort    |

**Sheng Siong is a Meteor SPA.** Their site is a single-page Meteor app; the products live in a JS bundle, not in the HTML. The script's `urllib.request` cannot extract them. The script logs `unavailable: meteor_spa` and the agent should fall back to a `web_search` (SearXNG or equivalent) for that retailer.

**FairPrice has no public API.** Their Next.js site uses server-side rendering for category pages, so product data (name, price, weight, rating) is in the HTML. We parse it with regex on `data-testid` attributes. If FairPrice switches to fully client-rendered pages, this breaks and we fall back to `web_search` (same pattern as Sheng Siong).

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

| Format       | When                                | How |
|--------------|-------------------------------------|-----|
| **CSV** (default) | Recurring weekly snapshots     | `python3 scripts/fruit_price_tracker.py --csv > fruit-prices-YYYY-MM-DD.csv` |
| **JSON**     | Piping into Slack/Discord webhook, programmatic diffing | `python3 scripts/fruit_price_tracker.py --json` |

CSV columns: `retailer, name, weight_g, price_sgd, original_price_sgd, promo, rating, review_count, url, scraped_at`.

## Storage layout

```
~/cron/output/fairprice-tracker/
├── fruit-prices-2026-06-27.csv
├── fruit-prices-2026-06-20.csv
├── ...                            # rolling 7 files
└── fruit-prices-2026-05-30.csv    # oldest, deleted by cleanup
```

Rolling 7-file cleanup is the script's job — deletes anything older than 7 days after a successful write. Don't keep more than 7 days; CSV bloat slows down diff tools.

## Cron configuration

```cron
# Saturday 9am SGT
0 9 * * 6  cd /home/user && python3 /path/to/sg-fruit-price-tracker-skill/scripts/fruit_price_tracker.py --csv > ~/cron/output/fairprice-tracker/fruit-prices-$(date +\%Y-\%m-\%d).csv 2>>~/cron/log/fruit-tracker.err
```

The `> ~/cron/output/.../fruit-prices-$(date +\%Y-\%m-\%d).csv` filename pattern ensures one file per run, even if late. The 7-day cleanup runs inside the script *after* the new file is written.

**Cron-safe constraints:**
1. No shell pipes inside the script (cron shells don't always honour them)
2. No `subprocess` calls to other CLIs (use stdlib `urllib.request` for HTTP)
3. No interactive prompts — every input is a CLI flag
4. Exit codes: 0 = success, 1 = all-retailers-failed, 2 = partial-failure (some retailers OK)

## Helper script — `scripts/fruit_price_tracker.py`

Standalone fruit price scraper. Stdlib only.

```bash
python3 scripts/fruit_price_tracker.py --all                    # all 30 fruits
python3 scripts/fruit_price_tracker.py --fruit mango           # one fruit
python3 scripts/fruit_price_tracker.py --retailer cold_storage # one retailer
python3 scripts/fruit_price_tracker.py --json                  # JSON instead of CSV
python3 scripts/fruit_price_tracker.py --offline               # use cache only (no network)
python3 scripts/fruit_price_tracker.py --retailer fairprice --fruit apple  # both
```

Exit codes:

| Code | Meaning                                                   |
|------|-----------------------------------------------------------|
| 0    | All requested retailers returned data                     |
| 1    | All requested retailers failed (network / parse error)    |
| 2    | Partial success — some retailers OK, others failed        |

### Caching

- Cache dir: `~/.hermes/cache/sg-fruit-prices/`
- One HTML file per URL
- TTL: 3600s (1 hour)
- `--offline` mode reads from cache only; never touches the network. Useful for re-runs after partial failure.

### Blocklist (70+ keywords)

Applied to product names to filter out non-fresh-fruit products (juice, yoghurt, dried, candy, soap, etc.). Full list at the top of `scripts/fruit_price_tracker.py`. **When in doubt, exclude.** False positives (real fruit accidentally blocked) are recoverable; false negatives (yoghurt-with-fruit sneaking through) pollute the price report.

### Price validation

`$0.50 ≤ price_sgd ≤ $200`. Outside that range = drop silently.

- `< $0.50` = bundle / multi-pack misread
- `> $200` = bulk case (e.g. 5kg) or weight mismatch

## Workflow (agent + script)

When the user asks for a price check, the agent follows these steps:

1. **Identify the scope** — single fruit, all 30, single retailer, or all 3.
2. **Run the script** for Cold Storage + FairPrice:
   ```bash
   python3 scripts/fruit_price_tracker.py --fruit <name> --json
   python3 scripts/fruit_price_tracker.py --retailer fairprice --fruit <name> --json
   ```
3. **For Sheng Siong, invoke `web_search`** at runtime:
   ```
   web_search("sheng siong <fruit> price sgd")
   ```
   Parse the snippets for product name + price. Add records to the same output.
4. **Combine, dedup, emit** — single CSV/JSON across all 3 retailers.
5. **Cleanup** — delete CSV files older than 7 days from the output dir.

If Sheng Siong web_search is unavailable, log `unavailable: meteor_spa + no_web_search` and proceed with Cold Storage + FairPrice only. Do NOT retry Sheng Siong with urllib — it will always return 0 matches.

## Extraction rules (in detail)

### Cold Storage

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

Regex:
```python
NAME_RE = re.compile(r'aria-label="([^"]+)"')
PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
```

First 2 prices after each name = (promo, regular). Order is fragile — verify with the lower/higher comparison.

### FairPrice

Server-rendered HTML from `/category/fruits`:

```html
<div data-testid="product-name-and-metadata" class="...">
  <span weight="normal" color="#333333" class="...">Fresh Blueberries</span>
  <span color="#666666" class="...">125g</span>
</div>
<div class="...">
  <span weight="black" class="...">$3.95</span>
</div>
<div data-testid="ratings-star-container" class="...">
  <span aria-label="Average rating is 4.0" class="...">4.0</span>
</div>
<a href="/product/agroberries-premium-blueberry-bleuets-125g-10632060" class="...">
  View product
</a>
```

Parser strategy:
1. Fetch `https://www.fairprice.com.sg/category/fruits` once
2. Find all `<a href="/product/{slug}">` patterns
3. For each, extract name, weight, price, original price, rating from the surrounding HTML
4. Filter by fruit keyword (the 30-fruit list above)
5. Build records

URL: `https://www.fairprice.com.sg/product/{slug}`

### Sheng Siong

Not directly scrapable. Use `web_search` at runtime with a query like:
```
"sheng siong" "{fruit}" price site:shengsiong.com.sg
```

Parse the top 3-5 snippets. Each snippet is usually one product with name + price embedded. Format expected in the snippet: `"Sheng Siong Lychee 500g - $12.90"`. Extract via regex.

If no snippets return usable data, log `unavailable: meteor_spa + no_web_search` and skip.

## Pitfalls (hardening notes)

1. **Sheng Siong Meteor SPA** — products in JS bundle, not HTML. `urllib` returns empty result. Don't retry; log and skip.
2. **FairPrice category page changes** — if they switch to client-rendering, the HTML will be empty. Fall back to `web_search` (same as Sheng Siong pattern). Detect by checking for `data-testid="product-name-and-metadata"` in the response.
3. **Cold Storage aria-label ordering is fragile** — if regex returns 0 products, do NOT invent prices from elsewhere on the page. Log and exit partial-failure.
4. **SearXNG / web_search may go down** — log `unavailable: web_search_down` and continue.
5. **`curl | python3` blocked in cron** — use the script directly, no shell pipes.
6. **Concurrent runs** — if two cron jobs fire within the same minute, use a per-run filename (`fruit-prices-YYYY-MM-DD-HHMM.csv`) or `flock`.
7. **CJK / non-English fruit names** — Cold Storage renders names in English with SKU numbers. The blocklist includes `sku` and similar tokens. FairPrice product names are also English.
8. **Price format variations** — Cold Storage uses `$8.95`; FairPrice uses `$3.95`; Sheng Siong snippets vary. Regex `\$\s*(\d+(?:\.\d{1,2})?)` covers all three.

## Anti-patterns (do NOT do these)

Each of these was observed in fresh-LLM (no-skill) responses. If you find yourself reaching for any of them, stop and re-read the script + this skill.

1. **`curl | python3 parse_prices.py`** — fragile shell pipe, breaks under cron, not stdlib, blocks if the upstream is slow. Use `python3 scripts/fruit_price_tracker.py --all --csv` directly. No pipes.
2. **`pip install requests beautifulsoup4`** — cron can't pip install, and we don't need them. Stdlib `urllib.request` + regex is sufficient. The script is stdlib-only by design.
3. **Headless browser / Playwright for FairPrice** — FairPrice's `/category/fruits` is server-rendered Next.js. The HTML contains all product data. A browser is unnecessary overhead. Only fall back to a browser if the regex returns 0 products (and log the regression).
4. **`curl https://shengsiong.com.sg/...`** — always returns `<div id="root"></div>`. No HTML to parse. Do not retry; do not invent a parser for an empty body. The script's `unavailable: meteor_spa` is the correct answer. For Sheng Siong prices, run `web_search` at runtime.
5. **Separate `ls | tail | xargs rm` cron for cleanup** — the script has `--cleanup N` built in. Add `--cleanup 7` to the same cron line, not a second job.
6. **`/search?q=mango` for FairPrice** — that endpoint is JS-rendered and returns >5 MB of bundle before any products. Use `/category/fruits` (one fetch, all 30 fruits' worth of products).
7. **Writing a one-off parser per fruit** — the script has a 30-fruit keyword set (`TARGET_FRUITS` dict) with exotic aliases (dragon_fruit → `dragon fruit` / `pitaya`, star_fruit → `star fruit` / `carambola`). Use `--all` or `--fruit <name>` and let the script handle the keyword expansion.
8. **Hallucinating Sheng Siong prices** — when the script returns `unavailable: meteor_spa`, the correct response is to flag it in the output, not to invent prices from memory. SS prices from `web_search` are low-confidence; mark them `confidence: low` and `source: web_search`.
9. **Per-fruit cron lines** — one cron line with `--all` is cheaper than 30 lines. One Python startup, one log file, one timestamp per run.
10. **String `"null"` for missing fields** — use JSON `null`. The output schema uses `null` (not `"null"`, not `0`) for missing `weight_g`, `original_price_sgd`, `rating`, `review_count`.
11. **Filtering on the CS `was` price alone** — `was` may be absent (no promo). Fall back to the first `$N.NN` after the name. The script's regex does this; don't reinvent.
12. **Using `--retailer sheng_siong` and expecting data** — the script will log `unavailable: meteor_spa` and exit 1. If you want SS data, run `web_search` and merge into the CS+FP output by hand. Do not retry SS scraping.

## When the agent triggers this skill

Match any of these intents:
- **"track [fruit] prices at [retailer]"** — single-fruit, single-retailer
- **"weekly fruit price report"** — all 30 fruits, all 3 retailers, one CSV
- **"compare mango prices across FairPrice and Cold Storage"** — single-fruit, multi-retailer
- **"set up a Saturday morning fruit price check"** — cron setup
- **"what's the cheapest durian in SG this week"** — single-fruit, all retailers
- **"add a fruit price tracker to my crontab"** — installation
- **"are blueberries on promo at FairPrice?"** — promo check
- **"compare exotic fruit prices (dragon fruit, mangosteen)"** — multi-fruit

Do **not** trigger for:
- "Plan my weekly groceries" (use `singapore_api.py` or `hawker-discover-skill`)
- "Find me a recipe using durian" (off-topic)
- "What's the weather like" (use `air-quality-advisor-skill`)
- Non-fruit produce (vegetables, herbs) — out of scope

## Hardening

- **Stdlib only.** No `requests`, no `bs4`, no `pandas`. Cron can't `pip install`.
- **No shell pipes inside the script.** All HTTP via `urllib.request`.
- **No subprocess.** The script is a single Python process.
- **No interactive prompts.** All inputs are CLI flags.
- **Determinism:** cache hits produce byte-identical output. Cache misses depend only on the network.
- **Exit codes are non-zero on partial failure** — cron can alert via mail.
- **CSV with header row** — easier for diff tools.
- **All HTTP timeouts:** 10s connect, 30s read.
- **Blocklist is over-inclusive by design** — better to miss a real fruit than admit a juice pack.

## Data sources

| Source                          | Purpose                                | Where                              |
|---------------------------------|----------------------------------------|------------------------------------|
| Cold Storage product pages      | Product name, price, rating, URL       | `urllib.request` (no API)          |
| FairPrice `/category/fruits`    | All current fruit products in one call | `urllib.request` (no API)          |
| Sheng Siong web_search snippets | Best-effort price data                 | `web_search` runtime function      |
| Blocklist keywords              | Filter non-fruit products              | `scripts/fruit_price_tracker.py`   |
| Cache layer                     | Avoid re-fetching within 1 hour        | `~/.hermes/cache/sg-fruit-prices/` |
