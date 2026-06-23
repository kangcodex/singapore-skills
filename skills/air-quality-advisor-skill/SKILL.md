---
name: air-quality-advisor-skill
description: "Current PSI / PM2.5 / UV index + 4-day forecast for any Singapore location. Returns a single health_advisory string (good / moderate / unhealthy / hazardous) derived from the worst of the three pollutants. Use when the user asks 'is the air safe to run?', 'should I avoid outdoor activity today?', or 'what's the PSI like in BISHAN right now?'."
---

# air-quality-advisor-skill

A real-time Singapore air-quality advisor. Fetches current PSI, PM2.5, and UV index from NEA's public endpoints, classifies each into a 5-band health scale, and emits a single `health_advisory` string driven by the worst of the three. Includes a 4-day forecast pulled from NEA's 4-day weather forecast endpoint.

## Quick Start

```bash
# By address
python3 skills/air-quality-advisor-skill/scripts/air_quality.py --location "Bishan Park"

# By lat,lon
python3 skills/air-quality-advisor-skill/scripts/air_quality.py --location 1.3508,103.8494

# By 6-digit Singapore postcode
python3 skills/air-quality-advisor-skill/scripts/air_quality.py --postcode 570123
```

Stdlib only — no `pip install`. No auth required for NEA endpoints (anonymous access works).

## Triggers

Run this skill when the user says any of:

- "Is the air safe to run at MacRitchie right now?"
- "Should I avoid outdoor activity today?"
- "What's the PSI in Bishan like right now?"
- "Will the haze be bad this afternoon?"
- "Is the UV high enough that I need sunscreen?"

Do not run for: historical air quality, air quality outside Singapore, or for specific pollutant source attribution (PSI doesn't tell you what's burning).

## How the advisory is computed

The skill classifies each of three pollutants into a band, then picks the worst band:

```
band:    good → moderate → unhealthy → very_unhealthy → hazardous
         (or: low → moderate → high → very_high → extreme, for UV)
```

The `health_advisory` is a plain-language string for the worst band. Examples:

- All three are "good" / "low" → `"Good for outdoor activities"`
- UV is "extreme", others fine → `"Extreme UV — avoid sun exposure, protect skin"`
- PSI is "hazardous" → `"Hazardous — avoid all outdoor activity, stay indoors"`

The PM2.5 24-hour bands follow the US EPA / NEA standard:
- 0-12: good
- 13-55: moderate
- 56-150: unhealthy
- 151-250: very_unhealthy
- 251+: hazardous

The PSI bands are NEA's local scale (24-hour average):
- 0-50: good
- 51-100: moderate
- 101-200: unhealthy
- 201-300: very_unhealthy
- 301+: hazardous

The UV index bands follow WHO:
- 0-2: low
- 3-5: moderate
- 6-7: high
- 8-10: very_high
- 11+: extreme

## CLI

| Flag          | Required | Description                                                                                            |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------ |
| `--location`  | one of   | Address (e.g. `"Bishan Park"`) OR `lat,lon` pair (e.g. `1.3508,103.8494`)                              |
| `--postcode`  | one of   | 6-digit Singapore postcode (e.g. `570123`)                                                             |

`--location` and `--postcode` are mutually exclusive. The lat,lon form of `--location` is detected by the presence of a comma; addresses with commas are rejected.

## Workflow

1. **Resolve location.** `--location <address>` → `geocode(address)`. `--location <lat,lon>` → parse floats. `--postcode <6-digit>` → validate format, then `geocode(postcode)`.
2. **Fetch PSI** (national + 5 regions). `fetch_psi()` returns the realtime PSI payload.
3. **Fetch PM2.5** (national). `fetch_pm25()` returns the realtime PM2.5 payload.
4. **Fetch UV** (national). `fetch_uv()` returns the realtime UV index.
5. **Fetch 4-day forecast.** `fetch_four_day_forecast()` returns 4 days of forecast text + temperature + humidity + wind per area.
6. **Classify each pollutant.** `_classify_psi`, `_classify_pm25`, `_classify_uv` → band + advisory text.
7. **Worst-band health_advisory.** `_health_advisory(psi_band, pm25_band, uv_band)` → plain-language recommendation.
8. **Forecast summary.** `_forecast_summary(forecast_data)` → 4-day list with date / forecast text / temperature / humidity / wind.
9. **Output JSON.** All fields per the schema below.

## Output shape (canonical)

```json
{
  "current": {
    "psi": {
      "value": 42,
      "band": "good",
      "advisory": "Good for outdoor activities"
    },
    "pm25": {
      "value": 12,
      "band": "good",
      "advisory": "Good for outdoor activities"
    },
    "uv": {
      "value": 5,
      "band": "moderate",
      "advisory": "Moderate UV — wear sunscreen"
    }
  },
  "health_advisory": "Moderate UV — wear sunscreen",
  "forecast": {
    "next_4_days": [
      {
        "date": "2026-06-22",
        "forecast": "Afternoon thundery showers",
        "temperature_low_c": 25,
        "temperature_high_c": 33,
        "relative_humidity_low_pct": 60,
        "relative_humidity_high_pct": 95,
        "wind_speed_low_kmh": 5,
        "wind_speed_high_kmh": 15
      },
      {
        "date": "2026-06-23",
        "forecast": "Partly cloudy",
        "temperature_low_c": 26,
        "temperature_high_c": 34
      }
    ]
  },
  "location": {
    "source": "address",
    "address": "Bishan Park",
    "lat": 1.3615,
    "lon": 103.8485
  }
}
```

## Data sources

- **NEA PSI** (realtime) — `fetch_psi()`. See `references/nea-realtime.md`.
- **NEA PM2.5** (realtime) — `fetch_pm25()`.
- **NEA UV index** (realtime) — `fetch_uv()`.
- **NEA 4-day forecast** — `fetch_four_day_forecast()`.
- **OneMap geocoder** for address / postcode resolution.

Cross-references: canonical `docs/api/NEA.md` for the full NEA catalog.

## Caching

All NEA realtime calls go through `singapore_api.request_json`, which writes to `~/.hermes/cache/<namespace>/<sha1>.json`. The NEA endpoints themselves are cached on the server side for ~5-15 minutes; the skill's cache amplifies this.

Namespaces used:
- `v1|psi` for PSI
- `v1|pm25` for PM2.5
- `v1|uv` for UV
- `v1|four_day_forecast` for the 4-day forecast
- `onemap:search` for geocoding

## Hardening

- **Mutually exclusive flags.** `--location` and `--postcode` cannot be combined; argparse exits with an error.
- **Postcode validation.** Must be exactly 6 digits.
- **No top-level network.** `singapore_api` is lazy; no calls at import time.
- **Reading unavailable is graceful.** If a fetcher returns `None` for the value, the band is `unknown` and the advisory is `"Reading unavailable"`. The worst-band logic skips `unknown`.
- **Address geocoding failure is graceful.** Returns `{"error": "address not found: <query>"}` with exit 0.
- **Latency budget: < 500ms end-to-end** (all fetchers are realtime + cached).

## Pitfalls

- **PSI is a 24-hour average.** A single reading can lag a sudden haze event by up to 24 hours. For real-time haze (e.g. a burning peat bog), check the 1-hour PM2.5 instead.
- **The 5-band table is fixed.** It does not adapt to NEA's special advisories (e.g. "unhealthy for sensitive groups" on PSI 100-200). Treat the band as an indicator, not a directive.
- **Forecast area may not match your location.** NEA's 4-day forecast is per-area (Bishan, Jurong, etc.). The skill pulls the first area in the response; if you need a specific area, the skill's location parameter is cosmetic.
- **UV index is for the national peak.** It does not adjust for shade, altitude, or surface reflection. A reading of 8 in the open is more dangerous than 8 in the shade.
- **No PM10.** The skill reports PM2.5 only. PM10 is a different (and usually higher) number; if you need both, that's a future enhancement.
- **Geocoder is the only network call that requires external services.** NEA endpoints are anonymous; OneMap requires internet but no auth.

## Tests

Smoke tests use stdlib `unittest` + `unittest.mock` to stub `fetch_psi`, `fetch_pm25`, `fetch_uv`, `fetch_four_day_forecast`, and `geocode`:

```bash
python3 -m unittest discover -s skills/air-quality-advisor-skill/tests
```

The suite covers:
- Location resolution (address, postcode, lat,lon)
- Postcode validation (5-digit rejected)
- PSI / PM2.5 / UV classification (good / unhealthy / hazardous / extreme)
- Health advisory worst-band logic
- Forecast summary (group by date, extract fields)
- Assess end-to-end (all good, all hazardous)
- Module import + public surface
- No top-level network calls

## References

- `references/nea-realtime.md` — NEA endpoint shapes, response payloads, example outputs
- `references/health-advisories.md` — the 5-band table with NEA citations
- `../docs/api/NEA.md` — canonical NEA catalog (109 collections)

## Install

```bash
npx skills add kangcodex/singapore-skills --skill air-quality-advisor-skill
```

The skill ships `scripts/singapore_api.py` as a per-skill copy (synced from the canonical at the repo root via `scripts/sync_singapore_api.py`). No runtime dependency on the parent repo.
