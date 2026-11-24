"""Turns form inputs + settings into (a) a validated loan plan and (b) the docxtpl context and documents.
No GUI code here, so it can be tested without a display."""
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from docx import Document
from docxtpl import DocxTemplate

import loan_calc as c
import rules_text as rt

HERE = Path(__file__).parent
DOCS = {  # key -> template file name
    "disclosure": "01_disclosure_statement.docx",
    "schedule": "02_amortization_schedule_annex_a.docx",
    "agreement": "03_loan_agreement.docx",
    "note": "04_promissory_note.docx",
    "ack": "05_notarial_acknowledgment_page.docx",
}
BANNER = {"en": "DRAFT \u2014 NOT LEGALLY REVIEWED", "ceb": "DRAFT \u2014 WALA PA NAREVIEW SA ABOGADO"}
PRIOR_DEFAULT = {"en": "monthly interest only, with no payment of principal and no written schedule",
                 "ceb": "interes lang matag bulan, walay bayad sa prinsipal ug walay sinulat nga talaan"}


class InputError(ValueError):
    pass


def money_in(s, field):
    try:
        v = Decimal(str(s).replace(",", "").replace("PHP", "").strip() or "0")
    except InvalidOperation:
        raise InputError(f"{field}: '{s}' is not a number")
    return v


def date_in(s, field):
    try:
        return date.fromisoformat(str(s).strip())
    except ValueError:
        raise InputError(f"{field}: use the format YYYY-MM-DD (for example 2026-12-15)")


def fmt_rate(x):
    s = f"{Decimal(x).quantize(Decimal('0.0001')):.4f}".rstrip("0")
    return s + "0" * (2 - len(s.split(".")[1])) if "." in s else s


@dataclass
class Plan:
    path: str
    principal: Decimal
    annual: Decimal
    r: Decimal
    rows: list
    regular: Decimal
    floor: Decimal
    first: date
    signing: date
    due_day: int
    max_months: int
    warnings: list

    @property
    def total_interest(self): return sum(x["interest"] for x in self.rows)
    @property
    def total_principal(self): return sum(x["principal"] for x in self.rows)
    @property
    def total_payable(self): return sum(x["payment"] for x in self.rows)


def principal_of(inp):
    """NEW: the entered principal. EXISTING: outstanding principal + adjustment + amounts carried in."""
    if inp.get("path", "NEW") == "EXISTING":
        P = (money_in(inp.get("opening_balance", ""), "Outstanding principal") + money_in(inp.get("adjustment", "0"), "Agreed adjustment")
             + money_in(inp.get("arrears", "0"), "Unpaid amounts carried in"))
    else:
        P = money_in(inp.get("principal", ""), "Principal")
    if P <= 0:
        raise InputError("Principal must be greater than zero")
    return P


def compute_plan(inp, cfg):
    """Validate the inputs and build the schedule. Raises InputError or loan_calc.LoanError."""
    path = inp.get("path", "NEW")
    P = principal_of(inp)
    annual = money_in(inp.get("annual_rate", cfg["default_annual_rate"]), "Annual rate")
    if annual < 0 or annual > 100:
        raise InputError("Annual rate must be between 0 and 100 percent")
    try:
        due_day = int(inp.get("due_day", ""))
    except ValueError:
        raise InputError("Due day must be a whole number from 1 to 31")
    if not 1 <= due_day <= 31:
        raise InputError("Due day must be from 1 to 31")
    signing = date_in(inp.get("signing_date", ""), "Signing date")
    first = date_in(inp.get("first_due_date", ""), "First due date")
    if first <= signing:
        raise InputError("First due date must be after the signing date")
    disclosure = date_in(inp.get("disclosure_date", inp.get("signing_date", "")), "Disclosure date")
    if disclosure > signing:
        raise InputError("The disclosure must be given on or before the signing date")
    cap = int(cfg["max_months"])
    r = c.monthly_rate(annual)
    floor = c.min_payment(P, annual, cap)
    if inp.get("mode", "payment") == "term":
        try:
            term = int(inp.get("term", ""))
        except ValueError:
            raise InputError("Term must be a whole number of months")
        regular = c.term_mode(P, annual, term, cfg["installment_rounding"], cap)
        rows = c.schedule(P, r, term, regular, first, due_day)
    else:
        regular = money_in(inp.get("payment", ""), "Monthly payment")
        rows = c.payment_plan(P, annual, regular, first, due_day, cap)
    warnings = []
    if annual > 24:
        warnings.append("Rate is above 24% a year. Courts can reduce rates they find unconscionable; check with the lawyer.")
    if due_day > 28:
        warnings.append(f"Due day {due_day} falls on the last day of shorter months (rule S2).")
    if abs(rows[-1]["payment"] - regular) > 50 and len(rows) > 1 and rows[-1]["payment"] > regular:
        warnings.append("The final installment is noticeably larger than the regular one.")
    return Plan(path, P, annual, r, rows, regular, floor, first, signing, due_day, cap, warnings)


def build_context(inp, cfg, lang, docs=None):
    plan = compute_plan(inp, cfg)
    docs = docs or list(DOCS)
    en = lang == "en"
    f = lambda d: rt.fmt_date(d, lang)
    path, P, rows = plan.path, plan.principal, plan.rows
    signing = plan.signing
    disclosure = date_in(inp.get("disclosure_date", inp.get("signing_date", "")), "Disclosure date")
    pen = str(cfg["late_penalty_pct"]).strip()
    ctx = dict(
        draft_banner=BANNER[lang] if cfg["draft_banner_on"] else "",
        loan_ref=inp["loan_ref"], version_no=int(inp.get("version_no", 1)), path=path,
        with_promissory_note="note" in docs, with_loan_agreement="agreement" in docs,
        agreement_title=("LOAN AGREEMENT" if path == "NEW" else "LOAN RESTRUCTURING AGREEMENT") if en
        else ("KASUNDUAN SA UTANG" if path == "NEW" else "KASUNDUAN SA PAG-USAB SA UTANG"),
        doc_date=f(signing), disclosure_date=f(disclosure), disbursement_date=f(signing),
        place_of_signing=inp.get("place_of_signing") or cfg["place_of_signing"],
        lender_name=cfg["lender_name"], lender_citizenship=cfg["lender_citizenship"], lender_civil_status=cfg["lender_civil_status"],
        lender_address=cfg["lender_address"],
        borrower_name=inp["borrower_name"], borrower_citizenship=inp.get("borrower_citizenship", ""),
        borrower_civil_status=inp.get("borrower_civil_status", ""), borrower_address=inp.get("borrower_address", ""),
        witness1_name=inp.get("witness1_name", ""), witness2_name=inp.get("witness2_name", ""),
        as_of_date=f(date_in(inp["as_of_date"], "As-of date")) if path == "EXISTING" else "",
        opening_balance=rt.php(money_in(inp.get("opening_balance", "0"), "Outstanding principal")) if path == "EXISTING" else "",
        adjustment_fmt=rt.php(money_in(inp.get("adjustment", "0"), "Adjustment")),
        arrears_fmt=rt.php(money_in(inp.get("arrears", "0"), "Arrears")),
        prior_arrangement_text=(inp.get("prior_arrangement") or "").strip() or PRIOR_DEFAULT[lang],
        principal=rt.php(P), principal_words=rt.peso_words(P, lang), amount_financed=rt.php(P),
        annual_rate=f"{plan.annual:.2f}", monthly_rate=fmt_rate(plan.r * 100), simple_annual=f"{plan.annual:.2f}",
        effective_annual=f"{((1 + plan.r) ** 12 - 1) * 100:.2f}", term_months=len(rows),
        payment=rt.php(plan.regular), final_payment=rt.php(rows[-1]["payment"]),
        due_day=plan.due_day, first_due_date=f(rows[0]["due"]), last_due_date=f(rows[-1]["due"]),
        finance_charge=rt.php(plan.total_interest), total_interest=rt.php(plan.total_interest), total_payable=rt.php(plan.total_payable),
        total_interest_plain=rt.money(plan.total_interest), total_principal_plain=rt.money(plan.total_principal),
        total_payable_plain=rt.money(plan.total_payable),
        other_charges_text="None." if en else "Wala.",
        dst_estimate=rt.php(c.dst_estimate(P, signing, rows[-1]["due"])) + (" (estimate; confirm with a lawyer or the BIR)" if en else " (banabana lang; kumpirmahon sa abogado o sa BIR)"),
        dst_payer=("the Lender" if cfg["dst_payer"] == "lender" else "the Borrower") if en else ("ang Nagpautang" if cfg["dst_payer"] == "lender" else "ang Nangutang"),
        default_days=cfg["default_days"], notice_days=cfg["notice_days"],
        ack_document_title=" and ".join(t for k, t in (("agreement", "Loan Agreement"), ("note", "Promissory Note")) if k in docs) or "instrument",
        schedule=[dict(seq=x["seq"], due_date=rt.fmt_date(x["due"], lang, short=True), opening=rt.money(x["opening"]), interest=rt.money(x["interest"]),
                       principal=rt.money(x["principal"]), payment=rt.money(x["payment"]), closing=rt.money(x["closing"])) for x in rows],
    )
    ctx.update(rt.rules(lang, ctx["annual_rate"], ctx["monthly_rate"], plan.due_day, int(cfg["grace_days"]), pen))
    if float(pen) == 0:
        ctx["late_charge_text"] = "No late charge applies." if en else "Walay multa sa paglangan."
    return ctx, plan


def check_rendered(path, ctx, key):
    d = Document(str(path))
    body = [p.text for p in d.paragraphs]
    cells = [p.text for tb in d.tables for r in tb.rows for cl in r.cells for p in cl.paragraphs]
    full = "\n".join(body + cells)
    if "{{" in full or "{%" in full:
        raise RuntimeError(f"{path.name}: leftover template tag")
    if [x for x in body if x.strip().rstrip(".").isdigit()]:
        raise RuntimeError(f"{path.name}: a numbered clause has no text")
    rules = [k for k in ctx if k.startswith("rule_")]
    need = {"disclosure": [k for k in rules if k != "rule_records"], "schedule": ["rule_interest_method", "rule_rounding", "rule_short_month", "rule_application", "rule_records"],
            "agreement": rules, "note": rules}.get(key, [])
    for k in need + (["late_charge_text"] if key in ("disclosure", "agreement", "note") else []):
        if ctx[k] not in full:
            raise RuntimeError(f"{path.name}: missing {k}")


def safe(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_") or "loan"


def generate(inp, cfg, langs, docs, out_root=None):
    """Render the chosen documents for each language. Returns list of (lang, folder, [files])."""
    out_root = Path(out_root or cfg["output_dir"])
    if not out_root.is_absolute():
        out_root = HERE / out_root
    results = []
    for lang in langs:
        ctx, _ = build_context(inp, cfg, lang, docs)
        folder = out_root / f"{safe(inp['loan_ref'])}_{safe(inp['borrower_name'])}" / lang
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for key in docs:
            tpl = DocxTemplate(str(HERE / "templates" / lang / DOCS[key]))
            tpl.render(ctx, autoescape=True)
            dest = folder / DOCS[key]
            tpl.save(str(dest))
            check_rendered(dest, ctx, key)
            files.append(dest)
        results.append((lang, folder, files))
    return results
