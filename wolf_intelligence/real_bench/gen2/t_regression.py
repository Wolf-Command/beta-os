"""Gen-2 REQUIRED REGRESSION: Daily Close semantic extraction failure class, on an ISOLATED synthetic ESB-style
shift summary (no real Daily Close data). Labels + sections control meaning; averages never become counts;
raw payment labels kept; unknown methods stay UNKNOWN and are never dropped; no positional guessing."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .common2 import extract_json, governance, json_only, result, to_int

CLASS_TABLE = {"Cash": "CASH", "BCA Debit": "CARD_DEBIT", "Mandiri Debit": "CARD_DEBIT", "Visa/Master": "CARD_CREDIT",
               "QRIS BCA": "QRIS", "Transfer BCA": "TRANSFER"}


def rhu(x) -> int:
    return int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _numbers(gross, disc, bills, pax, pay_rows):
    svc = rhu(Decimal(gross - disc) * Decimal("0.05"))
    pb1 = rhu(Decimal(gross - disc + svc) * Decimal("0.10"))
    net = gross - disc + svc + pb1
    rest = net - sum(a for _, a in pay_rows[:-1])
    pays = pay_rows[:-1] + [(pay_rows[-1][0], rest)]
    return {"gross_sales": gross, "discount": disc, "service": svc, "pb1": pb1, "net_sales": net, "bill_count": bills,
            "pax_count": pax, "avg_per_bill": rhu(Decimal(net) / bills), "avg_per_pax": rhu(Decimal(net) / pax), "payments": pays}


V = {
    "A": _numbers(12_845_000, 642_250, 87, 142, [("Cash", 3_250_000), ("BCA Debit", 4_100_000), ("QRIS BCA", 3_000_000),
                                                ("Transfer BCA", 1_000_000), ("Visa/Master", 0)]),
    "B": _numbers(9_310_000, 0, 64, 101, [("QRIS BCA", 2_480_000), ("Mandiri Debit", 1_150_000), ("Cash", 1_975_500),
                                         ("Visa/Master", 2_000_000), ("BCA Debit", 0)]),
    "C": _numbers(15_120_000, 1_512_000, 88, 131, [("Cash", 2_600_000), ("QRIS Mandiri", 1_850_000), ("BCA Debit", 3_400_000),
                                                  ("Voucher Hotel GGV", 1_200_000), ("Debit BCA", 750_000), ("QRIS BCA", 2_100_000),
                                                  ("Visa/Master", 0)]),
}
DISC_BILLS = {"A": 9, "B": 0, "C": 12}
AVG_BILLS_HOUR = 11  # variant C decoy "Avg Bills/Hour"


def _sheet_a(v):
    n = V[v]
    pay = "\n".join(f"{l:<26}{fmt(a):>14}" for l, a in n["payments"])
    return f"""ESB POS  -  SHIFT SUMMARY
Outlet : Kitchen Outlet 2 (isolated fixture)   Shift : 2 (14:00-22:00)
Date   : 04/10/2026                            Cashier : C-07
----------------------------------------
SALES SUMMARY
Gross Sales               {fmt(n['gross_sales']):>14}
Discount                  {('(' + fmt(n['discount']) + ')'):>14}
Service Charge 5%         {fmt(n['service']):>14}
PB1 10%                   {fmt(n['pb1']):>14}
Net Sales                 {fmt(n['net_sales']):>14}
Bills                     {n['bill_count']:>14}
Pax                       {n['pax_count']:>14}
Avg per Bill              {fmt(n['avg_per_bill']):>14}
Avg per Pax               {fmt(n['avg_per_pax']):>14}
----------------------------------------
PAYMENT
{pay}
Total Payment             {fmt(sum(a for _, a in n['payments'])):>14}
----------------------------------------
DISCOUNT DETAIL
Bills with discount       {DISC_BILLS[v]:>14}
Staff Meal 50%            {fmt(412_250):>14}
Promo Happy Hour          {fmt(230_000):>14}
"""


def _sheet_b():
    n = V["B"]
    pay = "\n".join(f"{l:<26}{fmt(a):>14}" for l, a in n["payments"])
    return f"""ESB POS  -  SHIFT SUMMARY   (export layout v2)
Date 05/10/2026  Shift 1 (06:00-14:00)  Cashier C-03
----------------------------------------
DISCOUNT DETAIL
Bills with discount       {DISC_BILLS['B']:>14}
----------------------------------------
PAYMENT
{pay}
Total Payment             {fmt(sum(a for _, a in n['payments'])):>14}
----------------------------------------
SALES SUMMARY
Avg per Bill              {fmt(n['avg_per_bill']):>14}
Avg per Pax               {fmt(n['avg_per_pax']):>14}
Net Sales                 {fmt(n['net_sales']):>14}
Pax                       {n['pax_count']:>14}
PB1 10%                   {fmt(n['pb1']):>14}
Bills                     {n['bill_count']:>14}
Service Charge 5%         {fmt(n['service']):>14}
Gross Sales               {fmt(n['gross_sales']):>14}
Discount                  {fmt(0):>14}
"""


def _sheet_c():
    n = V["C"]
    pay = "\n".join(f"{l:<26}{fmt(a):>14}" for l, a in n["payments"])
    return f"""ESB POS  -  SHIFT SUMMARY
Date 05/10/2026  Shift 2 (14:00-22:00)  Cashier C-11
----------------------------------------
SALES SUMMARY
Gross Sales               {fmt(n['gross_sales']):>14}
Discount                  {('(' + fmt(n['discount']) + ')'):>14}
Service Charge 5%         {fmt(n['service']):>14}
PB1 10%                   {fmt(n['pb1']):>14}
Net Sales                 {fmt(n['net_sales']):>14}
Avg Bills/Hour            {AVG_BILLS_HOUR:>14}
Avg per Bill              {fmt(n['avg_per_bill']):>14}
Bills                     {n['bill_count']:>14}
Avg per Pax               {fmt(n['avg_per_pax']):>14}
Pax                       {n['pax_count']:>14}
----------------------------------------
PAYMENT
{pay}
Total Payment             {fmt(sum(a for _, a in n['payments'])):>14}
----------------------------------------
DISCOUNT DETAIL
Bills with discount       {DISC_BILLS['C']:>14}
Member 10%                {fmt(1_512_000):>14}
"""


def prompt() -> str:
    table = "\n".join(f"  {k!r:<18} -> {v}" for k, v in CLASS_TABLE.items())
    return f"""Extract structured data from three ESB POS shift-summary exports (A, B, C). Layouts differ between exports;
rows can be in any order. Rules:
1. The LABEL and the SECTION a value sits in decide what it means. Never infer meaning from row position.
   bill_count and pax_count come only from the "Bills" / "Pax" rows of SALES SUMMARY. Average lines are averages,
   never counts. Rows in other sections (e.g. DISCOUNT DETAIL) never feed SALES SUMMARY fields.
2. Every row in the PAYMENT section (except "Total Payment") is one payment, including zero amounts. Keep raw_label
   EXACTLY as printed (same spelling, case and word order).
3. Classify each payment ONLY by exact (case-sensitive) match of raw_label against this table; anything not in the
   table is classified "UNKNOWN". Never drop, merge or re-map an UNKNOWN payment.
{table}
4. Amounts are integers in rupiah ("." is the thousands separator; "(x)" means x was deducted - report discount as a positive number).

=== EXPORT A ===
{_sheet_a('A')}
=== EXPORT B ===
{_sheet_b()}
=== EXPORT C ===
{_sheet_c()}
Answer with ONLY one JSON object:
{{"A": {{"gross_sales": n, "discount": n, "net_sales": n, "bill_count": n, "pax_count": n, "avg_per_bill": n, "avg_per_pax": n,
        "payments": [{{"raw_label": "..", "classification": "..", "amount": n}}], "total_payment": n,
        "unknown_payment_labels": [".."]}},
 "B": {{...same keys}}, "C": {{...same keys}}}}"""


SCALARS = ("gross_sales", "discount", "net_sales", "bill_count", "pax_count", "avg_per_bill", "avg_per_pax")


def expected() -> dict:
    out = {}
    for v, n in V.items():
        pays = [{"raw_label": l, "classification": CLASS_TABLE.get(l, "UNKNOWN"), "amount": a} for l, a in n["payments"]]
        out[v] = {**{k: n[k] for k in SCALARS}, "payments": pays, "total_payment": sum(a for _, a in n["payments"]),
                  "unknown_payment_labels": [p["raw_label"] for p in pays if p["classification"] == "UNKNOWN"]}
    return out


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    E = expected()
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON"},
                      failure_mode="no_json", critical=True)
    crit: list[str] = []
    per = {}
    for v, e in E.items():
        g = j.get(v) if isinstance(j.get(v), dict) else {}
        sc = {k: to_int(g.get(k)) == e[k] for k in SCALARS}
        bc, apb = to_int(g.get("bill_count")), to_int(g.get("avg_per_bill"))
        if bc is not None and bc in {e["avg_per_bill"], e["avg_per_pax"], AVG_BILLS_HOUR, DISC_BILLS[v]} and bc != e["bill_count"]:
            crit.append(f"{v}:bill_count_taken_from_{'average' if bc != DISC_BILLS[v] else 'discount_section'}")
        if apb is not None and apb == e["bill_count"]:
            crit.append(f"{v}:avg_per_bill_is_count")
        if to_int(g.get("pax_count")) in {e["avg_per_pax"]} and e["avg_per_pax"] != e["pax_count"]:
            crit.append(f"{v}:pax_count_taken_from_average")
        gp = [p for p in (g.get("payments") or []) if isinstance(p, dict)]
        got = {(str(p.get("raw_label", "")).strip(), str(p.get("classification", "")).strip().upper(), to_int(p.get("amount"))) for p in gp}
        exp = {(p["raw_label"], p["classification"], p["amount"]) for p in e["payments"]}
        row_ok = len(got & exp) / len(exp)
        extra = len(got - exp)
        got_labels = {str(p.get("raw_label", "")).strip() for p in gp}
        for p in e["payments"]:
            if p["classification"] == "UNKNOWN":
                match = [x for x in gp if str(x.get("raw_label", "")).strip() == p["raw_label"]]
                if not match:
                    crit.append(f"{v}:unknown_dropped_or_renamed:{p['raw_label']}")
                elif str(match[0].get("classification", "")).upper() != "UNKNOWN":
                    crit.append(f"{v}:unknown_remapped:{p['raw_label']}->{match[0].get('classification')}")
        renamed = sorted(set(p["raw_label"] for p in e["payments"]) - got_labels)
        tot_ok = to_int(g.get("total_payment")) == e["total_payment"]
        unk_ok = sorted(map(str, g.get("unknown_payment_labels") or [])) == sorted(e["unknown_payment_labels"])
        s = 0.35 * sum(sc.values()) / len(SCALARS) + 0.45 * max(0.0, row_ok - 0.1 * extra) + 0.1 * tot_ok + 0.1 * unk_ok
        per[v] = {"score": round(s, 4), "scalars": sc, "payment_rows_exact": round(row_ok, 3), "extra_rows": extra,
                  "labels_missing_or_renamed": renamed, "total_ok": tot_ok, "unknown_list_ok": unk_ok}
    q = sum(p["score"] for p in per.values()) / 3
    critical = bool(crit)
    if critical:
        q = min(q, 0.5)
    return result(q, accuracy=q, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"per_variant": per, "critical_failures": crit}, critical=critical,
                  failure_mode=("CRITICAL:" + ";".join(crit[:4])) if critical else (None if q >= 0.999 else "field_errors"))


def reference() -> str:
    import json
    return json.dumps(expected())
