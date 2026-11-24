"""Headless smoke test of the GUI. Linux: xvfb-run -a python3 smoke_test_gui.py [screenshot_dir]
Uses a temporary database/output folder so nothing real is touched."""
import sys, tempfile
from pathlib import Path
import loan_store, settings
tmp = Path(tempfile.mkdtemp())
loan_store.DATA_DIR = tmp / "data"; loan_store.DB_PATH = loan_store.DATA_DIR / "loan_app.db"
settings.CONFIG_PATH = tmp / "cfg.json"
import loan_app

shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
app = loan_app.App()
app.info = app.error = lambda *a: print("DIALOG:", a)
app.ask = lambda *a: False
def pump():
    for _ in range(5): app.update_idletasks(); app.update()
def shot(name):
    pump()
    if shots:
        import subprocess; shots.mkdir(exist_ok=True)
        subprocess.run(["import", "-window", "root", str(shots / name)], check=False)

# settings
for k, v in dict(lender_name="JUAN D. SAMPLE", lender_civil_status="married", lender_address="Sample St., Candijay, Bohol", place_of_signing="Candijay, Bohol", output_dir=str(tmp / "out")).items():
    app.sv[k].set(v)
app.save_settings(); assert app.cfg["lender_name"] == "JUAN D. SAMPLE"

v = app.v
v["path"].set("EXISTING"); v["opening_balance"].set("100000"); v["borrower_name"].set("MARIA S. EXAMPLE")
v["borrower_civil_status"].set("single"); v["borrower_address"].set("Example St., Example Barangay, Candijay, Bohol")
v["witness1_name"].set("WITNESS ONE"); v["witness2_name"].set("WITNESS TWO"); v["payment"].set("5000")
v["signing_date"].set("2026-11-20"); v["disclosure_date"].set("2026-11-18"); v["as_of_date"].set("2026-11-15")
app.suggest_first_due(); app.path_changed(); pump(); app.recalc(); pump()
assert app.plan and len(app.plan.rows) == 24, app.plan
assert len(app.tree.get_children()) == 24
shot("loan_tab.png")

# refusals shown in the summary, not as crashes
v["payment"].set("3000"); app.recalc(); pump()
assert app.plan is None and "too small" in app.summary.get("1.0", "end"); shot("refused.png")
v["payment"].set("5000"); app.recalc()

# compare tab
app.nb.select(app.tab_cmp); app.compare(); pump()
rows = [app.cmp_tree.item(i)["values"] for i in app.cmp_tree.get_children()]
assert len(rows) == 7 and rows[0][4] == "OK", rows
app.cmp_var.set("1250, 3000, 3467, 9026"); app.compare(); pump()
res = [app.cmp_tree.item(i)["values"][4] for i in app.cmp_tree.get_children()]
assert res[0] != "OK" and res[1] != "OK" and res[2] == "OK" and res[3] == "OK", res
shot("compare.png")
app.cmp_tree.selection_set(app.cmp_tree.get_children()[3]); app.use_selected(); assert v["payment"].get() == "9026.00", v["payment"].get()
v["payment"].set("5000"); app.recalc()

# generate (both languages)
v["lang"].set("English + Cebuano"); app.generate_docs(); pump()
out = list((tmp / "out").rglob("*.docx")); assert len(out) == 10, len(out)
app.nb.select(app.tab_saved); app.refresh_saved(); pump()
assert app.saved_tree.get_children() == ("L-0001",), app.saved_tree.get_children()
shot("saved.png")
app.nb.select(app.tab_set); shot("settings.png")

# reload a saved loan, backup, new loan
app.new_loan(); assert v["borrower_name"].get() == "" and v["loan_ref"].get() == "L-0002"
app.saved_tree.selection_set("L-0001"); app.load_selected(); assert v["borrower_name"].get() == "MARIA S. EXAMPLE" and v["payment"].get() == "5000"
app.do_backup(); assert any((loan_store.DATA_DIR / "backups").glob("*.db"))
# settings change takes effect: shorter cap refuses 3,467
app.sv["max_months"].set("24"); app.save_settings(); v["payment"].set("3467"); app.recalc(); assert app.plan is None
print("GUI smoke test passed:", len(out), "documents,", "10 checks")
app.destroy()
