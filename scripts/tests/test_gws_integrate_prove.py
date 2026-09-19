#!/usr/bin/env python3
"""CAP-INTG-03 workspace prove. Four surfaces. No probe. No GREEN. No PROVEN."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import shutil
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
os.environ.pop("WOLF_ESB_SQLITE", None)

from core import gws_integrate_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "gws_integrate_prove.py"
CR_ID = "CR-260e724b776f2b89"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
STEP_IDS = (
    "CHK-NAME-GMAIL",
    "CHK-NAME-CALENDAR",
    "CHK-NAME-DRIVE",
    "CHK-NAME-AUTH",
    "CHK-NOT-CONFLATED",
    "CHK-DOCUMENT-GAPS",
    "CHK-NO-PROBE",
    "CHK-NO-SCOPE-WIDEN",
    "CHK-NO-PRODUCTION",
    "CHK-NO-RESOLVE",
)
SURFACE_IDS = ("SURF-GMAIL", "SURF-CALENDAR", "SURF-DRIVE", "SURF-AUTH")
GAP_IDS = (
    "GAP-GMAIL-ABSENT",
    "GAP-CALENDAR-ABSENT",
    "GAP-DRIVE-ABSENT",
    "GAP-AUTH-ABSENT",
    "GAP-NOT-GREEN",
    "GAP-SCOPES-NOT-WIDENED",
)
READERS = (
    "scripts/core/gmail_reader.py",
    "scripts/core/calendar_reader.py",
    "scripts/core/drive_reader.py",
    "scripts/core/gws_oauth.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT state, blocker_class, capability, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _resolved_count() -> int:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'").fetchone()[0]
        )
    finally:
        conn.close()


def _copy_log() -> dict:
    return json.loads(json.dumps(prove.not_run_log()))


def test_live_framework() -> None:
    report = prove.build_framework()
    steps = report["checklist"]
    named = report["surfaces"]
    gaps = report["gaps"]
    check("ten steps", [row["id"] for row in steps] == list(STEP_IDS), str([row["id"] for row in steps]))
    check(
        "none executed",
        all(row["executed"] is False and row["result"] == "NOT_RUN" and row["slot"] == "EMPTY" and row["required"] is True for row in steps),
    )
    check("executed count zero", report["checklist_executed"] == 0 and report["checklist_count"] == 10)
    check("empty slots", report["empty_slot_count"] == 14 and report["slots_filled"] is False)
    check("status not run", report["status"] == "NOT_RUN" and report["probed"] is False and report["green_claimed"] is False)
    check("four surfaces", [row["id"] for row in named] == list(SURFACE_IDS) and report["surface_count"] == 4)
    check("six gaps", [row["id"] for row in gaps] == list(GAP_IDS) and report["gap_count"] == 6)
    by_id = {row["id"]: row for row in named}
    sources = {row["source_system"] for row in named}
    check(
        "not conflated",
        report["conflated"] is False
        and sources == {"gmail", "google-calendar", "google-drive", "google-oauth"}
        and by_id["SURF-GMAIL"]["source_system"] != by_id["SURF-CALENDAR"]["source_system"]
        and "SURF-CALENDAR" in by_id["SURF-GMAIL"]["not_same_as"]
        and "SURF-GMAIL" in by_id["SURF-AUTH"]["not_same_as"]
        and all(row["conflated"] is False for row in named),
    )
    check(
        "none called",
        all(
            row["called"] is False
            and row["network"] is False
            and row["probed"] is False
            and row["write"] is False
            and row["scopes_widened"] is False
            and row["green"] is False
            and row["health"] == "NOT_PROBED"
            and row["slot"] == "EMPTY"
            and row["reader_present"] is False
            for row in named
        ),
    )
    check(
        "counts stay null",
        all(row["messages"] is None and row["events"] is None and row["files"] is None and row["scopes"] is None for row in named)
        and report["messages"] is None
        and report["events"] is None
        and report["files"] is None
        and report["scopes"] is None,
    )
    by_gap = {row["id"]: row for row in gaps}
    check(
        "reader gaps absent",
        by_gap["GAP-GMAIL-ABSENT"]["status"] == "ABSENT"
        and by_gap["GAP-CALENDAR-ABSENT"]["status"] == "ABSENT"
        and by_gap["GAP-DRIVE-ABSENT"]["status"] == "ABSENT"
        and by_gap["GAP-AUTH-ABSENT"]["status"] == "ABSENT"
        and all(row["messages"] is None and row["scopes"] is None and row["called"] is False for row in gaps),
    )
    check(
        "green and scopes refused gaps",
        by_gap["GAP-NOT-GREEN"]["status"] == "REFUSED"
        and by_gap["GAP-SCOPES-NOT-WIDENED"]["status"] == "REFUSED"
        and by_gap["GAP-NOT-GREEN"]["probed"] is False
        and "GREEN" in by_gap["GAP-NOT-GREEN"]["why"]
        and by_gap["GAP-SCOPES-NOT-WIDENED"]["scopes"] is None,
    )
    split = report["distinction"]
    check(
        "distinction documented",
        split["gmail"] == "SURF-GMAIL"
        and split["calendar"] == "SURF-CALENDAR"
        and split["drive"] == "SURF-DRIVE"
        and split["auth"] == "SURF-AUTH"
        and split["same_surface"] is False
        and split["conflated"] is False
        and split["distinction"] == "DOCUMENTED"
        and split["slot"] == "EMPTY",
    )
    schema = report["schema"]
    check("schema id", schema["schema_id"] == prove.SCHEMA_ID and schema["additionalProperties"] is False)
    check("schema only not-run", schema["status_enum"] == ["NOT_RUN"] and schema["slot_enum"] == ["EMPTY"])
    check(
        "schema names refused success",
        "SUCCESS" in schema["refused_status"] and "READY" in schema["refused_status"] and "PROVEN" in schema["refused_status"] and "GREEN" in schema["refused_status"],
    )
    log = report["log"]
    check("log not run", log["status"] == "NOT_RUN" and log["result"] == "NOT_RUN" and log["prove_id"] is None)
    check(
        "log claims nothing",
        log["gmail_called"] is False
        and log["calendar_called"] is False
        and log["drive_called"] is False
        and log["auth_called"] is False
        and log["conflated"] is False
        and log["probed"] is False
        and log["scopes_widened"] is False
        and log["green_claimed"] is False
        and log["cr_resolved"] is False
        and log["messages"] is None
        and log["scopes"] is None,
    )
    check("log does not claim ready", log["ready_claimed"] is False and log["proven_claimed"] is False)
    check("log valid", report["log_valid"] is True)
    dumped_log = json.dumps(log)
    check("log text has no success word", '"SUCCESS"' not in dumped_log and '"GREEN"' not in dumped_log and '"PROVEN"' not in dumped_log)
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-INTG-03")
    check("honesty.cr_blocker", flags.get("cr_blocker") == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("honesty.cr_next", flags.get("cr_next_action") == "CAP-bound INTEGRATE prove pack", str(flags.get("cr_next_action")))
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "BUILT")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False)
    check("honesty.not_invented", flags.get("invented_proven") is False and flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check(
        "honesty.no_call",
        flags.get("gmail_called") is False
        and flags.get("calendar_called") is False
        and flags.get("drive_called") is False
        and flags.get("auth_called") is False
        and flags.get("probed") is False
        and flags.get("scopes_widened") is False
        and flags.get("green_claimed") is False
        and flags.get("conflated") is False,
    )
    check("honesty.counts null", flags.get("messages") is None and flags.get("scopes") is None and flags.get("events") is None and flags.get("files") is None)
    check("pack flags", report["ledger_write"] is False and report["external_writes"] is False and report["production_mutated"] is False and report["cr_resolved"] is False)
    one = prove.read_step("CHK-NO-PROBE")
    check("read probe step", one["ok"] is True and one["step"]["executed"] is False and one["step"]["slot"] == "EMPTY" and one["probed"] is False)
    check("read step bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    gmail = prove.read_surface("SURF-GMAIL")
    check("read gmail", gmail["ok"] is True and gmail["surface"]["called"] is False and gmail["surface"]["health"] == "NOT_PROBED" and gmail["surface"]["source_system"] == "gmail")
    calendar = prove.read_surface("SURF-CALENDAR")
    check("read calendar", calendar["surface"]["source_system"] == "google-calendar" and calendar["surface"]["reader_present"] is False and calendar["calendar_called"] is False)
    drive = prove.read_surface("SURF-DRIVE")
    check("read drive", drive["surface"]["source_system"] == "google-drive" and drive["drive_called"] is False and drive["surface"]["files"] is None)
    auth = prove.read_surface("SURF-AUTH")
    check("read auth", auth["surface"]["source_system"] == "google-oauth" and auth["auth_called"] is False and auth["surface"]["scopes"] is None and auth["scopes_widened"] is False)
    gap = prove.read_gap("GAP-GMAIL-ABSENT")
    check("read gmail gap", gap["gap"]["status"] == "ABSENT" and gap["gap"]["messages"] is None)
    ref = prove.read_ref("GAP-NOT-GREEN")
    check("read ref gap", ref["gap"]["status"] == "REFUSED" and ref["green_claimed"] is False)
    try:
        prove.read_ref("BRAND-HABITAT")
        check("unknown brand not invented", False)
    except prove.GwsProveError as exc:
        check("unknown brand not invented", exc.code == "not_found", exc.code)
    validated = prove.validate_log(prove.not_run_log())
    check("validate exemplar", validated["ok"] is True and validated["valid"] is True and validated["probed"] is False and validated["green_claimed"] is False and validated["conflated"] is False)


def test_refuses(td: Path) -> None:
    before = list(td.iterdir())
    cases = [
        ("gmail called", {"gmail_called": True}, "gmail_write_refused"),
        ("gmail write", {"gmail_write": True}, "gmail_write_refused"),
        ("calendar called", {"calendar_called": True}, "calendar_write_refused"),
        ("calendar write", {"calendar_write": True}, "calendar_write_refused"),
        ("drive called", {"drive_called": True}, "drive_write_refused"),
        ("drive write", {"drive_write": True}, "drive_write_refused"),
        ("auth called", {"auth_called": True}, "oauth_write_refused"),
        ("oauth write", {"oauth_write": True}, "oauth_write_refused"),
        ("probe flag", {"probed": True}, "probe_refused"),
        ("scopes widened", {"scopes_widened": True}, "scope_widen_refused"),
        ("green flag", {"green_claimed": True}, "green_refused"),
        ("conflate flag", {"conflated": True}, "conflate_refused"),
        ("production flag", {"production_mutated": True}, "production_refused"),
        ("resolve flag", {"cr_resolved": True}, "resolve_refused"),
        ("slots flag", {"slots_filled": True}, "slots_refused"),
        ("ready flag", {"ready_claimed": True}, "ready_refused"),
        ("proven flag", {"proven_claimed": True}, "proven_refused"),
        ("success status", {"status": "SUCCESS"}, "success_refused"),
        ("green status", {"status": "GREEN"}, "green_refused"),
        ("read_ok status", {"status": "READ_OK"}, "green_refused"),
        ("probed status", {"status": "PROBED"}, "probe_refused"),
        ("widened status", {"status": "WIDENED"}, "scope_widen_refused"),
        ("proved status", {"status": "PROVED"}, "success_refused"),
        ("ready status", {"status": "READY"}, "ready_refused"),
        ("proven status", {"status": "PROVEN"}, "proven_refused"),
        ("resolved status", {"status": "RESOLVED"}, "resolve_refused"),
        ("filled status", {"status": "FILLED"}, "slots_refused"),
        ("messages zero", {"messages": 0}, "invent_metrics_refused"),
        ("events zero", {"events": 0}, "invent_metrics_refused"),
        ("files zero", {"files": 0}, "invent_metrics_refused"),
        ("scopes empty list", {"scopes": []}, "invent_metrics_refused"),
    ]
    for name, patch, code in cases:
        payload = _copy_log()
        payload.update(patch)
        try:
            prove.validate_log(payload)
            check(name, False, "accepted")
        except prove.GwsProveError as exc:
            check(name, exc.code == code, exc.code)
    called = _copy_log()
    called["surfaces"][0]["called"] = True
    try:
        prove.validate_log(called)
        check("gmail row called refused", False)
    except prove.GwsProveError as exc:
        check("gmail row called refused", exc.code == "gmail_write_refused", exc.code)
    swapped = _copy_log()
    swapped["surfaces"][1]["source_system"] = "gmail"
    try:
        prove.validate_log(swapped)
        check("calendar source swapped refused", False)
    except prove.GwsProveError as exc:
        check("calendar source swapped refused", exc.code == "conflate_refused", exc.code)
    emptied = _copy_log()
    emptied["surfaces"][0]["not_same_as"] = []
    try:
        prove.validate_log(emptied)
        check("empty not_same_as refused", False)
    except prove.GwsProveError as exc:
        check("empty not_same_as refused", exc.code == "conflate_refused", exc.code)
    greened = _copy_log()
    greened["surfaces"][0]["health"] = "GREEN"
    try:
        prove.validate_log(greened)
        check("surface green refused", False)
    except prove.GwsProveError as exc:
        check("surface green refused", exc.code == "green_refused", exc.code)
    counted = _copy_log()
    counted["surfaces"][2]["files"] = 0
    try:
        prove.validate_log(counted)
        check("drive zero refused", False)
    except prove.GwsProveError as exc:
        check("drive zero refused", exc.code == "invent_metrics_refused", exc.code)
    filled = _copy_log()
    filled["checklist"][6]["slot"] = "FILLED"
    try:
        prove.validate_log(filled)
        check("filled slot refused", False)
    except prove.GwsProveError as exc:
        check("filled slot refused", exc.code == "slots_refused", exc.code)
    try:
        prove.guard_query(probe="1")
        check("query probe refused", False)
    except prove.GwsProveError as exc:
        check("query probe refused", exc.code == "probe_refused", exc.code)
    try:
        prove.guard_query(prove="1")
        check("query prove refused", False)
    except prove.GwsProveError as exc:
        check("query prove refused", exc.code == "proven_refused", exc.code)
    try:
        prove.guard_query(green="1")
        check("query green refused", False)
    except prove.GwsProveError as exc:
        check("query green refused", exc.code == "green_refused", exc.code)
    try:
        prove.guard_query(scopes="widen")
        check("query scopes refused", False)
    except prove.GwsProveError as exc:
        check("query scopes refused", exc.code == "scope_widen_refused", exc.code)
    try:
        prove.guard_query(messages="0")
        check("query messages zero refused", False)
    except prove.GwsProveError as exc:
        check("query messages zero refused", exc.code == "invent_metrics_refused", exc.code)
    try:
        prove.guard_query(gmail="1")
        check("query gmail refused", False)
    except prove.GwsProveError as exc:
        check("query gmail refused", exc.code == "gmail_write_refused", exc.code)
    try:
        prove.guard_query(write="1")
        check("query write refused", False)
    except prove.GwsProveError as exc:
        check("query write refused", exc.code == "writes_refused", exc.code)
    try:
        prove.guard_query(production="1")
        check("query production refused", False)
    except prove.GwsProveError as exc:
        check("query production refused", exc.code == "production_refused", exc.code)
    try:
        prove.guard_query(ready="1")
        check("query ready refused", False)
    except prove.GwsProveError as exc:
        check("query ready refused", exc.code == "ready_refused", exc.code)
    try:
        prove.guard_query(resolve="yes")
        check("query resolve refused", False)
    except prove.GwsProveError as exc:
        check("query resolve refused", exc.code == "resolve_refused", exc.code)
    try:
        prove.refuse_external_write({})
        check("empty write refused", False)
    except prove.GwsProveError as exc:
        check("empty write refused", exc.code == "writes_refused", exc.code)
    try:
        prove.refuse_external_write({"action": "probe"})
        check("action probe refused", False)
    except prove.GwsProveError as exc:
        check("action probe refused", exc.code == "probe_refused", exc.code)
    try:
        prove.refuse_external_write({"action": "green"})
        check("action green refused", False)
    except prove.GwsProveError as exc:
        check("action green refused", exc.code == "green_refused", exc.code)
    try:
        prove.refuse_external_write({"action": "widen"})
        check("action widen refused", False)
    except prove.GwsProveError as exc:
        check("action widen refused", exc.code == "scope_widen_refused", exc.code)
    try:
        prove.read_ref("GREEN")
        check("green token refused", False)
    except prove.GwsProveError as exc:
        check("green token refused", exc.code == "green_refused", exc.code)
    try:
        prove.read_ref("OAUTH-WIDEN")
        check("widen token refused", False)
    except prove.GwsProveError as exc:
        check("widen token refused", exc.code == "scope_widen_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/wolf-system/ledger.json"))
        check("wolf-system path refused", False)
    except prove.GwsProveError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        prove.ledger_cap_state(td / "alchemist" / "ledger.json")
        check("alchemist path refused", False)
    except prove.GwsProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("https://gmail.googleapis.com/gmail/v1/users/me/messages"))
        check("google network path refused", False)
    except prove.GwsProveError as exc:
        check("google network path refused", exc.code == "probe_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/credentials.json"))
        check("credential path refused", False)
    except prove.GwsProveError as exc:
        check("credential path refused", exc.code == "oauth_write_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/auth/gmail.modify"))
        check("scope grant path refused", False)
    except prove.GwsProveError as exc:
        check("scope grant path refused", exc.code == "scope_widen_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/production/money.sqlite"))
        check("production path refused", False)
    except prove.GwsProveError as exc:
        check("production path refused", exc.code == "production_refused", exc.code)
    check("refuse left no files", list(td.iterdir()) == before)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-INTG-03"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = prove.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("higher still not a probe", flags["probed"] is False and flags["gmail_called"] is False and flags["ready"] is False and flags["green_claimed"] is False)
    ready = json.loads(before.decode())
    ready["CAP-INTG-03"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = prove.honesty_flags(ready_path)
    check("ready fixture ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY" and ready_flags["invented_ready"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-INTG-03"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = prove.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False and junk_flags["green_claimed"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = prove.honesty_flags(catalog_db=missing_db)
    check("missing cr not invented", absent["cr_present"] is False and absent["cr_resolved"] is False and absent["cr_id"] == CR_ID)
    check("live ledger untouched after junk", LEDGER.read_bytes() == before)


def test_source_and_files() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    joined = " ".join(imported)
    check("module does not import wolf_intelligence", "wolf_intelligence" not in joined)
    check("module does not import google client", "google" not in joined and "googleapiclient" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("no scope url grant", "https://www.googleapis.com/auth/" not in src)
    check("source has no googleapiclient", "googleapiclient" not in src)
    for rel in READERS:
        check(f"reader absent {Path(rel).name}", not (ROOT / rel).is_file())
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/gws-integrate-prove" in serve)
    check("page route registered", "/gws-integrate-prove" in serve)
    check("gmail route refused in server", "/api/gws-integrate-prove/gmail-write" in serve)
    check("probe route refused in server", "/api/gws-integrate-prove/probe" in serve)
    check("scope route refused in server", "/api/gws-integrate-prove/oauth-widen" in serve)
    check("green route refused in server", "/api/gws-integrate-prove/green" in serve)
    check("prove route refused in server", "/api/gws-integrate-prove/prove" in serve)
    check("resolve route refused in server", "/api/gws-integrate-prove/resolve" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
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
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if "json" in ctype or url_path.startswith("/api/"):
                        try:
                            return resp.status, json.loads(raw.decode())
                        except json.JSONDecodeError:
                            return resp.status, raw
                    return resp.status, raw
            except HTTPError as exc:
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode())
                except json.JSONDecodeError:
                    parsed = raw
                return exc.code, parsed

        st, _anon = call("GET", "/api/gws-integrate-prove", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/gws-integrate-prove", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/gws-integrate-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner ten steps", owner.get("checklist_count") == 10 and owner.get("checklist_executed") == 0)
            check("owner status", owner.get("status") == "NOT_RUN" and owner.get("probed") is False and owner.get("green_claimed") is False)
            check("owner not conflated", owner.get("conflated") is False and (owner.get("distinction") or {}).get("slot") == "EMPTY")
            check("owner surfaces empty", owner.get("surface_count") == 4 and owner.get("gmail_called") is False and owner.get("auth_called") is False)
            check("owner counts null", owner.get("messages") is None and owner.get("scopes") is None and owner.get("events") is None)
            check("owner log quiet", (owner.get("log") or {}).get("status") == "NOT_RUN" and (owner.get("log") or {}).get("probed") is False)
            check("owner no write", owner.get("production_mutated") is False and owner.get("cr_resolved") is False and owner.get("scopes_widened") is False)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID and (owner.get("honesty") or {}).get("cr_state") == "OPEN")
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling", (owner.get("honesty") or {}).get("maturity") == "BUILT" and (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
            systems = {row["source_system"] for row in owner.get("surfaces") or []}
            check("owner systems differ", systems == {"gmail", "google-calendar", "google-drive", "google-oauth"})
            healths = {row["health"] for row in owner.get("surfaces") or []}
            check("owner health not green", healths == {"NOT_PROBED"})
        st, steps = call("GET", "/api/gws-integrate-prove/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(steps, dict) and steps.get("checklist_count") == 10, str(st))
        st, schema = call("GET", "/api/gws-integrate-prove/schema", MATT)
        check("owner schema 200", st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == prove.SCHEMA_ID, str(st))
        st, log = call("GET", "/api/gws-integrate-prove/log", MATT)
        check("owner log 200", st == 200 and isinstance(log, dict) and (log.get("log") or {}).get("green_claimed") is False, str(st))
        st, surfaces = call("GET", "/api/gws-integrate-prove/surfaces", MATT)
        check("owner surfaces 200", st == 200 and isinstance(surfaces, dict) and surfaces.get("surface_count") == 4, str(st))
        st, gaps = call("GET", "/api/gws-integrate-prove/gaps", MATT)
        check("owner gaps 200", st == 200 and isinstance(gaps, dict) and gaps.get("gap_count") == 6, str(st))
        st, one = call("GET", "/api/gws-integrate-prove/SURF-GMAIL", MATT)
        check("owner surface 200", st == 200 and isinstance(one, dict) and (one.get("surface") or {}).get("called") is False, str(st))
        st, missing = call("GET", "/api/gws-integrate-prove/NO-SUCH", MATT)
        check("unknown id 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/gws-integrate-prove", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, (bytes, bytearray)) and b"Gmail is not Calendar" in page and b"not GREEN" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/gws-integrate-prove", None)
        check("anon page 403", st == 403, str(st))
        st, _post_anon = call("POST", "/api/gws-integrate-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/gws-integrate-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, put = call("PUT", "/api/gws-integrate-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/gws-integrate-prove", MATT)
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, gwrite = call("POST", "/api/gws-integrate-prove/gmail-write", MATT)
        check("gmail POST 405", st == 405 and isinstance(gwrite, dict) and gwrite.get("error") == "gmail_write_refused", str(gwrite)[:180])
        st, cwrite = call("POST", "/api/gws-integrate-prove/calendar-write", MATT)
        check("calendar POST 405", st == 405 and isinstance(cwrite, dict) and cwrite.get("error") == "calendar_write_refused", str(cwrite)[:180])
        st, dwrite = call("POST", "/api/gws-integrate-prove/drive-write", MATT)
        check("drive POST 405", st == 405 and isinstance(dwrite, dict) and dwrite.get("error") == "drive_write_refused", str(dwrite)[:180])
        st, oauth = call("POST", "/api/gws-integrate-prove/oauth-widen", MATT)
        check("widen POST 405", st == 405 and isinstance(oauth, dict) and oauth.get("error") == "scope_widen_refused", str(oauth)[:180])
        st, probe = call("POST", "/api/gws-integrate-prove/probe", MATT)
        check("probe POST 405", st == 405 and isinstance(probe, dict) and probe.get("error") == "probe_refused", str(probe)[:180])
        st, green = call("POST", "/api/gws-integrate-prove/green", MATT)
        check("green POST 405", st == 405 and isinstance(green, dict) and green.get("error") == "green_refused", str(green)[:180])
        st, conflate = call("POST", "/api/gws-integrate-prove/conflate", MATT)
        check("conflate POST 405", st == 405 and isinstance(conflate, dict) and conflate.get("error") == "conflate_refused", str(conflate)[:180])
        st, prod = call("POST", "/api/gws-integrate-prove/production", MATT)
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, proved = call("POST", "/api/gws-integrate-prove/prove", MATT)
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, resolve = call("POST", "/api/gws-integrate-prove/resolve", MATT)
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, fill = call("POST", "/api/gws-integrate-prove/fill", MATT)
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, qprobe = call("GET", "/api/gws-integrate-prove?probe=1", MATT)
        check("query probe http refused", st == 405 and isinstance(qprobe, dict) and qprobe.get("error") == "probe_refused", str(qprobe)[:180])
        st, qgreen = call("GET", "/api/gws-integrate-prove?green=1", MATT)
        check("query green http refused", st == 405 and isinstance(qgreen, dict) and qgreen.get("error") == "green_refused", str(qgreen)[:180])
        st, qprove = call("GET", "/api/gws-integrate-prove?prove=1", MATT)
        check("query prove http refused", st == 405 and isinstance(qprove, dict) and qprove.get("error") == "proven_refused", str(qprove)[:180])
        st, qmsg = call("GET", "/api/gws-integrate-prove?messages=0", MATT)
        check("query messages http refused", st == 405 and isinstance(qmsg, dict) and qmsg.get("error") == "invent_metrics_refused", str(qmsg)[:180])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="gws-integrate-prove-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_framework()
        test_refuses(td)
        test_ledger_ceiling(td)
        test_source_and_files()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    check("credits doc unchanged", hashlib.sha256(CREDITS.read_bytes()).hexdigest() == credits_before)
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger still 77", len(doc) == 77, str(len(doc)))
    check("CAP-INTG-03 stays BUILT", doc["CAP-INTG-03"][0] == "BUILT")
    check("CR row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("CR stays OPEN", cr_before is not None and cr_before[0] == "OPEN")
    check("resolved count unchanged", _resolved_count() == resolved_before, str(_resolved_count()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
