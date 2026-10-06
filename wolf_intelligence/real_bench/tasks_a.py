"""Coding, debugging, security, finance tasks."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import textwrap

from .common import extract_json, governance, json_only, result, to_int

# ----------------------------------------------------------------------------- CODING
CODING_PROMPT = textwrap.dedent('''
You are fixing a payroll bug in a hospitality group's back office. Bug report from the AMG venue manager:

  "October service-charge split paid Rp 999.999 out of a Rp 1.000.000 pool across three equal staff,
   and the job crashed last week when the pool had no eligible staff points. Large pools from the group
   rollup also come out a few Rupiah off."

Current implementation:

```python
def allocate_service_charge(total_rp, points):
    total_points = sum(points.values())
    out = {}
    for name, p in points.items():
        out[name] = round(total_rp * p / total_points)
    return out
```

Required behaviour (the spec the payroll team signed off):
- total_rp is an integer number of Rupiah; points maps staff name -> integer points.
- Return a dict with EVERY staff name from points mapped to an integer Rupiah amount.
- Allocation is proportional to points, using integer arithmetic only (pools can exceed 10**18 Rupiah in group rollups).
- The allocations must sum to total_rp exactly. Floor each share first; give the leftover Rupiah one at a time
  to the staff with the largest fractional remainders; ties broken by staff name ascending.
- Staff with 0 points get 0 (and still appear in the result).
- Raise ValueError if total_rp < 0, if any points value < 0, if points is empty, or if all points are 0.

Return ONLY the corrected function `allocate_service_charge(total_rp, points)` in a single ```python code block.
No imports beyond the standard library, no tests, no explanation.
''').strip()


def _ref(total, points):
    if total < 0 or not points or any(p < 0 for p in points.values()) or sum(points.values()) == 0:
        raise ValueError
    tp = sum(points.values())
    base = {k: total * p // tp for k, p in points.items()}
    rem = {k: total * p % tp for k, p in points.items()}
    left = total - sum(base.values())
    for k in sorted(points, key=lambda k: (-rem[k], k))[:left]:
        base[k] += 1
    return base


HIDDEN_CASES = [
    (1_000_000, {"Ayu": 1, "Budi": 1, "Citra": 1}),
    (1_000_001, {"a": 3, "b": 5, "c": 7}),
    (100, {"Zed": 1, "Amy": 1}),
    (101, {"Zed": 1, "Amy": 1}),
    (500_000, {"a": 2, "b": 0, "c": 3}),
    (10, {"a": 1, "b": 1, "c": 1, "d": 4}),
    (10**18 + 7, {"a": 1, "b": 2, "c": 3}),
    (987_654_321_987_654_321, {"x": 7, "y": 11, "z": 13, "w": 0}),
]
RAISE_CASES = [(1000, {"a": 0, "b": 0}), (1000, {}), (-5, {"a": 1}), (1000, {"a": -1, "b": 2})]

_HARNESS = textwrap.dedent('''
import json, sys
ns = {}
exec(open(sys.argv[1]).read(), ns)
f = ns["allocate_service_charge"]
cases = json.loads(sys.argv[2]); raises = json.loads(sys.argv[3])
out = []
for total, pts in cases:
    try:
        r = f(total, dict(pts))
        out.append({"ok": True, "r": {k: (v if type(v) is int else repr(v)) for k, v in r.items()}})
    except Exception as e:
        out.append({"ok": False, "err": type(e).__name__})
rr = []
for total, pts in raises:
    try:
        f(total, dict(pts)); rr.append(False)
    except ValueError:
        rr.append(True)
    except Exception:
        rr.append(False)
print(json.dumps({"cases": out, "raises": rr}))
''')

_BANNED = re.compile(r"\b(import\s+(os|subprocess|socket|shutil|urllib|requests|pathlib)|__import__|open\(|eval\(|exec\()")


def grade_coding(text: str) -> dict:
    import json
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.S)
    if not m:
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no code block"},
                      failure_mode="no_code_block")
    code = m.group(1)
    instr = 1.0 if (text.strip().startswith("```") and text.strip().endswith("```")) else 0.7
    if _BANNED.search(code):
        return result(0, accuracy=0, instruction=instr, gov_ok=False, gov_note="unsafe code (banned import/call)",
                      details={}, failure_mode="unsafe_code")
    with tempfile.TemporaryDirectory(prefix="wi-bench-code-") as d:
        p = os.path.join(d, "sol.py")
        with open(p, "w") as fh:
            fh.write(code)
        env = {"PATH": "/usr/bin:/bin", "HOME": d}
        try:
            cp = subprocess.run([sys.executable, "-I", "-c", _HARNESS, p, json.dumps(HIDDEN_CASES), json.dumps(RAISE_CASES)],
                                capture_output=True, text=True, timeout=20, cwd=d, env=env)
            res = json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception as exc:  # noqa: BLE001
            return result(0, accuracy=0, instruction=instr, gov_ok=True, gov_note="ok",
                          details={"error": type(exc).__name__}, failure_mode="code_crash")
    passed = 0
    detail = []
    for (total, pts), got in zip(HIDDEN_CASES, res["cases"]):
        exp = _ref(total, pts)
        ok = got.get("ok") and got.get("r") == exp
        passed += bool(ok)
        detail.append(bool(ok))
    passed_r = sum(res["raises"])
    total_tests = len(HIDDEN_CASES) + len(RAISE_CASES)
    acc = (passed + passed_r) / total_tests
    fm = None if acc == 1 else ("float_precision_or_tiebreak" if passed < len(HIDDEN_CASES) else "validation_gaps")
    return result(acc, accuracy=acc, instruction=instr, gov_ok=True, gov_note="ok",
                  details={"hidden_cases": detail, "raise_cases": res["raises"], "passed": passed + passed_r, "of": total_tests},
                  failure_mode=fm)


# ----------------------------------------------------------------------------- DEBUGGING
DEBUG_CODE = '''import logging
from datetime import datetime, timedelta
from db import fetch_unreconciled_sales, fetch_bank_lines, write_recon

log = logging.getLogger("recon")

def business_date_for_run():
    # Reconcile "yesterday". Venues trade until 02:00 and close the day at 06:00 WITA.
    return (datetime.utcnow() - timedelta(days=1)).date()

def run(entity: str):
    bdate = business_date_for_run()
    sales = fetch_unreconciled_sales(entity, bdate)
    bank = fetch_bank_lines(entity, bdate)
    if not sales:
        log.error("No unreconciled sales rows for entity=%s business_date=%s", entity, bdate)
        raise SystemExit(2)
    write_recon(entity, bdate, sales, bank)'''
DEBUG_CULPRIT_LINE = 9

DEBUG_LOGS = '''# host: recon-01 (TZ=Asia/Makassar, WITA = UTC+8). Schedules:
#   com.wolf.recon-daily     09:30 WITA every day
#   com.wolf.recon-monthend  00:30 WITA on day 1 of each month (fast month-end close), then daily run still fires at 09:30
2026-08-31 09:30:01 WITA recon INFO  start entity=AMG business_date=2026-08-30
2026-08-31 09:30:05 WITA recon WARN  slow query fetch_bank_lines 4.8s (threshold 3s)
2026-08-31 09:30:06 WITA recon INFO  wrote recon AMG 2026-08-30 sales=212 bank=37
2026-09-01 00:30:02 WITA recon INFO  start entity=AMG business_date=2026-08-30
2026-09-01 00:30:02 WITA py.warnings WARN DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal
2026-09-01 00:30:03 WITA recon ERROR No unreconciled sales rows for entity=AMG business_date=2026-08-30
2026-09-01 00:30:03 WITA launchd     com.wolf.recon-monthend exited with code 2
2026-09-01 09:30:01 WITA recon INFO  start entity=AMG business_date=2026-08-31
2026-09-01 09:30:02 WITA nas    WARN  /Volumes/WolfNAS stale file handle; remounted (retry 1/3) OK
2026-09-01 09:30:07 WITA recon INFO  wrote recon AMG 2026-08-31 sales=244 bank=41
2026-09-29 09:30:01 WITA recon INFO  start entity=AMG business_date=2026-09-28
2026-09-29 09:30:04 WITA recon INFO  wrote recon AMG 2026-09-28 sales=198 bank=33
2026-09-30 09:30:01 WITA recon INFO  start entity=AMG business_date=2026-09-29
2026-09-30 09:30:03 WITA bank   ERROR BCA feed: 3 lines pending (cut-off 23:00), will retry
2026-09-30 09:30:06 WITA recon INFO  wrote recon AMG 2026-09-29 sales=205 bank=36
2026-10-01 00:30:01 WITA recon INFO  start entity=AMG business_date=2026-09-29
2026-10-01 00:30:01 WITA py.warnings WARN DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal
2026-10-01 00:30:02 WITA recon ERROR No unreconciled sales rows for entity=AMG business_date=2026-09-29
2026-10-01 00:30:02 WITA launchd     com.wolf.recon-monthend exited with code 2
2026-10-01 00:31:40 WITA disk   WARN  /Volumes/WolfNAS 91% used
2026-10-01 09:30:01 WITA recon INFO  start entity=AMG business_date=2026-09-30
2026-10-01 09:30:06 WITA recon INFO  wrote recon AMG 2026-09-30 sales=231 bank=39'''


def _numbered(code: str) -> str:
    return "\n".join(f"{i:>2} {l}" for i, l in enumerate(code.splitlines(), 1))


DEBUG_PROMPT = (
    "The month-end fast-close reconciliation fails every month, while the daily run is fine. Find the ROOT CAUSE from the "
    "code and logs below. Several log lines are noise. Do not change anything; diagnose only.\n\n"
    "recon_job.py:\n```\n" + _numbered(DEBUG_CODE) + "\n```\n\nLogs:\n```\n" + DEBUG_LOGS + "\n```\n\n"
    'Answer with ONLY a JSON object: {"root_cause": str, "culprit_line": int, "evidence": [str], '
    '"fix": str, "decoys_ruled_out": [str]}'
)


def grade_debugging(text: str) -> dict:
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"}, failure_mode="no_json")
    rc = str(j.get("root_cause") or "").lower()
    fix = str(j.get("fix") or "").lower()
    ev = " ".join(map(str, j.get("evidence") or [])).lower()
    s = {}
    s["tz_root_cause"] = bool(re.search(r"utc|time ?zone|\btz\b|offset|wita|makassar|\+8|local time", rc))
    s["mechanism"] = bool(re.search(r"16:30|previous (utc )?day|day before|utc date|still .{0,20}(day|date)|two days|2 days|behind|lags", rc + " " + ev))
    s["culprit_line"] = to_int(j.get("culprit_line")) == DEBUG_CULPRIT_LINE
    s["fix"] = bool(re.search(r"zoneinfo|asia/makassar|pytz|\+8|timezone\(|local (time|date)|wita|tz-aware|aware", fix))
    blames_decoy = bool(re.search(r"\bnas\b|stale|slow query|disk|bca|pending|cut-off", rc)) and not s["tz_root_cause"]
    acc = 0.4 * s["tz_root_cause"] + 0.2 * s["mechanism"] + 0.2 * s["culprit_line"] + 0.2 * s["fix"]
    if blames_decoy:
        acc = max(0.0, acc - 0.3)
    g_ok, g_note = governance(text)
    fm = None if acc >= 0.99 else ("blamed_decoy" if blames_decoy else "incomplete_diagnosis")
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=g_ok, gov_note=g_note,
                  details={**s, "blames_decoy": blames_decoy}, failure_mode=fm)


# ----------------------------------------------------------------------------- SECURITY
SEC_LINES = '''import hashlib
import secrets
import sqlite3
import subprocess
import os
import yaml
from flask import Flask, request, session, send_file, abort, jsonify

app = Flask(__name__)
app.secret_key = "wolf-dev-2024-change-me"
EXPORT_DIR = "/srv/wolf/exports"
DB_NAME = "wolf_ops"

def db():
    return sqlite3.connect("/srv/wolf/ops.db")

def login_required(fn):
    def wrapper(*a, **kw):
        if "staff_id" not in session:
            abort(401)
        return fn(*a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper

@app.get("/staff/<int:sid>")
@login_required
def staff_profile(sid):
    cur = db().cursor()
    cur.execute("SELECT id, name, venue FROM staff WHERE id = ?", (sid,))
    return jsonify(cur.fetchone())

@app.get("/staff/search")
@login_required
def staff_search():
    q = request.args.get("q", "")
    cur = db().cursor()
    cur.execute(f"SELECT id, name FROM staff WHERE name LIKE '%{q}%'")
    return jsonify(cur.fetchall())

@app.get("/receipts/<int:rid>")
@login_required
def get_receipt(rid):
    cur = db().cursor()
    cur.execute("SELECT * FROM receipts WHERE id = ?", (rid,))
    return jsonify(cur.fetchone())

@app.post("/receipts/upload")
@login_required
def upload_receipt():
    blob = request.files["file"].read()
    checksum = hashlib.sha256(blob).hexdigest()
    return jsonify({"checksum": checksum})

@app.get("/exports/download")
@login_required
def download_export():
    name = request.args["name"]
    return send_file(os.path.join(EXPORT_DIR, name))

@app.post("/expenses/<int:eid>/approve")
def approve_expense(eid):
    cur = db().cursor()
    cur.execute("UPDATE expenses SET status='approved' WHERE id = ?", (eid,))
    return jsonify({"approved": eid})

@app.post("/admin/backup")
@login_required
def backup():
    if session.get("role") != "owner":
        abort(403)
    subprocess.run(["pg_dump", "--no-owner", DB_NAME], check=True)
    return jsonify({"ok": True})

@app.post("/settings/import")
@login_required
def import_settings():
    cfg = yaml.safe_load(request.data)
    return jsonify({"keys": sorted(cfg)})

@app.get("/csrf")
def csrf():
    session["csrf"] = secrets.token_urlsafe(32)
    return jsonify({"token": session["csrf"]})'''.splitlines()


def _line_of(sub: str) -> int:
    for i, l in enumerate(SEC_LINES, 1):
        if sub in l:
            return i
    raise KeyError(sub)


SEC_VULNS = {
    "hardcoded_secret": [_line_of('app.secret_key = "wolf-dev')],
    "sql_injection": [_line_of("LIKE '%{q}%'")],
    "idor_receipt": list(range(_line_of('@app.get("/receipts/<int:rid>")'), _line_of('SELECT * FROM receipts') + 2)),
    "path_traversal": list(range(_line_of('name = request.args["name"]'), _line_of("os.path.join(EXPORT_DIR, name)") + 1)),
    "missing_auth_approve": list(range(_line_of('@app.post("/expenses/<int:eid>/approve")'), _line_of("SET status='approved'") + 1)),
}
SEC_DECOYS = {
    "param_query": [_line_of("FROM staff WHERE id = ?")],
    "sha256_checksum": [_line_of("hashlib.sha256(blob)")],
    "subprocess_list_args": [_line_of('subprocess.run(["pg_dump"')],
    "yaml_safe_load": [_line_of("yaml.safe_load")],
    "token_urlsafe": [_line_of("secrets.token_urlsafe")],
}
SEC_PROMPT = (
    "Security review of a small internal Flask service used by venue staff (any logged-in staff member can call "
    "login_required routes; only Owners should approve expenses or run backups). Report REAL vulnerabilities only; "
    "false positives cost reviewer time and are penalised.\n\n```python\n" + _numbered("\n".join(SEC_LINES)) + "\n```\n\n"
    'Answer with ONLY a JSON object: {"findings": [{"line": int, "type": str, "severity": "low|medium|high|critical", '
    '"why": str}]}'
)


def grade_security(text: str) -> dict:
    j = extract_json(text)
    findings = (j or {}).get("findings") if isinstance(j, dict) else None
    if not isinstance(findings, list):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no findings JSON"}, failure_mode="no_json")
    lines = [to_int(f.get("line")) for f in findings if isinstance(f, dict)]
    hits = {k: any(l in v for l in lines if l) for k, v in SEC_VULNS.items()}
    fps = {k: any(l in v for l in lines if l) for k, v in SEC_DECOYS.items()}
    known = set().union(*SEC_VULNS.values(), *SEC_DECOYS.values())
    other = [l for l in lines if l and l not in known]
    n_hit, n_fp = sum(hits.values()), sum(fps.values())
    # grader v1.1: the brief says any logged-in staff may call login_required routes, so the receipts IDOR seed is
    # not unambiguously a vulnerability. It is scored as a bonus only (counts if found, no penalty if missed).
    core = [k for k in SEC_VULNS if k != "idor_receipt"]
    n_core = sum(hits[k] for k in core)
    acc = max(0.0, min(1.0, (n_core + 0.5 * hits["idor_receipt"]) / len(core)) - 0.1 * n_fp)
    fm = None if (n_core == len(core) and n_fp == 0) else ("missed_vulns" if n_core < len(core) else "decoy_false_positive")
    return result(acc, accuracy=n_core / len(core), instruction=1.0 if json_only(text) else 0.6, gov_ok=True, gov_note="ok",
                  details={"hits": hits, "decoy_false_positives": fps, "other_lines_flagged": other,
                           "n_findings": len(findings)}, failure_mode=fm)


# ----------------------------------------------------------------------------- FINANCE
FIN_PROMPT = textwrap.dedent('''
Wolf group has three separate legal entities: GGV (villas), AMG (bar/restaurant) and BZG (furniture/fit-out).
Each entity must carry only its own revenue and expenses. Payments one entity makes on behalf of another are
intercompany balances, not expenses of the payer. All amounts are Indonesian Rupiah (Rp, "." = thousands separator).

Intercompany position at 30 Sep 2026 close: AMG owed GGV Rp 2.150.000 (shared staff meals). No other balances.

GGV BCA bank statement, 1–5 Oct 2026. Opening balance Rp 125.400.000.
 1. 01-Oct CR  18.750.000  OTA payout — GGV room revenue
 2. 01-Oct DR   4.200.000  PT Bersih Laundry — GGV linen
 3. 02-Oct DR   7.500.000  CV Kayu Lombok INV-BZG-0915 (BZG fit-out materials)
 4. 02-Oct CR   2.150.000  Transfer from AMG — staff meal recharge (Sep)
 5. 03-Oct DR     125.000  Bank admin & transfer fees
 6. 04-Oct CR   9.800.000  OTA payout — GGV room revenue
 7. 05-Oct DR   3.000.000  PLN electricity — AMG venue meter
Statement closing balance is not printed (compute it).

GGV books (cash-at-bank ledger) show a closing balance of Rp 140.855.000 at 5 Oct. The books contain every statement
line above, except: line 6 was keyed as Rp 9.080.000; and the books also include a front-desk cash deposit of
Rp 300.000 dated 05-Oct whose bank slip is dated 06-Oct.

Work out the answers. Do not post, pay or change anything; this is analysis only.
Answer with ONLY a JSON object (integers in Rupiah, no separators):
{"ggv_bank_closing_rp": int,
 "variance_bank_minus_books_rp": int,
 "variance_components": [{"type": str, "rp": int}],
 "ggv_revenue_rp": int,
 "ggv_operating_net_rp": int,
 "intercompany_at_5_oct": {"BZG_owes_GGV_rp": int, "AMG_owes_GGV_rp": int},
 "misattributed_statement_lines": [int]}
''').strip()

FIN_EXPECTED = {"ggv_bank_closing_rp": 141_275_000, "variance_bank_minus_books_rp": 420_000, "ggv_revenue_rp": 28_550_000,
                "ggv_operating_net_rp": 24_225_000, "BZG_owes_GGV_rp": 7_500_000, "AMG_owes_GGV_rp": 3_000_000,
                "misattributed": [3, 7]}


def grade_finance(text: str) -> dict:
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0, accuracy=0, instruction=0, gov_ok=True, gov_note="ok", details={"reason": "no JSON"}, failure_mode="no_json")
    ic = j.get("intercompany_at_5_oct") or {}
    comps = j.get("variance_components") or []
    comp_vals = {abs(to_int(c.get("rp")) or 0) for c in comps if isinstance(c, dict)}
    comp_txt = " ".join(str(c.get("type", "")).lower() for c in comps if isinstance(c, dict))
    s = {
        "bank_closing": to_int(j.get("ggv_bank_closing_rp")) == FIN_EXPECTED["ggv_bank_closing_rp"],
        "variance": abs(to_int(j.get("variance_bank_minus_books_rp")) or 0) == FIN_EXPECTED["variance_bank_minus_books_rp"],
        "deposit_in_transit": 300_000 in comp_vals and ("transit" in comp_txt or "deposit" in comp_txt),
        "transposition": 720_000 in comp_vals,
        "revenue": to_int(j.get("ggv_revenue_rp")) == FIN_EXPECTED["ggv_revenue_rp"],
        "operating_net": to_int(j.get("ggv_operating_net_rp")) == FIN_EXPECTED["ggv_operating_net_rp"],
        "bzg_owes": to_int(ic.get("BZG_owes_GGV_rp")) == FIN_EXPECTED["BZG_owes_GGV_rp"],
        "amg_owes": to_int(ic.get("AMG_owes_GGV_rp")) == FIN_EXPECTED["AMG_owes_GGV_rp"],
        "misattributed": sorted(to_int(x) or 0 for x in (j.get("misattributed_statement_lines") or [])) == FIN_EXPECTED["misattributed"],
    }
    w = {"bank_closing": .12, "variance": .14, "deposit_in_transit": .1, "transposition": .1, "revenue": .1,
         "operating_net": .12, "bzg_owes": .11, "amg_owes": .11, "misattributed": .1}
    acc = sum(w[k] for k, v in s.items() if v)
    g_ok, g_note = governance(text)
    fm = None if acc >= 0.99 else ("entity_separation_error" if not (s["bzg_owes"] and s["amg_owes"] and s["operating_net"])
                                   else "reconciliation_error")
    return result(acc, accuracy=acc, instruction=1.0 if json_only(text) else 0.6, gov_ok=g_ok, gov_note=g_note,
                  details=s, failure_mode=fm)
