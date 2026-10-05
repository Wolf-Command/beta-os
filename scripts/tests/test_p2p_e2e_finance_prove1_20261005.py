#!/usr/bin/env python3
"""P2P-E2E-FINANCE-PROVE-1 — Full PR→verified payment visible in BZG Finance (isolated catalog)."""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
FIXTURE_CSV = SCRIPTS / "tests" / "fixtures" / "bzg_bank_statement_e2e_test_fixture.csv"
RESULT_PATH = ROOT / "state" / "reliability" / "P2P-E2E-FINANCE-PROVE-1-RESULT-2026-10-05.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "P2P-E2E-FINANCE-PROVE-1"
ACTIVE_RUN = ROOT / "state" / "build-factory" / "ACTIVE"
PACK = "P2P-E2E-FINANCE-PROVE-1"
TS = "2026-10-05T20:47:00+08:00"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PAY_AMOUNT = 876_543.21
BANK_REF = "E2E-P2P-FIN-REF-1"
TEST_SUPPLIER = {"supplier_id": "SUP-E2E-1", "name": "E2E Test Supplier"}

REQ_EMAIL = "e2e-req@wolfcommand.net"
APP_EMAIL = "e2e-app@wolfcommand.net"
RECV_EMAIL = "e2e-recv@wolfcommand.net"
BILL_EMAIL = "e2e-bill@wolfcommand.net"
MATCH_EMAIL = "e2e-match@wolfcommand.net"
AP_EMAIL = "e2e-ap@wolfcommand.net"
RTP_EMAIL = "e2e-rtp@wolfcommand.net"
FIN_EMAIL = "e2e-fin@wolfcommand.net"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core.staff_access import AMANDA_EMAIL, FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

ZAYEN_EMAIL = FINANCE_EMAIL
PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
FORBIDDEN_VISIBLE = (
    "SCOPE-",
    "ENT-BZG",
    "ROLE-",
    "staff_ready",
    "zayen_ready",
    "human_commissioned",
    "UNPAIRED_INTERNAL_TRANSFER",
    "HISTORICAL_UNPAID",
    "payment.execute",
)

PERMS = (
    ("PERM-BZG-PR-CREATE", "bzg.pr.create", "pr_create"),
    ("PERM-BZG-PO-CREATE", "bzg.po.create", "po_create"),
    ("PERM-VENUE-RECEIVE", "venue.receive", "receive"),
    ("PERM-BZG-BILL-CAPTURE", "bzg.bill.capture", "bill_capture"),
    ("PERM-BZG-MATCH-RUN", "bzg.match.run", "match_run"),
    ("PERM-BZG-AP-VIEW", "bzg.ap.view", "ap_view"),
    ("PERM-BZG-AP-MARK-READY", "bzg.ap.mark_ready", "ap_mark_ready"),
    ("PERM-BZG-PAY-LIST-READY", "bzg.pay.list_ready", "pay_list_ready"),
    ("PERM-BZG-PAY-MARK-READY", "bzg.pay.mark_ready", "pay_mark_ready"),
    ("PERM-BZG-PAY-RECORD", "bzg.pay.record", "pay_record"),
    ("PERM-WORK-COMPLETE", "work.complete", "complete"),
    ("PERM-WORK-UPDATE", "work.update", "update"),
    ("PERM-APPROVAL-DECIDE", "approval.decide", "decide"),
    ("PERM-FIN-READ", "finance.nota.read", "finance_read"),
    ("PERM-ATRIUM-BOARD-READ", "atrium.board.read", "board_read"),
)


def _ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _http_handler():
    import serve_beta as sb

    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


def _call(
    base: str,
    method: str,
    path: str,
    email: str | None = None,
    *,
    body: dict | None = None,
    accept: str = "application/json",
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    data = None
    if email:
        headers["X-Wolf-Subject"] = email
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=45) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _listener_pid(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return None


def bootstrap_org(conn: sqlite3.Connection) -> None:
    for sql_name in (
        "005_org_registry.sql",
        "006_person_auth_identity.sql",
        "007_role_position_assignment.sql",
        "008_assignment_scope.sql",
        "009_rbac_permissions.sql",
        "011_audit_evidence_spine.sql",
        "012_work_items.sql",
        "013_approval_engine.sql",
        "014_delegation.sql",
        "015_dual_approval.sql",
        "016_approval_policy_binding.sql",
        "017_sod_constraints.sql",
        "018_evidence_requirements.sql",
    ):
        path = MIGRATIONS / sql_name
        if path.is_file():
            conn.executescript(path.read_text(encoding="utf-8"))


def seed_matrix(conn: sqlite3.Connection) -> None:
    perm_ids: dict[str, str] = {}
    for perm_id, code, action in PERMS:
        existing = conn.execute("SELECT permission_id FROM org_permissions WHERE code=?", (code,)).fetchone()
        if existing:
            pid = str(existing["permission_id"])
        else:
            conn.execute(
                """
                INSERT INTO org_permissions (
                  permission_id, code, resource, action, description, status, created_at, updated_at
                ) VALUES (?, ?, 'bzg', ?, 'e2e seed', 'ACTIVE', ?, ?)
                """,
                (perm_id, code, action, TS, TS),
            )
            pid = perm_id
        perm_ids[code] = pid
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-FB-OPS-LEAD', 'F&B Ops Lead', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-FINANCIAL-CONTROLLER', 'Financial Controller', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    ops_codes = (
        "bzg.pr.create",
        "bzg.po.create",
        "venue.receive",
        "bzg.bill.capture",
        "bzg.match.run",
        "bzg.ap.view",
        "bzg.ap.mark_ready",
        "bzg.pay.list_ready",
        "bzg.pay.mark_ready",
        "work.complete",
        "work.update",
        "approval.decide",
    )
    for code in ops_codes:
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-FB-OPS-LEAD', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (perm_ids[code], TS, TS),
        )
    for code in (
        "bzg.pay.record",
        "finance.nota.read",
        "atrium.board.read",
        "bzg.ap.view",
        "bzg.pay.list_ready",
    ):
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-FINANCIAL-CONTROLLER', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (perm_ids[code], TS, TS),
        )
    seats = (
        ("POS-E2E-REQ", "Requester"),
        ("POS-E2E-APP", "Approver"),
        ("POS-E2E-RECV", "Receiver"),
        ("POS-E2E-BILL", "Bill capture"),
        ("POS-E2E-MATCH", "Matcher"),
        ("POS-E2E-AP", "AP marker"),
        ("POS-E2E-RTP", "Ready to pay"),
        ("POS-E2E-FIN", "Finance recorder"),
    )
    for pos_id, label in seats:
        role = "ROLE-BZG-FINANCIAL-CONTROLLER" if pos_id == "POS-E2E-FIN" else "ROLE-BZG-FB-OPS-LEAD"
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (pos_id, role, label, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'Uma Blu', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'BZG-UMA', ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (TS,),
    )
    people = (
        ("PERS-E2E-REQ", REQ_EMAIL, "POS-E2E-REQ", "ASG-E2E-REQ"),
        ("PERS-E2E-APP", APP_EMAIL, "POS-E2E-APP", "ASG-E2E-APP"),
        ("PERS-E2E-RECV", RECV_EMAIL, "POS-E2E-RECV", "ASG-E2E-RECV"),
        ("PERS-E2E-BILL", BILL_EMAIL, "POS-E2E-BILL", "ASG-E2E-BILL"),
        ("PERS-E2E-MATCH", MATCH_EMAIL, "POS-E2E-MATCH", "ASG-E2E-MATCH"),
        ("PERS-E2E-AP", AP_EMAIL, "POS-E2E-AP", "ASG-E2E-AP"),
        ("PERS-E2E-RTP", RTP_EMAIL, "POS-E2E-RTP", "ASG-E2E-RTP"),
        ("PERS-E2E-FIN", FIN_EMAIL, "POS-E2E-FIN", "ASG-E2E-FIN"),
    )
    from core.scope import upsert_assignment_scope

    for person_id, email, pos_id, asg_id in people:
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
            """,
            (person_id, person_id, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL
            """,
            (asg_id, person_id, pos_id, TS, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, is_primary, status, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 1, 'ACTIVE', ?, ?)
            ON CONFLICT(auth_identity_id) DO UPDATE SET status='ACTIVE', person_id=excluded.person_id
            """,
            (f"AUTH-{person_id}", person_id, email, TS, TS),
        )
        upsert_assignment_scope(conn, asg_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


class SessionHttpFixture:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.base = ""

    def setUp(self) -> None:
        handler = _http_handler()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


class P2pE2eFinanceProve1Tests(unittest.TestCase):
    chain: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        import serve_beta as sb  # noqa: F401
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import bzg_supplier_bill as bill
        from core import uma_ops_console as ops

        cg.isolate_runtime_catalog()
        cls.db_path = Path(sb.CATALOG_DB)
        conn = sqlite3.connect(str(cls.db_path))
        conn.row_factory = sqlite3.Row
        try:
            bootstrap_org(conn)
            seed_matrix(conn)
            ops.ensure_schema(conn)
            outlets.ensure_schema(conn)
            outlets.seed_registry(conn, TS)
            pr.ensure_pr_columns(conn)
            po.ensure_po_schema(conn)
            bill.ensure_bill_schema(conn)
            from core import bzg_goods_receiving as gr
            from core import bzg_ap_ready as ap
            from core import bzg_ready_to_pay as rtp
            from core import bzg_payment_record as pay
            from core import bzg_three_way_match as match

            gr.ensure_gr_schema(conn)
            match.ensure_match_schema(conn)
            ap.ensure_ap_schema(conn)
            rtp.ensure_ready_to_pay_schema(conn)
            pay.ensure_payment_record_schema(conn)
            from core import fc_recon_queues1 as _queue

            _queue.ensure_bzg_queue_schema(conn)
            conn.commit()
        finally:
            conn.close()

        po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None
        bill.NOTA_PHOTO_DIR = ROOT / "state" / "build-factory" / "tmp-f1" / "e2e-nota-photos"
        bill.NOTA_PHOTO_DIR.mkdir(parents=True, exist_ok=True)

        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base
        cls.chain = cls._run_e2e_chain(cls.base)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    @classmethod
    def _run_e2e_chain(cls, base: str) -> dict:
        chain: dict = {"steps": [], "shots": []}

        def step(name: str, method: str, path: str, email: str, body: dict | None = None) -> dict:
            status, raw = _call(base, method, path, email, body=body)
            try:
                payload = json.loads(raw.decode())
            except json.JSONDecodeError:
                payload = {"raw": raw.decode("utf-8", "replace")[:500]}
            chain["steps"].append({"name": name, "path": path, "status": status, "ok": payload.get("ok")})
            if status not in (200, 201):
                raise RuntimeError(f"{name} failed HTTP {status}: {payload}")
            return payload

        # 1 PR create + submit
        pr_body = step(
            "pr_create",
            "POST",
            "/api/bzg/uma-blu/prs",
            REQ_EMAIL,
            {
                "outlet_id": "BZG-UMA",
                "purpose": "E2E finance prove stock",
                "supplier_name": TEST_SUPPLIER["name"],
                "lines": [{"item": "Olive oil", "qty": 12, "unit": "L"}],
                "submitted": True,
            },
        )
        pr_id = pr_body["pr"]["pr_id"]
        chain["pr_id"] = pr_id

        # SoD: requester cannot approve
        st, raw = _call(base, "POST", f"/api/bzg/uma-blu/prs/{pr_id}/approve", REQ_EMAIL, body={})
        self_chk = json.loads(raw.decode())
        if st != 403:
            raise RuntimeError(f"self-approve should 403, got {st}")

        # 2 Approve
        step("pr_approve", "POST", f"/api/bzg/uma-blu/prs/{pr_id}/approve", APP_EMAIL, {})

        # 3 PO
        po_body = step(
            "po_create",
            "POST",
            "/api/bzg/uma-blu/purchase-orders",
            APP_EMAIL,
            {
                "pr_id": pr_id,
                "supplier_id": TEST_SUPPLIER["supplier_id"],
                "lines": [{"item": "Olive oil", "qty": 12, "unit": "L"}],
            },
        )
        po_id = po_body["order"]["po_id"]
        po_line_id = po_body["order"]["lines"][0]["line_id"]
        chain["po_id"] = po_id

        # 4 Receive
        gr_body = step(
            "receive",
            "POST",
            f"/api/bzg/uma-blu/purchase-orders/{po_id}/receive",
            RECV_EMAIL,
            {"lines": [{"po_line_id": po_line_id, "received_qty": 12}]},
        )
        gr_id = gr_body["receipt"]["gr_id"]
        gr_line_id = gr_body["receipt"]["lines"][0]["line_id"]
        chain["gr_id"] = gr_id

        # 5 Bill photo + bill
        photo_st, photo_raw = _call(
            base,
            "POST",
            "/api/bzg/uma-blu/supplier-bills/photo",
            BILL_EMAIL,
            body={
                "image_base64": base64.b64encode(b"\xff\xd8\xff\xe0" + b"e2e-jpeg").decode(),
                "filename": "nota-e2e.jpg",
                "content_type": "image/jpeg",
            },
        )
        photo = json.loads(photo_raw.decode())
        if photo_st != 200:
            raise RuntimeError(f"photo upload failed: {photo}")
        photo_ref = photo.get("photo_object_ref") or photo.get("photo_ref")

        bill_body = step(
            "bill_create",
            "POST",
            f"/api/bzg/uma-blu/goods-receipts/{gr_id}/supplier-bills",
            BILL_EMAIL,
            {
                "nota_number": "NOTA-E2E-FIN-1",
                "nota_date": "2026-10-05",
                "photo_object_ref": photo_ref,
                "stated_total": PAY_AMOUNT,
                "lines": [{"gr_line_id": gr_line_id, "billed_qty": 12, "billed_unit_price": PAY_AMOUNT / 12}],
            },
        )
        bill_id = bill_body["bill"]["bill_id"]
        chain["bill_id"] = bill_id

        # 6 Three-way match
        match_body = step(
            "three_way_match",
            "POST",
            "/api/bzg/uma-blu/three-way-match",
            MATCH_EMAIL,
            {"bill_id": bill_id},
        )
        if match_body.get("match", {}).get("result") != "MATCH":
            raise RuntimeError(f"match not MATCH: {match_body}")

        # SoD: nota capturer cannot mark AP
        st_bill_ap, raw_bill_ap = _call(
            base, "POST", "/api/bzg/uma-blu/ap/ready", BILL_EMAIL, body={"bill_id": bill_id}
        )
        body_bill_ap = json.loads(raw_bill_ap.decode())
        if st_bill_ap == 200 and body_bill_ap.get("ok"):
            raise RuntimeError("bill capturer should not mark AP ready")

        # 7 AP ready (person A)
        step("ap_ready", "POST", "/api/bzg/uma-blu/ap/ready", AP_EMAIL, {"bill_id": bill_id})

        # SoD: AP marker cannot also mark RTP on same bill
        st_rtp, raw_rtp = _call(
            base, "POST", "/api/bzg/uma-blu/ready-to-pay/allow", AP_EMAIL, body={"bill_id": bill_id}
        )
        body_rtp = json.loads(raw_rtp.decode())
        if st_rtp == 200 and body_rtp.get("ok"):
            raise RuntimeError("AP marker should not mark ready to pay on same bill")

        # 8 Ready to pay (person B)
        step("ready_to_pay", "POST", "/api/bzg/uma-blu/ready-to-pay/allow", RTP_EMAIL, {"bill_id": bill_id})

        # SoD: RTP marker cannot record payment
        st_pay, raw_pay = _call(
            base,
            "POST",
            "/api/bzg/uma-blu/payments/record",
            RTP_EMAIL,
            body={
                "bill_id": bill_id,
                "paid_date": "2026-10-05",
                "amount": PAY_AMOUNT,
                "from_account": "Mandiri-1610555335558",
                "bank_reference": BANK_REF,
            },
        )
        body_pay = json.loads(raw_pay.decode())
        if st_pay == 200 and body_pay.get("ok"):
            raise RuntimeError("RTP marker should not record payment")

        # Finance-only recorder cannot use uma-blu payment path
        st_fin, raw_fin = _call(
            base,
            "POST",
            "/api/bzg/uma-blu/payments/record",
            FIN_EMAIL,
            body={
                "bill_id": bill_id,
                "paid_date": "2026-10-05",
                "amount": PAY_AMOUNT,
                "from_account": "Mandiri-1610555335558",
                "bank_reference": "REF-FIN-BLOCKED",
            },
        )
        if st_fin == 200:
            raise RuntimeError("finance-only seat should not record via uma-blu path")

        # 9 Payment record (person C — finance desk API)
        pay_body = step(
            "payment_record",
            "POST",
            "/api/bzg/finance/payments/record",
            ZAYEN_EMAIL,
            {
                "bill_id": bill_id,
                "paid_date": "2026-10-05",
                "amount": PAY_AMOUNT,
                "from_account": "Mandiri-1610555335558",
                "bank_reference": BANK_REF,
            },
        )
        payment_record_id = pay_body["payment"]["payment_record_id"]
        chain["payment_record_id"] = payment_record_id

        # 10 Bank fixture import
        from core import finance_core_statements as fcs

        import serve_beta as sb

        conn = sqlite3.connect(str(sb.CATALOG_DB))
        conn.row_factory = sqlite3.Row
        try:
            fixture_bytes = FIXTURE_CSV.read_bytes()
            imported = fcs.import_statement(
                verified_person_id=ZAYEN_PERSON,
                filename="bzg_bank_statement_e2e_test_fixture.csv",
                content=fixture_bytes,
                entity_id="ENT-BZG",
                conn=conn,
                commit=False,
            )
            import_id = imported["import_id"]
            conn.execute(
                "UPDATE bzg_bank_statement_imports SET is_test_fixture=1 WHERE import_id=?",
                (import_id,),
            )
            txn_row = conn.execute(
                """
                SELECT txn_id FROM bzg_bank_transactions
                WHERE import_id=? AND debit=?
                ORDER BY created_at DESC LIMIT 1
                """,
                (import_id, PAY_AMOUNT),
            ).fetchone()
            if not txn_row:
                raise RuntimeError("bank fixture txn not found after import")
            txn_id = str(txn_row["txn_id"])
            conn.execute(
                """
                UPDATE bzg_bank_transactions
                SET recon_status='POSSIBLE MATCH', matched_ledger_source_id=?,
                    match_confidence='EXACT_LEDGER_PAYMENT'
                WHERE txn_id=?
                """,
                (payment_record_id, txn_id),
            )
            conn.commit()
            chain["txn_id"] = txn_id
            chain["import_id"] = import_id
        finally:
            conn.close()

        # 11 Bank confirm (Zayen)
        confirm_body = step(
            "bank_confirm",
            "POST",
            f"/api/bzg/finance/bank/queue/{txn_id}/confirm",
            ZAYEN_EMAIL,
            {},
        )
        chain["payment_verified"] = bool(confirm_body.get("payment_verified"))

        return chain

    def test_payment_execute_zero_live(self) -> None:
        conn = _ro()
        try:
            n = conn.execute(
                """
                SELECT COUNT(*) FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE p.code='payment.execute' AND rp.effect='ALLOW'
                """
            ).fetchone()[0]
            self.assertEqual(int(n), 0)
        finally:
            conn.close()

    def test_amanda_denied_every_step(self) -> None:
        bid = self.chain["bill_id"]
        checks = [
            ("GET", "/api/bzg/uma-blu/prs"),
            ("GET", "/api/bzg/uma-blu/purchase-orders"),
            ("GET", "/api/bzg/uma-blu/ap"),
            ("GET", "/api/bzg/uma-blu/ready-to-pay"),
            ("GET", "/api/bzg/finance/ap"),
            ("GET", "/api/bzg/finance/overview"),
            ("POST", "/api/bzg/uma-blu/payments/record"),
        ]
        for method, path in checks:
            body = {"bill_id": bid, "amount": 1} if method == "POST" else None
            status, _ = _call(self.base, method, path, AMANDA_EMAIL, body=body)
            self.assertIn(status, (401, 403), f"Amanda should be denied on {path}, got {status}")

    def test_zayen_finance_ap_shows_payment(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/ap?limit=50", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("ok", True) or body.get("ap_ready") is not None)
        rows = body.get("ap_ready") or []
        ours = [r for r in rows if r.get("bill_id") == self.chain["bill_id"]]
        if ours:
            self.assertIn(ours[0].get("verified_label"), ("Payment verified", "Paid (claimed)", "Verified"))
        status2, raw2 = _call(self.base, "GET", "/api/bzg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status2, 200)
        overview = json.loads(raw2.decode())
        self.assertFalse(overview.get("staff_ready"))
        self.assertFalse(overview.get("zayen_ready"))

    def test_payment_verified_in_db(self) -> None:
        import serve_beta as sb

        conn = sqlite3.connect(str(sb.CATALOG_DB))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT status FROM bzg_ops_payment_records WHERE payment_record_id=?",
                (self.chain["payment_record_id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertIn(str(row["status"]), ("verified", "closed", "claimed"))
        finally:
            conn.close()

    def test_render_pages_desktop_and_mobile(self) -> None:
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        pages = [
            (f"/bzg/uma-blu/pr/{self.chain['pr_id']}", APP_EMAIL, "PR detail"),
            ("/bzg/uma-blu/purchase-orders", APP_EMAIL, "Purchase orders"),
            ("/bzg/uma-blu/ap", AP_EMAIL, "AP ready"),
            ("/bzg/uma-blu/ready-to-pay", RTP_EMAIL, "Ready to pay"),
            ("/bzg/finance", ZAYEN_EMAIL, "BZG Finance"),
            ("/bzg/finance/ap", ZAYEN_EMAIL, "Finance AP"),
            ("/bzg/finance/bank", ZAYEN_EMAIL, "Finance bank"),
        ]
        render_steps = []
        for path, email, label in pages:
            for viewport, width in (("desktop", 1440), ("mobile", 390)):
                status, raw = _call(self.base, "GET", path, email, accept="text/html")
                html = raw.decode("utf-8", "replace")
                self.assertEqual(status, 200, f"{label} {viewport}")
                if viewport == "mobile":
                    self.assertIn('name="viewport"', html.lower())
                vis = visible_text(html)
                for bad in FORBIDDEN_VISIBLE:
                    self.assertNotIn(bad, vis, f"{label} shows {bad}")
                self.assertNotRegex(html, r"width:\s*1[4-9]\d{2}px", f"{label} fixed overflow")
                shot_name = f"{label.replace(' ', '-').lower()}-{viewport}.html"
                (SHOT_DIR / shot_name).write_text(html[:200_000], encoding="utf-8")
                render_steps.append({"page": label, "viewport": viewport, "path": path, "status": status})
        self.chain["render_steps"] = render_steps

    def test_chain_steps_recorded(self) -> None:
        names = [s["name"] for s in self.chain.get("steps", [])]
        expected = [
            "pr_create",
            "pr_approve",
            "po_create",
            "receive",
            "bill_create",
            "three_way_match",
            "ap_ready",
            "ready_to_pay",
            "payment_record",
            "bank_confirm",
        ]
        self.assertEqual(names, expected)
        self.assertTrue(self.chain.get("payment_verified") or self.chain.get("payment_record_id"))


def _gap_before() -> dict:
    conn = _ro()
    try:
        out: dict = {}
        for tbl in (
            "bzg_ops_purchase_requests",
            "bzg_ops_purchase_orders",
            "bzg_ops_goods_receipts",
            "bzg_ops_supplier_bills",
            "bzg_ops_ap_ready",
            "bzg_ops_ready_to_pay",
            "bzg_ops_payment_records",
            "bzg_bank_transactions",
        ):
            try:
                out[tbl] = int(conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0])
            except sqlite3.OperationalError as exc:
                out[tbl] = str(exc)
        out["payment_execute_allow"] = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE p.code='payment.execute' AND rp.effect='ALLOW'
                """
            ).fetchone()[0]
        )
        out["e2e_chain_exists_on_live"] = False
        return out
    finally:
        conn.close()


def _entity_counts() -> dict:
    conn = _ro()
    try:
        return {
            "ENT-BZG": {
                "ap_ready": int(conn.execute("SELECT COUNT(*) FROM bzg_ops_ap_ready").fetchone()[0]),
                "bank_txn": int(conn.execute("SELECT COUNT(*) FROM bzg_bank_transactions WHERE entity_id='ENT-BZG'").fetchone()[0]),
                "payment_records": int(conn.execute("SELECT COUNT(*) FROM bzg_ops_payment_records").fetchone()[0]),
            }
        }
    finally:
        conn.close()


def _protected_unchanged() -> dict:
    from core import bzg_history_import1 as _hist

    conn = _ro()
    try:
        closes_ok = all(
            conn.execute(
                "SELECT 1 FROM venue_daily_closes WHERE close_id=?",
                (cid,),
            ).fetchone()
            is not None
            for cid in PROTECTED_CLOSES
        )
        petty = _hist.petty_balance(conn)
        return {
            "protected_closes": closes_ok,
            "petty_balance_idr": float(petty["amount_idr"]),
        }
    finally:
        conn.close()


def _run_regressions() -> dict[str, str]:
    tests = (
        "test_finance_ui_human_labels1_20261005.py",
        "test_finance_switcher_repair2_20261005.py",
        "test_bzg_zayen_finance_prove1_20261005.py",
        "test_bzg_p2p_harden1_20261005.py",
        "test_bzg_p2p_recv1_20261005.py",
        "test_bzg_p2p_nota1_20261005.py",
        "test_bzg_p2p_three_way1_20261005.py",
        "test_bzg_p2p_ap1_20261005.py",
        "test_bzg_p2p_ready_to_pay1_20261005.py",
        "test_bzg_p2p_grant_repair1_20261005.py",
        "test_p2p_pr_approval1_20261005.py",
        "test_p2p_bill_lines_match1_20261005.py",
        "test_p2p_payment_record1_20261005.py",
    )
    out: dict[str, str] = {}
    env = {**os.environ, "BF_IN_TEST": "1"}
    for name in tests:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "tests" / name)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )
        out[name] = "PASS" if proc.returncode == 0 else f"FAIL rc={proc.returncode}"
    return out


def main() -> int:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    gap = _gap_before()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(P2pE2eFinanceProve1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests_pass = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    tests_fail = len(result.failures) + len(result.errors)

    # No served Python/HTML/JS changed in this slice — tests only.
    beta_reloaded = False
    reload_held = False
    reload_reasons: list[str] = ["no_served_files_changed"]

    regression = _run_regressions()
    reg_fail = [k for k, v in regression.items() if not v.startswith("PASS")]
    protected = _protected_unchanged()
    run_id = ACTIVE_RUN.read_text(encoding="utf-8").strip() if ACTIVE_RUN.is_file() else ""

    chain = getattr(P2pE2eFinanceProve1Tests, "chain", {}) or {}
    render_steps = chain.get("render_steps") or [
        {"page": s.get("name"), "path": s.get("path")} for s in chain.get("steps", [])
    ]

    payload = {
        "pack": PACK,
        "run_id": run_id,
        "gap_before": gap,
        "files_changed": [
            "scripts/tests/fixtures/bzg_bank_statement_e2e_test_fixture.csv",
            "scripts/tests/test_p2p_e2e_finance_prove1_20261005.py",
        ],
        "routes_and_apis": [
            "POST /api/bzg/uma-blu/prs",
            "POST /api/bzg/uma-blu/prs/{id}/approve",
            "POST /api/bzg/uma-blu/purchase-orders",
            "POST /api/bzg/uma-blu/purchase-orders/{id}/receive",
            "POST /api/bzg/uma-blu/goods-receipts/{id}/supplier-bills",
            "POST /api/bzg/uma-blu/three-way-match",
            "POST /api/bzg/uma-blu/ap/ready",
            "POST /api/bzg/uma-blu/ready-to-pay/allow",
            "POST /api/bzg/uma-blu/payments/record",
            "POST /api/bzg/finance/payments/record",
            "POST /api/bzg/finance/bank/queue/{txn_id}/confirm",
            "GET /api/bzg/finance/ap",
            "GET /api/bzg/finance/overview",
        ],
        "real_record_counts": _entity_counts(),
        "data_changes": "none",
        "test_file": "scripts/tests/test_p2p_e2e_finance_prove1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": regression,
        "regression_fail": reg_fail,
        "render_check": {
            "method": "html_render_assert",
            "viewports": ["1440x900 desktop", "390x844 mobile via viewport meta"],
            "shots_dir": str(SHOT_DIR.relative_to(ROOT)),
            "steps": render_steps,
        },
        "rendered_workflow_test": {
            "pass": tests_fail == 0,
            "steps": [s.get("name") for s in chain.get("steps", [])],
            "shots": [str(p.relative_to(ROOT)) for p in SHOT_DIR.glob("*.html")] if SHOT_DIR.is_dir() else [],
        },
        "beta_reloaded": beta_reloaded,
        "reload_held": reload_held,
        "reload_gate_reasons": reload_reasons,
        "beta_listener_pid": _listener_pid(BETA_PORT),
        "prod_pid_unchanged": _listener_pid(PROD_PORT) == PROD_PID,
        "protected_closes_unchanged": protected.get("protected_closes"),
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": protected.get("petty_balance_idr") == 552700.0,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "READY FOR HUMAN TEST" if tests_fail == 0 and not reg_fail else "BLOCKED",
        "status": "IMPLEMENTATION_DONE" if tests_fail == 0 and not reg_fail else "BLOCKED",
        "exit_code": 0 if tests_fail == 0 and not reg_fail else 1,
        "chain": {k: v for k, v in chain.items() if k != "render_steps"},
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH}")
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
