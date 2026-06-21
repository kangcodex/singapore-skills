---
name: mrt-rerouter-skill
description: "Public-transit rerouting that combines live LTA MRT arrivals, bus arrivals, traffic camera images, NEA weather, and PSI into a single ranked recommendation. Use when a Singaporean asks 'how do I get from X to Y fastest right now?'"
---

# mrt-rerouter-skill

## When to use

A Singaporean asks one of:

- "How do I get from Bishan to Changi Airport fastest right now?"
- "Should I take MRT or bus from Clementi to Tampines?"
- "There's a thunderstorm — will my bus still be on time?"
- "My MRT line is delayed, what's the alternative?"

If the answer is just one of {weather, PSI, bus arrival} on its own, prefer
`weekend-planner-skill` or `singapore_api.geocode/fetch_*` directly. Use this
skill only when the user is choosing between **multiple transit modes** for a
specific origin-destination pair.

## Quick Start

```bash
# Geocodes both endpoints, fetches live LTA + NEA data, returns ranked JSON.
python3 mrt-rerouter-skill/scripts/mrt_rerouter.py \
  --origin "Bishan MRT" --destination "Changi Airport"
```

Optional flags:

- `--origin-station NS17` — skip the geocode for origin
- `--dest-station CG2` — skip the geocode for destination

## Workflow

1. **Geocode** origin and destination (via `singapore_api.geocode`).
2. **Find the nearest MRT station** to each end (haversine, max walk 800 m).
3. **Fetch live data** (graceful fallbacks; never crashes on partial failure):
   - `fetch_lta_mrt_arrival(...)` — needs `DATA_GOV_SG_API_KEY`. If unset, MRT
     routes are skipped entirely; bus-only output.
   - `fetch_lta_bus_arrival(...)` — public, no key required.
   - `fetch_lta_traffic_images()` — public, no key required.
   - `fetch_two_hour_forecast()` — public, no key required.
   - `fetch_psi()` — public, no key required.
4. **Build candidate routes**: MRT-only (1-2 lines), bus-only, hybrid.
5. **Apply downgrades** (see below) BEFORE ranking.
6. **Rank** by `eta_min`. Disruption-flagged routes are pushed to the end.
7. **Emit** the JSON contract consumed by S07 (orchestration doc).

## Decision rules (downgrades)

These are heuristics, calibrated to typical Singapore conditions:

| Condition                                       | Effect                  | Source |
|-------------------------------------------------|-------------------------|--------|
| PSI ≥ 101 (unhealthy or worse)                  | +5 min to any walking leg > 200 m | NEA PSI tier table |
| NEA 2-hour forecast contains "Heavy thundery showers" or "Heavy rain" | +10 min to any bus route | NEA 2-hour forecast vocabulary |
| LTA traffic camera near a bus route segment is flagged slow | +10 min to that bus route | LTA traffic-images metadata |
| LTA MRT data shows a disruption flag on the line | Route ranked LAST regardless of ETA | LTA MRT data `Disruption` field |

**Cumulative**: PSI 101 + heavy rain + slow camera = +5 (walk) + +10 (bus) + +10 (bus, second camera) = up to +20 min to a hybrid route.

## Hardening

- **No top-level network calls at import.** All fetching happens inside
  `assess()`. Tests can `import mrt_rerouter` without internet.
- **Geocode fallback to postal lookup.** If OneMap returns empty, the script
  asks the user to clarify (does not crash with a generic message).
- **Missing `DATA_GOV_SG_API_KEY`.** MRT fetcher raises `RuntimeError`; the
  script catches it and emits bus routes only, with a `note: "DATA_GOV_SG_API_KEY
  unset; MRT routes omitted"` field in the JSON.
- **Disruption > ETA.** A flagged disruption pushes the route to the bottom
  even if its raw ETA is the lowest. This is intentional — reliability
  matters more than speed when the user is already in transit.

## Pitfalls (real ones we hit)

1. **MRT data is v2-only.** v1 endpoints do not publish MRT train arrival
   data publicly. Set `DATA_GOV_SG_API_KEY` or accept bus-only output.
2. **PSI tiers use 24-hourly average.** NEA's `psi_twenty_four_hourly.national`
   is the regulatory headline number; PM2.5/PM10 sub-indices are separate.
3. **Walking leg = (haversine distance, not turn-by-turn path).** A station
   500 m away on a map may require 700 m of walking through a HDB estate.
   The script rounds up; the user should budget more time.
4. **LTA traffic cameras cover expressways, not every road.** A slow camera
   is a strong signal on PIE/CTE/ECP; a missing camera does NOT mean the
   traffic is good. The script flags the latter as "no camera data" rather
   than a green light.
5. **Bus `NextBus.EstimatedArrival` is in ISO 8601.** The script computes
   `eta_min = (eta_iso - now).total_seconds() / 60` — do not trust the
   integer "minutes" field LTA sometimes sends.
6. **Hybrid routes (MRT + bus) require a transfer point.** If the bus stop
   nearest the destination is more than 200 m from the destination
   geocoded point, the hybrid is discarded as impractical.
7. **Disruption flag is per-line, not per-train.** LTA reports "NSL delayed"
   for the whole line; the script applies this to every route that uses
   the NSL, not just specific trains.

## Caching

All `singapore_api` fetchers cache to `~/.hermes/cache/<namespace>/`. A
re-run of the same route within 15 minutes is instant. The cache key
includes the LTA API path + station code, so different stations are
isolated.

## Tests

```bash
python3 -m unittest discover -s mrt-rerouter-skill/tests
```

All five fetchers are mocked via `unittest.mock.patch`. The downgrade
table is tested as a pure function (no I/O).
