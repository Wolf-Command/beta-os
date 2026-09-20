#!/usr/bin/env python3
"""CAP-AMG-06 SLA/incident trail framework. Empty is not a live SLA trail."""
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
os.environ.pop("WOLF_ALLOW_LIVE_AMG_SLA_INCIDENT", None)

from core import amg_sla_incident as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "amg_sla_incident.py"
IMPROVE_MODULE = SCRIPTS / "core" / "amg_service_improve.py"
JOURNEY_MODULE = SCRIPTS / "core" / "amg_journey_workflow.py"
OPS_MODULE = SCRIPTS / "core" / "amg_daily_ops_state.py"
PACKAGES_MODULE = SCRIPTS / "core" / "amg_packages_products.py"
YIELD_MODULE = SCRIPTS / "core" / "amg_revenue_yield.py"
BZG_MODULE = SCRIPTS / "core" / "bzg_venue_pnl.py"
CR_ID = "CR-e9b3d23e63c1c8a7"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["request", "incident", "sla", "escalation", "trail", "notes"]
NEXT_ACTION = "SLA/incident trail"


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
        and row["request"] is None
        and row["incident"] is None
        and row["incident_number"] is None
        and row["sla"] is None
        and row["sla_timer"] is None
        and row["escalation"] is None
        and row["escalation_outcome"] is None
        and row["trail"] is None
        and row["current"] is False
        and row["live_request"] is False
        and row["live_incident"] is False
        and row["live_sla"] is False
        and row["guest_experience_machinery"] is False
        and row["guest_blast"] is False
        and row["public_post"] is False
        and row["yanolja_write"] is False
        and row["payment"] is None
        and row["payment_executed"] is False
    )


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not sla trail",
        report["empty_is_sla_trail"] is False
        and report["empty_is_guest_experience"] is False
        and report["proved"] is False
        and report["empty_is_ready"] is False
        and report["live_incident"] is False
        and report["live_sla"] is False
        and report["guest_experience_machinery"] is False,
    )
    check(
        "metrics unread",
        report["request"] is None
        and report["incident"] is None
        and report["incident_number"] is None
        and report["sla"] is None
        and report["sla_timer"] is None
        and report["escalation"] is None
        and report["escalation_outcome"] is None
        and report["trail"] is None
        and report["invented_incident"] is False
        and report["invented_sla"] is False
        and report["invented_escalation"] is False,
    )
    check("not current", report["current"] is False)
    check("guest quiet", report["guest_blast"] is False and report["public_post"] is False)
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
        and report["schema"]["request_property"] is False
        and report["schema"]["incident_property"] is False
        and report["schema"]["sla_property"] is False
        and report["schema"]["escalation_property"] is False
        and report["schema"]["trail_property"] is False
        and report["schema"]["guest_blast_property"] is False
        and report["schema"]["public_post_property"] is False
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
    check("six kinds", [row["kind"] for row in kinds] == KINDS)
    check("every slot empty", all(_slot_empty(row) for row in kinds))
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-AMG-06" and flags["cr_id"] == CR_ID and flags["bound"] == "beta-amg-ops-safe")
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED" and flags["specified"] is True)
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not invented",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["built"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["invented_incident"] is False
        and flags["invented_sla"] is False
        and flags["invented_escalation"] is False
        and flags["guest_experience_machinery"] is False
        and flags["request"] is None
        and flags["incident"] is None
        and flags["sla"] is None
        and flags["escalation"] is None
        and flags["trail"] is None
        and flags["guest_blast"] is False
        and flags["public_post"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-AMG-06" and flags["cr_capability"] == "CAP-AMG-06")
        check("cr next action", row[3] == NEXT_ACTION and flags["cr_next_action"] == row[3])
    check("gaps name the empty framework", "An empty framework is not a live SLA/incident trail." in report["gaps"])
    check("gaps name not guest experience", "An empty framework is not proof of guest experience loop machinery." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("gaps stay specified", "CAP-AMG-06 stays SPECIFIED." in report["gaps"])
    check("gaps ceiling built", "The ceiling label is BUILT." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    request = base.read_kind("request")
    check(
        "request slot read",
        request["ok"] is True
        and request["kind"]["kind"] == "request"
        and request["empty"] is True
        and request["proved"] is False
        and request["live_incident"] is False
        and request["guest_experience_machinery"] is False
        and request["request"] is None
        and request["incident"] is None
        and request["sla"] is None,
    )
    notes = base.read_kind("notes")
    check("notes slot read", notes["ok"] is True and notes["kind"]["kind"] == "notes" and notes["incident"] is None)
    escalation = base.read_kind("escalation")
    check(
        "escalation slot read",
        escalation["ok"] is True and escalation["kind"]["kind"] == "escalation" and escalation["guest_blast"] is False,
    )
    for bad, label in (("yanolja", "yanolja"), ("ready", "ready"), ("review", "review"), ("finding", "finding")):
        try:
            base.read_kind(bad)
            check(f"{label} is not a slot", False)
        except base.SlaIncidentError as exc:
            check(f"{label} is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.SlaIncidentError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.SlaIncidentError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.SlaIncidentError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    wolf = td / "wolf-system-copy.sqlite"
    wolf.write_bytes(b"sentinel-wolf")
    wolf_before = wolf.read_bytes()
    try:
        base.refuse_store(wolf)
        check("wolf-system path refused", False)
    except base.SlaIncidentError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    check("wolf-system sentinel unchanged", wolf.read_bytes() == wolf_before)
    bank = td / "bank.sqlite"
    bank.write_bytes(b"sentinel-bank")
    bank_before = bank.read_bytes()
    try:
        base.refuse_store(bank)
        check("bank path refused", False)
    except base.SlaIncidentError as exc:
        check("bank path refused", exc.code == "bank_refused", exc.code)
    check("bank sentinel unchanged", bank.read_bytes() == bank_before)
    pay = td / "payment.sqlite"
    pay.write_bytes(b"sentinel-pay")
    pay_before = pay.read_bytes()
    try:
        base.refuse_store(pay)
        check("payment path refused", False)
    except base.SlaIncidentError as exc:
        check("payment path refused", exc.code == "payment_refused", exc.code)
    check("payment sentinel unchanged", pay.read_bytes() == pay_before)
    books = td / "zayen-books.sqlite"
    books.write_bytes(b"sentinel-books")
    books_before = books.read_bytes()
    try:
        base.refuse_store(books)
        check("books path refused", False)
    except base.SlaIncidentError as exc:
        check("books path refused", exc.code == "books_refused", exc.code)
    check("books sentinel unchanged", books.read_bytes() == books_before)
    yanolja = td / "yanolja.sqlite"
    yanolja.write_bytes(b"sentinel-yanolja")
    yanolja_before = yanolja.read_bytes()
    try:
        base.refuse_store(yanolja)
        check("yanolja path refused", False)
    except base.SlaIncidentError as exc:
        check("yanolja path refused", exc.code == "yanolja_refused", exc.code)
    check("yanolja sentinel unchanged", yanolja.read_bytes() == yanolja_before)
    guest = td / "guest-blast.sqlite"
    guest.write_bytes(b"sentinel-guest")
    guest_before = guest.read_bytes()
    try:
        base.refuse_store(guest)
        check("guest blast path refused", False)
    except base.SlaIncidentError as exc:
        check("guest blast path refused", exc.code == "guest_blast_refused", exc.code)
    check("guest blast sentinel unchanged", guest.read_bytes() == guest_before)
    public = td / "public-post.sqlite"
    public.write_bytes(b"sentinel-public")
    public_before = public.read_bytes()
    try:
        base.refuse_store(public)
        check("public post path refused", False)
    except base.SlaIncidentError as exc:
        check("public post path refused", exc.code == "public_post_refused", exc.code)
    check("public post sentinel unchanged", public.read_bytes() == public_before)
    try:
        base.refuse_store(td / "model-c-baseline-assessments.json")
        check("ledger path refused", False)
    except base.SlaIncidentError as exc:
        check("ledger path refused", exc.code == "ledger_write_refused", exc.code)
    check("ledger fixture absent", not (td / "model-c-baseline-assessments.json").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.SlaIncidentError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.SlaIncidentError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    refusals = (
        (base.refuse_fill, {"kind": "notes", "status": "NOTED"}, "slots_refused", "fill refused"),
        (base.refuse_payment, {"payment": "1500000"}, "payment_refused", "payment refused"),
        (base.refuse_bank, {}, "bank_refused", "bank refused"),
        (base.refuse_books, {}, "books_refused", "books refused"),
        (base.call_yanolja, None, "yanolja_refused", "yanolja helper"),
        (base.blast_guests, None, "guest_blast_refused", "guest blast helper"),
        (base.post_public, None, "public_post_refused", "public post helper"),
        (base.move_money, None, "payment_refused", "money helper"),
        (base.mark_current, None, "current_refused", "current helper"),
        (base.invent_incident, None, "current_refused", "incident helper"),
        (base.invent_sla, None, "current_refused", "sla helper"),
        (base.invent_escalation, None, "current_refused", "escalation helper"),
        (base.refuse_cloudflare, {}, "cloudflare_refused", "cloudflare refused"),
        (base.refuse_access, {}, "access_refused", "access refused"),
        (base.mark_proven, None, "proven_refused", "prove helper"),
        (base.mark_ready, None, "ready_refused", "ready helper"),
        (base.resolve_cr, None, "resolve_refused", "resolve helper"),
        (base.refuse_score, {}, "score_refused", "score refused"),
        (base.refuse_alchemist, {}, "alchemist_refused", "alchemist helper"),
        (base.refuse_production, {}, "production_refused", "production helper"),
    )
    for fn, arg, code, label in refusals:
        try:
            fn() if arg is None else fn(arg)
            check(label, False)
        except base.SlaIncidentError as exc:
            check(label, exc.code == code, exc.code)
    bodies = (
        ({"payment": 1}, "payment_refused", "body payment refused"),
        ({"bank": "write"}, "bank_refused", "body bank refused"),
        ({"zayen": "write"}, "books_refused", "body books refused"),
        ({"yanolja": "call"}, "yanolja_refused", "body yanolja refused"),
        ({"guest_blast": 1}, "guest_blast_refused", "body guest blast refused"),
        ({"public_post": 1}, "public_post_refused", "body public post refused"),
        ({"request": "x"}, "current_refused", "body request refused"),
        ({"incident": "x"}, "current_refused", "body incident refused"),
        ({"sla": "1h"}, "current_refused", "body sla refused"),
        ({"escalation": "y"}, "current_refused", "body escalation refused"),
        ({"trail": "z"}, "current_refused", "body trail refused"),
        ({"current": "yes"}, "current_refused", "body current refused"),
        ({"cloudflare": "flip"}, "cloudflare_refused", "body cloudflare refused"),
        ({"access": "mutate"}, "access_refused", "body access refused"),
        ({"notes": "filled"}, "slots_refused", "body notes slot refused"),
        ({"score": 99}, "score_refused", "body score refused"),
        ({"alchemist": "write"}, "alchemist_refused", "body alchemist refused"),
        ({"proven": 1}, "proven_refused", "body proven refused"),
        ({"ready": 1}, "ready_refused", "body ready refused"),
        ({"resolve": 1}, "resolve_refused", "body resolve refused"),
        ({"production": 1}, "production_refused", "body production refused"),
    )
    for body, code, label in bodies:
        try:
            base.refuse_external_write(body)
            check(label, False)
        except base.SlaIncidentError as exc:
            check(label, exc.code == code, exc.code)
    queries = (
        ({"payment": "1"}, "payment_refused", "query payment refused"),
        ({"bank": "1"}, "bank_refused", "query bank refused"),
        ({"books": "1"}, "books_refused", "query books refused"),
        ({"yanolja": "1"}, "yanolja_refused", "query yanolja refused"),
        ({"guest_blast": "1"}, "guest_blast_refused", "query guest blast refused"),
        ({"public_post": "1"}, "public_post_refused", "query public post refused"),
        ({"request": "1"}, "current_refused", "query request refused"),
        ({"incident": "1"}, "current_refused", "query incident refused"),
        ({"sla": "1"}, "current_refused", "query sla refused"),
        ({"escalation": "1"}, "current_refused", "query escalation refused"),
        ({"trail": "1"}, "current_refused", "query trail refused"),
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
        except base.SlaIncidentError as exc:
            check(label, exc.code == code, exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-AMG-06": [state, "note"]}), encoding="utf-8")
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
        and live["guest_experience_machinery"] is False
        and live["request"] is None
        and live["incident"] is None
        and live["sla"] is None
        and live["escalation"] is None
        and live["trail"] is None
        and live["guest_blast"] is False
        and live["public_post"] is False,
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
    check("module does not import journey", "amg_journey_workflow" not in joined)
    check("module does not import daily ops", "amg_daily_ops_state" not in joined)
    check("module does not import packages", "amg_packages_products" not in joined)
    check("module does not import revenue yield", "amg_revenue_yield" not in joined)
    check("module does not import venue pnl", "bzg_venue_pnl" not in joined)
    check("module does not import service improve", "amg_service_improve" not in joined)
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
    check("route registered", "/api/amg/sla-incident" in serve)
    check("page route registered", "/amg-sla-incident" in serve)
    check("payment route refused", "/api/amg/sla-incident/payment" in serve)
    check("bank route refused", "/api/amg/sla-incident/bank" in serve)
    check("books route refused", "/api/amg/sla-incident/zayen" in serve)
    check("yanolja route refused", "/api/amg/sla-incident/yanolja" in serve)
    check("guest blast route refused", "/api/amg/sla-incident/guest-blast" in serve)
    check("public post route refused", "/api/amg/sla-incident/public-post" in serve)
    check("cloudflare route refused", "/api/amg/sla-incident/cloudflare" in serve)
    check("access route refused", "/api/amg/sla-incident/access" in serve)
    check("prove route refused", "/api/amg/sla-incident/prove" in serve)
    check("ready route refused", "/api/amg/sla-incident/ready" in serve)
    check("resolve route refused", "/api/amg/sla-incident/resolve" in serve)
    check("score route refused", "/api/amg/sla-incident/score" in serve)
    check("alchemist route refused", "/api/amg/sla-incident/alchemist" in serve)
    check("fill route refused", "/api/amg/sla-incident/fill" in serve)
    check("journey route still present", "/api/amg/journey-workflow" in serve)
    check("daily ops route still present", "/api/amg/daily-ops-state" in serve)
    check("packages route still present", "/api/amg/packages-products" in serve)
    check("yield route still present", "/api/amg/revenue-yield" in serve)
    check("venue pnl route still present", "/api/bzg/venue-pnl" in serve)
    check("service improve route still present", "/api/amg/service-improve" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "amg-sla-incident.html").read_text(encoding="utf-8")
    check("page says not loop", "not a live SLA/incident trail" in page and "not READY" in page)
    check("page says not machinery", "not proof of guest experience loop machinery" in page)
    check("page stays specified", "CAP-AMG-06 stays SPECIFIED" in page)
    check("page ceiling built", "ceiling label is BUILT" in page)
    check("page does not resolve", "does not resolve" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page no yanolja", "does not call Yanolja" in page)
    check("page no guest blast", "does not guest blast" in page)
    check("page no public post", "does not public post" in page)
    check(
        "page no invented metrics",
        "does not invent live incidents" in page
        and "does not invent SLA timers" in page
        and "does not invent escalation outcomes" in page,
    )
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

        st, _anon = call("GET", "/api/amg/sla-incident", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/amg/sla-incident", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/amg/sla-incident", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check(
                "owner not sla trail",
                owner.get("empty_is_sla_trail") is False
                and owner.get("empty_is_guest_experience") is False
                and owner.get("proved") is False
                and owner.get("empty_is_ready") is False
                and owner.get("live_incident") is False
                and owner.get("live_sla") is False
                and owner.get("guest_experience_machinery") is False,
            )
            check(
                "owner metrics null",
                owner.get("request") is None
                and owner.get("incident") is None
                and owner.get("incident_number") is None
                and owner.get("sla") is None
                and owner.get("sla_timer") is None
                and owner.get("escalation") is None
                and owner.get("escalation_outcome") is None
                and owner.get("trail") is None
                and owner.get("current") is False
                and owner.get("invented_incident") is False
                and owner.get("invented_sla") is False
                and owner.get("invented_escalation") is False
                and owner.get("guest_blast") is False
                and owner.get("public_post") is False,
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
                and flags.get("specified") is True
                and flags.get("request") is None
                and flags.get("incident") is None
                and flags.get("sla") is None
                and flags.get("escalation") is None,
            )
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("request") is None
                    and row.get("incident") is None
                    and row.get("sla") is None
                    and row.get("guest_experience_machinery") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/amg/sla-incident/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/amg/sla-incident/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/amg/sla-incident/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200
            and isinstance(kinds, dict)
            and kinds.get("empty_is_sla_trail") is False
            and kinds.get("empty_is_guest_experience") is False,
            str(st),
        )
        slot_paths = (
            ("/api/amg/sla-incident/request", "request", "request slot 200"),
            ("/api/amg/sla-incident/incident", "incident", "incident slot 200"),
            ("/api/amg/sla-incident/sla", "sla", "sla slot 200"),
            ("/api/amg/sla-incident/escalation", "escalation", "escalation slot 200"),
            ("/api/amg/sla-incident/trail", "trail", "trail slot 200"),
            ("/api/amg/sla-incident/notes", "notes", "notes slot 200"),
        )
        for path, kind, label in slot_paths:
            st, slot = call("GET", path, MATT)
            check(
                label,
                st == 200
                and isinstance(slot, dict)
                and (slot.get("kind") or {}).get("kind") == kind
                and slot.get("proved") is False
                and slot.get("request") is None
                and slot.get("incident") is None
                and slot.get("sla") is None
                and slot.get("guest_blast") is False
                and slot.get("public_post") is False,
                str(slot)[:180],
            )
        st, missing = call("GET", "/api/amg/sla-incident/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/amg-sla-incident", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not a live SLA/incident trail" in page
            and b"not proof of guest experience loop machinery" in page
            and b"stays SPECIFIED" in page
            and b"does not resolve" in page
            and b"does not call Yanolja" in page
            and b"does not guest blast" in page
            and b"does not public post" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/amg-sla-incident", None)
        check("anon page 403", st == 403, str(st))
        posts = (
            ("/api/amg/sla-incident/payment", {"payment": 100}, "payment_refused", "payment POST 405"),
            ("/api/amg/sla-incident/bank", {}, "bank_refused", "bank POST 405"),
            ("/api/amg/sla-incident/zayen", {}, "books_refused", "zayen POST 405"),
            ("/api/amg/sla-incident/books", {}, "books_refused", "books POST 405"),
            ("/api/amg/sla-incident/yanolja", {}, "yanolja_refused", "yanolja POST 405"),
            ("/api/amg/sla-incident/guest-blast", {}, "guest_blast_refused", "guest blast POST 405"),
            ("/api/amg/sla-incident/public-post", {}, "public_post_refused", "public post POST 405"),
            ("/api/amg/sla-incident/request", {"request": "x"}, "current_refused", "request POST 405"),
            ("/api/amg/sla-incident/incident", {"incident": "x"}, "current_refused", "incident POST 405"),
            ("/api/amg/sla-incident/sla", {"sla": "1h"}, "current_refused", "sla POST 405"),
            ("/api/amg/sla-incident/escalation", {"escalation": "y"}, "current_refused", "escalation POST 405"),
            ("/api/amg/sla-incident/trail", {"trail": "z"}, "current_refused", "trail POST 405"),
            ("/api/amg/sla-incident/current", {}, "current_refused", "current POST 405"),
            ("/api/amg/sla-incident/cloudflare", {}, "cloudflare_refused", "cloudflare POST 405"),
            ("/api/amg/sla-incident/access", {}, "access_refused", "access POST 405"),
            ("/api/amg/sla-incident/prove", {}, "proven_refused", "prove POST 405"),
            ("/api/amg/sla-incident/ready", {}, "ready_refused", "ready POST 405"),
            ("/api/amg/sla-incident/resolve", {}, "resolve_refused", "resolve POST 405"),
            ("/api/amg/sla-incident/production", {}, "production_refused", "production POST 405"),
            ("/api/amg/sla-incident/score", {}, "score_refused", "score POST 405"),
            ("/api/amg/sla-incident/alchemist", {}, "alchemist_refused", "alchemist POST 405"),
            ("/api/amg/sla-incident/fill", {}, "slots_refused", "fill POST 405"),
            ("/api/amg/sla-incident/note", {"kind": "notes", "status": "NOTED"}, "slots_refused", "note POST 405"),
            ("/api/amg/sla-incident/notes", {}, "slots_refused", "notes POST 405"),
        )
        for path, body, code, label in posts:
            st, payload = call("POST", path, MATT, body)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, bare = call("POST", "/api/amg/sla-incident", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/amg/sla-incident", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/amg/sla-incident", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/amg/sla-incident/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        queries = (
            ("?payment=1", "payment_refused", "query payment http refused"),
            ("?yanolja=1", "yanolja_refused", "query yanolja http refused"),
            ("?guest_blast=1", "guest_blast_refused", "query guest blast http refused"),
            ("?public_post=1", "public_post_refused", "query public post http refused"),
            ("?request=1", "current_refused", "query request http refused"),
            ("?incident=1", "current_refused", "query incident http refused"),
            ("?sla=1", "current_refused", "query sla http refused"),
            ("?cloudflare=1", "cloudflare_refused", "query cloudflare http refused"),
            ("?score=1", "score_refused", "query score http refused"),
            ("?alchemist=1", "alchemist_refused", "query alchemist http refused"),
        )
        for suffix, code, label in queries:
            st, payload = call("GET", "/api/amg/sla-incident" + suffix, MATT)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, again = call("GET", "/api/amg/sla-incident", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("live_incident") is False
            and again.get("guest_experience_machinery") is False
            and again.get("request") is None
            and again.get("incident") is None
            and again.get("sla") is None
            and again.get("guest_blast") is False
            and again.get("public_post") is False
            and again.get("yanolja_write") is False
            and again.get("payment") is None
            and again.get("current") is False,
            str(again)[:240],
        )
        flags = (again.get("honesty") or {}) if isinstance(again, dict) else {}
        check("owner still specified", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
        check("http left no live file", not base.DEFAULT_DB.exists())
        st, journey = call("GET", "/api/amg/journey-workflow", MATT)
        check(
            "journey lane still owner readable",
            st == 200 and isinstance(journey, dict) and journey.get("cap") == "CAP-AMG-02",
            str(journey)[:180] if isinstance(journey, dict) else str(st),
        )
        st, ops = call("GET", "/api/amg/daily-ops-state", MATT)
        check(
            "daily ops lane still owner readable",
            st == 200 and isinstance(ops, dict) and ops.get("cap") == "CAP-AMG-04",
            str(ops)[:180] if isinstance(ops, dict) else str(st),
        )
        st, packages = call("GET", "/api/amg/packages-products", MATT)
        check(
            "packages lane still owner readable",
            st == 200 and isinstance(packages, dict) and packages.get("cap") == "CAP-AMG-03",
            str(packages)[:180] if isinstance(packages, dict) else str(st),
        )
        st, yield_pack = call("GET", "/api/amg/revenue-yield", MATT)
        check(
            "yield lane still owner readable",
            st == 200 and isinstance(yield_pack, dict) and yield_pack.get("cap") == "CAP-AMG-05",
            str(yield_pack)[:180] if isinstance(yield_pack, dict) else str(st),
        )
        st, pnl = call("GET", "/api/bzg/venue-pnl", MATT)
        check(
            "venue pnl lane still owner readable",
            st == 200 and isinstance(pnl, dict) and pnl.get("cap") == "CAP-BZG-02",
            str(pnl)[:180] if isinstance(pnl, dict) else str(st),
        )
        st, improve = call("GET", "/api/amg/service-improve", MATT)
        check(
            "service improve lane still owner readable",
            st == 200 and isinstance(improve, dict) and improve.get("cap") == "CAP-AMG-07",
            str(improve)[:180] if isinstance(improve, dict) else str(st),
        )
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="amg-sla-incident-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    journey_before = hashlib.sha256(JOURNEY_MODULE.read_bytes()).hexdigest()
    ops_before = hashlib.sha256(OPS_MODULE.read_bytes()).hexdigest()
    packages_before = hashlib.sha256(PACKAGES_MODULE.read_bytes()).hexdigest()
    yield_before = hashlib.sha256(YIELD_MODULE.read_bytes()).hexdigest()
    bzg_before = hashlib.sha256(BZG_MODULE.read_bytes()).hexdigest()
    improve_before = hashlib.sha256(IMPROVE_MODULE.read_bytes()).hexdigest()
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
        "journey module unchanged",
        hashlib.sha256(JOURNEY_MODULE.read_bytes()).hexdigest() == journey_before,
    )
    check(
        "daily ops module unchanged",
        hashlib.sha256(OPS_MODULE.read_bytes()).hexdigest() == ops_before,
    )
    check(
        "packages module unchanged",
        hashlib.sha256(PACKAGES_MODULE.read_bytes()).hexdigest() == packages_before,
    )
    check(
        "yield module unchanged",
        hashlib.sha256(YIELD_MODULE.read_bytes()).hexdigest() == yield_before,
    )
    check(
        "venue pnl module unchanged",
        hashlib.sha256(BZG_MODULE.read_bytes()).hexdigest() == bzg_before,
    )
    check(
        "service improve module unchanged",
        hashlib.sha256(IMPROVE_MODULE.read_bytes()).hexdigest() == improve_before,
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
