#!/usr/bin/env python3
"""CAP-STRAT-02 Owner Radar prove. No ledger write. No invented pulse. No PROVEN."""
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

from core import strat_radar_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "strat_radar_prove.py"
CR_ID = "CR-7a145ad69d8bf3c5"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
GAP_TEXT = "CAP-bound Model C prove; Progress is not this CAP alone"


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


def _tile_html(extra: str = "") -> str:
    tiles = "".join('<article id="%s"></article>' % tile for tile in prove.REQUIRED_TILES)
    return (
        "<h1>Wolf Radar</h1><p>Owner plan board.</p>"
        "Never invent. Never paint RAG green."
        '<button data-entity="GGV"></button>'
        '<button class="stub" data-entity="AMG"></button>'
        '<button class="stub" data-entity="BZG"></button>'
        '<div class="plan-progress-strip"></div>'
        '<form action="/api/radar/task"></form>'
        + tiles
        + extra
    )


def _board_text(extra: str = "") -> str:
    return (
        'MODE = "LEARN"\n'
        'VESPER = "AMBER"\n'
        "def public(who=\"\"):\n"
        '    """Must never write tasks.json."""\n'
        '    return {"auto_now": False}\n'
        "def create_task(payload, who):\n"
        "    return None\n"
        "Never invent metrics, never paint RAG green\n"
        "POST /api/radar stays 405\n"
        + extra
    )


def test_entities_and_pulse() -> None:
    unread = prove.pulse_binding(None, None)
    check("unread pulse", unread["status"] == "NOT_READ")
    check("unread counts none", unread["pulse_count"] is None and unread["exception_count"] is None)
    check("unread quiet none", unread["quiet"] is None)
    absent = prove.pulse_binding(_tile_html(), _board_text("except Exception as exc:\n"))
    check("live-shaped pulse absent", absent["status"] == "ABSENT")
    check("absent counts none", absent["pulse_count"] is None and absent["exception_count"] is None)
    check("python exception is not the binding", absent["exceptions_named"] is False)
    named = prove.pulse_binding(_tile_html("Pulse + Exceptions"), _board_text("progressive quiet"))
    check("named pulse", named["status"] == "NAMED" and named["pulse_named"] and named["exceptions_named"])
    check("name is not a count", named["pulse_count"] is None and named["quiet"] is False)
    bird_unread = prove.birdseye(None, unread)
    check("bird unread", bird_unread["status"] == "NOT_READ" and bird_unread["tile_count"] is None)
    bird = prove.birdseye(_tile_html(), absent)
    check("bird read not satisfied", bird["status"] == "READ" and bird["satisfied"] is False)
    check("bird until satisfied", bird["until_satisfied"] is True and bird["quiet"] is False)
    check("bird tile count", bird["tile_count"] == len(prove.REQUIRED_TILES))
    full = prove.birdseye(_tile_html("Pulse + Exceptions"), named)
    check("named quiet still not operating quiet", full["satisfied"] is True and full["quiet"] is False)
    try:
        prove.entity_surface("  ")
        check("blank entity refused", False, "no raise")
    except prove.ProveError as exc:
        check("blank entity refused", exc.code == "invalid", exc.code)
    try:
        prove.entity_surface("HABITAT")
        check("unknown entity refused", False, "no raise")
    except prove.ProveError as exc:
        check("unknown entity refused", exc.code == "invalid", exc.code)
    ggv = prove.entity_surface("ggv")
    check("ggv live no numbers", ggv["state"] == "live" and ggv["numbers"] is None)
    amg = prove.entity_surface("AMG")
    check("amg stub", amg["state"] == "stub" and amg["numbers"] is None and amg["operating_board"] is False)
    try:
        prove.entity_surface("BZG", numbers={"leads": 0})
        check("bzg numbers refused", False, "no raise")
    except prove.ProveError as exc:
        check("bzg numbers refused", exc.code == "boundary_breach", exc.code)
    try:
        prove.entity_surface("GGV", numbers=25.5)
        check("ggv score refused", False, "no raise")
    except prove.ProveError as exc:
        check("ggv score refused", exc.code == "invent_refused", exc.code)
    try:
        prove.reject_progress_as_cap(25.5)
        check("progress percent refused", False, "no raise")
    except prove.ProveError as exc:
        check("progress percent refused", exc.code == "progress_not_this_cap", exc.code)
    prove.reject_progress_as_cap(None)
    check("unread progress percent allowed", True)
    mission = prove.mission_control_binding(_tile_html(), _board_text("# Mission Control / Mars\n"))
    check("comment is alias not a board", mission["status"] == "ALIAS" and mission["separate_board"] is False)
    titled = prove.mission_control_binding("<h1>Mission Control</h1>", "")
    check("titled mission still not a write", titled["status"] == "PRESENT" and titled["separate_board"] is True)


def test_honesty_and_refusals(td: Path) -> None:
    flags = prove.honesty_flags()
    check("cr bound", flags["cr_id"] == CR_ID and flags["cr_bound"] is True)
    check("cr present", flags["cr_present"] is True)
    check("cr open", flags["cr_state"] == "OPEN", str(flags.get("cr_state")))
    check("cr blocker", flags["cr_blocker"] == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("cr not resolved", flags["cr_resolved"] is False)
    check("cr cap", flags["cr_capability"] == "CAP-STRAT-02")
    check("cr next action", flags["cr_next_action"] == GAP_TEXT, str(flags.get("cr_next_action")))
    check("live built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling built", flags["maturity_ceiling"] == "BUILT")
    check("not proven", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("no raise", flags["model_c_maturity_raised"] is False and flags["model_c_write"] is False)
    check("no cr mutate", flags["cr_mutated"] is False)
    check("progress not this cap", flags["progress_dashboard_is_not_this_cap"] is True)
    check("progress unused", flags["progress_used_as_cap"] is False)
    check("strat01 not this prove", flags["cap_strat_01_not_this_prove"] is True)
    check("radar not executed", flags["radar_executed"] is False and flags["create_task_called"] is False)
    proven = td / "proven.json"
    proven.write_text(json.dumps({"CAP-STRAT-02": ["PROVEN", "fixture", "gap"]}), encoding="utf-8")
    high = prove.honesty_flags(proven)
    check("fixture proven reported", high["proven"] is True and high["maturity_ceiling"] == "PROVEN")
    check("fixture does not raise live", prove.ledger_cap_state() == "BUILT")
    ready = td / "ready.json"
    ready.write_text(json.dumps({"CAP-STRAT-02": ["READY"]}), encoding="utf-8")
    ready_flags = prove.honesty_flags(ready)
    check("fixture ready reported", ready_flags["ready"] is True and ready_flags["maturity_ceiling"] == "READY")
    specified = td / "specified.json"
    specified.write_text(json.dumps({"CAP-STRAT-02": ["SPECIFIED"]}), encoding="utf-8")
    low = prove.honesty_flags(specified)
    check("specified stays below", low["maturity"] == "SPECIFIED" and low["proven"] is False and low["maturity_ceiling"] == "BUILT")
    junk = td / "junk.json"
    junk.write_text(json.dumps({"CAP-STRAT-02": ["GREEN"]}), encoding="utf-8")
    junk_flags = prove.honesty_flags(junk)
    check("non maturity unknown", junk_flags["ledger_maturity"] == "UNKNOWN" and junk_flags["proven"] is False)
    empty_db = td / "empty.sqlite"
    sqlite3.connect(empty_db).close()
    missing = prove.honesty_flags(catalog_db=empty_db)
    check("missing table not present", missing["cr_present"] is False and missing["cr_bound"] is True)
    check("missing table not resolved", missing["cr_resolved"] is False)
    try:
        prove.inspect_radar(radar_html=td / "alchemist" / "radar.html")
        check("alchemist path refused", False, "no raise")
    except prove.ProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    for label, call, code in (
        ("write", lambda: prove.refuse_external_write({}), "writes_refused"),
        ("task", lambda: prove.refuse_external_write({"create_task": True}), "create_task_refused"),
        ("progress", lambda: prove.refuse_external_write({"system_pct": 25.5}), "progress_not_this_cap"),
        ("score", lambda: prove.refuse_external_write({"proven": True}), "score_refused"),
    ):
        try:
            call()
            check(label + " refused", False, "no raise")
        except prove.ProveError as exc:
            check(label + " refused", exc.code == code, exc.code)


def test_surfaces_and_live(td: Path) -> None:
    html_path = td / "radar.html"
    board_path = td / "radar_board.py"
    html_path.write_text(_tile_html(), encoding="utf-8")
    board_path.write_text(_board_text("Mission Control / Radar\n"), encoding="utf-8")
    surfaces = prove.inspect_radar(html_path, board_path)
    html = surfaces["html"]
    board = surfaces["board"]
    check("fixture html present", html["present"] and html["executed"] is False)
    check("fixture never invent", html["never_invent_stated"] is True)
    check("fixture stubs", html["amg_stub"] and html["bzg_stub"] and html["ggv_live"])
    check("fixture strip not this cap", html["progress_strip_present"] and html["progress_strip_is_this_cap"] is False)
    check("fixture now not called", html["now_write_path_present"] and html["now_write_called_by_prove"] is False)
    check("fixture board not executed", board["present"] and board["executed"] is False and board["posts"] is False)
    check("fixture public and task", board["has_public"] and board["has_create_task"] and board["create_task_called_by_prove"] is False)
    check("fixture locks", board["learn_mode"] and board["vesper_amber"] and board["auto_now_false_stated"])
    check("fixture 405 stated", board["post_radar_405_stated"] is True)
    progress_page = td / "progress.html"
    progress_page.write_text("<title>Wolf · Progress</title>", encoding="utf-8")
    progress = prove.inspect_progress(progress_page)
    check("progress present not this cap", progress["present"] and progress["this_cap"] is False)
    check("progress percent absent", progress["system_pct"] is None and progress["used_as_maturity"] is False)
    adoption = prove.read_adoption()
    check("au read", adoption["au_id"] == "AU-STRAT-02-OWNER" and adoption["present"] is True)
    check("au not started as read", adoption["state"] == "NOT STARTED", str(adoption.get("state")))
    missing_au = td / "no-au.json"
    missing_au.write_text("[]", encoding="utf-8")
    gone = prove.read_adoption(missing_au)
    check("au absent when missing", gone["status"] == "ABSENT" and gone["state"] is None)
    pack = prove.build_prove()
    live_html = pack["surfaces"]["html"]
    live_board = pack["surfaces"]["board"]
    check("live html bound", live_html["present"] and live_html["owner_plan_board"] and live_html["executed"] is False)
    check("live board not executed", live_board["present"] and live_board["executed"] is False)
    check("live public", live_board["has_public"] and live_board["read_only_stated"])
    check("live task not called", live_board["has_create_task"] and live_board["create_task_called_by_prove"] is False)
    check("live pulse absent", pack["surfaces"]["pulse"]["status"] == "ABSENT")
    check("live pulse counts none", pack["surfaces"]["pulse"]["pulse_count"] is None)
    check("live bird not satisfied", pack["surfaces"]["birdseye"]["satisfied"] is False)
    check("live mission alias", pack["surfaces"]["mission_control"]["status"] == "ALIAS")
    check("live progress excluded", pack["progress"]["this_cap"] is False and pack["progress"]["system_pct"] is None)
    check("live pack built", pack["honesty"]["maturity"] == "BUILT" and pack["honesty"]["proven"] is False)
    check("live cr open", pack["honesty"]["cr_state"] == "OPEN" and pack["honesty"]["cr_resolved"] is False)
    check("gaps block higher", pack["gaps"] and all(g.get("blocks_proven") is True for g in pack["gaps"]))
    ids = {g["id"] for g in pack["gaps"]}
    check(
        "gap ids",
        {
            "pulse_exceptions",
            "progressive_quiet",
            "progress_dashboard",
            "mission_control",
            "model_e_au",
            "ledger_gap_text",
            "cap_strat_01",
            "stub_entities",
        }
        <= ids,
    )
    check("schema", pack["schema"] == prove.SCHEMA)
    gap = prove.ledger_gap_text()
    check("ledger gap uncleared", gap == GAP_TEXT, str(gap))
    check("no system percent key copied", pack["progress"]["system_pct"] is None)


def test_source_and_routes() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("module names the CR", CR_ID in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not import radar_board", "import radar_board" not in src and "from radar_board" not in src)
    check("create task flag stays false", '"create_task_called": False' in src)
    check("module does not import progress model", "progress_read_model" not in src)
    check("module does not bind 8787", "8787" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/strat/radar-prove" in serve)
    check("page route registered", "/radar-prove" in serve)
    check("task hint wired", 'return {"create_task": True}' in serve)
    check("progress hint wired", 'return {"progress": True}' in serve)
    check("score hint wired", 'return {"proven": True}' in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "radar-prove.html").read_text(encoding="utf-8")
    check("page does not say proven as status", "PROVEN" not in page)
    check("page refuses promotion", "does not promote" in page)
    check("page excludes progress", "Progress dashboard is not this CAP alone" in page)


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

        st, anon = call("GET", "/api/strat/radar-prove", None)
        check("anon GET 403", st == 403, str(anon)[:180])
        st, staff = call("GET", "/api/strat/radar-prove", STAFF)
        check("staff GET 403", st == 403, str(staff)[:180])
        st, owner = call("GET", "/api/strat/radar-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            flags = owner.get("honesty") or {}
            check("owner honesty bound", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner maturity built", flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner progress excluded", flags.get("progress_used_as_cap") is False)
            check("owner pulse absent", (owner.get("surfaces") or {}).get("pulse", {}).get("status") == "ABSENT")
            progress = owner.get("progress") or {}
            check("owner progress percent none", progress.get("system_pct") is None and progress.get("this_cap") is False)
        st, page = call("GET", "/radar-prove", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/radar-prove", MATT)
        check("owner page 200", st == 200 and isinstance(page, str) and "does not promote" in page, str(st))
        st, posted = call("POST", "/api/strat/radar-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, task = call("POST", "/api/strat/radar-prove/task", MATT)
        check("owner task 405", st == 405 and isinstance(task, dict) and task.get("error") == "create_task_refused", str(task)[:160])
        st, progress_post = call("POST", "/api/strat/radar-prove/progress", MATT)
        check(
            "owner progress 405",
            st == 405 and isinstance(progress_post, dict) and progress_post.get("error") == "progress_not_this_cap",
            str(progress_post)[:160],
        )
        st, scored = call("POST", "/api/strat/radar-prove/proven", MATT)
        check("owner score 405", st == 405 and isinstance(scored, dict) and scored.get("error") == "score_refused", str(scored)[:160])
        st, _ = call("POST", "/api/strat/radar-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, put = call("PUT", "/api/strat/radar-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:120])
        st, patched = call("PATCH", "/api/strat/radar-prove", MATT)
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
        test_entities_and_pulse()
        test_honesty_and_refusals(td)
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
