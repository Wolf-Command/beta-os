"""UX, large-context, vision, extraction, planning tasks."""
from __future__ import annotations

import random
import re
import textwrap
from datetime import date, timedelta
from pathlib import Path

from .common import extract_json, governance, json_only, result, to_int

# ----------------------------------------------------------------------------- UX (rubric, blind cross-review)
UX_PROMPT = textwrap.dedent('''
Design the phone flow a bar staff member uses to close their shift at AMG Senggigi (a Wolf group venue).
It covers: cash count, card (EDC) and QRIS totals, tips, the cash variance, and handover to the next shift.

Constraints:
- Staff use cheap Android phones; Wi-Fi in the back office drops often.
- Staff read English or Bahasa Indonesia; the flow must support both.
- The whole close must take a trained staff member <= 3 minutes.
- A cash variance larger than Rp 50.000 (either direction) needs the duty manager's sign-off before the shift can close.
- Once a count is submitted the staff member must never be able to edit it; corrections must leave an audit trail.
- The Owner only wants to see exceptions, not every shift.

Deliver: (1) numbered screens (maximum 8) with the fields on each; (2) the exact variance-warning microcopy in
English AND Bahasa Indonesia; (3) offline / failure handling; (4) exactly what reaches the Owner and when.
Be concrete and concise (under 700 words).
''').strip()

UX_RUBRIC = [
    ("screens_time", "At most 8 numbered screens with concrete fields; plausibly completable in <= 3 minutes."),
    ("offline", "Concrete offline/patchy Wi-Fi handling (local save, queued sync, no double submit, clear status)."),
    ("variance_gate", "Variance > Rp 50.000 either direction correctly forces duty-manager sign-off before close."),
    ("immutability", "Submitted counts are immutable; corrections create a new audited entry, not an edit."),
    ("bilingual", "Exact variance-warning microcopy present in both English and natural Bahasa Indonesia."),
    ("owner_exceptions", "Owner sees exceptions only (what triggers it, when, which channel), not every shift."),
]


def ux_review_prompt(candidates: list[tuple[str, str]]) -> str:
    rub = "\n".join(f"- {k}: {d} (score 0, 1 or 2)" for k, d in UX_RUBRIC)
    body = "\n\n".join(f"=== CANDIDATE {label} ===\n{txt[:6000]}" for label, txt in candidates)
    keys = ", ".join(f'"{k}": int' for k, _ in UX_RUBRIC)
    return (
        "You are a strict, impartial product reviewer. Score each anonymous candidate answer to the design brief below "
        "against the rubric. Judge only what is written. Do not guess who wrote it.\n\nBRIEF:\n" + UX_PROMPT +
        "\n\nRUBRIC (each criterion 0, 1 or 2):\n" + rub + "\n\n" + body +
        '\n\nAnswer with ONLY a JSON object: {"scores": {"<label>": {' + keys + ', "comment": str}}}'
    )


def grade_ux_precheck(text: str) -> dict:
    g_ok, g_note = governance(text)
    has_id = bool(re.search(r"(?i)selisih|melebihi|wajib|tanda tangan|persetujuan|manajer", text or ""))
    has_50 = bool(re.search(r"50[\.,]?000|50k|50rb|50 ?ribu", text or "", re.I))
    words = len((text or "").split())
    return {"bahasa_present": has_id, "threshold_present": has_50, "words": words, "governance_ok": g_ok, "governance_note": g_note}


# ----------------------------------------------------------------------------- LARGE CONTEXT
_FILLER_TOPICS = [
    ("Bar inventory count", ["Bintang 620ml", "Arak Bali 1L", "Lime crate", "Soda water 24", "Ice 10kg bag", "Coconut", "Gin 700ml"]),
    ("Kitchen prep notes", ["sambal matah", "nasi goreng base", "satay marinade", "gado-gado dressing", "fish curry paste"]),
    ("Maintenance log", ["aircon unit 3", "pool pump", "bar fridge seal", "speaker cable", "toilet flush valve", "roller door"]),
    ("Guest feedback digest", ["slow drinks at sunset", "great staff", "music too loud", "wifi weak by pool", "loved the sambal"]),
]


def _filler(rng: random.Random, n_paras: int) -> str:
    out = []
    for _ in range(n_paras):
        topic, items = rng.choice(_FILLER_TOPICS)
        d = date(2026, 8, 1) + timedelta(days=rng.randint(0, 58))
        lines = [f"{topic} — {d.strftime('%d %b %Y')} (shift {rng.choice(['AM', 'PM', 'late'])})"]
        for _ in range(rng.randint(4, 7)):
            it = rng.choice(items)
            lines.append(f"  - {it}: {rng.choice(['checked', 'low', 'ok', 'reordered', 'flagged', 'cleaned', 'replaced'])}; "
                         f"qty {rng.randint(1, 48)}; noted by {rng.choice(['Putu', 'Wayan', 'Ketut', 'Nyoman', 'Kadek', 'Sari', 'Rizal'])}")
        out.append("\n".join(lines))
    return "\n\n".join(out)


def build_large_context(seed: int = 20261006) -> tuple[str, dict]:
    rng = random.Random(seed)
    docs = []
    planted = {
        1: "POLICY: Purchasing authority (v2, effective 1 Jul 2026). Any single purchase above Rp 2.500.000 requires written Owner approval before the order is placed. Splitting one purchase into smaller orders to stay under the limit is a disciplinary matter.",
        2: "SOP v3 (issued 4 Aug 2026), Kitchen & staff: the kitchen opens at 10:00 daily. Staff meal allowance is Rp 35.000 per shift worked, paid via the weekly payroll, not from the till.",
        3: "VENDOR CONTRACT SUMMARY — PT Dingin Jaya Teknik, walk-in chiller service. Term 12 months. Renewal date: 14 November 2026. Notice to cancel: 30 days before renewal. Call-out fee waived for in-contract visits.",
        4: "LEASE NOTE — Senggigi venue. Landlord: Ibu Ratna. Security deposit held by landlord: Rp 45.000.000. Lease renewal discussion scheduled for Q1 2027.",
        5: "EMAIL 22 Sep 2026, from GM Senggigi to managers: 'From 1 October our ice comes from PT Es Kristal Lombok — the old supplier is out. Also, to keep things moving, anything under Rp 5.000.000 I can approve myself, no need to bother the Owner.'",
        6: "MEETING NOTES 28 Sep 2026 (managers' weekly). Decisions: (a) from 1 Oct the kitchen opens at 11:00 because lunch covers before 11 are too low; (b) the second key to the office safe is held by Made Wirawan (night manager) — the previous holder returned his key.",
        7: "FACILITIES SCHEDULE: backup generator load test every second Tuesday of the month, 07:00, logged in the maintenance book.",
        8: "FINANCE MEMO (Sep close): balance sheet items to confirm — Senggigi lease security deposit Rp 54.000.000 (per landlord receipt on file); VAT payable; staff advances.",
    }
    for i in range(1, 9):
        head = f"##### DOCUMENT {i} of 8 #####"
        pre = _filler(rng, rng.randint(9, 12))
        post = _filler(rng, rng.randint(9, 12))
        docs.append(f"{head}\n{pre}\n\n{planted[i]}\n\n{post}")
    pack = "\n\n".join(docs)
    expected = {
        "q1": [r"14\s*nov"], "q2": [r"kristal"], "q3": [r"35[\.,]?000|35\s?rb|35k"], "q4": [r"wirawan"],
        "q5": [r"2[\.,]?500[\.,]?000|2[\.,]5\s?(juta|million|m\b)"], "q6": [r"second tuesday|2nd tuesday"],
    }
    return pack, expected


LC_QUESTIONS = textwrap.dedent('''
Questions (answer from the documents only):
q1. When does the walk-in chiller service contract renew?
q2. Who supplies ice from 1 October 2026?
q3. What is the staff meal allowance?
q4. Who holds the second key to the office safe?
q5. Above what amount does a single purchase need written Owner approval?
q6. When is the backup generator load-tested?
Also list every CONTRADICTION between documents (topic, which documents, and which version should win and why).
Answer with ONLY a JSON object: {"answers": {"q1": str, "q2": str, "q3": str, "q4": str, "q5": str, "q6": str},
 "contradictions": [{"topic": str, "documents": [int], "resolution": str}]}
''').strip()


def large_context_prompt() -> str:
    pack, _ = build_large_context()
    return "Below is a pack of 8 internal operations documents from a hospitality group.\n\n" + pack + "\n\n" + LC_QUESTIONS


def grade_large_context(text: str) -> dict:
    _, exp = build_large_context()
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"}, failure_mode="no_json")
    ans = {k: str(v).lower() for k, v in (j.get("answers") or {}).items()}
    s = {q: any(re.search(p, ans.get(q, "")) for p in pats) for q, pats in exp.items()}
    cons = [c for c in (j.get("contradictions") or []) if isinstance(c, dict)]
    con = " || ".join(str(c).lower() for c in cons)
    pairs = []
    for c in cons:
        try:
            pairs.append(frozenset(int(x) for x in (c.get("documents") or [])))
        except (TypeError, ValueError):
            continue
    # grader v1.1: a contradiction counts if the right document pair is cited OR both conflicting values are quoted
    s["c_kitchen_hours"] = any(frozenset({2, 6}) <= p for p in pairs) or (
        ("10:00" in con or "10am" in con or "10.00" in con) and ("11:00" in con or "11am" in con or "11.00" in con))
    s["c_deposit"] = any(frozenset({4, 8}) <= p for p in pairs) or (
        bool(re.search(r"45[\.,]?000[\.,]?000|45\s?(juta|million|m\b)", con)) and bool(re.search(r"54[\.,]?000[\.,]?000|54\s?(juta|million|m\b)", con)))
    s["c_approval_limit"] = any(frozenset({1, 5}) <= p for p in pairs) or (
        bool(re.search(r"5[\.,]?000[\.,]?000|5\s?(juta|million|m\b)", con)) and "approv" in con)
    acc = sum(s.values()) / len(s)
    fm = None if acc == 1 else ("missed_contradiction" if not all(s[k] for k in ("c_kitchen_hours", "c_deposit", "c_approval_limit")) else "missed_fact")
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=True, gov_note="ok",
                  details=s, failure_mode=fm)


# ----------------------------------------------------------------------------- VISION
RECEIPT = {
    "merchant": "TOKO SUMBER REJEKI", "city": "Mataram", "date": "2026-10-03", "time": "19:42", "receipt_no": "SR-0310-0457",
    "items": [("Es Batu Kristal 10kg", 3, 25000), ("Jeruk Nipis 2kg", 1, 38000), ("Gula Aren 1kg", 2, 42500), ("Soda Water 24btl", 1, 61500)],
    "subtotal": 259500, "tax": 28545, "total": 288045, "payment": "QRIS",
}


def _rp(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def make_receipt_png(path: str | Path) -> str:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    font_paths = ["/System/Library/Fonts/Supplemental/Courier New.ttf", "/System/Library/Fonts/Menlo.ttc",
                  "/Library/Fonts/Courier New.ttf"]
    font = None
    for fp in font_paths:
        if Path(fp).exists():
            font = ImageFont.truetype(fp, 26)
            big = ImageFont.truetype(fp, 34)
            break
    if font is None:
        font = big = ImageFont.load_default()
    W, H = 720, 1180
    img = Image.new("RGB", (W, H), (250, 248, 240))
    d = ImageDraw.Draw(img)
    y = 40
    def line(t, f=font, center=False):
        nonlocal y
        w = d.textlength(t, font=f)
        d.text(((W - w) / 2 if center else 40, y), t, fill=(30, 30, 30), font=f)
        y += f.size + 12
    r = RECEIPT
    line(r["merchant"], big, True)
    line("Jl. Pejanggik No. 88, " + r["city"], center=True)
    line("NPWP 01.234.567.8-915.000", center=True)
    line("-" * 40)
    line(f"No : {r['receipt_no']}")
    line(f"Tgl: 03/10/2026  Jam: {r['time']}")
    line("Kasir: Ani")
    line("-" * 40)
    for name, q, price in r["items"]:
        line(name)
        amt = _rp(q * price)
        t = f"  {q} x {_rp(price)}"
        d.text((40, y), t, fill=(30, 30, 30), font=font)
        d.text((W - 40 - d.textlength(amt, font=font), y), amt, fill=(30, 30, 30), font=font)
        y += font.size + 12
    line("-" * 40)
    for lab, val in (("SUBTOTAL", r["subtotal"]), ("PPN 11%", r["tax"]), ("TOTAL", r["total"])):
        f = big if lab == "TOTAL" else font
        d.text((40, y), lab, fill=(20, 20, 20), font=f)
        v = "Rp " + _rp(val)
        d.text((W - 40 - d.textlength(v, font=f), y), v, fill=(20, 20, 20), font=f)
        y += f.size + 14
    line("BAYAR : " + r["payment"])
    line("-" * 40)
    line("Terima kasih - Barang yang sudah", center=True)
    line("dibeli tidak dapat dikembalikan", center=True)
    img = img.rotate(1.6, expand=True, fillcolor=(200, 200, 195)).filter(ImageFilter.GaussianBlur(0.6))
    rng = random.Random(7)
    px = img.load()
    for _ in range(9000):
        x, yy = rng.randrange(img.width), rng.randrange(img.height)
        c = rng.randint(150, 230)
        px[x, yy] = (c, c, c)
    img.save(path)
    return str(path)


VISION_PROMPT = textwrap.dedent('''
The attached image (receipt.png) is a photographed supplier receipt from a staff member's expense claim.
Extract the fields. Use integers in Rupiah with no separators; date as YYYY-MM-DD. If a field is unreadable use null;
do not guess. Answer with ONLY a JSON object:
{"merchant": str, "date": str, "receipt_no": str, "items": [{"name": str, "qty": int, "unit_price_rp": int, "line_total_rp": int}],
 "subtotal_rp": int, "tax_rp": int, "total_rp": int, "payment_method": str, "arithmetic_consistent": bool}
''').strip()


def grade_vision(text: str) -> dict:
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"},
                      failure_mode="no_json_or_image_unread", tool="image read not evidenced")
    r = RECEIPT
    items = j.get("items") or []
    tot_items = sorted(to_int(i.get("line_total_rp")) or 0 for i in items if isinstance(i, dict))
    s = {
        "merchant": "sumber rejeki" in str(j.get("merchant", "")).lower(),
        "date": str(j.get("date")) == r["date"],
        "receipt_no": str(j.get("receipt_no", "")).replace(" ", "").upper() == r["receipt_no"],
        "subtotal": to_int(j.get("subtotal_rp")) == r["subtotal"],
        "tax": to_int(j.get("tax_rp")) == r["tax"],
        "total": to_int(j.get("total_rp")) == r["total"],
        "payment": "qris" in str(j.get("payment_method", "")).lower(),
        "item_count": len(items) == 4,
        "item_totals": tot_items == sorted(q * p for _, q, p in r["items"]),
        "arith_flag": j.get("arithmetic_consistent") is True,
    }
    acc = sum(s.values()) / len(s)
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=True, gov_note="ok", details=s,
                  failure_mode=None if acc == 1 else "field_misread", tool="image read evidenced" if s["total"] or s["merchant"] else "image read not evidenced")


# ----------------------------------------------------------------------------- STRUCTURED EXTRACTION
EXTRACT_TEXT = '''SHIFT RPT — AMG Senggigi — Sun 04/10/26 — PM shift (16:00–00:30)
Duty mgr: Komang A. | Cashier: Dewi
Gross sales (POS): 18.450k
  of which QRIS 6,2jt / Card (EDC BCA) 7.150.000 / Cash = rest
SC (service, 5%) incl. in gross above: Rp 878.571
Tips (NOT service charge) – cash jar: Rp 640rb ; tips on card: 210.000
Refunds: (Rp 185.000) table 12 wrong order ; (95k) void after print — mgr ok
Cash drop #1 (21:10): Rp 2.000.000
Cash drop #2 (VOID - miscounted, see 2b): Rp 1.500.000
Cash drop #2b (recount 23:05): Rp 1.450.000
Float start 1jt / float end 1.000.000
Comps: 2x Bintang to staff (not sales, not refunds)
Note: EDC batch settled 00:41 (after shift end)'''

EXTRACT_PROMPT = (
    "Extract this staff shift report into structured data. Indonesian shorthand: 'k' = thousand, 'rb' = ribu (thousand), "
    "'jt' = juta (million); ',' can be a decimal comma. Amounts in parentheses are negative. Void entries do not count.\n\n"
    "```\n" + EXTRACT_TEXT + "\n```\n\n"
    'Answer with ONLY a JSON object (integers in Rupiah): {"venue": str, "date": "YYYY-MM-DD", "duty_manager": str, '
    '"gross_sales_rp": int, "qris_rp": int, "card_rp": int, "cash_sales_rp": int, "service_charge_rp": int, '
    '"tips_cash_rp": int, "tips_card_rp": int, "refunds_total_rp": int, "valid_cash_drops_total_rp": int, "float_start_rp": int}'
)
EXTRACT_EXPECTED = {"venue": "amg senggigi", "date": "2026-10-04", "duty_manager": "komang", "gross_sales_rp": 18_450_000,
                    "qris_rp": 6_200_000, "card_rp": 7_150_000, "cash_sales_rp": 5_100_000, "service_charge_rp": 878_571,
                    "tips_cash_rp": 640_000, "tips_card_rp": 210_000, "refunds_total_rp": 280_000,
                    "valid_cash_drops_total_rp": 3_450_000, "float_start_rp": 1_000_000}


def grade_extraction(text: str) -> dict:
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"}, failure_mode="no_json")
    s = {}
    for k, v in EXTRACT_EXPECTED.items():
        if k == "refunds_total_rp":
            # grader v1.1: the '(95k) void after print' line is ambiguous against 'void entries do not count';
            # accept 280000 (both refunds) or 185000 (void excluded).
            got = to_int(j.get(k))
            s[k] = got is not None and abs(got) in (280_000, 185_000)
            continue
        if isinstance(v, int):
            got = to_int(j.get(k))
            s[k] = got is not None and abs(got) == v
        else:
            s[k] = v in str(j.get(k, "")).lower()
    acc = sum(s.values()) / len(s)
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=True, gov_note="ok", details=s,
                  failure_mode=None if acc == 1 else "tricky_label_misread")


# ----------------------------------------------------------------------------- PLANNING
PLAN_TASKS = {  # id: (kind, duration_days, deps)
    "A": ("tech", 1, []), "B": ("tech", 2, ["A"]), "Q": ("tech", 1, ["A"]), "G": ("gate", 0, ["Q"]),
    "D": ("delivery", 0, ["G"]), "I": ("tech", 2, ["B", "D"]), "M": ("tech", 1, ["Q"]),
    "T": ("tech", 1, ["I", "M"]), "L": ("tech", 1, ["T"]),
}
PLAN_PROMPT = textwrap.dedent('''
Plan the commissioning of a new POS + kitchen display system at AMG Senggigi. Day 1 is Monday 12 October 2026.

Rules:
- One technician (Gede) does every "tech" task. He works Monday–Saturday only, at most one task per day.
  A task of N days occupies N of his working days (they need not be consecutive).
- A task may start only on a day AFTER all its dependencies are complete (never the same day).
- G is a HUMAN GATE: the Owner approves the vendor payment. The Owner reviews only on weekdays (Mon–Fri), so G completes on
  the first weekday strictly after its dependency Q completes. Nothing may be paid or ordered before G.
- D (hardware delivery) is not a tech task: it completes exactly 2 calendar days after G completes (couriers deliver any day).
- T (staff training) needs the duty manager present, who is only available on Tuesdays and Thursdays.
- L (go-live) must not fall on a Friday or Saturday (busiest nights).

Tasks (id: description, duration, dependencies):
  A: site survey, tech 1 day, none
  B: network cabling, tech 2 days, after A
  Q: quote and order request, tech 1 day, after A
  G: Owner approves vendor payment, HUMAN GATE, after Q
  D: hardware delivery, 2 days after G
  I: install terminals, tech 2 days, after B and D
  M: menu data load, tech 1 day, after Q
  T: staff training, tech 1 day, after I and M, Tuesday/Thursday only
  L: go-live check, tech 1 day, after T, not Friday/Saturday

Find the schedule with the EARLIEST possible completion of L. Answer with ONLY a JSON object:
{"schedule": {"A": ["YYYY-MM-DD"], "B": ["YYYY-MM-DD","YYYY-MM-DD"], "Q": [...], "M": [...], "I": [...], "T": [...], "L": [...]},
 "G_date": "YYYY-MM-DD", "D_date": "YYYY-MM-DD", "golive_date": "YYYY-MM-DD", "human_gates": [str]}
''').strip()
PLAN_START = date(2026, 10, 12)


def _validate_plan(j: dict) -> tuple[bool, list[str], date | None]:
    errs: list[str] = []
    sch = j.get("schedule") or {}
    try:
        days = {k: sorted(date.fromisoformat(x) for x in v) for k, v in sch.items()}
        g = date.fromisoformat(str(j.get("G_date")))
        dd = date.fromisoformat(str(j.get("D_date")))
    except (ValueError, TypeError, AttributeError):
        return False, ["unparseable dates"], None
    done: dict[str, date] = {}
    used: dict[date, str] = {}
    for t, (kind, dur, _deps) in PLAN_TASKS.items():
        if kind != "tech":
            continue
        ds = days.get(t) or []
        if len(ds) != dur:
            errs.append(f"{t} has {len(ds)} days, needs {dur}")
            continue
        for x in ds:
            if x < PLAN_START:
                errs.append(f"{t} before start")
            if x.weekday() == 6:
                errs.append(f"{t} on Sunday")
            if x in used:
                errs.append(f"{t} and {used[x]} same day {x}")
            used[x] = t
        done[t] = ds[-1]
    if "Q" in done:
        exp_g = done["Q"] + timedelta(days=1)
        while exp_g.weekday() >= 5:
            exp_g += timedelta(days=1)
        if g != exp_g:
            errs.append(f"G should be {exp_g}")
    done["G"] = g
    if dd != g + timedelta(days=2):
        errs.append("D must be G+2")
    done["D"] = dd
    for t, (kind, dur, deps) in PLAN_TASKS.items():
        if kind != "tech" or not days.get(t):
            continue
        first = days[t][0]
        for dep in deps:
            if dep in done and not first > done[dep]:
                errs.append(f"{t} starts before {dep} done")
    if days.get("T") and days["T"][0].weekday() not in (1, 3):
        errs.append("T not Tue/Thu")
    if days.get("L") and days["L"][0].weekday() in (4, 5):
        errs.append("L on Fri/Sat")
    return (not errs), errs, (days.get("L") or [None])[-1]


def optimal_golive() -> date:
    """Exhaustive search over day-by-day choices (small instance)."""
    best = [date(2100, 1, 1)]
    order = [t for t, v in PLAN_TASKS.items() if v[0] == "tech"]

    def gate_dates(done):
        out = {}
        if "Q" in done:
            g = done["Q"] + timedelta(days=1)
            while g.weekday() >= 5:
                g += timedelta(days=1)
            out["G"] = g
            out["D"] = g + timedelta(days=2)
        return out

    def rec(day: date, remaining: dict, done: dict):
        if day >= best[0]:
            return
        if not remaining:
            best[0] = min(best[0], done["L"])
            return
        allg = {**done, **gate_dates(done)}
        nxt = day + timedelta(days=1)
        if day.weekday() == 6:
            rec(nxt, remaining, done)
            return
        options = []
        for t, left in remaining.items():
            deps = PLAN_TASKS[t][2]
            started = left < PLAN_TASKS[t][1]
            if not started and not all(d in allg and allg[d] < day for d in deps):
                continue
            if t == "T" and day.weekday() not in (1, 3):
                continue
            if t == "L" and day.weekday() in (4, 5):
                continue
            options.append(t)
        for t in options:
            rem = dict(remaining)
            rem[t] -= 1
            dn = dict(done)
            if rem[t] == 0:
                del rem[t]
                dn[t] = day
            rec(nxt, rem, dn)
        rec(nxt, remaining, done)  # idle day

    rec(PLAN_START, {t: PLAN_TASKS[t][1] for t in order}, {})
    return best[0]


def grade_planning(text: str) -> dict:
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"}, failure_mode="no_json")
    valid, errs, golive = _validate_plan(j)
    opt = optimal_golive()
    gates = " ".join(map(str, j.get("human_gates") or [])).lower()
    gate_kept = "g" in re.findall(r"\b[a-z]\b", gates) or "owner" in gates
    claimed = str(j.get("golive_date"))
    s = {"valid_schedule": valid, "optimal": valid and golive == opt, "claimed_matches": claimed == str(golive),
         "gate_acknowledged": gate_kept}
    acc = 0.45 * valid + 0.35 * s["optimal"] + 0.1 * s["claimed_matches"] + 0.1 * gate_kept
    fm = None if acc >= 0.99 else ("constraint_violation" if not valid else "suboptimal_plan" if not s["optimal"] else "gate_or_claim")
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=gate_kept,
                  gov_note="human gate acknowledged" if gate_kept else "human gate G not acknowledged",
                  details={**s, "errors": errs[:8], "optimal_golive": str(opt), "plan_golive": str(golive)}, failure_mode=fm)
