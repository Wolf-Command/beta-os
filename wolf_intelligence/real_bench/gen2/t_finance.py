"""Gen-2 FINANCE: GGV/AMG/BZG multi-entity allocation, PPN, intercompany netting, two bank recs, controls.
Expected answers are computed from the data below, never hand-typed."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

from .common2 import extract_json, governance, json_only, norm, result, to_int

ENT = ("GGV", "AMG", "BZG")
KEYS = {"K_ELEC": {"GGV": 50, "AMG": 30, "BZG": 20}, "K_HEAD": {"GGV": 18, "AMG": 9, "BZG": 3},
        "K_SQM": {"GGV": 400, "AMG": 250, "BZG": 150}}
# id, date, paid_by, supplier, supplier_invoice_no, addressed_to, amount_field, ppn_mode, allocation, requester, approver
REG = [
    ("T01", "2026-09-02", "GGV", "PLN", "PLN-0926-311", "GGV", 18_870_000, "none", "K_ELEC", "Rudi", "Dewi"),
    ("T02", "2026-09-03", "GGV", "Dapur Sasak", "INV-DS-0912", "GGV", 6_660_000, "inclusive", "K_HEAD", "Rudi", ""),
    ("T03", "2026-09-05", "AMG", "Telkom", "TLK-889120", "AMG", 2_500_000, "exclusive", "K_SQM", "Ayu", "Made"),
    ("T04", "2026-09-06", "BZG", "Pertamina Marine", "PM-55102", "BZG", 4_200_000, "none", "BZG", "Komang", ""),
    ("T05", "2026-09-09", "GGV", "CV Lombok Linen", "LL-2026-140", "AMG", 12_000_000, "exclusive", "AMG", "Rudi", "Dewi"),
    ("T06", "2026-09-11", "AMG", "Bali Seafood", "BS-77311", "AMG", 15_540_000, "inclusive", "AMG", "Ayu", ""),
    ("T07", "2026-09-30", "GGV", "PT Satpam Nusa", "SN-0930", "GGV", 9_990_000, "inclusive", "K_SQM", "Rudi", ""),
    ("T08", "2026-09-16", "GGV", "Dapur Sasak", "INV-DS-0912", "GGV", 6_660_000, "inclusive", "K_HEAD", "Rudi", ""),
    ("T09", "2026-09-18", "BZG", "Gili Water", "GW-1188", "BZG", 1_110_000, "inclusive", "K_HEAD", "Komang", ""),
    ("T10", "2026-09-20", "AMG", "Xero", "XR-20260920", "AMG", 1_800_000, "exclusive", "K_HEAD", "Made", "Made"),
    ("T11", "2026-09-22", "GGV", "CV Lombok Linen", "LL-2026-151", "BZG", 3_330_000, "inclusive", "GGV", "Rudi", ""),
    ("T12", "2026-09-25", "BZG", "PT Satpam Nusa", "SN-0925", "BZG", 2_220_000, "inclusive", "BZG", "Komang", ""),
]
THRESH = 10_000_000


def rhu(x: Decimal) -> int:
    return int(x.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def gross_ppn(amount: int, mode: str) -> tuple[int, int]:
    if mode == "inclusive":
        dpp = rhu(Decimal(amount) * 100 / 111)
        return amount, amount - dpp
    if mode == "exclusive":
        ppn = rhu(Decimal(amount) * Decimal("0.11"))
        return amount + ppn, ppn
    return amount, 0


def allocate(total: int, alloc: str) -> dict[str, int]:
    if alloc in ENT:
        return {e: (total if e == alloc else 0) for e in ENT}
    w = KEYS[alloc]
    s = sum(w.values())
    shares = {e: (total * w[e]) // s for e in ENT}
    big = max(ENT, key=lambda e: (w[e], -ENT.index(e)))
    shares[big] += total - sum(shares.values())
    return shares


def duplicates() -> list[str]:
    seen, dup = set(), []
    for r in sorted(REG, key=lambda r: (r[1], r[0])):
        k = (r[3], r[4])
        if k in seen:
            dup.append(r[0])
        seen.add(k)
    return dup


# Book cash ledgers and bank statements (Sept 2026)
GGV_BOOK_OPEN, GGV_BANK_OPEN = 250_000_000, 250_000_000
AMG_BOOK_OPEN, AMG_BANK_OPEN = 120_000_000, 120_000_000


def _gross(tid: str) -> int:
    r = next(x for x in REG if x[0] == tid)
    return gross_ppn(r[6], r[7])[0]


def ledgers():
    ggv_book = [("R-GGV-0915", "Room revenue deposit", 60_000_000)] + [(t, "Payment " + t, -_gross(t)) for t in ("T01", "T02", "T05", "T07", "T08", "T11")] + [("R-GGV-0930", "Room revenue deposit", 25_000_000)]
    ggv_bank = [("R-GGV-0915", "CR transfer", 60_000_000)] + [(t, "DB transfer " + t, -_gross(t)) for t in ("T01", "T02", "T05", "T11")] + [("FEE-0930", "Biaya admin", -15_000)]
    t03_wrong = -(_gross("T03") - 18_000)  # booked 2.757.000 instead of 2.775.000 (transposition)
    amg_book = [("R-AMG-0910", "Restaurant takings", 40_000_000), ("T03", "Payment T03", t03_wrong)] + [(t, "Payment " + t, -_gross(t)) for t in ("T06", "T10")]
    amg_bank = [("R-AMG-0910", "CR setoran", 40_000_000), ("T03", "DB Telkom", -_gross("T03")), ("T10", "DB Xero", -_gross("T10")),
                ("INT-0930", "Bunga", 42_500), ("FEE-0930", "Biaya admin", -10_000)]
    return ggv_book, ggv_bank, amg_book, amg_bank


def expected() -> dict:
    dup = set(duplicates())
    exp = {e: 0 for e in ENT}
    ppn_claim = {e: 0 for e in ENT}
    ic: dict[tuple[str, str], int] = {}
    for r in REG:
        if r[0] in dup:
            continue
        g, p = gross_ppn(r[6], r[7])
        sh = allocate(g, r[8])
        for e in ENT:
            exp[e] += sh[e]
            if e != r[2] and sh[e]:
                ic[(e, r[2])] = ic.get((e, r[2]), 0) + sh[e]
        ppn_claim[r[5]] += p
    net = []
    for a, b in [("AMG", "GGV"), ("BZG", "GGV"), ("BZG", "AMG")]:
        v = ic.get((a, b), 0) - ic.get((b, a), 0)
        if v > 0:
            net.append({"debtor": a, "creditor": b, "amount": v})
        elif v < 0:
            net.append({"debtor": b, "creditor": a, "amount": -v})
    gb, gk, ab, ak = ledgers()
    ggv_book_close = GGV_BOOK_OPEN + sum(x[2] for x in gb)
    ggv_bank_close = GGV_BANK_OPEN + sum(x[2] for x in gk)
    amg_book_close = AMG_BOOK_OPEN + sum(x[2] for x in ab)
    amg_bank_close = AMG_BANK_OPEN + sum(x[2] for x in ak)
    ggv_adj = ggv_book_close - 15_000 + _gross("T08")
    assert ggv_adj == ggv_bank_close - _gross("T07") + 25_000_000, "GGV rec must tie"
    amg_adj = amg_book_close + 42_500 - 10_000 - 18_000
    assert amg_adj == amg_bank_close - _gross("T06"), "AMG rec must tie"
    exc = []
    for r in REG:
        if r[0] in dup:
            exc.append((r[0], "DUPLICATE"))
            continue
        g = gross_ppn(r[6], r[7])[0]
        if g >= THRESH and not r[10]:
            exc.append((r[0], "NO_APPROVAL"))
        if r[10] and r[10] == r[9]:
            exc.append((r[0], "SELF_APPROVAL"))
        if allocate(100, r[8])[r[5]] == 0:
            exc.append((r[0], "WRONG_ENTITY"))
    return {"excluded_duplicates": sorted(dup), "expense_gross_by_entity": exp, "input_ppn_claimable_by_entity": ppn_claim,
            "intercompany_net": net,
            "bank_rec": {"GGV": {"book_closing": ggv_book_close, "bank_closing": ggv_bank_close, "adjusted_balance": ggv_adj,
                                 "outstanding_payments": ["T07"], "deposits_in_transit": ["R-GGV-0930"],
                                 "unbooked_bank_items": {"FEE-0930": -15_000}, "book_errors": {"T08": _gross("T08")}},
                         "AMG": {"book_closing": amg_book_close, "bank_closing": amg_bank_close, "adjusted_balance": amg_adj,
                                 "outstanding_payments": ["T06"], "deposits_in_transit": [],
                                 "unbooked_bank_items": {"INT-0930": 42_500, "FEE-0930": -10_000}, "book_errors": {"T03": -18_000}}},
            "control_exceptions": sorted(exc)}


def _fmt(n: int) -> str:
    s = f"{abs(n):,}".replace(",", ".")
    return ("-" if n < 0 else "") + s


def prompt() -> str:
    reg = "\n".join(" | ".join([r[0], r[1], r[2], r[3], r[4], r[5], _fmt(r[6]), r[7], r[8], r[9], r[10] or "-"]) for r in REG)
    gb, gk, ab, ak = ledgers()
    led = lambda rows: "\n".join(f"  {a:<11} {b:<22} {_fmt(c):>14}" for a, b, c in rows)
    return f"""Month-end close, September 2026, for three separate legal entities: GGV, AMG and BZG. They must never be
blended: every figure is per entity. All amounts are Indonesian Rupiah ("." = thousands separator). Analysis only:
you are not approving or paying anything.

RULES
R1 PPN rate 11%. ppn_mode "inclusive": the amount INCLUDES PPN; DPP = round_half_up(amount x 100/111), PPN = amount - DPP,
   gross = amount. "exclusive": the amount is DPP; PPN = round_half_up(DPP x 11%), gross = DPP + PPN. "none": gross = amount, PPN 0.
R2 Allocation: the gross amount is borne by the entity named in `allocation`, or split by the allocation key.
   Keys (weights): K_ELEC GGV 50 / AMG 30 / BZG 20; K_HEAD headcount GGV 18 / AMG 9 / BZG 3; K_SQM floor m2 GGV 400 / AMG 250 / BZG 150.
   Each share = floor(gross x weight / total weight) in whole rupiah; the rounding remainder goes to the entity with the largest weight.
R3 Input PPN is claimable ONLY by the entity named in `addressed_to` (the name on the tax invoice), for that invoice's full PPN,
   regardless of allocation.
R4 Intercompany: the paying entity (`paid_by`) is owed each OTHER entity's allocated gross share. Net PAIRWISE only
   (no multilateral netting); report each pair once, in the direction of the net debt, omit zero pairs.
R5 Duplicates: if the same supplier + supplier_invoice_no appears more than once, the LATER-dated row is a duplicate. Exclude it
   from R1-R4 and report it. All other rows, including those with control exceptions, are calculated exactly as booked.
R6 Control exceptions: NO_APPROVAL = gross >= 10.000.000 with no approver; SELF_APPROVAL = approver is the requester (any amount);
   WRONG_ENTITY = the entity named in addressed_to bears 0% of the cost under the booked allocation; DUPLICATE per R5.

PAYMENT REGISTER
id | date | paid_by | supplier | supplier_invoice_no | addressed_to | amount | ppn_mode | allocation | requester | approver
{reg}

GGV book cash ledger (opening {_fmt(GGV_BOOK_OPEN)}):
{led(gb)}
GGV bank statement BCA (opening {_fmt(GGV_BANK_OPEN)}):
{led(gk)}
AMG book cash ledger (opening {_fmt(AMG_BOOK_OPEN)}):
{led(ab)}
AMG bank statement BCA (opening {_fmt(AMG_BANK_OPEN)}):
{led(ak)}
(Bank recs: items on the statement but not in the book are unbooked bank items; payments/deposits in the book not yet on the
statement are outstanding payments / deposits in transit; a book entry that is wrong is a book error, reported as the correction
to the BOOK balance (positive increases the book balance). adjusted_balance = corrected book balance = bank balance adjusted for
outstanding items; they must agree.)

Answer with ONLY one JSON object, integers in rupiah (no separators):
{{"excluded_duplicates": [ids],
 "expense_gross_by_entity": {{"GGV": n, "AMG": n, "BZG": n}},
 "input_ppn_claimable_by_entity": {{"GGV": n, "AMG": n, "BZG": n}},
 "intercompany_net": [{{"debtor": "..", "creditor": "..", "amount": n}}],
 "bank_rec": {{"GGV": {{"book_closing": n, "bank_closing": n, "adjusted_balance": n, "outstanding_payments": [refs],
                      "deposits_in_transit": [refs], "unbooked_bank_items": {{"ref": signed n}}, "book_errors": {{"ref": signed correction}}}},
             "AMG": {{same keys}}}},
 "control_exceptions": [["id", "TYPE"], ...]}}"""


PROMPT = None  # built lazily via prompt()


def _eq_map(got: dict, exp: dict) -> float:
    if not isinstance(got, dict):
        return 0.0
    g = {str(k).strip().upper(): to_int(v) for k, v in got.items()}
    return sum(1 for k, v in exp.items() if g.get(str(k).upper()) == v) / max(1, len(exp)) if exp else (1.0 if not g or all(v == 0 for v in g.values()) else 0.0)


def _rec_score(g: dict, e: dict) -> float:
    parts = [to_int(g.get(k)) == e[k] for k in ("book_closing", "bank_closing", "adjusted_balance")]
    parts.append(sorted(norm(x).upper() for x in (g.get("outstanding_payments") or [])) == e["outstanding_payments"])
    parts.append(sorted(norm(x).upper() for x in (g.get("deposits_in_transit") or [])) == e["deposits_in_transit"])
    ub, be = g.get("unbooked_bank_items") or {}, g.get("book_errors") or {}
    parts.append(_eq_map(ub, e["unbooked_bank_items"]) == 1.0 and len(ub) == len(e["unbooked_bank_items"]))
    parts.append((not be and not e["book_errors"]) or (_eq_map(be, e["book_errors"]) == 1.0 and len(be) == len(e["book_errors"])))
    return sum(parts) / len(parts)


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    E = expected()
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON"}, failure_mode="no_json")
    d = {}
    d["duplicates"] = sorted(norm(x).upper() for x in (j.get("excluded_duplicates") or [])) == E["excluded_duplicates"]
    d["expense"] = _eq_map(j.get("expense_gross_by_entity"), E["expense_gross_by_entity"])
    d["ppn"] = _eq_map(j.get("input_ppn_claimable_by_entity"), E["input_ppn_claimable_by_entity"])
    got_ic = {(norm(x.get("debtor")).upper(), norm(x.get("creditor")).upper()): to_int(x.get("amount"))
              for x in (j.get("intercompany_net") or []) if isinstance(x, dict)}
    exp_ic = {(x["debtor"], x["creditor"]): x["amount"] for x in E["intercompany_net"]}
    d["intercompany"] = (sum(1 for k, v in exp_ic.items() if got_ic.get(k) == v) / len(exp_ic)) * (1.0 if set(got_ic) == set(exp_ic) else 0.5)
    br = j.get("bank_rec") or {}
    rec_scores = {}
    # Grader 2.1: the brief does not state whether the bank paid the duplicate T08 once or not at all, so two
    # internally consistent GGV treatments are accepted: (A) T08 = book error (+gross), or (B) T08 = outstanding payment.
    alt = json.loads(json.dumps(E["bank_rec"]["GGV"]))
    alt.update({"adjusted_balance": E["bank_rec"]["GGV"]["adjusted_balance"] - _gross("T08"),
                "outstanding_payments": sorted(["T07", "T08"]), "book_errors": {}})
    for ent in ("GGV", "AMG"):
        g = br.get(ent) or {}
        cands = [E["bank_rec"][ent]] + ([alt] if ent == "GGV" else [])
        best = 0.0
        for e in cands:
            best = max(best, _rec_score(g, e))
        rec_scores[ent] = best
    d["bank_rec"] = rec_scores
    got_exc = set()
    for x in (j.get("control_exceptions") or []):
        if isinstance(x, (list, tuple)) and len(x) >= 2:
            got_exc.add((norm(x[0]).upper(), norm(x[1]).upper()))
        elif isinstance(x, dict):
            got_exc.add((norm(x.get("id")).upper(), norm(x.get("type")).upper()))
    exp_exc = set(E["control_exceptions"])
    tp = len(got_exc & exp_exc)
    prec = tp / len(got_exc) if got_exc else 0.0
    rec = tp / len(exp_exc)
    d["exceptions_f1"] = round(2 * prec * rec / (prec + rec), 3) if tp else 0.0
    d["exceptions_missed"] = sorted(map(list, exp_exc - got_exc))
    d["exceptions_extra"] = sorted(map(list, got_exc - exp_exc))
    q = (0.05 * d["duplicates"] + 0.2 * d["expense"] + 0.15 * d["ppn"] + 0.2 * d["intercompany"]
         + 0.125 * rec_scores["GGV"] + 0.125 * rec_scores["AMG"] + 0.15 * d["exceptions_f1"])
    return result(q, accuracy=q, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details=d, failure_mode=None if q >= 0.999 else "numeric_or_control_errors")


def reference() -> str:
    E = expected()
    E = json.loads(json.dumps(E))
    return json.dumps(E)
