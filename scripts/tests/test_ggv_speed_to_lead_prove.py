#!/usr/bin/env python3
"""CAP-GGV-04 speed-to-lead bound prove. No ledger write. No invented lead. No PROVEN."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import ggv_speed_to_lead_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "ggv_speed_to_lead_prove.py"
CR_ID = "CR-f089b11530ab4673"
GAP = "Governed speed-to-lead capability with tests/red-team"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
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
        "source_observed_at": "2026-09-01T00:00:00Z",
        "first_human_touch_at": None,
        "wolf_stage": "OPEN",
        "demo": True,
    }
    base.update(extra)
    return base


def test_classify() -> None:
    unread = prove.classify_speed(None, brand_id="habitat", now=NOW)
    check("unread status", unread["status"] == "NOT_READ")
    check(
        "unread not zero",
        unread["rows"] is None and unread["waiting"] is None and unread["receipt_absent"] is None,
    )
    check("unread receipts not invented", unread["receipts_invented"] == 0 and unread["leads_invented"] is False)
    check("unread sla absent", unread["sla_target_seconds"] is None and unread["sla_breached"] is None)
    check("unread sales absent", unread["sales"] is None)
    empty = prove.classify_speed([], brand_id="habitat", now=NOW)
    check("empty is read", empty["status"] == "READ" and empty["empty"] is True and empty["rows"] == 0)
    check("empty not a lead", empty["leads_invented"] is False and empty["receipts_invented"] == 0)
    check("empty not a board", empty["operating_board"] is False and empty["sales"] is None)
    try:
        prove.classify_speed([], brand_id="ivy", now=NOW)
        check("non habitat refused", False, "no raise")
    except prove.ProveError as exc:
        check("non habitat refused", exc.code == "not_habitat", exc.code)
    try:
        prove.classify_speed([], brand_id="  ", now=NOW)
        check("blank brand refused", False, "no raise")
    except prove.ProveError as exc:
        check("blank brand refused", exc.code == "not_habitat", exc.code)
    try:
        prove.classify_speed([_row(brand_id="atrium")], brand_id="habitat", now=NOW)
        check("cross brand refused", False, "no raise")
    except prove.ProveError as exc:
        check("cross brand refused", exc.code == "boundary_breach", exc.code)
    try:
        prove.classify_speed([_row(entity_id="")], brand_id="habitat", now=NOW)
        check("missing entity refused", False, "no raise")
    except prove.ProveError as exc:
        check("missing entity refused", exc.code == "boundary_breach", exc.code)
    try:
        prove.classify_speed([_row(sla_target_seconds=60)], brand_id="habitat", now=NOW)
        check("sla on row refused", False, "no raise")
    except prove.ProveError as exc:
        check("sla on row refused", exc.code == "invent_sla_refused", exc.code)
    try:
        prove.classify_speed([_row(invented_receipt=True)], brand_id="habitat", now=NOW)
        check("marked receipt refused", False, "no raise")
    except prove.ProveError as exc:
        check("marked receipt refused", exc.code == "invent_receipt_refused", exc.code)
    try:
        prove.classify_speed(["nope"], brand_id="habitat", now=NOW)
        check("non object refused", False, "no raise")
    except prove.ProveError as exc:
        check("non object refused", exc.code == "invalid", exc.code)
    try:
        prove.classify_speed([], brand_id="habitat", now=datetime(2026, 9, 20, 12, 0))
        check("naive clock refused", False, "no raise")
    except prove.ProveError as exc:
        check("naive clock refused", exc.code == "invalid", exc.code)
    pack = prove.classify_speed(
        [
            _row(),
            _row(first_human_touch_at="2026-09-01T00:01:00Z", wolf_stage="ACTIVE"),
            _row(wolf_stage="CLOSED"),
            _row(source_observed_at=None, first_human_touch_at=None),
            _row(source_observed_at="2026-09-21T00:00:00Z"),
            _row(first_human_touch_at="not-a-clock", demo=False),
        ],
        brand_id="habitat",
        now=NOW,
    )
    check("speed split", pack["waiting"] == 2 and pack["measured"] == 1 and pack["unavailable"] == 3, str(pack))
    check("speed sums", pack["waiting"] + pack["measured"] + pack["unavailable"] == pack["rows"])
    check(
        "receipt split",
        pack["receipt_present"] == 1 and pack["receipt_absent"] == 4 and pack["receipt_unreadable"] == 1,
        str(pack),
    )
    check("receipts not invented", pack["receipts_invented"] == 0 and pack["leads_invented"] is False)
    check("no sla in pack", pack["sla_target_seconds"] is None and pack["sla_breached"] is None)
    check("closed counted not sold", pack["closed"] == 1 and pack["sales"] is None)
    check("demo split", pack["demo"] == 5 and pack["not_demo"] == 1)
    check("boundary held", pack["boundary"] == "HELD" and pack["operating_board"] is False)
    dumped = json.dumps(pack)
    check("timestamps not copied out", "2026-09-01" not in dumped and "first_human_touch_at" not in pack)


def test_ivy_and_refusals(td: Path) -> None:
    absent = prove.ivy_surface(0)
    check("ivy zero is absent", absent["status"] == "ABSENT" and absent["rows"] is None)
    check("ivy absent not a board", absent["operating_board"] is False)
    unread = prove.ivy_surface(None)
    check("ivy unread", unread["status"] == "NOT_READ" and unread["rows"] is None)
    present = prove.ivy_surface(2)
    check("ivy present counted", present["status"] == "PRESENT" and present["rows"] == 2)
    check("ivy present not scored", present["operating_board"] is False)
    flags = prove.honesty_flags()
    check("cr bound", flags["cr_id"] == CR_ID and flags["cr_bound"] is True)
    check("cr present", flags["cr_present"] is True)
    check("cr open", flags["cr_state"] == "OPEN", str(flags.get("cr_state")))
    check("cr blocker", flags["cr_blocker"] == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("cr next action", flags["cr_next_action"] == GAP, str(flags.get("cr_next_action")))
    check("cr not resolved", flags["cr_resolved"] is False)
    check("cr cap", flags["cr_capability"] == "CAP-GGV-04")
    check("live built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling built", flags["maturity_ceiling"] == "BUILT")
    check("not proven", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("ledger rows", flags["ledger_rows"] == 77, str(flags.get("ledger_rows")))
    check("no raise", flags["model_c_maturity_raised"] is False and flags["model_c_write"] is False)
    check("no cr mutate", flags["cr_mutated"] is False)
    check("ggv05 not this prove", flags["cap_ggv_05_not_this_prove"] is True)
    check("triage not executed", flags["triage_board_executed"] is False)
    check(
        "writes off",
        flags["klaviyo_write"] is False
        and flags["metricool_write"] is False
        and flags["activecampaign_write"] is False
        and flags["external_crm_write"] is False
        and flags["klaviyo_called"] is False,
    )
    proven = td / "proven.json"
    proven.write_text(json.dumps({"CAP-GGV-04": ["PROVEN", "fixture", "gap"]}), encoding="utf-8")
    high = prove.honesty_flags(proven)
    check("fixture proven reported", high["proven"] is True and high["maturity_ceiling"] == "PROVEN")
    check("fixture does not raise live", prove.ledger_cap_state() == "BUILT")
    ready = td / "ready.json"
    ready.write_text(json.dumps({"CAP-GGV-04": ["READY"]}), encoding="utf-8")
    ready_flags = prove.honesty_flags(ready)
    check("fixture ready reported", ready_flags["ready"] is True and ready_flags["maturity_ceiling"] == "READY")
    specified = td / "specified.json"
    specified.write_text(json.dumps({"CAP-GGV-04": ["SPECIFIED"]}), encoding="utf-8")
    low = prove.honesty_flags(specified)
    check("specified stays below", low["maturity"] == "SPECIFIED" and low["proven"] is False and low["maturity_ceiling"] == "BUILT")
    junk = td / "junk.json"
    junk.write_text(json.dumps({"CAP-GGV-04": ["GREEN"]}), encoding="utf-8")
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
        ("ac", lambda: prove.refuse_external_write({"activecampaign": True}), "activecampaign_write_refused"),
        ("crm", lambda: prove.refuse_external_write({"external_crm": True}), "external_crm_write_refused"),
        ("invent", lambda: prove.refuse_external_write({"invent_lead": True}), "invent_lead_refused"),
        ("receipt", lambda: prove.refuse_external_write({"invent_receipt": True}), "invent_receipt_refused"),
        ("score", lambda: prove.refuse_external_write({"proven": True}), "score_refused"),
        ("ready", lambda: prove.refuse_external_write({"ready": True}), "score_refused"),
    ):
        try:
            call()
            check(label + " refused", False, "no raise")
        except prove.ProveError as exc:
            check(label + " refused", exc.code == code, exc.code)
    table = {row["id"]: row for row in prove.red_team_table()}
    check("red team ids", {"invent_proven", "invent_leads", "write_locks", "anon_403", "invent_receipts"} <= set(table))
    check("invent proven row", table["invent_proven"]["result"] == "REFUSED" and table["invent_proven"]["code"] == "score_refused")
    check("invent leads row", table["invent_leads"]["result"] == "REFUSED")
    check("invent receipts row", table["invent_receipts"]["result"] == "REFUSED" and table["invent_receipts"]["code"] == "invent_receipt_refused")
    check("write locks row", table["write_locks"]["result"] == "REFUSED" and all(item["refused"] for item in table["write_locks"]["locks"]))
    check(
        "anon row not faked",
        table["anon_403"]["result"] == "FAIL_CLOSED" and table["anon_403"]["exercised_in_module"] is False,
    )


def test_surfaces_and_live(td: Path) -> None:
    surfaces = prove.inspect_surfaces()
    spine = surfaces["lead_spine"]
    check("spine present not executed", spine["present"] is True and spine["executed"] is False)
    check("spine never invent lead", spine["never_invent_lead_stated"] is True)
    check("spine never inserts", spine["never_inserts_lead_stated"] is True)
    check("spine sla stated", spine["sla_not_invented_stated"] is True and spine["proven_false_stated"] is True)
    check("spine receipt clock", spine["receipt_clock_stated"] is True and spine["maturity_built_stated"] is True)
    reader = surfaces["klaviyo_reader"]
    check("klaviyo write path not called", reader["present"] and reader["write_path_present"] and reader["called_by_prove"] is False)
    check("klaviyo network not called", reader["network_called"] is False)
    ac = surfaces["activecampaign_reader"]
    check("ac reader absent", ac["present"] is False and ac["called_by_prove"] is False and ac["network_called"] is False)
    page = surfaces["habitat_page"]
    check("habitat page demo", page["present"] and page["demo_stated"] and page["closed_not_sale_stated"])
    check("habitat page no sla invent", page["sla_not_invented_stated"] is True)
    check("metricool write flag off", surfaces["metricool_write"] is False)
    check("triage flag off", surfaces["triage_board_executed"] is False)
    adoption = prove.read_adoption()
    check("au id", adoption["au_id"] == "AU-GGV-04-HABITAT")
    check("au absent", adoption["present"] is False and adoption["status"] == "ABSENT", str(adoption.get("status")))
    missing_au = td / "no-au.json"
    missing_au.write_text("[]", encoding="utf-8")
    gone = prove.read_adoption(missing_au)
    check("au absent when file empty", gone["status"] == "ABSENT" and gone["state"] is None)
    pack = prove.build_prove(now=NOW)
    habitat = pack["habitat"]
    check("live habitat read", habitat["status"] == "READ" and habitat["boundary"] == "HELD")
    check("live speed sums", habitat["waiting"] + habitat["measured"] + habitat["unavailable"] == habitat["rows"])
    check(
        "live receipt sums",
        habitat["receipt_present"] + habitat["receipt_absent"] + habitat["receipt_unreadable"] == habitat["rows"],
    )
    check("live not invented", habitat["leads_invented"] is False and habitat["receipts_invented"] == 0)
    check("live sla none", habitat["sla_target_seconds"] is None and habitat["sales"] is None)
    check("live not a board", habitat["operating_board"] is False)
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    habitat_n = conn.execute("SELECT COUNT(*) FROM core_leads WHERE lower(brand_id)='habitat'").fetchone()[0]
    ivy_n = conn.execute("SELECT COUNT(*) FROM core_leads WHERE lower(brand_id)='ivy'").fetchone()[0]
    conn.close()
    check("live habitat count", habitat["rows"] == habitat_n, str(habitat["rows"]))
    if ivy_n == 0:
        check("live ivy absent not zero", pack["ivy"]["status"] == "ABSENT" and pack["ivy"]["rows"] is None)
    else:
        check("live ivy counted", pack["ivy"]["status"] == "PRESENT" and pack["ivy"]["rows"] == ivy_n)
    check("live pack built", pack["honesty"]["maturity"] == "BUILT" and pack["honesty"]["proven"] is False)
    check("live cr open", pack["honesty"]["cr_state"] == "OPEN" and pack["honesty"]["cr_resolved"] is False)
    check("live cr next", pack["honesty"]["cr_next_action"] == GAP, str(pack["honesty"].get("cr_next_action")))
    check("gaps block higher", pack["gaps"] and all(g.get("blocks_proven") is True for g in pack["gaps"]))
    ids = {g["id"] for g in pack["gaps"]}
    check(
        "gap ids",
        {
            "ivy_surface",
            "habitat_operating_board",
            "first_touch_receipts",
            "klaviyo_write",
            "activecampaign_write",
            "metricool_write",
            "external_crm_write",
            "model_e_au",
            "ledger_gap_text",
            "change_request",
        }
        <= ids,
    )
    check("no email in pack", "email" not in json.dumps(pack))
    check("schema", pack["schema"] == prove.SCHEMA)
    team = {row["id"]: row for row in pack["red_team"]}
    check("pack red team", team["invent_proven"]["result"] == "REFUSED" and team["write_locks"]["result"] == "REFUSED")
    check("pack anon contract", team["anon_403"]["result"] == "FAIL_CLOSED")
    gap = prove.ledger_gap_text()
    check("ledger gap uncleared", gap == GAP, str(gap))
    check("ledger count stays", prove.ledger_row_count() == 77)


def test_source_and_routes() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("module names the CR", CR_ID in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not call run_ingest", "run_ingest(" not in src)
    check("module does not import klaviyo", "import core.habitat_klaviyo" not in src and "import lead_spine" not in src)
    check("module does not bind 8787", "8787" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/ggv/speed-to-lead-prove" in serve)
    check("page route registered", "/speed-to-lead-prove" in serve)
    check("metricool hint wired", 'path.endswith("/metricool")' in serve)
    check("klaviyo hint wired", 'path.endswith("/klaviyo")' in serve)
    check("ac hint wired", 'path.endswith("/activecampaign")' in serve)
    check("invent hint wired", 'path.endswith("/leads")' in serve)
    check("receipt hint wired", 'path.endswith("/receipts")' in serve)
    check("proven hint wired", 'path.endswith("/proven")' in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "speed-to-lead-prove.html").read_text(encoding="utf-8")
    check("page does not say proven as status", "PROVEN" not in page and "READY" not in page)
    check("page refuses promotion", "does not promote" in page)
    check("page refuses invent", "No lead is invented" in page and "No first-touch receipt is invented" in page)
    check("page names write locks", "Metricool, Klaviyo, and ActiveCampaign" in page)


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

        st, anon = call("GET", "/api/ggv/speed-to-lead-prove", None)
        check("anon GET 403", st == 403, str(anon)[:180])
        st, staff = call("GET", "/api/ggv/speed-to-lead-prove", STAFF)
        check("staff GET 403", st == 403, str(staff)[:180])
        st, owner = call("GET", "/api/ggv/speed-to-lead-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            flags = owner.get("honesty") or {}
            check("owner honesty bound", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner maturity built", flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            habitat = owner.get("habitat") or {}
            check("owner no sale", habitat.get("sales") is None and habitat.get("receipts_invented") == 0)
            check("owner sla none", habitat.get("sla_target_seconds") is None)
            check(
                "owner writes off",
                flags.get("klaviyo_write") is False
                and flags.get("metricool_write") is False
                and flags.get("activecampaign_write") is False,
            )
            ivy = owner.get("ivy") or {}
            if ivy.get("status") == "ABSENT":
                check("owner ivy not zero", ivy.get("rows") is None)
            else:
                check("owner ivy read", ivy.get("status") in {"PRESENT", "NOT_READ"})
            team = {row["id"]: row for row in owner.get("red_team") or []}
            check("owner invent proven", (team.get("invent_proven") or {}).get("result") == "REFUSED")
            check("owner write locks", (team.get("write_locks") or {}).get("result") == "REFUSED")
        st, page = call("GET", "/speed-to-lead-prove", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/speed-to-lead-prove", MATT)
        check("owner page 200", st == 200 and isinstance(page, str) and "does not promote" in page, str(st))
        st, html = call("GET", "/speed-to-lead-prove.html", None)
        check("anon html 403", st == 403, str(st))
        st, posted = call("POST", "/api/ggv/speed-to-lead-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, klaviyo = call("POST", "/api/ggv/speed-to-lead-prove/klaviyo", MATT)
        check("owner klaviyo 405", st == 405 and isinstance(klaviyo, dict) and klaviyo.get("error") == "klaviyo_write_refused", str(klaviyo)[:160])
        st, metricool = call("POST", "/api/ggv/speed-to-lead-prove/metricool", MATT)
        check("owner metricool 405", st == 405 and isinstance(metricool, dict) and metricool.get("error") == "metricool_write_refused", str(metricool)[:160])
        st, ac = call("POST", "/api/ggv/speed-to-lead-prove/activecampaign", MATT)
        check("owner ac 405", st == 405 and isinstance(ac, dict) and ac.get("error") == "activecampaign_write_refused", str(ac)[:160])
        st, crm = call("POST", "/api/ggv/speed-to-lead-prove/crm", MATT)
        check("owner crm 405", st == 405 and isinstance(crm, dict) and crm.get("error") == "external_crm_write_refused", str(crm)[:160])
        st, invented = call("POST", "/api/ggv/speed-to-lead-prove/leads", MATT)
        check("owner invent 405", st == 405 and isinstance(invented, dict) and invented.get("error") == "invent_lead_refused", str(invented)[:160])
        st, receipt = call("POST", "/api/ggv/speed-to-lead-prove/receipts", MATT)
        check("owner receipt 405", st == 405 and isinstance(receipt, dict) and receipt.get("error") == "invent_receipt_refused", str(receipt)[:160])
        st, scored = call("POST", "/api/ggv/speed-to-lead-prove/proven", MATT)
        check("owner proven 405", st == 405 and isinstance(scored, dict) and scored.get("error") == "score_refused", str(scored)[:160])
        st, _ = call("POST", "/api/ggv/speed-to-lead-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, put = call("PUT", "/api/ggv/speed-to-lead-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:120])
        st, patched = call("PATCH", "/api/ggv/speed-to-lead-prove", MATT)
        check("owner PATCH 405", st == 405 and isinstance(patched, dict) and patched.get("error") == "writes_refused", str(patched)[:120])
        st, anon_put = call("PUT", "/api/ggv/speed-to-lead-prove/leads", None)
        check("anon PUT 403", st == 403, str(st))
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    ledger_before = _sha(LEDGER)
    history_before = _sha(HISTORY)
    credits_before = _sha(CREDITS)
    wip_before = {rel: _sha(ROOT / rel) for rel in WIP}
    cr_before = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True).execute(
        "SELECT state, blocker_class, next_action FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        test_classify()
        test_ivy_and_refusals(td)
        test_surfaces_and_live(td)
    test_source_and_routes()
    test_api()
    check("ledger bytes unchanged", _sha(LEDGER) == ledger_before)
    check("score history unchanged", _sha(HISTORY) == history_before)
    check("credits doc unchanged", _sha(CREDITS) == credits_before)
    cr_after = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True).execute(
        "SELECT state, blocker_class, next_action FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    check("cr row unchanged", cr_before == cr_after == ("OPEN", "NEEDS_ENGINEERING", GAP), str(cr_after))
    for rel, digest in wip_before.items():
        check(f"WIP untouched {Path(rel).name}", _sha(ROOT / rel) == digest)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
