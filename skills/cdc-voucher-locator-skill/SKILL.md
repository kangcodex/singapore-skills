---
name: cdc-voucher-locator-skill
description: "Find CDC Voucher-accepting merchants near any Singapore location. Use this skill whenever the user asks where to use CDC vouchers, hawker/heartland merchants nearby, supermarkets or budget meals near a Singapore address, or food recommendations that accept CDC vouchers. Handles intent filtering (food, supermarket, budget meal, or full generic) and auto-expands search radius when results are sparse."
---

# CDC Voucher Locator

Find CDC Voucher-accepting merchants near any Singapore location, with smart intent-based filtering and efficient data handling.

## Quick Start — Portable

After installing, run:

```bash
python3 /path/to/your/skills/singapore/cdc-voucher-locator/scripts/cdc_voucher_locator.py "Ang Mo Kio Hub" B 500
```

Arguments: `query`, `mode` (A|B|C|D), `radius_m` (default 500)

## Installation

1. Copy the `cdc-voucher-locator` folder into your Hermes skills directory:
   ```
   <hermes_home>/skills/singapore/cdc-voucher-locator/
   ```
2. Update the paths in this file (SKILL.md) to match your install location
3. First run downloads ~2MB of data; subsequent runs skip if unchanged

## Modes

| Mode | Trigger | What it shows |
|------|---------|---------------|
| **A** — Generic | Default / "CDC vouchers near X" | Supermarkets + Hawker & Heartland sub-categorized (F&B, Beauty, Health, Retail, Home, Services, Other) + Budget Meal |
| **B** — Food | "food", "eat", "makan", "dine" | Only food-related merchants, sorted by recommendation |
| **C** — Supermarkets | "supermarket", "grocery", "groceries" | Only supermarkets, sorted by distance |
| **D** — Budget Meal | "budget", "cheap", "affordable" | Only budget-meal tagged merchants |

## Data Sources

Two files from the GoWhere CDN (updated regularly):
- **Main merchants** (`data.gzip`): ~25,500 hawker/heartland merchants → type `HAWKER_HEARTLAND_MERCHANT`
- **Supermarkets** (`data_supermarket.json`): ~400 supermarkets → type `SUPERMARKET`
- Base URL: `https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/`

Official search page: `https://www.gowhere.gov.sg/cdcvouchers?result=addr~{POSTAL}&sort=relevance&status=success`

## Workflow (for the agent)

### Step 1: Detect mode from user query
- "food/eat/makan/dine" → Mode B
- "supermarket/grocery/groceries" → Mode C
- "budget/cheap/affordable" → Mode D
- Default → Mode A

### Step 2: Run the helper script
```bash
python3 <skill_dir>/scripts/cdc_voucher_locator.py "Ang Mo Kio Hub" B 500
```

The script handles:
- **Caching** data to `~/.hermes/cache/cdc-vouchers/` (only re-downloads if `Last-Modified` changed)
- **Geocoding** via OneMap public API (free, no auth key)
- **Haversine filter** with auto-expand if < 5 results (500m → up to 1km)
- **All filtering and categorization** (food keywords, sub-categories, budget meal)
- Returns **JSON** output for you to format

### Step 3: Web research for ratings (Mode B: Food)
1. Search: `"best food {location} hawker CDC voucher"`
2. Cross-reference with results list
3. Assign ⭐ ratings (⭐⭐⭐⭐⭐ = well-known, etc.)
4. If web_search fails, fall back to distance-sorted with a note

### Step 4: Format report
**Mode B (Food):**
```
=== CDC Voucher Food: {location} (S{postal}) ===
📅 {last_updated} | 📏 {radius}m

🍽 Top Food Picks (sorted by recommendation)

⭐⭐⭐⭐⭐ {name} — {addr} ({dist}m)
   {what they're known for}
⭐⭐⭐⭐ {name} — ...
```

**Mode C (Supermarkets):**
```
=== CDC Voucher Groceries: {location} (S{postal}) ===
📅 {last_updated} | 📏 {radius}m

🏪 Supermarkets ({n})
  • {name} — {addr} ({dist}m) ⭐{rating} | {highlight}
```

### Step 5: Verify
- All results accept CDC vouchers ✓
- Distances correct ✓
- Food mode shows NO non-food merchants ✓

## Hardening Features

- ✅ **Cached data** to `~/.hermes/cache/cdc-vouchers/` — survives restarts
- ✅ **Conditional re-download** checks `Last-Modified` header
- ✅ **Auto-expand radius** from 500m → 1km if < 5 results
- ✅ **Graceful geocode** — falls back, returns error if all fails
- ✅ **50+ food keywords** (English, Chinese, Malay), 6 sub-categories
- ✅ **Supermarket name list** checked first to avoid "rice" in "FairPrice"
- ✅ **Standalone Python script** (`cdc_voucher_locator.py`)

## Pitfalls

- **OneMap auth warning**: Returns `"error": "Authentication token missing"` in JSON even though `results[]` has valid data — ignore the error, use `results[]`
- **Gzip**: Main merchant file is gzip-compressed JSON — the script handles this
- **CDN path**: Must include `/assets/` prefix or you get AccessDenied
- **Null coordinates**: ~2 merchants have null LAT/LON — script skips them
- **Semicolons**: Some addresses end with `;` — script strips them
- **First run**: Downloads ~2MB of data; subsequent runs skip if unchanged
- **OneMap mall ambiguity**: For malls like "Ang Mo Kio Hub", OneMap returns 3 sub-buildings (53/55/57). Use postal 569933 (main shopping centre building)

## Official URL Params

- `result=addr~{POSTAL}` — search by postal code
- `sort=relevance` — sort by relevance (default)
- `voucherType=SUPERMARKET` — filter to supermarkets only
- `voucherType=HAWKER_HEARTLAND_MERCHANT` — filter to hawkers only
- `filters=BUDGETMEAL` — budget meal filter
- `status=success` — confirms search completed

Example: `https://www.gowhere.gov.sg/cdcvouchers?result=addr~569933&sort=relevance&voucherType=HAWKER_HEARTLAND_MERCHANT&status=success`

## OneMap Geocoding API

```
GET https://www.onemap.gov.sg/api/common/elastic/search?searchVal={query}&returnGeom=Y&getAddrDetails=Y&pageNum=1
```

Returns: LATITUDE, LONGITUDE, POSTAL, ADDRESS, BUILDING. Public API — no auth key needed.