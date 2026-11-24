#!/usr/bin/env python3
"""Loan App — simple desktop GUI (Tkinter).  Run:  python3 loan_app.py

Tabs: Loan (enter details, live schedule, generate documents) | Compare payments |
      Saved loans | Settings.
This is the first slice: drafts and documents. The payments ledger and version locking
(master document milestones M4/M5) are not built yet. Every document keeps its DRAFT banner
until you turn it off in Settings after a lawyer has approved the wording."""
import os
import subprocess
import sys
import tkinter as tk
from datetime import date
from decimal import Decimal
from tkinter import messagebox, ttk

import doc_context as dc
import loan_calc as c
import loan_store
import rules_text as rt
import settings

LANG_CHOICES = {"English": "en", "Cebuano": "ceb", "English + Cebuano": "both"}
DOC_LABELS = [("disclosure", "Disclosure"), ("schedule", "Schedule (Annex A)"), ("agreement", "Agreement"),
              ("note", "Promissory note"), ("ack", "Notary acknowledgment page")]


def open_folder(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Loan App \u2014 restructuring and documents (DRAFT tool)")
        self.geometry("1320x840")
        self.minsize(1180, 700)
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass
        self.cfg = settings.load()
        c.CONFIG.update({"max_months": int(self.cfg["max_months"]), "installment_rounding": self.cfg["installment_rounding"]})
        self.v = {}        # loan form variables
        self.sv = {}       # settings variables
        self._after = None
        self.plan = None
        self.status = tk.StringVar(value="")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        self.nb = nb
        self.tab_loan, self.tab_cmp, self.tab_saved, self.tab_set = (ttk.Frame(nb) for _ in range(4))
        for t, name in ((self.tab_loan, "  Loan  "), (self.tab_cmp, "  Compare payments  "), (self.tab_saved, "  Saved loans  "), (self.tab_set, "  Settings  ")):
            nb.add(t, text=name)
        self.build_loan(); self.build_compare(); self.build_saved(); self.build_settings()
        ttk.Label(self, textvariable=self.status, anchor="w", foreground="#444").pack(fill="x", padx=8, pady=(2, 6))
        self.new_loan()
        if not self.cfg["lender_name"]:
            self.say("Start in Settings: enter the lender's details so every document is filled in.")

    # ---------- small helpers (overridable in tests) ----------
    def say(self, msg): self.status.set(msg)
    def info(self, title, msg): messagebox.showinfo(title, msg)
    def error(self, title, msg): messagebox.showerror(title, msg)
    def ask(self, title, msg): return messagebox.askyesno(title, msg)

    def entry(self, parent, row, label, key, width=26, hint=None, store=None):
        store = self.v if store is None else store
        store[key] = tk.StringVar()
        lab = ttk.Label(parent, text=label)
        lab.grid(row=row, column=0, sticky="w", padx=(6, 8), pady=2)
        e = ttk.Entry(parent, textvariable=store[key], width=width)
        e.grid(row=row, column=1, sticky="we", pady=2, padx=(0, 6))
        if hint and len(hint) <= 12:
            ttk.Label(parent, text=hint, foreground="#777").grid(row=row, column=2, sticky="w")
        return lab, e

    # ---------- LOAN TAB ----------
    def build_loan(self):
        left = ttk.Frame(self.tab_loan); left.pack(side="left", fill="y", padx=8, pady=8)
        right = ttk.Frame(self.tab_loan); right.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        lf = ttk.LabelFrame(left, text=" Loan "); lf.pack(fill="x")
        lf.columnconfigure(1, weight=1)
        r = 0
        self.entry(lf, r, "Loan reference", "loan_ref", 14); r += 1
        self.v["path"] = tk.StringVar(value="EXISTING")
        ttk.Label(lf, text="Loan type").grid(row=r, column=0, sticky="w", padx=(6, 8), pady=2)
        cb = ttk.Combobox(lf, textvariable=self.v["path"], values=["NEW", "EXISTING"], state="readonly", width=12)
        cb.grid(row=r, column=1, sticky="w"); cb.bind("<<ComboboxSelected>>", lambda e: self.path_changed())
        r += 1
        self.new_rows = [self.entry(lf, r, "Principal (PHP)", "principal", 16)]; r += 1
        self.ex_rows = [self.entry(lf, r, "Outstanding principal (PHP)", "opening_balance", 16, "from your balance list"),
                        self.entry(lf, r + 1, "Agreed adjustment (+/-)", "adjustment", 16, "0 unless agreed"),
                        self.entry(lf, r + 2, "Unpaid amounts carried in", "arrears", 16, "0 by default"),
                        self.entry(lf, r + 3, "Balance as of (YYYY-MM-DD)", "as_of_date", 16)]
        r += 4
        self.entry(lf, r, "Annual interest rate (%)", "annual_rate", 10, "per year"); r += 1
        self.v["mode"] = tk.StringVar(value="payment")
        ttk.Radiobutton(lf, text="Monthly payment (PHP)", variable=self.v["mode"], value="payment", command=self.mode_changed).grid(row=r, column=0, sticky="w", padx=6)
        self.v["payment"] = tk.StringVar(); self.e_pay = ttk.Entry(lf, textvariable=self.v["payment"], width=16); self.e_pay.grid(row=r, column=1, sticky="w")
        r += 1
        ttk.Radiobutton(lf, text="Fixed term (months)", variable=self.v["mode"], value="term", command=self.mode_changed).grid(row=r, column=0, sticky="w", padx=6)
        self.v["term"] = tk.StringVar(); self.e_term = ttk.Entry(lf, textvariable=self.v["term"], width=16); self.e_term.grid(row=r, column=1, sticky="w")
        self.lbl_cap = ttk.Label(lf, text="", foreground="#777", width=18); self.lbl_cap.grid(row=r, column=2, sticky="w"); r += 1
        self.entry(lf, r, "Due day of month (1-31)", "due_day", 8); r += 1
        self.entry(lf, r, "Signing date (YYYY-MM-DD)", "signing_date", 14); r += 1
        lab, e = self.entry(lf, r, "First due date (YYYY-MM-DD)", "first_due_date", 14)
        ttk.Button(lf, text="Suggest", width=8, command=self.suggest_first_due).grid(row=r, column=2, sticky="w"); r += 1
        self.entry(lf, r, "Disclosure given on", "disclosure_date", 14, "on or before signing"); r += 1
        self.entry(lf, r, "Place of signing", "place_of_signing", 26)

        ttk.Label(left, text="NEW = money lent now.  EXISTING = restructure a running loan.\nMonthly payment = what the borrower can pay; the term follows.", foreground="#666", justify="left").pack(anchor="w", padx=6, pady=(4, 0))
        bf = ttk.LabelFrame(left, text=" Borrower "); bf.pack(fill="x", pady=(8, 0)); bf.columnconfigure(1, weight=1)
        for i, (lbl, key) in enumerate((("Full name", "borrower_name"), ("Citizenship", "borrower_citizenship"), ("Civil status", "borrower_civil_status"),
                                        ("Address", "borrower_address"), ("Witness 1", "witness1_name"), ("Witness 2", "witness2_name"),
                                        ("Previous arrangement", "prior_arrangement"))):
            self.entry(bf, i, lbl, key, 30)
        ttk.Label(bf, text="(leave 'Previous arrangement' blank for the standard wording)", foreground="#777").grid(row=7, column=0, columnspan=3, sticky="w", padx=6)

        self.summary = tk.Text(right, height=11, wrap="word", state="disabled", background="#fafafa", tabs=("230",), padx=8, pady=6)
        self.summary.pack(fill="x")
        self.summary.tag_configure("bad", foreground="#b00020"); self.summary.tag_configure("warn", foreground="#7a4b00"); self.summary.tag_configure("h", font=("TkDefaultFont", 10, "bold"))
        act = ttk.LabelFrame(right, text=" Documents "); act.pack(fill="x", pady=(8, 0))
        self.doc_vars = {}
        for i, (k, lbl) in enumerate(DOC_LABELS):
            self.doc_vars[k] = tk.BooleanVar(value=True)
            ttk.Checkbutton(act, text=lbl, variable=self.doc_vars[k]).grid(row=i // 2, column=i % 2, sticky="w", padx=6, pady=1)
        self.v["lang"] = tk.StringVar()
        ttk.Label(act, text="Language").grid(row=3, column=0, sticky="w", padx=6, pady=(6, 4))
        ttk.Combobox(act, textvariable=self.v["lang"], values=list(LANG_CHOICES), state="readonly", width=18).grid(row=3, column=1, sticky="w", pady=(6, 4))
        bb = ttk.Frame(right); bb.pack(fill="x", pady=(8, 0))
        ttk.Button(bb, text="New loan", command=self.new_loan).pack(side="left")
        ttk.Button(bb, text="Save draft", command=self.save_draft).pack(side="left", padx=6)
        ttk.Button(bb, text="Generate documents", command=self.generate_docs).pack(side="left")

        cols = ("No.", "Due date", "Opening", "Interest", "Principal", "Installment", "Closing")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=14)
        for col, w in zip(cols, (40, 95, 100, 90, 95, 100, 100)):
            self.tree.heading(col, text=col); self.tree.column(col, width=w, anchor="e" if col not in ("No.", "Due date") else "center")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, pady=(8, 0)); sb.pack(side="left", fill="y", pady=(8, 0))
        for key in self.v:
            if key not in ("path", "mode", "lang"):
                self.v[key].trace_add("write", lambda *a: self.schedule_recalc())
        self.v["path"].trace_add("write", lambda *a: self.schedule_recalc())
        self.v["mode"].trace_add("write", lambda *a: self.schedule_recalc())

    def path_changed(self):
        ex = self.v["path"].get() == "EXISTING"
        for lab, e in self.new_rows:
            for w in (lab, e):
                w.grid_remove() if ex else w.grid()
        for lab, e in self.ex_rows:
            for w in (lab, e):
                w.grid() if ex else w.grid_remove()
        self.schedule_recalc()

    def mode_changed(self):
        pay = self.v["mode"].get() == "payment"
        self.e_pay.state(["!disabled"] if pay else ["disabled"]); self.e_term.state(["disabled"] if pay else ["!disabled"])
        self.schedule_recalc()

    def suggest_first_due(self):
        try:
            signing = date.fromisoformat(self.v["signing_date"].get().strip()); dd = int(self.v["due_day"].get())
            self.v["first_due_date"].set(c.due_date(signing, dd, 1).isoformat())
        except ValueError:
            self.say("Enter a valid signing date and due day first.")

    def new_loan(self):
        today = date.today().isoformat()
        for k in self.v:
            if k not in ("path", "mode", "lang"):
                self.v[k].set("")
        self.v["loan_ref"].set(loan_store.next_ref())
        self.v["path"].set("EXISTING"); self.v["mode"].set("payment")
        self.v["annual_rate"].set(str(self.cfg["default_annual_rate"])); self.v["adjustment"].set("0"); self.v["arrears"].set("0")
        self.v["due_day"].set("15"); self.v["signing_date"].set(today); self.v["disclosure_date"].set(today); self.v["as_of_date"].set(today)
        self.v["place_of_signing"].set(self.cfg["place_of_signing"]); self.v["borrower_citizenship"].set("Filipino")
        self.v["lang"].set({v: k for k, v in LANG_CHOICES.items()}[self.cfg["language"]])
        self.suggest_first_due(); self.path_changed(); self.mode_changed()
        self.lbl_cap.config(text=f"up to {self.cfg['max_months']} months")
        self.say("New loan started.")

    def inputs(self):
        d = {k: var.get().strip() for k, var in self.v.items() if k != "lang"}
        d["version_no"] = 1
        return d

    def schedule_recalc(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(250, self.recalc)

    def write_summary(self, lines):
        self.summary.config(state="normal"); self.summary.delete("1.0", "end")
        for text, tag in lines:
            self.summary.insert("end", text + "\n", tag or ())
        self.summary.config(state="disabled")

    def recalc(self):
        self._after = None
        self.tree.delete(*self.tree.get_children())
        self.plan = None
        inp = self.inputs()
        try:
            p = dc.compute_plan(inp, self.cfg)
        except (dc.InputError, c.LoanError) as e:
            msg = str(e)
            self.write_summary([("Cannot build a schedule yet:", "bad"), (msg, "bad")]); return
        self.plan = p
        yrs, mos = divmod(len(p.rows), 12)
        term = (f"{yrs} yr " if yrs else "") + (f"{mos} mo" if mos else "")
        dst = c.dst_estimate(p.principal, p.signing, p.rows[-1]["due"])
        lines = [
            (f"Principal\tPHP {rt.money(p.principal)}", 'h'),
            (f"Rate\t{p.annual:.2f}% a year  ({dc.fmt_rate(p.r * 100)}% a month, simple)", None),
            (f"Regular installment\tPHP {rt.money(p.regular)}", None),
            (f"Number of installments\t{len(p.rows)}  ({term.strip()})", None),
            (f"Final installment\tPHP {rt.money(p.rows[-1]['payment'])}", None),
            (f"Total interest\tPHP {rt.money(p.total_interest)}", None),
            (f"Total to be paid\tPHP {rt.money(p.total_payable)}", None),
            (f"Minimum payment for {p.max_months} months\tPHP {rt.money(p.floor)}", None),
            (f"Stamp tax (estimate only)\tPHP {rt.money(dst)}", None)]
        lines += [("! " + w, "warn") for w in p.warnings]
        self.write_summary(lines)
        for x in p.rows:
            self.tree.insert("", "end", values=(x["seq"], x["due"].isoformat(), rt.money(x["opening"]), rt.money(x["interest"]),
                                                rt.money(x["principal"]), rt.money(x["payment"]), rt.money(x["closing"])))

    def need_people(self):
        if not self.cfg["lender_name"].strip():
            self.error("Lender details missing", "Enter the lender's name and address in the Settings tab first."); return False
        if not self.v["borrower_name"].get().strip():
            self.error("Borrower missing", "Enter the borrower's full name."); return False
        return True

    def save_draft(self):
        if not self.v["borrower_name"].get().strip():
            self.error("Borrower missing", "Enter the borrower's full name before saving."); return False
        try:
            loan_store.save_loan(self.inputs())
        except Exception as e:
            self.error("Could not save", str(e)); return False
        self.say(f"Draft {self.v['loan_ref'].get()} saved."); self.refresh_saved(); return True

    def generate_docs(self):
        if not self.need_people():
            return
        docs = [k for k, var in self.doc_vars.items() if var.get()]
        if not docs:
            self.error("Nothing selected", "Tick at least one document."); return
        lang = LANG_CHOICES[self.v["lang"].get()]
        langs = ["en", "ceb"] if lang == "both" else [lang]
        try:
            if not self.save_draft():
                return
            results = dc.generate(self.inputs(), self.cfg, langs, docs)
        except (dc.InputError, c.LoanError) as e:
            self.error("Check the loan details", str(e)); return
        except Exception as e:
            self.error("Could not generate documents", f"{type(e).__name__}: {e}"); return
        for lg, folder, files in results:
            loan_store.log_docs(self.v["loan_ref"].get().strip(), lg, folder)
        self.refresh_saved()
        folder = results[0][1].parent
        self.say(f"{sum(len(r[2]) for r in results)} documents written to {folder}")
        if self.ask("Documents ready", f"{sum(len(r[2]) for r in results)} documents were written to:\n{folder}\n\nThey are DRAFTS. Open the folder?"):
            open_folder(folder)

    # ---------- COMPARE TAB ----------
    def build_compare(self):
        f = self.tab_cmp
        top = ttk.Frame(f); top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Monthly payments to compare (PHP, separated by commas; leave blank for suggestions):").pack(anchor="w")
        self.cmp_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.cmp_var, width=70).pack(side="left", pady=4)
        ttk.Button(top, text="Compare", command=self.compare).pack(side="left", padx=8)
        ttk.Button(top, text="Use selected payment", command=self.use_selected).pack(side="left")
        self.cmp_note = ttk.Label(f, text="Uses the principal and rate from the Loan tab.", foreground="#555"); self.cmp_note.pack(anchor="w", padx=10)
        cols = ("Monthly payment", "Months", "Final installment", "Total interest", "Result")
        self.cmp_tree = ttk.Treeview(f, columns=cols, show="headings", height=18)
        for col, w in zip(cols, (130, 70, 140, 130, 620)):
            self.cmp_tree.heading(col, text=col); self.cmp_tree.column(col, width=w, anchor="w" if col == "Result" else "e")
        self.cmp_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def compare(self):
        inp = self.inputs()
        try:
            P = dc.principal_of(inp)
            annual = dc.money_in(inp.get("annual_rate") or self.cfg["default_annual_rate"], "Annual rate")
            first = dc.date_in(inp["first_due_date"], "First due date"); due_day = int(inp["due_day"])
        except (dc.InputError, c.LoanError, ValueError) as e:
            self.error("Check the Loan tab", str(e)); return
        floor = c.min_payment(P, annual, int(self.cfg["max_months"]))
        txt = self.cmp_var.get().strip()
        if txt:
            try:
                pays = [dc.money_in(x, "Payment") for x in txt.split(",") if x.strip()]
            except dc.InputError as e:
                self.error("Check the payments", str(e)); return
        else:
            pays = [floor + step for step in (0, 500, 1000, 2000, 3000, 5000, 10000)]
        self.cmp_tree.delete(*self.cmp_tree.get_children())
        for o in c.affordability(P, annual, pays, first, due_day, int(self.cfg["max_months"])):
            if o["ok"]:
                self.cmp_tree.insert("", "end", values=(rt.money(o["payment"]), o["months"], rt.money(o["final"]), rt.money(o["total_interest"]), "OK"))
            else:
                self.cmp_tree.insert("", "end", values=(rt.money(o["payment"]), "-", "-", "-", o["note"]))
        self.cmp_note.config(text=f"Principal PHP {rt.money(P)} at {annual:.2f}% a year. Minimum payment for {self.cfg['max_months']} months: PHP {rt.money(floor)}.")

    def use_selected(self):
        sel = self.cmp_tree.selection()
        if not sel:
            self.say("Select a row first."); return
        vals = self.cmp_tree.item(sel[0])["values"]
        if vals[4] != "OK":
            self.say("That payment is refused; pick a row marked OK."); return
        self.v["mode"].set("payment"); self.v["payment"].set(str(vals[0]).replace(",", ""))
        self.nb.select(self.tab_loan); self.say("Payment copied to the Loan tab.")

    # ---------- SAVED TAB ----------
    def build_saved(self):
        f = self.tab_saved
        cols = ("Reference", "Borrower", "Type", "Status", "Updated")
        self.saved_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        for col, w in zip(cols, (110, 300, 90, 110, 180)):
            self.saved_tree.heading(col, text=col); self.saved_tree.column(col, width=w, anchor="w")
        self.saved_tree.pack(fill="both", expand=True, padx=10, pady=10)
        bar = ttk.Frame(f); bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="Load into Loan tab", command=self.load_selected).pack(side="left")
        ttk.Button(bar, text="Back up database", command=self.do_backup).pack(side="left", padx=8)
        ttk.Button(bar, text="Open output folder", command=lambda: open_folder(dc.HERE / self.cfg["output_dir"])).pack(side="left")
        self.refresh_saved()

    def refresh_saved(self):
        self.saved_tree.delete(*self.saved_tree.get_children())
        for r in loan_store.list_loans():
            self.saved_tree.insert("", "end", iid=r["loan_ref"], values=(r["loan_ref"], r["borrower_name"], r["path"], r["status"], r["updated_at"]))

    def load_selected(self):
        sel = self.saved_tree.selection()
        if not sel:
            self.say("Select a saved loan first."); return
        data = loan_store.get_loan(sel[0])
        for k, val in data.items():
            if k in self.v:
                self.v[k].set(str(val))
        self.path_changed(); self.mode_changed(); self.nb.select(self.tab_loan); self.say(f"Loaded {sel[0]}.")

    def do_backup(self):
        try:
            out = loan_store.backup()
        except Exception as e:
            self.error("Backup failed", str(e)); return
        self.say(f"Backup saved: {out}")

    # ---------- SETTINGS TAB ----------
    def build_settings(self):
        f = self.tab_set
        box = ttk.Frame(f); box.pack(anchor="nw", padx=14, pady=12); box.columnconfigure(1, weight=1)
        sections = [
            ("Lender (appears on every document)", [("lender_name", "Lender full name", 40), ("lender_citizenship", "Citizenship", 20),
                                                    ("lender_civil_status", "Civil status", 20), ("lender_address", "Address", 60), ("place_of_signing", "Default place of signing", 40)]),
            ("Calculator", [("max_months", "Longest term (months)", 8), ("default_annual_rate", "Default annual rate (%)", 8)]),
            ("Late payment and default (proposals; confirm with the lawyer)", [("late_penalty_pct", "Late charge (% of overdue installment per month; 0 = none)", 8),
                                                                              ("grace_days", "Grace days before a late charge", 8), ("default_days", "Days overdue before written notice", 8),
                                                                              ("notice_days", "Days allowed after the notice", 8)]),
            ("Output", [("output_dir", "Output folder", 40)]),
        ]
        r = 0
        for title, fields in sections:
            ttk.Label(box, text=title, font=("TkDefaultFont", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 2)); r += 1
            for key, label, w in fields:
                self.entry(box, r, label, key, w, store=self.sv); self.sv[key].set(str(self.cfg[key])); r += 1
        for key, label, values in (("installment_rounding", "Installment rounding", ["peso", "centavo"]), ("dst_payer", "Who bears stamp tax and notary fee", ["lender", "borrower"]),
                                   ("language", "Default language", ["en", "ceb", "both"])):
            self.sv[key] = tk.StringVar(value=str(self.cfg[key]))
            ttk.Label(box, text=label).grid(row=r, column=0, sticky="w", padx=(6, 8), pady=2)
            ttk.Combobox(box, textvariable=self.sv[key], values=values, state="readonly", width=12).grid(row=r, column=1, sticky="w"); r += 1
        self.sv["draft_banner_on"] = tk.BooleanVar(value=bool(self.cfg["draft_banner_on"]))
        ttk.Checkbutton(box, text="Show the DRAFT banner on every document (keep ON until a lawyer has approved the wording)",
                        variable=self.sv["draft_banner_on"]).grid(row=r, column=0, columnspan=2, sticky="w", padx=6, pady=(10, 2)); r += 1
        ttk.Button(box, text="Save settings", command=self.save_settings).grid(row=r, column=0, sticky="w", padx=6, pady=12)

    def save_settings(self):
        new = dict(self.cfg)
        for k, var in self.sv.items():
            new[k] = var.get() if not isinstance(var, tk.BooleanVar) else bool(var.get())
        try:
            self.cfg = settings.save(new)
        except (ValueError, TypeError) as e:
            self.error("Check the settings", str(e)); return
        self.lbl_cap.config(text=f"up to {self.cfg['max_months']} months")
        self.say("Settings saved."); self.schedule_recalc()


if __name__ == "__main__":
    App().mainloop()
