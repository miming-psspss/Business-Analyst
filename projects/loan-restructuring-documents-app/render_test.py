"""Render the templates with SYNTHETIC data and check the output.

Usage:  python render_test.py [en|ceb] [NEW|EXISTING] [PAYMENT]   (defaults: en NEW 5000)
Output: ./rendered_<lang>_<path>/*.docx
All names and figures are fake. Tunable lender decisions are the constants below.
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from docx import Document
from docxtpl import DocxTemplate

import loan_calc as c
import rules_text as rt

# ---- lender decisions (proposed values; confirm with the lawyer) ----
ANNUAL_RATE = Decimal("15")      # percent per annum  (decision A1)
LATE_PENALTY_PCT = "2"           # % of the overdue installment per month, in addition to interest (proposal)
GRACE_DAYS = 3                   # proposal
DEFAULT_DAYS, NOTICE_DAYS = 30, 7  # proposal for the default clause
DRAFT_BANNER = {"en": "DRAFT \u2014 NOT LEGALLY REVIEWED", "ceb": "DRAFT \u2014 WALA PA NAREVIEW SA ABOGADO"}  # set to "" after approval


def build_context(lang="en", path="NEW", principal="100000.00", payment="5000"):
    """Payment-first: the lender enters what the borrower can pay monthly; the term follows (cap: loan_config.json)."""
    P, pay = Decimal(principal), Decimal(payment)
    r = c.monthly_rate(ANNUAL_RATE)
    signing, first, due_day = date(2026, 11, 20), date(2026, 12, 15), 15
    rows = c.payment_plan(P, ANNUAL_RATE, pay, first, due_day)
    tot_i = sum(x["interest"] for x in rows); tot_p = sum(x["principal"] for x in rows); tot_pay = sum(x["payment"] for x in rows)
    f = lambda d: rt.fmt_date(d, lang)
    en = lang == "en"
    ctx = dict(
        draft_banner=DRAFT_BANNER[lang], loan_ref="L-0001", version_no=1, path=path,
        with_promissory_note=True, with_loan_agreement=True,
        agreement_title=("LOAN AGREEMENT" if path == "NEW" else "LOAN RESTRUCTURING AGREEMENT") if en
        else ("KASUNDUAN SA UTANG" if path == "NEW" else "KASUNDUAN SA PAG-USAB SA UTANG"),
        doc_date=f(signing), disclosure_date=f(date(2026, 11, 18)), disbursement_date=f(signing), place_of_signing="Candijay, Bohol",
        lender_name="JUAN D. SAMPLE", lender_citizenship="Filipino" if en else "Pilipino", lender_civil_status="married" if en else "minyo",
        lender_address="Sample St., Sample Barangay, Candijay, Bohol",
        borrower_name="MARIA S. EXAMPLE", borrower_citizenship="Filipino" if en else "Pilipino", borrower_civil_status="single" if en else "dili pa minyo",
        borrower_address="Example St., Example Barangay, Candijay, Bohol", witness1_name="WITNESS ONE", witness2_name="WITNESS TWO",
        as_of_date=f(date(2026, 11, 15)), opening_balance=rt.php(P), adjustment_fmt=rt.php(0), arrears_fmt=rt.php(0),
        prior_arrangement_text=("monthly interest only, with no payment of principal and no written schedule" if en
                                else "interes lang matag bulan, walay bayad sa prinsipal ug walay sinulat nga talaan"),
        principal=rt.php(P), principal_words=rt.peso_words(P, lang), amount_financed=rt.php(P),
        annual_rate=f"{ANNUAL_RATE:.2f}", monthly_rate=f"{r * 100:.2f}", simple_annual=f"{ANNUAL_RATE:.2f}",
        effective_annual=f"{((1 + r) ** 12 - 1) * 100:.2f}", term_months=len(rows), payment=rt.php(pay), final_payment=rt.php(rows[-1]["payment"]),
        due_day=due_day, first_due_date=f(rows[0]["due"]), last_due_date=f(rows[-1]["due"]),
        finance_charge=rt.php(tot_i), total_interest=rt.php(tot_i), total_payable=rt.php(tot_pay),
        total_interest_plain=rt.money(tot_i), total_principal_plain=rt.money(tot_p), total_payable_plain=rt.money(tot_pay),
        other_charges_text="None." if en else "Wala.",
        dst_estimate=rt.php(c.dst_estimate(P, signing, rows[-1]["due"])) + (" (estimate; confirm with a lawyer or the BIR)" if en else " (banabana lang; kumpirmahon sa abogado o sa BIR)"),
        dst_payer="the Lender" if en else "ang Nagpautang",
        default_days=DEFAULT_DAYS, notice_days=NOTICE_DAYS, ack_document_title="Loan Agreement and Promissory Note",
        schedule=[dict(seq=x["seq"], due_date=rt.fmt_date(x["due"], lang, short=True), opening=rt.money(x["opening"]), interest=rt.money(x["interest"]),
                       principal=rt.money(x["principal"]), payment=rt.money(x["payment"]), closing=rt.money(x["closing"])) for x in rows],
    )
    ctx.update(rt.rules(lang, ctx["annual_rate"], ctx["monthly_rate"], due_day, GRACE_DAYS, LATE_PENALTY_PCT))
    return ctx, rows


def check(path, ctx, name):
    d = Document(str(path))
    body = [p.text for p in d.paragraphs]
    cells = [p.text for tb in d.tables for r in tb.rows for cl in r.cells for p in cl.paragraphs]
    full = "\n".join(body + cells)
    assert "{{" not in full and "{%" not in full, f"{name}: leftover template tag"
    empty = [x for x in body if x.strip().rstrip(".").isdigit()]
    assert not empty, f"{name}: numbered clause with no text: {empty}"
    uses = {"01": [k for k in ctx if k.startswith("rule_") and k != "rule_records"] + ["late_charge_text"],
            "02": ["rule_interest_method", "rule_rounding", "rule_short_month", "rule_application", "rule_records"],
            "03": [k for k in ctx if k.startswith("rule_")] + ["late_charge_text"],
            "04": [k for k in ctx if k.startswith("rule_")] + ["late_charge_text"]}.get(name[:2], [])
    for k in uses:
        assert ctx[k] in full, f"{name}: missing {k}"
    for k in ("payment", "total_payable"):
        if name[:2] in ("01", "03"):
            assert ctx[k] in full, f"{name}: missing {k}"


if __name__ == "__main__":
    lang = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()
    path = (sys.argv[2] if len(sys.argv) > 2 else "NEW").upper()
    pay = sys.argv[3] if len(sys.argv) > 3 else "5000"
    ctx, rows = build_context(lang, path, payment=pay)
    assert rows[-1]["closing"] == Decimal("0.00")
    print(f"[{lang}/{path}] {ctx['principal']} at {ctx['annual_rate']}% p.a., payment {ctx['payment']} -> {ctx['term_months']} installments, final {ctx['final_payment']}, interest {ctx['total_interest']}")
    here = Path(__file__).parent
    out = here / f"rendered_{lang}_{path.lower()}"; out.mkdir(exist_ok=True)
    for t in sorted((here / "templates" / lang).glob("0*.docx")):
        doc = DocxTemplate(str(t)); doc.render(ctx, autoescape=True); doc.save(str(out / t.name))
        check(out / t.name, ctx, t.name); print("  ok", t.name)
