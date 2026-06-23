"""mrt-rerouter-skill — Public Transit Reliability.

Given an origin and destination, geocode both, fetch live LTA MRT + bus +
traffic image data, NEA weather, and PSI, then build + rank + recommend
route candidates (MRT-only, bus-only, hybrid).

Stdlib only. Reads from the per-skill copy of `singapore_api.py` (byte-
identical to the repo-root canonical; see scripts/sync_singapore_api.py).

CLI:
    python3 mrt_rerouter.py --origin "Bishan MRT" --destination "Changi Airport"
"""

import argparse
import json

import singapore_api

STATIONS = {
    "NS17": {"name": "Bishan", "line": "NS", "lat": 1.3508, "lon": 103.8494},
    "NS22": {"name": "Orchard", "line": "NS", "lat": 1.3030, "lon": 103.8322},
    "NS26": {"name": "Raffles Place", "line": "NS", "lat": 1.2841, "lon": 103.8514},
    "NS27": {"name": "Marina Bay", "line": "NS", "lat": 1.2723, "lon": 103.8543},
    "EW4": {"name": "Tanah Merah", "line": "EW", "lat": 1.3172, "lon": 103.9460},
    "EW8": {"name": "Paya Lebar", "line": "EW", "lat": 1.3177, "lon": 103.8924},
    "EW12": {"name": "Bugis", "line": "EW", "lat": 1.3006, "lon": 103.8556},
    "EW13": {"name": "City Hall", "line": "EW", "lat": 1.2932, "lon": 103.8524},
    "CC2": {"name": "Bras Basah", "line": "CC", "lat": 1.2968, "lon": 103.8504},
    "CC4": {"name": "Promenade", "line": "CC", "lat": 1.2933, "lon": 103.8607},
    "CG2": {"name": "Changi Airport", "line": "CG", "lat": 1.3573, "lon": 103.9874},
    "DT17": {"name": "Downtown", "line": "DT", "lat": 1.2794, "lon": 103.8528},
}

MAX_WALK_M = 800
WALK_SPEED_M_PER_MIN = 80
TRANSFER_MIN = 4
HEAVY_RAIN_PENALTY_MIN = 10
WALK_LEG_PENALTY_MIN = 5
SLOW_TRAFFIC_PENALTY_MIN = 10
WALK_LEG_PENALTY_THRESHOLD_M = 200
SEVERE_PSI_THRESHOLD = 101
HEAVY_RAIN_KEYWORDS = ("heavy thundery showers", "heavy rain", "thundery showers")


def find_nearest_station(lat, lon):
    """Return (station_code, walk_metres) for the nearest station within
    MAX_WALK_M. Returns (None, None) if none is within range."""
    best_code = None
    best_d = MAX_WALK_M
    for code, s in STATIONS.items():
        d = singapore_api.haversine_m(lat, lon, s["lat"], s["lon"])
        if d < best_d:
            best_d = d
            best_code = code
    if best_code is None:
        return (None, None)
    return (best_code, round(best_d))


def walk_minutes(walk_metres):
    return walk_metres / WALK_SPEED_M_PER_MIN


def mrt_data_has_disruption(mrt_data):
    """Pull the Disruption field out of LTA MRT data, return True if active."""
    if not isinstance(mrt_data, dict):
        return False
    if mrt_data.get("error"):
        return False
    if mrt_data.get("Disruption"):
        return True
    for item in _items_from(mrt_data):
        if isinstance(item, dict) and item.get("Disruption"):
            return True
    flag = mrt_data.get("Status") or mrt_data.get("status")
    if isinstance(flag, str) and flag.lower() in ("disrupted", "delayed", "delay"):
        return True
    return False


def _items_from(payload):
    if not isinstance(payload, dict):
        return []
    return payload.get("items") or payload.get("result", {}).get("records") or []


def next_train_min(mrt_data):
    """Extract first train ETA in minutes from LTA MRT response. Returns
    None if no train data is present."""
    items = _items_from(mrt_data)
    for item in items:
        nt = item.get("NextTrain") or item.get("next_train") or []
        if not nt:
            continue
        first = nt[0]
        eta = first.get("EstimatedArrival") or first.get("eta_min")
        if isinstance(eta, (int, float)):
            return float(eta)
        if isinstance(eta, str):
            from datetime import datetime
            try:
                t = datetime.fromisoformat(eta.replace("Z", "+00:00"))
                now = datetime.now(t.tzinfo)
                return max(0.0, (t - now).total_seconds() / 60.0)
            except ValueError:
                continue
    return None


def next_bus_min(bus_data):
    """Extract first bus ETA in minutes from LTA bus arrival response."""
    items = _items_from(bus_data)
    for item in items:
        nb = item.get("NextBus") or item.get("next_bus") or []
        if not nb:
            continue
        first = nb[0]
        eta = first.get("EstimatedArrival") or first.get("eta_min")
        if isinstance(eta, (int, float)):
            return float(eta)
        if isinstance(eta, str):
            from datetime import datetime
            try:
                t = datetime.fromisoformat(eta.replace("Z", "+00:00"))
                now = datetime.now(t.tzinfo)
                return max(0.0, (t - now).total_seconds() / 60.0)
            except ValueError:
                continue
    return None


def build_mrt_routes(origin_station, dest_station, mrt_data, walk_to_origin_m, walk_from_dest_m):
    """Build a single MRT route from origin_station to dest_station using
    mrt_data as the live arrival input. Walk distances in metres. Returns
    a list of one route dict, or empty list if origin/dest is None or
    the data is empty."""
    if origin_station is None or dest_station is None:
        return []
    train_min = next_train_min(mrt_data)
    if train_min is None and not mrt_data_has_disruption(mrt_data):
        return []
    base_eta = train_min if train_min is not None else 25.0
    total = walk_minutes(walk_to_origin_m) + base_eta + TRANSFER_MIN + walk_minutes(walk_from_dest_m)
    has_disruption = mrt_data_has_disruption(mrt_data)
    verdict = "disrupted" if has_disruption else "normal"
    return [{
        "mode": "mrt+walk",
        "segments": [STATIONS[origin_station]["name"], STATIONS[dest_station]["name"]],
        "eta_min": round(total, 1),
        "walk_m": walk_to_origin_m + walk_from_dest_m,
        "disruptions": ["MRT line disrupted"] if has_disruption else [],
        "verdict": verdict,
    }]


def build_bus_routes(origin_lat, origin_lon, dest_lat, dest_lon, bus_data):
    """Build one bus route between origin and destination. Returns empty
    list if no bus data is available."""
    bus_min = next_bus_min(bus_data)
    if bus_min is None:
        return []
    return [{
        "mode": "bus",
        "segments": ["Origin bus stop", "Destination bus stop"],
        "eta_min": round(bus_min, 1),
        "walk_m": 0,
        "disruptions": [],
        "verdict": "normal",
    }]


from singapore_api import is_heavy_rain, psi_national  # noqa: E402  (shared via sync script)


def slow_traffic_camera_near(traffic_payload, segment_lat, segment_lon, radius_m=2000):
    """Return True if any LTA traffic camera within `radius_m` of the bus
    segment's midpoint is flagged slow/congested. The LTA v1 traffic-images
    payload does not carry a congestion field, so this is a heuristic stub
    that defaults to False — any real slow-traffic detection would need a
    derived signal. The hook is here for the S04b references doc to
    document the contract."""
    if not isinstance(traffic_payload, dict):
        return False
    items = _items_from(traffic_payload)
    for item in items:
        cameras = item.get("cameras") or []
        for cam in cameras:
            clat = cam.get("location", {}).get("latitude")
            clon = cam.get("location", {}).get("longitude")
            if clat is None or clon is None:
                continue
            d = singapore_api.haversine_m(segment_lat, segment_lon, clat, clon)
            if d <= radius_m:
                cam_flag = (cam.get("Congestion") or cam.get("congestion") or "").lower()
                if cam_flag in ("slow", "heavy", "congested"):
                    return True
    return False


def apply_downgrades(routes, psi_value, heavy_rain, slow_camera, bus_segment_lat=None, bus_segment_lon=None):
    """Return a NEW list of routes with the downgrade table applied.
    Pure function — input routes, return routes."""
    if not routes:
        return routes
    out = []
    for r in routes:
        r = dict(r)
        walk_m = r.get("walk_m", 0) or 0
        is_bus = r.get("mode", "").startswith("bus")
        is_disrupted = r.get("verdict") == "disrupted"
        eta = r.get("eta_min", 0)
        disruptions = list(r.get("disruptions") or [])
        if (psi_value is not None and psi_value >= SEVERE_PSI_THRESHOLD
                and walk_m > WALK_LEG_PENALTY_THRESHOLD_M):
            eta += WALK_LEG_PENALTY_MIN
            disruptions.append(
                "PSI %d (unhealthy): +%d min to walk leg" % (psi_value, WALK_LEG_PENALTY_MIN)
            )
        if heavy_rain and is_bus:
            eta += HEAVY_RAIN_PENALTY_MIN
            disruptions.append(
                "Heavy rain forecast: +%d min to bus" % HEAVY_RAIN_PENALTY_MIN
            )
        if slow_camera and is_bus and bus_segment_lat is not None and bus_segment_lon is not None:
            eta += SLOW_TRAFFIC_PENALTY_MIN
            disruptions.append(
                "Slow traffic on bus segment (LTA camera): +%d min" % SLOW_TRAFFIC_PENALTY_MIN
            )
        r["eta_min"] = round(eta, 1)
        r["disruptions"] = disruptions
        out.append(r)
    return out


def rank_routes(routes):
    """Sort by eta_min ascending; disrupted routes pushed to the end (and
    sorted among themselves by eta). Pure function."""
    def key(r):
        return (1 if r.get("verdict") == "disrupted" else 0, r.get("eta_min", 0))
    return sorted(routes, key=key)


def build_recommendation(routes, origin, destination):
    if not routes:
        return "No viable route from %s to %s right now. Try again later or call a ride-hail." % (origin, destination)
    chosen = next((r for r in routes if r.get("verdict") != "disrupted"), routes[0])
    return "%s route (%s min) preferred from %s to %s" % (
        chosen.get("mode", "?"), chosen.get("eta_min", "?"), origin, destination,
    )


def _safe_fetch_mrt(station_code):
    if not station_code:
        return None
    try:
        return singapore_api.fetch_lta_mrt_arrival(station_code)
    except (RuntimeError, Exception):
        return {"error": "MRT data unavailable", "reason": "fetch_failed"}


def _safe_fetch_bus(bus_stop_code, service_no):
    if not bus_stop_code:
        return None
    try:
        return singapore_api.fetch_lta_bus_arrival(bus_stop_code, service_no)
    except (RuntimeError, Exception):
        return {"error": "Bus data unavailable", "reason": "fetch_failed"}


def _geocode_safe(query):
    try:
        return singapore_api.geocode(query)
    except (RuntimeError, ValueError, Exception):
        return None


def assess(origin, destination, origin_station=None, dest_station=None):
    origin_geo = _geocode_safe(origin)
    dest_geo = _geocode_safe(destination)
    origin_lat, origin_lon = (origin_geo[1], origin_geo[2]) if origin_geo else (None, None)
    dest_lat, dest_lon = (dest_geo[1], dest_geo[2]) if dest_geo else (None, None)
    origin_station, origin_walk_m = (
        (origin_station, 0) if origin_station else (None, None)
    ) if origin_lat is None else (origin_station, 0) if origin_station else find_nearest_station(origin_lat, origin_lon)
    dest_station, dest_walk_m = (
        (dest_station, 0) if dest_station else (None, None)
    ) if dest_lat is None else (dest_station, 0) if dest_station else find_nearest_station(dest_lat, dest_lon)

    note = None
    if "DATA_GOV_SG_API_KEY" not in __import__("os").environ:
        note = "DATA_GOV_SG_API_KEY unset; MRT routes omitted unless origin_station is provided"
        mrt_data = {"error": "key_unset", "reason": "DATA_GOV_SG_API_KEY is required for MRT data"}
    else:
        mrt_data = _safe_fetch_mrt(origin_station or dest_station)
    bus_data = _safe_fetch_bus("00000", None)
    traffic = singapore_api.fetch_lta_traffic_images()
    weather = singapore_api.fetch_two_hour_forecast()
    psi = singapore_api.fetch_psi()

    routes = []
    routes += build_mrt_routes(origin_station, dest_station, mrt_data,
                               origin_walk_m or 0, dest_walk_m or 0)
    if origin_lat is not None and dest_lat is not None:
        mid_lat = (origin_lat + dest_lat) / 2
        mid_lon = (origin_lon + dest_lon) / 2
    else:
        mid_lat, mid_lon = 1.3521, 103.8198
    routes += build_bus_routes(
        origin_lat if origin_lat is not None else 0,
        origin_lon if origin_lon is not None else 0,
        dest_lat if dest_lat is not None else 0,
        dest_lon if dest_lon is not None else 0,
        bus_data,
    )

    heavy_rain = is_heavy_rain(weather)
    slow_cam = slow_traffic_camera_near(traffic, mid_lat, mid_lon)
    psi_val = psi_national(psi)

    routes = apply_downgrades(routes, psi_val, heavy_rain, slow_cam, mid_lat, mid_lon)
    routes = rank_routes(routes)
    recommendation = build_recommendation(routes, origin, destination)

    result = {
        "origin": origin,
        "destination": destination,
        "routes": routes,
        "weather_advisory": (
            "Heavy rain expected; bus routes downgraded" if heavy_rain
            else "Light rain / fair; no reroute needed"
        ),
        "recommendation": recommendation,
    }
    if note:
        result["note"] = note
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--origin", required=True)
    p.add_argument("--destination", required=True)
    p.add_argument("--origin-station", default=None,
                   help="Override origin geocoding with a station code (e.g. NS17)")
    p.add_argument("--dest-station", default=None,
                   help="Override destination geocoding with a station code (e.g. CG2)")
    args = p.parse_args()
    out = assess(args.origin, args.destination, args.origin_station, args.dest_station)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
