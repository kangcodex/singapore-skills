# NEA Realtime Fetchers

The `air-quality-advisor-skill` uses 4 realtime NEA endpoints plus OneMap for geocoding. All NEA endpoints are anonymous (no API key required) and serve JSON.

## Endpoints

| Fetcher                     | URL (relative to v1 base)                                | Refresh cadence |
| --------------------------- | --------------------------------------------------------- | --------------- |
| `fetch_psi()`               | `/v1/environment/psi`                                     | 1 hour          |
| `fetch_pm25()`              | `/v1/environment/pm25`                                    | 1 hour          |
| `fetch_uv()`                | `/v1/environment/uv`                                      | 1 hour          |
| `fetch_four_day_forecast()` | `/v1/environment/4-day-weather-forecast`                  | 30 min          |

The base URL is `https://api.data.gov.sg/v1/environment/`. All four endpoints are routed through the v2 dataset flow when an API key is present (faster, more reliable); otherwise they fall back to the v1 endpoint directly.

## Response shapes

### `fetch_psi()`

```json
{
  "items": [
    {
      "region": "national",
      "reading": {
        "psi_twenty_four_hourly": {"national": 42, "west": 45, "east": 39, ...}
      }
    },
    {"region": "west", "reading": {"psi_twenty_four_hourly": {"national": 45}}},
    ...
  ]
}
```

The skill reads `items[0].reading.psi_twenty_four_hourly.national` for the national PSI value.

### `fetch_pm25()`

```json
{
  "items": [
    {
      "region": "national",
      "reading": {
        "pm25_one_hourly": {"national": 12}
      }
    }
  ]
}
```

The skill reads `items[0].reading.pm25_one_hourly.national`. Note: some v1 payloads use `pm25_twenty_four_hourly` instead of `pm25_one_hourly`; the skill tries both.

### `fetch_uv()`

```json
{
  "items": [
    {
      "index": [
        {"value": 6, "desc": "High"}
      ]
    }
  ]
}
```

The skill reads `items[0].index[0].value` for the UV index. (Some legacy payloads have `items[0].index` as a single integer; the skill handles both shapes.)

### `fetch_four_day_forecast()`

```json
{
  "items": [
    {
      "timestamp": "2026-06-22T00:00:00+08:00",
      "forecasts": [
        {"area": "Bishan", "forecast": "Afternoon thundery showers"},
        {"area": "Bishan", "temperature": {"low": 25, "high": 33}},
        {"area": "Bishan", "relative_humidity": {"low": 60, "high": 95}},
        {"area": "Bishan", "wind": {"speed": {"low": 5, "high": 15}}},
        ...
      ]
    },
    ...
  ]
}
```

The skill groups by date (the day-level `timestamp`), then for each day picks the first `forecast` text, the `temperature.low/high`, `relative_humidity.low/high`, and `wind.speed.low/high`. If a day has no humidity or wind, those fields are `null` in the output (not an error).

## Caching

All realtime calls go through `singapore_api.request_json`, which writes to `~/.hermes/cache/v1|<endpoint_path>/<sha1>.json`. NEA's own cache is ~5-15 minutes; the skill's cache is fresh-as-fetched until the upstream `Last-Modified` changes.

When the user re-runs the script within the cache window, all 4 endpoints are free.

## Quirks

- **No API key required.** All 4 NEA endpoints work anonymously.
- **`items[0]` is "national" for PSI and PM2.5.** The regional readings are in `items[1..6]`. The skill reads only the national value.
- **Forecast areas are not always present.** Some NEA payloads have only the forecast text and no temperature/humidity. The skill handles missing fields gracefully.
- **NEA uses Singapore local time (SGT, UTC+8) for forecast timestamps.** The skill truncates to the date portion (`2026-06-22`) for the `date` field.

## See also

- `references/health-advisories.md` — the 5-band table the skill uses
- Canonical `docs/api/NEA.md` — the full NEA catalog (109 collections)
