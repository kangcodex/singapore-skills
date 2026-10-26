#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 advisor_cli.py --case ../assets/case-template.json
# Or: uv run advisor_cli.py --case case.json --format json
"""Audit/render a local case or run explicit, reproducible financial scenarios."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from advisor_calculations import CalculationError, cost_total, monthly_payment, price_premium
from advisor_case import Audit, audit_case
from advisor_records import CaseError, JSONValue, Record, parse_json, read_case, record, rows
from advisor_workflow import ASSESSORS, assess, evaluate_case


def cell(value: JSONValue) -> str:
    return str(value if value is not None else "unknown").replace("|", "\\|").replace("\n", " ")


def describe(value: JSONValue, depth: int = 0) -> list[str]:
    """Present record fields as readable nested bullets rather than JSON prose."""
    indent = "  " * depth
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            label = key.replace("_", " ").capitalize()
            if isinstance(item, (dict, list)):
                lines.append(f"{indent}- **{label}:**")
                lines.extend(describe(item, depth + 1))
            else:
                lines.append(f"{indent}- **{label}:** {cell(item)}")
        return lines
    if isinstance(value, list):
        return [line for item in value for line in describe(item, depth)] or [f"{indent}- None recorded."]
    return [f"{indent}- {cell(value)}"]


def render_report(case: Record, audit: Audit) -> str:
    """Render the same audited record; never invent recommendations or source facts."""
    brief = record(case["buyer_brief"], "buyer_brief")
    search = record(case["search_brief"], "search_brief")
    decision = "Prior summary is superseded pending reassessment. Use the recomputed checks below; the previous decision is not current advice." if case.get("summary_status") == "superseded_pending_reassessment" else str(case.get("summary") or "Research is incomplete; no purchase recommendation has been established.")
    lines = [f"# Housing decision: {cell(case['case_id'])}",
             f"Version {case['version']} | Research date: {case['research_date']}",
             "", "## Decision", decision,
             "", "## Household and assumptions", *describe(brief),
             "", "## Search coverage", str(search.get("coverage")),
             "", "## Candidate comparison", "| Home | Fit | Availability | Price basis |", "|---|---|---|---|"]
    for candidate in rows(case["candidates"], "candidates"):
        lines.append("| " + " | ".join(cell(candidate.get(key)) for key in ("id", "fit", "availability", "price")) + " |")
    for field, title in (("recommendations", "Conditional recommendations"), ("policy_assessments", "Policy and eligibility"), ("comparables", "Matched comparables"), ("cost_scenarios", "Costs and affordability"), ("history", "Changes and next actions")):
        lines.extend(["", f"## {title}"])
        entries = rows(case[field], field)
        if not entries:
            lines.append("Not established; further research or explicit assumptions are required.")
        for entry in entries:
            if entry.get("status") == "superseded_pending_reassessment":
                lines.append("Superseded recommendation — historical wording below is not current advice:")
            lines.extend(describe(entry))
    if case.get("assessment_results"):
        lines.extend(["", "## Computed question-led assessments", *describe(case["assessment_results"])])
    if case.get("change_summary"):
        lines.extend(["", "## Recomputed changes", *describe(case["change_summary"])])
    lines.extend(["", "## Source register", "| Claim | Kind / scope | Confidence | Source | Retrieved |", "|---|---|---|---|---|"])
    for claim in rows(case["evidence"], "evidence"):
        lines.append(f"| {cell(claim.get('id'))} | {cell(claim.get('kind'))} / {cell(claim.get('scope'))} | {cell(claim.get('confidence'))} | {cell(claim.get('source'))} | {cell(claim.get('retrieved_at'))} |")
    lines.extend(["", "## Evidence gaps and audit"])
    for warning in (*audit.errors, *audit.warnings):
        lines.append(f"- {warning}")
    for access in rows(case["source_access"], "source_access"):
        lines.append(f"- {cell(access.get('source'))}: {cell(access.get('status'))}; {cell(access.get('limitation'))}")
    lines.extend(["", "Audit checks record consistency, not independent source truth or professional approval."])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    task = parser.add_mutually_exclusive_group(required=True)
    task.add_argument("--case", type=Path)
    task.add_argument("--calculate", choices=("subtotal", "mortgage", "premium"))
    task.add_argument("--assess", choices=tuple(ASSESSORS))
    parser.add_argument("--input", type=Path, help="JSON input for a focused assessment; only this explicit file is read")
    parser.add_argument("--previous-case", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--components", help='JSON object of cost name to decimal string or null')
    parser.add_argument("--principal")
    parser.add_argument("--annual-rate")
    parser.add_argument("--years", type=int)
    parser.add_argument("--asking")
    parser.add_argument("--baseline")
    parser.add_argument("--asking-unit", choices=("total", "psf", "monthly", "psf_month", "land_psf", "built_psf"))
    parser.add_argument("--baseline-unit", choices=("total", "psf", "monthly", "psf_month", "land_psf", "built_psf"))
    parser.add_argument("--area-sqft")
    args = parser.parse_args(argv)
    if args.previous_case is not None and args.case is None:
        parser.error("--previous-case is only valid with --case")
    if args.input is not None and args.assess is None:
        parser.error("--input is only valid with --assess")
    try:
        if args.assess is not None:
            if args.input is None:
                parser.error("--assess requires --input FILE.json")
            result = assess(args.assess, read_case(args.input))
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            else:
                print(f"# {args.assess.replace('_', ' ').title()} assessment\n\n" + "\n".join(describe(result)))
            return 0
        if args.case is not None:
            case = read_case(args.case)
            previous = read_case(args.previous_case) if args.previous_case else None
            case = evaluate_case(case, previous)
            audit = audit_case(case, previous)
            if args.format == "json" or audit.errors:
                print(json.dumps({"case": case, "audit": asdict(audit)}, ensure_ascii=False, indent=2, allow_nan=False))
            else:
                print(render_report(case, audit), end="")
            return 2 if audit.errors else 0
        if args.calculate == "subtotal":
            raw = parse_json(args.components or "{}")
            components = record(raw, "components")
            costs: dict[str, str | None] = {}
            for name, value in components.items():
                if value is not None and not isinstance(value, str):
                    raise CaseError(name, "cost must be a decimal string or null")
                costs[name] = value
            print(json.dumps(cost_total(costs)))
        elif args.calculate == "mortgage":
            if args.principal is None or args.annual_rate is None or args.years is None:
                parser.error("mortgage requires --principal, --annual-rate and --years")
            print(json.dumps({"monthly_payment": str(monthly_payment(args.principal, args.annual_rate, args.years)), "currency": "SGD", "status": "scenario, not lender approval"}))
        else:
            if None in (args.asking, args.asking_unit, args.baseline, args.baseline_unit):
                parser.error("premium requires --asking, --asking-unit, --baseline and --baseline-unit")
            print(json.dumps({"premium_pct": str(price_premium(args.asking, args.asking_unit, args.baseline, args.baseline_unit, args.area_sqft)), "status": "arithmetic only; comparability must be established separately"}))
        return 0
    except (OSError, json.JSONDecodeError, CaseError, CalculationError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
