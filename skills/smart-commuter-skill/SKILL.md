---
name: smart-commuter-skill
description: "Given a Singapore destination (postal / town / address), tell the agent whether the driver should reroute to a neighbouring HDB carpark because the primary lot is filling up, an LTA traffic jam is on the direct route, or NEA weather shows heavy rain on that area."
---

## When to trigger

The agent should pick this skill up when the user says things like:

- "I'm driving to Toa Payoh Central, where should I park?"
- "Parking near Marina Bay — is the usual lot full?"
- "Should I drive to Bugis now or is the traffic bad?"
- "Is there a carpark near me with lots available?"

The agent extracts the destination (a place name, postal code, or address) and runs the script.

## Quick Start

```bash
python3 skills/smart-commuter-skill/scripts/smart_commuter.py "Toa Payoh Central"
python3 skills/smart-commuter-skill/scripts/smart_commuter.py "310080"          # postal
python3 skills/smart-commuter-skill/scripts/smart_commuter.py "Marina Bay" "HE12"  # with hint
```

`smart_commuter.py` is **stdlib-only** (urllib, json, math, pathlib). It imports
from the per-skill copy of `singapore_api.py` (kept byte-identical to the
canonical at the repo root by `scripts/sync_singapore_api.py`). No `pip install`.

Arguments: `python3 smart_commuter.py "<destination>" [carpark_code]`
- `destination` — required, geocoded via OneMap
- `carpark_code` — optional HDB carpark id (e.g. `HE12`). When given, used as the primary; otherwise the nearest HDB carpark to the destination is chosen.

Output: JSON to stdout. Pipe through `jq` for a quick look.

## JSON output schema

```json
{
  "destination": "Toa Payoh Central",
  "postal": "310080",
  "primary_carpark": {
    "code": "TP23",
    "lots_available": 3,
    "walk_min": 1,
    "address": "Blk 122 Toa Payoh Lor 1"
  },
  "alternates": [
    {"code": "TP24", "lots_available": 142, "walk_min": 4, "address": "Blk 125 Toa Payoh Lor 1"}
  ],
  "traffic": {
    "heavy_segments": ["PIE Exit 10"],
    "advisory": "slow"
  },
  "weather": {
    "nowcast": "Heavy thundery showers",
    "area": "Toa Payoh"
  },
  "recommendation": "Bypass PIE, park at TP24 (142 lots, 4 min walk). Heavy thundery showers in Toa Payoh — drive carefully."
}
```

Field semantics:

- `primary_carpark` — the carpark the driver would naively head to. `walk_min` is roughly `distance / 80m` from the geocoded destination, rounded up to ≥ 1.
- `alternates` — HDB carparks within 500 m of the destination with `lots_available > 50`, sorted by `lots_available` descending.
- `traffic.heavy_segments` — LTA traffic camera names within 2 km of the destination. Treat as advisories only — the camera is just *near* the route, not necessarily the route itself.
- `traffic.advisory` — `"slow"` when ≥ 1 heavy segment found, `"normal"` when none, `"unavailable"` when LTA returned an empty image list (graceful skip).
- `weather.nowcast` — NEA 2-hour forecast for the destination's area, when matchable; empty when no area match or the forecast list is empty.
- `recommendation` — single-line verdict. Bypasses the primary when the swap rule fires.

## Decision rules

1. **Swap rule.** `primary.lots_available < 10` **AND** there is at least one alternate within 500 m with `lots_available > 50` → recommend the alternate (highest `lots_available` first).
2. **Traffic advisory.** When `traffic.heavy_segments` is non-empty, append "Bypass <segment>," to the recommendation.
3. **Weather advisory.** When `weather.nowcast` contains `"Heavy thundery showers"`, `"Heavy rain"`, or `"Thundery showers"`, append the warning to the recommendation.
4. **Empty LTA fallback.** When `fetch_lta_traffic_images()` returns an empty list, `traffic.advisory` is `"unavailable"` and no bypass text is added. No crash.
5. **Empty forecast fallback.** When the forecast list is empty or no item matches the destination's area, `weather` is `{}` and no warning is added.

## Caching

Cache lives at `~/.hermes/cache/smart-commuter/` (via `singapore_api.request_json` namespace). The OneMap geocode is NOT cached (it's fast and query-specific).

| Key | Source | Fresh for |
|-----|--------|-----------|
| `request_json` URL hash | data.gov.sg (real-time endpoints) | until underlying cache key changes (revalidated on each call) |
| OneMap geocode | per query | not cached |

## Hardening pitfalls

- **OneMap returns `error: missing token` even on success.** Handled inside `singapore_api.geocode()` (reads `results[0]`). Do not re-implement in skill scripts.
- **HDB `lot_type` breakdown.** The v2 envelope's `lot_type` field is one of `"C"` (car), `"M"` (motorcycle), `"H"` (heavy vehicle). This skill filters to `"C"` only — the recommendation is for a *car*.
- **`lots_available == 0` sentinel.** Means "lot is full" but the data is still published (HDB does not withhold zero-lot rows). Do not treat zero as "no data".
- **LTA camera list can be empty.** At night or during CDN maintenance the v2 endpoint sometimes returns `{"items": []}`. The skill must skip the traffic advisory and continue.
- **No HDB carpark within 500 m with > 50 lots.** `alternates` is `[]`. Recommendation stays with the primary even when it's low — the script never recommends "drive somewhere with no parking".
- **Carpark code `hint` not in current snapshot.** If the user-supplied `carpark_code` is not in the HDB availability data, the script falls back to "nearest HDB carpark" silently and adds a `"hint_miss": true` field to `primary_carpark`.

## Workflow for the agent

1. Parse the user's destination (and optional carpark code) from the request.
2. Run the script. If it exits non-zero, surface the error verbatim.
3. Render the JSON into a chat reply, leading with the `recommendation` field.
4. When `weather.nowcast` contains heavy-rain keywords, prepend "Weather: ..." to the reply.

## Files

```
skills/smart-commuter-skill/
├── SKILL.md                          # this file
├── scripts/
│   ├── smart_commuter.py             # stdlib-only helper
│   └── singapore_api.py              # per-skill copy (synced from ../../singapore_api.py)
└── tests/
    └── test_smart_commuter.py        # smoke tests (pure fns + mocked network)
```

## Tests

```bash
python3 -m unittest discover -s tests
```

Tests cover:
- Pure helpers: `haversine_m`, `find_primary_carpark`, `find_alternates`, `build_traffic_advisory`, `build_weather_advisory`, `decide_recommendation`
- The 3 swap / no-swap / boundary cases
- Empty LTA fallback (no crash)
- Hint code miss fallback
- OneMap geocode quirk (covered in `tests/test_singapore_api.py`; the skill re-exercises the seam)

All network paths are mocked via `unittest.mock.patch` — the suite passes offline.
