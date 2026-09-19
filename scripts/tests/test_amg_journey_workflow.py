#!/usr/bin/env python3
"""CAP-AMG-02 guest journey framework. Empty is not a live journey or guest operations."""
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
os.environ.pop("WOLF_ALLOW_LIVE_AMG_JOURNEY", None)

from core import amg_journey_workflow as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "amg_journey_workflow.py"
STRATEGY_MODULE = SCRIPTS / "core" / "ggv_strategy_machine.py"
CR_ID = "CR-ce127471ba41692b"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["enquiry", "booking", "pre-arrival", "arrival", "stay", "checkout", "return"]
NEXT_ACTION = "Journey workflow implementation"


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
            conn.execute(
                "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
            ).fetchone()[0]
        )
    finally:
        conn.close()


def _media_count() -> int:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
    finally:
        conn.close()


def _slot_empty(row: dict) -> bool:
    return (
        row["slot"] == "empty"
        and row["evidence"] is None
        and row["booking_count"] is None
        and row["occupancy"] is None
        and row["yanolja_live"] is False
        and row["current"] is False
        and row["live_journey"] is False
        and row["guest_operations"] is False
        and row["yanolja_write"] is False
        and row["payment"] is None
        and row["payment_executed"] is False
    )


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not a journey",
        report["empty_is_journey"] is False
        and report["proved"] is False
        and report["empty_is_ready"] is False
        and report["live_journey"] is False
        and report["guest_operations"] is False
        and report["empty_is_operations"] is False,
    )
    check(
        "numbers unread",
        report["booking_count"] is None and report["occupancy"] is None and report["yanolja_live"] is False,
    )
    check("not current", report["current"] is False)
    check("yanolja unread", report["yanolja_write"] is False and report["yanolja_called"] is False)
    check(
        "payment not executed",
        report["payment"] is None and report["money"] is None and report["payment_executed"] is False,
    )
    check("bank and books unread", report["bank_write"] is False and report["books_write"] is False and report["zayen_write"] is False)
    check("alchemist unread", report["alchemist_write"] is False)
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("score unchanged", report["score_changed"] is False)
    check("not on disk", report["on_disk"] is False)
    check("bound", report["bound"] == "beta-amg-ops-safe")
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["bank_property"] is False
        and report["schema"]["books_property"] is False
        and report["schema"]["yanolja_property"] is False
        and report["schema"]["booking_count_property"] is False
        and report["schema"]["occupancy_property"] is False
        and report["schema"]["current_property"] is False
        and report["schema"]["cloudflare_property"] is False
        and report["schema"]["access_property"] is False
        and report["schema"]["proven_property"] is False
        and report["schema"]["ready_property"] is False
        and report["schema"]["kind_enum"] == KINDS,
    )
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check("ledger not written", report["ledger_write"] is False and report["cr_resolved"] is False)
    kinds = report["kinds"]
    check("seven kinds", [row["kind"] for row in kinds] == KINDS)
    check("every slot empty", all(_slot_empty(row) for row in kinds))
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-AMG-02" and flags["cr_id"] == CR_ID and flags["bound"] == "beta-amg-ops-safe")
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED" and flags["specified"] is True)
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not invented",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["built"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["guest_operations"] is False
        and flags["booking_count"] is None,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-AMG-02" and flags["cr_capability"] == "CAP-AMG-02")
        check("cr next action", row[3] == NEXT_ACTION and flags["cr_next_action"] == row[3])
    check("gaps name the empty framework", "An empty framework is not a live journey workflow." in report["gaps"])
    check("gaps name not operations", "An empty framework is not proof of guest operations." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("gaps stay specified", "CAP-AMG-02 stays SPECIFIED." in report["gaps"])
    check("gaps ceiling built", "The ceiling label is BUILT." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    one = base.read_kind("enquiry")
    check(
        "enquiry slot read",
        one["ok"] is True
        and one["kind"]["kind"] == "enquiry"
        and one["empty"] is True
        and one["proved"] is False
        and one["live_journey"] is False
        and one["guest_operations"] is False
        and one["booking_count"] is None,
    )
    back = base.read_kind("return")
    check(
        "return slot read",
        back["ok"] is True and back["kind"]["kind"] == "return" and back["occupancy"] is None,
    )
    pre = base.read_kind("pre-arrival")
    check(
        "pre-arrival slot read",
        pre["ok"] is True and pre["kind"]["kind"] == "pre-arrival" and pre["yanolja_live"] is False,
    )
    for bad, label in (("yanolja", "yanolja"), ("ready", "ready"), ("occupancy", "occupancy")):
        try:
            base.read_kind(bad)
            check(f"{label} is not a slot", False)
        except base.JourneyWorkflowError as exc:
            check(f"{label} is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.JourneyWorkflowError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.JourneyWorkflowError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.JourneyWorkflowError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    wolf = td / "wolf-system-copy.sqlite"
    wolf.write_bytes(b"sentinel-wolf")
    wolf_before = wolf.read_bytes()
    try:
        base.refuse_store(wolf)
        check("wolf-system path refused", False)
    except base.JourneyWorkflowError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    check("wolf-system sentinel unchanged", wolf.read_bytes() == wolf_before)
    bank = td / "bank.sqlite"
    bank.write_bytes(b"sentinel-bank")
    bank_before = bank.read_bytes()
    try:
        base.refuse_store(bank)
        check("bank path refused", False)
    except base.JourneyWorkflowError as exc:
        check("bank path refused", exc.code == "bank_refused", exc.code)
    check("bank sentinel unchanged", bank.read_bytes() == bank_before)
    pay = td / "payment.sqlite"
    pay.write_bytes(b"sentinel-pay")
    pay_before = pay.read_bytes()
    try:
        base.refuse_store(pay)
        check("payment path refused", False)
    except base.JourneyWorkflowError as exc:
        check("payment path refused", exc.code == "payment_refused", exc.code)
    check("payment sentinel unchanged", pay.read_bytes() == pay_before)
    books = td / "zayen-books.sqlite"
    books.write_bytes(b"sentinel-books")
    books_before = books.read_bytes()
    try:
        base.refuse_store(books)
        check("books path refused", False)
    except base.JourneyWorkflowError as exc:
        check("books path refused", exc.code == "books_refused", exc.code)
    check("books sentinel unchanged", books.read_bytes() == books_before)
    yanolja = td / "yanolja.sqlite"
    yanolja.write_bytes(b"sentinel-yanolja")
    yanolja_before = yanolja.read_bytes()
    try:
        base.refuse_store(yanolja)
        check("yanolja path refused", False)
    except base.JourneyWorkflowError as exc:
        check("yanolja path refused", exc.code == "yanolja_refused", exc.code)
    check("yanolja sentinel unchanged", yanolja.read_bytes() == yanolja_before)
    try:
        base.refuse_store(td / "model-c-baseline-assessments.json")
        check("ledger path refused", False)
    except base.JourneyWorkflowError as exc:
        check("ledger path refused", exc.code == "ledger_write_refused", exc.code)
    check("ledger fixture absent", not (td / "model-c-baseline-assessments.json").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.JourneyWorkflowError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.JourneyWorkflowError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    refusals = (
        (base.refuse_fill, {"kind": "enquiry", "status": "NOTED"}, "slots_refused", "fill refused"),
        (base.refuse_payment, {"payment": "1500000"}, "payment_refused", "payment refused"),
        (base.refuse_bank, {}, "bank_refused", "bank refused"),
        (base.refuse_books, {}, "books_refused", "books refused"),
        (base.call_yanolja, None, "yanolja_refused", "yanolja helper"),
        (base.move_money, None, "payment_refused", "money helper"),
        (base.mark_current, None, "current_refused", "current helper"),
        (base.refuse_cloudflare, {}, "cloudflare_refused", "cloudflare refused"),
        (base.refuse_access, {}, "access_refused", "access refused"),
        (base.mark_proven, None, "proven_refused", "prove helper"),
        (base.mark_ready, None, "ready_refused", "ready helper"),
        (base.resolve_cr, None, "resolve_refused", "resolve helper"),
        (base.refuse_score, {}, "score_refused", "score refused"),
        (base.refuse_alchemist, {}, "alchemist_refused", "alchemist helper"),
    )
    for fn, arg, code, label in refusals:
        try:
            fn() if arg is None else fn(arg)
            check(label, False)
        except base.JourneyWorkflowError as exc:
            check(label, exc.code == code, exc.code)
    bodies = (
        ({"payment": 1}, "payment_refused", "body payment refused"),
        ({"bank": "write"}, "bank_refused", "body bank refused"),
        ({"zayen": "write"}, "books_refused", "body books refused"),
        ({"yanolja": "call"}, "yanolja_refused", "body yanolja refused"),
        ({"booking-count": 9}, "current_refused", "body booking count refused"),
        ({"occupancy": 1}, "current_refused", "body occupancy refused"),
        ({"current": "yes"}, "current_refused", "body current refused"),
        ({"cloudflare": "flip"}, "cloudflare_refused", "body cloudflare refused"),
        ({"access": "mutate"}, "access_refused", "body access refused"),
        ({"enquiry": "filled"}, "slots_refused", "body enquiry refused"),
        ({"return": "filled"}, "slots_refused", "body return slot refused"),
        ({"score": 99}, "score_refused", "body score refused"),
        ({"alchemist": "write"}, "alchemist_refused", "body alchemist refused"),
        ({"proven": 1}, "proven_refused", "body proven refused"),
        ({"ready": 1}, "ready_refused", "body ready refused"),
        ({"resolve": 1}, "resolve_refused", "body resolve refused"),
    )
    for body, code, label in bodies:
        try:
            base.refuse_external_write(body)
            check(label, False)
        except base.JourneyWorkflowError as exc:
            check(label, exc.code == code, exc.code)
    queries = (
        ({"payment": "1"}, "payment_refused", "query payment refused"),
        ({"bank": "1"}, "bank_refused", "query bank refused"),
        ({"books": "1"}, "books_refused", "query books refused"),
        ({"yanolja": "1"}, "yanolja_refused", "query yanolja refused"),
        ({"occupancy": "1"}, "current_refused", "query occupancy refused"),
        ({"booking_count": "1"}, "current_refused", "query booking count refused"),
        ({"cloudflare": "1"}, "cloudflare_refused", "query cloudflare refused"),
        ({"access": "1"}, "access_refused", "query access refused"),
        ({"score": "1"}, "score_refused", "query score refused"),
        ({"alchemist": "1"}, "alchemist_refused", "query alchemist refused"),
        ({"prove": "1"}, "proven_refused", "query prove refused"),
        ({"ready": "1"}, "ready_refused", "query ready refused"),
        ({"resolve": "1"}, "resolve_refused", "query resolve refused"),
    )
    for kwargs, code, label in queries:
        try:
            base.guard_query(**kwargs)
            check(label, False)
        except base.JourneyWorkflowError as exc:
            check(label, exc.code == code, exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-AMG-02": [state, "note"]}), encoding="utf-8")
        return path

    absent = write("ABSENT")
    absent_before = absent.read_bytes()
    flags = base.honesty_flags(absent, CATALOG_DB)
    check("absent stays absent", flags["maturity"] == "ABSENT" and flags["maturity_ceiling"] == "BUILT")
    check("absent file untouched", absent.read_bytes() == absent_before)
    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = base.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT" and flags["specified"] is True)
    check("specified file untouched", specified.read_bytes() == before)
    built = write("BUILT")
    built_before = built.read_bytes()
    flags = base.honesty_flags(built, CATALOG_DB)
    check("built fixture ceiling stays built", flags["maturity"] == "BUILT" and flags["maturity_ceiling"] == "BUILT" and flags["built"] is True)
    check("built file untouched", built.read_bytes() == built_before)
    proven = write("PROVEN")
    proven_before = proven.read_bytes()
    flags = base.honesty_flags(proven, CATALOG_DB)
    check(
        "already proven not raised",
        flags["maturity"] == "PROVEN"
        and flags["maturity_ceiling"] == "BUILT"
        and flags["proven"] is True
        and flags["invented_proven"] is False,
    )
    check("proven file untouched", proven.read_bytes() == proven_before)
    ready = write("READY")
    ready_before = ready.read_bytes()
    flags = base.honesty_flags(ready, CATALOG_DB)
    check(
        "already ready not raised",
        flags["maturity"] == "READY"
        and flags["maturity_ceiling"] == "BUILT"
        and flags["ready"] is True
        and flags["invented_ready"] is False,
    )
    check("ready file untouched", ready.read_bytes() == ready_before)
    green = write("GREEN")
    flags = base.honesty_flags(green, CATALOG_DB)
    check("green is unknown", flags["maturity"] == "UNKNOWN" and flags["maturity_ceiling"] == "BUILT")
    missing = base.honesty_flags(td / "missing-ledger.json", CATALOG_DB)
    check("missing ledger unknown", missing["maturity"] == "UNKNOWN" and missing["maturity_ceiling"] == "BUILT")
    live = base.honesty_flags()
    check(
        "live ledger specified ceiling built",
        live["maturity"] == "SPECIFIED"
        and live["maturity_ceiling"] == "BUILT"
        and live["specified"] is True
        and live["proven"] is False
        and live["ready"] is False
        and live["built"] is False
        and live["invented_proven"] is False
        and live["invented_ready"] is False
        and live["guest_operations"] is False,
    )


def test_source() -> None:
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
    check("module does not import cloudflare", "cloudflare" not in joined)
    check("module does not import yanolja", "yanolja" not in joined)
    check("module does not import strategy machine", "ggv_strategy_machine" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not call cloudflare", "api.cloudflare.com" not in src)
    check("module does not call yanolja", "yanolja.com" not in src and "api.yanolja" not in src)
    check("module does not json.dump(", "json.dump(" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not update completion", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("module does not insert evidence", "INSERT INTO" not in src and "CREATE TABLE" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/amg/journey-workflow" in serve)
    check("page route registered", "/amg-journey-workflow" in serve)
    check("payment route refused", "/api/amg/journey-workflow/payment" in serve)
    check("bank route refused", "/api/amg/journey-workflow/bank" in serve)
    check("books route refused", "/api/amg/journey-workflow/zayen" in serve)
    check("yanolja route refused", "/api/amg/journey-workflow/yanolja" in serve)
    check("booking count route refused", "/api/amg/journey-workflow/booking-count" in serve)
    check("occupancy route refused", "/api/amg/journey-workflow/occupancy" in serve)
    check("cloudflare route refused", "/api/amg/journey-workflow/cloudflare" in serve)
    check("access route refused", "/api/amg/journey-workflow/access" in serve)
    check("prove route refused", "/api/amg/journey-workflow/prove" in serve)
    check("ready route refused", "/api/amg/journey-workflow/ready" in serve)
    check("resolve route refused", "/api/amg/journey-workflow/resolve" in serve)
    check("score route refused", "/api/amg/journey-workflow/score" in serve)
    check("alchemist route refused", "/api/amg/journey-workflow/alchemist" in serve)
    check("fill route refused", "/api/amg/journey-workflow/fill" in serve)
    check("strategy route still present", "/api/ggv/strategy-machine" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "amg-journey-workflow.html").read_text(encoding="utf-8")
    check("page says not a journey", "not a live journey workflow" in page and "not READY" in page)
    check("page says not operations", "not proof of guest operations" in page)
    check("page stays specified", "CAP-AMG-02 stays SPECIFIED" in page)
    check("page ceiling built", "ceiling label is BUILT" in page)
    check("page does not resolve", "does not resolve" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page no yanolja", "does not call Yanolja" in page)
    check("page no invented numbers", "does not invent booking counts" in page and "does not invent occupancy" in page)
    check("page no money", "does not move money" in page)
    check("page bound", "beta-amg-ops-safe" in page)
    check("page not proven", "Not PROVEN" in page)


def test_api(td: Path) -> None:
    del td
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
        def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = None
            if method != "GET":
                data = json.dumps({} if body is None else body).encode()
                headers["Content-Type"] = "application/json"
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

        st, _anon = call("GET", "/api/amg/journey-workflow", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/amg/journey-workflow", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/amg/journey-workflow", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check(
                "owner not journey",
                owner.get("empty_is_journey") is False
                and owner.get("proved") is False
                and owner.get("empty_is_ready") is False
                and owner.get("live_journey") is False
                and owner.get("guest_operations") is False
                and owner.get("empty_is_operations") is False,
            )
            check(
                "owner numbers null",
                owner.get("booking_count") is None
                and owner.get("occupancy") is None
                and owner.get("yanolja_live") is False
                and owner.get("current") is False,
            )
            check("owner yanolja quiet", owner.get("yanolja_write") is False and owner.get("yanolja_called") is False)
            check(
                "owner payment null",
                owner.get("payment") is None
                and owner.get("money") is None
                and owner.get("payment_executed") is False,
            )
            check("owner books quiet", owner.get("bank_write") is False and owner.get("zayen_write") is False)
            check("owner edge quiet", owner.get("cloudflare_mutated") is False and owner.get("access_mutated") is False)
            check("owner no resolve", owner.get("cr_resolved") is False and owner.get("on_disk") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner bound", owner.get("bound") == "beta-amg-ops-safe")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check(
                "owner ceiling",
                flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT",
            )
            check(
                "owner did not invent",
                flags.get("invented_proven") is False
                and flags.get("invented_ready") is False
                and flags.get("proven") is False
                and flags.get("ready") is False
                and flags.get("specified") is True,
            )
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("booking_count") is None
                    and row.get("occupancy") is None
                    and row.get("guest_operations") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/amg/journey-workflow/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/amg/journey-workflow/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/amg/journey-workflow/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200
            and isinstance(kinds, dict)
            and kinds.get("empty_is_journey") is False
            and kinds.get("empty_is_operations") is False,
            str(st),
        )
        st, slot = call("GET", "/api/amg/journey-workflow/booking", MATT)
        check(
            "booking slot 200",
            st == 200
            and isinstance(slot, dict)
            and (slot.get("kind") or {}).get("kind") == "booking"
            and slot.get("proved") is False
            and slot.get("booking_count") is None,
            str(slot)[:180],
        )
        st, pre = call("GET", "/api/amg/journey-workflow/pre-arrival", MATT)
        check(
            "pre-arrival slot 200",
            st == 200
            and isinstance(pre, dict)
            and (pre.get("kind") or {}).get("kind") == "pre-arrival"
            and pre.get("yanolja_live") is False
            and pre.get("guest_operations") is False,
            str(pre)[:180],
        )
        st, stay = call("GET", "/api/amg/journey-workflow/stay", MATT)
        check(
            "stay slot 200",
            st == 200
            and isinstance(stay, dict)
            and (stay.get("kind") or {}).get("kind") == "stay"
            and stay.get("occupancy") is None,
            str(stay)[:180],
        )
        st, checkout = call("GET", "/api/amg/journey-workflow/checkout", MATT)
        check(
            "checkout slot 200",
            st == 200 and isinstance(checkout, dict) and (checkout.get("kind") or {}).get("kind") == "checkout",
            str(checkout)[:180],
        )
        st, arrival = call("GET", "/api/amg/journey-workflow/arrival", MATT)
        check(
            "arrival slot 200",
            st == 200 and isinstance(arrival, dict) and (arrival.get("kind") or {}).get("kind") == "arrival",
            str(arrival)[:180],
        )
        st, missing = call("GET", "/api/amg/journey-workflow/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/amg-journey-workflow", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not a live journey workflow" in page
            and b"not proof of guest operations" in page
            and b"stays SPECIFIED" in page
            and b"does not resolve" in page
            and b"does not call Yanolja" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/amg-journey-workflow", None)
        check("anon page 403", st == 403, str(st))
        posts = (
            ("/api/amg/journey-workflow/payment", {"payment": 100}, "payment_refused", "payment POST 405"),
            ("/api/amg/journey-workflow/bank", {}, "bank_refused", "bank POST 405"),
            ("/api/amg/journey-workflow/zayen", {}, "books_refused", "zayen POST 405"),
            ("/api/amg/journey-workflow/books", {}, "books_refused", "books POST 405"),
            ("/api/amg/journey-workflow/yanolja", {}, "yanolja_refused", "yanolja POST 405"),
            ("/api/amg/journey-workflow/booking-count", {}, "current_refused", "booking-count POST 405"),
            ("/api/amg/journey-workflow/occupancy", {}, "current_refused", "occupancy POST 405"),
            ("/api/amg/journey-workflow/current", {}, "current_refused", "current POST 405"),
            ("/api/amg/journey-workflow/cloudflare", {}, "cloudflare_refused", "cloudflare POST 405"),
            ("/api/amg/journey-workflow/access", {}, "access_refused", "access POST 405"),
            ("/api/amg/journey-workflow/prove", {}, "proven_refused", "prove POST 405"),
            ("/api/amg/journey-workflow/ready", {}, "ready_refused", "ready POST 405"),
            ("/api/amg/journey-workflow/resolve", {}, "resolve_refused", "resolve POST 405"),
            ("/api/amg/journey-workflow/production", {}, "production_refused", "production POST 405"),
            ("/api/amg/journey-workflow/score", {}, "score_refused", "score POST 405"),
            ("/api/amg/journey-workflow/alchemist", {}, "alchemist_refused", "alchemist POST 405"),
            ("/api/amg/journey-workflow/fill", {}, "slots_refused", "fill POST 405"),
            ("/api/amg/journey-workflow/note", {"kind": "enquiry", "status": "NOTED"}, "slots_refused", "note POST 405"),
        )
        for path, body, code, label in posts:
            st, payload = call("POST", path, MATT, body)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, bare = call("POST", "/api/amg/journey-workflow", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/amg/journey-workflow", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/amg/journey-workflow", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/amg/journey-workflow/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        queries = (
            ("?payment=1", "payment_refused", "query payment http refused"),
            ("?yanolja=1", "yanolja_refused", "query yanolja http refused"),
            ("?occupancy=1", "current_refused", "query occupancy http refused"),
            ("?booking-count=1", "current_refused", "query booking count http refused"),
            ("?cloudflare=1", "cloudflare_refused", "query cloudflare http refused"),
            ("?score=1", "score_refused", "query score http refused"),
            ("?alchemist=1", "alchemist_refused", "query alchemist http refused"),
        )
        for suffix, code, label in queries:
            st, payload = call("GET", "/api/amg/journey-workflow" + suffix, MATT)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, again = call("GET", "/api/amg/journey-workflow", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("live_journey") is False
            and again.get("guest_operations") is False
            and again.get("booking_count") is None
            and again.get("occupancy") is None
            and again.get("yanolja_live") is False
            and again.get("yanolja_write") is False
            and again.get("payment") is None
            and again.get("current") is False,
            str(again)[:240],
        )
        flags = (again.get("honesty") or {}) if isinstance(again, dict) else {}
        check("owner still specified", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
        check("http left no live file", not base.DEFAULT_DB.exists())
        st, strategy = call("GET", "/api/ggv/strategy-machine", MATT)
        check(
            "strategy lane still owner readable",
            st == 200 and isinstance(strategy, dict) and strategy.get("cap") == "CAP-GGV-01",
            str(strategy)[:180] if isinstance(strategy, dict) else str(st),
        )
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="amg-journey-workflow-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    strategy_before = hashlib.sha256(STRATEGY_MODULE.read_bytes()).hexdigest()
    live_existed = base.DEFAULT_DB.exists()
    try:
        test_empty_framework()
        test_refuses(td)
        test_ledger_ceiling(td)
        test_source()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    check("credits unchanged", hashlib.sha256(CREDITS.read_bytes()).hexdigest() == credits_before)
    check("cr row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("resolved count unchanged", _resolved_count() == resolved_before)
    check("media assets count unchanged", _media_count() == media_before)
    check(
        "cap-ggv-01 module unchanged",
        hashlib.sha256(STRATEGY_MODULE.read_bytes()).hexdigest() == strategy_before,
    )
    for rel, digest in wip_before.items():
        check(f"wip unchanged {Path(rel).name}", hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest)
    check(
        "live framework still absent" if not live_existed else "live framework untouched",
        (not base.DEFAULT_DB.exists()) if not live_existed else True,
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
