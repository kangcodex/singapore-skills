# LTA MRT + Bus Arrival (`fetch_lta_mrt_arrival`, `fetch_lta_bus_arrival`)

`mrt-rerouter-skill` uses these for live transit data. They have
**different auth rules** — read the pitfall section carefully.

## MRT — `fetch_lta_mrt_arrival(station_code)`

```
GET https://api-open.data.gov.sg/v2/real-time/api/mrt-train-arrival?StationCode=<code>
```

**v2 only.** v1 has no MRT train arrival data. The shared client
**requires** `DATA_GOV_SG_API_KEY` to be set; if it isn't, the helper
raises `RuntimeError` and `mrt-rerouter-skill` catches it and emits
bus-only output.

### Response shape (v2)

```json
{
  "StationCode": "NS17",
  "MRT": [
    {
      "NextTrain": {
        "EstimatedArrival": "2026-06-21T22:35:00+08:00",
        "Platform": "A"
      },
      "Line": "NSL",
      "Status": "Normal"
    }
  ]
}
```

`mrt-rerouter-skill` reads `MRT[*].NextTrain.EstimatedArrival` (ISO 8601
→ minutes from now) and `MRT[*].Status` (or top-level `Disruption` flag).
If the line is delayed, the entire route is flagged `disrupted` and
pushed to the end of the ranking.

### Disruption detection

LTA signals a disruption in two ways:

1. A top-level `Disruption` field on the response, OR
2. An item with `Status: "Disrupted"` / `Status: "Delayed"` inside
   `MRT[]`.

`mrt_rerouter.mrt_data_has_disruption()` checks both. See S04a
`tests/test_mrt_rerouter.py` for the live test data.

## Bus — `fetch_lta_bus_arrival(bus_stop_code, service_no=None)`

```
GET https://api-open.data.gov.sg/v2/real-time/api/bus-arrival
    ?BusStopCode=<code>&ServiceNo=<service_no>
```

**v2 with v1 fallback.** If `DATA_GOV_SG_API_KEY` is unset, the shared
client transparently falls back to v1's public bus-arrival endpoint.
v1 returns the same shape (different namespace), so callers don't
care.

### Response shape (canonical, v1 + v2)

```json
{
  "BusStopCode": "00000",
  "Services": [
    {
      "ServiceNo": "53",
      "NextBus": {
        "EstimatedArrival": "2026-06-21T22:38:00+08:00"
      }
    }
  ]
}
```

`mrt-rerouter-skill` reads `Services[0].NextBus.EstimatedArrival` (ISO
8601 → minutes from now). The `mrt_rerouter.next_bus_min()` helper
unwraps the v1 nested envelope too.

## Pitfalls (read these or you will ship a broken skill)

1. **MRT data is v2-only.** No API key, no MRT. The skill's `assess()`
   catches the `RuntimeError` and emits bus-only with a `note: "..."`
   field. If you see empty `routes[]` from the MRT entry, this is why.
2. **v1 bus response nests differently.** v1 puts bus arrival data
   under `Services`, not `Items`. The shared client flattens this for
   the v1 path; if you call the v1 URL directly you'll get a
   different shape and `next_bus_min` will return `None`.
3. **`EstimatedArrival` is always ISO 8601, never an integer minutes
   field.** LTA used to send `"min": "3"` — that field is deprecated.
   The skill parses ISO and computes `(eta - now) / 60`. Don't trust
   any `"min"` field.
4. **MRT `Status` strings are case-sensitive.** LTA uses
   `"Normal"`, `"Disrupted"`, `"Delayed"`. The helper lowercases the
   comparison so `"DELAYED"` works too, but the actual LTA payload
   uses title case.
5. **Bus `NextBus` can be `null` for a service with no imminent
   arrival.** The skill iterates `Services[*].NextBus` and skips
   `None`. A bus stop with all `NextBus = null` is treated as
   "no bus data" and the bus route is not emitted.
6. **MRT line codes are case-sensitive on the LTA side but lowercase
   on the NEA side.** LTA uses `NSL`, `EWL`, `CCL`, `CEL`, `NEL`,
   `DTL`, `TEL`. Don't lowercase them when comparing.
7. **The skill does not handle multi-leg bus routes.** `NextBus` is
   the next bus at the stop, not the bus that takes you to the
   destination. `mrt-rerouter-skill` uses this as a coarse ETA proxy
   (the user's actual bus might be 2-3 stops away).
8. **`BusStopCode` is the 5-digit LTA ID, not a postal code.** The
   skill currently passes a dummy `"00000"` — a future improvement
   is to use OneMap → bus-stop lookup.
9. **`mrt_data_has_disruption` returns False on an error envelope.**
   An error from v2 (`{"error": "key_unset"}`) is *not* a disruption
   — the skill should fall back to bus-only, not flag the line as
   broken. See `test_error_envelope_not_treated_as_disruption`.

## What the skill uses vs drops

- Uses: `MRT[*].NextTrain.EstimatedArrival`, `MRT[*].Status`,
  `Services[*].NextBus.EstimatedArrival`.
- Drops: `Platform`, `Operator`, `WheelchairAccessible`, all
  `LoadIndicator` fields. The skill is about timing, not crowding
  or accessibility.
