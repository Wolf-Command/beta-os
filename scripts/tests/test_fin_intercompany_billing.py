#!/usr/bin/env python3
"""CAP-FIN-06 Intercompany Billing framework. Empty is not live billing."""
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
os.environ.pop("WOLF_ALLOW_LIVE_FIN_INTERCOMPANY_BILLING", None)

from core import fin_intercompany_billing as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "fin_intercompany_billing.py"
MGMT_MODULE = SCRIPTS / "core" / "fin_mgmt_reporting.py"
GGV_MODULE = SCRIPTS / "core" / "ggv_intercompany_client.py"
RET_MODULE = SCRIPTS / "core" / "hr_retention_signals.py"
CR_ID = "CR-48e86edd40f5c009"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["invoice", "allocation", "arms_length", "ar_ap", "checklist", "notes"]
NEXT_ACTION = "Implementation"


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
        and row["invoice"] is None
        and row["allocation"] is None
        and row["arms_length"] is None
        and row["ar_ap"] is None
        and row["checklist"] is None
        and row["tax_treatment"] is None
        and row["tax_claimed"] is False
        and row["current"] is False
        and row["live_billing"] is False
        and row["billing_machinery"] is False
        and row["ggv_client_mode_proven"] is False
        and row["guest_blast"] is False
        and row["staff_blast"] is False
        and row["public_post"] is False
        and row["payment"] is None
        and row["payment_executed"] is False
    )


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not billing",
        report["empty_is_billing"] is False
        and report["empty_is_billing_machinery"] is False
        and report["proved"] is False
        and report["empty_is_ready"] is False
        and report["live_billing"] is False
        and report["billing_machinery"] is False
        and report["ggv_client_mode_proven"] is False,
    )
    check(
        "balances unread",
        report["invoice"] is None
        and report["allocation"] is None
        and report["arms_length"] is None
        and report["ar_ap"] is None
        and report["checklist"] is None
        and report["tax_treatment"] is None
        and report["tax_claimed"] is False
        and report["invented_invoice"] is False
        and report["invented_allocation"] is False
        and report["invented_ar_ap"] is False
        and report["invented_tax"] is False,
    )
    check("not current", report["current"] is False)
    check(
        "blast quiet",
        report["guest_blast"] is False
        and report["staff_blast"] is False
        and report["public_post"] is False,
    )
    check(
        "payment not executed",
        report["payment"] is None and report["money"] is None and report["payment_executed"] is False,
    )
    check("bank and books unread", report["bank_write"] is False and report["books_write"] is False and report["zayen_write"] is False)
    check("alchemist unread", report["alchemist_write"] is False)
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("score unchanged", report["score_changed"] is False)
    check("not on disk", report["on_disk"] is False)
    check("bound", report["bound"] == "beta-fin-safe")
    check("paired cap", report["paired_cap"] == "CAP-GGV-06")
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["bank_property"] is False
        and report["schema"]["books_property"] is False
        and report["schema"]["invoice_property"] is False
        and report["schema"]["allocation_property"] is False
        and report["schema"]["ar_ap_property"] is False
        and report["schema"]["checklist_property"] is False
        and report["schema"]["tax_property"] is False
        and report["schema"]["guest_blast_property"] is False
        and report["schema"]["staff_blast_property"] is False
        and report["schema"]["public_post_property"] is False
        and report["schema"]["current_property"] is False
        and report["schema"]["cloudflare_property"] is False
        and report["schema"]["access_property"] is False
        and report["schema"]["proven_property"] is False
        and report["schema"]["ready_property"] is False
        and report["schema"]["ggv_client_mode_proven_property"] is False
        and report["schema"]["kind_enum"] == KINDS,
    )
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check("ledger not written", report["ledger_write"] is False and report["cr_resolved"] is False)
    kinds = report["kinds"]
    check("six kinds", [row["kind"] for row in kinds] == KINDS)
    check("every slot empty", all(_slot_empty(row) for row in kinds))
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-FIN-06" and flags["cr_id"] == CR_ID and flags["bound"] == "beta-fin-safe")
    check("paired honesty", flags["paired_cap"] == "CAP-GGV-06" and flags["ggv_client_mode_proven"] is False)
    check("paired stays specified", flags["paired_maturity"] == "SPECIFIED" and flags["paired_specified"] is True)
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED" and flags["specified"] is True)
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not invented",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["built"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False
        and flags["invented_invoice"] is False
        and flags["invented_allocation"] is False
        and flags["invented_ar_ap"] is False
        and flags["invented_tax"] is False
        and flags["billing_machinery"] is False
        and flags["invoice"] is None
        and flags["allocation"] is None
        and flags["ar_ap"] is None
        and flags["tax_claimed"] is False
        and flags["guest_blast"] is False
        and flags["staff_blast"] is False
        and flags["public_post"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-FIN-06" and flags["cr_capability"] == "CAP-FIN-06")
        check("cr next action", row[3] == NEXT_ACTION and flags["cr_next_action"] == row[3])
    check("gaps name the empty framework", "An empty framework is not live intercompany billing." in report["gaps"])
    check("gaps name not machinery", "An empty framework is not proof of GGV↔AMG/BZG billing machinery." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("gaps stay specified", "CAP-FIN-06 stays SPECIFIED." in report["gaps"])
    check("gaps ceiling built", "The ceiling label is BUILT." in report["gaps"])
    check("gaps no tax", "Tax treatment is not claimed." in report["gaps"])
    check("gaps paired honesty", "CAP-GGV-06 client-mode PROVEN is not claimed." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    invoice = base.read_kind("invoice")
    check(
        "invoice slot read",
        invoice["ok"] is True
        and invoice["kind"]["kind"] == "invoice"
        and invoice["empty"] is True
        and invoice["proved"] is False
        and invoice["live_billing"] is False
        and invoice["billing_machinery"] is False
        and invoice["ggv_client_mode_proven"] is False
        and invoice["invoice"] is None
        and invoice["allocation"] is None
        and invoice["ar_ap"] is None,
    )
    notes = base.read_kind("notes")
    check("notes slot read", notes["ok"] is True and notes["kind"]["kind"] == "notes" and notes["invoice"] is None)
    arms = base.read_kind("arms-length")
    check(
        "arms-length slot read",
        arms["ok"] is True and arms["kind"]["kind"] == "arms_length" and arms["tax_claimed"] is False,
    )
    checklist = base.read_kind("checklist")
    check(
        "checklist slot read",
        checklist["ok"] is True and checklist["kind"]["kind"] == "checklist" and checklist["staff_blast"] is False,
    )
    for bad, label in (("tax", "tax"), ("ready", "ready"), ("service_record", "service_record"), ("proven", "proven")):
        try:
            base.read_kind(bad)
            check(f"{label} is not a slot", False)
        except base.FinIntercompanyBillingError as exc:
            check(f"{label} is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    media_before = _media_count()
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    wolf = td / "wolf-system-copy.sqlite"
    wolf.write_bytes(b"sentinel-wolf")
    wolf_before = wolf.read_bytes()
    try:
        base.refuse_store(wolf)
        check("wolf-system path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    check("wolf-system sentinel unchanged", wolf.read_bytes() == wolf_before)
    bank = td / "bank.sqlite"
    bank.write_bytes(b"sentinel-bank")
    bank_before = bank.read_bytes()
    try:
        base.refuse_store(bank)
        check("bank path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("bank path refused", exc.code == "bank_refused", exc.code)
    check("bank sentinel unchanged", bank.read_bytes() == bank_before)
    pay = td / "payment.sqlite"
    pay.write_bytes(b"sentinel-pay")
    pay_before = pay.read_bytes()
    try:
        base.refuse_store(pay)
        check("payment path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("payment path refused", exc.code == "payment_refused", exc.code)
    check("payment sentinel unchanged", pay.read_bytes() == pay_before)
    books = td / "zayen-books.sqlite"
    books.write_bytes(b"sentinel-books")
    books_before = books.read_bytes()
    try:
        base.refuse_store(books)
        check("books path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("books path refused", exc.code == "books_refused", exc.code)
    check("books sentinel unchanged", books.read_bytes() == books_before)
    guest = td / "guest-blast.sqlite"
    guest.write_bytes(b"sentinel-guest")
    guest_before = guest.read_bytes()
    try:
        base.refuse_store(guest)
        check("guest blast path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("guest blast path refused", exc.code == "guest_blast_refused", exc.code)
    check("guest blast sentinel unchanged", guest.read_bytes() == guest_before)
    staff = td / "staff-blast.sqlite"
    staff.write_bytes(b"sentinel-staff")
    staff_before = staff.read_bytes()
    try:
        base.refuse_store(staff)
        check("staff blast path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("staff blast path refused", exc.code == "staff_blast_refused", exc.code)
    check("staff blast sentinel unchanged", staff.read_bytes() == staff_before)
    public = td / "public-post.sqlite"
    public.write_bytes(b"sentinel-public")
    public_before = public.read_bytes()
    try:
        base.refuse_store(public)
        check("public post path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("public post path refused", exc.code == "public_post_refused", exc.code)
    check("public post sentinel unchanged", public.read_bytes() == public_before)
    invoice = td / "invoice.sqlite"
    invoice.write_bytes(b"sentinel-invoice")
    invoice_before = invoice.read_bytes()
    try:
        base.refuse_store(invoice)
        check("invoice path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("invoice path refused", exc.code == "current_refused", exc.code)
    check("invoice sentinel unchanged", invoice.read_bytes() == invoice_before)
    tax = td / "tax.sqlite"
    tax.write_bytes(b"sentinel-tax")
    tax_before = tax.read_bytes()
    try:
        base.refuse_store(tax)
        check("tax path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("tax path refused", exc.code == "tax_refused", exc.code)
    check("tax sentinel unchanged", tax.read_bytes() == tax_before)
    try:
        base.refuse_store(td / "model-c-baseline-assessments.json")
        check("ledger path refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("ledger path refused", exc.code == "ledger_write_refused", exc.code)
    check("ledger fixture absent", not (td / "model-c-baseline-assessments.json").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.FinIntercompanyBillingError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    refusals = (
        (base.refuse_fill, {"kind": "notes", "status": "NOTED"}, "slots_refused", "fill refused"),
        (base.refuse_payment, {"payment": "1500000"}, "payment_refused", "payment refused"),
        (base.refuse_bank, {}, "bank_refused", "bank refused"),
        (base.refuse_books, {}, "books_refused", "books refused"),
        (base.invent_tax, None, "tax_refused", "tax helper"),
        (base.blast_guests, None, "guest_blast_refused", "guest blast helper"),
        (base.blast_staff, None, "staff_blast_refused", "staff blast helper"),
        (base.post_public, None, "public_post_refused", "public post helper"),
        (base.move_money, None, "payment_refused", "money helper"),
        (base.mark_current, None, "current_refused", "current helper"),
        (base.invent_invoice, None, "current_refused", "invoice helper"),
        (base.invent_allocation, None, "current_refused", "allocation helper"),
        (base.invent_ar_ap, None, "current_refused", "ar_ap helper"),
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
        except base.FinIntercompanyBillingError as exc:
            check(label, exc.code == code, exc.code)
    bodies = (
        ({"payment": 1}, "payment_refused", "body payment refused"),
        ({"bank": "write"}, "bank_refused", "body bank refused"),
        ({"zayen": "write"}, "books_refused", "body books refused"),
        ({"tax": "gst"}, "tax_refused", "body tax refused"),
        ({"guest_blast": 1}, "guest_blast_refused", "body guest blast refused"),
        ({"staff_blast": 1}, "staff_blast_refused", "body staff blast refused"),
        ({"public_post": 1}, "public_post_refused", "body public post refused"),
        ({"invoice": 3}, "current_refused", "body invoice refused"),
        ({"allocation": 1}, "current_refused", "body allocation refused"),
        ({"ar_ap": 1}, "current_refused", "body ar_ap refused"),
        ({"arms_length": 1}, "current_refused", "body arms_length refused"),
        ({"checklist": "z"}, "slots_refused", "body checklist invent refused"),
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
        except base.FinIntercompanyBillingError as exc:
            check(label, exc.code == code, exc.code)
    try:
        base.guard_query(bank="1")
        check("query bank refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("query bank refused", exc.code == "bank_refused", exc.code)
    try:
        base.guard_query(invoice="1")
        check("query invoice refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("query invoice refused", exc.code == "current_refused", exc.code)
    try:
        base.guard_query(staff_blast="1")
        check("query staff blast refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("query staff blast refused", exc.code == "staff_blast_refused", exc.code)
    try:
        base.guard_query(checklist="1")
        check("query checklist refused", False)
    except base.FinIntercompanyBillingError as exc:
        check("query checklist refused", exc.code == "slots_refused", exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    fixture = td / "ledger.json"
    for state, label in (
        ("SPECIFIED", "specified fixture"),
        ("BUILT", "built fixture"),
        ("PROVEN", "proven fixture reports proven"),
        ("READY", "ready fixture reports ready"),
        ("GREEN", "green fixture unknown"),
    ):
        fixture.write_text(
            json.dumps({"CAP-FIN-06": [state], "CAP-GGV-06": ["SPECIFIED"]}),
            encoding="utf-8",
        )
        flags = base.honesty_flags(fixture)
        if state in {"SPECIFIED", "BUILT", "PROVEN", "READY"}:
            check(f"{label} maturity", flags["maturity"] == state)
        else:
            check(f"{label} maturity", flags["maturity"] == "UNKNOWN")
        check(f"{label} ceiling", flags["maturity_ceiling"] == "BUILT")
        check(f"{label} not invented", flags["invented_proven"] is False and flags["invented_ready"] is False)
        check(f"{label} not written", flags["ledger_write"] is False and flags["model_c_write"] is False)
        check(f"{label} paired not proven", flags["ggv_client_mode_proven"] is False)
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
        and live["billing_machinery"] is False
        and live["ggv_client_mode_proven"] is False
        and live["paired_maturity"] == "SPECIFIED"
        and live["invoice"] is None
        and live["allocation"] is None
        and live["ar_ap"] is None
        and live["tax_claimed"] is False
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
    check("module does not import fin mgmt", "fin_mgmt_reporting" not in joined)
    check("module does not import ggv intercompany", "ggv_intercompany_client" not in joined)
    check("module does not import retention signals", "hr_retention_signals" not in joined)
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
    check("route registered", "/api/fin/intercompany-billing" in serve)
    check("page route registered", "/fin-intercompany-billing" in serve)
    check("payment route refused", "/api/fin/intercompany-billing/payment" in serve)
    check("bank route refused", "/api/fin/intercompany-billing/bank" in serve)
    check("books route refused", "/api/fin/intercompany-billing/zayen" in serve)
    check("tax route refused", "/api/fin/intercompany-billing/tax" in serve)
    check("guest blast route refused", "/api/fin/intercompany-billing/guest-blast" in serve)
    check("staff blast route refused", "/api/fin/intercompany-billing/staff-blast" in serve)
    check("public post route refused", "/api/fin/intercompany-billing/public-post" in serve)
    check("cloudflare route refused", "/api/fin/intercompany-billing/cloudflare" in serve)
    check("access route refused", "/api/fin/intercompany-billing/access" in serve)
    check("prove route refused", "/api/fin/intercompany-billing/prove" in serve)
    check("ready route refused", "/api/fin/intercompany-billing/ready" in serve)
    check("resolve route refused", "/api/fin/intercompany-billing/resolve" in serve)
    check("score route refused", "/api/fin/intercompany-billing/score" in serve)
    check("alchemist route refused", "/api/fin/intercompany-billing/alchemist" in serve)
    check("fill route refused", "/api/fin/intercompany-billing/fill" in serve)
    check("mgmt route still present", "/api/fin/mgmt-reporting" in serve)
    check("ggv ic route still present", "/api/ggv/intercompany-client" in serve)
    check("retention route still present", "/api/hr/retention-signals" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "fin-intercompany-billing.html").read_text(encoding="utf-8")
    check("page says not billing", "not live intercompany billing" in page and "not READY" in page)
    check("page says not machinery", "not proof of GGV↔AMG/BZG billing machinery" in page)
    check("page stays specified", "CAP-FIN-06 stays SPECIFIED" in page)
    check("page paired honesty", "does not claim client-mode PROVEN" in page)
    check("page ceiling built", "ceiling label is BUILT" in page)
    check("page does not resolve", "does not resolve" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page no guest blast", "does not guest blast" in page)
    check("page no staff blast", "does not staff blast" in page)
    check("page no public post", "does not public post" in page)
    check("page no tax claim", "does not claim tax treatment" in page)
    check(
        "page no invented balances",
        "does not invent invoices" in page
        and "does not invent allocations" in page
        and "does not invent AR/AP" in page,
    )
    check("page no money", "does not move money" in page)
    check("page bound", "beta-fin-safe" in page)
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

        st, _anon = call("GET", "/api/fin/intercompany-billing", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/fin/intercompany-billing", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/fin/intercompany-billing", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check(
                "owner not billing",
                owner.get("empty_is_billing") is False
                and owner.get("empty_is_billing_machinery") is False
                and owner.get("proved") is False
                and owner.get("empty_is_ready") is False
                and owner.get("live_billing") is False
                and owner.get("billing_machinery") is False
                and owner.get("ggv_client_mode_proven") is False,
            )
            check(
                "owner balances null",
                owner.get("invoice") is None
                and owner.get("allocation") is None
                and owner.get("ar_ap") is None
                and owner.get("arms_length") is None
                and owner.get("checklist") is None
                and owner.get("tax_treatment") is None
                and owner.get("tax_claimed") is False
                and owner.get("current") is False
                and owner.get("invented_invoice") is False
                and owner.get("invented_allocation") is False
                and owner.get("invented_ar_ap") is False
                and owner.get("invented_tax") is False
                and owner.get("guest_blast") is False
                and owner.get("staff_blast") is False
                and owner.get("public_post") is False,
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
            check("owner bound", owner.get("bound") == "beta-fin-safe")
            check("owner paired", owner.get("paired_cap") == "CAP-GGV-06")
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
                and flags.get("ggv_client_mode_proven") is False
                and flags.get("paired_maturity") == "SPECIFIED"
                and flags.get("invoice") is None
                and flags.get("allocation") is None
                and flags.get("ar_ap") is None
                and flags.get("tax_claimed") is False,
            )
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("invoice") is None
                    and row.get("allocation") is None
                    and row.get("ar_ap") is None
                    and row.get("billing_machinery") is False
                    and row.get("ggv_client_mode_proven") is False
                    and row.get("tax_claimed") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/fin/intercompany-billing/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/fin/intercompany-billing/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/fin/intercompany-billing/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200
            and isinstance(kinds, dict)
            and kinds.get("empty_is_billing") is False
            and kinds.get("empty_is_billing_machinery") is False
            and kinds.get("billing_machinery") is False
            and kinds.get("ggv_client_mode_proven") is False,
            str(st),
        )
        slot_paths = (
            ("/api/fin/intercompany-billing/invoice", "invoice", "invoice slot 200"),
            ("/api/fin/intercompany-billing/allocation", "allocation", "allocation slot 200"),
            ("/api/fin/intercompany-billing/arms_length", "arms_length", "arms_length slot 200"),
            ("/api/fin/intercompany-billing/ar_ap", "ar_ap", "ar_ap slot 200"),
            ("/api/fin/intercompany-billing/checklist", "checklist", "checklist slot 200"),
            ("/api/fin/intercompany-billing/notes", "notes", "notes slot 200"),
        )
        for path, kind, label in slot_paths:
            st, slot = call("GET", path, MATT)
            check(
                label,
                st == 200
                and isinstance(slot, dict)
                and (slot.get("kind") or {}).get("kind") == kind
                and slot.get("proved") is False
                and slot.get("invoice") is None
                and slot.get("allocation") is None
                and slot.get("ar_ap") is None
                and slot.get("tax_claimed") is False
                and slot.get("guest_blast") is False
                and slot.get("staff_blast") is False
                and slot.get("public_post") is False
                and slot.get("ggv_client_mode_proven") is False,
                str(slot)[:180],
            )
        st, missing = call("GET", "/api/fin/intercompany-billing/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/fin-intercompany-billing", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not live intercompany billing" in page
            and b"not proof of GGV\xe2\x86\x94AMG/BZG billing machinery" in page
            and b"stays SPECIFIED" in page
            and b"does not invent invoices" in page
            and b"does not invent allocations" in page
            and b"does not invent AR/AP" in page
            and b"does not resolve" in page
            and b"does not guest blast" in page
            and b"does not staff blast" in page
            and b"does not public post" in page
            and b"does not claim client-mode PROVEN" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/fin-intercompany-billing", None)
        check("anon page 403", st == 403, str(st))
        posts = (
            ("/api/fin/intercompany-billing/payment", {"payment": 100}, "payment_refused", "payment POST 405"),
            ("/api/fin/intercompany-billing/bank", {}, "bank_refused", "bank POST 405"),
            ("/api/fin/intercompany-billing/zayen", {}, "books_refused", "zayen POST 405"),
            ("/api/fin/intercompany-billing/books", {}, "books_refused", "books POST 405"),
            ("/api/fin/intercompany-billing/tax", {}, "tax_refused", "tax POST 405"),
            ("/api/fin/intercompany-billing/guest-blast", {}, "guest_blast_refused", "guest blast POST 405"),
            ("/api/fin/intercompany-billing/staff-blast", {}, "staff_blast_refused", "staff blast POST 405"),
            ("/api/fin/intercompany-billing/public-post", {}, "public_post_refused", "public post POST 405"),
            ("/api/fin/intercompany-billing/invoice", {"invoice": 100}, "current_refused", "invoice POST 405"),
            ("/api/fin/intercompany-billing/allocation", {"allocation": 1}, "current_refused", "allocation POST 405"),
            ("/api/fin/intercompany-billing/ar_ap", {"ar_ap": 1}, "current_refused", "ar_ap POST 405"),
            ("/api/fin/intercompany-billing/arms_length", {"arms_length": 1}, "current_refused", "arms_length POST 405"),
            ("/api/fin/intercompany-billing/checklist", {"checklist": "z"}, "slots_refused", "checklist POST 405"),
            ("/api/fin/intercompany-billing/current", {}, "current_refused", "current POST 405"),
            ("/api/fin/intercompany-billing/cloudflare", {}, "cloudflare_refused", "cloudflare POST 405"),
            ("/api/fin/intercompany-billing/access", {}, "access_refused", "access POST 405"),
            ("/api/fin/intercompany-billing/prove", {}, "proven_refused", "prove POST 405"),
            ("/api/fin/intercompany-billing/ready", {}, "ready_refused", "ready POST 405"),
            ("/api/fin/intercompany-billing/resolve", {}, "resolve_refused", "resolve POST 405"),
            ("/api/fin/intercompany-billing/production", {}, "production_refused", "production POST 405"),
            ("/api/fin/intercompany-billing/score", {}, "score_refused", "score POST 405"),
            ("/api/fin/intercompany-billing/alchemist", {}, "alchemist_refused", "alchemist POST 405"),
            ("/api/fin/intercompany-billing/fill", {}, "slots_refused", "fill POST 405"),
            ("/api/fin/intercompany-billing/note", {"kind": "notes", "status": "NOTED"}, "slots_refused", "note POST 405"),
            ("/api/fin/intercompany-billing/notes", {}, "slots_refused", "notes POST 405"),
        )
        for path, body, code, label in posts:
            st, payload = call("POST", path, MATT, body)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, bare = call("POST", "/api/fin/intercompany-billing", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/fin/intercompany-billing", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/fin/intercompany-billing", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/fin/intercompany-billing/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        queries = (
            ("?payment=1", "payment_refused", "query payment http refused"),
            ("?bank=1", "bank_refused", "query bank http refused"),
            ("?tax=1", "tax_refused", "query tax http refused"),
            ("?guest_blast=1", "guest_blast_refused", "query guest blast http refused"),
            ("?staff_blast=1", "staff_blast_refused", "query staff blast http refused"),
            ("?public_post=1", "public_post_refused", "query public post http refused"),
            ("?invoice=1", "current_refused", "query invoice http refused"),
            ("?allocation=1", "current_refused", "query allocation http refused"),
            ("?ar_ap=1", "current_refused", "query ar_ap http refused"),
            ("?cloudflare=1", "cloudflare_refused", "query cloudflare http refused"),
            ("?score=1", "score_refused", "query score http refused"),
            ("?alchemist=1", "alchemist_refused", "query alchemist http refused"),
        )
        for suffix, code, label in queries:
            st, payload = call("GET", "/api/fin/intercompany-billing" + suffix, MATT)
            check(label, st == 405 and isinstance(payload, dict) and payload.get("error") == code, str(payload)[:180])
        st, again = call("GET", "/api/fin/intercompany-billing", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("live_billing") is False
            and again.get("billing_machinery") is False
            and again.get("ggv_client_mode_proven") is False
            and again.get("invoice") is None
            and again.get("allocation") is None
            and again.get("ar_ap") is None
            and again.get("tax_claimed") is False
            and again.get("guest_blast") is False
            and again.get("staff_blast") is False
            and again.get("public_post") is False
            and again.get("payment") is None
            and again.get("current") is False,
            str(again)[:240],
        )
        flags = (again.get("honesty") or {}) if isinstance(again, dict) else {}
        check("owner still specified", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
        check("http left no live file", not base.DEFAULT_DB.exists())
        st, mgmt = call("GET", "/api/fin/mgmt-reporting", MATT)
        check(
            "mgmt lane still owner readable",
            st == 200 and isinstance(mgmt, dict) and mgmt.get("cap") == "CAP-FIN-05",
            str(mgmt)[:180] if isinstance(mgmt, dict) else str(st),
        )
        st, ggv = call("GET", "/api/ggv/intercompany-client", MATT)
        check(
            "ggv ic lane still owner readable",
            st == 200 and isinstance(ggv, dict) and ggv.get("cap") == "CAP-GGV-06",
            str(ggv)[:180] if isinstance(ggv, dict) else str(st),
        )
        st, ret = call("GET", "/api/hr/retention-signals", MATT)
        check(
            "retention lane still owner readable",
            st == 200 and isinstance(ret, dict) and ret.get("cap") == "CAP-HR-05",
            str(ret)[:180] if isinstance(ret, dict) else str(st),
        )
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="fin-intercompany-billing-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    mgmt_before = hashlib.sha256(MGMT_MODULE.read_bytes()).hexdigest()
    ggv_before = hashlib.sha256(GGV_MODULE.read_bytes()).hexdigest()
    ret_before = hashlib.sha256(RET_MODULE.read_bytes()).hexdigest()
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
        "mgmt module unchanged",
        hashlib.sha256(MGMT_MODULE.read_bytes()).hexdigest() == mgmt_before,
    )
    check(
        "ggv ic module unchanged",
        hashlib.sha256(GGV_MODULE.read_bytes()).hexdigest() == ggv_before,
    )
    check(
        "retention module unchanged",
        hashlib.sha256(RET_MODULE.read_bytes()).hexdigest() == ret_before,
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
