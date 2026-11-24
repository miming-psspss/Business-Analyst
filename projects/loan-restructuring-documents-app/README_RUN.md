# Running the Loan App

## One-time setup (Fedora)
    sudo dnf install python3-tkinter
    pip install --user docxtpl python-docx

(Windows/macOS: Tkinter comes with the python.org installer; `pip install docxtpl python-docx`.)

## Start
    cd "<this folder>"
    python3 loan_app.py

## First use
1. **Settings tab** — enter the lender's name, civil status and address, the place of signing, and check the proposed late-charge and default numbers. Click *Save settings*.
2. **Loan tab** — choose NEW or EXISTING, enter the principal (or the outstanding balance), the annual rate, and the **monthly payment** the borrower can afford. The schedule and totals update as you type. A payment that is too small is refused with the minimum shown.
3. **Compare payments tab** — try several monthly payments side by side, then *Use selected payment*.
4. Fill in the borrower and witnesses, tick the documents you want, pick the language, and click **Generate documents**. Files go to the output folder, one sub-folder per loan and language.
5. **Saved loans tab** — reload a draft, or back up the database.

## What this version does NOT do yet
- No payments ledger, receipts or statement of account (milestone M4).
- No locking of a signed version (M5). Saving a draft again overwrites that draft.
- No database triggers protecting records (M2).
- Every document carries a DRAFT banner. Turn it off in Settings only after a lawyer has approved the wording.

## Files
| File | Role |
|---|---|
| loan_app.py | The window |
| doc_context.py | Validates inputs, builds the plan, fills the templates |
| loan_calc.py | Money math (Decimal) |
| rules_text.py | Rule sentences in English and Cebuano |
| settings.py, loan_config.json | Adjustable settings |
| loan_store.py | SQLite drafts (data/loan_app.db) |
| templates/en, templates/ceb | Word templates |
| test_loan_calc.py, smoke_test_gui.py | Tests (`xvfb-run -a python3 smoke_test_gui.py` on a server without a display) |
