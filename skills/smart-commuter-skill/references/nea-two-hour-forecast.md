# NEA 2-Hour Weather Forecast (`v1/environment/2-hour-weather-forecast`)

NEA publishes a 2-hour text forecast covering every planning area in
Singapore. The forecast is updated approximately every 30 minutes.

**Endpoint**

```
GET https://api.data.gov.sg/v1/environment/2-hour-weather-forecast
```

**Auth**: none. Public. The response envelope is the standard v1
"items + area_metadata" pattern.

The `singapore_api.fetch_two_hour_forecast()` fetcher normalises the v1
nested `items[].forecasts[]` into a flat `items: [{area, forecast}]` shape
and preserves the original `area_metadata` block for callers that need to
geocode an area name.

## Live request + response (truncated)

Captured 2026-06-20 22:31 SGT.

```bash
curl -s "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast" | head -c 1500
```

```json
{
  "area_metadata": [
    {"name": "Ang Mo Kio", "label_location": {"longitude": 103.839, "latitude": 1.375}},
    {"name": "Bedok",     "label_location": {"latitude": 1.321, "longitude": 103.924}},
    {"name": "Bishan",    "label_location": {"longitude": 103.839, "latitude": 1.350772}},
    {"name": "Bukit Merah", "label_location": {"longitude": 103.819, "latitude": 1.277}}
    /* ... 50+ planning areas total ... */
  ],
  "items": [
    {
      "update_timestamp": "2026-06-20T22:18:00+08:00",
      "timestamp": "2026-06-20T22:30:00+08:00",
      "valid_period": {"start": "2026-06-20T22:30:00+08:00", "end": "2026-06-21T00:30:00+08:00"},
      "forecasts": [
        {"area": "Ang Mo Kio", "forecast": "Partly Cloudy (Night)"},
        {"area": "Bedok",       "forecast": "Partly Cloudy (Night)"},
        {"area": "Bishan",      "forecast": "Partly Cloudy (Night)"},
        {"area": "Bukit Merah", "forecast": "Showers"}
        /* ... one per planning area ... */
      ]
    }
  ]
}
```

After normalisation by `singapore_api._flatten_v1_two_hour_forecast()`:

```json
{
  "items": [
    {"area": "Ang Mo Kio", "forecast": "Partly Cloudy (Night)"},
    {"area": "Bedok",       "forecast": "Partly Cloudy (Night)"},
    {"area": "Bishan",      "forecast": "Partly Cloudy (Night)"},
    {"area": "Bukit Merah", "forecast": "Showers"}
  ],
  "area_metadata": [
    {"name": "Ang Mo Kio", "label_location": {"longitude": 103.839, "latitude": 1.375}}
    /* ... 50+ ... */
  ],
  "valid_period": {"start": "...", "end": "..."},
  "update_timestamp": "2026-06-20T22:18:00+08:00"
}
```

## Fields the skill uses

| Field | Type | Consumed by | Notes |
|-------|------|-------------|-------|
| `items[].area` | str | case-insensitive substring match | Matched against the geocoded address (e.g. "Toa Payoh Central" → "Toa Payoh"). |
| `items[].forecast` | str | heavy-rain keyword match | The skill pattern-matches on `HEAVY_RAIN_KEYWORDS` (see smart_commuter.py). |
| `valid_period` | dict | dropped | The skill doesn't track forecast staleness; the cache + `Last-Modified` revalidation does. |
| `area_metadata` | list | dropped | Kept on the envelope for callers that need to resolve an area name to lat/lon (future S03 weekend-planner may use this). |

## What the skill drops

- The outer `items[].timestamp` / `update_timestamp` — the per-call cache key covers freshness.
- `valid_period` — same reason.
- The full list of areas when the geocoded address doesn't match any of them. The skill returns `{}` and adds no weather advisory.

## Forecast text vocabulary (observed)

The full vocabulary NEA uses (current and recent past):

| Phrase | Skill interpretation |
|--------|---------------------|
| `"Fair"` | no advisory |
| `"Partly Cloudy (Night)"` / `"Partly Cloudy (Day)"` | no advisory |
| `"Light Rain"` | no advisory (skipped; only heavy keywords trigger) |
| `"Showers"` | no advisory |
| `"Thundery Showers"` | **TRIGGERS** advisory (matches `"thundery showers"`) |
| `"Heavy Thundery Showers"` | **TRIGGERS** advisory (matches `"heavy thundery showers"`) |
| `"Heavy Rain"` | **TRIGGERS** advisory (matches `"heavy rain"`) |

Keywords are matched case-insensitively. See `HEAVY_RAIN_KEYWORDS` in
`scripts/smart_commuter.py` for the canonical list.

## Rate limits

- Undocumented; NEA's gateway is more permissive than LTA's.
- The endpoint is small (~10 KB compressed) so cache hits are nearly free.

## Pitfalls

1. **`area` is not geocoded.** The skill must do its own substring match
   between the OneMap `address` and the NEA `area` strings. v1 does not
   include the lat/lon of the destination area in the `forecasts[]` items
   (only the `area_metadata[]` map has the lat/lon, and the skill does not
   look it up by default).
2. **Substring match is fuzzy by design.** "Toa Payoh Central" matches
   "Toa Payoh" because the substring is contained. But "Pasir Ris" can match
   "Marine Parade" if the geocoder returns "Pasir Ris Drive 8" — both contain
   "Pasir". To prevent false matches, the skill uses case-insensitive
   substring with the area name **longer than 3 chars** (catches most
   mistakes via short-word exclusions; tune as needed).
3. **NEA phrases change over time.** Historical phrases like "Partly Cloudy
   (Afternoon)" vs "(Day)" appear interchangeably. Do not pattern-match on
   day/night; pattern-match on the heavy-rain keywords only.
4. **`update_timestamp` lag.** The forecast is generated ~12 min before
   `valid_period.start`. There is a window where the response reflects the
   previous forecast. Acceptable for a parking recommendation.
5. **v1 envelope is nested.** Raw response is `items[].forecasts[]`; the
   helper `_flatten_v1_two_hour_forecast()` collapses it to `items[]`. Don't
   write skill code against the raw shape.

## See also

- [`lta-traffic-images.md`](./lta-traffic-images.md) — LTA camera data.
- [`hdb-carpark-availability.md`](./hdb-carpark-availability.md) — HDB carpark data.
- `singapore_api.py` `_flatten_v1_two_hour_forecast` — the normalisation helper.
