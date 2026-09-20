#!/usr/bin/env python3
"""CAP-HR-02 Hiring & Onboarding framework. Empty is not a live hiring workflow."""
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
os.environ.pop("WOLF_ALLOW_LIVE_HR_HIRING_ONBOARDING", None)

from core import hr_hiring_onboarding as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "hr_hiring_onboarding.py"
PMS_MODULE = SCRIPTS / "core" / "amg_pms_orchestration.py"
SLA_MODULE = SCRIPTS / "core" / "amg_sla_incident.py"
BOM_MODULE = SCRIPTS / "core" / "bzg_bom_yield.py"
CR_ID = "CR-934f33e65b834254"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["requisition", "candidate", "offer", "onboarding", "checklist", "notes"]
NEXT_ACTION = "Workflows"


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
        and row["requisition"] is None
        and row["requisition_number"] is None
        and row["candidate"] is None
        and row["candidate_number"] is None
        and row["hire"] is None
        and row["hire_number"] is None
        and row["offer"] is None
        and row["offer_number"] is None
        and row["onboarding"] is None
        and row["onboarding_number"] is None
        and row["checklist"] is None
        and row["current"] is False
        and row["live_hiring"] is False
        and row["live_hiring_onboarding"] is False
        and row["hr_hire_machinery"] is False
        and row["guest_blast"] is False
        and row["staff_blast"] is False
        and row["public_post"] is False
        and row["hr_master_write"] is False
        and row["payroll_executed"] is False
        and row["payment"] is None
        and row["payment_executed"] is False
    )


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not hiring workflow",
        report["empty_is_hiring_onboarding"] is False
        and report["empty_is_hr_hire_machinery"] is False
        and report["proved"] is False
        and report["empty_is_ready"] is False
        and report["live_hiring_onboarding"] is False
        and report["live_hiring"] is False
        and report["hr_hire_machinery"] is False,
    )
    check(
        "metrics unread",
        report["requisition"] is None
        and report["requisition_number"] is None
        and report["candidate"] is None
        and report["candidate_number"] is None
        and report["hire"] is None
        and report["hire_number"] is None
        and report["offer"] is None
        and report["offer_number"] is None
        and report["onboarding"] is None
        and report["onboarding_number"] is None
        and report["checklist"] is None
        and report["invented_hire"] is False
        and report["invented_candidate"] is False
        and report["invented_offer"] is False
        and report["invented_onboarding"] is False,
    )
    check("not current", report["current"] is False)
    check(
        "blast quiet",
        report["guest_blast"] is False
        and report["staff_blast"] is False
        and report["public_post"] is False,
    )
    check("hr master unread", report["hr_master_write"] is False)
    check("payroll unread", report["payroll_executed"] is False)
    check(
        "payment not executed",
        report["payment"] is None and report["money"] is None and report["payment_executed"] is False,
    )
    check("bank and books unread", report["bank_write"] is False and report["books_write"] is False and report["zayen_write"] is False)
    check("alchemist unread", report["alchemist_write"] is False)
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("score unchanged", report["score_changed"] is False)
    check("not on disk", report["on_disk"] is False)
    check("bound", report["bound"] == "beta-hr-safe")
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["bank_property"] is False
        and report["schema"]["books_property"] is False
        and report["schema"]["payroll_property"] is False
        and report["schema"]["hr_master_property"] is False
        and report["schema"]["requisition_property"] is False
        and report["schema"]["candidate_property"] is False
        and report["schema"]["offer_property"] is False
        and report["schema"]["onboarding_property"] is False
        and report["schema"]["checklist_property"] is False
        and report["schema"]["guest_blast_property"] is False
        and report["schema"]["staff_blast_property"] is False
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
    check("cap bound", flags["cap"] == "CAP-HR-02" and flags["cr_id"] == CR_ID and flags["bound"] == "beta-hr-safe")
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED" and flags["specified"] is True)
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not invented",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["built"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["invented_hire"] is False
        and flags["invented_candidate"] is False
        and flags["invented_offer"] is False
        and flags["invented_onboarding"] is False
        and flags["hr_hire_machinery"] is False
        and flags["hire"] is None
        and flags["candidate"] is None
        and flags["offer"] is None
        and flags["onboarding"] is None
        and flags["guest_blast"] is False
        and flags["staff_blast"] is False
        and flags["public_post"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-HR-02" and flags["cr_capability"] == "CAP-HR-02")
        check("cr next action", row[3] == NEXT_ACTION and flags["cr_next_action"] == row[3])
    check("gaps name the empty framework", "An empty framework is not a live hiring/onboarding workflow." in report["gaps"])
    check("gaps name not hr machinery", "An empty framework is not proof of HR hire machinery." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("gaps stay specified", "CAP-HR-02 stays SPECIFIED." in report["gaps"])
    check("gaps ceiling built", "The ceiling label is BUILT." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    req = base.read_kind("requisition")
    check(
        "requisition slot read",
        req["ok"] is True
        and req["kind"]["kind"] == "requisition"
        and req["empty"] is True
        and req["proved"] is False
        and req["live_hiring_onboarding"] is False
        and req["hr_hire_machinery"] is False
        and req["requisition"] is None
        and req["candidate"] is None
        and req["offer"] is None,
    )
    notes = base.read_kind("notes")
    check("notes slot read", notes["ok"] is True and notes["kind"]["kind"] == "notes" and notes["hire"] is None)
    candidate = base.read_kind("candidate")
    check(
        "candidate slot read",
        candidate["ok"] is True and candidate["kind"]["kind"] == "candidate" and candidate["staff_blast"] is False,
    )
    for bad, label in (("payroll", "payroll"), ("ready", "ready"), ("pms", "pms"), ("hire", "hire")):
        try:
            base.read_kind(bad)
            check(f"{label} is not a slot", False)
        except base.HiringOnboardingError as exc:
            check(f"{label} is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.HiringOnboardingError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    media_before = _media_count()
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.HiringOnboardingError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.HiringOnboardingError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    wolf = td / "wolf-system-copy.sqlite"
    wolf.write_bytes(b"sentinel-wolf")
    wolf_before = wolf.read_bytes()
    try:
        base.refuse_store(wolf)
        check("wolf-system path refused", False)
    except base.HiringOnboardingError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    check("wolf-system sentinel unchanged", wolf.read_bytes() == wolf_before)
    bank = td / "bank.sqlite"
    bank.write_bytes(b"sentinel-bank")
    bank_before = bank.read_bytes()
    try:
        base.refuse_store(bank)
        check("bank path refused", False)
    except base.HiringOnboardingError as exc:
        check("bank path refused", exc.code == "bank_refused", exc.code)
    check("bank sentinel unchanged", bank.read_bytes() == bank_before)
    pay = td / "payment.sqlite"
    pay.write_bytes(b"sentinel-pay")
    pay_before = pay.read_bytes()
    try:
        base.refuse_store(pay)
        check("payment path refused", False)
    except base.HiringOnboardingError as exc:
        check("payment path refused", exc.code == "payment_refused", exc.code)
    check("payment sentinel unchanged", pay.read_bytes() == pay_before)
    books = td / "zayen-books.sqlite"
    books.write_bytes(b"sentinel-books")
    books_before = books.read_bytes()
    try:
        base.refuse_store(books)
        check("books path refused", False)
    except base.HiringOnboardingError as exc:
        check("books path refused", exc.code == "books_refused", exc.code)
    check("books sentinel unchanged", books.read_bytes() == books_before)
    payroll = td / "payroll.sqlite"
    payroll.write_bytes(b"sentinel-payroll")
    payroll_before = payroll.read_bytes()
    try:
        base.refuse_store(payroll)
        check("payroll path refused", False)
    except base.HiringOnboardingError as exc:
        check("payroll path refused", exc.code == "payroll_refused", exc.code)
    check("payroll sentinel unchanged", payroll.read_bytes() == payroll_before)
    master = td / "hr-master.sqlite"
    master.write_bytes(b"sentinel-master")
    master_before = master.read_bytes()
    try:
        base.refuse_store(master)
        check("hr master path refused", False)
    except base.HiringOnboardingError as exc:
        check("hr master path refused", exc.code == "hr_master_refused", exc.code)
    check("hr master sentinel unchanged", master.read_bytes() == master_before)
    guest = td / "guest-blast.sqlite"
    guest.write_bytes(b"sentinel-guest")
    guest_before = guest.read_bytes()
    try:
        base.refuse_store(guest)
        check("guest blast path refused", False)
    except base.HiringOnboardingError as exc:
        check("guest blast path refused", exc.code == "guest_blast_refused", exc.code)
    check("guest blast sentinel unchanged", guest.read_bytes() == guest_before)
    staff = td / "staff-blast.sqlite"
    staff.write_bytes(b"sentinel-staff")
    staff_before = staff.read_bytes()
    try:
        base.refuse_store(staff)
        check("staff blast path refused", False)
    except base.HiringOnboardingError as exc:
        check("staff blast path refused", exc.code == "staff_blast_refused", exc.code)
    check("staff blast sentinel unchanged", staff.read_bytes() == staff_before)
    public = td / "public-post.sqlite"
    public.write_bytes(b"sentinel-public")
    public_before = public.read_bytes()
    try:
        base.refuse_store(public)
        check("public post path refused", False)
    except base.HiringOnboardingError as exc:
        check("public post path refused", exc.code == "public_post_refused", exc.code)
    check("public post sentinel unchanged", public.read_bytes() == public_before)
    try:
        base.refuse_store(td / "model-c-baseline-assessments.json")
        check("ledger path refused", False)
    except base.HiringOnboardingError as exc:
        check("ledger path refused", exc.code == "ledger_write_refused", exc.code)
    check("ledger fixture absent", not (td / "model-c-baseline-assessments.json").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.HiringOnboardingError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.HiringOnboardingError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    refusals = (
        (base.refuse_fill, {"kind": "notes", "status": "NOTED"}, "slots_refused", "fill refused"),
        (base.refuse_payment, {"payment": "1500000"}, "payment_refused", "payment refused"),
        (base.refuse_bank, {}, "bank_refused", "bank refused"),
        (base.refuse_books, {}, "books_refused", "books refused"),
        (base.execute_payroll, None, "payroll_refused", "payroll helper"),
        (base.write_hr_master, None, "hr_master_refused", "hr master helper"),
        (base.blast_guests, None, "guest_blast_refused", "guest blast helper"),
        (base.blast_staff, None, "staff_blast_refused", "staff blast helper"),
        (base.post_public, None, "public_post_refused", "public post helper"),
        (base.move_money, None, "payment_refused", "money helper"),
        (base.mark_current, None, "current_refused", "current helper"),
        (base.invent_hire, None, "current_refused", "hire helper"),
        (base.invent_candidate, None, "current_refused", "candidate helper"),
        (base.invent_offer, None, "current_refused", "offer helper"),
        (base.invent_onboarding, None, "current_refused", "onboarding helper"),
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
        except base.HiringOnboardingError as exc:
            check(label, exc.code == code, exc.code)
    bodies = (
        ({"payment": 1}, "payment_refused", "body payment refused"),
        ({"bank": "write"}, "bank_refused", "body bank refused"),
        ({"zayen": "write"}, "books_refused", "body books refused"),
        ({"payroll": "run"}, "payroll_refused", "body payroll refused"),
        ({"hr_master": "write"}, "hr_master_refused", "body hr master refused"),
        ({"guest_blast": 1}, "guest_blast_refused", "body guest blast refused"),
        ({"staff_blast": 1}, "staff_blast_refused", "body staff blast refused"),
        ({"public_post": 1}, "public_post_refused", "body public post refused"),
        ({"requisition": "x"}, "current_refused", "body requisition refused"),
        ({"candidate": "x"}, "current_refused", "body candidate refused"),
        ({"offer": "y"}, "current_refused", "body offer refused"),
        ({"onboarding": "z"}, "current_refused", "body onboarding refused"),
        ({"hire": "z"}, "current_refused", "body hire refused"),
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
        except base.HiringOnboardingError as exc:
            check(label, exc.code == code, exc.code)
    try:
        base.guard_query(payroll="1")
        check("query payroll refused", False)
    except base.HiringOnboardingError as exc:
        check("query payroll refused", exc.code == "payroll_refused", exc.code)
    try:
        base.guard_query(candidate="1")
        check("query candidate refused", False)
    except base.HiringOnboardingError as exc:
        check("query candidate refused", exc.code == "current_refused", exc.code)
    try:
        base.guard_query(staff_blast="1")
        check("query staff blast refused", False)
    except base.HiringOnboardingError as exc:
        check("query staff blast refused", exc.code == "staff_blast_refused", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    fixture = td / "ledger.json"
    for state, label in (
        ("SPECIFIED", "specified fixture"),
        ("BUILT", "built fixture"),
        ("PROVEN", "proven fixture reports proven"),
        ("READY", "ready fixture reports ready"),
        ("GREEN", "green fixture unknown"),
    ):
        fixture.write_text(json.dumps({"CAP-HR-02": [state]}), encoding="utf-8")
        flags = base.honesty_flags(fixture)
        if state in {"SPECIFIED", "BUILT", "PROVEN", "READY"}:
            check(f"{label} maturity", flags["maturity"] == state)
        else:
            check(f"{label} maturity", flags["maturity"] == "UNKNOWN")
        check(f"{label} ceiling", flags["maturity_ceiling"] == "BUILT")
        check(f"{label} not invented", flags["invented_proven"] is False and flags["invented_ready"] is False)
        check(f"{label} not written", flags["ledger_write"] is False and flags["model_c_write"] is False)
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
        and live["hr_hire_machinery"] is False
        and live["hire"] is None
        and live["candidate"] is None
        and live["offer"] is None
        and live["onboarding"] is None
        and live["guest_blast"] is False
        and live["staff_blast"] is False
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
    check("module does not import pms orchestration", "amg_pms_orchestration" not in joined)
    check("module does not import sla incident", "amg_sla_incident" not in joined)
    check("module does not import bom yield", "bzg_bom_yield" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not call cloudflare", "api.cloudflare.com" not in src)
    check("module does not json.dump(", "json.dump(" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not update completion", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("module does not insert evidence", "INSERT INTO" not in src and "CREATE TABLE" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/hr/hiring-onboarding" in serve)
    check("page route registered", "/hr-hiring-onboarding" in serve)
    check("payment route refused", "/api/hr/hiring-onboarding/payment" in serve)
    check("bank route refused", "/api/hr/hiring-onboarding/bank" in serve)
    check("books route refused", "/api/hr/hiring-onboarding/zayen" in serve)
    check("payroll route refused", "/api/hr/hiring-onboarding/payroll" in serve)
    check("hr master route refused", "/api/hr/hiring-onboarding/hr-master" in serve)
    check("guest blast route refused", "/api/hr/hiring-onboarding/guest-blast" in serve)
    check("staff blast route refused", "/api/hr/hiring-onboarding/staff-blast" in serve)
    check("public post route refused", "/api/hr/hiring-onboarding/public-post" in serve)
    check("cloudflare route refused", "/api/hr/hiring-onboarding/cloudflare" in serve)
    check("access route refused", "/api/hr/hiring-onboarding/access" in serve)
    check("prove route refused", "/api/hr/hiring-onboarding/prove" in serve)
    check("ready route refused", "/api/hr/hiring-onboarding/ready" in serve)
    check("resolve route refused", "/api/hr/hiring-onboarding/resolve" in serve)
    check("score route refused", "/api/hr/hiring-onboarding/score" in serve)
    check("alchemist route refused", "/api/hr/hiring-onboarding/alchemist" in serve)
    check("fill route refused", "/api/hr/hiring-onboarding/fill" in serve)
    check("pms route still present", "/api/amg/pms-orchestration" in serve)
    check("sla incident route still present", "/api/amg/sla-incident" in serve)
    check("bom yield route still present", "/api/bzg/bom-yield" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "hr-hiring-onboarding.html").read_text(encoding="utf-8")
    check("page says not workflow", "not a live hiring/onboarding workflow" in page and "not READY" in page)
    check("page says not machinery", "not proof of HR hire machinery" in page)
    check("page stays specified", "CAP-HR-02 stays SPECIFIED" in page)
    check("page ceiling built", "ceiling label is BUILT" in page)
    check("page does not resolve", "does not resolve" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page no hr master", "does not write the HR people master" in page)
    check("page no payroll", "does not execute payroll" in page)
    check("page no guest blast", "does not guest blast" in page)
    check("page no staff blast", "does not staff blast" in page)
    check("page no public post", "does not public post" in page)
    check(
        "page no invented metrics",
        "does not invent hire numbers" in page
        and "does not invent candidate numbers" in page
        and "does not invent offer numbers" in page
        and "does not invent onboarding numbers" in page,
    )
    check("page no money", "does not move money" in page)
    check("page bound", "beta-hr-safe" in page)
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

        st, _anon = call("GET", "/api/hr/hiring-onboarding", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/hr/hiring-onboarding", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/hr/hiring-onboarding", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check(
                "owner not hiring workflow",
                owner.get("empty_is_hiring_onboarding") is False
                and owner.get("empty_is_hr_hire_machinery") is False
                and owner.get("proved") is False
                and owner.get("empty_is_ready") is False
                and owner.get("live_hiring_onboarding") is False
                and owner.get("live_hiring") is False
                and owner.get("hr_hire_machinery") is False,
            )
            check(
                "owner metrics null",
                owner.get("requisition") is None
                and owner.get("candidate") is None
                and owner.get("hire") is None
                and owner.get("offer") is None
                and owner.get("onboarding") is None
                and owner.get("checklist") is None
                and owner.get("current") is False
                and owner.get("invented_hire") is False
                and owner.get("invented_candidate") is False
                and owner.get("invented_offer") is False
                and owner.get("invented_onboarding") is False
                and owner.get("guest_blast") is False
                and owner.get("staff_blast") is False
                and owner.get("public_post") is False
                and owner.get("hr_master_write") is False
                and owner.get("payroll_executed") is False,
            )
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
            check("owner bound", owner.get("bound") == "beta-hr-safe")
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
                and flags.get("hire") is None
                and flags.get("candidate") is None
                and flags.get("offer") is None
                and flags.get("onboarding") is None,
            )
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("hire") is None
                    and row.get("candidate") is None
                    and row.get("offer") is None
                    and row.get("hr_hire_machinery") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/hr/hiring-onboarding/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/hr/hiring-onboarding/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/hr/hiring-onboarding/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200
            and isinstance(kinds, dict)
            and kinds.get("empty_is_hiring_onboarding") is False
            and kinds.get("empty_is_hr_hire_machinery") is False,
            str(st),
        )
        slot_paths = (
            ("/api/hr/hiring-onboarding/requisition", "requisition", "requisition slot 200"),
            ("/api/hr/hiring-onboarding/candidate", "candidate", "candidate slot 200"),
            ("/api/hr/hiring-onboarding/offer", "offer", "offer slot 200"),
            ("/api/hr/hiring-onboarding/onboarding", "onboarding", "onboarding slot 200"),
            ("/api/hr/hiring-onboarding/checklist", "checklist", "checklist slot 200"),
            ("/api/hr/hiring-onboarding/notes", "notes", "notes slot 200"),
        )
        for path, kind, label in slot_paths:
            st, slot = call("GET", path, MATT)
            check(
                label,
                st == 200
                and isinstance(slot, dict)
                and (slot.get("kind") or {}).get("kind") == kind
                and slot.get("proved") is False
                and slot.get("hire") is None
                and slot.get("candidate") is None
                and slot.get("offer") is None
                and slot.get("guest_blast") is False
                and slot.get("staff_blast") is False
                and slot.get("public_post") is False,
                str(slot)[:180],
            )
        st, missing = call("GET", "/api/hr/hiring-onboarding/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/hr-hiring-onboarding", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not a live hiring/onboarding workflow" in page
            and b"not proof of HR hire machinery" in page
            and b"stays SPECIFIED" in page
            and b"does not invent hire numbers" in page
            and b"does not invent candidate numbers" in page
            and b"does not invent offer numbers" in page
            and b"does not invent onboarding numbers" in page
            and b"does not resolve" in page
            and b"does not write the HR people master" in page
            and b"does not execute payroll" in page
            and b"does not guest blast" in page
            and b"does not staff blast" in page
            and b"does not public post" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/hr-hiring-onboarding", None)
        check("anon page 403", st == 403, str(st))
        posts = (
            ("/api/hr/hiring-onboarding/payment", {"payment": 100}, "payment_refused", "payment POST 405"),
            ("/api/hr/hiring-onboarding/bank", {}, "bank_refused", "bank POST 405"),
            ("/api/hr/hiring-onboarding/zayen", {}, "books_refused", "zayen POST 405"),
            ("/api/hr/hiring-onboarding/books", {}, "books_refused", "books POST 405"),
            ("/api/hr/hiring-onboarding/payroll", {}, "payroll_refused", "payroll POST 405"),
            ("/api/hr/hiring-onboarding/hr-master", {}, "hr_master_refused", "hr master POST 405"),
            ("/api/hr/hiring-onboarding/guest-blast", {}, "guest_blast_refused", "guest blast POST 405"),
            ("/api/hr/hiring-onboarding/staff-blast", {}, "staff_blast_refused", "staff blast POST 405"),
            ("/api/hr/hiring-onboarding/public-post", {}, "public_post_refused", "public post POST 405"),
            ("/api/hr/hiring-onboarding/requisition", {"requisition": "x"}, "current_refused", "requisition POST 405"),
            ("/api/hr/hiring-onboarding/candidate", {"candidate": "x"}, "current_refused", "candidate POST 405"),
            ("/api/hr/hiring-onboarding/offer", {"offer": "y"}, "current_refused", "offer POST 405"),
            ("/api/hr/hiring-onboarding/onboarding", {"onboarding": "z"}, "current_refused", "onboarding POST 405"),
            ("/api/hr/hiring-onboarding/checklist", {"checklist": "z"}, "current_refused", "checklist POST 405"),
            ("/api/hr/hiring-onboarding/current", {}, "current_refused", "current POST 405"),
            ("/api/hr/hiring-onboarding/cloudflare", {}, "cloudflare_refused", "cloudflare POST 405"),
            ("/api/hr/hiring-onboarding/access", {}, "access_refused", "access POST 405"),
            ("/api/hr/hiring-onboarding/prove", {}, "proven_refused", "prove POST 405"),
            ("/api/hr/hiring-onboarding/ready", {}, "ready_refused", "ready POST 405"),
            ("/api/hr/hiring-onboarding/resolve", {}, "resolve_refused", "resolve POST 405"),
            ("/api/hr/hiring-onboarding/production", {}, "production_refused", "production POST 405"),
            ("/api/hr/hiring-onboarding/score", {}, "score_refused", "score POST 405"),
            ("/api/hr/hiring-onboarding/alchemist", {}, "alchemist_refused", "alchemist POST 405"),
            ("/api/hr/hiring-onboarding/fill", {}, "slots_refused", "fill POST 405"),
            ("/api/hr/hiring-onboarding/note", {"kind": "notes", "status": "NOTED"}, "slots_refused", "note POST 405"),
            ("/api/hr/hiring-onboarding/notes", {}, "slots_refused", "notes POST 405"),
        )
        for path, body, code, label in posts:
            st, payload = call("POST", path, MATT, body)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, bare = call("POST", "/api/hr/hiring-onboarding", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/hr/hiring-onboarding", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/hr/hiring-onboarding", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/hr/hiring-onboarding/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        queries = (
            ("?payment=1", "payment_refused", "query payment http refused"),
            ("?payroll=1", "payroll_refused", "query payroll http refused"),
            ("?hr_master=1", "hr_master_refused", "query hr master http refused"),
            ("?guest_blast=1", "guest_blast_refused", "query guest blast http refused"),
            ("?staff_blast=1", "staff_blast_refused", "query staff blast http refused"),
            ("?public_post=1", "public_post_refused", "query public post http refused"),
            ("?requisition=1", "current_refused", "query requisition http refused"),
            ("?candidate=1", "current_refused", "query candidate http refused"),
            ("?offer=1", "current_refused", "query offer http refused"),
            ("?onboarding=1", "current_refused", "query onboarding http refused"),
            ("?hire=1", "current_refused", "query hire http refused"),
            ("?cloudflare=1", "cloudflare_refused", "query cloudflare http refused"),
            ("?score=1", "score_refused", "query score http refused"),
            ("?alchemist=1", "alchemist_refused", "query alchemist http refused"),
        )
        for suffix, code, label in queries:
            st, payload = call("GET", "/api/hr/hiring-onboarding" + suffix, MATT)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, again = call("GET", "/api/hr/hiring-onboarding", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("live_hiring_onboarding") is False
            and again.get("hr_hire_machinery") is False
            and again.get("hire") is None
            and again.get("candidate") is None
            and again.get("offer") is None
            and again.get("onboarding") is None
            and again.get("guest_blast") is False
            and again.get("staff_blast") is False
            and again.get("public_post") is False
            and again.get("hr_master_write") is False
            and again.get("payroll_executed") is False
            and again.get("payment") is None
            and again.get("current") is False,
            str(again)[:240],
        )
        flags = (again.get("honesty") or {}) if isinstance(again, dict) else {}
        check("owner still specified", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
        check("http left no live file", not base.DEFAULT_DB.exists())
        st, pms = call("GET", "/api/amg/pms-orchestration", MATT)
        check(
            "pms lane still owner readable",
            st == 200 and isinstance(pms, dict) and pms.get("cap") == "CAP-AMG-01",
            str(pms)[:180] if isinstance(pms, dict) else str(st),
        )
        st, sla = call("GET", "/api/amg/sla-incident", MATT)
        check(
            "sla incident lane still owner readable",
            st == 200 and isinstance(sla, dict) and sla.get("cap") == "CAP-AMG-06",
            str(sla)[:180] if isinstance(sla, dict) else str(st),
        )
        st, bom = call("GET", "/api/bzg/bom-yield", MATT)
        check(
            "bom yield lane still owner readable",
            st == 200 and isinstance(bom, dict) and bom.get("cap") == "CAP-BZG-06",
            str(bom)[:180] if isinstance(bom, dict) else str(st),
        )
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="hr-hiring-onboarding-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    pms_before = hashlib.sha256(PMS_MODULE.read_bytes()).hexdigest()
    sla_before = hashlib.sha256(SLA_MODULE.read_bytes()).hexdigest()
    bom_before = hashlib.sha256(BOM_MODULE.read_bytes()).hexdigest()
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
        "pms module unchanged",
        hashlib.sha256(PMS_MODULE.read_bytes()).hexdigest() == pms_before,
    )
    check(
        "sla incident module unchanged",
        hashlib.sha256(SLA_MODULE.read_bytes()).hexdigest() == sla_before,
    )
    check(
        "bom yield module unchanged",
        hashlib.sha256(BOM_MODULE.read_bytes()).hexdigest() == bom_before,
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
