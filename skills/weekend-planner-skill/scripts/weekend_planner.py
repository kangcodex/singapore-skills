"""Weekend Planner — weather + air + UV + hawker-aware activity advisor.

Pure-stdlib. Reads NEA signals (PSI, UV, two-hour forecast, hawker closures)
and ActiveSG facilities via the shared `singapore_api` client.

Usage:
    python3 weekend_planner.py --location "Botanic Gardens" \
        --activity makan --time "Saturday noon"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import singapore_api as _api


PRIMARY_LOW_LOTS = 10
ALTERNATE_HIGH_LOTS = 50
ALTERNATE_RADIUS_M = 500
INDOOR_PIVOT_RADIUS_M = 2000
HAWKER_ALTERNATE_RADIUS_M = 1000

UV_EXTREME = 11
PSI_UNHEALTHY = 101

HEAVY_RAIN_KEYWORDS = ("heavy", "thundery", "showers")


from singapore_api import psi_tier  # noqa: E402  (shared via sync script)


def uv_tier(index):
    """Map a UV index to a tier per WHO / NEA SGP convention.

    low 0-2, moderate 3-5, high 6-7, very_high 8-10, extreme >= 11.
    None -> "unknown".
    """
    if index is None:
        return "unknown"
    if index <= 2:
        return "low"
    if index <= 5:
        return "moderate"
    if index <= 7:
        return "high"
    if index <= 10:
        return "very_high"
    return "extreme"


def _records(envelope):
    if not isinstance(envelope, dict):
        return []
    items = envelope.get("items")
    if items is None:
        items = (envelope.get("data") or {}).get("items")
    if items is not None:
        return list(items)
    result = envelope.get("result") or {}
    return list(result.get("records") or [])


def find_hawker(name, hawker_records):
    """Case-insensitive substring match. First hit wins."""
    if not name:
        return None
    needle = name.strip().lower()
    for r in hawker_records:
        if needle in (r.get("name") or "").lower():
            return r
    return None


def _parse_iso_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def is_hawker_closed(record, today=None):
    """A hawker is closed when `today` is inside [next_closure_start, next_closure_end].

    Either bound missing -> not closed (conservative: don't claim a closure we
    can't prove). Return False on missing record.
    """
    if not isinstance(record, dict):
        return False
    if today is None:
        today = _dt.date.today()
    start = _parse_iso_date(record.get("next_closure_start"))
    end = _parse_iso_date(record.get("next_closure_end"))
    if start is None or end is None:
        return False
    return start <= today <= end


def nearest_indoor_active_sg(lat, lon, activesg_records, radius_m=INDOOR_PIVOT_RADIUS_M):
    """Indoor ActiveSG facilities within `radius_m`, sorted by haversine."""
    indoor = [r for r in activesg_records if r.get("indoor") is True]
    if not indoor:
        return None

    def _dist(r):
        rlat = r.get("lat")
        rlon = r.get("lon")
        if rlat is None or rlon is None:
            return float("inf")
        return _api.haversine_m(lat, lon, rlat, rlon)

    indoor.sort(key=_dist)
    for r in indoor:
        if _dist(r) <= radius_m:
            return r
    return None


def nearest_open_hawker(lat, lon, hawker_records, today=None, radius_m=HAWKER_ALTERNATE_RADIUS_M):
    """Open hawker centres within `radius_m`, sorted by haversine."""
    if today is None:
        today = _dt.date.today()

    def _dist(r):
        rlat = r.get("lat")
        rlon = r.get("lon")
        if rlat is None or rlon is None:
            return float("inf")
        return _api.haversine_m(lat, lon, rlat, rlon)

    open_ones = [r for r in hawker_records if not is_hawker_closed(r, today=today)]
    open_ones.sort(key=_dist)
    return [r for r in open_ones if _dist(r) <= radius_m]


def _two_hour_area_match(forecast_records, address):
    """Pick the forecast record whose `area` label best matches the address.

    Substring match either direction; first hit wins. Falls back to the
    "Central" record; falls back to the first record; returns None if empty.
    """
    if not forecast_records:
        return None
    if not address:
        return forecast_records[0]
    addr = address.lower()
    for r in forecast_records:
        area = (r.get("area") or "").lower()
        if area and (area in addr or addr in area):
            return r
    for r in forecast_records:
        if (r.get("area") or "").lower() == "central":
            return r
    return forecast_records[0]


def _is_heavy_rain(forecast_text):
    if not forecast_text:
        return False
    t = forecast_text.lower()
    return any(k in t for k in HEAVY_RAIN_KEYWORDS)


def build_recommendation(psi_reading, uv_index, weather_text, activity, hawker, alternates, indoor_pivot):
    """One-line text. First matching rule wins."""
    uv = uv_tier(uv_index)
    psi = psi_tier(psi_reading)

    if uv_index is not None and uv_index >= UV_EXTREME:
        if indoor_pivot:
            name = indoor_pivot.get("name") or "indoor ActiveSG"
            plat = float(indoor_pivot.get("lat") or 0.0)
            plon = float(indoor_pivot.get("lon") or 0.0)
            dist_m = int(round(float(_api.haversine_m(0.0, 0.0, plat, plon))))
            return (
                "UV %d (extreme) — strongly recommend indoor pivot: "
                "%s (%dm away)" % (uv_index, name, dist_m)
            )
        return "UV %d (extreme) — postpone outdoor activity or seek indoor shelter" % uv_index

    if psi_reading is not None and psi_reading >= PSI_UNHEALTHY:
        if indoor_pivot:
            return (
                "Air quality is %s (PSI %d) — recommend indoor pivot at %s"
                % (psi, psi_reading, indoor_pivot.get("name", "indoor ActiveSG"))
            )
        return "Air quality is %s (PSI %d) — postpone outdoor activity" % (psi, psi_reading)

    if _is_heavy_rain(weather_text):
        if activity == "makan" and hawker and not is_hawker_closed(hawker):
            return "Heavy rain expected — bring umbrella, prefer sheltered makan at %s" % hawker.get("name", "hawker centre")
        return "Heavy rain expected — bring umbrella, prefer sheltered activities"

    if activity == "makan" and hawker and is_hawker_closed(hawker):
        if alternates:
            top = alternates[0]
            return (
                "Hawker centre is closed for cleaning. Closest open: %s (%dm)"
                % (top.get("name", "hawker centre"), _dist_to(lat := hawker.get("lat", 0), lon := hawker.get("lon", 0),
                    top.get("lat", 0), top.get("lon", 0)))
            )
        return "Hawker centre is closed for cleaning — pivot to a non-hawker meal plan"

    if psi_reading is not None and 51 <= psi_reading <= 100:
        if activity in ("outdoors", "kids", "exercise"):
            return "Air quality is moderate (PSI %d) — outdoor OK, but kids / elderly should pace themselves" % psi_reading

    if psi == "good" and (uv == "low" or uv == "moderate" or uv == "high" or uv == "very_high") and not _is_heavy_rain(weather_text):
        return "Conditions are good — proceed as planned"

    return "Conditions are acceptable — proceed with normal precautions"


def _dist_to(lat1, lon1, lat2, lon2):
    if not all(isinstance(x, (int, float)) for x in (lat1, lon1, lat2, lon2)):
        return 0
    if 0 in (lat1, lon1, lat2, lon2):
        return 0
    return int(_api.haversine_m(lat1, lon1, lat2, lon2))


def assess(location, activity, time_str):
    """Run the full pipeline. Returns the JSON-ready dict.

    Raises ValueError on unresolvable geocode. Network errors propagate from
    the fetchers (caller can catch and degrade).
    """
    geo = _api.geocode(location)
    address, lat, lon, _postal = geo
    if lat is None or lon is None:
        raise ValueError("Could not geocode %r" % location)

    psi_envelope = _api.fetch_psi()
    psi_reading = _psi_national(psi_envelope)

    uv_envelope = _api.fetch_uv()
    uv_index = _uv_index(uv_envelope)

    forecast_envelope = _api.fetch_two_hour_forecast()
    forecast_record = _two_hour_area_match(_records(forecast_envelope), address)
    weather_text = (forecast_record or {}).get("forecast") if forecast_record else None

    hawker_records = _api.fetch_hawker_closures()
    hawker = find_hawker(location, hawker_records) if activity == "makan" else None

    today = _dt.date.today()
    if hawker is not None and is_hawker_closed(hawker, today=today):
        alternates = nearest_open_hawker(lat, lon, hawker_records, today=today)
    else:
        alternates = []

    indoor_pivot = None
    if (uv_index is not None and uv_index >= UV_EXTREME) or \
       (psi_reading is not None and psi_reading >= PSI_UNHEALTHY):
        activesg_envelope = _api.fetch_activesg_facilities()
        indoor_pivot = nearest_indoor_active_sg(lat, lon, _records(activesg_envelope))

    recommendation = build_recommendation(
        psi_reading, uv_index, weather_text, activity, hawker, alternates, indoor_pivot
    )

    return {
        "location": {"query": location, "lat": lat, "lon": lon, "address": address},
        "activity": activity,
        "time": time_str,
        "psi": {"national": psi_reading, "tier": psi_tier(psi_reading)},
        "uv": {"index": uv_index, "tier": uv_tier(uv_index)},
        "weather": {
            "area": (forecast_record or {}).get("area") if forecast_record else None,
            "forecast": weather_text,
        },
        "hawker_closures": [
            {
                "name": hawker.get("name"),
                "closed_now": is_hawker_closed(hawker, today=today),
                "next_closure": {
                    "start": hawker.get("next_closure_start"),
                    "end": hawker.get("next_closure_end"),
                    "reason": hawker.get("reason") or "Quarterly cleaning",
                } if hawker and (hawker.get("next_closure_start") or hawker.get("next_closure_end")) else None,
            }
        ] if hawker else [],
        "alternates": [
            {
                "name": a.get("name"),
                "distance_m": _dist_to(lat, lon, a.get("lat", 0), a.get("lon", 0)),
            }
            for a in alternates[:3]
        ],
        "recommendation": recommendation,
    }


def _psi_national(envelope):
    """Extract the national PSI reading. None if the envelope is malformed.
    v1 includes a `national` key in psi_twenty_four_hourly; v2 omits it and
    reports per-region values. We treat the max of any numeric values as the
    national reading (matches NEA's convention of reporting the worst region
    as the headline PSI)."""
    if not isinstance(envelope, dict):
        return None
    items = (envelope.get("items") or (envelope.get("data") or {}).get("items") or [None])
    if not items or items[0] is None:
        return None
    readings = items[0].get("readings") or {}
    val = readings.get("psi_twenty_four_hourly") or {}
    if not val:
        return None
    try:
        return int(max(int(v) for v in val.values() if isinstance(v, (int, float))))
    except (TypeError, ValueError):
        return None


def _uv_index(envelope):
    if not isinstance(envelope, dict):
        return None
    items = (envelope.get("items") or [{}])[0]
    if items:
        for k in ("uv_index", "index", "value"):
            v = items.get(k)
            if isinstance(v, (int, float)):
                return int(v)
    records = ((envelope.get("data") or {}).get("records") or [])
    if records:
        index_list = records[0].get("index") or []
        if index_list:
            v = index_list[0].get("value")
            if isinstance(v, (int, float)):
                return int(v)
    return None


def _build_argparser():
    p = argparse.ArgumentParser(description="Weekend Planner — weather + air + UV + hawker pivots")
    p.add_argument("--location", required=True, help="Free-text location (geocoded via OneMap)")
    p.add_argument("--activity", required=True, choices=("makan", "outdoors", "kids", "exercise", "general"),
                   help="What the user plans to do")
    p.add_argument("--time", required=True, help="Free-text time (e.g. 'Saturday noon')")
    return p


def main(argv=None):
    args = _build_argparser().parse_args(argv)
    try:
        result = assess(args.location, args.activity, args.time)
    except ValueError as e:
        sys.stderr.write("Error: %s\n" % e)
        return 2
    json.dump(result, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
