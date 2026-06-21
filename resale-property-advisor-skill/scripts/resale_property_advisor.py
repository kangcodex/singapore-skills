#!/usr/bin/env python3
"""Resale Property Advisor — cluster baseline + URA uplift + rainfall context.

Imports from the per-skill singapore_api copy. Stdlib only. No pip deps.

Usage:
    python3 resale_property_advisor.py \\
        --town BISHAN --flat-type 5-ROOM \\
        --since 2025-12-01 --asking 720000

Exit code 0 on success. JSON to stdout.
"""

import argparse
import json
import math
import re
import statistics
import sys
import time
from typing import Any

from singapore_api import (
    DATA_GOV_V1,
    HDB_RESALE_DATASET_ID,
    fetch_dataset_rows,
    fetch_nea_historical_rainfall,
    fetch_ura_master_plan,
    geocode,
    haversine_m,
    svy21_to_wgs84,
)


FLAT_TYPES = {
    "1-ROOM", "2-ROOM", "3-ROOM", "4-ROOM", "5-ROOM", "EXEC",
    "MULTI-GEN", "STUDIO",
}

RAINFALL_LOOKBACK_24MO = 24
RAINFALL_LOOKBACK_5YR = 60
RAISE_SIGMA = 1.0
URA_RADIUS_M = 1000.0
AMENITY_RADIUS_M = 1000.0

LU_CATEGORIES = [
    (re.compile(r"\b(school|primary|secondary|junior college)\b", re.I), "primary_school"),
    (re.compile(r"\b(hospital|clinic|polyclinic|healthcare|nursing home)\b", re.I), "healthcare"),
    (re.compile(r"\b(mrt|station|metro|rapid transit)\b", re.I), "MRT"),
    (re.compile(r"\b(business|office|commercial hub|cbd)\b", re.I), "business_hub"),
    (re.compile(r"\b(industrial|factory|warehouse)\b", re.I), "industrial"),
]


def categorise_lu(lu_desc: str) -> str | None:
    if not lu_desc:
        return None
    for rx, label in LU_CATEGORIES:
        if rx.search(lu_desc):
            return label
    return None


def cluster_centroid_easting_northing(records: list[dict]) -> tuple[float, float] | None:
    if not records:
        return None
    xs, ys = [], []
    for r in records:
        x = r.get("_x") or r.get("x") or r.get("easting")
        y = r.get("_y") or r.get("y") or r.get("northing")
        if x is None or y is None:
            continue
        try:
            xs.append(float(x))
            ys.append(float(y))
        except (TypeError, ValueError):
            continue
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def to_float(s: Any) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _since_iso(s: str) -> int:
    parts = s.split("-")
    if len(parts) < 1:
        raise ValueError("since must be YYYY-MM-DD or YYYY-MM")
    return int(parts[0]) * 100 + int(parts[1]) if len(parts) >= 2 else int(parts[0]) * 100


def fetch_hdb_records(town: str, flat_type: str, since: str) -> list[dict]:
    town_lc = town.lower().strip()
    flat_norm = flat_type.upper().strip().replace(" ", "-")
    filters = [
        {"columnName": "town", "type": "EQ", "value": town_lc},
        {"columnName": "flat_type", "type": "EQ", "value": flat_norm},
    ]
    records = fetch_dataset_rows(HDB_RESALE_DATASET_ID, filters=filters)
    since_yyyymm = _since_iso(since)
    out = []
    for r in records:
        month = r.get("month") or r.get("transaction_month")
        try:
            month_int = int(str(month)[:7].replace("-", ""))
        except (TypeError, ValueError, IndexError):
            continue
        if month_int < since_yyyymm:
            continue
        out.append(r)
    return out


def cluster_average(records: list[dict]) -> float | None:
    prices = []
    for r in records:
        p = to_float(r.get("resale_price"))
        if p is not None:
            prices.append(p)
    if not prices:
        return None
    return sum(prices) / len(prices)


def premium_pct(asking: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0
    return (asking - baseline) / baseline * 100.0


def future_amenities(town: str, records: list[dict]) -> list[str]:
    centroid = cluster_centroid_easting_northing(records)
    if centroid is None:
        try:
            geocoded = geocode(f"{town} Town Centre, Singapore")
        except (ValueError, RuntimeError):
            return []
        if geocoded is None:
            return []
        lat, lon = geocoded[1], geocoded[2]
        return _amenities_around_latlon(lat, lon, AMENITY_RADIUS_M)
    ex, ny = centroid
    lat, lon = svy21_to_wgs84(ex, ny)
    return _amenities_around_latlon(lat, lon, AMENITY_RADIUS_M)


def _amenities_around_latlon(lat: float, lon: float, radius_m: float) -> list[str]:
    envelope = fetch_ura_master_plan()
    features = envelope.get("result", {}).get("records", [])
    found: set[str] = set()
    for f in features:
        x = to_float(f.get("_x") or f.get("x") or f.get("easting"))
        y = to_float(f.get("_y") or f.get("y") or f.get("northing"))
        if x is None or y is None:
            continue
        wgs = svy21_to_wgs84(float(x), float(y))
        flat_lat: float = wgs[0]
        flat_lon: float = wgs[1]
        if haversine_m(lat, lon, flat_lat, flat_lon) > radius_m:
            continue
        cat = categorise_lu(f.get("lu_desc", "") or f.get("mpro_use", ""))
        if cat:
            found.add(cat)
    return sorted(found)


def rainfall_history() -> dict:
    records = fetch_nea_historical_rainfall(months=RAINFALL_LOOKBACK_5YR)
    if not records:
        return {"classification": "unknown", "recent_24mo_mm": 0.0, "five_year_avg_mm": 0.0}
    months = []
    for r in records:
        v = to_float(r.get("total_rainfall_mm") or r.get("rainfall_mm") or r.get("value"))
        if v is not None:
            months.append(v)
    if not months:
        return {"classification": "unknown", "recent_24mo_mm": 0.0, "five_year_avg_mm": 0.0}
    months_sorted = months[:RAINFALL_LOOKBACK_24MO]
    recent_24mo = sum(months_sorted) / len(months_sorted)
    if len(months) < 2:
        std = 0.0
    else:
        std = statistics.pstdev(months)
    five_year_avg = sum(months) / len(months)
    if recent_24mo > five_year_avg + RAISE_SIGMA * std:
        classification = "above-average"
    elif recent_24mo < five_year_avg - RAISE_SIGMA * std:
        classification = "below-average"
    else:
        classification = "typical"
    return {
        "classification": classification,
        "recent_24mo_mm": round(recent_24mo, 1),
        "five_year_avg_mm": round(five_year_avg, 1),
    }


def verdict(asking: float, baseline: float, amenities: list[str], rain_class: str) -> str:
    p = premium_pct(asking, baseline)
    has_uplift = len(amenities) >= 2
    if p <= 5.0:
        return "fair"
    if p <= 10.0 and has_uplift and rain_class != "above-average":
        return "premium justified"
    if p > 5.0 and not has_uplift:
        return "above market"
    if rain_class == "above-average" and p > 0:
        return "above market"
    return "premium justified"


def recommendation(verdict_str: str, baseline: float, asking: float, amenities: list[str], rain_class: str) -> str:
    p = premium_pct(asking, baseline)
    if verdict_str == "fair":
        return (f"Asking ${asking:,.0f} is within {p:.1f}% of the ${baseline:,.0f} cluster average for this town/flat-type. "
                "Reasonable offer; proceed with valuation inspection.")
    if verdict_str == "premium justified":
        amen_str = ", ".join(amenities) if amenities else "future amenity uplift"
        return (f"Asking ${asking:,.0f} is {p:.1f}% above the ${baseline:,.0f} cluster baseline, but "
                f"future amenities within 1 km ({amen_str}) support the premium. Worth negotiating toward the baseline.")
    return (f"Asking ${asking:,.0f} is {p:.1f}% above the ${baseline:,.0f} cluster baseline with "
            f"no clear uplift within 1 km"
            + (f" and above-average rainfall ({rain_class})" if rain_class == "above-average" else "")
            + ". Negotiate down toward baseline or look at comparable towns.")


def assess(town: str, flat_type: str, since: str, asking: float) -> dict:
    if flat_type.upper().replace(" ", "-") not in FLAT_TYPES:
        raise ValueError(f"unknown flat_type: {flat_type!r}; valid: {sorted(FLAT_TYPES)}")
    records = fetch_hdb_records(town, flat_type, since)
    baseline = cluster_average(records)
    if baseline is None:
        raise ValueError(f"no HDB resale records for {town} {flat_type} since {since}")
    amenities = future_amenities(town, records)
    rain = rainfall_history()
    v = verdict(asking, baseline, amenities, rain["classification"])
    return {
        "town": town.upper(),
        "flat_type": flat_type.upper().replace(" ", "-"),
        "since": since,
        "asking": asking,
        "cluster_avg": round(baseline, 2),
        "premium_pct": round(premium_pct(asking, baseline), 1),
        "verdict": v,
        "future_amenities": amenities,
        "rainfall_history": rain,
        "recommendation": recommendation(v, baseline, asking, amenities, rain["classification"]),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Resale HDB value advisor")
    p.add_argument("--town", required=True, help="HDB town name (e.g. BISHAN)")
    p.add_argument("--flat-type", required=True, help=f"One of {sorted(FLAT_TYPES)}")
    p.add_argument("--since", required=True, help="YYYY-MM-DD or YYYY-MM inclusive lower bound")
    p.add_argument("--asking", type=float, required=True, help="Asking price in SGD")
    args = p.parse_args(argv)
    try:
        result = assess(args.town, args.flat_type, args.since, args.asking)
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 0
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
