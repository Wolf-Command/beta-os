#!/usr/bin/env python3
"""CAP-CORE-12 escalation burn-down. No ledger write. No invented PROVEN. No Needs Matt clear."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import escalation_burndown as burn  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "escalation_burndown.py"
CR_ID = "CR-6e3fd7b9d7edca0e"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=burn.WITA)


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


def _iso(day: datetime) -> str:
    return day.astimezone(burn.WITA).isoformat(timespec="seconds")


def _window(report: dict, days: int) -> dict:
    rows = [row for row in report["windows"] if row["days"] == days]
    return rows[0] if rows else {}


def _schema(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE wolf_completion_items (
          id TEXT PRIMARY KEY,
          state TEXT,
          blocker_class TEXT,
          first_seen TEXT,
          resolved_at TEXT,
          resolution_evidence TEXT
        );
        CREATE TABLE core_delegations (
          delegation_id TEXT PRIMARY KEY,
          status TEXT,
          effective_from TEXT,
          effective_to TEXT
        );
        """
    )
    conn.commit()
    return conn


def _item(
    item_id: str,
    *,
    state: str = "OPEN",
    blocker: str = "NEEDS_MATT",
    seen: str | None = None,
    resolved_at: str | None = None,
    evidence: str | None = None,
) -> dict:
    return {
        "id": item_id,
        "state": state,
        "blocker_class": blocker,
        "first_seen": seen,
        "resolved_at": resolved_at,
        "resolution_evidence": evidence,
    }


def test_unread_and_empty() -> None:
    blank = burn.counters_for(None, [], NOW)
    check("unread completion is not zero", blank["needs_matt_open"] is None and blank["completion_status"] == "NOT_READ")
    check("unread windows blank", all(row["opened"] is None and row["independence"] == "NOT_READ" for row in blank["windows"]))
    check("unread not proven", blank["proven"] is False and all(row["proven"] is False for row in blank["windows"]))
    both = burn.counters_for(None, None, NOW)
    check("both unread", both["delegation_status"] == "NOT_READ" and both["windows"][0]["intentional_time_bounded"] is None)
    empty = burn.counters_for([], [], NOW)
    check("empty register", empty["completion_rows"] == 0 and empty["needs_matt_open"] == 0)
    check("empty is not clear", all(row["independence"] == "EMPTY" for row in empty["windows"]))
    check("empty counts are zero not null", empty["windows"][0]["still_open"] == 0 and empty["windows"][0]["burned_down"] == 0)
    check("four windows", [row["days"] for row in empty["windows"]] == [7, 30, 90, 365])
    check("operating test stays off", empty["operating_test"] is False)


def test_windows() -> None:
    recent = _iso(NOW - timedelta(days=2))
    mid = _iso(NOW - timedelta(days=18))
    old = _iso(datetime(2026, 6, 1, 9, 0, tzinfo=burn.WITA))
    staff_only = burn.counters_for(
        [_item("staff", blocker="NEEDS_STAFF", seen=recent)],
        [],
        NOW,
    )
    check("staff is not needs matt", staff_only["needs_matt_open"] == 0)
    check("staff register can be clear", _window(staff_only, 7)["independence"] == "CLEAR")
    check("clear is not proven", _window(staff_only, 7)["proven"] is False and "promote" in _window(staff_only, 7)["why"])
    titled = burn.counters_for(
        [_item("eng", blocker="NEEDS_ENGINEERING", seen=recent)],
        [],
        NOW,
    )
    check("engineering title not reclassed", titled["needs_matt_open"] == 0 and _window(titled, 7)["independence"] == "CLEAR")

    open_recent = burn.counters_for([_item("m1", seen=recent)], [], NOW)
    w7 = _window(open_recent, 7)
    check("recent still open", w7["still_open"] == 1 and w7["older_open"] == 0 and w7["independence"] == "OPEN")
    check("recent not burned", w7["burned_down"] == 0 and w7["opened"] == 1)
    check("open why refuses clear", "not cleared" in w7["why"])

    aged = burn.counters_for([_item("m2", seen=mid)], [], NOW)
    check("18d is older than 7", _window(aged, 7)["older_open"] == 1 and _window(aged, 7)["still_open"] == 0)
    check("18d is inside 30", _window(aged, 30)["still_open"] == 1 and _window(aged, 30)["independence"] == "OPEN")
    check("18d inside 90", _window(aged, 90)["still_open"] == 1)

    year = burn.counters_for([_item("m3", seen=old)], [], NOW)
    check("june is older than 90", _window(year, 90)["older_open"] == 1 and _window(year, 90)["still_open"] == 0)
    check("june is inside 365", _window(year, 365)["still_open"] == 1 and _window(year, 365)["older_open"] == 0)
    check("backlog keeps 7 open", _window(year, 7)["independence"] == "OPEN")

    burned = burn.counters_for(
        [
            _item(
                "done",
                state="RESOLVED",
                seen=_iso(NOW - timedelta(days=3)),
                resolved_at=_iso(NOW - timedelta(days=1)),
                evidence="resolution note abc123",
            )
        ],
        [],
        NOW,
    )
    b7 = _window(burned, 7)
    check("evidenced burn counts", b7["burned_down"] == 1 and b7["still_open"] == 0 and b7["opened"] == 1)
    check("evidenced burn can clear the window", b7["independence"] == "CLEAR" and burned["needs_matt_open"] == 0)
    check("evidenced burn not an operating test", b7["operating_test"] is False)

    silent = burn.counters_for(
        [
            _item(
                "ghost",
                state="RESOLVED",
                seen=_iso(NOW - timedelta(days=1)),
                resolved_at=_iso(NOW - timedelta(hours=2)),
                evidence="   ",
            )
        ],
        [],
        NOW,
    )
    s7 = _window(silent, 7)
    check("blank evidence is not a burn", s7["burned_down"] == 0 and s7["refused_silent_clear"] == 1)
    check("silent clear blocks", s7["independence"] == "BLOCKED" and silent["refused_silent_clear"] == 1)
    check("silent clear is not open zero success", "without evidence" in s7["why"])

    undated = burn.counters_for([_item("nodate", seen=None)], [], NOW)
    check("undated not dropped", undated["undated_or_future"] == 1 and undated["needs_matt_open"] == 1)
    check("undated blocks", _window(undated, 365)["independence"] == "BLOCKED" and _window(undated, 365)["still_open"] == 0)
    future = burn.counters_for([_item("later", seen=_iso(NOW + timedelta(days=1)))], [], NOW)
    check("future timestamp blocks", future["undated_or_future"] == 1 and _window(future, 7)["independence"] == "BLOCKED")


def test_delegations() -> None:
    seen = _iso(NOW - timedelta(days=1))
    bounded = {
        "delegation_id": "DLG-1",
        "status": "ACTIVE",
        "effective_from": _iso(NOW - timedelta(days=10)),
        "effective_to": _iso(NOW + timedelta(days=20)),
    }
    pack = burn.counters_for([_item("other", blocker="NEEDS_POLICY", seen=seen)], [bounded], NOW)
    check("time-bounded counted", _window(pack, 7)["intentional_time_bounded"] == 1)
    check("time-bounded does not invent needs matt", pack["needs_matt_open"] == 0 and _window(pack, 7)["independence"] == "CLEAR")
    ended = {
        "delegation_id": "DLG-OLD",
        "status": "ACTIVE",
        "effective_from": _iso(NOW - timedelta(days=40)),
        "effective_to": _iso(NOW - timedelta(days=20)),
    }
    old_pack = burn.counters_for([_item("other", blocker="NEEDS_POLICY", seen=seen)], [ended], NOW)
    check("ended before 7 not in 7", _window(old_pack, 7)["intentional_time_bounded"] == 0)
    check("ended still inside 30", _window(old_pack, 30)["intentional_time_bounded"] == 1)
    unbounded = {
        "delegation_id": "DLG-OPEN",
        "status": "ACTIVE",
        "effective_from": _iso(NOW - timedelta(days=1)),
        "effective_to": None,
    }
    blocked = burn.counters_for([_item("other", blocker="NEEDS_POLICY", seen=seen)], [unbounded], NOW)
    check("missing end blocks", blocked["unbounded_delegations"] == 1 and _window(blocked, 7)["independence"] == "BLOCKED")
    check("unbounded not counted as intentional", _window(blocked, 7)["intentional_time_bounded"] == 0)
    empty_plus = burn.counters_for([], [unbounded], NOW)
    check("empty register plus unbounded is blocked", _window(empty_plus, 7)["independence"] == "BLOCKED")
    revoked = {
        "delegation_id": "DLG-R",
        "status": "REVOKED",
        "effective_from": None,
        "effective_to": None,
    }
    quiet = burn.counters_for([_item("other", blocker="NEEDS_POLICY", seen=seen)], [revoked], NOW)
    check("revoked without dates does not block", quiet["unbounded_delegations"] == 0 and _window(quiet, 7)["independence"] == "CLEAR")


def test_fixture_db(td: Path) -> None:
    db = td / "catalog.sqlite"
    conn = _schema(db)
    conn.execute(
        "INSERT INTO wolf_completion_items VALUES (?,?,?,?,?,?)",
        ("CR-OPEN", "OPEN", "NEEDS_MATT", _iso(NOW - timedelta(days=1)), None, None),
    )
    conn.execute(
        "INSERT INTO core_delegations VALUES (?,?,?,?)",
        ("DLG-1", "ACTIVE", _iso(NOW - timedelta(days=2)), _iso(NOW + timedelta(days=5))),
    )
    conn.commit()
    before = conn.execute("SELECT state, resolution_evidence FROM wolf_completion_items").fetchall()
    dlg_before = conn.execute("SELECT status FROM core_delegations").fetchall()
    conn.close()
    report = burn.build_report(db, now=NOW, ledger_path=td / "missing-ledger.json")
    check("fixture read", report["ok"] is True and report["needs_matt_auto_cleared"] is False)
    check("fixture open", _window(report, 7)["still_open"] == 1 and _window(report, 7)["independence"] == "OPEN")
    check("fixture intentional", _window(report, 7)["intentional_time_bounded"] == 1)
    check("fixture ledger unknown", report["honesty"]["maturity"] == "UNKNOWN" and report["honesty"]["proven"] is False)
    check("fixture cr absent", report["honesty"]["cr_present"] is False and report["honesty"]["cr_bound"] is True)
    after = sqlite3.connect(db).execute(
        "SELECT state, resolution_evidence FROM wolf_completion_items"
    ).fetchall()
    dlg_after = sqlite3.connect(db).execute("SELECT status FROM core_delegations").fetchall()
    check("fixture needs matt unchanged", before == after == [("OPEN", None)])
    check("fixture delegation unchanged", dlg_before == dlg_after == [("ACTIVE",)])
    empty = td / "empty.sqlite"
    sqlite3.connect(empty).close()
    missing_tables = burn.build_report(empty, now=NOW, ledger_path=td / "missing-ledger.json")
    check("missing tables not read", missing_tables["completion_status"] == "NOT_READ")
    check("missing tables not zero", missing_tables["needs_matt_open"] is None and _window(missing_tables, 7)["independence"] == "NOT_READ")
    gone = burn.build_report(td / "nope.sqlite", now=NOW, ledger_path=td / "missing-ledger.json")
    check("missing file not read", gone["completion_status"] == "NOT_READ" and gone["needs_matt_open"] is None)
    (td / "alchemist.sqlite").write_bytes(b"")
    try:
        burn.build_report(td / "alchemist.sqlite", now=NOW)
        check("alchemist path refused", False, "no raise")
    except burn.BurndownError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    (td / "money.sqlite").write_bytes(b"")
    try:
        burn.build_report(td / "money.sqlite", now=NOW)
        check("money path refused", False, "no raise")
    except burn.BurndownError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    try:
        burn.refuse_needs_matt_clear({"id": "CR-OPEN"})
        check("clear refused", False, "no raise")
    except burn.BurndownError as exc:
        check("clear refused", exc.code == "writes_refused" and "not auto-cleared" in str(exc), exc.code)


def test_honesty(td: Path) -> None:
    flags = burn.honesty_flags()
    check("cr bound", flags["cr_id"] == CR_ID and flags["cr_bound"] is True)
    check("cr present", flags["cr_present"] is True)
    check("cr open", flags["cr_state"] == "OPEN", str(flags.get("cr_state")))
    check("cr not resolved", flags["cr_resolved"] is False)
    check("cr cap", flags["cr_capability"] == "CAP-CORE-12")
    check("cr blocker stays engineering", flags["cr_blocker"] == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("live built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling built", flags["maturity_ceiling"] == "BUILT")
    check("not proven", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("no raise", flags["model_c_maturity_raised"] is False and flags["model_c_write"] is False)
    check("no cr mutate", flags["cr_mutated"] is False and flags["auto_clear_needs_matt"] is False)
    check("operating test off", flags["operating_test"] is False)
    proven = td / "proven.json"
    proven.write_text(json.dumps({"CAP-CORE-12": ["PROVEN", "fixture"]}), encoding="utf-8")
    high = burn.honesty_flags(proven)
    check("fixture proven reported", high["proven"] is True and high["maturity_ceiling"] == "PROVEN")
    check("fixture does not raise live", burn.ledger_cap_state() == "BUILT")
    specified = td / "specified.json"
    specified.write_text(json.dumps({"CAP-CORE-12": ["SPECIFIED"]}), encoding="utf-8")
    low = burn.honesty_flags(specified)
    check("specified stays below proven", low["maturity"] == "SPECIFIED" and low["proven"] is False and low["maturity_ceiling"] == "BUILT")
    empty_db = td / "empty-honesty.sqlite"
    sqlite3.connect(empty_db).close()
    missing = burn.honesty_flags(catalog_db=empty_db)
    check("missing table not present", missing["cr_present"] is False and missing["cr_bound"] is True)
    check("missing table not resolved", missing["cr_resolved"] is False)


def test_live_read() -> None:
    report = burn.build_report(now=NOW)
    check("live ok", report["ok"] is True and report["read_only"] is True)
    check("live cap", report["cap"] == "CAP-CORE-12" and report["honesty"]["maturity"] == "BUILT")
    check("live not proven", report["honesty"]["proven"] is False and report["operating_test"] is False)
    check("live cr open", report["honesty"]["cr_state"] == "OPEN" and report["honesty"]["cr_id"] == CR_ID)
    check("live windows", [row["days"] for row in report["windows"]] == [7, 30, 90, 365])
    check("live counts read", report["completion_status"] == "READ" and isinstance(report["needs_matt_open"], int))
    check("live independence allowed", all(row["independence"] in {"EMPTY", "BLOCKED", "OPEN", "CLEAR"} for row in report["windows"]))
    check("live window not proven", all(row["proven"] is False and row["operating_test"] is False for row in report["windows"]))
    check("live no auto clear flag", report["needs_matt_auto_cleared"] is False and report["ledger_write"] is False)


def test_source_and_routes() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    low = src.lower()
    check("module names the CR", CR_ID in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not sql-mutate", "update " not in low and "insert " not in low and "delete " not in low)
    check("module does not bind 8787", "8787" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/core/escalation-burndown" in serve)
    check("page route registered", "/escalation-burndown" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "escalation-burndown.html").read_text(encoding="utf-8")
    check("page does not say proven as status", "PROVEN" not in page)
    check("page refuses promotion", "does not promote" in page)
    check("page refuses clear", "does not clear Needs Matt" in page)


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
            data = b'{"clear": true}' if method != "GET" else None
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

        st, anon = call("GET", "/api/core/escalation-burndown", None)
        check("anon GET 403", st == 403, str(anon)[:180])
        st, staff = call("GET", "/api/core/escalation-burndown", STAFF)
        check("staff GET 403", st == 403, str(staff)[:180])
        st, owner = call("GET", "/api/core/escalation-burndown", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            flags = owner.get("honesty") or {}
            check("owner honesty bound", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner maturity built", flags.get("maturity") == "BUILT" and flags.get("proven") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner no auto clear", owner.get("needs_matt_auto_cleared") is False)
            check("owner windows", [row.get("days") for row in owner.get("windows") or []] == [7, 30, 90, 365])
            check("owner operating test off", owner.get("operating_test") is False and flags.get("operating_test") is False)
        st, page = call("GET", "/escalation-burndown", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/escalation-burndown", MATT)
        check("owner page 200", st == 200 and isinstance(page, str) and "does not clear Needs Matt" in page, str(st))
        st, posted = call("POST", "/api/core/escalation-burndown", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        if isinstance(posted, dict):
            check("post says not cleared", "not auto-cleared" in str(posted.get("message")))
        st, cleared = call("POST", "/api/core/escalation-burndown/clear", MATT)
        check("clear path 405", st == 405 and isinstance(cleared, dict) and cleared.get("needs_matt_auto_cleared") is False, str(cleared)[:180])
        st, _ = call("POST", "/api/core/escalation-burndown", None)
        check("anon POST 403", st == 403, str(st))
        st, put = call("PUT", "/api/core/escalation-burndown", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:120])
        st, patched = call("PATCH", "/api/core/escalation-burndown", MATT)
        check("owner PATCH 405", st == 405 and isinstance(patched, dict) and patched.get("error") == "writes_refused", str(patched)[:120])
    finally:
        httpd.shutdown()


def main() -> int:
    ledger_before = _sha(LEDGER)
    history_before = _sha(HISTORY)
    credits_before = _sha(CREDITS)
    wip_before = {rel: _sha(ROOT / rel) for rel in WIP}
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    cr_before = conn.execute(
        "SELECT state, blocker_class FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    needs_before = conn.execute(
        "SELECT COUNT(*) FROM wolf_completion_items WHERE state!='RESOLVED' AND blocker_class='NEEDS_MATT'"
    ).fetchone()[0]
    conn.close()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        test_unread_and_empty()
        test_windows()
        test_delegations()
        test_fixture_db(td)
        test_honesty(td)
    test_live_read()
    test_source_and_routes()
    test_api()
    check("ledger bytes unchanged", _sha(LEDGER) == ledger_before)
    check("score history unchanged", _sha(HISTORY) == history_before)
    check("credits doc unchanged", _sha(CREDITS) == credits_before)
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    cr_after = conn.execute(
        "SELECT state, blocker_class FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    needs_after = conn.execute(
        "SELECT COUNT(*) FROM wolf_completion_items WHERE state!='RESOLVED' AND blocker_class='NEEDS_MATT'"
    ).fetchone()[0]
    conn.close()
    check("cr row unchanged", cr_before == cr_after == ("OPEN", "NEEDS_ENGINEERING"), str(cr_after))
    check("needs matt count unchanged", needs_before == needs_after, f"{needs_before} -> {needs_after}")
    for rel, digest in wip_before.items():
        check(f"WIP untouched {Path(rel).name}", _sha(ROOT / rel) == digest)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
