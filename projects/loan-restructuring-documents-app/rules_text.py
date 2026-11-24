"""ONE source for every rule sentence used by all documents, in English (en) and Cebuano (ceb).
Cebuano text is a DRAFT for review by a native speaker and the lawyer."""
from decimal import Decimal
import loan_calc as c

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "ceb": ["Enero", "Pebrero", "Marso", "Abril", "Mayo", "Hunyo", "Hulyo", "Agosto", "Septyembre", "Oktubre", "Nobyembre", "Disyembre"],
}
MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "ceb": ["Ene", "Peb", "Mar", "Abr", "May", "Hun", "Hul", "Ago", "Sep", "Okt", "Nob", "Dis"],
}


def fmt_date(d, lang, short=False):
    m = (MONTHS_SHORT if short else MONTHS)[lang][d.month - 1]
    return f"{m} {d.day}, {d.year}"


# ---------- amount in words ----------
_EN1 = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen Seventeen Eighteen Nineteen".split()
_EN10 = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def words_en(n):
    if n < 20: return _EN1[n]
    if n < 100: return _EN10[n // 10] + ("-" + _EN1[n % 10] if n % 10 else "")
    if n < 1000: return _EN1[n // 100] + " Hundred" + (" " + words_en(n % 100) if n % 100 else "")
    for div, name in ((10**9, "Billion"), (10**6, "Million"), (1000, "Thousand")):
        if n >= div:
            return words_en(n // div) + f" {name}" + (" " + words_en(n % div) if n % div else "")


_C1 = ["", "usa", "duha", "tulo", "upat", "lima", "unom", "pito", "walo", "siyam"]
_C10 = {1: "napulo", 2: "kawhaan", 3: "katloan", 4: "kap-atan", 5: "kalim-an", 6: "kaunom-an", 7: "kapitoan", 8: "kawaloan", 9: "kasiyaman"}


def words_ceb(n):
    """Cebuano numerals (draft; verify with a native speaker)."""
    if n == 0: return "zero"
    parts = []
    for div, name in ((10**9, "bilyon"), (10**6, "milyon"), (1000, "libo")):
        if n >= div:
            parts.append(f"{words_ceb(n // div)} ka {name}"); n %= div
    if n >= 100:
        parts.append(f"{_C1[n // 100]} ka gatos"); n %= 100
    if n:
        if n < 10: parts.append(_C1[n])
        elif 10 < n < 20: parts.append(f"napulog {_C1[n - 10]}")
        elif n % 10 == 0: parts.append(_C10[n // 10])
        else: parts.append(f"{_C10[n // 10]} ug {_C1[n % 10]}")
    return " ".join(parts)


def peso_words(x, lang):
    x = c.to_centavo(x); pesos = int(x); cents = int((x - pesos) * 100)
    if lang == "ceb":
        s = f"{words_ceb(pesos)} ka pesos".capitalize()
        return s + (f" ug {words_ceb(cents)} ka sentimos" if cents else " lamang")
    s = f"{words_en(pesos)} Pesos"
    return s + (f" and {cents:02d}/100" if cents else " Only")


def money(x):
    return f"{c.to_centavo(x):,.2f}"


def php(x):
    return f"PHP {money(x)}"


# ---------- rule sentences ----------
def rules(lang, annual_pct, monthly_pct, due_day, grace_days, penalty_pct):
    if lang == "ceb":
        return dict(
            rule_interest_method=(f"Ang interes gisingil sa takdang rate nga {annual_pct}% matag tuig, nga gisingil isip {monthly_pct}% "
                                  "matag bulan sa wala pa mabayri nga prinsipal sa sugod sa matag buwanang yugto, bisan pila ka adlaw ang bulan."),
            rule_rounding=("Ang interes sa matag bulan gikuwenta hangtod sa sentimo, nga gi-round pataas kon .50 pataas. Ang regular nga hulog "
                           "gi-round sa tibuok peso (50 sentimos pataas gi-round pataas). Ang kataposang hulog mao ang nabilin nga prinsipal "
                           "dugang ang interes niana nga bulan, busa mahimong mas gamay (o gamay nga mas dako) kini kay sa regular nga hulog."),
            rule_short_month=(f"Ang matag hulog bayranon sa adlaw {due_day} sa bulan. Kon mas mubo ang bulan, bayranon kini sa kataposang adlaw sa maong bulan."),
            rule_application=("Ang matag bayad nga madawat gigamit niini nga han-ay: una, ang multa sa paglangan (kon aduna); ikaduha, ang interes nga "
                              "angay nang bayran; ikatulo, ang prinsipal. Ang interes nga wala mabayri sa tukmang panahon gidala sa unahan isip "
                              "wala mabayri nga interes ug dili kini mag-interes."),
            rule_prepayment=("Ang Nangutang makabayad og labaw sa hulog, o mobayad sa tibuok, bisan kanus-a nga walay silot. Ang dugang nga kantidad "
                             "makapakunhod sa prinsipal sa petsa nga kini madawat, ug ang interes sa sunod nga mga bulan kuwentahon sa nikunhod nga "
                             "balanse. Ang gipirmahan nga talaan dili usbon; ang ledger sa Nagpautang magpakita sa kalainan."),
            rule_place_of_payment=("Ang mga bayad kolektahon personal sa adres sa Nangutang nga gilista sa ibabaw, o sa laing lugar nga gisabutan sa "
                                   "pagsulat, ug ang Nagpautang maghatag og resibo alang sa matag bayad."),
            rule_records=("Ang ledger sa Nagpautang sa mga bayad nga tinuod nga nadawat mao ang rekord sa mga bayad. Ang gilakip nga talaan mao ang "
                          "plano sa pagbayad. Kon ang aktuwal nga mga bayad lahi sa talaan, ang kalainan ipakita sa statement of account ug dili "
                          "kini mausab niini nga dokumento; ang bisan unsang pag-usab sa termino nagkinahanglan og bag-ong sinulat nga kasabutan "
                          "nga gipirmahan sa duha ka partido."),
            late_charge_text=(f"Kon ang usa ka hulog dili mabayran sulod sa {grace_days} ka adlaw human sa petsa nga angay kini bayran, ang Nangutang "
                              f"mobayad og multa nga {penalty_pct}% sa nalangan nga hulog matag bulan, o bahin sa bulan, nga dili kini mabayran. "
                              "Ang multa dugang sa interes, dili kini mag-interes, ug dili kini singilan og multa."),
        )
    return dict(
        rule_interest_method=(f"Interest is charged at a fixed rate of {annual_pct}% per year, applied as {monthly_pct}% per month on the unpaid "
                              "principal balance at the start of each monthly period, regardless of the number of days in the month."),
        rule_rounding=("Each month\u2019s interest is computed to the centavo, rounding half up. The regular installment is rounded to the whole "
                       "peso (50 centavos or more rounds up). The final installment is the remaining principal plus that month\u2019s interest, "
                       "so it may be smaller (or slightly larger) than the regular installment."),
        rule_short_month=(f"Each installment falls due on day {due_day} of the month. If a month has fewer days, it falls due on the last day of that month."),
        rule_application=("Each payment received is applied in this order: first, any late charge (if any); second, interest then due; third, "
                          "principal. Interest not paid when due is carried forward as unpaid interest and does not itself earn interest."),
        rule_prepayment=("The Borrower may pay more than the installment, or pay in full, at any time without penalty. Extra amounts reduce the "
                         "principal on the date received, and interest for later months is computed on the reduced balance. The signed schedule "
                         "is not rewritten; the Lender\u2019s ledger shows the difference."),
        rule_place_of_payment=("Payments are collected in person at the Borrower\u2019s address stated above, or at another place agreed in writing, "
                               "and the Lender gives a receipt for every payment."),
        rule_records=("The Lender\u2019s ledger of payments actually received is the record of payments. The attached schedule is the payment plan. "
                      "If actual payments differ from the schedule, the difference is shown in a statement of account and does not change this "
                      "document; any change in terms requires a new written agreement signed by both parties."),
        late_charge_text=(f"If an installment is not paid within {grace_days} days after its due date, the Borrower shall pay a late charge of "
                          f"{penalty_pct}% of the overdue installment for each month, or part of a month, that it stays unpaid. The late charge is "
                          "in addition to the interest, does not itself earn interest, and is not itself charged a late charge."),
    )
