"""Loan calculator (milestone M1 seed). Decimal only, no floats in money math.

Decisions applied (Oct 26, 2026):
  - Rate is quoted per ANNUM; monthly rate = annual / 12 (simple).          [A1]
  - Installment is rounded to the WHOLE PESO, 50 centavos and up rounds up.  [A2]
  - Interest per period is rounded half-up to the centavo; the final
    installment = remaining balance + that period's interest.
  - PAYMENT-FIRST (revised Oct 26, 2026): the lender enters what the borrower can
    pay each month; the term follows from it. The longest term is a SETTING
    (loan_config.json, "max_months", default 36 = three years). A payment too
    small to finish within that cap is refused, and the minimum is shown.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, getcontext
import json
from pathlib import Path

getcontext().prec = 28
CENTAVO = Decimal("0.01")
PESO = Decimal("1")

# ---- adjustable settings: edit loan_config.json next to this file ----
DEFAULT_CONFIG = {"max_months": 36, "installment_rounding": "peso"}


def load_config(path=None):
    cfg = dict(DEFAULT_CONFIG)
    p = Path(path) if path else Path(__file__).with_name("loan_config.json")
    if p.exists():
        cfg.update(json.loads(p.read_text()))
    if int(cfg["max_months"]) < 1:
        raise ValueError("max_months must be at least 1")
    return cfg


CONFIG = load_config()


class LoanError(ValueError):
    pass


def to_centavo(x):
    return Decimal(x).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def to_peso(x):
    return Decimal(x).quantize(PESO, rounding=ROUND_HALF_UP)


def monthly_rate(annual_pct):
    """15 (percent per year) -> Decimal('0.0125')."""
    return Decimal(annual_pct) / Decimal(1200)


def exact_payment(P, r, n):
    P = Decimal(P)
    if r == 0:
        return P / n
    return P * r / (1 - (1 + r) ** -n)


def installment(P, r, n, round_to="peso"):
    """Term mode. round_to: 'peso' (loan default) or 'centavo' (used by the acceptance check)."""
    if n < 1:
        raise LoanError("term must be at least 1 month")
    raw = exact_payment(P, r, n)
    pay = to_peso(raw) if round_to == "peso" else to_centavo(raw)
    if pay <= to_centavo(Decimal(P) * r):
        raise LoanError("installment does not exceed one month's interest")
    return pay


def term_mode(P, annual_pct, term, round_to=None, max_months=None):
    """Lender fixes a term (1..max_months); the app proposes the installment."""
    cap = max_months or CONFIG["max_months"]
    if not 1 <= term <= cap:
        raise LoanError(f"term must be between 1 and {cap} months")
    return installment(P, monthly_rate(annual_pct), term, round_to or CONFIG["installment_rounding"])


def min_payment(P, annual_pct, max_months=None):
    """Smallest whole-peso installment that clears the loan within max_months (rounded UP,
    so that a payment at or above it can never run past the cap)."""
    cap = max_months or CONFIG["max_months"]
    raw = exact_payment(P, monthly_rate(annual_pct), cap)
    return Decimal(raw).quantize(PESO, rounding=ROUND_CEILING)


def check_payment(P, annual_pct, payment, max_months=None):
    """Payment-first rule: refuse a payment that cannot finish the loan within the cap."""
    cap = max_months or CONFIG["max_months"]
    P, payment, r = Decimal(P), Decimal(payment), monthly_rate(annual_pct)
    interest1 = to_centavo(P * r)
    if payment <= interest1:
        raise LoanError(f"payment {payment} does not exceed one month's interest {interest1}; the principal would never fall")
    floor = min_payment(P, annual_pct, cap)
    if payment < floor:
        raise LoanError(f"payment {payment} is too small to finish within {cap} months; the minimum is {floor}")
    return floor


def payment_plan(P, annual_pct, payment, first, due_day, max_months=None):
    """Payment mode: returns the schedule for the lender-entered installment (term follows)."""
    cap = max_months or CONFIG["max_months"]
    check_payment(P, annual_pct, payment, cap)
    return schedule(P, monthly_rate(annual_pct), cap, Decimal(payment), first, due_day)


def affordability(P, annual_pct, payments, first=date(2027, 1, 15), due_day=15, max_months=None):
    """Side-by-side view for the first screen: what each candidate monthly payment means."""
    out = []
    for pay in payments:
        try:
            rows = payment_plan(P, annual_pct, pay, first, due_day, max_months)
            out.append(dict(payment=Decimal(pay), months=len(rows), total_interest=sum(x["interest"] for x in rows),
                            final=rows[-1]["payment"], ok=True, note=""))
        except LoanError as e:
            out.append(dict(payment=Decimal(pay), months=None, total_interest=None, final=None, ok=False, note=str(e)))
    return out


def due_date(first, due_day, k):
    """Rules S1/S2: month counted from the first due month; day clamped to month length."""
    m = first.month - 1 + k
    y, mo = first.year + m // 12, m % 12 + 1
    return date(y, mo, min(due_day, monthrange(y, mo)[1]))


def schedule(P, r, n, payment, first, due_day):
    bal, rows = to_centavo(P), []
    for k in range(1, n + 1):
        interest = to_centavo(bal * r)
        pay = payment if k < n else bal + interest
        if k < n and pay >= bal + interest:      # payment finishes the loan early
            pay = bal + interest
            rows.append(_row(k, first, due_day, bal, interest, pay))
            break
        rows.append(_row(k, first, due_day, bal, interest, pay))
        bal = rows[-1]["closing"]
    return rows


def _row(k, first, due_day, bal, interest, pay):
    principal = pay - interest
    return dict(seq=k, due=due_date(first, due_day, k - 1), opening=bal, interest=interest,
                principal=principal, payment=pay, closing=bal - principal)


def dst_estimate(P, signing_date, last_due_date):
    """ESTIMATE ONLY: PHP 1.50 per PHP 200 (or fraction) of face value; prorated by days/365 when the
    term is under one year (per the rules retrieved Oct 25, 2026). Confirm with a lawyer or the BIR."""
    units = (Decimal(P) / 200).to_integral_value(rounding=ROUND_CEILING)
    tax = units * Decimal("1.50")
    days = (last_due_date - signing_date).days
    if days < 365:
        tax = tax * Decimal(days) / Decimal(365)
    return to_centavo(tax)
