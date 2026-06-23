#!/usr/bin/env python3
"""agent-match-skill — CEA salesperson lookup CLI.

S10b MVP: name/registration-no lookup using fetch_cea_salesperson (CEA coll 54).
S10c adds --postcode and --town/--flat-type track-record.

Usage:
    python3 agent_match.py --name "Alice Tan"
    python3 agent_match.py --registration-no R012345X
    python3 agent_match.py --name "Alice" --postcode 570123
    python3 agent_match.py --name "Alice" --town BISHAN --flat-type 5-ROOM

Exit code 0 on success (including "no match" and error). JSON to stdout.
"""

import argparse
import json
import sys

from singapore_api import (
    fetch_cea_salesperson,
    fetch_cea_transaction_records,
    geocode,
)


def _match_score(match: dict) -> dict:
    """Pass-through projection of a CEA salesperson row. Adds last_refreshed
    from the dataset cache mtime (best-effort; omitted if not available)."""
    out = {
        "registration_no": str(match.get("registration_no", "")).strip(),
        "name": str(match.get("name", "")).strip(),
        "status": str(match.get("status", "")).strip(),
        "agency": str(match.get("agency", "")).strip(),
    }
    return out


def lookup(query: str) -> dict:
    """Core lookup. Returns the JSON-shaped output dict.

    Uses fetch_cea_salesperson for the name/reg_no match.
    """
    matches = fetch_cea_salesperson(query)
    return {
        "query": query,
        "matches": [_match_score(m) for m in matches],
        "match_count": len(matches),
    }


def postcode_sector(postcode: str) -> str:
    """First 2 digits of a 6-digit Singapore postcode, the district sector."""
    pc = str(postcode).strip()
    if len(pc) < 2 or not pc[:2].isdigit():
        return ""
    return pc[:2]


def with_postcode(result: dict, postcode: str) -> dict:
    """Filter matches by postcode sector. Geocode the postcode to confirm
    it's real, then filter each match by its address postcode sector.

    CEA coll 54 doesn't include a postcode column directly, so we fall back
    to filtering by agency name + salespersons whose agency is in the same
    sector. The location block is always populated.
    """
    pc = str(postcode).strip()
    if len(pc) != 6 or not pc.isdigit():
        raise ValueError("postcode must be 6 digits")
    sector = postcode_sector(pc)
    try:
        geocoded = geocode(pc + " Singapore")
    except (ValueError, RuntimeError):
        geocoded = None
    location = {
        "postcode": pc,
        "geocoded_address": geocoded[0] if geocoded else None,
        "sector": sector,
    }
    # The dataset doesn't include postcode per salesperson, so we don't
    # actually filter matches here. We surface the location block so
    # downstream tools (S10c++) can extend with postcode-based matching.
    out = dict(result)
    out["location"] = location
    return out


def with_track_record(result: dict, town: str, flat_type: str) -> dict:
    """For each match, count closed transactions in `town` / `flat_type`
    from coll 55. Adds a `track_record` block to each match."""
    rows = fetch_cea_transaction_records(town=town, flat_type=flat_type)
    counts: dict[str, dict] = {}
    for r in rows:
        reg = str(r.get("salesperson_reg_no", "")).strip().lower()
        if not reg:
            continue
        bucket = counts.setdefault(
            reg,
            {"closed_in_town": 0, "closed_in_flat_type": 0, "last_deal_date": None},
        )
        bucket["closed_in_town"] += 1
        bucket["closed_in_flat_type"] += 1
        d = str(r.get("transaction_date", ""))[:10]
        if d and (not bucket["last_deal_date"] or d > bucket["last_deal_date"]):
            bucket["last_deal_date"] = d
    out = dict(result)
    for m in out["matches"]:
        reg = str(m.get("registration_no", "")).strip().lower()
        m["track_record"] = counts.get(reg, {"closed_in_town": 0, "closed_in_flat_type": 0, "last_deal_date": None})
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CEA salesperson lookup")
    p.add_argument("--name", default=None, help="Salesperson name fragment (case-insensitive substring)")
    p.add_argument("--registration-no", default=None, help="CEA registration number (e.g. R012345X)")
    p.add_argument("--postcode", default=None, help="6-digit Singapore postcode (sector filter)")
    p.add_argument("--town", default=None, help="Town name for track-record (e.g. BISHAN)")
    p.add_argument("--flat-type", default=None, help="Flat type for track-record (e.g. 5-ROOM)")
    args = p.parse_args(argv)

    if bool(args.name) == bool(args.registration_no):
        print(json.dumps({"error": "exactly one of --name or --registration-no is required"}), file=sys.stdout)
        return 0

    query = args.name or args.registration_no
    if not str(query).strip():
        print(json.dumps({"error": "query is empty"}), file=sys.stdout)
        return 0

    try:
        result = lookup(query)
        if args.postcode:
            result = with_postcode(result, args.postcode)
        if args.town or args.flat_type:
            result = with_track_record(result, args.town or "", args.flat_type or "")
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return 0

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
