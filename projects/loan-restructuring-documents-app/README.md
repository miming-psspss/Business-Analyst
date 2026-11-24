# Loan Restructuring & Documents App

Python and SQLite desktop tool (Tkinter, docxtpl) for a small private lender who is
moving informal, interest-only loans onto clear written terms. It calculates a plain
amortization schedule from a monthly payment the borrower can afford, and generates the
signable documents: disclosure statement, amortization schedule annex, loan agreement,
promissory note and notarial acknowledgment page.

**Status: design and partial build.** The calculator and document engine are built and
tested; the desktop GUI is in progress. Not in production. Synthetic data only. The
generated documents are drafts and have not been legally reviewed.

## What is here

| Path | Purpose |
|---|---|
| `Loan_Restructuring_App_Case_Study.pdf` | Business analysis case study: stakeholders, current state, requirements, numbered assumptions with confidence ratings, a decision log, calculation rules with worked examples, data model and tests |
| `loan_calc.py` | Calculation engine (amortization, payment-first terms, rounding) |
| `loan_store.py`, `settings.py`, `rules_text.py` | Storage, settings and the rule text used by the documents |
| `doc_context.py` | Builds the data passed into the Word templates |
| `loan_app.py` | Desktop GUI (in progress) |
| `templates/en/` | English Word templates; `templates/build_templates.js` regenerates them |
| `test_loan_calc.py`, `render_test.py`, `smoke_test_gui.py` | Calculator tests, a template render test on synthetic data, and a GUI smoke test |
| `README_RUN.md`, `TEMPLATE_GUIDE.md` | How to run the app and how the templates work |

## Run the tests

    pip install docxtpl python-docx
    python3 test_loan_calc.py
    python3 render_test.py

The calculator tests and the English template render test pass on synthetic data.

## Known gaps

- Only the English templates are included in this copy. The code supports a Cebuano
  document set, but those templates are not part of this repository.
- The GUI is not finished; see `README_RUN.md` for what the current version does not do.
- No real borrower data is stored or committed. The database is created on first run.
