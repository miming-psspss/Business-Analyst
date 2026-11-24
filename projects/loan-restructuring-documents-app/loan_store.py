"""Tiny SQLite store for saved loan drafts and a log of generated documents.
NOTE: this is the first slice only. The payments ledger, version locking and triggers from the
master document (milestones M2, M4, M5) are NOT here yet."""
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "loan_app.db"


def _conn():
    DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_ref TEXT PRIMARY KEY, borrower_name TEXT NOT NULL, path TEXT NOT NULL,
            inputs_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS doc_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, loan_ref TEXT NOT NULL, lang TEXT NOT NULL,
            folder TEXT NOT NULL, generated_at TEXT NOT NULL);
    """)
    return con


def now():
    return datetime.now().isoformat(timespec="seconds")


def save_loan(inputs):
    ref = inputs["loan_ref"].strip()
    if not ref:
        raise ValueError("Loan reference is required")
    with _conn() as con:
        row = con.execute("SELECT created_at FROM loans WHERE loan_ref=?", (ref,)).fetchone()
        con.execute("""INSERT INTO loans(loan_ref,borrower_name,path,inputs_json,status,created_at,updated_at)
                       VALUES(?,?,?,?,'draft',?,?)
                       ON CONFLICT(loan_ref) DO UPDATE SET borrower_name=excluded.borrower_name, path=excluded.path,
                       inputs_json=excluded.inputs_json, updated_at=excluded.updated_at""",
                    (ref, inputs.get("borrower_name", ""), inputs.get("path", "NEW"), json.dumps(inputs),
                     row["created_at"] if row else now(), now()))


def list_loans():
    with _conn() as con:
        return [dict(r) for r in con.execute("SELECT loan_ref,borrower_name,path,status,inputs_json,updated_at FROM loans ORDER BY updated_at DESC")]


def get_loan(ref):
    with _conn() as con:
        r = con.execute("SELECT inputs_json FROM loans WHERE loan_ref=?", (ref,)).fetchone()
    return json.loads(r["inputs_json"]) if r else None


def next_ref():
    with _conn() as con:
        n = con.execute("SELECT COUNT(*) FROM loans").fetchone()[0] + 1
        while con.execute("SELECT 1 FROM loans WHERE loan_ref=?", (f"L-{n:04d}",)).fetchone():
            n += 1
    return f"L-{n:04d}"


def log_docs(ref, lang, folder):
    with _conn() as con:
        con.execute("INSERT INTO doc_log(loan_ref,lang,folder,generated_at) VALUES(?,?,?,?)", (ref, lang, str(folder), now()))
        con.execute("UPDATE loans SET status='generated', updated_at=? WHERE loan_ref=?", (now(), ref))


def backup():
    _conn().close()
    dest = DATA_DIR / "backups"; dest.mkdir(exist_ok=True)
    out = dest / f"loan_app_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DB_PATH, out)
    return out
