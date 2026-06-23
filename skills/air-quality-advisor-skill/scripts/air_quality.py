#!/usr/bin/env python3
"""Air Quality Advisor — current PSI/PM2.5/UV + 4-day forecast for any location.

Imports from the per-skill singapore_api copy. Stdlib only. No pip deps.

Usage:
    python3 scripts/air_quality.py --location "Bishan Park"
    python3 scripts/air_quality.py --location 1.3508,103.8494
    python3 scripts/air_quality.py --postcode 570123

Exit code 0 on success. JSON to stdout.
"""

import argparse
import json
import re
import sys
from typing import Any

from singapore_api import (
    fetch_psi,
    fetch_pm25,
    fetch_uv,
    fetch_four_day_forecast,
    geocode,
)


HEALTH_BANDS = [
    (50, "good", "Good for outdoor activities"),
    (100, "moderate", "Moderate — limit prolonged outdoor exertion"),
    (200, "unhealthy", "Unhealthy — sensitive groups should avoid outdoor activity"),
    (300, "very_unhealthy", "Very unhealthy — avoid outdoor activity"),
    (10**9, "hazardous", "Hazardous — avoid all outdoor activity, stay indoors"),
]

PM25_BANDS = [
    (12, "good", "Good for outdoor activities"),
    (55, "moderate", "Moderate — limit prolonged outdoor exertion"),
    (150, "unhealthy", "Unhealthy — sensitive groups should avoid outdoor activity"),
    (250, "very_unhealthy", "Very unhealthy — avoid outdoor activity"),
    (10**9, "hazardous", "Hazardous — avoid all outdoor activity, stay indoors"),
]

UV_BANDS = [
    (3, "low", "Low UV — no protection needed"),
    (6, "moderate", "Moderate UV — wear sunscreen"),
    (8, "high", "High UV — protection essential"),
    (11, "very_high", "Very high UV — extra protection"),
    (10**9, "extreme", "Extreme UV — avoid sun exposure, protect skin"),
]


def _classify_psi(psi: int) -> dict:
    for threshold, label, advisory in HEALTH_BANDS:
        if psi <= threshold:
            return {"band": label, "advisory": advisory}
    return {"band": "unknown", "advisory": "Reading unavailable"}


def _classify_pm25(pm25: int) -> dict:
    for threshold, label, advisory in PM25_BANDS:
        if pm25 <= threshold:
            return {"band": label, "advisory": advisory}
    return {"band": "unknown", "advisory": "Reading unavailable"}


def _classify_uv(uv: int) -> dict:
    for threshold, label, advisory in UV_BANDS:
        if uv <= threshold:
            return {"band": label, "advisory": advisory}
    return {"band": "unknown", "advisory": "Reading unavailable"}


def _psi_national(psi_data: Any) -> int | None:
    items = psi_data.get("items") or []
    if not items:
        return None
    reading = items[0].get("reading") or items[0].get("readings") or {}
    val = reading.get("psi_twenty_four_hourly") or reading.get("psi_three_hourly")
    if isinstance(val, dict):
        val = val.get("national")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _pm25_national(pm25_data: Any) -> int | None:
    items = pm25_data.get("items") or []
    if not items:
        return None
    reading = items[0].get("reading") or items[0].get("readings") or {}
    val = reading.get("pm25_one_hourly") or reading.get("pm25_twenty_four_hourly")
    if isinstance(val, dict):
        val = val.get("national")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _uv_national(uv_data: Any) -> int | None:
    items = uv_data.get("items") or []
    if not items:
        return None
    val = items[0].get("index")
    if val is None:
        return None
    if isinstance(val, list):
        if not val:
            return None
        val = val[0].get("value") if isinstance(val[0], dict) else val[0]
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _resolve_location(args) -> dict:
    if args.postcode:
        if not re.match(r"^\d{6}$", args.postcode):
            raise ValueError("postcode must be exactly 6 digits: " + args.postcode)
        geocoded = geocode(args.postcode)
        if geocoded is None:
            raise ValueError("postcode not found: " + args.postcode)
        address, lat, lon, postal = geocoded
        return {"source": "postcode", "postcode": args.postcode, "address": address, "lat": lat, "lon": lon}
    if args.location and "," in args.location:
        m = re.match(r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$", args.location)
        if not m:
            raise ValueError("--location lat,lon must be two numbers separated by a comma")
        return {"source": "lat,lon", "address": args.location, "lat": float(m.group(1)), "lon": float(m.group(2))}
    if args.location:
        geocoded = geocode(args.location)
        if geocoded is None:
            raise ValueError("address not found: " + args.location)
        address, lat, lon, postal = geocoded
        return {"source": "address", "address": address, "lat": lat, "lon": lon}
    raise ValueError("either --location or --postcode is required")


def _forecast_summary(forecast_data: Any) -> list[dict]:
    items = forecast_data.get("items") or []
    if not items:
        return []
    out = []
    for day in items:
        timestamp = day.get("timestamp") or day.get("date") or ""
        date = str(timestamp)[:10] if timestamp else None
        forecast_text = None
        temp_low, temp_high = None, None
        humidity_low, humidity_high = None, None
        wind_low, wind_high = None, None
        for p in day.get("forecasts") or []:
            if not isinstance(p, dict):
                continue
            if forecast_text is None and p.get("forecast"):
                forecast_text = p.get("forecast")
            t = p.get("temperature")
            if isinstance(t, dict):
                temp_low = t.get("low")
                temp_high = t.get("high")
            h = p.get("relative_humidity") or p.get("humidity")
            if isinstance(h, dict):
                humidity_low = h.get("low")
                humidity_high = h.get("high")
            w = p.get("wind")
            if isinstance(w, dict):
                speed = w.get("speed")
                if isinstance(speed, dict):
                    wind_low = speed.get("low")
                    wind_high = speed.get("high")
        out.append({
            "date": date,
            "forecast": forecast_text,
            "temperature_low_c": temp_low,
            "temperature_high_c": temp_high,
            "relative_humidity_low_pct": humidity_low,
            "relative_humidity_high_pct": humidity_high,
            "wind_speed_low_kmh": wind_low,
            "wind_speed_high_kmh": wind_high,
        })
    return out


def _health_advisory(psi_band: str, pm25_band: str, uv_band: str) -> str:
    rank = {
        "good": 1, "low": 1,
        "moderate": 2,
        "high": 3, "unhealthy": 3,
        "very_high": 4, "very_unhealthy": 4,
        "extreme": 5, "hazardous": 5,
    }
    worst = max(((band, rank.get(band, 0)) for band in (psi_band, pm25_band, uv_band)), key=lambda x: x[1])[0]
    text = {
        "good": "Good for outdoor activities",
        "low": "Good for outdoor activities",
        "moderate": "Moderate — limit prolonged outdoor exertion",
        "high": "High UV — protection essential",
        "unhealthy": "Unhealthy — sensitive groups should avoid outdoor activity",
        "very_high": "Very high UV — extra protection",
        "very_unhealthy": "Very unhealthy — avoid outdoor activity",
        "extreme": "Extreme UV — avoid sun exposure, protect skin",
        "hazardous": "Hazardous — avoid all outdoor activity, stay indoors",
    }
    return text.get(worst, "Reading unavailable")


def assess(location: dict) -> dict:
    psi_data = fetch_psi()
    pm25_data = fetch_pm25()
    uv_data = fetch_uv()
    forecast_data = fetch_four_day_forecast()

    psi_val = _psi_national(psi_data)
    pm25_val = _pm25_national(pm25_data)
    uv_val = _uv_national(uv_data)

    psi_block = {"value": psi_val, **_classify_psi(psi_val)} if psi_val is not None else {"value": None, "band": "unknown", "advisory": "Reading unavailable"}
    pm25_block = {"value": pm25_val, **_classify_pm25(pm25_val)} if pm25_val is not None else {"value": None, "band": "unknown", "advisory": "Reading unavailable"}
    uv_block = {"value": uv_val, **_classify_uv(uv_val)} if uv_val is not None else {"value": None, "band": "unknown", "advisory": "Reading unavailable"}

    advisory = _health_advisory(psi_block["band"], pm25_block["band"], uv_block["band"])
    forecast_days = _forecast_summary(forecast_data)

    return {
        "current": {"psi": psi_block, "pm25": pm25_block, "uv": uv_block},
        "health_advisory": advisory,
        "forecast": {"next_4_days": forecast_days},
        "location": location,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Singapore air-quality advisor (PSI/PM2.5/UV + 4-day forecast)")
    p.add_argument("--location", help="Address OR lat,lon pair (e.g. '1.3508,103.8494')")
    p.add_argument("--postcode", help="6-digit Singapore postcode")
    args = p.parse_args(argv)

    if bool(args.location) == bool(args.postcode):
        print(json.dumps({"error": "provide exactly one of --location or --postcode"}), file=sys.stdout)
        return 0

    try:
        loc = _resolve_location(args)
        result = assess(loc)
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 0

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
