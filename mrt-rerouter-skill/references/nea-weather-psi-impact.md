# NEA Weather & PSI → ETA downgrades (calibration notes)

`mrt-rerouter-skill` applies three downgrades based on real-time
NEA data. The values (+5 min, +10 min) are **heuristics**, not
measurements. This doc justifies them and documents where to find
the live data.

## Endpoints

```
GET https://api.data.gov.sg/v1/environment/psi
GET https://api.data.gov.sg/v1/environment/2-hour-weather-forecast
```

Both v1, public, no API key. v2 also publishes these but adds
nothing the skill needs. The shared client falls back from v2 to
v1 transparently.

## Downgrade table (current values)

| Condition                                  | Effect                    | Justification |
|--------------------------------------------|---------------------------|---------------|
| PSI 24-hourly national ≥ 101 (unhealthy+)  | +5 min to walking legs > 200 m | A 600 m walk in unhealthy air is genuinely slower (people reduce pace, find sheltered paths) |
| NEA forecast contains "Heavy thundery showers" or "Heavy rain" | +10 min to any bus route | Buses crawl in heavy rain; LTA historical data shows 1.5–2× journey time |
| LTA traffic camera flagged slow near bus segment | +10 min to that bus route | Reserved — v1 has no `Congestion` field, so this does not fire today. Documented for forward compatibility |

The **disruption** flag (MRT line delayed) is not a downgrade — it
pushes the route to the bottom of the ranking regardless of ETA.
This is intentional; a 25-min ETA on a known-disrupted line is
worse than a 40-min ETA on a working bus.

## PSI tier table

| psi_24h | tier | walk downgrade? |
|---------|------|-----------------|
| 0–50 | good | no |
| 51–100 | moderate | no |
| 101–200 | unhealthy | **yes** |
| 201+ | hazardous | **yes** |

The threshold is 101 (unhealthy), not 200 (hazardous), because at
unhealthy Singaporeans already take defensive measures (slower
walking pace, mask use, sheltered path preference). The +5 min
penalty reflects the **incremental** cost of walking 600 m through
unhealthy air vs walking 600 m through good air.

## NEA forecast vocabulary

The 2-hour forecast uses a fixed set of strings. The skill matches
against this list (case-insensitive substring match):

- `"Fair"` — no penalty
- `"Partly Cloudy"` — no penalty
- `"Light Rain"` — no penalty
- `"Showers"` — no penalty
- `"Thundery Showers"` — **heavy rain penalty** (matches "thundery showers" substring)
- `"Heavy Thundery Showers"` — **heavy rain penalty**
- `"Heavy Rain"` — **heavy rain penalty**
- `"Cloudy"` — no penalty
- `"Mist"` — no penalty
- `"Fog"` — no penalty
- `"Haze"` — no penalty (the skill treats haze as a PSI concern, not a rain concern)

If NEA introduces a new forecast string, the skill will silently
treat it as "no rain" until you update the `HEAVY_RAIN_KEYWORDS`
tuple in `scripts/mrt_rerouter.py`. Add to the tuple rather than
branching on a new string elsewhere.

## Pitfalls (real ones we hit)

1. **PSI tiers use 24-hourly average, not the live PM2.5 sub-index.**
   NEA's `psi_twenty_four_hourly.national` is the regulatory
   headline number. PM2.5/PM10/CO/O3/SO2 are separate sub-indices.
   The skill uses only the headline.
2. **NEA region names are lowercase.** `psi_twenty_four_hourly`
   keys are `west`, `east`, `central`, `south`, `north`, `national`.
   Capitalising returns `None`.
3. **The 2-hour forecast is per-area**, not per-coords. The skill
   looks up the user's geocoded area name and matches against the
   `area` field of the forecast. If the geocoded area is not in
   the forecast, the skill falls back to `national` or `central`.
4. **Heavy-rain threshold is fuzzy by design.** NEA's "Heavy rain"
   string is rare (3-5 events per year). "Thundery showers" is the
   common case. The skill matches both because the operational
   impact is similar — buses slow in heavy convective rain.
5. **PSI national is sometimes `null`.** During sensor maintenance
   or haze events, v1 may return `"national": null` for an hour or
   two. The skill treats `None` as "no PSI data, no walk penalty"
   rather than flagging a 0.0 value.
6. **The +5 and +10 min values are not calibrated against real
   data.** They are placeholders. To calibrate, run the skill
   against historical NEA data and LTA bus journey times, fit a
   regression, and update the constants. See `mrt_rerouter.py`
   (`WALK_LEG_PENALTY_MIN`, `HEAVY_RAIN_PENALTY_MIN`,
   `SLOW_TRAFFIC_PENALTY_MIN`).
7. **Downgrades are additive, not multiplicative.** A user with
   PSI 110, heavy rain, AND slow traffic gets
   5 + 10 + 10 = 25 min of penalties. This is conservative; a
   multiplicative model would give less penalty. The additive
   model matches the way a human would describe the
   inconvenience.

## What the skill uses vs drops

- Uses: `psi_twenty_four_hourly.national`, `forecast` (substring
  match), `area` (only for matching the user's location).
- Drops: `region_metadata`, all `items[1..]`, PM2.5/PM10 sub-indices,
  `update_timestamp` (the skill uses `now()`).

## Calibration history

| Date | Change | Source |
|------|--------|--------|
| 2026-06-21 | Initial +5 / +10 min values | Heuristic from public SGT commuter discussion |
