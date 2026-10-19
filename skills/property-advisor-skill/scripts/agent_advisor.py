#!/usr/bin/env python3
"""Property-agent advisor layer (`property_advisor.py --mode agent`).

Tasks:
    profile  buyer profile: shortlist, location, questions, red flags, due diligence
    plan     cash/CPF timeline, monthly commitments and stress test for one option
    compare  two or more options side by side, with lifestyle add-ons and break-even
    advise   profile + compare (or plan) with one plain-language summary

Usage:
    python3 agent_advisor.py --task profile --profile dink
    python3 agent_advisor.py --task plan --scenario scenario.json
    python3 agent_advisor.py --task compare --scenario scenario.json
    python3 agent_advisor.py --task advise --scenario scenario.json --summary-only

No network. Policy figures come from references/policy-tables.json (dated, sourced).
Exit code 0; errors are {"error": "..."} on stdout, like the other modes.
"""
import argparse
import json
import sys
from decimal import Decimal

import agent_cashflow as cf
import agent_compare as cmp
import agent_policy as ap
import agent_profiles as pr
import agent_report as rp

TASKS = ("profile", "plan", "compare", "advise")


def _json_default(o):
    if isinstance(o, Decimal):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def _load_scenario(path):
    if not path:
        raise ValueError("--scenario FILE.json is required for this task")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def _envelope(task, scenario, verdict, asking, agent, summary):
    first = (scenario or {}).get("option") or ((scenario or {}).get("options") or [{}])[0]
    return {
        "mode": "agent", "task": task,
        "town": (scenario or {}).get("town") or first.get("town"),
        "since": (scenario or {}).get("start_date"),
        "asking": asking, "verdict": verdict, "premium_pct": None,
        "trend": None, "location": None, "ura_context": None, "cea_verification": None,
        "agent": agent,
        "summary": rp.with_disclaimer(summary),
        "disclaimer": rp.DISCLAIMER,
        "policy_as_of": max(i["as_of"] for i in _policy()["items"].values()),
    }


_POLICY = None


def _policy():
    global _POLICY
    if _POLICY is None:
        _POLICY = ap.load_policy()
    return _POLICY


def _lowest_tco(comparison):
    best = min(comparison["options"], key=lambda o: Decimal(o["tco"]["10"]["total"]))
    return f"lowest 10-year cost of occupancy: {best['name']}"


def run_task(args):
    policy = _policy()
    if args.task == "profile":
        if not args.profile:
            raise ValueError("--profile is required (dink | first_home_couple | family_of_five)")
        p = pr.build_profile(args.profile, variant=args.variant, max_price=args.max_price)
        return _envelope("profile", None, None, None, {"profile": p}, rp.profile_summary(p))
    scenario = _load_scenario(args.scenario)
    if args.task == "plan":
        plan = cf.plan({k: v for k, v in scenario.items() if k != "options"}, policy)
        return _envelope("plan", scenario, plan["verdict"], plan["option"]["price"], {"plan": plan}, rp.plan_summary(plan))
    if args.task == "compare":
        c = cmp.compare(scenario, policy)
        return _envelope("compare", scenario, _lowest_tco(c), None, {"comparison": c}, rp.compare_summary(c))
    # advise
    profile_id = scenario.get("profile") or args.profile
    if not profile_id:
        raise ValueError("advise needs scenario.profile or --profile")
    p = pr.build_profile(profile_id, variant=scenario.get("variant") or args.variant, max_price=args.max_price)
    parts, agent = [rp.profile_summary(p)], {"profile": p}
    verdict, asking = None, None
    if len(scenario.get("options", [])) >= 2:
        c = cmp.compare(scenario, policy)
        agent["comparison"] = c
        parts += ["", "=== Your options compared ===", rp.compare_summary(c)]
        verdict = _lowest_tco(c)
    else:
        single = scenario.get("option") or scenario["options"][0]
        plan = cf.plan({**{k: v for k, v in scenario.items() if k != "options"}, "option": single}, policy)
        agent["plan"] = plan
        parts += ["", "=== Your cash flow ===", rp.plan_summary(plan)]
        verdict, asking = plan["verdict"], plan["option"]["price"]
    return _envelope("advise", scenario, verdict, asking, agent, "\n".join(parts))


def main(argv=None):
    ap_ = argparse.ArgumentParser(description="Singapore property-agent advisor (profiles, cash flow, comparison)")
    ap_.add_argument("--task", choices=TASKS, required=True)
    ap_.add_argument("--profile", help="dink | first_home_couple | family_of_five")
    ap_.add_argument("--variant", help="profile variant, e.g. multigen for family_of_five")
    ap_.add_argument("--scenario", help="scenario JSON (see references/agent-scenario.md)")
    ap_.add_argument("--max-price", help="annotate shortlist entries likely above this budget (SGD)")
    ap_.add_argument("--summary-only", action="store_true", help="print the plain-language summary instead of JSON")
    args = ap_.parse_args(argv)
    try:
        result = run_task(args)
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}" if isinstance(e, KeyError) else str(e)}))
        return 0
    print(result["summary"] if args.summary_only else json.dumps(result, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    sys.exit(main())
