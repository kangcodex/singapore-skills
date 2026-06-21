# OneMap API Reference

Public geocoding endpoint (no API key required):

```
GET https://www.onemap.gov.sg/api/common/elastic/search
  ?searchVal={query}
  &returnGeom=Y
  &getAddrDetails=Y
  &pageNum=1
```

## Response Structure

```json
{
  "found": 4,
  "totalNumPages": 1,
  "pageNum": 1,
  "results": [
    {
      "SEARCHVAL": "PASIR RIS MRT STATION (EW1)",
      "BLK_NO": "10",
      "ROAD_NAME": "PASIR RIS CENTRAL",
      "BUILDING": "PASIR RIS MRT STATION (EW1)",
      "ADDRESS": "10 PASIR RIS CENTRAL PASIR RIS MRT STATION (EW1) SINGAPORE 519634",
      "POSTAL": "519634",
      "X": "40905.597462655",
      "Y": "39449.9823396821",
      "LATITUDE": "1.37304331635804",
      "LONGITUDE": "103.949284527763"
    }
  ]
}
```

## Key Resolution Examples (verified)

| Query | Primary Result | Lat | Lon | Postal |
|-------|---------------|-----|-----|--------|
| Ang Mo Kio Hub | AMK Hub 53 | 1.369389 | 103.848478 | 569933 |
| Pasir Ris MRT | Pasir Ris MRT (EW1) | 1.373043 | 103.949285 | 519634 |
| Jurong Point | (mdx find for others) | — | — | — |

## Pitfalls

- OneMap returns ALL matches, not just the best one. For malls, multiple sub-buildings (53/55/57 AMK Hub) may appear. Pick the primary postal for the main shopping centre.
- The public elastic endpoint works without auth. The private `/xgw/onemap/search` endpoint on gowhere.gov.sg requires the site's referer.
- SVY21 coordinates (X/Y) are also returned — use LATITUDE/LONGITUDE for haversine.
- "NIL" as POSTAL means no postal code available — skip those.
- For MRT stations, prefer the station building result (e.g., "(EW1)" suffix) over exit-specific results.