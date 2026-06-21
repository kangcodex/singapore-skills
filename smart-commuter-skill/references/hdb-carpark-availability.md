# HDB Carpark Availability (`v1/transport/carpark-availability`)

HDB publishes the real-time number of parking lots available at every HDB
carpark, broken down by lot type (cars, motorcycles, heavy vehicles).
Updated every ~1–2 minutes via URA / HDB's feed.

**Endpoint**

```
GET https://api.data.gov.sg/v1/transport/carpark-availability
```

**Auth**: none. Public. The v1 endpoint is HDB-only; URA private carparks
are not in this feed.

The `singapore_api.fetch_hdb_carpark_availability()` fetcher normalises the
v1 deeply-nested envelope
(`items[].carpark_data[].carpark_info[]`) into a flat
`items: [{carpark_id, lots_available, lot_type, total_lots, agency, update_datetime}]`
shape, coercing the string-encoded `lots_available` and `total_lots` to int.

## Live request + response (truncated)

Captured 2026-06-20 22:31 SGT.

```bash
curl -s "https://api.data.gov.sg/v1/transport/carpark-availability" | head -c 2000
```

```json
{
  "items": [
    {
      "timestamp": "2026-06-20T22:31:37+08:00",
      "carpark_data": [
        {
          "update_datetime": "2026-06-20T22:31:00",
          "carpark_number": "HE12",
          "carpark_info": [
            {"lots_available": "101", "lot_type": "C", "total_lots": "105"}
          ]
        },
        {
          "carpark_number": "HLM",
          "update_datetime": "2026-06-20T22:30:35",
          "carpark_info": [
            {"lots_available": "486", "total_lots": "583", "lot_type": "C"}
          ]
        },
        {
          "carpark_number": "BM3",
          "update_datetime": "2026-06-20T22:30:26",
          "carpark_info": [
            {"lot_type": "C", "lots_available": "0", "total_lots": "5"}
          ]
        }
        /* ... 2000+ HDB carparks total ... */
      ]
    }
  ]
}
```

After normalisation by `singapore_api._flatten_v1_carpark_availability()`:

```json
{
  "items": [
    {"carpark_id": "HE12", "lots_available": 101, "lot_type": "C", "total_lots": 105, "agency": "HDB", "update_datetime": "2026-06-20T22:31:00"},
    {"carpark_id": "HLM",  "lots_available": 486, "lot_type": "C", "total_lots": 583, "agency": "HDB", "update_datetime": "2026-06-20T22:30:35"},
    {"carpark_id": "BM3",  "lots_available": 0,   "lot_type": "C", "total_lots": 5,   "agency": "HDB", "update_datetime": "2026-06-20T22:30:26"}
  ]
}
```

## Fields the skill uses

| Field | Type | Consumed by | Notes |
|-------|------|-------------|-------|
| `carpark_id` | str | hint match, primary pick, alternate filter | Stable HDB identifier (e.g. `HE12`, `TP23`, `BM3`). The user can pass it as `[carpark_code]`. |
| `lots_available` | int (after coercion) | swap rule, alternate filter | **v1 sends it as a string** (`"101"`); the normaliser coerces. |
| `lot_type` | str | filter | `"C"` (car), `"M"` (motorcycle), `"H"` (heavy vehicle). smart-commuter filters to `"C"`. |
| `agency` | str | filter | Always `"HDB"` after normalisation (v1's carpark-availability is HDB-only). |
| `total_lots` | int (after coercion) | dropped | Could be used for "lot occupancy" stats; smart-commuter doesn't. |
| `update_datetime` | str | dropped | Cache + `Last-Modified` cover freshness. |

## What the skill drops

- `timestamp` (the outer bucket timestamp) — distinct from per-carpark `update_datetime`. We keep the per-carpark one.
- The nested v1 structure (flattened by helper).
- `total_lots` — the skill's swap rule is purely on `lots_available`.

## `lots_available == 0` semantics

`lots_available == 0` is **not** a "no data" signal. HDB publishes zero-lot
rows when a carpark is genuinely full. The smart-commuter swap rule treats
`lots_available < 10` as "low" — the 0 case is the primary trigger for the
recommendation to swap.

## Rate limits

- Undocumented; the v1 endpoint is small (~150 KB compressed) and the HDB
  feed is updated every ~1–2 min. Cache hits are nearly free.
- v1 has no documented throttling. The `request_json` 3-attempt backoff
  covers 429/5xx transient errors.

## Pitfalls

1. **`lots_available` is a STRING in v1.** `"101"` not `101`. The normaliser
   coerces; do not assume `> 50` comparison works on the raw payload. This
   bit S02a (resale-property-advisor) on its HDB Resale Prices sibling
   dataset — same string-encoding pattern, different field name.
2. **`carpark_id` is not a postal code.** The id (e.g. `HE12`) is an HDB
   internal code, not the carpark's postal address. Geocoding must be
   done separately (e.g. via the HDB carpark-geojson dataset or by
   cross-referencing carpark postal).
3. **`lot_type` is single-letter.** `"C"` is cars, `"M"` is motorcycles,
   `"H"` is heavy vehicles. Smart-commuter filters to cars. A bike rider
   would want a different filter; future skill.
4. **No `agency` filter is needed in v1.** The v1 endpoint is HDB-only.
   The `agency` field is added in the normalised output for forward
   compatibility (if v2 ever lands URA carparks here).
5. **`carpark_info` array has 1 element per carpark in v1.** v2 sometimes
   publishes one row per lot_type, so a single carpark can have 2-3 entries
   in `carpark_info`. The v1 normaliser flattens this correctly because
   the array always has 1 element per `carpark_data` row.
6. **Distance calculation needs lat/lon, which v1 does NOT provide.**
   HDB carparks are not geocoded in this endpoint. The smart-commuter
   skill uses a separate carpark → lat/lon lookup table maintained in
   the HDB carpark-geojson dataset (or a future `_hdb_carpark_locations`
   helper). For S01a, the script accepts a `--carpark-code` hint and
   looks up locations from a small built-in list of common carparks
   (extend as needed).
7. **The skill can return "no nearby carparks".** When the geocoded
   destination has no HDB carpark within 500 m, `alternates` is `[]` and
   the recommendation stays with the primary. Don't crash.

## Distance / geocoding note

S01a's smart-commuter does not maintain a full HDB carpark lat/lon table
inline (that would duplicate the HDB carpark-geojson dataset, which is
out of scope for this slice). The script's haversine-based filtering
works for any carpark entries that include `latitude`/`longitude` (the
test fixtures do). A future slice can add a `_hdb_carpark_locations()`
helper to the shared `singapore_api.py` that joins the HDB carpark-geojson
static dataset with this feed.

## See also

- [`lta-traffic-images.md`](./lta-traffic-images.md) — LTA camera data.
- [`nea-two-hour-forecast.md`](./nea-two-hour-forecast.md) — NEA forecast.
- `singapore_api.py` `_flatten_v1_carpark_availability` — the normalisation helper.
- S02a `resale-property-advisor-skill` — same string-encoded-number pattern on the HDB Resale Prices dataset.
