"""Buyer profiles + due-diligence checklists (data in references/*.json).

build_profile(profile_id) -> dict. Valuation args map each shortlisted category to
the existing property_advisor modes (hdb / private / ec) so asking prices can be
checked against the market.
"""
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"


def _load(name: str) -> dict:
    with open(REFS / name, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def profile_ids() -> list:
    return list(_load("buyer-profiles.json")["profiles"])


def variants(profile_id: str) -> list:
    return list(_load("buyer-profiles.json")["profiles"][profile_id].get("variants", {}))


def _expand_entry(entry: dict, categories: dict) -> dict:
    cat = categories[entry["category"]]
    out = deepcopy(entry)
    out["label"] = cat["label"]
    out["payment_model"] = cat["payment_model"]
    mode = cat["valuation_mode"]["mode"]
    segments = []
    for seg in entry.get("segments", []):
        info = categories["new_launch_condo"]["segments"][seg]
        segments.append({"segment": seg, "label": info["label"], "fit": info["fit"],
                         "tradeoff": info["tradeoff"],
                         "valuation_args": {"mode": "private", "region": info["region_arg"]}})
    out["segments"] = segments
    if mode == "hdb":
        out["valuation_args"] = {"mode": "hdb"}
        out.setdefault("flat_types", cat["flat_types"])
    elif mode == "ec":
        out["valuation_args"] = {"mode": "ec"}
    else:
        out["valuation_args"] = {"mode": "private"}
    out["category_tradeoffs"] = cat["tradeoffs"]
    return out


def build_profile(profile_id: str, variant: str = None, max_price=None, price_guides: dict = None) -> dict:
    data = _load("buyer-profiles.json")
    dd = _load("due-diligence.json")
    if profile_id not in data["profiles"]:
        raise ValueError(f"unknown profile {profile_id!r}; choose from {sorted(data['profiles'])}")
    base = deepcopy(data["profiles"][profile_id])
    variant_defs = base.pop("variants", {})
    shortlist_src = base["shortlist"]
    if variant:
        if variant not in variant_defs:
            raise ValueError(f"unknown variant {variant!r} for {profile_id}")
        v = variant_defs[variant]
        base["label"] = v["label"]
        base["priorities"] = base["priorities"] + v.get("extra_priorities", [])
        base["red_flags"] = base["red_flags"] + v.get("red_flags", [])
        shortlist_src = v.get("shortlist_override", shortlist_src)
    shortlist = [_expand_entry(e, data["categories"]) for e in shortlist_src]
    shortlist.sort(key=lambda e: e["rank"])
    if max_price is not None and price_guides:
        cap = Decimal(str(max_price))
        for e in shortlist:
            guide = price_guides.get(e["category"])
            if guide is not None and Decimal(str(guide)) > cap:
                e["likely_out_of_reach"] = True
    base["shortlist"] = shortlist
    base["profile_id"] = profile_id
    base["variant"] = variant
    base["due_diligence"] = {
        "property": dd["common_property"],
        "financial": dd["common_financial"],
        "by_category": {e["category"]: dd["by_category"][e["category"]] for e in shortlist},
    }
    base["related_skills"] = data["related_skills"]
    base["category_notes"] = {e["category"]: data["categories"][e["category"]]["tradeoffs"] for e in shortlist}
    return base
