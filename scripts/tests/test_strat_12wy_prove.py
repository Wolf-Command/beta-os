#!/usr/bin/env python3
"""CAP-STRAT-01 12WY prove pack. No ledger write. No invented PROVEN."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import strat_12wy_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "strat_12wy_prove.py"
CR_ID = "CR-6535f7cb02370850"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
WEEK2 = datetime(2026, 9, 19, 10, 0, tzinfo=prove.WITA)
RADAR_OK = (
    'SCORE_LOCK_PCT = 85\n'
    'def weekly_scorecard():\n    return None\n'
    'def score_tactics():\n    return None\n'
    '"auto_now": False\n'
    'EMPTY, not 0%\n'
)
HELM_EMPTY = (
    '<span class="score">EMPTY</span> week=<b>2</b> planned=<b>0</b> done=<b>0</b>'
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


def test_clock_and_contract() -> None:
    clock = prove.period_clock(WEEK2)
    check("week 2 on 19 Sep", clock["week"] == 2 and clock["phase"] == "p1", str(clock))
    before = prove.period_clock(datetime(2026, 9, 1, 8, 0, tzinfo=prove.WITA))
    check("before period", before["phase"] == "before" and before["week"] is None)
    buffer = prove.period_clock(datetime(2026, 11, 30, 8, 0, tzinfo=prove.WITA))
    check("buffer week 13", buffer["week"] == 13 and buffer["phase"] == "buffer", str(buffer))
    after = prove.period_clock(datetime(2026, 12, 7, 8, 0, tzinfo=prove.WITA))
    check("after period", after["phase"] == "after" and after["week"] is None)
    empty = prove.score_contract(0, 0)
    check("planned 0 is EMPTY", empty["state"] == "EMPTY" and empty["percent"] is None)
    check("planned 0 not on track", empty["on_track"] is False and empty["threshold_met"] is None)
    check("planned 0 auto now off", empty["auto_now"] is False and empty["rag"] is None)
    zero = prove.score_contract(5, 0)
    check("evidenced zero stays wired", zero["state"] == "WIRED" and zero["percent"] == 0, str(zero))
    under = prove.score_contract(5, 4)
    check("80 not on track", under["percent"] == 80 and under["on_track"] is False and under["state"] == "WIRED")
    lock = prove.score_contract(20, 17)
    check("85 is the lock", lock["percent"] == 85 and lock["on_track"] is True and lock["threshold"] == 85)
    over = prove.score_contract(4, 9)
    check("done clamped", over["done"] == 4 and over["percent"] == 100 and over["auto_now"] is False)
    check("bool is not a count", prove.score_contract(True, False)["state"] == "EMPTY")
    check("negative is empty", prove.score_contract(-3, 1)["state"] == "EMPTY")
    check("lock text refuses proven", "Not PROVEN." in lock["why"] and lock["state"] != "PROVEN")


def test_tactic_filter() -> None:
    tasks = [
        {"id": "a", "tactic": True, "week": 2, "status": "done"},
        {"id": "b", "tactic": True, "week": 1, "status": "done"},
        {"id": "c", "status": "done", "week": 2},
        {"id": "d", "kind": "12wy", "week": 2, "status": "open"},
        {"id": "e", "twelve_week": True, "period_week": 2, "status": "DONE"},
        {"id": "f", "kind": "tactic", "week": 2, "status": "complete"},
    ]
    scored = prove.score_week(tasks, 2)
    check("four week-2 tactics", scored["planned"] == 4, str(scored["tactic_ids"]))
    check("two evidenced done", scored["done"] == 2, str(scored))
    check("ids keep a and d and e and f", set(scored["tactic_ids"]) == {"a", "d", "e", "f"})
    check("wrong week excluded", "b" not in scored["tactic_ids"])
    check("unflagged excluded", "c" not in scored["tactic_ids"])
    check("filter has no rag", scored["rag"] is None and scored["auto_now"] is False)


def test_bindings(td: Path) -> None:
    tasks = td / "tasks.json"
    tasks.write_text(
        json.dumps(
            {
                "tasks": [
                    {"id": "w2", "tactic": True, "week": 2, "status": "done"},
                    {"id": "other", "tactic": True, "week": 9, "status": "done"},
                ]
            }
        ),
        encoding="utf-8",
    )
    radar = td / "radar_ok.py"
    radar.write_text(RADAR_OK, encoding="utf-8")
    helm = td / "helm.html"
    helm.write_text(HELM_EMPTY, encoding="utf-8")
    missing = td / "no-helm.html"
    pack = prove.build_prove(
        now=WEEK2,
        tasks_path=tasks,
        radar_path=radar,
        helm_path=helm,
        helm_prod_path=missing,
        read_tasks=True,
    )
    check("fixture wired 100", pack["score"]["state"] == "WIRED" and pack["score"]["percent"] == 100, str(pack["score"]))
    check("fixture week 2", pack["score"]["week"] == 2 and pack["score"]["planned"] == 1)
    check("other week not counted", pack["score"]["tactic_ids"] == ["w2"])
    check("radar not executed", pack["radar"]["executed"] is False and pack["radar"]["lock_matches_contract"] is True)
    check("helm stated empty", pack["helm"]["stated_state"] == "EMPTY" and pack["helm"]["stated_planned"] == 0)
    check("helm not today's score", pack["helm"]["dated_pack"] is True and pack["helm"]["invented"] is False)
    check("wolf public not called", pack["tasks"]["wolf_public_called"] is False)
    check("writes false", pack["ledger_write"] is False and pack["alchemist_write"] is False and pack["production_write"] is False)
    unread = prove.build_prove(
        now=WEEK2,
        tasks_path=tasks,
        radar_path=radar,
        helm_path=missing,
        helm_prod_path=missing,
        read_tasks=False,
    )
    check("skipped read is NOT_READ", unread["score"]["state"] == "NOT_READ" and unread["score"]["percent"] is None)
    bad = td / "radar_bad.py"
    bad.write_text("SCORE_LOCK_PCT = 50\ndef weekly_scorecard():\n pass\ndef score_tactics():\n pass\n", encoding="utf-8")
    mismatch = prove.build_prove(
        now=WEEK2,
        tasks_path=tasks,
        radar_path=bad,
        helm_path=missing,
        helm_prod_path=missing,
    )
    check("lock mismatch emits no percent", mismatch["score"]["state"] == "LOCK_MISMATCH" and mismatch["score"]["percent"] is None)
    junk = td / "tasks-junk.json"
    junk.write_text("{", encoding="utf-8")
    invalid = prove.build_prove(
        now=WEEK2,
        tasks_path=junk,
        radar_path=radar,
        helm_path=missing,
        helm_prod_path=missing,
    )
    check("invalid tasks not EMPTY", invalid["score"]["state"] == "NOT_READ" and invalid["score"]["planned"] is None)
    gone = prove.build_prove(
        now=WEEK2,
        tasks_path=td / "missing-tasks.json",
        radar_path=td / "missing-radar.py",
        helm_path=missing,
        helm_prod_path=missing,
    )
    check("missing tasks not a zero", gone["score"]["state"] == "NOT_READ" and gone["radar"]["present"] is False)
    preview = prove.build_prove(
        now=datetime(2026, 9, 1, 8, 0, tzinfo=prove.WITA),
        tasks_path=tasks,
        radar_path=radar,
        helm_path=missing,
        helm_prod_path=missing,
    )
    check("preview week 1", preview["score"]["preview"] is True and preview["score"]["week"] == 1)
    check("preview does not steal week 2", preview["score"]["state"] == "EMPTY")


def test_honesty(td: Path) -> None:
    flags = prove.honesty_flags()
    check("cr bound", flags["cr_id"] == CR_ID and flags["cr_bound"] is True)
    check("cr present", flags["cr_present"] is True)
    check("cr open", flags["cr_state"] == "OPEN", str(flags.get("cr_state")))
    check("cr not resolved", flags["cr_resolved"] is False)
    check("cr cap", flags["cr_capability"] == "CAP-STRAT-01")
    check("live built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling built", flags["maturity_ceiling"] == "BUILT")
    check("not proven", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("no raise", flags["model_c_maturity_raised"] is False and flags["model_c_write"] is False)
    check("no cr mutate", flags["cr_mutated"] is False)
    check("strat02 not this prove", flags["cap_strat_02_not_this_prove"] is True)
    proven = td / "proven.json"
    proven.write_text(json.dumps({"CAP-STRAT-01": ["PROVEN", "fixture"]}), encoding="utf-8")
    high = prove.honesty_flags(proven)
    check("fixture proven reported", high["proven"] is True and high["maturity_ceiling"] == "PROVEN")
    check("fixture does not raise live", prove.ledger_cap_state() == "BUILT")
    specified = td / "specified.json"
    specified.write_text(json.dumps({"CAP-STRAT-01": ["SPECIFIED"]}), encoding="utf-8")
    low = prove.honesty_flags(specified)
    check("specified stays below proven", low["maturity"] == "SPECIFIED" and low["proven"] is False and low["maturity_ceiling"] == "BUILT")
    empty_db = td / "empty.sqlite"
    sqlite3.connect(empty_db).close()
    missing = prove.honesty_flags(catalog_db=empty_db)
    check("missing table not present", missing["cr_present"] is False and missing["cr_bound"] is True)
    check("missing table not resolved", missing["cr_resolved"] is False)
    try:
        prove.inspect_radar(td / "alchemist" / "radar.py")
        check("alchemist path refused", False, "no raise")
    except prove.ProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        prove.refuse_external_write({})
        check("write refused", False, "no raise")
    except prove.ProveError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)


def test_live_bindings() -> None:
    radar = prove.inspect_radar()
    check("live radar present", radar["present"] is True and radar["executed"] is False)
    check("live radar functions", radar["has_weekly_scorecard"] and radar["has_score_tactics"])
    check("live lock 85", radar["score_lock_pct"] == 85 and radar["lock_matches_contract"] is True, str(radar["score_lock_pct"]))
    check("live empty contract", radar["empty_not_zero_stated"] is True and radar["auto_now_false_stated"] is True)
    check("prove does not call create_task", radar["create_task_called_by_prove"] is False)
    helm = prove.inspect_helm(prove.HELM_BETA)
    check("beta helm present", helm["present"] is True)
    check("beta helm empty", helm["stated_state"] == "EMPTY" and helm["stated_week"] == 2, str(helm))
    check("beta helm planned 0", helm["stated_planned"] == 0 and helm["stated_done"] == 0)
    pack = prove.build_prove(now=WEEK2, helm_path=prove.HELM_BETA)
    score = pack["score"]
    if score["state"] == "EMPTY":
        check("live empty has no percent", score["percent"] is None and score["planned"] == 0)
    elif score["state"] == "WIRED":
        expect = int(round(100.0 * score["done"] / score["planned"])) if score["planned"] else None
        check("live wired matches lock", score["percent"] == expect and score["percent"] != "PROVEN")
    else:
        check("live score is a known state", score["state"] in {"NOT_READ", "LOCK_MISMATCH"}, score["state"])
    check("live pack not proven", pack["honesty"]["proven"] is False and pack["honesty"]["maturity"] == "BUILT")
    check("live pack no wolf.public", pack["honesty"]["wolf_public_called"] is False)


def test_source_and_routes() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("module names the CR", CR_ID in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not call wolf.public", "wolf.public" not in src)
    check("module does not call create_task", "create_task(" not in src)
    check("module does not bind 8787", "8787" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/strat/12wy-prove" in serve)
    check("page route registered", "/12wy-prove" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "12wy-prove.html").read_text(encoding="utf-8")
    check("page does not say proven as status", "PROVEN" not in page)
    check("page refuses promotion", "does not promote" in page)


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

        st, anon = call("GET", "/api/strat/12wy-prove", None)
        check("anon GET 403", st == 403, str(anon)[:180])
        st, staff = call("GET", "/api/strat/12wy-prove", STAFF)
        check("staff GET 403", st == 403, str(staff)[:180])
        st, owner = call("GET", "/api/strat/12wy-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            flags = owner.get("honesty") or {}
            score = owner.get("score") or {}
            check("owner honesty bound", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner maturity built", flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner no green rag", score.get("rag") is None and "GREEN" not in json.dumps(owner))
            check("owner auto now off", score.get("auto_now") is False and flags.get("wolf_public_called") is False)
            check("owner state allowed", score.get("state") in {"EMPTY", "WIRED", "NOT_READ", "LOCK_MISMATCH"}, str(score.get("state")))
            if score.get("state") == "EMPTY":
                check("owner empty percent", score.get("percent") is None)
            else:
                check("owner empty percent", True)
        st, page = call("GET", "/12wy-prove", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/12wy-prove", MATT)
        check("owner page 200", st == 200 and isinstance(page, str) and "does not promote" in page, str(st))
        st, posted = call("POST", "/api/strat/12wy-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, _ = call("POST", "/api/strat/12wy-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, put = call("PUT", "/api/strat/12wy-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:120])
        st, patched = call("PATCH", "/api/strat/12wy-prove", MATT)
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
        test_clock_and_contract()
        test_tactic_filter()
        test_bindings(td)
        test_honesty(td)
    test_live_bindings()
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
