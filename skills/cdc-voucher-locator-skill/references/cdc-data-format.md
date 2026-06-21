# CDC Voucher Data Format

Data sourced from the GoWhere CDN (prd-tmp.cdn.gowhere.gov.sg).

## Main Merchant Data (`data.gzip`)

~25,500 merchants. Type: gzip-compressed JSON.

```
{
  "lastUpdated": "13 Jun 2026",
  "locations": [
    {
      "id": "merchant_<uuid>",
      "name": "BEE CHENG HIANG AMK",
      "address": "Ang Mo Kio Avenue 8, #01-2525,  S560702;",
      "postalCode": "560702",
      "type": "HAWKER_HEARTLAND_MERCHANT",
      "LAT": 1.3693,
      "LON": 103.8484,
      "filters": {
        "vouchers": { "supermarket": false, "hawker_heartland_merchant": true },
        "secondary": { "budgetmeal": false }
      },
      "lastResetDate": "2024-06-12"
    }
  ]
}
```

### Key Fields
- **type**: Always `HAWKER_HEARTLAND_MERCHANT` in this file
- **filters.vouchers.supermarket**: `true` = accepts supermarket-type CDC vouchers
- **filters.vouchers.hawker_heartland_merchant**: `true` = accepts hawker-type CDC vouchers
- **filters.secondary.budgetmeal**: `true` = Budget Meal tagged
- **LAT/LON**: Decimal degrees. ~2 merchants have `null` — skip those.
- **address**: May have trailing `;` — strip before display.

## Supermarket Data (`data_supermarket.json`)

~400 supermarkets. Plain JSON (no compression).

```
{
  "lastUpdated": "2 June 2026",
  "locations": [
    {
      "id": "1",
      "name": "NTUC FairPrice",
      "address": "53 Ang Mo Kio Ave 3, Ang Mo Kio Hub #B2-40 (569933)",
      "postalCode": "569933",
      "LAT": 1.3692, "LON": 103.8487,
      "type": "SUPERMARKET",
      "filters": { "vouchers": { "supermarket": false, "hawker_heartland_merchant": false } },
      "lastResetDate": ""
    }
  ]
}
```

### Key Fields
- **type**: Always `SUPERMARKET`
- **IMPORTANT**: `filters.vouchers.supermarket: false` does NOT mean "not a supermarket" — it means this outlet doesn't separately accept the supermarket-type voucher. All entries here ARE supermarkets.
- **address**: Clean, no trailing semicolons.
- **id**: Sequential number (1, 2, 3...), not UUID.

## Known Supermarket Chains (Jun 2026 counts)
| Chain | Outlets | Chain | Outlets |
|-------|---------|-------|---------|
| NTUC FairPrice | 165 | Sheng Siong | 87 |
| Giant | 39 | Prime Supermarket | 28 |
| U Stars | 18 | Ang Mo Supermarket | 10 |
| Hao | 7 | Cold Storage + CS Fresh | ~33 |
| Jason's | ~3 | Hill View Market Place | 1 |