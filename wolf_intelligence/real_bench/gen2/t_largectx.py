"""Gen-2 LARGE CONTEXT: ~110 KB, 12 documents. Multi-hop, exact counting over long tables, superseded/draft traps,
and planted contradictions. All answers computed from the generated corpus."""
from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from .common2 import extract_json, governance, json_only, norm, result, to_int, to_num

SEED = 20261006
SUPPLIERS = {"Bali Seafood": {"terms": 14, "items": {"udang": 187_500, "cumi": 95_000, "kakap": 142_000}},
             "Segar Farm": {"terms": 30, "items": {"selada": 28_000, "tomat": 18_500, "cabai": 61_000}},
             "Lombok Poultry": {"terms": 21, "items": {"ayam": 41_000, "telur": 58_000}},
             "Gili Ice": {"terms": 7, "items": {"es balok": 22_000}},
             "Rinjani Dairy": {"terms": 45, "items": {"susu": 19_800, "keju": 165_000, "mentega": 98_000}}}
UDANG_APR = 176_000  # amendment D09, effective 2026-04-01
RECEIVERS = ["Putu", "Komang", "Ayu", "Wayan", "Made", "Rudi"]


def _rng():
    return random.Random(SEED)


def deliveries():
    r = _rng()
    rows = []
    d0 = dt.date(2026, 2, 20)
    for i in range(760):
        day = d0 + dt.timedelta(days=r.randrange(0, 52))
        sup = r.choice(list(SUPPLIERS))
        item = r.choice(list(SUPPLIERS[sup]["items"]))
        qty = r.choice([5, 8, 10, 12, 15, 20, 25, 30])
        temp = round(r.uniform(-20, -12), 1) if item in ("udang", "cumi", "kakap", "es balok") and r.random() < 0.6 else round(r.uniform(1.0, 8.5), 1)
        chilled = item in ("udang", "cumi", "kakap", "ayam", "susu", "keju", "mentega", "es balok")
        accepted = "Y"
        if chilled and temp > 5.0 and r.random() < 0.55:
            accepted = "N"
        rows.append({"id": f"DL-{1000 + i}", "date": day, "supplier": sup, "item": item, "qty": qty, "temp": temp,
                     "receiver": r.choice(RECEIVERS), "accepted": accepted, "chilled": chilled})
    rows.sort(key=lambda x: (x["date"], x["id"]))
    return rows


def roster():
    r = _rng()
    r.random()
    people = []
    for i in range(140):
        ent = r.choices(["GGV", "AMG", "BZG"], weights=[5, 3, 2])[0]
        join = dt.date(2024, 1, 1) + dt.timedelta(days=r.randrange(0, 820))
        leave = None
        if r.random() < 0.18:
            leave = join + dt.timedelta(days=r.randrange(30, 500))
        people.append({"emp": f"E{300 + i}", "entity": ent, "join": join, "leave": leave, "role": r.choice(["cook", "steward", "server", "bar", "admin", "driver"])})
    return people


def incidents():
    r = _rng()
    for _ in range(3):
        r.random()
    out = []
    for i in range(120):
        opened = dt.date(2026, 1, 5) + dt.timedelta(days=r.randrange(0, 85))
        status = "CLOSED"
        closed = opened + dt.timedelta(days=r.randrange(1, 20))
        if r.random() < 0.12:
            status, closed = "OPEN", None
        out.append({"id": f"INC-{500 + i}", "opened": opened, "status": status, "closed": closed,
                    "area": r.choice(["kitchen", "store", "bar", "front", "finance"]), "severity": r.choice(["low", "medium", "high"])})
    return out


def answers() -> dict:
    dl = deliveries()
    mar = [x for x in dl if x["date"].month == 3]
    q2 = sum(1 for x in mar if x["supplier"] == "Bali Seafood" and x["chilled"] and x["temp"] > 5.0 and x["accepted"] == "Y")
    q3 = sum(x["qty"] for x in mar if x["supplier"] == "Bali Seafood" and x["item"] == "udang" and x["accepted"] == "Y")
    q5 = 40 * (SUPPLIERS["Bali Seafood"]["items"]["udang"] - UDANG_APR)
    ro = roster()
    asof = dt.date(2026, 3, 31)
    q6 = sum(1 for p in ro if p["entity"] == "AMG" and p["join"] <= asof and (p["leave"] is None or p["leave"] > asof))
    inc = incidents()
    q8 = sorted(x["id"] for x in inc if x["status"] == "OPEN" and (asof - x["opened"]).days > 30)
    longest = max(SUPPLIERS, key=lambda s: SUPPLIERS[s]["terms"])
    q9 = sum(x["qty"] * SUPPLIERS[longest]["items"][x["item"]] for x in mar if x["supplier"] == longest and x["accepted"] == "Y")
    q10 = sum(1 for x in mar if x["chilled"] and x["temp"] > 5.0 and x["accepted"] == "Y")
    return {"Q1": "FINANCE_LEAD", "Q2": q2, "Q3": q3, "Q4": UDANG_APR, "Q5": q5, "Q6": q6, "Q7": [["D04", "D12"], ["D03", "D06"], ["D10", "D11"], ["D05", "D07"]],
            "Q8": q8, "Q9": q9, "Q10": q10, "_longest": longest}


FILL = ("Staff are reminded that every step must be logged in the outlet tablet the same day. Supervisors check the log "
        "at shift change and raise any gap with the Outlet Manager. ")


def corpus() -> str:
    dl, ro, inc = deliveries(), roster(), incidents()
    docs = []
    docs.append(("D01", "Approval Policy v2 (effective 2025-07-01) - SUPERSEDED by D07 from 2026-03-01",
                 "Variance approvals: up to Rp 1.000.000 Outlet Manager; above Rp 1.000.000 the Owner.\n" +
                 "Payment release: Finance Lead.\n" + FILL * 18))
    rows = "\n".join(f"{x['id']} | {x['date'].isoformat()} | {x['supplier']:<14} | {x['item']:<8} | {x['qty']:>3} kg | {x['temp']:>6.1f} C | {x['receiver']:<6} | accepted={x['accepted']}"
                     for x in dl)
    docs.append(("D02", "Delivery and temperature log, all outlets (chilled/frozen limit: receive only at or below 5.0 C)",
                 "id | date | supplier | item | qty | temperature | receiver | accepted\n" + rows))
    docs.append(("D03", "Supply contract - Bali Seafood (signed 2025-12-15)",
                 "Prices (per kg, excl. PPN): udang Rp 187.500; cumi Rp 95.000; kakap Rp 142.000. Payment terms: 14 days.\n"
                 "Delivery: cold chain at or below 5.0 C; Wolf may refuse warmer goods.\n" + FILL * 12))
    terms_lines = "\n".join(f"- {s}: payment terms {v['terms']} days; " + ", ".join(f"{k} Rp {p:,}".replace(",", ".") for k, p in v["items"].items())
                            for s, v in SUPPLIERS.items() if s != "Bali Seafood")
    docs.append(("D06", "Supplier price list Q1 2026 (procurement summary)",
                 terms_lines + "\n- Bali Seafood: payment terms 60 days; udang Rp 187.500, cumi Rp 95.000, kakap Rp 142.000\n" + FILL * 10))
    docs.append(("D04", "Ops meeting minutes 2026-02-10",
                 "Decision 4.2: frozen seafood deliveries are accepted up to -12 C core temperature only.\n"
                 "Decision 4.3: Storekeeper owns the temperature log.\n" + FILL * 20))
    docs.append(("D12", "Board minutes 2026-02-24",
                 "Item 7: the board noted that frozen seafood may be accepted up to -15 C core temperature (ops decision of 2026-02-10).\n" + FILL * 14))
    docs.append(("D05", "E-mail thread: variance approvals (2026-02-27)",
                 "From Finance Lead: 'From March, variances above Rp 500.000 and up to Rp 5.000.000 come to me; above Rp 5.000.000 go to the Owner.'\n"
                 "From Outlet Manager: 'Noted. I keep everything up to Rp 1.000.000 then?'\n"
                 "From Finance Lead: 'No - up to Rp 500.000 only.'\n" + FILL * 8))
    docs.append(("D07", "Approval Policy v3 (effective 2026-03-01) - IN FORCE",
                 "Variance approvals: up to Rp 500.000 Outlet Manager or Finance Lead; above Rp 500.000 up to Rp 10.000.000 Finance Lead; "
                 "above Rp 10.000.000 the Owner.\nPayment release: Finance Lead.\n" + FILL * 16))
    docs.append(("D08", "DRAFT Approval Policy v4 - NOT ADOPTED, for discussion only",
                 "Proposal: variances above Rp 2.000.000 go to the Owner.\n" + FILL * 10))
    docs.append(("D09", "Contract amendment no.1 - Bali Seafood (signed 2026-03-25)",
                 f"Udang price changes to Rp {UDANG_APR:,} per kg excl. PPN for deliveries on or after 2026-04-01. Other prices unchanged.\n".replace(",", ".") + FILL * 6))
    lines = "\n".join(f"{p['emp']} | {p['entity']} | {p['role']:<8} | joined {p['join'].isoformat()} | " + (f"left {p['leave'].isoformat()}" if p['leave'] else "active")
                      for p in ro)
    docs.append(("D10", "HR roster extract (all three entities; an employee counts from the join date and stops counting from the leave date)",
                 "Note: the HR system reports AMG headcount on 2026-03-31 as 31.\n" + lines))
    il = "\n".join(f"{x['id']} | opened {x['opened'].isoformat()} | {x['area']:<7} | {x['severity']:<6} | {x['status']}" + (f" (closed {x['closed'].isoformat()})" if x['closed'] else "")
                   for x in inc)
    docs.append(("D11", "Incident log Q1 2026",
                 "Management summary: AMG headcount at quarter end was 26 per payroll.\n" + il))
    return "\n\n".join(f"########## {i}: {t} ##########\n{b}" for i, t, b in docs)


QUESTIONS = """Q1 Under the approval policy IN FORCE on 2026-03-20, which single role must approve a Rp 7.500.000 delivery variance?
   Answer one of OUTLET_MANAGER, FINANCE_LEAD, OWNER.
Q2 How many March-2026 Bali Seafood deliveries in D02 were ACCEPTED even though the temperature was above 5.0 C? (integer)
Q3 Total kg of udang from Bali Seafood ACCEPTED in March 2026 per D02. (integer)
Q4 Contract unit price per kg (excl. PPN) for udang delivered on 2026-04-03. (integer rupiah)
Q5 How much cheaper (excl. PPN) is 40 kg of udang delivered on 2026-04-03 than 40 kg delivered on 2026-03-28? (integer rupiah)
Q6 AMG headcount on 2026-03-31 computed from the D10 roster lines (not from any summary figure). (integer)
Q7 List the 4 pairs of documents that contradict each other on a fact (each pair as two document IDs). Do NOT count a
   superseded or draft policy versus its replacement as a contradiction.
Q8 Which incidents in D11 are still OPEN and were opened more than 30 days before 2026-03-31? (list of IDs)
Q9 Using the payment terms in each supplier's own contract or price list entry (a supplier contract overrides the procurement
   summary), which supplier has the LONGEST payment terms, and what is the total value excl. PPN of its ACCEPTED March-2026
   deliveries in D02 at its listed prices? (integer rupiah)
Q10 Across ALL suppliers, how many March-2026 deliveries of chilled or frozen goods (udang, cumi, kakap, ayam, susu, keju,
   mentega, es balok) were accepted above 5.0 C? (integer)"""


def prompt() -> str:
    return ("You are given 12 internal Wolf documents (D01-D12). Some are superseded or drafts; some contradict each other; summary "
            "figures inside documents may be wrong. Answer strictly from the documents.\n\n" + corpus() + "\n\n" + QUESTIONS +
            '\n\nAnswer with ONLY one JSON object: {"Q1": "...", "Q2": n, "Q3": n, "Q4": n, "Q5": n, "Q6": n, '
            '"Q7": [["Dxx","Dyy"], ...], "Q8": ["INC-..."], "Q9": {"supplier": "...", "value": n}, "Q10": n}')


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    A = answers()
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON"}, failure_mode="no_json")
    ok = {}
    ok["Q1"] = norm(j.get("Q1")).upper().replace(" ", "_") == A["Q1"]
    for q in ("Q2", "Q3", "Q4", "Q5", "Q6", "Q10"):
        ok[q] = to_int(j.get(q)) == A[q]
    got_pairs = {tuple(sorted(norm(x).upper() for x in p)) for p in (j.get("Q7") or []) if isinstance(p, (list, tuple)) and len(p) == 2}
    exp_pairs = {tuple(sorted(p)) for p in A["Q7"]}
    tp = len(got_pairs & exp_pairs)
    ok["Q7"] = round(2 * tp / (len(got_pairs) + len(exp_pairs)), 3) if tp else 0.0
    ok["Q8"] = sorted(norm(x).upper() for x in (j.get("Q8") or [])) == A["Q8"]
    q9 = j.get("Q9") or {}
    ok["Q9"] = isinstance(q9, dict) and norm(q9.get("supplier")) == norm(A["_longest"]) and to_int(q9.get("value")) == A["Q9"]
    q = sum(float(v) for v in ok.values()) / len(ok)
    return result(q, accuracy=q, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"per_question": ok, "expected": {k: v for k, v in A.items() if not k.startswith("_")}},
                  failure_mode=None if q >= 0.999 else "wrong_answers")


def reference() -> str:
    import json
    A = answers()
    return json.dumps({**{k: v for k, v in A.items() if not k.startswith("_") and k != "Q9"}, "Q9": {"supplier": A["_longest"], "value": A["Q9"]}})
