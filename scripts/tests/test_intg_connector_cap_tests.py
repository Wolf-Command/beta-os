#!/usr/bin/env python3
"""CAP-INTG-04 connector tests framework. Empty is not a bank prove or a bank feed."""
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
os.environ.pop("WOLF_ALLOW_LIVE_INTG_CAP_TESTS", None)

from core import intg_connector_cap_tests as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "intg_connector_cap_tests.py"
CONTRACT_MODULE = SCRIPTS / "core" / "intg_connector_contract.py"
CR_ID = "CR-859e7cad64e7e4ad"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["cap", "fixture", "refuse"]


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


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not a prove",
        report["empty_is_prove"] is False
        and report["proved"] is False
        and report["empty_is_ready"] is False
        and report["live_bank_connector"] is False,
    )
    check("empty is not a bank feed", report["empty_is_bank_feed"] is False and report["bank_feed"] is None)
    check("calls unread", report["bank_api_called"] is False and report["bank_feed_called"] is False)
    check(
        "slots unread",
        report["fixture"] is None
        and report["bank_connector"] is None
        and report["current"] is False,
    )
    check(
        "payment not executed",
        report["payment"] is None and report["money"] is None and report["payment_executed"] is False,
    )
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("score unchanged", report["score_changed"] is False and report["external_write"] is False)
    check("not on disk", report["on_disk"] is False)
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["bank_api_property"] is False
        and report["schema"]["bank_feed_property"] is False
        and report["schema"]["current_property"] is False
        and report["schema"]["fixture_property"] is False
        and report["schema"]["cloudflare_property"] is False
        and report["schema"]["access_property"] is False
        and report["schema"]["proven_property"] is False
        and report["schema"]["ready_property"] is False
        and report["schema"]["kind_enum"] == KINDS,
    )
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check(
        "ledger not written",
        report["ledger_write"] is False
        and report["cr_resolved"] is False
        and report["cap_intg_01_rewritten"] is False,
    )
    kinds = report["kinds"]
    check("three kinds", [row["kind"] for row in kinds] == KINDS)
    check(
        "every slot empty",
        all(
            row["slot"] == "empty"
            and row["evidence"] is None
            and row["fixture"] is None
            and row["bank_feed"] is None
            and row["bank_connector"] is None
            and row["current"] is False
            and row["proved"] is False
            and row["payment"] is None
            and row["payment_executed"] is False
            and row["bank_api_called"] is False
            and row["bank_feed_called"] is False
            for row in kinds
        ),
    )
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-INTG-04" and flags["cr_id"] == CR_ID)
    check("ledger stays built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not invented",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["cap_intg_01"] == "ABSENT"
        and flags["cap_intg_01_rewritten"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-INTG-04" and flags["cr_capability"] == "CAP-INTG-04")
        check(
            "cr next action",
            row[3] == "CAP-bound connector tests" and flags["cr_next_action"] == row[3],
        )
    check("gaps name the empty framework", "An empty framework is not a live bank-connector prove." in report["gaps"])
    check("gaps name not a bank feed", "An empty framework is not a live bank feed." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("gaps stay built", "CAP-INTG-04 stays BUILT." in report["gaps"])
    check("gaps leave intg-01", "CAP-INTG-01 stays ABSENT." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    one = base.read_kind("cap")
    check(
        "cap slot read",
        one["ok"] is True
        and one["kind"]["kind"] == "cap"
        and one["empty"] is True
        and one["proved"] is False
        and one["bank_api_called"] is False
        and one["bank_feed_called"] is False
        and one["live_bank_connector"] is False,
    )
    try:
        base.read_kind("bank")
        check("bank is not a slot", False)
    except base.ConnectorCapTestsError as exc:
        check("bank is not a slot", exc.code == "not_found", exc.code)
    try:
        base.read_kind("feed")
        check("feed is not a slot", False)
    except base.ConnectorCapTestsError as exc:
        check("feed is not a slot", exc.code == "not_found", exc.code)
    try:
        base.read_kind("ready")
        check("ready is not a slot", False)
    except base.ConnectorCapTestsError as exc:
        check("ready is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    wolf = td / "wolf-system-copy.sqlite"
    wolf.write_bytes(b"sentinel-wolf")
    wolf_before = wolf.read_bytes()
    try:
        base.refuse_store(wolf)
        check("wolf-system path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    check("wolf-system sentinel unchanged", wolf.read_bytes() == wolf_before)
    bank = td / "plaid.sqlite"
    bank.write_bytes(b"sentinel-bank")
    bank_before = bank.read_bytes()
    try:
        base.refuse_store(bank)
        check("bank path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("bank path refused", exc.code == "bank_refused", exc.code)
    check("bank sentinel unchanged", bank.read_bytes() == bank_before)
    feed = td / "bank-feed.sqlite"
    feed.write_bytes(b"sentinel-feed")
    feed_before = feed.read_bytes()
    try:
        base.refuse_store(feed)
        check("feed path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("feed path refused", exc.code == "bank_refused", exc.code)
    check("feed sentinel unchanged", feed.read_bytes() == feed_before)
    try:
        base.refuse_store(base.CONTRACT_DB)
        check("contract path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("contract path refused", exc.code == "rewrite_refused", exc.code)
    try:
        base.refuse_store(td / "model-c-baseline-assessments.json")
        check("ledger path refused", False)
    except base.ConnectorCapTestsError as exc:
        check("ledger path refused", exc.code == "ledger_write_refused", exc.code)
    check("ledger fixture absent", not (td / "model-c-baseline-assessments.json").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.ConnectorCapTestsError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.ConnectorCapTestsError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    try:
        base.refuse_fill({"kind": "cap", "status": "NOTED"})
        check("fill refused", False)
    except base.ConnectorCapTestsError as exc:
        check("fill refused", exc.code == "slots_refused", exc.code)
    try:
        base.refuse_payment({"payment": "1500000"})
        check("payment refused", False)
    except base.ConnectorCapTestsError as exc:
        check("payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.call_bank_api()
        check("bank helper", False)
    except base.ConnectorCapTestsError as exc:
        check("bank helper", exc.code == "bank_refused", exc.code)
    try:
        base.call_bank_feed()
        check("feed helper", False)
    except base.ConnectorCapTestsError as exc:
        check("feed helper", exc.code == "feed_refused", exc.code)
    try:
        base.mark_current()
        check("current helper", False)
    except base.ConnectorCapTestsError as exc:
        check("current helper", exc.code == "current_refused", exc.code)
    try:
        base.refuse_cloudflare({})
        check("cloudflare refused", False)
    except base.ConnectorCapTestsError as exc:
        check("cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_access({})
        check("access refused", False)
    except base.ConnectorCapTestsError as exc:
        check("access refused", exc.code == "access_refused", exc.code)
    try:
        base.mark_proven()
        check("prove helper", False)
    except base.ConnectorCapTestsError as exc:
        check("prove helper", exc.code == "proven_refused", exc.code)
    try:
        base.mark_ready()
        check("ready helper", False)
    except base.ConnectorCapTestsError as exc:
        check("ready helper", exc.code == "ready_refused", exc.code)
    try:
        base.resolve_cr()
        check("resolve helper", False)
    except base.ConnectorCapTestsError as exc:
        check("resolve helper", exc.code == "resolve_refused", exc.code)
    try:
        base.refuse_score({})
        check("score refused", False)
    except base.ConnectorCapTestsError as exc:
        check("score refused", exc.code == "score_refused", exc.code)
    try:
        base.refuse_rewrite({})
        check("rewrite refused", False)
    except base.ConnectorCapTestsError as exc:
        check("rewrite refused", exc.code == "rewrite_refused", exc.code)
    try:
        base.refuse_external_write({"payment": 1})
        check("body payment refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.refuse_external_write({"bank": "call"})
        check("body bank refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body bank refused", exc.code == "bank_refused", exc.code)
    try:
        base.refuse_external_write({"feed": "call"})
        check("body feed refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body feed refused", exc.code == "feed_refused", exc.code)
    try:
        base.refuse_external_write({"current": "yes"})
        check("body current refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body current refused", exc.code == "current_refused", exc.code)
    try:
        base.refuse_external_write({"connector": "write"})
        check("body connector refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body connector refused", exc.code == "connector_refused", exc.code)
    try:
        base.refuse_external_write({"cloudflare": "flip"})
        check("body cloudflare refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_external_write({"access": "mutate"})
        check("body access refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body access refused", exc.code == "access_refused", exc.code)
    try:
        base.refuse_external_write({"cap": "filled"})
        check("body cap refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body cap refused", exc.code == "slots_refused", exc.code)
    try:
        base.refuse_external_write({"score": 99})
        check("body score refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body score refused", exc.code == "score_refused", exc.code)
    try:
        base.refuse_external_write({"rewrite": "CAP-INTG-01"})
        check("body rewrite refused", False)
    except base.ConnectorCapTestsError as exc:
        check("body rewrite refused", exc.code == "rewrite_refused", exc.code)
    try:
        base.guard_query(payment="1")
        check("query payment refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.guard_query(bank="1")
        check("query bank refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query bank refused", exc.code == "bank_refused", exc.code)
    try:
        base.guard_query(feed="1")
        check("query feed refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query feed refused", exc.code == "feed_refused", exc.code)
    try:
        base.guard_query(current="1")
        check("query current refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query current refused", exc.code == "current_refused", exc.code)
    try:
        base.guard_query(cloudflare="1")
        check("query cloudflare refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.guard_query(access="1")
        check("query access refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query access refused", exc.code == "access_refused", exc.code)
    try:
        base.guard_query(score="1")
        check("query score refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query score refused", exc.code == "score_refused", exc.code)
    try:
        base.guard_query(rewrite="1")
        check("query rewrite refused", False)
    except base.ConnectorCapTestsError as exc:
        check("query rewrite refused", exc.code == "rewrite_refused", exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str, other: str = "ABSENT") -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(
            json.dumps({"CAP-INTG-04": [state, "note"], "CAP-INTG-01": [other, "note"]}),
            encoding="utf-8",
        )
        return path

    absent = write("ABSENT")
    absent_before = absent.read_bytes()
    flags = base.honesty_flags(absent, CATALOG_DB)
    check("absent stays absent", flags["maturity"] == "ABSENT" and flags["maturity_ceiling"] == "BUILT")
    check("absent file untouched", absent.read_bytes() == absent_before)
    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = base.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT")
    check("specified file untouched", specified.read_bytes() == before)
    built = write("BUILT")
    built_before = built.read_bytes()
    flags = base.honesty_flags(built, CATALOG_DB)
    check("built ceiling stays built", flags["maturity"] == "BUILT" and flags["maturity_ceiling"] == "BUILT")
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
    other = write("BUILT", "SPECIFIED")
    other_before = other.read_bytes()
    flags = base.honesty_flags(other, CATALOG_DB)
    check(
        "other cap is read not written",
        flags["cap_intg_01"] == "SPECIFIED" and flags["cap_intg_01_rewritten"] is False,
    )
    check("other file untouched", other.read_bytes() == other_before)
    missing = base.honesty_flags(td / "missing-ledger.json", CATALOG_DB)
    check("missing ledger unknown", missing["maturity"] == "UNKNOWN" and missing["maturity_ceiling"] == "BUILT")
    live = base.honesty_flags()
    check(
        "live ledger built ceiling built",
        live["maturity"] == "BUILT"
        and live["maturity_ceiling"] == "BUILT"
        and live["proven"] is False
        and live["ready"] is False
        and live["cap_intg_01"] == "ABSENT"
        and live["invented_proven"] is False,
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
    check("module does not import contract writer", "intg_connector_contract" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not call cloudflare", "api.cloudflare.com" not in src)
    check("module does not call a bank host", "plaid.com" not in src and "openbanking.com" not in src)
    check("module does not json.dump(", "json.dump(" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not update completion", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("module does not insert evidence", "INSERT INTO" not in src and "CREATE TABLE" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/intg/connector-cap-tests" in serve)
    check("page route registered", "/connector-cap-tests" in serve)
    check("payment route refused", "/api/intg/connector-cap-tests/payment" in serve)
    check("bank route refused", "/api/intg/connector-cap-tests/bank" in serve)
    check("feed route refused", "/api/intg/connector-cap-tests/bank-feed" in serve)
    check("current route refused", "/api/intg/connector-cap-tests/current" in serve)
    check("connector route refused", "/api/intg/connector-cap-tests/connector" in serve)
    check("cloudflare route refused", "/api/intg/connector-cap-tests/cloudflare" in serve)
    check("access route refused", "/api/intg/connector-cap-tests/access" in serve)
    check("prove route refused", "/api/intg/connector-cap-tests/prove" in serve)
    check("ready route refused", "/api/intg/connector-cap-tests/ready" in serve)
    check("resolve route refused", "/api/intg/connector-cap-tests/resolve" in serve)
    check("score route refused", "/api/intg/connector-cap-tests/score" in serve)
    check("rewrite route refused", "/api/intg/connector-cap-tests/rewrite" in serve)
    check("fill route refused", "/api/intg/connector-cap-tests/fill" in serve)
    check("contract route still present", "/api/intg/connector-contract" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "connector-cap-tests.html").read_text(encoding="utf-8")
    check("page says not a prove", "not a live bank-connector prove" in page and "not READY" in page)
    check("page says not a bank feed", "not a live bank feed" in page)
    check("page stays built", "CAP-INTG-04 stays BUILT" in page)
    check("page leaves intg-01", "CAP-INTG-01 stays ABSENT" in page)
    check("page does not resolve", "does not resolve" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page ceiling built", "ceiling label is BUILT" in page)
    check("page no bank api", "does not call a bank API" in page)
    check("page no payment", "does not execute a payment" in page)


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

        st, _anon = call("GET", "/api/intg/connector-cap-tests", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/intg/connector-cap-tests", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/intg/connector-cap-tests", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check(
                "owner not prove",
                owner.get("empty_is_prove") is False
                and owner.get("proved") is False
                and owner.get("empty_is_ready") is False
                and owner.get("live_bank_connector") is False,
            )
            check("owner not a bank feed", owner.get("empty_is_bank_feed") is False and owner.get("bank_feed") is None)
            check("owner calls unread", owner.get("bank_api_called") is False and owner.get("bank_feed_called") is False)
            check("owner slots unread", owner.get("fixture") is None and owner.get("bank_connector") is None)
            check("owner current false", owner.get("current") is False)
            check(
                "owner payment null",
                owner.get("payment") is None
                and owner.get("money") is None
                and owner.get("payment_executed") is False,
            )
            check("owner edge quiet", owner.get("cloudflare_mutated") is False and owner.get("access_mutated") is False)
            check("owner no resolve", owner.get("cr_resolved") is False and owner.get("on_disk") is False)
            check("owner did not rewrite", owner.get("cap_intg_01_rewritten") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check(
                "owner ceiling",
                flags.get("maturity") == "BUILT"
                and flags.get("maturity_ceiling") == "BUILT"
                and flags.get("cap_intg_01") == "ABSENT",
            )
            check(
                "owner did not invent",
                flags.get("invented_proven") is False
                and flags.get("invented_ready") is False
                and flags.get("proven") is False
                and flags.get("ready") is False,
            )
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("bank_api_called") is False
                    and row.get("bank_feed_called") is False
                    and row.get("proved") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/intg/connector-cap-tests/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/intg/connector-cap-tests/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/intg/connector-cap-tests/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200
            and isinstance(kinds, dict)
            and kinds.get("empty_is_prove") is False
            and kinds.get("empty_is_bank_feed") is False,
            str(st),
        )
        st, slot = call("GET", "/api/intg/connector-cap-tests/fixture", MATT)
        check(
            "fixture slot 200",
            st == 200
            and isinstance(slot, dict)
            and (slot.get("kind") or {}).get("kind") == "fixture"
            and slot.get("proved") is False
            and slot.get("bank_feed_called") is False,
            str(slot)[:180],
        )
        st, refuse = call("GET", "/api/intg/connector-cap-tests/refuse", MATT)
        check(
            "refuse slot 200",
            st == 200
            and isinstance(refuse, dict)
            and (refuse.get("kind") or {}).get("kind") == "refuse"
            and refuse.get("bank_api_called") is False
            and refuse.get("live_bank_connector") is False,
            str(refuse)[:180],
        )
        st, missing = call("GET", "/api/intg/connector-cap-tests/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/connector-cap-tests", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not a live bank-connector prove" in page
            and b"not a live bank feed" in page
            and b"stays BUILT" in page
            and b"stays ABSENT" in page
            and b"does not resolve" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/connector-cap-tests", None)
        check("anon page 403", st == 403, str(st))
        st, paid = call("POST", "/api/intg/connector-cap-tests/payment", MATT, {"payment": 100})
        check("payment POST 405", st == 405 and isinstance(paid, dict) and paid.get("error") == "payment_refused", str(paid)[:180])
        st, bank = call("POST", "/api/intg/connector-cap-tests/bank", MATT, {})
        check("bank POST 405", st == 405 and isinstance(bank, dict) and bank.get("error") == "bank_refused", str(bank)[:180])
        st, live_bank = call("POST", "/api/intg/connector-cap-tests/live-bank", MATT, {})
        check("live-bank POST 405", st == 405 and isinstance(live_bank, dict) and live_bank.get("error") == "bank_refused", str(live_bank)[:180])
        st, feed = call("POST", "/api/intg/connector-cap-tests/bank-feed", MATT, {})
        check("feed POST 405", st == 405 and isinstance(feed, dict) and feed.get("error") == "feed_refused", str(feed)[:180])
        st, current = call("POST", "/api/intg/connector-cap-tests/current", MATT, {})
        check("current POST 405", st == 405 and isinstance(current, dict) and current.get("error") == "current_refused", str(current)[:180])
        st, connector = call("POST", "/api/intg/connector-cap-tests/connector", MATT, {})
        check("connector POST 405", st == 405 and isinstance(connector, dict) and connector.get("error") == "connector_refused", str(connector)[:180])
        st, cf = call("POST", "/api/intg/connector-cap-tests/cloudflare", MATT, {})
        check("cloudflare POST 405", st == 405 and isinstance(cf, dict) and cf.get("error") == "cloudflare_refused", str(cf)[:180])
        st, access = call("POST", "/api/intg/connector-cap-tests/access", MATT, {})
        check("access POST 405", st == 405 and isinstance(access, dict) and access.get("error") == "access_refused", str(access)[:180])
        st, proved = call("POST", "/api/intg/connector-cap-tests/prove", MATT, {})
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, ready = call("POST", "/api/intg/connector-cap-tests/ready", MATT, {})
        check("ready POST 405", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:180])
        st, resolve = call("POST", "/api/intg/connector-cap-tests/resolve", MATT, {})
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, prod = call("POST", "/api/intg/connector-cap-tests/production", MATT, {})
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, score = call("POST", "/api/intg/connector-cap-tests/score", MATT, {})
        check("score POST 405", st == 405 and isinstance(score, dict) and score.get("error") == "score_refused", str(score)[:180])
        st, rewrite = call("POST", "/api/intg/connector-cap-tests/rewrite", MATT, {})
        check("rewrite POST 405", st == 405 and isinstance(rewrite, dict) and rewrite.get("error") == "rewrite_refused", str(rewrite)[:180])
        st, fill = call("POST", "/api/intg/connector-cap-tests/fill", MATT, {})
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, note = call("POST", "/api/intg/connector-cap-tests/note", MATT, {"kind": "cap", "status": "NOTED"})
        check("note POST 405", st == 405 and isinstance(note, dict) and note.get("error") == "slots_refused", str(note)[:180])
        st, bare = call("POST", "/api/intg/connector-cap-tests", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/intg/connector-cap-tests", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/intg/connector-cap-tests", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/intg/connector-cap-tests/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        st, qpay = call("GET", "/api/intg/connector-cap-tests?payment=1", MATT)
        check("query payment http refused", st == 405 and isinstance(qpay, dict) and qpay.get("error") == "payment_refused", str(qpay)[:180])
        st, qbank = call("GET", "/api/intg/connector-cap-tests?bank=1", MATT)
        check("query bank http refused", st == 405 and isinstance(qbank, dict) and qbank.get("error") == "bank_refused", str(qbank)[:180])
        st, qfeed = call("GET", "/api/intg/connector-cap-tests?feed=1", MATT)
        check("query feed http refused", st == 405 and isinstance(qfeed, dict) and qfeed.get("error") == "feed_refused", str(qfeed)[:180])
        st, qcf = call("GET", "/api/intg/connector-cap-tests?cloudflare=1", MATT)
        check("query cloudflare http refused", st == 405 and isinstance(qcf, dict) and qcf.get("error") == "cloudflare_refused", str(qcf)[:180])
        st, again = call("GET", "/api/intg/connector-cap-tests", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("bank_api_called") is False
            and again.get("bank_feed_called") is False
            and again.get("fixture") is None
            and again.get("payment") is None
            and again.get("current") is False,
            str(again)[:240],
        )
        flags = (again.get("honesty") or {}) if isinstance(again, dict) else {}
        check("owner still built", flags.get("maturity") == "BUILT" and flags.get("maturity_ceiling") == "BUILT")
        check("http left no live file", not base.DEFAULT_DB.exists())
        st, contract = call("GET", "/api/intg/connector-contract", MATT)
        check(
            "contract lane still owner readable",
            st == 200 and isinstance(contract, dict) and contract.get("cap") == "CAP-INTG-01",
            str(contract)[:180] if isinstance(contract, dict) else str(st),
        )
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="intg-connector-cap-tests-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    contract_before = hashlib.sha256(CONTRACT_MODULE.read_bytes()).hexdigest()
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
        "cap-intg-01 module unchanged",
        hashlib.sha256(CONTRACT_MODULE.read_bytes()).hexdigest() == contract_before,
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
