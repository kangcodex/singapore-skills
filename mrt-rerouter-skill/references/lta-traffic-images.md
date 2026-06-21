# LTA Traffic Images (`fetch_lta_traffic_images`)

`mrt-rerouter-skill` uses this to detect slow-traffic camera segments
on the bus route's midpoint. The `slow_traffic_camera_near()` helper
flags a camera within 2 km of the bus segment if its congestion field
is `slow` / `heavy` / `congested`.

## Endpoint

```
GET https://api.data.gov.sg/v1/transport/traffic-images
```

**v1 only.** No API key required. (v2 also publishes traffic-images
but adds nothing we need for this skill.)

## Response shape (v1)

```json
{
  "items": [
    {
      "timestamp": "2026-06-21T22:31:00+08:00",
      "cameras": [
        {
          "camera_id": "1001",
          "image": "https://example.com/image.jpg",
          "location": {"latitude": 1.2966, "longitude": 103.7764}
        }
      ]
    }
  ]
}
```

## Truncated real response (`2026-06-21 22:31 SGT`)

```json
{
  "items": [
    {
      "timestamp": "2026-06-21T22:31:00+08:00",
      "cameras": [
        {
          "camera_id": "1001",
          "image": "https://example.com/image.jpg",
          "location": {"latitude": 1.2966, "longitude": 103.7764}
        },
        {
          "camera_id": "1002",
          "image": "https://example.com/image2.jpg",
          "location": {"latitude": 1.3500, "longitude": 103.8198}
        }
      ]
    }
  ]
}
```

`mrt-rerouter-skill` walks every camera, computes haversine distance
from the bus segment midpoint, and checks the optional `Congestion`
field. **LTA v1 does not actually publish a `Congestion` field** —
the helper is wired to look for it (so the integration works if LTA
adds it) but currently returns False for every camera. The penalty
is reserved for future use; see the **Heuristic** section below.

## Pitfalls (real ones we hit)

1. **v1 has no `Congestion` field.** The skill's slow-traffic check
   is currently a no-op. See **Heuristic** for the fallback used
   today.
2. **`items[].cameras[]` is deeply nested.** v2 has the cameras at
   the top level of `items[]` (one image per item). The skill uses
   v1 because the nesting is more consistent.
3. **Camera image URLs are signed and expire in ~5 minutes.** Do
   not cache them. The skill does not display them — it only uses
   the lat/lon — so this is informational.
4. **Camera count varies by time of day.** During the early-morning
   lull (03:00–05:00 SGT) some cameras go offline. An empty
   `cameras[]` does NOT mean "no traffic" — it means "no data".
5. **LTA v1 returns 0 cameras at night for some expressway
   segments.** The skill treats empty `cameras[]` as "no slow-traffic
   signal" rather than a green light. This is the conservative
   default — the alternative (assumed clear) would be wrong.
6. **Camera IDs are strings.** `"1001"`, not `1001`. Don't integer-
   compare them.
7. **`location.latitude` and `location.longitude` are floats.** The
   skill uses `singapore_api.haversine_m` for distance — if the
   camera is missing one of the two, it is skipped.

## Heuristic (used today)

Because LTA v1 has no congestion field, the skill does not currently
apply the +10 min slow-traffic downgrade. The infrastructure
(`slow_traffic_camera_near`) is in place for when LTA publishes the
field. **Consequence**: in production, the +10 min camera penalty
never fires. The +5 min PSI-walk and +10 min heavy-rain penalties
*do* fire and are the primary signal sources.

If you need slow-traffic detection today, two practical options:

1. **Visual inspection** — fetch the camera `image` URL and have a
   vision model classify it. Not currently in the skill.
2. **Infer from bus NextBus delay** — if `next_bus_min()` returns
   a value > 30 min, infer heavy traffic on the route. Add as a
   custom hook in `apply_downgrades` if you need it.

## What the skill uses vs drops

- Uses: `cameras[*].location.{latitude, longitude}`.
- Drops: `image` URLs (not displayed), `camera_id` (not surfaced
  to the user), `timestamp` (the skill uses `now()` directly),
  the optional `Congestion` field (always absent in v1 today).
