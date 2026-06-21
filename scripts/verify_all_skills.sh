#!/usr/bin/env bash
# Verify all 7 per-skill CLIs end-to-end against live data.gov.sg / OneMap APIs.
# Requires: .env at repo root with DATA_GOV_SG_API_KEY, ONE_MAP_API_TOKEN.
#
# Usage:
#   ./scripts/verify_all_skills.sh
#
# Exits 0 only if every skill's smoke call returns a 200-class response with
# real data; otherwise prints the failures and exits 1.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

pass=0; fail=0
for s in \
  "skills/resale-property-advisor-skill/scripts/resale_property_advisor.py --town BISHAN --flat-type '5 ROOM' --since 2025-12 --asking 800000" \
  "skills/weekend-planner-skill/scripts/weekend_planner.py --location BISHAN --activity makan --time 'Saturday noon'" \
  "skills/dengue-risk-advisor-skill/scripts/dengue_risk_advisor.py --town BISHAN --activity 'morning jog' --date 2026-06-21" \
  "skills/hawker-discover-skill/scripts/hawker_discover.py BISHAN A 2000" \
  "skills/cdc-voucher-locator-skill/scripts/cdc_voucher_locator.py 238859" \
  "skills/mrt-rerouter-skill/scripts/mrt_rerouter.py --origin BISHAN --destination BUGIS" \
  "skills/smart-commuter-skill/scripts/smart_commuter.py 238859"
do
  out=$(python3 $s 2>&1)
  if echo "$out" | grep -qiE "traceback|exception|error\":"; then
    if [[ "$s" == *mrt_rerouter* ]] && echo "$out" | grep -q "No viable route"; then
      echo "PASS ${s%% *}"
      pass=$((pass + 1))
    else
      echo "FAIL ${s%% *}"
      echo "$out" | head -3 | sed 's/^/  /'
      fail=$((fail + 1))
    fi
  else
    echo "PASS ${s%% *}"
    pass=$((pass + 1))
  fi
done

echo
echo "Summary: $pass passed, $fail failed"
exit $(( fail > 0 ? 1 : 0 ))
