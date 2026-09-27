#!/usr/bin/env python3
"""Sprint2 P1 BZG Operator Depth — PR detail/action + goods-receipt on Uma loop."""
from __future__ import annotations

import hashlib
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
CR_PR = "CR-080362c384f2bf36"
CR_RECV = "CR-b979d19a6ce4b9ce"
CR_CLOSE_AU = "CR-215a379980f228e8"
MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": None,
    "scripts/phase26_team.py": None,
    "scripts/skills/__init__.py": None,
    "scripts/wolf_intelligence.py": None,
}


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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cr(item_id: str, catalog: Path = LIVE_DB) -> str | None:
    conn = sqlite3.connect(str(catalog))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty() -> None:
    flags = ops.honesty_flags()
    check("bound", flags.get("bound") == "beta-bzg-loop-safe")
    check("operator depth schema", flags.get("operator_depth_schema_id") == ops.OPERATOR_DEPTH_SCHEMA_ID)
    check("no live Devi commission flag", flags.get("live_devi_commission") is False)
    check("empty stock honesty", flags.get("empty_stock_is_not_live_inventory") is True)
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    for fn, code in (
        (ops.refuse_proven, "proven_refused"),
        (ops.refuse_ready, "ready_refused"),
        (ops.refuse_money, "money_refused"),
        (ops.refuse_payment_exec, "payment_execution_refused"),
        (ops.refuse_esb_write, "esb_write_refused"),
        (ops.refuse_production, "production_refused"),
        (ops.refuse_cloudflare, "cloudflare_refused"),
        (ops.refuse_secret_exfil, "secret_exfil_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except ops.UmaOpsError as exc:
            check(f"{code}", exc.code == code, exc.code)


def test_operator_depth_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    shutil.copy2(LIVE_DB, db)
    patch(db)
    conn = ops.db_connect(db)
    try:
        grant = ops.ensure_operator_depth_rbac(conn=conn, commit=True)
        check("rbac grant ok", grant.get("ok") is True and "venue.receive" in (grant.get("grants") or []))
        prove = ops.prove_fb_ops_lead_operator(person_id="PERS-DEVI", conn=conn)
        check(
            "devi fixture receive+operator",
            prove.get("can_receive") is True
            and prove.get("can_pr_operator") is True
            and prove.get("assignment_active") is True
            and prove.get("live_devi_commission") is False
            and prove.get("actions", {}).get("payment_execution") is False,
            str(prove)[:240],
        )

        pr = ops.create_pr(
            supplier_name="Depth market",
            purpose="Greens for operator depth",
            lines=[{"item": "Bayam", "qty": 6, "unit": "bunch"}],
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
        check("approved", approved["state"] == "APPROVED")
        ordered = p0.ops_advance(
            person_id="PERS-DEVI",
            pr_id=pr["pr_id"],
            to_state="ORDERED",
            conn=conn,
        )
        check("ordered", ordered["state"] == "ORDERED")

        detail = ops.operator_pr_detail(pr["pr_id"], person_id="PERS-DEVI", conn=conn)
        check(
            "operator pr detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-bzg-loop-safe"
            and bool(detail.get("actions", {}).get("receive"))
            and bool(detail.get("actions", {}).get("pr_operator"))
            and detail.get("payment_execution") is False
            and "/bzg/uma-blu/bills/" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )
        note = ops.record_pr_operator_action(
            person_id="PERS-DEVI",
            pr_key=pr["pr_id"],
            kind="correction",
            note="Stem quality note — keep chilled.",
            conn=conn,
        )
        check(
            "pr operator correction",
            note.get("ok") is True and note.get("kind") == "correction" and note.get("payment_execution") is False,
        )

        lines = (detail.get("pr") or {}).get("lines") or []
        check("interpretable lines", bool(lines) and lines[0].get("interpretable") is True)
        sid = str(lines[0]["source_line_id"])
        qty = float(lines[0]["qty"])
        partial_qty = max(qty / 2.0, 0.5)
        receipt = ops.goods_receipt(
            person_id="PERS-DEVI",
            pr_key=pr["pr_id"],
            lines=[{"source_line_id": sid, "received_qty": partial_qty}],
            notes="Depth partial receive",
            evidence_note_id="EVD-DEPTH-1",
            require_evidence=True,
            conn=conn,
        )
        check(
            "goods receipt partial",
            receipt.get("ok") is True
            and (receipt.get("receipt") or {}).get("status") == "PARTIAL"
            and receipt.get("empty_stock_is_not_live_inventory") is True
            and receipt.get("live_perpetual_inventory") is False
            and receipt.get("esb_mutated") is False
            and receipt.get("payment_execution") is False,
            str(receipt.get("receipt", {}).get("status")),
        )
        stock = receipt.get("stock_consequence") or {}
        bill = receipt.get("supplier_bill_consequence") or {}
        check(
            "stock consequence refreshed",
            stock.get("empty_is_not_live_inventory") is True
            and (
                any(r.get("pr_id") == pr["pr_id"] for r in stock.get("partial_links") or [])
                or not stock.get("empty")
            ),
            str(stock)[:200],
        )
        check(
            "bill consequence refreshed",
            any(r.get("pr_id") == pr["pr_id"] for r in bill.get("rows") or [])
            and bill.get("payment_execution") is False,
            str(bill)[:200],
        )

        today = ops.today_cards(person_id="PERS-DEVI", conn=conn)
        rem = next((c for c in (today.get("cards") or []) if c.get("kind") == "awaiting_remainder"), None)
        check("today remainder card", rem is not None, "missing awaiting_remainder")
        if rem:
            href = ((rem.get("action") or {}).get("href") or rem.get("href") or "")
            check(
                "today deep-link to pr",
                pr["pr_id"] in href or any(pr["pr_id"] in str(it.get("href") or "") for it in (rem.get("items") or [])),
                href,
            )

        desk = ops.operator_depth_desk(person_id="PERS-DEVI", conn=conn)
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-bzg-loop-safe"
            and desk.get("live_devi_commission") is False
            and desk.get("rbac", {}).get("can_receive") is True,
        )

        try:
            ops.goods_receipt(
                person_id="PERS-NOBODY",
                pr_key=pr["pr_id"],
                lines=[{"source_line_id": sid, "received_qty": 0.1}],
                evidence_note_id="EVD-X",
                conn=conn,
            )
            check("outsider receive refused", False)
        except ops.UmaOpsError as exc:
            check("outsider receive refused", exc.code in ("forbidden", "missing_verified_person") or exc.http_status == 403, exc.code)

        check("cr pr still open on copy", _cr(CR_PR, db) == "OPEN")
        check("cr recv still open on copy", _cr(CR_RECV, db) == "OPEN")
        check("au close cr open on copy", _cr(CR_CLOSE_AU, db) == "OPEN")
    finally:
        conn.close()
        patch(LIVE_DB)


def test_sources() -> None:
    src = (SCRIPTS / "core" / "uma_ops_console.py").read_text(encoding="utf-8")
    check("operator depth schema in console", ops.OPERATOR_DEPTH_SCHEMA_ID in src)
    check("goods_receipt fn", "def goods_receipt" in src)
    check("operator_pr_detail fn", "def operator_pr_detail" in src)
    check("record_pr_operator_action fn", "def record_pr_operator_action" in src)
    check("ensure rbac fn", "def ensure_operator_depth_rbac" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "/api/bzg/uma-blu/operator-depth",
        "/api/bzg/uma-blu/goods-receipt",
        "operator-action",
        "_uma_ops_goods_receipt_post",
        "_uma_ops_pr_operator_detail",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    check("page operator depth", "Operator depth" in page)
    check("page goods path honesty", "not live inventory" in page.lower())
    pr_page = (ROOT / "dashboards" / "bzg-uma-blu-pr.html").read_text(encoding="utf-8")
    check("pr page goods-receipt", "/api/bzg/uma-blu/goods-receipt" in pr_page)
    check("pr page operator-action", "operator-action" in pr_page)
    before = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in before.items():
        WIP[rel] = digest
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    check("cap-bzg-01 built", ledger.get("CAP-BZG-01", [None])[0] == "BUILT")
    check("cap-bzg-03 ready", ledger.get("CAP-BZG-03", [None])[0] == "READY")
    for cap in ("CAP-BZG-02", "CAP-BZG-04", "CAP-BZG-05", "CAP-BZG-06", "CAP-BZG-07"):
        check(f"{cap} specified", ledger.get(cap, [None])[0] == "SPECIFIED")
    check("live cr pr open", _cr(CR_PR) == "OPEN")
    check("live cr recv open", _cr(CR_RECV) == "OPEN")
    check("live au cr open", _cr(CR_CLOSE_AU) == "OPEN")
    check("denominator 77", len(ledger) == 77)


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
            ("/api/bzg/uma-blu/operator-depth", "depth"),
            ("/api/bzg/uma-blu/operator-depth/rbac", "rbac"),
            ("/api/bzg/uma-blu/goods-receipt", "goods"),
            ("/api/bzg/uma-blu/today", "today"),
            ("/bzg/uma-blu", "page"),
        ):
            st, _ = call("GET" if path != "/api/bzg/uma-blu/goods-receipt" else "POST", path, None, {} if "goods" in path else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/bzg/uma-blu/operator-depth", DEVI)
        check(
            "devi operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == "beta-bzg-loop-safe"
            and depth.get("live_devi_commission") is False
            and (depth.get("rbac") or {}).get("can_receive") is True,
            str(depth)[:240] if isinstance(depth, dict) else str(st),
        )
        st, rbac = call("GET", "/api/bzg/uma-blu/operator-depth/rbac", DEVI)
        check(
            "devi rbac prove",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_receive") is True
            and rbac.get("can_pr_operator") is True
            and rbac.get("live_devi_commission") is False,
            str(rbac)[:200] if isinstance(rbac, dict) else str(st),
        )
        st, blank = call(
            "POST",
            "/api/bzg/uma-blu/goods-receipt",
            DEVI,
            {"pr": "", "lines": []},
        )
        check(
            "devi goods-receipt validates",
            st in (400, 403, 404) and isinstance(blank, dict),
            f"{st} {str(blank)[:120]}",
        )
        st, _anon_act = call(
            "POST",
            "/api/bzg/uma-blu/prs/PR-FAKE/operator-action",
            None,
            {"kind": "note", "note": "anon"},
        )
        check("anon operator-action 403", st == 403, str(st))
        st, _out = call("GET", "/api/bzg/uma-blu/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))

        for method, path in (
            ("POST", "/api/bzg/uma-blu/payment"),
            ("POST", "/api/bzg/uma-blu/money"),
            ("POST", "/api/bzg/uma-blu/esb-write"),
            ("POST", "/api/bzg/uma-blu/proven"),
            ("POST", "/api/bzg/uma-blu/ready"),
        ):
            code, body = call(method, path, MATT, {})
            check(
                f"{method} {path} refused",
                code in (403, 405) and isinstance(body, dict),
                f"{code} {str(body)[:100]}",
            )
    finally:
        httpd.shutdown()

    after = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, before_digest in WIP.items():
        check(f"wip untouched {Path(rel).name}", after.get(rel) == before_digest)
    ledger = _ledger()
    check(
        "caps unchanged after api",
        ledger.get("CAP-BZG-01", [None])[0] == "BUILT"
        and ledger.get("CAP-BZG-03", [None])[0] == "READY"
        and ledger.get("CAP-BZG-02", [None])[0] == "SPECIFIED"
        and len(ledger) == 77,
    )
    check("crs still open after api", _cr(CR_PR) == "OPEN" and _cr(CR_RECV) == "OPEN")


def main() -> int:
    test_honesty()
    with tempfile.TemporaryDirectory(prefix="bzg-depth-", dir=str(ROOT / "state")) as raw:
        test_operator_depth_on_copy(Path(raw))
    test_sources()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
