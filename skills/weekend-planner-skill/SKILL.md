---
name: weekend-planner-skill
description: "Plan a Singapore weekend around weather, air quality, UV, and hawker-centre opening hours. Given a location, activity, and time, recommends indoor or outdoor pivots when PSI / UV / hawker closures are bad. Pulls from NEA (PSI, UV, two-hour forecast, hawker closures) and ActiveSG facilities. Use this skill whenever the user asks 'what should I do this weekend', 'is it safe to [outdoor activity] in [town] Saturday', 'where can I eat that's open', or wants a Singapore weekend plan that handles weather and air quality."
---

# Weekend Planner

## Quick start

```bash
python3 skills/weekend-planner-skill/scripts/weekend_planner.py \
    --location "Botanic Gardens" --activity "makan" --time "Saturday noon"
```

Returns JSON:

```json
{
  "location": {"query": "Botanic Gardens", "lat": 1.3194, "lon": 103.8156, "address": "..."},
  "activity": "makan",
  "time": "Saturday noon",
  "psi": {"national": 32, "tier": "good"},
  "uv": {"index": 8, "tier": "very_high"},
  "weather": {"area": "Botanic Gardens", "forecast": "Partly Cloudy", "advisory": null},
  "hawker_closures": [
    {"name": "Adam Road Food Centre", "closed_now": false, "next_closure": {"start": "2026-07-01", "end": "2026-07-15", "reason": "Quarterly cleaning"}}
  ],
  "alternates": [],
  "recommendation": "UV 8 is very high — bring sunscreen. Adam Road Food Centre is open; no closure today."
}
```

## When the agent triggers this skill

Match user intent that combines **time + place + activity** in a single question:

- "What should I do this Saturday at Botanic Gardens?"
- "Family makan plan for Sunday afternoon in Bishan — anything to watch out for?"
- "Plan my Saturday morning — outdoors with the kids, then makan nearby"
- "Hawker food near me on a Sunday noon, given today's weather"

If the user asks only for weather OR only for a place OR only for food, defer to the more focused skill (`smart-commuter-skill` for routing, `hawker-discover-skill` for CDC-voucher food).

## Workflow

1. **Geocode the location** via `geocode()`. Reject unresolvable queries with a clear error.
2. **Fetch the three real-time signals in parallel** (no actual parallelism in stdlib — sequence them with a single retry budget per call):
   - `fetch_psi()` — national reading + 5 regions.
   - `fetch_uv()` — single daily peak index.
   - `fetch_two_hour_forecast()` — pick the `area` whose label best matches the geocoded address; fuzzy-substring match falls back to "Central".
3. **Classify each signal into a tier** (`psi_tier`, `uv_tier`). The tiers are documented constants — see Hardening.
4. **Decide the activity pivot** (see Decision rules). Pivot text uses the geocoded address for context, not a generic template.
5. **Fetch the NEA hawker-closure list** (`fetch_hawker_closures()`) and check whether the user's named makan place (if any) is in it. If yes, surface `closed_now: true` and `next_closure: {start, end, reason}`.
6. **If the activity is `makan` AND the chosen centre is closed, pick the nearest open hawker** within 1 km of the geocoded address. If none, suggest a non-hawker pivot ("indoor ActiveSG café" or "skip the hawker plan").
7. **If a UV≥11 or PSI≥101 pivot fires, pick the nearest indoor ActiveSG facility** within 2 km via `fetch_activesg_facilities()` + `haversine_m`.
8. **Emit JSON** with the recommendation text last. The text is the single line the user sees; everything else is context for the agent's follow-up.

## Decision rules

| Condition | Pivot |
|-----------|-------|
| `uv >= 11` (extreme) | "Strongly recommend indoor pivot: nearest indoor ActiveSG is {name} ({distance_m}m)" |
| `psi >= 101` (unhealthy / hazardous) | "Air quality is {tier} — recommend indoor pivot at {facility}" |
| `psi in 51-100` (moderate) | "Air quality is moderate — outdoor OK, but kids / elderly should pace themselves" |
| `weather` contains "Heavy" or "Thundery" | "Heavy rain expected — bring umbrella, prefer sheltered makan" |
| `hawker_closure.closed_now == true` | "Hawker centre is closed for cleaning until {end}. Closest open hawker: {alternates[0].name} ({distance_m}m)" |
| `psi <= 50 AND uv <= 10 AND weather == "Fair"` | "Conditions are good — proceed as planned" |

Rules fire in order; first match wins. If multiple rules match, only the first is reported (keep the text short).

## Hardening

- **PSI tier boundaries are inclusive on the low side** (`good <= 50`, `moderate 51-100`, `unhealthy 101-200`, `hazardous >= 201`). Test the boundaries.
- **UV tiers follow the WHO standard** (`low 0-2`, `moderate 3-5`, `high 6-7`, `very_high 8-10`, `extreme >= 11`). The SGP equivalent in the data source is `0-2 / 3-5 / 6-7 / 8-10 / 11+`.
- **Two-hour forecast `area` is fuzzy.** NEA labels are coarse ("West", "City", "Bukit Timah"). Substring match the geocoded address; fall back to "Central" on no match — never crash.
- **Hawker closure dates are ISO strings**, not datetimes. Compare strings, not `date.today()` objects, to avoid timezone confusion.
- **ActiveSG facilities may have `indoor: false` (swimming complex, outdoor stadium)**. The pivot specifically wants `indoor: true`. Filter before haversine-sort.
- **The script never makes a top-level network call.** All fetches happen inside `assess()` after the user runs the CLI.
- **When the geocoder returns no result, raise a clear `ValueError` and print a usage hint** — don't return a half-empty JSON.

## Caching

All fetches go through `singapore_api.request_json()` which caches responses at `~/.hermes/cache/<namespace>/<sha1>.json`. The cache TTLs:

- PSI: 10 min (NEA refreshes every 15 min anyway)
- UV: 1 hour (NEA publishes once per day)
- Two-hour forecast: 30 min
- Hawker closures: 24 hours (cleaning schedule changes weekly at most)
- ActiveSG facilities: 7 days (static list)

Tunables live in the cache namespace argument, not in the script.

## Data sources

| Source | Endpoint | What we pull |
|--------|----------|--------------|
| NEA PSI | `fetch_psi()` | 5 regions + national reading |
| NEA UV | `fetch_uv()` | Today's peak UV index |
| NEA Two-Hour Forecast | `fetch_two_hour_forecast()` | Per-area forecast for the next 2 hours |
| NEA Hawker Closures | `fetch_hawker_closures()` | All hawker centres + cleaning schedule |
| ActiveSG Facilities | `fetch_activesg_facilities()` | All ActiveSG facilities + indoor flag |
| OneMap Geocoder | `geocode()` | Address → (lat, lon, address, postal) |

## Testing

Smoke tests at `tests/test_weekend_planner.py` cover pure helpers (tier classification, pivot selection, hawker open/closed check, indoor-nearest) with no network. Integration tests mock the 5 fetchers and the geocoder via `unittest.mock.patch`. Run with:

```bash
python3 -m unittest discover -s skills/weekend-planner-skill/tests -v
```

Or include the whole repo:

```bash
python3 -m unittest discover -s tests
```
