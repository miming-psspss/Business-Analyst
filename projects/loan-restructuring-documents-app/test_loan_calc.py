"""Run: python test_loan_calc.py   (plain asserts, no framework needed)"""
from datetime import date
from decimal import Decimal as D
import loan_calc as c

# T1/T2: acceptance check from the master document (2% per MONTH = 24% per annum, centavo rounding)
r = c.monthly_rate(24)
pay = c.installment(D("10000"), r, 12, "centavo")
assert pay == D("945.60"), pay
rows = c.schedule(D("10000"), r, 12, pay, date(2026, 12, 15), 15)
assert rows[-1]["payment"] == D("945.55") and rows[-1]["closing"] == D("0.00")
assert sum(x["interest"] for x in rows) == D("1347.15")

# T3/T4/T5: payment-first mode (24% per annum = 2% per month; cap set explicitly to 12 for this check)
from datetime import date as _d
rows = c.payment_plan(D("10000"), 24, D("946"), _d(2026, 12, 15), 15, max_months=12)
assert len(rows) == 12 and rows[-1]["closing"] == D("0.00")
assert c.min_payment(D("10000"), 24, max_months=12) == D("946")        # 945.60 rounds UP to a whole peso
for bad in (D("200"), D("200.01"), D("500")):
    try:
        c.check_payment(D("10000"), 24, bad, max_months=12); raise SystemExit(f"should refuse {bad}")
    except c.LoanError:
        pass

# T6: zero rate
assert c.installment(D("12000"), D(0), 12) == D("1000")

# Decision (revised): term follows the payment; longest term is a setting, default 36 months
assert c.CONFIG["max_months"] == 36
assert c.min_payment(D("100000"), 15) == D("3467")
for pay, months in ((D("3467"), 36), (D("5000"), 24), (D("9026"), 12), (D("20000"), 6)):
    rows = c.payment_plan(D("100000"), 15, pay, date(2026, 12, 15), 15)
    assert len(rows) == months and rows[-1]["closing"] == D("0.00"), (pay, len(rows))
    assert all(x["payment"] > 0 for x in rows)
for bad in (D("1250"), D("3466"), D("1000")):          # <= monthly interest, or too small for 36 months
    try:
        c.payment_plan(D("100000"), 15, bad, date(2026, 12, 15), 15); raise SystemExit(f"should refuse {bad}")
    except c.LoanError as e:
        assert "interest" in str(e) or "minimum" in str(e)
# the cap is adjustable: with a 24-month cap 3,467 is no longer enough
assert c.min_payment(D("100000"), 15, max_months=24) > D("3467")
try:
    c.payment_plan(D("100000"), 15, D("3467"), date(2026, 12, 15), 15, max_months=24); raise SystemExit("cap change ignored")
except c.LoanError:
    pass
# fixed-term mode still works for any term up to the cap, and refuses beyond it
assert c.term_mode(D("100000"), 15, 36) > c.min_payment(D("100000"), 15) - 2
try:
    c.term_mode(D("100000"), 15, 37); raise SystemExit("term above cap accepted")
except c.LoanError:
    pass

# Decision A1/A2: 15% per annum, whole-peso installment, residual in final installment
for P in (D("100000"), D("27500"), D("5000")):
    for n in (6, 12, 36):
        pay = c.term_mode(P, 15, n)
        assert pay == pay.to_integral_value()
        rows = c.schedule(P, c.monthly_rate(15), n, pay, date(2026, 12, 15), 15)
        assert rows[-1]["closing"] == D("0.00") and len(rows) == n
        assert abs(rows[-1]["payment"] - pay) < n + 1   # final within a few pesos of regular
print("100,000 @15%/yr: 12 mo ->", c.term_mode(D("100000"), 15, 12), "| 36 mo ->", c.term_mode(D("100000"), 15, 36), "| floor for 36 mo ->", c.min_payment(D("100000"), 15))

# T7: due day 31 never drifts
ds = [c.due_date(date(2027, 1, 31), 31, k) for k in range(3)]
assert ds == [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)], ds
assert c.due_date(date(2028, 1, 31), 31, 1) == date(2028, 2, 29)

# T15: 1,000 pseudo-random loans always close at exactly 0.00
import random
random.seed(7)
for _ in range(1000):
    P = D(random.randrange(1000, 100001, 50)); a = random.choice((12, 15, 18))
    pay = c.min_payment(P, a) + D(random.randrange(0, 3000, 10))      # any payment at or above the floor
    rows = c.payment_plan(P, a, pay, date(2026, 12, 31), 31)
    assert rows[-1]["closing"] == D("0.00") and len(rows) <= 36
    assert rows[-1]["payment"] > 0

print("DST estimate, 100,000, ~1 yr:", c.dst_estimate(D("100000"), date(2026, 11, 20), date(2027, 11, 15)))
print("all calculator tests passed")
