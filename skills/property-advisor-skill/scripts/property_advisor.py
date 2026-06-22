#!/usr/bin/env python3
"""Property Advisor (v2) — HDB resale, private condo, rental, EC, and investment lens.

Imports from the per-skill singapore_api copy. Stdlib only. No pip deps.

Five modes (default = hdb, v1 behavior preserved):
    hdb        — HDB resale cluster baseline + URA uplift + NEA rainfall (v1)
    private    — URA Private Residential Property Transactions (by region)
    rental     — URA Rentals of Non-Landed Residential Buildings
    ec         — URA Executive Condominium sales + sale position
    investment — overlay of SINGSTAT supply pipeline + URA unsold units
                 (used with --property-mode to pick the base series)

Usage:
    # HDB resale (v1, default mode)
    python3 property_advisor.py --town BISHAN --flat-type 5-ROOM \\
        --since 2025-12-01 --asking 720000

    # Private condo (whole SG)
    python3 property_advisor.py --mode private --region whole_sg \\
        --town BISHAN --flat-type CONDO --since 2024-12-01 --asking 1500000

    # Rental
    python3 property_advisor.py --mode rental --region outside_central \\
        --town BISHAN --flat-type CONDO --since 2024-12-01 --asking 4200

    # EC
    python3 property_advisor.py --mode ec --town BUKIT_BATOK \\
        --flat-type EC --since 2024-12-01 --asking 1100000

    # Investment lens (overlay on HDB)
    python3 property_advisor.py --mode investment --property-mode hdb \\
        --town BISHAN --flat-type 5-ROOM --since 2025-12-01 --asking 720000

    # Verify a CEA salesperson alongside the verdict
    python3 property_advisor.py --mode hdb --town BISHAN --flat-type 5-ROOM \\
        --since 2025-12-01 --asking 720000 --verify-salesperson "R012345X"

Exit code 0 on success. JSON to stdout.
"""

import argparse
import json
import re
import statistics
import sys
from typing import Any

from singapore_api import (
    HDB_RESALE_DATASET_ID,
    fetch_cea_salesperson,
    fetch_dataset_rows,
    fetch_nea_historical_rainfall,
    fetch_singstat_supply_pipeline,
    fetch_singstat_vacancy,
    fetch_ura_ec_position,
    fetch_ura_ec_sales,
    fetch_ura_master_plan,
    fetch_ura_private_resi_trans,
    fetch_ura_rentals,
    fetch_ura_unsold_private_resi,
    geocode,
    haversine_m,
    svy21_to_wgs84,
)


# ── Constants (v1 preserved) ───────────────────────────────────────────

FLAT_TYPES = {
    "1-ROOM", "2-ROOM", "3-ROOM", "4-ROOM", "5-ROOM", "EXEC",
    "MULTI-GEN", "STUDIO",
}

MODES = ("hdb", "private", "rental", "ec", "investment")
PRIVATE_REGIONS = ("whole_sg", "central", "rest_central", "outside_central")

RAINFALL_LOOKBACK_24MO = 24
RAINFALL_LOOKBACK_5YR = 60
RAISE_SIGMA = 1.0
URA_RADIUS_M = 1000.0
AMENITY_RADIUS_M = 1000.0

# Investment overlay: pipeline + unsold > 1.5x trailing-4Q demand = surplus
#                    pipeline + unsold < 0.5x trailing-4Q demand = tight
SUPPLY_SURPLUS_RATIO = 1.5
SUPPLY_TIGHT_RATIO = 0.5

LU_CATEGORIES = [
    (re.compile(r"\b(school|primary|secondary|junior college)\b", re.I), "primary_school"),
    (re.compile(r"\b(hospital|clinic|polyclinic|healthcare|nursing home)\b", re.I), "healthcare"),
    (re.compile(r"\b(mrt|station|metro|rapid transit)\b", re.I), "MRT"),
    (re.compile(r"\b(business|office|commercial hub|cbd)\b", re.I), "business_hub"),
    (re.compile(r"\b(industrial|factory|warehouse)\b", re.I), "industrial"),
]

# Unicode block characters for 8-bin sparkline. Ordered low->high.
SPARKLINE_BINS = "▁▂▃▄▅▆▇█"


# ── Pure helpers (v1 preserved) ────────────────────────────────────────

def to_float(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _since_iso(s):
    parts = s.split("-")
    if len(parts) < 1:
        raise ValueError("since must be YYYY-MM-DD or YYYY-MM")
    return int(parts[0]) * 100 + int(parts[1]) if len(parts) >= 2 else int(parts[0]) * 100


def categorise_lu(lu_desc):
    if not lu_desc:
        return None
    for rx, label in LU_CATEGORIES:
        if rx.search(lu_desc):
            return label
    return None


def cluster_centroid_easting_northing(records):
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


# ── Trend block (new in v2) ────────────────────────────────────────────

def sparkline(values):
    """Map `values` to 8 unicode block chars (`SPARKLINE_BINS`).

    Equal-width bins across the value range. Flat series (hi == lo) -> all-low bar.
    Empty input -> empty string.
    """
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARKLINE_BINS[0] * len(values)
    n = len(SPARKLINE_BINS)
    spread = hi - lo
    return "".join(SPARKLINE_BINS[min(n - 1, int((v - lo) / spread * n))] for v in values)


def trend_block(records, value_key, qtr_key="qtr", n_periods=8):
    """Build the uniform trend block: `last_8_quarters`, `qoq_pct`,
    `yoy_pct`, `sparkline`. `records` must be sorted oldest->newest.

    `value_key` is the per-period metric column (e.g. "median_psf",
    "median_total", "median_rent_psf_pm"). QoQ uses the last 2 periods.
    YoY uses last vs (n_periods - 4)th-from-last. Skips records where
    `value_key` is not coercible to float.
    """
    series = []
    for r in records:
        v = to_float(r.get(value_key))
        if v is None:
            continue
        q = r.get(qtr_key) or r.get("quarter") or r.get("month")
        series.append({"qtr": q, "value": round(v, 2)})
    if not series:
        return {
            "last_8_quarters": [],
            "qoq_pct": 0.0,
            "yoy_pct": 0.0,
            "sparkline": "",
        }
    last_n = series[-n_periods:]
    values = [s["value"] for s in last_n]
    qoq = ((values[-1] - values[-2]) / values[-2] * 100.0) if len(values) >= 2 and values[-2] else 0.0
    yoy_idx = -5
    yoy = 0.0
    if len(values) >= abs(yoy_idx) and values[yoy_idx]:
        yoy = (values[-1] - values[yoy_idx]) / values[yoy_idx] * 100.0
    return {
        "last_8_quarters": last_n,
        "qoq_pct": round(qoq, 1),
        "yoy_pct": round(yoy, 1),
        "sparkline": sparkline(values),
    }


# ── HDB mode (v1 preserved) ────────────────────────────────────────────

def fetch_hdb_records(town, flat_type, since):
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


def cluster_average(records):
    prices = []
    for r in records:
        p = to_float(r.get("resale_price"))
        if p is not None:
            prices.append(p)
    if not prices:
        return None
    return sum(prices) / len(prices)


def premium_pct(asking, baseline):
    if baseline <= 0:
        return 0.0
    return (asking - baseline) / baseline * 100.0


def _amenities_around_latlon(lat, lon, radius_m):
    envelope = fetch_ura_master_plan()
    features = envelope.get("result", {}).get("records", [])
    found = set()
    for f in features:
        x = to_float(f.get("_x") or f.get("x") or f.get("easting"))
        y = to_float(f.get("_y") or f.get("y") or f.get("northing"))
        if x is None or y is None:
            continue
        wgs = svy21_to_wgs84(float(x), float(y))
        flat_lat = wgs[0]
        flat_lon = wgs[1]
        if haversine_m(lat, lon, flat_lat, flat_lon) > radius_m:
            continue
        cat = categorise_lu(f.get("lu_desc", "") or f.get("mpro_use", ""))
        if cat:
            found.add(cat)
    return sorted(found)


def future_amenities(town, records):
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


def rainfall_history():
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


def verdict(asking, baseline, amenities, rain_class):
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


def recommendation(verdict_str, baseline, asking, amenities, rain_class):
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


# ── Private / rental / EC mode helpers (v2) ────────────────────────────

def _filter_records_by_period(records, since, period_key="qtr"):
    """Filter `records` to those with period >= `since`. `since` is YYYY-MM;
    period strings may be YYYY-Q# or YYYY-MM."""
    since_yyyymm = _since_iso(since)
    out = []
    for r in records:
        p = r.get(period_key) or r.get("quarter") or r.get("month")
        if p is None:
            continue
        s = str(p).strip()
        # Convert YYYY-Q# -> YYYY-MM-equivalent (q1=01, q2=04, q3=07, q4=10)
        m = re.match(r"^(\d{4})[-\s]?[qQ]([1-4])$", s)
        if m:
            year = int(m.group(1))
            q = int(m.group(2))
            month = (q - 1) * 3 + 1
            s = f"{year}-{month:02d}"
        try:
            s_yyyymm = _since_iso(s)
        except (TypeError, ValueError):
            continue
        if s_yyyymm >= since_yyyymm:
            out.append(r)
    return out


def fetch_private_records(town, region, since):
    records = fetch_ura_private_resi_trans(region)
    return _filter_records_by_period(records, since, "qtr")


def fetch_rental_records(town, region, since):
    records = fetch_ura_rentals()
    return _filter_records_by_period(records, since, "qtr")


def fetch_ec_records(town, since):
    sales = fetch_ura_ec_sales()
    position = fetch_ura_ec_position()
    return (
        _filter_records_by_period(sales, since, "qtr"),
        _filter_records_by_period(position, since, "qtr"),
    )


def _median_value(records, value_key):
    vals = [to_float(r.get(value_key)) for r in records]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return statistics.median(vals)


# ── Location block (v2) ────────────────────────────────────────────────

def location_block(town):
    """Return {town, planning_area, region, nearest_mrt}. Falls back to
    `planning_area=town, region=unknown, nearest_mrt=unknown` if geocoding
    fails (which is the common offline case)."""
    out = {
        "town": town.upper(),
        "planning_area": town.upper(),
        "region": "unknown",
        "nearest_mrt": "unknown",
    }
    try:
        geocoded = geocode(f"{town}, Singapore")
    except (ValueError, RuntimeError):
        return out
    if geocoded is None:
        return out
    # geocode returns (search_val, lat, lon). We can't reverse-geocode MRT
    # offline, so just record coordinates-derived info if available.
    _ = geocoded
    return out


# ── Investment overlay (v2) ────────────────────────────────────────────

def _trailing_4q_demand(records, demand_key="sale_count"):
    """Sum the last 4 periods of `demand_key` from records (chronological)."""
    vals = [to_float(r.get(demand_key)) for r in records[-4:]]
    vals = [v for v in vals if v is not None]
    return sum(vals)


def investment_overlay_for(private_records=None):
    """Compute the supply-vs-demand overlay.

    Reads two sources (SINGSTAT supply pipeline + URA unsold private resi)
    plus the trailing 4Q demand from the most recent private trans series.
    Returns `supply_signal` in {tight, balanced, surplus} and the raw numbers.
    """
    pipeline = fetch_singstat_supply_pipeline()
    unsold = fetch_ura_unsold_private_resi()
    vacancy = fetch_singstat_vacancy()

    # Total supply: sum latest "In Planning" + "Under Construction" from pipeline
    # (SINGSTAT series names are spacy like "In Planning" / "Under Construction")
    # and total unsold from URA coll 1663 (column "unsold_units" or similar).
    pipeline_latest = {}
    for row in pipeline:
        series = row["series"]
        pipeline_latest[series] = pipeline_latest.get(series, 0.0) + row["value"]
    total_pipeline = sum(pipeline_latest.values())

    # URA unsold records: sum the latest quarter's unsold_units across all rows
    unsold_latest_qtr = {}
    for row in unsold:
        qtr = row.get("quarter") or row.get("qtr")
        if qtr is None:
            continue
        v = to_float(row.get("unsold_units") or row.get("value"))
        if v is None:
            continue
        unsold_latest_qtr[qtr] = unsold_latest_qtr.get(qtr, 0.0) + v
    total_unsold = max(unsold_latest_qtr.values()) if unsold_latest_qtr else 0.0

    # Trailing 4Q demand
    if private_records:
        trailing_4q = _trailing_4q_demand(private_records, "sale_count")
    else:
        trailing_4q = 0.0

    supply_ratio = (total_pipeline + total_unsold) / trailing_4q if trailing_4q else 0.0
    if supply_ratio > SUPPLY_SURPLUS_RATIO:
        signal = "surplus"
    elif 0 < supply_ratio < SUPPLY_TIGHT_RATIO:
        signal = "tight"
    else:
        signal = "balanced"

    return {
        "supply_pipeline_units": int(total_pipeline),
        "unsold_units": int(total_unsold),
        "trailing_4q_demand": int(trailing_4q),
        "supply_ratio": round(supply_ratio, 2) if supply_ratio else 0.0,
        "supply_signal": signal,
        "vacancy_series_count": len(vacancy),
    }


# ── CEA salesperson verification (v2) ──────────────────────────────────

def cea_verification(query):
    """Best-effort CEA salesperson lookup. Returns `None` when query is empty
    or no match. Logs a warning (printed to stderr) on lookup failures so
    the main JSON payload stays clean."""
    if not query:
        return None
    try:
        rows = fetch_cea_salesperson(query)
    except Exception as e:  # noqa: BLE001
        print("warning: CEA lookup failed: %s" % e, file=sys.stderr)
        return None
    if not rows:
        return None
    r = rows[0]
    return {
        "registration_no": r.get("registration_no"),
        "name": r.get("name"),
        "status": r.get("status"),
        "agency": r.get("agency"),
    }


# ── Mode assessors (v2) ────────────────────────────────────────────────

def _hdb_trend_from_records(records):
    """Aggregate HDB monthly records into 8 quarters and return trend block."""
    by_qtr = {}
    for r in records:
        month = r.get("month") or r.get("transaction_month")
        if not month:
            continue
        s = str(month)[:7]
        try:
            year, mon = s.split("-")
            year_i, mon_i = int(year), int(mon)
        except (TypeError, ValueError):
            continue
        q = (mon_i - 1) // 3 + 1
        qtr = "%d-Q%d" % (year_i, q)
        p = to_float(r.get("resale_price"))
        if p is None:
            continue
        by_qtr.setdefault(qtr, []).append(p)
    qtr_records = [{"qtr": q, "value": round(statistics.median(v), 2)} for q, v in sorted(by_qtr.items())]
    return trend_block(qtr_records, "value", "qtr", 8)


def assess_hdb(town, flat_type, since, asking, cea_query=None):
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
        "mode": "hdb",
        "town": town.upper(),
        "flat_type": flat_type.upper().replace(" ", "-"),
        "since": since,
        "asking": asking,
        "verdict": v,
        "cluster_avg": round(baseline, 2),
        "premium_pct": round(premium_pct(asking, baseline), 1),
        "trend": _hdb_trend_from_records(records),
        "location": location_block(town),
        "ura_context": {"future_amenities_within_1km": amenities},
        "rainfall_history": rain,
        "cea_verification": cea_verification(cea_query),
        "recommendation": recommendation(v, baseline, asking, amenities, rain["classification"]),
    }


def _generic_quarters_assess(records, town, asking, value_key, mode,
                             price_unit, cea_query=None):
    """Shared logic for private/rental/ec modes: median per series,
    trend block, premium vs trailing median, CEA verify."""
    if not records:
        raise ValueError(f"no {mode} records for {town} since cutoff")
    baseline = _median_value(records, value_key)
    if baseline is None:
        raise ValueError(f"no {value_key} values in {mode} records for {town}")
    trend = trend_block(records, value_key, "qtr", 8)
    p = premium_pct(asking, baseline)
    as_of = records[-1].get("qtr") or records[-1].get("quarter") or "unknown"
    if p <= 5.0:
        v = "fair"
    elif p <= 15.0:
        v = "premium justified"
    else:
        v = "above market"
    return {
        "mode": mode,
        "town": town.upper(),
        "asking": asking,
        "as_of_quarter": as_of,
        "verdict": v,
        "cluster_median_psf": baseline if price_unit == "psf" else None,
        "cluster_median_total": baseline if price_unit == "total" else None,
        "premium_pct": round(p, 1),
        "trend": trend,
        "location": location_block(town),
        "ura_context": {"future_amenities_within_1km": future_amenities(town, [])},
        "cea_verification": cea_verification(cea_query),
    }


def assess_private(town, region, since, asking, cea_query=None):
    records = fetch_private_records(town, region, since)
    return _generic_quarters_assess(records, town, asking, "median_psf", "private",
                                    "psf", cea_query)


def assess_rental(town, region, since, asking, cea_query=None):
    records = fetch_rental_records(town, region, since)
    return _generic_quarters_assess(records, town, asking, "median_rent_psf_pm", "rental",
                                    "psf", cea_query)


def assess_ec(town, since, asking, cea_query=None):
    sales, _position = fetch_ec_records(town, since)
    if not sales:
        raise ValueError(f"no EC sales records for {town} since {since}")
    # EC sales carry total units sold per quarter; median is meaningless at the
    # town level (one row per EC project per quarter). Use the latest row.
    latest = sales[-1]
    baseline = to_float(latest.get("median_psf") or latest.get("median_trans_price"))
    if baseline is None:
        raise ValueError(f"no median price in latest EC record for {town}")
    value_key = "median_psf" if "median_psf" in latest else "median_trans_price"
    trend = trend_block(sales, value_key, "qtr", 8)
    p = premium_pct(asking, baseline)
    if p <= 5.0:
        v = "fair"
    elif p <= 12.0:
        v = "premium justified"
    else:
        v = "above market"
    return {
        "mode": "ec",
        "town": town.upper(),
        "since": since,
        "asking": asking,
        "as_of_quarter": latest.get("qtr", "unknown"),
        "verdict": v,
        "cluster_median_psf": baseline,
        "premium_pct": round(p, 1),
        "trend": trend,
        "location": location_block(town),
        "ura_context": {"future_amenities_within_1km": future_amenities(town, [])},
        "cea_verification": cea_verification(cea_query),
    }


def assess_investment(town, flat_type, since, asking, property_mode="hdb",
                      region="whole_sg", cea_query=None):
    """Run the base mode's assess, then overlay the supply-vs-demand signal."""
    if property_mode == "hdb":
        base = assess_hdb(town, flat_type, since, asking, cea_query=cea_query)
        private_records = None
    elif property_mode == "private":
        base = assess_private(town, region, since, asking, cea_query=cea_query)
        private_records = fetch_private_records(town, region, since)
    elif property_mode == "rental":
        base = assess_rental(town, region, since, asking, cea_query=cea_query)
        private_records = fetch_private_records(town, region, since)
    elif property_mode == "ec":
        base = assess_ec(town, since, asking, cea_query=cea_query)
        private_records = fetch_private_records(town, region, since)
    else:
        raise ValueError(f"unknown --property-mode: {property_mode!r}")
    base["mode"] = "investment"
    base["property_mode"] = property_mode
    base["investment_overlay"] = investment_overlay_for(private_records)
    return base


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description="Singapore property advisor (HDB, private, rental, EC, investment)")
    p.add_argument("--mode", choices=MODES, default="hdb",
                   help="Advisory mode. Default 'hdb' (v1 behaviour).")
    p.add_argument("--property-mode", choices=("hdb", "private", "rental", "ec"),
                   help="Base series for --mode investment. Required when --mode=investment.")
    p.add_argument("--region", choices=PRIVATE_REGIONS, default="whole_sg",
                   help="Region for --mode private/rental/investment. Default 'whole_sg'.")
    p.add_argument("--town", required=True, help="Town / planning area (e.g. BISHAN)")
    p.add_argument("--flat-type", required=True,
                   help=f"HDB flat type ({sorted(FLAT_TYPES)}) or property type label for private/rental/ec")
    p.add_argument("--since", required=True, help="YYYY-MM-DD or YYYY-MM inclusive lower bound")
    p.add_argument("--asking", type=float, required=True, help="Asking price in SGD (or monthly rent for --mode rental)")
    p.add_argument("--verify-salesperson", default=None,
                   help="CEA registration no (e.g. R012345X) or name fragment to verify")
    p.add_argument("--json", action="store_true", default=True, help="Emit JSON (default true)")
    args = p.parse_args(argv)

    if args.mode == "investment" and not args.property_mode:
        print(json.dumps({"error": "--mode investment requires --property-mode"}), file=sys.stdout)
        return 0

    try:
        if args.mode == "hdb":
            result = assess_hdb(args.town, args.flat_type, args.since, args.asking,
                                cea_query=args.verify_salesperson)
        elif args.mode == "private":
            result = assess_private(args.town, args.region, args.since, args.asking,
                                    cea_query=args.verify_salesperson)
        elif args.mode == "rental":
            result = assess_rental(args.town, args.region, args.since, args.asking,
                                   cea_query=args.verify_salesperson)
        elif args.mode == "ec":
            result = assess_ec(args.town, args.since, args.asking,
                               cea_query=args.verify_salesperson)
        else:  # investment
            result = assess_investment(
                args.town, args.flat_type, args.since, args.asking,
                property_mode=args.property_mode or "hdb",
                region=args.region,
                cea_query=args.verify_salesperson,
            )
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 0
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
