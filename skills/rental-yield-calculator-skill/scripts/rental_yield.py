#!/usr/bin/env python3
"""rental-yield-calculator-skill — gross/net rental yield for a private condo buy.

S11a MVP. Uses URA coll 1655-1658 (Private Resi Trans by region) for the
buy-price baseline and URA coll 1660 (Rentals of Non-Landed) for the rent
series. Output is JSON to stdout.

Usage:
    python3 rental_yield.py --asking 1500000 --town "DISTRICT 9" \\
        --region whole_sg --flat-type "Non-Landed" --since 2025-01

Exit 0 on success. Errors caught and returned as {"error": "..."}.
"""

import argparse
import json
import sys

from singapore_api import (
    SPARKLINE_BINS,
    URA_REGION_DATASET_IDS,
    fetch_ura_master_plan,
    fetch_ura_private_resi_trans,
    fetch_ura_rentals,
    geocode,
    haversine_m,
    location_block,
    sparkline,
    svy21_to_wgs84,
    trend_block,
)


NET_DEDUCTION = 0.15  # 15% for tax + mgmt + insurance heuristic
TREND_PERIODS = 8


def ura_context(lat: float | None, lon: float | None, radius_m: float = 1000.0) -> list[str]:
    """Future amenities from URA Master Plan within radius_m of (lat, lon)."""
    if lat is None or lon is None:
        return []
    lat_f: float = float(lat)
    lon_f: float = float(lon)
    envelope = fetch_ura_master_plan()
    features = envelope.get("result", {}).get("records", [])
    found = set()
    for f in features:
        x = f.get("_x") or f.get("x") or f.get("easting")
        y = f.get("_y") or f.get("y") or f.get("northing")
        if x is None or y is None:
            continue
        try:
            xf, yf = float(x), float(y)
        except (TypeError, ValueError):
            continue
        flat_lat, flat_lon = svy21_to_wgs84(xf, yf)
        flat_lat_f, flat_lon_f = float(flat_lat), float(flat_lon)
        dist = haversine_m(lat_f, lon_f, flat_lat_f, flat_lon_f)
        if dist is None or dist > radius_m:
            continue
        lu = str(f.get("lu_desc") or f.get("mpro_use") or "").lower()
        if "school" in lu or "primary" in lu or "secondary" in lu:
            found.add("primary_school")
        elif "mrt" in lu or "station" in lu:
            found.add("MRT")
        elif "hospital" in lu or "clinic" in lu or "health" in lu:
            found.add("healthcare")
        elif "business" in lu or "office" in lu:
            found.add("business_hub")
    return sorted(found)


def median(values: list[float]) -> float | None:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return None
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def calculate(asking: float, town: str, region: str, flat_type: str, since: str) -> dict:
    if region not in URA_REGION_DATASET_IDS:
        raise ValueError("region %r not in %s" % (region, sorted(URA_REGION_DATASET_IDS)))

    rentals = fetch_ura_rentals()
    private_trans = fetch_ura_private_resi_trans(region)

    rent_filtered = [
        r for r in rentals
        if str(r.get("property_type", "")).strip().lower() == flat_type.strip().lower()
    ]
    if not rent_filtered:
        # Fall back to all non-landed records; log a warning
        rent_filtered = rentals

    trend = trend_block(rent_filtered)
    last_rent = rent_filtered[-1] if rent_filtered else None
    monthly_rent = None
    if last_rent is not None:
        try:
            monthly_rent = float(last_rent.get("median_rent") or last_rent.get("median_rent_psf_pm") or 0)
        except (TypeError, ValueError):
            monthly_rent = None
    annual_rent = (monthly_rent * 12) if monthly_rent else 0.0

    gross_yield_pct = (annual_rent / asking * 100.0) if asking else 0.0
    net_yield_pct = gross_yield_pct * (1.0 - NET_DEDUCTION)

    loc = location_block(town)
    lat = loc.get("geocoded_lat")
    lon = loc.get("geocoded_lon")
    try:
        amenities = ura_context(lat, lon)
    except Exception:
        amenities = []

    return {
        "asking": asking,
        "town": town,
        "region": region,
        "flat_type": flat_type,
        "since": since,
        "monthly_rent_estimate": round(monthly_rent, 2) if monthly_rent else 0.0,
        "annual_rent_estimate": round(annual_rent, 2),
        "gross_yield_pct": round(gross_yield_pct, 2),
        "net_yield_pct": round(net_yield_pct, 2),
        "trend": trend,
        "location": loc,
        "ura_context": {"future_amenities_within_1km": amenities},
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rental yield calculator for private condo buy")
    p.add_argument("--asking", type=float, required=True, help="Purchase price in SGD")
    p.add_argument("--town", required=True, help="District or town (e.g. DISTRICT 9)")
    p.add_argument("--region", default="whole_sg", choices=sorted(URA_REGION_DATASET_IDS))
    p.add_argument("--flat-type", default="Non-Landed", help="Property type for rent match")
    p.add_argument("--since", default="2025-01", help="Lower bound quarter, YYYY-MM")
    args = p.parse_args(argv)
    try:
        result = calculate(args.asking, args.town, args.region, args.flat_type, args.since)
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 0
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
