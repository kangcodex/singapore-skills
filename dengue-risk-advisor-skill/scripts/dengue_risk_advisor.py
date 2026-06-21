"""dengue-risk-advisor: assess outdoor-activity risk for a given town and date.

Stdlib only. Imports from the bundled singapore_api.py (per-skill copy
kept in sync with the canonical at the repo root).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from typing import Any

import singapore_api


CLUSTER_RADIUS_M = 1000
HISTORY_MONTHS = 24
MIN_HISTORY_MONTHS = 12
RAINFALL_TO_7D_FACTOR = 7
MONTHS_TO_DAYS = 30


def _polygon_centroid(feature):
    """Approximate centroid of a GeoJSON polygon feature in (lat, lon).
    GeoJSON coordinates are [lon, lat] — we flip on return."""
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if not coords:
        return None
    ring = coords[0] if geom.get("type") == "Polygon" else coords
    if not ring:
        return None
    lons = [pt[0] for pt in ring if isinstance(pt, (list, tuple)) and len(pt) >= 2]
    lats = [pt[1] for pt in ring if isinstance(pt, (list, tuple)) and len(pt) >= 2]
    if not lons or not lats:
        return None
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def cluster_count_within(features, lat, lon, radius_m=CLUSTER_RADIUS_M):
    """Count NEA dengue clusters within radius_m of (lat, lon).
    `features` is a list of GeoJSON Feature dicts.
    """
    n = 0
    for f in features:
        if not isinstance(f, dict):
            continue
        c = _polygon_centroid(f)
        if c is None:
            continue
        clat, clon = c
        d = singapore_api.haversine_m(lat, lon, clat, clon)
        if d <= radius_m:
            n += 1
    return n


_TOWN_COORDS = {
    "bedok": (1.3240, 103.9270), "bishan": (1.3526, 103.8350), "bukit batok": (1.3590, 103.7630),
    "bukit merah": (1.2810, 103.8230), "bukit panjang": (1.3770, 103.7710), "bukit timah": (1.3290, 103.7950),
    "central water catchment": (1.3700, 103.8050), "changi": (1.3570, 104.0000), "choa chu kang": (1.3840, 103.7440),
    "clementi": (1.3160, 103.7650), "downtown core": (1.2790, 103.8510), "geylang": (1.3200, 103.8840),
    "hougang": (1.3710, 103.8930), "jurong east": (1.3330, 103.7410), "jurong west": (1.3400, 103.7030),
    "kallang": (1.3110, 103.8660), "lim chu kang": (1.4380, 103.7010), "mandai": (1.4030, 103.7930),
    "marina east": (1.2880, 103.8900), "marina south": (1.2750, 103.8640), "marine parade": (1.3030, 103.9070),
    "museum": (1.3010, 103.8380), "newton": (1.3130, 103.8380), "north-eastern islands": (1.4200, 104.0200),
    "novena": (1.3230, 103.8430), "orchard": (1.3050, 103.8310), "outram": (1.2810, 103.8390),
    "pasir ris": (1.3720, 103.9490), "paya lebar": (1.3180, 103.8920), "pioneer": (1.3150, 103.7000),
    "punggol": (1.4040, 103.9020), "queenstown": (1.2940, 103.7860), "river valley": (1.2940, 103.8360),
    "rochor": (1.3030, 103.8520), "seletar": (1.4040, 103.8700), "sembawang": (1.4490, 103.8180),
    "sengkang": (1.3910, 103.8950), "serangoon": (1.3550, 103.8660), "simei": (1.3440, 103.9530),
    "singapore river": (1.2880, 103.8440), "southern islands": (1.2450, 103.8400), "straits view": (1.2700, 103.8100),
    "sungei kadut": (1.4130, 103.7560), "tampines": (1.3530, 103.9450), "tanglin": (1.3070, 103.8120),
    "tengah": (1.3700, 103.7200), "toa payoh": (1.3340, 103.8470), "tuas": (1.3140, 103.6510),
    "western islands": (1.2130, 103.7300), "western water catchment": (1.3300, 103.6600),
    "woodlands": (1.4360, 103.7860), "yishun": (1.4300, 103.8350),
}


def _town_centroid(town, cluster_records):
    """Resolve a planning-area name to (lat, lon) via the TOWN_COORDS lookup.
    Falls back to (1.3521, 103.8198) — the Singapore geographic centre."""
    SG_CENTRE = (1.3521, 103.8198)
    if not town:
        return SG_CENTRE
    key = town.strip().lower()
    if key in _TOWN_COORDS:
        return _TOWN_COORDS[key]
    for k, coord in _TOWN_COORDS.items():
        if key in k or k in key:
            return coord
    return SG_CENTRE


def _rainfall_to_mm_7d(current_mm):
    """7-day forecast proxy: current reading × 7. Clamped at 0."""
    if current_mm is None:
        return None
    try:
        return max(0.0, float(current_mm) * RAINFALL_TO_7D_FACTOR)
    except (TypeError, ValueError):
        return None


def _historical_mm_7d(monthly_records):
    """Compute (avg_7d, std_7d) from monthly records. None if insufficient data.

    Each record must carry a numeric "rainfall_mm" (or "value") field.
    """
    vals = []
    for r in monthly_records:
        if not isinstance(r, dict):
            continue
        v = r.get("rainfall_mm", r.get("value"))
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if len(vals) < MIN_HISTORY_MONTHS:
        return None, None
    mean = sum(vals) / len(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return mean * RAINFALL_TO_7D_FACTOR / MONTHS_TO_DAYS, stdev * RAINFALL_TO_7D_FACTOR / MONTHS_TO_DAYS


def is_above_average_rain(forecast_7d, avg_7d, std_7d):
    """True iff forecast exceeds mean + 1σ. None if any input is None."""
    if forecast_7d is None or avg_7d is None:
        return None
    if std_7d is None:
        std_7d = 0.0
    return forecast_7d > (avg_7d + std_7d)


def risk_score(clusters_nearby, above_avg_rain):
    """0..6+ integer score: clusters + 3 if above-avg rain."""
    base = max(0, int(clusters_nearby))
    return base + (3 if above_avg_rain is True else 0)


def risk_tier(clusters_nearby, above_avg_rain):
    """Map (clusters, above_avg_rain) to one of: low / moderate / elevated / high / unknown."""
    if above_avg_rain is None:
        return "unknown"
    if clusters_nearby >= 5:
        return "high"
    if clusters_nearby >= 3 and above_avg_rain is True:
        return "elevated"
    if clusters_nearby >= 1:
        return "moderate"
    if above_avg_rain is True:
        return "moderate"
    return "low"


from singapore_api import psi_tier as _psi_tier, psi_national as _psi_national  # noqa: E402  (shared via sync script)


def _recommendation(tier, psi_t):
    by_tier = {
        "low":      "Low risk. Standard outdoor precautions are sufficient.",
        "moderate": "Moderate risk. Apply DEET repellent; check NEA alerts before heading out.",
        "elevated": "Elevated risk. Postpone outdoor activity; consider an indoor alternative.",
        "high":     "High risk. Strongly recommend postponing or moving indoors.",
        "unknown":  "Insufficient data to score confidently. Check NEA's dengue page directly.",
    }
    msg = by_tier.get(tier, by_tier["unknown"])
    if psi_t in ("unhealthy", "hazardous"):
        msg += " Air is also unhealthy — reduce exertion regardless of mosquito risk."
    return msg


def assess(town, activity, date_str):
    """Build the full risk report. Returns a dict (also JSON-serialisable)."""
    cluster_fc = singapore_api.fetch_dengue_clusters()
    cluster_features = cluster_fc.get("features", []) if isinstance(cluster_fc, dict) else []
    lat, lon = _town_centroid(town, cluster_features)
    n_nearby = cluster_count_within(cluster_features, lat, lon)

    hist_records = singapore_api.fetch_nea_historical_rainfall(months=HISTORY_MONTHS) or []
    avg_7d, std_7d = _historical_mm_7d(hist_records)

    current_envelope = singapore_api.fetch_rainfall()
    current_mm = _rainfall_current_mm(current_envelope)
    forecast_7d = _rainfall_to_mm_7d(current_mm)

    above = is_above_average_rain(forecast_7d, avg_7d, std_7d)
    tier = risk_tier(n_nearby, above)
    score = risk_score(n_nearby, above)

    psi_envelope = singapore_api.fetch_psi()
    psi_val = _psi_national(psi_envelope)
    psi_t = _psi_tier(psi_val)

    return {
        "town": town,
        "activity": activity,
        "date": date_str,
        "dengue_clusters_nearby": n_nearby,
        "rainfall_forecast_mm_7d": round(forecast_7d, 1) if forecast_7d is not None else None,
        "rainfall_history_avg_mm_7d": round(avg_7d, 1) if avg_7d is not None else None,
        "rainfall_history_std_mm_7d": round(std_7d, 1) if std_7d is not None else None,
        "psi": {"national": psi_val, "tier": psi_t},
        "risk_score": score,
        "risk_tier": tier,
        "recommendation": _recommendation(tier, psi_t),
    }


def _rainfall_current_mm(envelope):
    """Average current rainfall (mm) across all stations from the v2 rainfall
    payload. v2 shape: {code, data: {readings: [{timestamp, data: [{stationId,
    value}, ...]}], stations: [...]}}."""
    if not isinstance(envelope, dict):
        return None
    data = envelope.get("data") or {}
    readings = data.get("readings") or []
    if not readings:
        items = envelope.get("items") or []
        if items:
            readings = items[0].get("readings") or []
    if not readings:
        return None
    latest = readings[0]
    if isinstance(latest, dict):
        station_data = latest.get("data") or []
    else:
        station_data = latest
    values = []
    for entry in station_data:
        if not isinstance(entry, dict):
            continue
        v = entry.get("value")
        if isinstance(v, (int, float)):
            values.append(float(v))
    if not values:
        return None
    return sum(values) / len(values)


def main(argv=None):
    p = argparse.ArgumentParser(description="Assess dengue risk for an outdoor activity.")
    p.add_argument("--town", required=True, help="Planning area / town (e.g. 'Bedok').")
    p.add_argument("--activity", required=True, help="Free-form activity (e.g. 'morning jog').")
    p.add_argument("--date", required=True, help="Planned date (YYYY-MM-DD).")
    args = p.parse_args(argv)
    report = assess(args.town, args.activity, args.date)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
