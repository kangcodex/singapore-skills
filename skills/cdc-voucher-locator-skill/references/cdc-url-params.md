# GoWhere.gov.sg URL Parameters

## Search URL Pattern

```
https://www.gowhere.gov.sg/cdcvouchers?result={type}~{value}&sort={sort}&status=success
```

### `result` param
| Pattern | Example | Description |
|---------|---------|-------------|
| `addr~{postal}` | `result=addr~569933` | Search by postal code (6 digits) |
| `gps~{lat},{lon}` | `result=gps~1.369,103.848` | Search by GPS coordinates |

### `sort` param
| Value | Description |
|-------|-------------|
| `relevance` | Default — Fuse.js fuzzy search ranking |
| `ascending` | Sort A-Z by name |
| `descending` | Sort Z-A by name |

### `status` param
| Value | Meaning |
|-------|---------|
| `success` | Search completed successfully |
| (absent) | Initial page load, no search performed |

### `voucherType` param (filter)
| Value | Filter |
|-------|--------|
| `SUPERMARKET` | Show only supermarkets |
| `HAWKER_HEARTLAND_MERCHANT` | Show only hawker/heartland merchants |

Can be comma-separated for multiple: `?voucherType=SUPERMARKET,HAWKER_HEARTLAND_MERCHANT`

### `filters` param (secondary filter)
| Value | Filter |
|-------|--------|
| `BUDGETMEAL` | Show only budget-meal-tagged merchants |

## Examples
```
# Search AMK Hub (postal), sort by relevance
/cdcvouchers?result=addr~569933&sort=relevance&status=success

# Search Pasir Ris, supermarkets only
/cdcvouchers?result=addr~519634&voucherType=SUPERMARKET&status=success

# Search by GPS, budget meal only
/cdcvouchers?result=gps~1.369,103.848&filters=BUDGETMEAL&status=success
```

## Internal API Behavior

The site loads ALL data client-side (two JSON files from CDN), then:
1. Geocodes the address via OneMap if needed
2. Filters merchants within ~2km of the target
3. Applies Fuse.js fuzzy search on merchant names
4. Applies voucherType and filters from URL params
5. Sorts results (relevance = Fuse.js score, ascending/descending = name)

No server-side search — the URL params just pre-populate the on-page filters.