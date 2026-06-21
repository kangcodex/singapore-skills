# CDC (Community Development Council) Vouchers — `gowhere.gov.sg` Data

The **CDC Vouchers** scheme is a Singapore government initiative where every
Singaporean household receives vouchers (typically S$300–500 per cycle) to spend
at heartland shops, hawkers, and supermarkets. The official locator lives at
**https://www.gowhere.gov.sg/cdcvouchers/** and is backed by a public CloudFront
CDN that exposes the full merchant + supermarket + micro-site catalogues as raw
JSON. No authentication is required.

There are four distinct endpoints that power the site:

| # | URL | What it returns | Approx size |
|---|-----|-----------------|-------------|
| 1 | `assets/cdcvouchersgowhere/data_supermarket.json?v=2` | Supermarket chain branches (NTUC, FairPrice, Giant, Sheng Siong, etc.) | 176 KB |
| 2 | `assets/sites/data.sites.json` | Master list of all 15 GoWhere micro-sites (CDC, HealthierSG, BudgetMeal, …) | 14 KB |
| 3 | `api/xgw/onemap/search?searchVal=…` | OneMap geocoding proxied through GoWhere | JSON |
| 4 | **`assets/cdcvouchersgowhere/data.gzip?v=2`** | **Master CDC merchant list — heartland shops + hawker stalls, with BudgetMeal flag** | **11 MB** |

The fourth endpoint (`data.gzip?v=2`) is the canonical, most up-to-date source
because it merges both heartland merchants and hawker stalls in a single
payload, and includes a `filters.secondary.budgetmeal` flag to disambiguate
the **624** stalls that also participate in the BudgetMeal programme (a
subscheme run by the same Mayor's Committee / CDC office).

> Despite the `.gzip` suffix, the file is **plain JSON on disk** — CloudFront
> gzips it on the wire when the client sends `Accept-Encoding: gzip`. `curl
> --compressed` (or any HTTP client with transparent gzip) is enough to read it.

---

## 1. Base URLs & infrastructure

| Layer | Host | Notes |
|---|---|---|
| Edge CDN (static data) | `prd-tmp.cdn.gowhere.gov.sg` | CloudFront, `vary: Accept-Encoding`, CORS `*` |
| API gateway (proxied) | `prd-tmp.api.gowhere.gov.sg` | Forwards OneMap calls |
| Site front-end | `https://www.gowhere.gov.sg` | React SPA, the `Referer` must match |

Required request headers (any modern browser UA is accepted; the CDN does
**not** enforce a strict referer or token but the production app sets them):

```http
accept: application/json, text/plain, */*
origin: https://www.gowhere.gov.sg
referer: https://www.gowhere.gov.sg/
user-agent: Mozilla/5.0 …      # any current Chrome/Safari/Firefox UA
```

No `Authorization` header. No cookies. No API key. The `?v=2` (or `?v=N`) query
parameter is a **cache-buster**; bump it to force a fresh payload.

---

## 2. Master merchant list — `data.gzip?v=2`

**Endpoint**

```
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data.gzip?v=2
```

**Verified response** (`200 OK`, `Content-Type: application/json`, ~11 MB,
served from CloudFront edge `SIN3-P4`):

```json
{
  "lastUpdated": "21 Jun 2026",
  "locations": [ /* 25,644 entries */ ]
}
```

### 2.1 Top-level shape

| Field | Type | Notes |
|---|---|---|
| `lastUpdated` | string (human date) | e.g. `"21 Jun 2026"` — the date the CDC published the dataset, **not** an ISO timestamp. Update cadence is typically weekly or after major campaign changes. |
| `locations` | array<object> | Always 25,644 entries at the time of writing. Each entry is one merchant / hawker stall. |

### 2.2 Per-location schema

Every entry has the same 10 fields:

| Field | Type | Example | Notes |
|---|---|---|---|
| `id` | string (UUID) | `merchant_dc06fa4b-0839-445a-8725-8e4328e52407` | Always prefixed with `merchant_`. |
| `entityId` | string (UUID) | identical to `id` in this dataset | Redundant; carry both for forward-compat. |
| `name` | string | `". SG SUPPLY"`, `"119 DRINKS"` | Free-text business name. Leading dots and spaces are present in the source — trim when displaying. |
| `address` | string | `"861 North Bridge Road, #01-83,  S198783;"` | HDB-style: `<BLK> <ROAD>, #<UNIT>-<FLOOR>, S<POSTAL>;`. Note the **double space** before `S<POSTAL>` and the trailing `;` — both are data-quality artefacts from the upstream CRM. Parse the postal out of the trailing `S\d{6};` substring, or use the dedicated `postalCode` field. |
| `postalCode` | string (6-digit) | `"198783"` | Clean. Use this for distance lookups, not `address`. |
| `type` | enum string | `"HAWKER_HEARTLAND_MERCHANT"` | **Only one value appears in `data.gzip`.** See §2.4. |
| `LAT` | number (WGS84) | `1.30563433652207` | 14-digit precision — fits SVY21 → WGS84 conversion. |
| `LON` | number (WGS84) | `103.863909336656` | 14-digit precision. |
| `filters.vouchers.supermarket` | bool | `false` | Always `false` here. Use `data_supermarket.json` for supermarkets. |
| `filters.vouchers.hawker_heartland_merchant` | bool | `true` | Always `true` here. |
| `filters.secondary.budgetmeal` | bool | `false` (or `true`) | `true` for the **624** stalls that also accept BudgetMeal — the "subsidised S$5 / S$3 meal" programme. See §2.3. |
| `lastResetDate` | string (`YYYY-MM-DD`) or `""` | `"2024-06-12"`, `"2025-02-19"`, or `""` | Date the merchant's voucher quota was last reset. **`""` is common** — treat empty string as "never reset / unknown" and display as `—`. |

### 2.3 The two filter dimensions

The `filters` object is a small DAG of booleans. Today only two top-level
groups exist:

```
filters
├── vouchers          ← "which CDC schemes does this outlet accept?"
│   ├── supermarket              (bool) — true ⇒ outlet is a supermarket
│   └── hawker_heartland_merchant(bool) — true ⇒ outlet is a CDC-Vouchers merchant
└── secondary         ← "which other GoWhere sub-schemes?"
    └── budgetmeal               (bool) — true ⇒ outlet is in the BudgetMeal programme
```

**Boolean combinations actually observed in the wild:**

| `vouchers.supermarket` | `vouchers.hawker_heartland_merchant` | `secondary.budgetmeal` | Count | Where to find |
|---|---|---|---|---|
| `false` | `true` | `false` | **25,020** | `data.gzip?v=2` |
| `false` | `true` | `true`  | **624**   | `data.gzip?v=2` |
| `false` | `false` | `false` | **402**   | `data_supermarket.json?v=2` |

**Rule of thumb:** the `type` field is the type-of-outlet, and the
`filters` block tells you which GoWhere programme(s) it appears in. To
render a "CDC voucher-accepting" map: any row with
`filters.vouchers.hawker_heartland_merchant == true` OR
`type == "SUPERMARKET"` (the supermarket JSON does not always set
`filters.vouchers.supermarket = true`, so do **not** rely on it for the
supermarket set — use the dedicated endpoint).

### 2.4 The `type` enum

`data.gzip?v=2` currently ships a single value: `"HAWKER_HEARTLAND_MERCHANT"`.
The other values observed in the broader GoWhere ecosystem (e.g.
`"SUPERMARKET"` in `data_supermarket.json`) hint that the schema is designed
to absorb more outlet classes in future schema versions. Treat `type` as
open-ended and switch on it rather than asserting a closed set.

### 2.5 Sample entries

Hawker / heartland merchant (normal):

```json
{
  "id": "merchant_dc06fa4b-0839-445a-8725-8e4328e52407",
  "entityId": "merchant_dc06fa4b-0839-445a-8725-8e4328e52407",
  "name": ". SG SUPPLY",
  "address": "861 North Bridge Road, #01-83,  S198783;",
  "postalCode": "198783",
  "type": "HAWKER_HEARTLAND_MERCHANT",
  "LAT": 1.30563433652207,
  "LON": 103.863909336656,
  "filters": {
    "vouchers": { "supermarket": false, "hawker_heartland_merchant": true },
    "secondary": { "budgetmeal": false }
  },
  "lastResetDate": "2024-06-12"
}
```

Same shape, with BudgetMeal flag set (subsidised-meal stall):

```json
{
  "id": "merchant_c872bc63-9744-4899-a644-8b891bd42769",
  "entityId": "merchant_c872bc63-9744-4899-a644-8b891bd42769",
  "name": "119 DRINKS",
  "address": "119 Aljunied Avenue 2, #01-54,  S380119;",
  "postalCode": "380119",
  "type": "HAWKER_HEARTLAND_MERCHANT",
  "LAT": 1.32012887290025,
  "LON": 103.886058091225,
  "filters": {
    "vouchers": { "supermarket": false, "hawker_heartland_merchant": true },
    "secondary": { "budgetmeal": true }
  },
  "lastResetDate": "2025-02-19"
}
```

### 2.6 curl recipe

```bash
curl --compressed \
  'https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data.gzip?v=2' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'origin: https://www.gowhere.gov.sg' \
  -H 'referer: https://www.gowhere.gov.sg/' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -o cdc_merchants.json

# Sanity-check: ~11 MB, 25,644 locations
ls -la cdc_merchants.json
python3 -c "import json; d=json.load(open('cdc_merchants.json')); print(len(d['locations']), 'locations, lastUpdated =', d['lastUpdated'])"
```

`curl --compressed` is mandatory — without it, the file is delivered
gzipped on the wire and you'll save a binary blob.

### 2.7 Quick filtering recipes (jq + Python)

Filter to BudgetMeal stalls only:

```bash
jq '.locations[] | select(.filters.secondary.budgetmeal == true)' cdc_merchants.json
```

Filter to a single postal district (e.g. Tampines = "52"):

```bash
jq '.locations[] | select(.postalCode | startswith("52"))' cdc_merchants.json
```

Group by type and count:

```bash
jq -r '.locations[].type' cdc_merchants.json | sort | uniq -c
#   25644 HAWKER_HEARTLAND_MERCHANT
```

Python equivalent (full pipeline):

```python
import json, urllib.request

req = urllib.request.Request(
    "https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data.gzip?v=2",
    headers={
        "accept": "application/json",
        "origin": "https://www.gowhere.gov.sg",
        "referer": "https://www.gowhere.gov.sg/",
        "user-agent": "Mozilla/5.0",
    },
)
with urllib.request.urlopen(req) as r:
    data = json.load(r)            # urllib transparently decodes gzip

print(data["lastUpdated"], len(data["locations"]))
hawker  = [l for l in data["locations"] if l["filters"]["vouchers"]["hawker_heartland_merchant"]]
budget  = [l for l in data["locations"] if l["filters"]["secondary"]["budgetmeal"]]
print(len(hawker), "hawker/heartland,", len(budget), "with budgetmeal")
```

---

## 3. Supermarket list — `data_supermarket.json?v=2`

**Endpoint**

```
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data_supermarket.json?v=2
```

**Response** (`200 OK`, ~176 KB, last updated `2 June 2026`):

```json
{
  "lastUpdated": "2 June 2026",
  "locations": [ /* 402 SUPERMARKET entries */ ]
}
```

### 3.1 Schema

Identical to the master list (§2.2), with these differences:

| Field | Supermarket value | Notes |
|---|---|---|
| `id` | numeric string `"1"`, `"2"`, … | Integer id assigned by the supermarket registry, not a UUID. |
| `entityId` | identical to `id` | |
| `type` | `"SUPERMARKET"` | Only value present. |
| `filters.vouchers.supermarket` | `false` | ⚠️ **Counter-intuitive**: every supermarket row has `supermarket: false` here. Don't use this flag to detect supermarkets — use `type == "SUPERMARKET"` instead. |
| `filters.vouchers.hawker_heartland_merchant` | `false` | |
| `filters.secondary` | absent | Supermarkets never carry a BudgetMeal flag. |
| `lastResetDate` | `""` | Always empty string for supermarkets. |
| `address` | `"693 Woodlands Avenue 6 #01-01"` | Cleaner than the hawker list — no `S<POSTAL>;` suffix. |

### 3.2 Sample

```json
{
  "id": "1",
  "entityId": "1",
  "name": "Ang Mo Supermarket",
  "address": "693 Woodlands Avenue 6 #01-01",
  "postalCode": "730693",
  "LAT": 1.43808788056635,
  "LON": 103.803764959272,
  "type": "SUPERMARKET",
  "filters": {
    "vouchers": { "supermarket": false, "hawker_heartland_merchant": false }
  },
  "lastResetDate": ""
}
```

### 3.3 curl recipe

```bash
curl --compressed \
  'https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data_supermarket.json?v=2' \
  -H 'accept: application/json' \
  -H 'origin: https://www.gowhere.gov.sg' \
  -H 'referer: https://www.gowhere.gov.sg/' \
  -o cdc_supermarkets.json
```

---

## 4. GoWhere micro-site registry — `data.sites.json`

**Endpoint**

```
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/sites/data.sites.json
```

**Response**: a top-level JSON array of 15 site descriptors. No envelope, no
`lastUpdated`. Each entry is a complete micro-site record:

| Field | Type | Example |
|---|---|---|
| `link` | URL (string) | `https://gowhere.gov.sg/cdcvouchers/` |
| `favicon` | URL (string) | `https://cdn.gowhere.gov.sg/assets/sites/favicons/revamped/site-cdcvouchersgowhere.svg` |
| `image` | URL (string) | hero image for the directory card |
| `primaryColor` | hex string | `"#E8FFF3"` — accent colour used in the card UI |
| `header` | object `{english, chinese, malay, tamil}` | localised name in all four official languages |
| `description` | object `{english, chinese, malay, tamil}` | one-sentence tagline, localised |
| `createdAt` | `YYYY-MM-DD` | `2023-01-01` |
| `updatedAt` | `YYYY-MM-DD` | `2023-01-01` |
| `featured` | bool (optional) | `true` for promoted entries |

**All 15 sites at time of writing:**

| Link | English name |
|---|---|
| `https://gowhere.gov.sg/healthiersg/` | HealthierSGGoWhere |
| `https://gowhere.gov.sg/budgetmeal/` | BudgetMealGoWhere |
| `https://supportgowhere.life.gov.sg/` | SupportGoWhere |
| **`https://gowhere.gov.sg/cdc/`** | **CDCGoWhere** |
| **`https://gowhere.gov.sg/cdcvouchers/`** | **CDCVouchersGoWhere** (this dataset) |
| `https://gowhere.gov.sg/vaccine/` | VaccineGoWhere |
| `https://gowhere.gov.sg/testcentres/` | TestCentresGoWhere |
| `https://supportgowhere.life.gov.sg/services/SVC-…/active-ageing-centres-aac` | Active Ageing Centres |
| `https://gowhere.gov.sg/hsgevents/` | HealthierSGEventsGoWhere |
| `https://gowhere.gov.sg/tampinescares/` | TampinesCaresGoWhere |
| `https://gowhere.gov.sg/hpbfitnesstracker/` | HPBFitnessTrackerGoWhere |
| `https://gowhere.gov.sg/passiondeals/` | PAssionDealsGoWhere |
| `https://gowhere.gov.sg/artseverywherecdc` | ArtsEverywhere@CDC |
| `https://gowhere.gov.sg/gp/` | GPGoWhere |
| `https://gowhere.gov.sg/infantchildminding/` | ChildminderGoWhere |

**curl recipe**

```bash
curl --compressed \
  'https://prd-tmp.cdn.gowhere.gov.sg/assets/sites/data.sites.json' \
  -H 'accept: application/json' \
  -H 'origin: https://www.gowhere.gov.sg' \
  -H 'referer: https://www.gowhere.gov.sg/' \
  -o gowhere_sites.json
```

---

## 5. OneMap search proxy — `prd-tmp.api.gowhere.gov.sg/xgw/onemap/search`

The CDC locator lets users type a postal code or address; the call hits a
GoWhere API gateway which in turn forwards to **OneMap's elastic search
endpoint** (see `Onemap.md` for the upstream surface).

**Endpoint**

```
GET https://prd-tmp.api.gowhere.gov.sg/xgw/onemap/search
    ?searchVal=569933
    &returnGeom=Y
    &getAddrDetails=Y
    &pageNum=1
```

**Sample call (no auth):**

```bash
curl -sL \
  'https://prd-tmp.api.gowhere.gov.sg/xgw/onemap/search?searchVal=569933&returnGeom=Y&getAddrDetails=Y&pageNum=1' \
  -H 'accept: application/json' \
  -H 'origin: https://www.gowhere.gov.sg' \
  -H 'referer: https://www.gowhere.gov.sg/'
```

**Sample response** (`200 OK`):

```json
{
  "found": 3,
  "totalNumPages": 1,
  "pageNum": 1,
  "results": [
    {
      "SEARCHVAL": "ABUNDANT LIFE FAMILY CHURCH",
      "BLK_NO": "53",
      "ROAD_NAME": "ANG MO KIO AVENUE 3",
      "BUILDING": "ABUNDANT LIFE FAMILY CHURCH",
      "ADDRESS": "53 ANG MO KIO AVENUE 3 ABUNDANT LIFE FAMILY CHURCH SINGAPORE 569933",
      "POSTAL": "569933",
      "X": "29711.0075057196",
      "Y": "39028.6385976207",
      "LATITUDE": "1.36923561405404",
      "LONGITUDE": "103.848693181185"
    },
    {
      "SEARCHVAL": "AMK HUB",
      "BLK_NO": "53",
      "ROAD_NAME": "ANG MO KIO AVENUE 3",
      "BUILDING": "AMK HUB",
      "ADDRESS": "53 ANG MO KIO AVENUE 3 AMK HUB SINGAPORE 569933",
      "POSTAL": "569933",
      "X": "29711.0075057196",
      "Y": "39028.6385976207",
      "LATITUDE": "1.36923561405404",
      "LONGITUDE": "103.848693181185"
    }
  ]
}
```

### 5.1 Schema (per `results[]` entry)

| Field | Type | Notes |
|---|---|---|
| `SEARCHVAL` | string | The matched name. |
| `BLK_NO` | string | House/building block number. |
| `ROAD_NAME` | string | UPPERCASE road name. |
| `BUILDING` | string | Building name (often same as `SEARCHVAL`). |
| `ADDRESS` | string | Concatenated single-line address, ending in `SINGAPORE <POSTAL>`. |
| `POSTAL` | string (6-digit) | Singapore postal code. |
| `X` | number (SVY21 easting) | EPSG:3414. |
| `Y` | number (SVY21 northing) | EPSG:3414. |
| `LATITUDE` | number (WGS84) | Already converted by OneMap — no need to call `/convert/3414to4326`. |
| `LONGITUDE` | number (WGS84) | |

### 5.2 Envelope fields

| Field | Type | Notes |
|---|---|---|
| `found` | int | Total number of matches (may be > page size). |
| `totalNumPages` | int | OneMap returns 1 page even when `found > pageSize`; use `pageNum` to paginate explicitly. |
| `pageNum` | int | Echo of the request parameter. |
| `results` | array<object> | Up to ~10 entries per page by default. |

### 5.3 When to use this vs. direct OneMap

- ✅ Use the GoWhere proxy when you've already loaded `data.gzip` and want to
  resolve the user's typed address to a coordinate for "find merchants near
  me" — saves you the cost of caching OneMap responses.
- ❌ Use **direct OneMap** (`www.onemap.gov.sg/api/common/elastic/search`) when
  you need pagination past 10 results, or you need a token-gated endpoint
  (routing, themesvc, popapi, etc.). The GoWhere proxy is read-only and
  unauthenticated.

---

## 6. Discovery & cache headers

All four endpoints sit behind AWS CloudFront with the following cache
directive:

```http
cache-control: public, max-age=0
vary: Accept-Encoding,Origin,Access-Control-Request-Headers,Access-Control-Request-Method
```

In practice the CDN honours a TTL measured in **hours to days** (the `age`
header on a repeat request typically shows `~1500s` for the merchant data
and `~30s` for `data.sites.json`). ETag and `last-modified` are present, so a
conditional GET with `If-None-Match` returns `304` to save bandwidth. Always
honour `304` and only re-parse the JSON when the status is `200`.

CORS is fully open:

```http
access-control-allow-origin: *
access-control-allow-methods: GET
access-control-max-age: 1800
```

…so you can fetch the data from a browser SPA without a proxy.

---

## 7. End-to-end example: find BudgetMeal stalls near a postal code

```python
import json, urllib.request
from math import radians, sin, cos, sqrt, atan2

UA = "Mozilla/5.0"

def fetch(url):
    req = urllib.request.Request(url, headers={
        "accept": "application/json",
        "origin": "https://www.gowhere.gov.sg",
        "referer": "https://www.gowhere.gov.sg/",
        "user-agent": UA,
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)

# 1. Resolve postal -> coordinates via the GoWhere OneMap proxy
geo = fetch(
    "https://prd-tmp.api.gowhere.gov.sg/xgw/onemap/search"
    "?searchVal=520100&returnGeom=Y&getAddrDetails=Y&pageNum=1"
)
lat0, lon0 = float(geo["results"][0]["LATITUDE"]), float(geo["results"][0]["LONGITUDE"])

# 2. Load the master CDC merchant list
merchants = fetch(
    "https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data.gzip?v=2"
)

# 3. Filter to BudgetMeal stalls within ~1 km
def km(a, b, c, d):
    R = 6371.0
    la1, lo1, la2, lo2 = map(radians, [a, b, c, d])
    h = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return 2*R*atan2(sqrt(h), sqrt(1-h))

budget_nearby = [
    m for m in merchants["locations"]
    if m["filters"]["secondary"]["budgetmeal"]
    and km(lat0, lon0, m["LAT"], m["LON"]) <= 1.0
]
print(f"{len(budget_nearby)} BudgetMeal stalls within 1 km of 520100")
```

---

## 8. Quick reference

```text
# Master CDC merchant list (canonical, use this)
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data.gzip?v=2
#   → { lastUpdated, locations[25644] }  ~11 MB
#   → filters.vouchers.hawker_heartland_merchant = true
#   → filters.secondary.budgetmeal            = true on 624 stalls

# Supermarket list
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/cdcvouchersgowhere/data_supermarket.json?v=2
#   → { lastUpdated, locations[402] }  ~176 KB
#   → type = "SUPERMARKET"

# GoWhere micro-site registry
GET https://prd-tmp.cdn.gowhere.gov.sg/assets/sites/data.sites.json
#   → [site, …]  15 entries

# OneMap geocoding (proxied)
GET https://prd-tmp.api.gowhere.gov.sg/xgw/onemap/search
    ?searchVal=<postal-or-string>
    &returnGeom=Y
    &getAddrDetails=Y
    &pageNum=1
#   → { found, totalNumPages, pageNum, results[] }
```

All four are GET, anonymous, served from CloudFront, `Content-Type:
application/json`. Use `curl --compressed` (or any client that transparently
handles `Content-Encoding: gzip`).
