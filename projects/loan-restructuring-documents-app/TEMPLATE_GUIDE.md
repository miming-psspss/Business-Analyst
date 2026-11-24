# Loan App Templates — Guide (VoP v1.1, DRAFT — not legally reviewed)

## Layout
| Path | What it is |
|---|---|
| templates/en/, templates/ceb/ | The five docxtpl templates in English and Cebuano (01 disclosure, 02 Annex A schedule, 03 agreement, 04 promissory note, 05 notarial acknowledgment page — English in both; it is the notary's own form) |
| loan_calc.py | Calculator (M1 seed): annual rate, payment-first mode, term cap from config, whole-peso installment, DST estimate |
| loan_config.json | Adjustable settings: `max_months` (default 36 = three years) and `installment_rounding` |
| test_loan_calc.py | Calculator tests, including the 945.60 acceptance check |
| rules_text.py | The ONE source for every rule sentence, in English and Cebuano, plus amount-in-words and date formats |
| render_test.py | Builds a synthetic context, renders a language/path, runs text checks. `python render_test.py ceb EXISTING 5000` (last argument = monthly payment) |
| build_templates.js | Regenerates all templates (`node build_templates.js`); all wording lives in its `S.en` / `S.ceb` tables |
| samples/ | One rendered set per language (100,000 at 5,000 a month = 24 installments), synthetic data only |

## Decisions applied (Oct 26, 2026)
- New rate **15% per annum** (shown as 1.25% per month, simple); the app stores the annual rate.
- **Payment-first (revised Oct 26, 2026):** the lender enters what the borrower can pay each month; the term follows from it. The longest term is `max_months` in loan_config.json (default 36). A payment at or below one month's interest, or below the minimum that clears the loan within the cap, is refused and the minimum is shown. Fixed-term mode still exists for any term up to the cap.
- Installment rounded to the **whole peso** (50 centavos and up rounds up); monthly interest to the centavo; the final installment absorbs the difference.
- Restructured balance comes from the lender's balance list; **no past charges carried in** (arrears default 0.00).
- Late charge: **proposal** 2% of the overdue installment per month after 3 days' grace, in addition to interest, never compounding. Default clause: 30 days overdue, then 7 days' written notice. Both are constants at the top of render_test.py.
- Documentary stamp tax and notary fee: proposed to be borne by the **Lender**. DST is an ESTIMATE (PHP 1.50 per PHP 200, prorated by days/365 under one year) and must be confirmed.
- One borrower per loan; witnesses (no co-signers).
- Every document still carries the DRAFT banner (`draft_banner`). Set it to "" only when the lawyer has actually approved.

## Rules for the app
- Render with `doc.render(ctx, autoescape=True)`. Build rule sentences once (`rules_text.rules(...)`) and pass them to every document.
- Final (non-draft) output only from a LOCKED loan version.
- Cebuano text is a draft for a native speaker and the lawyer. Bracketed DRAFTING NOTES stay in English on purpose.

## Context fields
Control: draft_banner, path (NEW | EXISTING), with_promissory_note, with_loan_agreement, agreement_title
Identity: loan_ref, version_no, doc_date, disclosure_date, disbursement_date, place_of_signing
Parties: lender_* and borrower_* (name, citizenship, civil_status, address); witness1_name, witness2_name
EXISTING only: as_of_date, opening_balance, adjustment_fmt, arrears_fmt, prior_arrangement_text
Money (formatted "PHP 9,026.00"): principal, principal_words, amount_financed, payment, final_payment, finance_charge, total_interest, total_payable, dst_estimate, dst_payer; plain numbers for the annex totals: total_interest_plain, total_principal_plain, total_payable_plain
Terms: annual_rate, monthly_rate, simple_annual, effective_annual, term_months (number of installments, set by the payment), due_day, first_due_date, last_due_date, other_charges_text, default_days, notice_days
Rules: rule_interest_method, rule_rounding, rule_short_month, rule_application, rule_prepayment, rule_place_of_payment, rule_records, late_charge_text
Schedule: `schedule` = list of {seq, due_date, opening, interest, principal, payment, closing} (strings)
Notary page: ack_document_title

## Lawyer flags
1. Disclosure items and format under the Truth in Lending Act, if it applies.
2. How the old arrangement ends; how it is described in the documents; treatment of interest already paid.
3. Penalty and default terms. Courts may reduce penalties under Civil Code Art. 1229; a 2% monthly penalty was upheld in one case and 3% cut to 1% in another (see master doc, Section 10).
4. Whether a penalty replaces interest unless the contract says otherwise (Art. 1226): the late-charge text says "in addition to interest".
5. One documentary stamp tax per agreement or note; who pays; the correct estimate.
6. Governing law, venue, spousal consent.
7. Acknowledgment form under the notarial rules now in force.
8. SEC authority for lending (RA 9474) and tax treatment of interest income: not addressed by any template.
