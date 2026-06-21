# LTA Traffic Images (`v1/transport/traffic-images`)

The data.gov.sg v1 traffic-images endpoint exposes LTA's static traffic
camera network. Each camera publishes a JPEG snapshot every ~20 seconds
together with location metadata.

**Endpoint**

```
GET https://api.data.gov.sg/v1/transport/traffic-images
```

**Auth**: none. Public. Pass an optional `?date_time=YYYY-MM-DDTHH:MM:SS`
to fetch a historical snapshot (omitted → latest).

The `singapore_api.fetch_lta_traffic_images()` fetcher normalises the v1
envelope (nested `items[].cameras[]`) into a flat `items: [{camera_id, image,
latitude, longitude, name, timestamp}]` shape. Skill scripts never see the
nesting.

## Live request + response (truncated)

Captured 2026-06-20 22:31 SGT against the public endpoint.

```bash
curl -s "https://api.data.gov.sg/v1/transport/traffic-images" | head -c 1500
```

```json
{
  "items": [
    {
      "timestamp": "2026-06-20T22:31:56+08:00",
      "cameras": [
        {
          "timestamp": "2026-06-20T22:30:56+08:00",
          "image": "https://images.data.gov.sg/api/traffic-images/2026/06/83c380b0-8ba1-4f46-9aff-d5b2336f77f5.jpg",
          "location": {"longitude": 103.871146, "latitude": 1.29531332},
          "camera_id": "1001",
          "image_metadata": {"height": 240, "width": 320, "md5": "0333595378b53c93cc4d2006d6dd4761"}
        },
        {
          "timestamp": "2026-06-20T22:30:56+08:00",
          "image": "https://images.data.gov.sg/api/traffic-images/2026/06/705eaad1-c728-4d6f-9a7c-295becc3ebfa.jpg",
          "location": {"latitude": 1.323957439, "longitude": 103.8728576},
          "camera_id": "1003",
          "image_metadata": {"height": 240, "width": 320, "md5": "9a5ac48184ff64a99668c831b8ccba04"}
        }
        /* ... 90+ more cameras, one per static LTA camera ... */
      ]
    }
  ]
}
```

After normalisation by `singapore_api._flatten_v1_traffic_images()`:

```json
{
  "items": [
    {
      "camera_id": "1001",
      "image": "https://images.data.gov.sg/api/traffic-images/2026/06/83c380b0-...jpg",
      "latitude": 1.29531332,
      "longitude": 103.871146,
      "name": "1001",
      "timestamp": "2026-06-20T22:30:56+08:00"
    }
  ]
}
```

## Fields the skill uses

| Field | Type | Consumed by | Notes |
|-------|------|-------------|-------|
| `camera_id` | str | `name` (fallback) | Stable LTA identifier. v1 has no human label — the id IS the label. |
| `image` | str (URL) | dropped | The skill does not download or analyse the JPEG; it just reports which cameras are near. Image URL is preserved for the agent if it wants to `curl` the snapshot. |
| `location.latitude` | float | distance filter | Used with `haversine_m` against the destination centroid. |
| `location.longitude` | float | distance filter | |
| `timestamp` | str (ISO 8601) | dropped | Cameras publish every ~20 s. The skill's cache window (per `request_json`) is the freshness contract. |

## What the skill drops

- `image_metadata.{height,width,md5}` — useful for image integrity but not for "is the road jammed".
- The outer `items[].timestamp` (bucket timestamp, distinct from the per-camera timestamp). We keep the per-camera one for accuracy.
- Cameras outside the destination's `TRAFFIC_CAMERA_RADIUS_M` (default 2 km). They are filtered out before the agent sees them.

## Rate limits

- Undocumented; sustained ~1 req/min per IP seems safe in practice.
- The data.gov.sg gateway returns `503` under load; the v1 retry policy in
  `request_json` (3 attempts, 0.5/1/2 s backoff) covers that.

## Pitfalls

1. **Empty list at night.** Between ~02:00 and ~05:00 SGT, the LTA CDN sometimes
   returns `{"items": [{"cameras": []}]}` while maintenance is in progress.
   The smart-commuter skill handles this by reporting `advisory: "unavailable"`
   and continuing with carpark + weather. Do **not** crash on empty list.
2. **`camera_id` is the label, not a human-readable name.** v1 has no
   `name`/`Location` field per camera. If the agent needs a human label
   (e.g. "PIE Exit 10"), it must maintain its own camera-id → label table.
   The v2 endpoint adds a `name` field but requires an `x-api-key` we don't ship.
3. **Image URL expiry.** The `image` URL is a one-shot pre-signed S3-style link.
   It is regenerated on every camera publish, so the URL is good for the
   ~20-second publish window. Stale URLs return 403. Do not cache the URL
   beyond the request.
4. **v1 envelope is nested.** Raw response is
   `items[].cameras[]`; the helper `_flatten_v1_traffic_images()` collapses
   it to `items[]`. Don't write skill code against the raw shape.
5. **Coordinates are WGS84 lat/lon.** No SVY21 conversion needed for this
   endpoint (unlike URA Master Plan). Use `haversine_m` directly.

## See also

- [`nea-two-hour-forecast.md`](./nea-two-hour-forecast.md) — NEA forecast; smart-commuter uses both.
- [`hdb-carpark-availability.md`](./hdb-carpark-availability.md) — HDB carpark data; smart-commuter uses both.
- `singapore_api.py` `_flatten_v1_traffic_images` — the normalisation helper.
