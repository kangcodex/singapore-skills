#!/usr/bin/env python3
"""Eval grader for sg-home-chef-skill.

Mirrors overseas-trip-planner-skill/evals/grade.py pattern.

For each eval in evals.json:
  1. Build the script command from the eval's expected params
  2. Run the script (--json), capture JSON output
  3. Match the report against the eval's `expectations` list (substring checks)
  4. Print per-eval pass/fail + write benchmark.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WS = Path("/tmp/sghc-eval-workspace/iteration-1")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sg_home_chef.py"


def _read_script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _run_script(args: list[str]) -> dict:
    """Run the script with --json and the provided args, return parsed JSON."""
    cmd = [sys.executable, str(SCRIPT), *args, "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode not in (0, 2):
        return {"_error": res.stderr or res.stdout, "_returncode": res.returncode}
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        return {"_error": f"JSON decode error: {e}", "_raw": res.stdout}


def _normalize_check(check: str) -> tuple[str, str]:
    """Split a check like 'a == b' or 'a is true' or 'a >= 30' or 'a contains X' or 'a does NOT contain Y' into (lhs, op, rhs)."""
    check = check.strip()
    if " == " in check:
        lhs, rhs = check.split(" == ", 1)
        return lhs.strip(), "eq", rhs.strip()
    if " != " in check:
        lhs, rhs = check.split(" != ", 1)
        return lhs.strip(), "neq", rhs.strip()
    if " >= " in check:
        lhs, rhs = check.split(" >= ", 1)
        return lhs.strip(), "gte", rhs.strip()
    if " <= " in check:
        lhs, rhs = check.split(" <= ", 1)
        return lhs.strip(), "lte", rhs.strip()
    if " does NOT contain " in check:
        lhs, rhs = check.split(" does NOT contain ", 1)
        return lhs.strip(), "does_not_contain", rhs.strip()
    if " contains " in check:
        lhs, rhs = check.split(" contains ", 1)
        return lhs.strip(), "contains", rhs.strip()
    if " is true" in check:
        return check.replace(" is true", "").strip(), "is_true", ""
    if " is false" in check:
        return check.replace(" is false", "").strip(), "is_false", ""
    return check, "raw", ""


def _resolve(report: dict, lhs: str):
    """Resolve a dotted path like 'skill_strategy.level' or 'milestones.length' against the report.

    Supports `.length` suffix to return len() of a list/dict.
    """
    # Pull off optional .length suffix
    length_suffix = False
    if lhs.endswith(".length"):
        lhs = lhs[: -len(".length")]
        length_suffix = True

    parts = lhs.split(".")
    cur = report
    for p in parts:
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        else:
            return None

    if length_suffix:
        if cur is None:
            return 0
        try:
            return len(cur)
        except TypeError:
            return 0
    return cur


def _check_expectation(report: dict, expectation: str) -> tuple[bool, str]:
    """Match one expectation against the report. Return (passed, evidence)."""
    lhs, op, rhs = _normalize_check(expectation)
    actual = _resolve(report, lhs)

    if op == "is_true":
        if actual is True:
            return True, f"{lhs} == True"
        return False, f"{lhs} == {actual!r} (expected True)"
    if op == "is_false":
        if actual is False:
            return True, f"{lhs} == False"
        return False, f"{lhs} == {actual!r} (expected False)"
    if op == "eq":
        if isinstance(actual, (int, float)) or (isinstance(rhs, str) and rhs.lstrip("-").isdigit()):
            try:
                return (int(actual) == int(rhs), f"{lhs} == {actual!r} (expected {rhs})")
            except (TypeError, ValueError):
                pass
        return (str(actual).strip().lower() == rhs.strip().lower(), f"{lhs} == {actual!r} (expected {rhs})")
    if op == "neq":
        return (str(actual).strip().lower() != rhs.strip().lower(), f"{lhs} == {actual!r} (must not be {rhs})")
    if op == "gte":
        try:
            return (float(actual) >= float(rhs), f"{lhs} == {actual!r} (>= {rhs})")
        except (TypeError, ValueError):
            return (False, f"cannot compare {actual!r} >= {rhs}")
    if op == "lte":
        try:
            return (float(actual) <= float(rhs), f"{lhs} == {actual!r} (<= {rhs})")
        except (TypeError, ValueError):
            return (False, f"cannot compare {actual!r} <= {rhs}")
    if op == "contains":
        if isinstance(actual, list):
            try:
                if actual and isinstance(actual[0], dict) and rhs in actual[0]:
                    keys = [item.get(rhs) for item in actual if isinstance(item, dict)]
                    if any(k for k in keys):
                        present = [str(k) for k in keys if k is not None]
                        return (True, f"list[{len(actual)}] has '{rhs}' field: {present[:5]}")
            except (IndexError, TypeError):
                pass
            haystack = " | ".join(str(x) for x in actual)
        else:
            haystack = str(actual) if actual is not None else ""
        if " or " in rhs:
            alts = [a.strip() for a in rhs.split(" or ")]
            present = [a for a in alts if a.lower() in haystack.lower()]
            return (bool(present), f"any of {alts}: {present}")
        if " and " in rhs:
            required = [a.strip() for a in rhs.split(" and ")]
            missing = [a for a in required if a.lower() not in haystack.lower()]
            return (not missing, f"all of {required}: missing {missing}")
        return (rhs.lower() in haystack.lower(), f"'{rhs}' in '{haystack[:80]}'")
    if op == "does_not_contain":
        if isinstance(actual, list):
            try:
                if actual and isinstance(actual[0], dict) and rhs in actual[0]:
                    keys = [item.get(rhs) for item in actual if isinstance(item, dict)]
                    present = [k for k in keys if k is not None]
                    return (not present, f"list[{len(actual)}] should NOT have '{rhs}': {present[:5]}")
            except (IndexError, TypeError):
                pass
            haystack = " | ".join(str(x) for x in actual)
        else:
            haystack = str(actual) if actual is not None else ""
        return (rhs.lower() not in haystack.lower(), f"'{rhs}' must not be in haystack")
    return (False, f"unparsed: {expectation}")


def _count_sections(blueprint) -> int:
    """Count section markers in the recipe_blueprint text. Looks for ## 1., ## 2., etc."""
    if not isinstance(blueprint, str):
        return 0
    return len(re.findall(r"^##\s+\d+\.", blueprint, flags=re.MULTILINE))


def grade_eval(eval_id: int, eval_def: dict, report: dict) -> dict:
    expectations = eval_def.get("expectations", [])
    results = []
    for exp in expectations:
        ok, evidence = _check_expectation(report, exp)
        results.append({"expectation": exp, "passed": ok, "evidence": evidence})
    return {
        "eval_id": eval_id,
        "eval_name": eval_def["eval_name"],
        "passed": sum(1 for r in results if r["passed"]),
        "total": len(results),
        "pass_rate": sum(1 for r in results if r["passed"]) / max(1, len(results)),
        "results": results,
    }


def _eval_params(eval_id: int) -> list[str]:
    """Map eval_id to the script args."""
    if eval_id == 1:
        return ["--dish", "Sambal Kang Kong", "--skill-level", "beginner",
                "--sourcing-track", "supermarket", "--servings", "2",
                "--time-budget", "30", "--dietary", "halal"]
    if eval_id == 2:
        return ["--dish", "Hainanese Chicken Rice", "--skill-level", "intermediate",
                "--sourcing-track", "wet-market", "--servings", "4",
                "--time-budget", "60", "--dietary", "none"]
    if eval_id == 3:
        return ["--dish", "Roti Prata", "--skill-level", "advanced",
                "--sourcing-track", "wet-market", "--servings", "4",
                "--time-budget", "240", "--dietary", "vegetarian"]
    return []


def main() -> int:
    evals_path = Path(__file__).resolve().parent / "evals.json"
    evals_doc = json.loads(evals_path.read_text(encoding="utf-8"))

    WS.mkdir(parents=True, exist_ok=True)
    benchmark = {"iteration": "iteration-1", "skill": "sg-home-chef-skill", "evals": []}

    for eval_def in evals_doc["evals"]:
        eval_id = eval_def["id"]
        params = _eval_params(eval_id)
        out_dir = WS / f"eval-{eval_id - 1}" / "with_skill"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "script_output.json"

        report = _run_script(params)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        result = grade_eval(eval_id, eval_def, report)
        benchmark["evals"].append(result)

        verdict = "PASS" if result["passed"] == result["total"] else "FAIL"
        print(f"  eval-{eval_id - 1} [{eval_def['eval_name']}]: "
              f"{result['passed']}/{result['total']} ({result['pass_rate']:.0%}) [{verdict}]")
        for r in result["results"]:
            if not r["passed"]:
                print(f"      FAIL: {r['expectation']}")
                print(f"            {r['evidence']}")

    bench_path = WS / "benchmark.json"
    bench_path.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    total_pass = sum(e["passed"] for e in benchmark["evals"])
    total_n = sum(e["total"] for e in benchmark["evals"])
    print(f"\nTotal: {total_pass}/{total_n} expectations passed ({total_pass / max(1, total_n):.0%})")
    print(f"Wrote {bench_path}")
    return 0 if total_pass == total_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
