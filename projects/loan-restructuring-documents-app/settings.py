"""App settings, stored in loan_config.json next to the app. loan_calc reads max_months and
installment_rounding from the same file."""
import json
from pathlib import Path

import loan_calc

CONFIG_PATH = Path(__file__).with_name("loan_config.json")

DEFAULTS = {
    # calculator
    "max_months": 36,                # longest term the app will accept (three years)
    "installment_rounding": "peso",  # "peso" (nearest whole peso) or "centavo"
    # loan defaults
    "default_annual_rate": "15",     # percent per annum
    "late_penalty_pct": "2",         # % of overdue installment per month; "0" = no late charge
    "grace_days": 3,
    "default_days": 30,              # default clause: days overdue before written notice
    "notice_days": 7,                # days allowed after the notice
    "dst_payer": "lender",           # "lender" or "borrower"
    # lender (fills every document)
    "lender_name": "",
    "lender_citizenship": "Filipino",
    "lender_civil_status": "",
    "lender_address": "",
    "place_of_signing": "",
    # output
    "language": "en",                # en, ceb, or both
    "output_dir": "output",
    "draft_banner_on": True,         # leave ON until a lawyer has actually approved the wording
}

NUMERIC_INT = ("max_months", "grace_days", "default_days", "notice_days")


def load():
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    return cfg


def save(cfg):
    clean = dict(DEFAULTS)
    clean.update(cfg)
    for k in NUMERIC_INT:
        clean[k] = int(clean[k])
        if clean[k] < 0 or (k == "max_months" and clean[k] < 1):
            raise ValueError(f"{k} must be a positive whole number")
    if clean["installment_rounding"] not in ("peso", "centavo"):
        raise ValueError("installment_rounding must be 'peso' or 'centavo'")
    if clean["dst_payer"] not in ("lender", "borrower"):
        raise ValueError("dst_payer must be 'lender' or 'borrower'")
    if clean["language"] not in ("en", "ceb", "both"):
        raise ValueError("language must be en, ceb or both")
    float(clean["default_annual_rate"]); float(clean["late_penalty_pct"])
    CONFIG_PATH.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    loan_calc.CONFIG.update({"max_months": clean["max_months"], "installment_rounding": clean["installment_rounding"]})
    return clean
