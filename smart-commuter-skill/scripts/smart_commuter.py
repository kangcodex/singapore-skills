"""
smart_commuter.py — Smart Driver rerouting for HDB carpark + LTA traffic + NEA weather.

Stdlib only (json, math, sys). Imports the per-skill copy of `singapore_api.py`,
which is kept byte-identical to the canonical at the repo root by
`scripts/sync_singapore_api.py`.

CLI:
    python3 smart_commuter.py "<destination>" [carpark_code]

Prints a JSON report on stdout. Exit 0 on success, 1 on hard failure
(geocode miss, malformed args).
"""
import argparse
import json
import math
import sys

from singapore_api import (
    fetch_hdb_carpark_availability,
    fetch_lta_traffic_images,
    fetch_two_hour_forecast,
    geocode,
)


# ── Constants ─────────────────────────────────────────────────────────

HAVERSINE_EARTH_M = 6_371_000.0

# Swap rule thresholds (mirrored in references/ for documentation)
PRIMARY_LOW_LOTS = 10
ALTERNATE_HIGH_LOTS = 50
ALTERNATE_RADIUS_M = 500
TRAFFIC_CAMERA_RADIUS_M = 2_000
WALK_SPEED_M_PER_MIN = 80

# Weather trigger keywords — case-insensitive substring match
HEAVY_RAIN_KEYWORDS = (
    "heavy thundery showers",
    "thundery showers",
    "heavy rain",
)


# ── Pure helpers ──────────────────────────────────────────────────────

from singapore_api import haversine_m  # noqa: E402  (shared via sync script)


def _items_from(envelope):
    """Pull the `items` array out of a v2 envelope. Returns [] on miss."""
    if not isinstance(envelope, dict):
        return []
    return envelope.get("items") or []


def _walk_minutes(distance_m):
    """Walking minutes from distance, rounded up to ≥ 1."""
    if distance_m <= 0:
        return 1
    return max(1, int(math.ceil(distance_m / WALK_SPEED_M_PER_MIN)))


def _hdb_carparks(availability_envelope):
    """Filter to HDB agency, car lot type only. Returns list of normalised dicts:
    {code, lots_available, latitude, longitude, address, lot_type}."""
    out = []
    for item in _items_from(availability_envelope):
        if (item.get("agency") or "").upper() != "HDB":
            continue
        if (item.get("lot_type") or "C").upper() != "C":
            continue  # only car lots
        try:
            lat = float(item["latitude"])
            lon = float(item["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({
            "code": item.get("carpark_id") or item.get("CarParkID"),
            "lots_available": int(item.get("lots_available", 0) or 0),
            "latitude": lat,
            "longitude": lon,
            "address": item.get("address") or item.get("Development") or "",
            "lot_type": "C",
        })
    return out


def find_primary_carpark(hdb_list, dest_lat, dest_lon, hint_code):
    """
    Pick the primary carpark. If `hint_code` is in the list, use it.
    Otherwise return the nearest HDB carpark to the destination, or None
    when the list is empty. Adds `hint_miss: True` when a hint was supplied
    but not found.
    """
    if not hdb_list:
        return None
    if hint_code:
        for c in hdb_list:
            if c["code"] == hint_code:
                c = dict(c)
                distance = haversine_m(dest_lat, dest_lon, c["latitude"], c["longitude"])
                c["walk_min"] = _walk_minutes(distance)
                return c
        # hint supplied but not present — fall through to nearest, mark the miss
        primary = min(
            hdb_list,
            key=lambda c: haversine_m(dest_lat, dest_lon, c["latitude"], c["longitude"]),
        )
        result = dict(primary)
        result["hint_miss"] = True
        distance = haversine_m(dest_lat, dest_lon, primary["latitude"], primary["longitude"])
        result["walk_min"] = _walk_minutes(distance)
        return result
    # No hint — pick nearest
    primary = min(
        hdb_list,
        key=lambda c: haversine_m(dest_lat, dest_lon, c["latitude"], c["longitude"]),
    )
    result = dict(primary)
    distance = haversine_m(dest_lat, dest_lon, primary["latitude"], primary["longitude"])
    result["walk_min"] = _walk_minutes(distance)
    return result


def find_alternates(hdb_list, dest_lat, dest_lon, exclude_code):
    """
    HDB carparks within ALTERNATE_RADIUS_M of the destination, with
    lots_available > ALTERNATE_HIGH_LOTS, excluding `exclude_code`.
    Sorted by `lots_available` descending. Each entry includes `walk_min`.
    """
    out = []
    for c in hdb_list:
        if c["code"] == exclude_code:
            continue
        if c["lots_available"] <= ALTERNATE_HIGH_LOTS:
            continue
        distance = haversine_m(dest_lat, dest_lon, c["latitude"], c["longitude"])
        if distance > ALTERNATE_RADIUS_M:
            continue
        entry = dict(c)
        entry["walk_min"] = _walk_minutes(distance)
        out.append(entry)
    out.sort(key=lambda c: c["lots_available"], reverse=True)
    return out


def build_traffic_advisory(images_envelope, dest_lat, dest_lon):
    """
    LTA traffic cameras within TRAFFIC_CAMERA_RADIUS_M of the destination.
    `heavy_segments` is the list of camera names (road / exit) nearby.
    `advisory` is "slow" when ≥ 1 nearby camera, "normal" when none, and
    "unavailable" when the LTA list is empty (graceful skip).
    """
    items = _items_from(images_envelope)
    if not items:
        return {"heavy_segments": [], "advisory": "unavailable"}
    segments = []
    for cam in items:
        try:
            lat = float(cam["latitude"])
            lon = float(cam["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if haversine_m(dest_lat, dest_lon, lat, lon) <= TRAFFIC_CAMERA_RADIUS_M:
            name = cam.get("name") or cam.get("Location") or cam.get("camera_id") or "?"
            if name not in segments:
                segments.append(name)
    advisory = "slow" if segments else "normal"
    return {"heavy_segments": segments, "advisory": advisory}


def build_weather_advisory(forecast_envelope, address):
    """
    Look up the NEA 2-hour forecast entry whose `area` name appears in the
    geocoded `address` (case-insensitive substring). Returns the matched
    entry, or {} when nothing matches / the list is empty.
    """
    items = _items_from(forecast_envelope)
    if not items:
        return {}
    addr_lc = (address or "").lower()
    for item in items:
        area = (item.get("area") or "").lower()
        if area and area in addr_lc:
            return {"nowcast": item.get("forecast", ""), "area": item.get("area", "")}
    return {}


def _is_heavy_rain(nowcast):
    """True when the forecast text contains any heavy-rain keyword."""
    if not nowcast:
        return False
    text = nowcast.lower()
    return any(kw in text for kw in HEAVY_RAIN_KEYWORDS)


def decide_recommendation(primary, alternates, traffic, weather):
    """
    Build the single-line recommendation string. Pure — does no I/O.

    Order of clauses:
      1. Bypass <segment> (when traffic.advisory == "slow")
      2. Park at <code> (N lots, M min walk) — alternate if swap, else primary
      3. Weather advisory (when heavy-rain keyword present)
    """
    parts = []

    if (traffic or {}).get("advisory") == "slow":
        segs = traffic.get("heavy_segments") or []
        if segs:
            parts.append("Bypass " + segs[0])

    # Swap rule
    should_swap = (
        primary
        and alternates
        and primary["lots_available"] < PRIMARY_LOW_LOTS
    )
    chosen = alternates[0] if should_swap else primary
    if chosen:
        code = chosen["code"]
        lots = chosen["lots_available"]
        walk = chosen.get("walk_min", 1)
        verb = "Park at" if should_swap else "Park at"
        parts.append(f"{verb} {code} ({lots} lots, {walk} min walk)")

    if _is_heavy_rain((weather or {}).get("nowcast")):
        area = (weather or {}).get("area") or "your area"
        parts.append(f"Heavy rain in {area} — drive carefully")

    return ". ".join(p for p in parts if p) or "No recommendation"


# ── Orchestration ─────────────────────────────────────────────────────


def assess(destination, carpark_code=None, _deps=None):
    """
    Top-level orchestration. Pure signature in, dict out. `_deps` is an
    optional override dict (used in tests) — keys: geocode, traffic,
    carpark, forecast. Each value is a callable returning the raw envelope.
    """
    deps = _deps or {
        "geocode": geocode,
        "traffic": fetch_lta_traffic_images,
        "carpark": fetch_hdb_carpark_availability,
        "forecast": fetch_two_hour_forecast,
    }

    address, lat, lon, postal = deps["geocode"](destination)

    availability = deps["carpark"]()
    hdb = _hdb_carparks(availability)
    primary = find_primary_carpark(hdb, lat, lon, carpark_code)
    exclude = primary["code"] if primary else None
    alternates = find_alternates(hdb, lat, lon, exclude_code=exclude)

    traffic = build_traffic_advisory(deps["traffic"](), lat, lon)
    weather = build_weather_advisory(deps["forecast"](), address)

    recommendation = decide_recommendation(primary, alternates, traffic, weather)

    return {
        "destination": address,
        "postal": postal,
        "primary_carpark": primary,
        "alternates": alternates,
        "traffic": traffic,
        "weather": weather,
        "recommendation": recommendation,
    }


def main(argv):
    parser = argparse.ArgumentParser(
        description="Smart driver rerouting: pick a less-crowded HDB carpark, warn of nearby traffic or heavy rain."
    )
    parser.add_argument("destination", help="Postal code, town, or address in Singapore")
    parser.add_argument("carpark_code", nargs="?", default=None, help="Optional HDB carpark code hint")
    args = parser.parse_args(argv[1:] if argv else None)
    try:
        report = assess(args.destination, args.carpark_code)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
