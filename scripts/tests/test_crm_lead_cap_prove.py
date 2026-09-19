#!/usr/bin/env python3
"""CAP-CRM-01 lead bound prove. No ledger write. No invented lead. No PROVEN."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import crm_lead_cap_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "crm_lead_cap_prove.py"
CR_ID = "CR-ff42f3a7c49caa79"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(**extra) -> dict:
    base = {
        "entity_id": "ENT-GGV",
        "brand_id": "habitat",
        "source_system": "fixture",
        "owner_person_id": None,
        "source_observed_at": "2026-09-01T00:00:00Z",
        "first_human_touch_at": None,
        "wolf_stage": "OPEN",
        "conversion_status": None,
        "demo": True,
    }
    base.update(extra)
    return base


def test_classify() -> None:
    unread = prove.classify_bound(None, brand_id="habitat")
    check("unread status", unread["status"] == "NOT_READ")
    check("unread not zero", unread["rows"] is None and unread["owned"] is None and unread["empty"] is None)
    check("unread sales absent", unread["sales"] is None)
    empty = prove.classify_bound([], brand_id="habitat")
    check("empty is read", empty["status"] == "READ" and empty["empty"] is True and empty["rows"] == 0)
    check("empty not a sale", empty["sales"] is None and empty["operating_board"] is False)
    try:
        prove.classify_bound([], brand_id="  ")
        check("blank brand refused", False, "no raise")
    except prove.ProveError as exc:
        check("blank brand refused", exc.code == "invalid", exc.code)
    mixed = [_row(), _row(brand_id="atrium")]
    try:
        prove.classify_bound(mixed, brand_id="habitat")
        check("cross brand refused", False, "no raise")
    except prove.ProveError as exc:
        check("cross brand refused", exc.code == "boundary_breach", exc.code)
    try:
        prove.classify_bound([_row(entity_id="")], brand_id="habitat")
        check("missing entity refused", False, "no raise")
    except prove.ProveError as exc:
        check("missing entity refused", exc.code == "boundary_breach", exc.code)
    pack = prove.classify_bound(
        [
            _row(owner_person_id="PERS-1", first_human_touch_at="2026-09-02T00:00:00Z", wolf_stage="ACTIVE"),
            _row(wolf_stage="CLOSED", conversion_status="CLAIMED"),
            _row(wolf_stage="CLOSED", conversion_status="VERIFIED", source_observed_at=None, demo=False),
        ],
        brand_id="habitat",
    )
    check("owned split", pack["owned"] == 1 and pack["unowned"] == 2, str(pack["owned"]))
    check("aged split", pack["aged"] == 2 and pack["not_aged"] == 1)
    check("followed split", pack["followed"] == 1 and pack["not_followed"] == 2)
    check("demo split", pack["demo"] == 2 and pack["not_demo"] == 1)
    check("closed counted not sold", pack["closed"] == 2 and pack["sales"] is None)
    check("claim is not a sale", pack["claimed_conversion"] == 1 and pack["verified_conversion"] == 1)
    check("boundary held", pack["boundary"] == "HELD" and pack["operating_board"] is False)
    try:
        prove.classify_bound(["nope"], brand_id="habitat")
        check("non object refused", False, "no raise")
    except prove.ProveError as exc:
        check("non object refused", exc.code == "invalid", exc.code)


def test_atrium_and_refusals(td: Path) -> None:
    absent = prove.atrium_surface(0)
    check("atrium zero is absent", absent["status"] == "ABSENT" and absent["rows"] is None)
    check("atrium absent not a board", absent["operating_board"] is False)
    unread = prove.atrium_surface(None)
    check("atrium unread", unread["status"] == "NOT_READ" and unread["rows"] is None)
    present = prove.atrium_surface(3)
    check("atrium present counted", present["status"] == "PRESENT" and present["rows"] == 3)
    check("atrium present not commissioned", present["operating_board"] is False)
    flags = prove.honesty_flags()
    check("cr bound", flags["cr_id"] == CR_ID and flags["cr_bound"] is True)
    check("cr present", flags["cr_present"] is True)
    check("cr open", flags["cr_state"] == "OPEN", str(flags.get("cr_state")))
    check("cr not resolved", flags["cr_resolved"] is False)
    check("cr cap", flags["cr_capability"] == "CAP-CRM-01")
    check("live built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling built", flags["maturity_ceiling"] == "BUILT")
    check("not proven", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("no raise", flags["model_c_maturity_raised"] is False and flags["model_c_write"] is False)
    check("no cr mutate", flags["cr_mutated"] is False)
    check("crm02 not this prove", flags["cap_crm_02_not_this_prove"] is True)
    check("writes off", flags["klaviyo_write"] is False and flags["metricool_write"] is False and flags["klaviyo_called"] is False)
    proven = td / "proven.json"
    proven.write_text(json.dumps({"CAP-CRM-01": ["PROVEN", "fixture", "gap"]}), encoding="utf-8")
    high = prove.honesty_flags(proven)
    check("fixture proven reported", high["proven"] is True and high["maturity_ceiling"] == "PROVEN")
    check("fixture does not raise live", prove.ledger_cap_state() == "BUILT")
    ready = td / "ready.json"
    ready.write_text(json.dumps({"CAP-CRM-01": ["READY"]}), encoding="utf-8")
    ready_flags = prove.honesty_flags(ready)
    check("fixture ready reported", ready_flags["ready"] is True and ready_flags["maturity_ceiling"] == "READY")
    specified = td / "specified.json"
    specified.write_text(json.dumps({"CAP-CRM-01": ["SPECIFIED"]}), encoding="utf-8")
    low = prove.honesty_flags(specified)
    check("specified stays below", low["maturity"] == "SPECIFIED" and low["proven"] is False and low["maturity_ceiling"] == "BUILT")
    junk = td / "junk.json"
    junk.write_text(json.dumps({"CAP-CRM-01": ["GREEN"]}), encoding="utf-8")
    junk_flags = prove.honesty_flags(junk)
    check("non maturity unknown", junk_flags["ledger_maturity"] == "UNKNOWN" and junk_flags["proven"] is False)
    empty_db = td / "empty.sqlite"
    sqlite3.connect(empty_db).close()
    missing = prove.honesty_flags(catalog_db=empty_db)
    check("missing table not present", missing["cr_present"] is False and missing["cr_bound"] is True)
    check("missing table not resolved", missing["cr_resolved"] is False)
    try:
        prove.inspect_surfaces(spine_path=td / "alchemist" / "lead_spine.py")
        check("alchemist path refused", False, "no raise")
    except prove.ProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    for label, call, code in (
        ("write", lambda: prove.refuse_external_write({}), "writes_refused"),
        ("klaviyo", lambda: prove.refuse_external_write({"klaviyo": True}), "klaviyo_write_refused"),
        ("metricool", lambda: prove.refuse_external_write({"action": "metricool"}), "metricool_write_refused"),
        ("invent", lambda: prove.refuse_external_write({"invent_lead": True}), "invent_lead_refused"),
        ("score", lambda: prove.refuse_external_write({"proven": True}), "score_refused"),
    ):
        try:
            call()
            check(label + " refused", False, "no raise")
        except prove.ProveError as exc:
            check(label + " refused", exc.code == code, exc.code)


def test_surfaces_and_live(td: Path) -> None:
    surfaces = prove.inspect_surfaces()
    spine = surfaces["lead_spine"]
    check("spine present not executed", spine["present"] is True and spine["executed"] is False)
    check("spine never invent", spine["never_invent_stated"] is True)
    check("spine entity-wide insufficient", spine["entity_wide_insufficient"] is True)
    reader = surfaces["klaviyo_reader"]
    check("klaviyo write path not called", reader["present"] and reader["write_path_present"] and reader["called_by_prove"] is False)
    check("klaviyo network not called", reader["network_called"] is False)
    page = surfaces["habitat_page"]
    check("habitat page demo", page["present"] and page["demo_stated"] and page["closed_not_sale_stated"])
    check("habitat page no sla invent", page["sla_not_invented_stated"] is True)
    check("metricool write flag off", surfaces["metricool_write"] is False)
    adoption = prove.read_adoption()
    check("au read", adoption["au_id"] == "AU-CRM-01-HABITAT" and adoption["present"] is True)
    check("au not started as read", adoption["state"] == "NOT STARTED", str(adoption.get("state")))
    missing_au = td / "no-au.json"
    missing_au.write_text("[]", encoding="utf-8")
    gone = prove.read_adoption(missing_au)
    check("au absent when missing", gone["status"] == "ABSENT" and gone["state"] is None)
    pack = prove.build_prove()
    habitat = pack["habitat"]
    check("live habitat read", habitat["status"] == "READ" and habitat["boundary"] == "HELD")
    check("live sums", habitat["owned"] + habitat["unowned"] == habitat["rows"])
    check("live age sums", habitat["aged"] + habitat["not_aged"] == habitat["rows"])
    check("live follow sums", habitat["followed"] + habitat["not_followed"] == habitat["rows"])
    check("live sales none", habitat["sales"] is None and habitat["operating_board"] is False)
    check("live not invented", pack["honesty"]["invented_leads"] is False and pack["writes"]["invented_leads"] is False)
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    atrium_n = conn.execute("SELECT COUNT(*) FROM core_leads WHERE brand_id='atrium'").fetchone()[0]
    conn.close()
    if atrium_n == 0:
        check("live atrium absent not zero", pack["atrium"]["status"] == "ABSENT" and pack["atrium"]["rows"] is None)
    else:
        check("live atrium counted", pack["atrium"]["status"] == "PRESENT" and pack["atrium"]["rows"] == atrium_n)
    check("live pack built", pack["honesty"]["maturity"] == "BUILT" and pack["honesty"]["proven"] is False)
    check("live cr open", pack["honesty"]["cr_state"] == "OPEN" and pack["honesty"]["cr_resolved"] is False)
    check("gaps block higher", pack["gaps"] and all(g.get("blocks_proven") is True for g in pack["gaps"]))
    ids = {g["id"] for g in pack["gaps"]}
    check("gap ids", {"atrium_board", "klaviyo_write", "metricool_write", "model_e_au", "ledger_gap_text", "cap_crm_02"} <= ids)
    check("no email in pack", "email" not in json.dumps(pack))
    check("schema", pack["schema"] == prove.SCHEMA)
    gap = prove.ledger_gap_text()
    check("ledger gap uncleared", gap == "CAP-bound tests/red-team", str(gap))


def test_source_and_routes() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("module names the CR", CR_ID in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not call run_ingest", "run_ingest(" not in src)
    check("module does not import klaviyo", "import core.habitat_klaviyo" not in src)
    check("module does not bind 8787", "8787" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/crm/lead-cap-prove" in serve)
    check("page route registered", "/crm-lead-cap-prove" in serve)
    check("klaviyo hint wired", 'return {"klaviyo": True}' in serve)
    check("metricool hint wired", 'return {"metricool": True}' in serve)
    check("invent hint wired", 'return {"invent_lead": True}' in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "crm-lead-cap-prove.html").read_text(encoding="utf-8")
    check("page does not say proven as status", "PROVEN" not in page)
    check("page refuses promotion", "does not promote" in page)
    check("page refuses invent", "No lead is invented" in page)


def test_api() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("API handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        def call(method: str, url_path: str, subject: str | None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = b"{}" if method != "GET" else None
            if data:
                headers["Content-Type"] = "application/json"
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if "json" in ctype:
                        return resp.status, json.loads(raw.decode())
                    return resp.status, raw.decode("utf-8", "replace")
            except HTTPError as exc:
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode())
                except json.JSONDecodeError:
                    parsed = raw.decode("utf-8", "replace")
                return exc.code, parsed

        st, anon = call("GET", "/api/crm/lead-cap-prove", None)
        check("anon GET 403", st == 403, str(anon)[:180])
        st, staff = call("GET", "/api/crm/lead-cap-prove", STAFF)
        check("staff GET 403", st == 403, str(staff)[:180])
        st, owner = call("GET", "/api/crm/lead-cap-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            flags = owner.get("honesty") or {}
            check("owner honesty bound", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner maturity built", flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner no sale", (owner.get("habitat") or {}).get("sales") is None)
            check("owner klaviyo off", flags.get("klaviyo_write") is False and flags.get("metricool_write") is False)
            atrium = owner.get("atrium") or {}
            if atrium.get("status") == "ABSENT":
                check("owner atrium not zero", atrium.get("rows") is None)
            else:
                check("owner atrium read", atrium.get("status") in {"PRESENT", "NOT_READ"})
        st, page = call("GET", "/crm-lead-cap-prove", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/crm-lead-cap-prove", MATT)
        check("owner page 200", st == 200 and isinstance(page, str) and "does not promote" in page, str(st))
        st, posted = call("POST", "/api/crm/lead-cap-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, klaviyo = call("POST", "/api/crm/lead-cap-prove/klaviyo", MATT)
        check("owner klaviyo 405", st == 405 and isinstance(klaviyo, dict) and klaviyo.get("error") == "klaviyo_write_refused", str(klaviyo)[:160])
        st, metricool = call("POST", "/api/crm/lead-cap-prove/metricool", MATT)
        check("owner metricool 405", st == 405 and isinstance(metricool, dict) and metricool.get("error") == "metricool_write_refused", str(metricool)[:160])
        st, invented = call("POST", "/api/crm/lead-cap-prove/leads", MATT)
        check("owner invent 405", st == 405 and isinstance(invented, dict) and invented.get("error") == "invent_lead_refused", str(invented)[:160])
        st, _ = call("POST", "/api/crm/lead-cap-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, put = call("PUT", "/api/crm/lead-cap-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:120])
        st, patched = call("PATCH", "/api/crm/lead-cap-prove", MATT)
        check("owner PATCH 405", st == 405 and isinstance(patched, dict) and patched.get("error") == "writes_refused", str(patched)[:120])
    finally:
        httpd.shutdown()


def main() -> int:
    ledger_before = _sha(LEDGER)
    history_before = _sha(HISTORY)
    credits_before = _sha(CREDITS)
    wip_before = {rel: _sha(ROOT / rel) for rel in WIP}
    cr_before = sqlite3.connect(CATALOG_DB).execute(
        "SELECT state FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        test_classify()
        test_atrium_and_refusals(td)
        test_surfaces_and_live(td)
    test_source_and_routes()
    test_api()
    check("ledger bytes unchanged", _sha(LEDGER) == ledger_before)
    check("score history unchanged", _sha(HISTORY) == history_before)
    check("credits doc unchanged", _sha(CREDITS) == credits_before)
    cr_after = sqlite3.connect(CATALOG_DB).execute(
        "SELECT state FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    check("cr row unchanged", cr_before == cr_after == ("OPEN",), str(cr_after))
    for rel, digest in wip_before.items():
        check(f"WIP untouched {Path(rel).name}", _sha(ROOT / rel) == digest)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
