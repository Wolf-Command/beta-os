#!/usr/bin/env python3
"""Sprint2 P1 BZG Loop Closure V2 — Uma Blu continuous loop on Beta."""
from __future__ import annotations

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
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import audit  # noqa: E402
from core import evidence  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import venue_close  # noqa: E402
from core import work_items  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-215a379980f228e8"
MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
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


def patch(path: Path) -> None:
    ops.CATALOG_DB = path
    evidence.CATALOG_DB = path
    audit.CATALOG_DB = path
    venue_close.CATALOG_DB = path
    work_items.CATALOG_DB = path


def _cr(catalog: Path = LIVE_DB) -> str | None:
    conn = sqlite3.connect(str(catalog))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty_and_schema() -> None:
    flags = ops.honesty_flags()
    check("loop bound", flags.get("loop_bound") == "beta-bzg-loop-safe")
    check("bound present", flags.get("bound") == "beta-bzg-loop-safe")
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("empty stock honesty", flags.get("empty_stock_is_not_live_inventory") is True)
    check("esb write false", flags.get("esb_write") is False and flags.get("esb_mutated") is False)
    check("payment not executed", flags.get("payment_executed") is False)
    schema = ops.schema_document()
    check(
        "14 loop stages",
        schema["loop_stages"] == list(ops.LOOP_STAGES) and len(schema["loop_stages"]) == 14,
    )
    check("loop schema id", schema["schema_id"] == "wolf.bzg-loop-closure.v2")
    check("schema empty stock", schema["empty_stock_is_not_live_inventory"] is True)
    for fn, code in (
        (ops.refuse_proven, "proven_refused"),
        (ops.refuse_ready, "ready_refused"),
        (ops.refuse_money, "money_refused"),
        (ops.refuse_payment_exec, "payment_execution_refused"),
        (ops.refuse_esb_write, "esb_write_refused"),
        (ops.refuse_production, "production_refused"),
        (ops.refuse_cloudflare, "cloudflare_refused"),
        (ops.refuse_secret_exfil, "secret_exfil_refused"),
        (ops.refuse_resolve, "resolve_refused"),
        (ops.refuse_zayen, "zayen_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except ops.UmaOpsError as exc:
            check(f"{code}", exc.code == code, exc.code)


def test_loop_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    shutil.copy2(LIVE_DB, db)
    patch(db)
    conn = ops.db_connect(db)
    try:
        desk = ops.loop_desk(person_id="PERS-DEVI", conn=conn)
        check("desk ok", desk.get("ok") is True and desk.get("bound") == "beta-bzg-loop-safe")
        check("14 stages on desk", len(desk.get("stages") or []) == 14)
        check(
            "stock honesty on desk",
            desk.get("empty_stock_is_not_live_inventory") is True
            and desk.get("on_hand") is None
            and desk.get("live_perpetual_inventory") is False
            and desk.get("esb_mutated") is False
            and desk.get("payment_execution") is False,
        )
        check(
            "ordering empty-or-object",
            isinstance(desk.get("ordering_state"), dict)
            and desk["ordering_state"].get("bound") == "beta-bzg-loop-safe",
        )
        check(
            "stock consequence empty honesty",
            desk["stock_consequence"]["empty_is_not_live_inventory"] is True
            and desk["stock_consequence"]["on_hand_status"] == "EMPTY"
            and desk["stock_consequence"]["esb_mutated"] is False,
        )
        check(
            "bill consequence present",
            isinstance(desk.get("supplier_bill_consequence"), dict)
            and desk["supplier_bill_consequence"].get("payment_execution") is False,
        )
        check(
            "exception strip present",
            isinstance(desk.get("exception"), dict) and desk["exception"].get("invented") is False,
        )
        check(
            "handover strip present",
            isinstance(desk.get("handover"), dict) and desk["handover"].get("bound") == "beta-bzg-loop-safe",
        )
        check(
            "manager visibility present",
            isinstance(desk.get("manager_visibility"), dict)
            and desk["manager_visibility"].get("invented_sla") is False,
        )
        check(
            "owner exception present",
            isinstance(desk.get("owner_exception"), dict)
            and desk["owner_exception"].get("money") is None
            and desk["owner_exception"].get("live_inventory") is False,
        )

        pr = ops.create_pr(
            supplier_name="Loop market",
            purpose="Greens for loop closure",
            lines=[{"item": "Kangkung", "qty": 4, "unit": "bunch"}],
            submitted=True,
            verified_person_id="PERS-DEVI",
            actor_type="PERSON",
            conn=conn,
        )
        check("pr requested", pr["state"] == "REQUESTED", pr["state"])
        approved = p0.ops_advance(
            person_id="PERS-DEVI",
            pr_id=pr["pr_id"],
            to_state="APPROVED",
            conn=conn,
        )
        check("approved", approved["state"] == "APPROVED", approved["state"])
        ordering = ops.ordering_state(conn=conn)
        check(
            "ordering sees approved",
            any(r.get("pr_id") == pr["pr_id"] for r in ordering.get("awaiting_order") or []),
            str(ordering)[:200],
        )
        ordered = p0.ops_advance(
            person_id="PERS-DEVI",
            pr_id=pr["pr_id"],
            to_state="ORDERED",
            conn=conn,
        )
        check("ordered", ordered["state"] == "ORDERED")
        ordering2 = ops.ordering_state(conn=conn)
        check(
            "ordering sees ordered",
            any(r.get("pr_id") == pr["pr_id"] for r in ordering2.get("ordered_not_received") or []),
        )

        detail = p0.pr_detail(pr["pr_id"], conn=conn)
        lines = detail.get("lines") or []
        check("interpretable lines", bool(lines) and lines[0].get("interpretable") is True, str(lines)[:160])
        sid = str(lines[0]["source_line_id"])
        qty = float(lines[0]["qty"])
        partial_qty = max(qty / 2.0, 0.5)
        partial = p0.receive_goods(
            person_id="PERS-DEVI",
            pr_key=pr["pr_id"],
            lines=[{"source_line_id": sid, "received_qty": partial_qty}],
            notes="Loop partial receive",
            evidence_note_id="EVD-LOOP-NOTE-1",
            require_evidence=True,
            conn=conn,
        )
        check(
            "partial receive",
            partial.get("status") == "PARTIAL" and partial.get("variance_flag") is True,
            str(partial.get("status")),
        )
        mid = ops.get_pr(pr["pr_id"], conn=conn)
        check("state partially received", mid and mid["state"] == "PARTIALLY_RECEIVED", str(mid and mid["state"]))

        part_state = ops.partial_receiving_state(conn=conn)
        check(
            "partial stage lists pr",
            any(r.get("pr_id") == pr["pr_id"] for r in part_state.get("rows") or []),
        )
        stock = ops.stock_consequence(conn=conn)
        check(
            "stock consequence after partial",
            stock.get("empty_is_not_live_inventory") is True
            and stock.get("live_perpetual_inventory") is False
            and stock.get("esb_mutated") is False
            and (
                any(r.get("pr_id") == pr["pr_id"] for r in stock.get("partial_links") or [])
                or not stock.get("empty")
            ),
            str(stock)[:220],
        )
        bill = ops.supplier_bill_consequence(conn=conn)
        check(
            "bill consequence after partial",
            any(r.get("pr_id") == pr["pr_id"] for r in bill.get("rows") or [])
            and bill.get("payment_execution") is False,
            str(bill)[:200],
        )

        hand = ops.record_loop_note(
            person_id="PERS-DEVI",
            kind="handover",
            note="Shift note: finish kangkung remainder before lunch.",
            source_id=pr["pr_id"],
            conn=conn,
        )
        check("handover note", hand.get("ok") is True and hand.get("kind") == "handover")
        exc_note = ops.record_loop_note(
            person_id="PERS-DEVI",
            kind="exception",
            note="Short delivery on greens — remainder chasing.",
            source_id=pr["pr_id"],
            conn=conn,
        )
        check("exception note", exc_note.get("kind") == "exception")
        mgr = ops.record_loop_note(
            person_id="PERS-DEVI",
            kind="manager",
            note="Manager: watch partial receive before close.",
            source_id=pr["pr_id"],
            conn=conn,
        )
        check("manager note", mgr.get("kind") == "manager")
        owner = ops.record_loop_note(
            person_id="PERS-DEVI",
            kind="owner",
            note="Owner look: short delivery on loop fixture.",
            source_id=pr["pr_id"],
            conn=conn,
        )
        check("owner note", owner.get("kind") == "owner")

        hand_strip = ops.handover_strip(conn=conn)
        check("handover strip has note", hand_strip.get("empty") is False and hand_strip.get("count") >= 1)
        exc_strip = ops.exception_strip(conn=conn)
        check("exception strip has note", any(
            r.get("note_id") == exc_note.get("note_id") for r in (exc_strip.get("exceptions") or [])
        ) or exc_strip.get("count") >= 1)
        mgr_strip = ops.manager_visibility(conn=conn)
        check(
            "manager strip active",
            mgr_strip.get("empty") is False and mgr_strip.get("invented_sla") is False,
        )
        owner_strip = ops.owner_exception_strip(conn=conn)
        check(
            "owner strip active",
            owner_strip.get("empty") is False
            and owner_strip.get("money") is None
            and owner_strip.get("live_inventory") is False,
        )

        today = ops.today_cards(person_id="PERS-DEVI", conn=conn)
        check(
            "today carries loop",
            isinstance(today.get("loop"), dict)
            and today.get("loop_bound") == "beta-bzg-loop-safe"
            and isinstance(today.get("ordering_state"), dict)
            and isinstance(today.get("stock_consequence"), dict)
            and today["stock_consequence"].get("empty_is_not_live_inventory") is True
            and isinstance(today.get("owner_exception"), dict),
            str((today.get("loop") or {}).get("bound")),
        )

        try:
            p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="PAYMENT_APPROVED",
                conn=conn,
            )
            check("payment exec refused on advance", False)
        except ops.UmaOpsError as exc:
            check(
                "payment exec refused on advance",
                exc.code == "payment_execution_refused",
                exc.code,
            )

        check("cr still open on copy", _cr(db) == "OPEN")
    finally:
        conn.close()
        patch(LIVE_DB)


def test_sources() -> None:
    src = (SCRIPTS / "core" / "uma_ops_console.py").read_text(encoding="utf-8")
    check("loop bound in console", "beta-bzg-loop-safe" in src)
    check("loop notes table", "bzg_ops_loop_notes" in src)
    check("ordering_state fn", "def ordering_state" in src)
    check("stock_consequence fn", "def stock_consequence" in src)
    check("bill consequence fn", "def supplier_bill_consequence" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src or "write_commissioning" in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "/api/bzg/uma-blu/loop",
        "/api/bzg/uma-blu/ordering-state",
        "/api/bzg/uma-blu/stock-consequence",
        "/api/bzg/uma-blu/bill-consequence",
        "/api/bzg/uma-blu/handover",
        "/api/bzg/uma-blu/manager-visibility",
        "/api/bzg/uma-blu/owner-exception",
        "/api/bzg/uma-blu/loop-note",
        "_uma_ops_loop",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    check("page loop bound", "beta-bzg-loop-safe" in page)
    check("page stock consequence", "Stock consequence" in page)
    check("page bill consequence", "bill consequence" in page.lower() or "Supplier / bill" in page)
    check("page manager", "Manager visibility" in page)
    check("page owner", "Owner exception" in page)
    check("page empty stock honesty", "not live inventory" in page.lower())
    for rel in WIP:
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    check("cap-bzg-03 ready unchanged", ledger.get("CAP-BZG-03", [None])[0] == "READY")
    check("cap-bzg-01 built unchanged", ledger.get("CAP-BZG-01", [None])[0] == "BUILT")
    check("live cr open", _cr() == "OPEN")


def test_api() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(
            f"http://127.0.0.1:{port}{url_path}",
            headers=headers,
            method=method,
            data=data,
        )
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        for path, label in (
            ("/api/bzg/uma-blu/loop", "loop"),
            ("/api/bzg/uma-blu/ordering-state", "ordering"),
            ("/api/bzg/uma-blu/stock-consequence", "stock"),
            ("/api/bzg/uma-blu/bill-consequence", "bill"),
            ("/api/bzg/uma-blu/exceptions", "exceptions"),
            ("/api/bzg/uma-blu/handover", "handover"),
            ("/api/bzg/uma-blu/manager-visibility", "manager"),
            ("/api/bzg/uma-blu/owner-exception", "owner"),
            ("/api/bzg/uma-blu/today", "today"),
            ("/bzg/uma-blu", "page"),
        ):
            st, _ = call("GET", path, None)
            check(f"anon {label} 403", st == 403, str(st))

        st, loop = call("GET", "/api/bzg/uma-blu/loop", MATT)
        check(
            "owner loop 200",
            st == 200
            and isinstance(loop, dict)
            and loop.get("ok") is True
            and loop.get("bound") == "beta-bzg-loop-safe"
            and loop.get("empty_stock_is_not_live_inventory") is True
            and loop.get("payment_execution") is False
            and loop.get("esb_mutated") is False,
            str(loop)[:240] if isinstance(loop, dict) else str(st),
        )
        st, ord_v = call("GET", "/api/bzg/uma-blu/ordering-state", MATT)
        check(
            "owner ordering 200",
            st == 200 and isinstance(ord_v, dict) and ord_v.get("bound") == "beta-bzg-loop-safe",
        )
        st, stock = call("GET", "/api/bzg/uma-blu/stock-consequence", DEVI)
        check(
            "devi stock 200",
            st == 200
            and isinstance(stock, dict)
            and stock.get("empty_is_not_live_inventory") is True
            and stock.get("on_hand_status") == "EMPTY",
            str(stock)[:200] if isinstance(stock, dict) else str(st),
        )
        st, owner_v = call("GET", "/api/bzg/uma-blu/owner-exception", MATT)
        check(
            "owner exception view",
            st == 200
            and isinstance(owner_v, dict)
            and owner_v.get("money") is None
            and owner_v.get("live_inventory") is False,
        )
        st, today = call("GET", "/api/bzg/uma-blu/today", DEVI)
        check(
            "devi today has loop",
            st == 200
            and isinstance(today, dict)
            and isinstance(today.get("loop"), dict)
            and today.get("loop_bound") == "beta-bzg-loop-safe",
            str(st),
        )

        st, note = call(
            "POST",
            "/api/bzg/uma-blu/loop-note",
            DEVI,
            {"kind": "handover", "note": "   "},
        )
        check(
            "devi blank handover note 400",
            st == 400
            and isinstance(note, dict)
            and (note.get("code") == "missing_note" or "note" in str(note.get("error") or "").lower()),
            str(note)[:200] if isinstance(note, dict) else str(st),
        )
        st, _anon_note = call(
            "POST",
            "/api/bzg/uma-blu/loop-note",
            None,
            {"kind": "handover", "note": "anon must fail"},
        )
        check("anon loop-note 403", st == 403, str(st))
        st, page_ok = call("GET", "/bzg/uma-blu", MATT)
        check(
            "owner page 200",
            st == 200 and (isinstance(page_ok, (bytes, bytearray)) or isinstance(page_ok, str) or page_ok is not None),
            str(st),
        )

        for method, path in (
            ("POST", "/api/bzg/uma-blu/payment"),
            ("POST", "/api/bzg/uma-blu/money"),
            ("POST", "/api/bzg/uma-blu/esb"),
            ("POST", "/api/bzg/uma-blu/esb-write"),
            ("POST", "/api/bzg/uma-blu/proven"),
            ("POST", "/api/bzg/uma-blu/ready"),
            ("POST", "/api/bzg/uma-blu/production"),
            ("POST", "/api/bzg/uma-blu/cloudflare"),
            ("POST", "/api/bzg/uma-blu/access"),
            ("POST", "/api/bzg/uma-blu/secret"),
            ("POST", "/api/bzg/uma-blu/zayen"),
            ("POST", "/api/bzg/uma-blu/resolve"),
            ("GET", "/api/bzg/uma-blu/proven"),
            ("GET", "/api/bzg/uma-blu/esb-write"),
        ):
            code, body = call(method, path, MATT, {} if method != "GET" else None)
            check(
                f"{method} {path} refused",
                code in (403, 405) and isinstance(body, dict),
                f"{code} {str(body)[:120]}",
            )

        st, _out = call("GET", "/api/bzg/uma-blu/loop", OUTSIDER)
        check("outsider loop 403", st == 403, str(st))
    finally:
        httpd.shutdown()

    ledger = _ledger()
    check("ledger untouched after api", ledger.get("CAP-BZG-03", [None])[0] == "READY" and len(ledger) == 77)
    check("cr untouched after api", _cr() == "OPEN")


def main() -> int:
    test_honesty_and_schema()
    with tempfile.TemporaryDirectory(prefix="bzg-loop-", dir=str(ROOT / "state")) as raw:
        test_loop_on_copy(Path(raw))
    test_sources()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
