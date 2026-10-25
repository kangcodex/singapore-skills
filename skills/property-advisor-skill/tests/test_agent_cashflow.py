"""Cash-flow engine for the agent mode (no network, Decimal only)."""
import copy
import json
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_cashflow as cf  # noqa: E402
import agent_money as am  # noqa: E402
import agent_policy as ap  # noqa: E402

POLICY = ap.load_policy()


def _buyers(cpf="300000", income="6000", props=0, residency="sc", ages=(32, 30), loans=0):
    return [{"age": a, "residency": residency, "existing_properties": props,
              "outstanding_loans": loans, "monthly_income": income, "cpf_oa": str(D(cpf) / len(ages)),
             "cpf_oa_monthly": "1000"} for a in ages]


def _scn(category, price, loan_type="bank", tenure=30, cash="500000", **kw):
    s = {
        "start_date": "2026-11-01",
        "option": {"name": category, "category": category, "price": str(price),
                   "loan": {"type": loan_type, "tenure_years": tenure}},
        "buyers": kw.pop("buyers", _buyers()),
        "household": {"cash": cash, "other_monthly_debts": "0"},
    }
    s["option"].update(kw)
    return s


def _sum(events, field, pred=lambda e: True):
    return sum((D(e[field]) for e in events if pred(e)), D("0"))


class TestResaleHdb(unittest.TestCase):
    def setUp(self):
        s = _scn("resale_hdb", 600000, loan_type="hdb", tenure=25)
        self.res = cf.plan(s, POLICY)
        self.ev = self.res["timeline"]

    def test_option_and_exercise_follow_hdb_otp_terms(self):
        by = {e["stage"]: e for e in self.ev}
        self.assertEqual(D(by["option_fee"]["cash"]), D("1000"))
        self.assertEqual(D(by["exercise"]["cash"]), D("4000"))
        self.assertEqual(by["exercise"]["date"], "2026-11-22")

    def test_bsd_and_fees_are_cash_at_completion(self):
        by = {e["stage"]: e for e in self.ev}
        self.assertEqual(D(by["stamp_duty"]["cash"]), D("12600"))
        self.assertEqual(D(by["legal_and_other_fees"]["cash"]), D("2800"))

    def test_loan_is_ltv_of_price_and_rest_is_cpf(self):
        self.assertEqual(D(self.res["loan"]["amount"]), D("450000.00"))
        comp = next(e for e in self.ev if e["stage"] == "completion_down_payment")
        self.assertEqual(D(comp["cpf"]), D("145000.00"))
        self.assertEqual(D(comp["cash"]), D("0.00"))

    def test_down_payment_pieces_sum_to_price_minus_loan(self):
        down = _sum(self.ev, "cash", lambda e: e["kind"] == "down") + _sum(self.ev, "cpf", lambda e: e["kind"] == "down")
        self.assertEqual(down, D("150000.00"))

    def test_upfront_totals(self):
        up = self.res["upfront"]
        self.assertEqual(D(up["cash"]), D("20400.00"))
        self.assertEqual(D(up["cpf"]), D("145000.00"))

    def test_instalment_uses_hdb_loan_rate(self):
        exp = am.monthly_payment(D("450000"), D("0.026"), 25)
        self.assertEqual(D(self.res["loan"]["monthly_instalment"]), exp)

    def test_cpf_pays_instalment_first(self):
        first = next(r for r in self.res["monthly_schedule"] if r["payment_type"] == "instalment")
        self.assertEqual(D(first["cpf_paid"]) + D(first["cash_paid"]), D(first["instalment"]))
        self.assertGreater(D(first["cpf_paid"]), D("0"))

    def test_msr_applies_and_is_checked(self):
        names = {c["name"] for c in self.res["checks"]}
        self.assertIn("MSR", names)
        self.assertNotIn("TDSR", names)  # HDB loan is MSR-governed

    def test_json_serialisable_with_no_floats(self):
        json.dumps(self.res)  # raises TypeError on Decimal/float leakage

        def walk(o):
            if isinstance(o, float):
                self.fail("float in output")
            if isinstance(o, dict):
                [walk(v) for v in o.values()]
            if isinstance(o, list):
                [walk(v) for v in o]
        walk(self.res)


class TestResaleCondo(unittest.TestCase):
    def test_bank_loan_minimum_cash_is_five_percent(self):
        res = cf.plan(_scn("resale_condo", 1500000), POLICY)
        self.assertEqual(D(res["loan"]["amount"]), D("1125000.00"))
        self.assertEqual(res["loan"]["ltv"], "0.75")
        down_cash = _sum(res["timeline"], "cash", lambda e: e["kind"] == "down")
        self.assertGreaterEqual(down_cash, D("75000"))
        by = {e["stage"]: e for e in res["timeline"]}
        self.assertEqual(D(by["option_fee"]["cash"]), D("15000.00"))
        self.assertEqual(D(by["stamp_duty"]["cash"]), D("44600"))

    def test_limited_cpf_pushes_balance_to_cash(self):
        res = cf.plan(_scn("resale_condo", 1500000, buyers=_buyers(cpf="100000")), POLICY)
        down_cpf = _sum(res["timeline"], "cpf", lambda e: e["kind"] == "down")
        down_cash = _sum(res["timeline"], "cash", lambda e: e["kind"] == "down")
        self.assertLessEqual(down_cpf, D("100000") + D("2") * D("1000") * 3)  # pool + a few months' inflow
        self.assertEqual(down_cpf + down_cash, D("375000.00"))

    def test_existing_property_triggers_absd_in_cash(self):
        res = cf.plan(_scn("resale_condo", 1500000, buyers=_buyers(props=1, loans=1)), POLICY)
        by = {e["stage"]: e for e in res["timeline"]}
        self.assertEqual(D(by["absd"]["cash"]), D("300000"))
        self.assertEqual(D(by["absd"]["cpf"]), D("0"))
        self.assertEqual(res["loan"]["ltv"], "0.45")  # one outstanding loan

    def test_long_tenure_drops_to_lower_ltv(self):
        res = cf.plan(_scn("resale_condo", 1500000, tenure=35), POLICY)
        self.assertEqual(res["loan"]["ltv"], "0.55")

    def test_tenure_beyond_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            cf.plan(_scn("resale_condo", 1500000, tenure=36), POLICY)

    def test_tdsr_stress_uses_floor_and_can_fail(self):
        poor = _scn("resale_condo", 1500000, buyers=_buyers(income="3000"))
        res = cf.plan(poor, POLICY)
        tdsr = next(c for c in res["checks"] if c["name"] == "TDSR")
        self.assertFalse(tdsr["pass"])
        self.assertEqual(tdsr["stress_rate"], "0.04")
        self.assertEqual(res["verdict"], "not affordable")


class TestNewLaunch(unittest.TestCase):
    def setUp(self):
        self.res = cf.plan(_scn("new_launch_condo", 1500000), POLICY)
        self.ev = self.res["timeline"]
        self.stages = [e for e in self.ev if e["kind"] in ("down", "stage")]

    def test_progressive_stage_totals_equal_price(self):
        total = sum((D(e["stage_amount"]) for e in self.stages), D("0"))
        self.assertEqual(total, D("1500000.00"))

    def test_booking_is_five_percent_cash(self):
        booking = next(e for e in self.ev if e["stage"] == "booking")
        self.assertEqual(D(booking["cash"]), D("75000.00"))
        self.assertEqual(D(booking["cpf"]), D("0.00"))

    def test_cash_plus_cpf_plus_loan_equals_price(self):
        cash = _sum(self.stages, "cash")
        cpf = _sum(self.stages, "cpf")
        loan = _sum(self.stages, "loan_drawn")
        self.assertEqual(cash + cpf + loan, D("1500000.00"))
        self.assertEqual(loan, D(self.res["loan"]["amount"]))

    def test_stamp_duty_due_at_sp_signing(self):
        sd = next(e for e in self.ev if e["stage"] == "stamp_duty")
        sp = next(e for e in self.ev if e["stage"] == "sp_signing")
        self.assertEqual(sd["date"], sp["date"])

    def test_interest_only_during_construction_then_full_instalment(self):
        sched = self.res["monthly_schedule_full"]
        csc = next(e for e in self.ev if e["stage"] == "csc")["month"]
        during = next(r for r in sched if r["month"] == csc - 1)
        after = next(r for r in sched if r["month"] == csc + 1)
        self.assertEqual(during["payment_type"], "interest_only")
        self.assertEqual(after["payment_type"], "instalment")
        self.assertGreater(D(after["instalment"]), D(during["instalment"]))

    def test_move_in_after_top_not_before(self):
        top = next(e for e in self.ev if e["stage"] == "top")["month"]
        self.assertGreater(self.res["move_in_month"], top)


class TestScenariosAndCumulative(unittest.TestCase):
    def setUp(self):
        self.res = cf.plan(_scn("resale_condo", 1500000), POLICY)

    def test_interest_scenarios_are_ordered_and_labelled_assumptions(self):
        sc = self.res["scenarios"]["interest"]
        low, base, high = (D(sc[k]["monthly_instalment"]) for k in ("low", "base", "high"))
        self.assertLess(low, base)
        self.assertLess(base, high)
        self.assertEqual(self.res["scenarios"]["status"], "assumption")

    def test_appreciation_scenarios_order_equity(self):
        sc = self.res["scenarios"]["appreciation"]
        eq = [D(sc[k]["horizon"]["10"]["equity_value"]) for k in ("low", "base", "high")]
        self.assertLess(eq[0], eq[1])
        self.assertLess(eq[1], eq[2])

    def test_user_override_of_rate_changes_instalment(self):
        s = _scn("resale_condo", 1500000)
        s["assumptions"] = {"interest_rate": {"base": "0.05"}}
        res = cf.plan(s, POLICY)
        self.assertEqual(D(res["loan"]["monthly_instalment"]),
                         am.monthly_payment(D("1125000"), D("0.05"), 30))

    def test_cumulative_costs_split_cash_and_cpf_and_grow(self):
        hz = self.res["horizon"]
        self.assertEqual(set(hz), {"1", "5", "10", "15"})
        totals = [D(hz[y]["cash"]) + D(hz[y]["cpf"]) for y in ("1", "5", "10", "15")]
        self.assertEqual(totals, sorted(totals))
        self.assertGreater(D(hz["5"]["cpf"]), D("0"))

    def test_cash_and_cpf_never_exceed_rules(self):
        # CPF used for the property never exceeds the valuation limit (= price here)
        hz = self.res["horizon"]["15"]
        self.assertLessEqual(D(hz["cpf_used_for_property"]), D("1500000"))

    def test_equity_built_is_principal_repaid_plus_appreciation(self):
        h = self.res["horizon"]["5"]
        value = D(h["property_value"])
        self.assertEqual(D(h["equity_built"]),
                         (value - D("1500000") + D(h["principal_repaid"])).quantize(D("0.01")))

    def test_month_by_month_schedule_has_36_rows(self):
        self.assertEqual(len(self.res["monthly_schedule"]), 36)
        row = self.res["monthly_schedule"][0]
        for key in ("month", "date", "instalment", "cpf_paid", "cash_paid", "maintenance",
                    "property_tax", "insurance", "total_commitment", "total_cash_outflow"):
            self.assertIn(key, row)


class TestGrantsAndAffordability(unittest.TestCase):
    def test_first_timer_ehg_credits_cpf_and_cuts_cash(self):
        base = _scn("resale_hdb", 600000, loan_type="hdb", tenure=25,
                    buyers=_buyers(cpf="40000", income="3500"))  # household income 7,000
        with_grant = copy.deepcopy(base)
        with_grant["option"]["first_timer"] = True
        r0, r1 = cf.plan(base, POLICY), cf.plan(with_grant, POLICY)
        self.assertEqual(D(r1["grants"]["ehg"]), D("30000"))  # 6,501-7,000 band
        self.assertLess(D(r1["upfront"]["cash"]), D(r0["upfront"]["cash"]))

    def test_grant_denied_above_ceiling(self):
        s = _scn("resale_hdb", 600000, loan_type="hdb", tenure=25,
                 buyers=_buyers(income="9000"), first_timer=True)
        res = cf.plan(s, POLICY)
        self.assertEqual(D(res["grants"]["ehg"]), D("0"))
        self.assertTrue(any("income" in n for n in res["grants"]["notes"]))

    def test_max_affordable_price_inverts_tdsr(self):
        mp = cf.max_affordable(_scn("resale_condo", 1500000), POLICY)
        self.assertGreater(D(mp["max_loan"]), D("0"))
        self.assertGreater(D(mp["max_price"]), D(mp["max_loan"]))
        # stressed instalment at max loan must sit at/below TDSR room
        pmt = am.monthly_payment(D(mp["max_loan"]), D("0.04"), 30)
        self.assertLessEqual(pmt, D(mp["monthly_instalment_room"]))

    def test_cash_gap_flagged_when_cash_short(self):
        res = cf.plan(_scn("resale_condo", 1500000, cash="10000"), POLICY)
        self.assertGreater(D(res["cash_check"]["gap"]), D("0"))
        self.assertEqual(res["verdict"], "not affordable")

    def test_unverified_inputs_are_reported(self):
        res = cf.plan(_scn("resale_hdb", 600000, loan_type="hdb", tenure=25), POLICY)
        names = {n["item"] for n in res["unverified_assumptions"]}
        self.assertIn("hdb_loan", names)


if __name__ == "__main__":
    unittest.main()
