#!/usr/bin/env python3
"""P2P-PAYMENT-RECORD-1 — Record outside-Wolf payments; bank verify closes (temp sqlite + harness)."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
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
DASHBOARD = ROOT / "dashboards" / "bzg-finance.html"
PACK = "P2P-PAYMENT-RECORD-1"
TS = "2026-10-05T20:30:00+08:00"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
PROTECTED_IDS = (
    PROTECTED_CLOSE,
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
TEST_SUPPLIER = {"supplier_id": "SUP-TEST-1", "name": "Test Supplier Co"}
PERM_PO = "PERM-BZG-PO-CREATE"
PERM_PR = "PERM-BZG-PR-CREATE"
PERM_RECV = "PERM-VENUE-RECEIVE"
PERM_BILL = "PERM-BZG-BILL-CAPTURE"
PERM_MATCH = "PERM-BZG-MATCH-RUN"
PERM_AP_MARK = "PERM-BZG-AP-MARK-READY"
PERM_PAY_MARK = "PERM-BZG-PAY-MARK-READY"
PERM_PAY_LIST = "PERM-BZG-PAY-LIST-READY"
PERM_PAY_RECORD = "PERM-BZG-PAY-RECORD"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
FINANCE_TEST_EMAIL = "finance-test@wolfcommand.net"
AMANDA_TEST_EMAIL = "amanda-test@wolfcommand.net"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core import fc_recon_queues1 as _queue  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


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
        with urlopen(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


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


def seed_permissions(conn: sqlite3.Connection) -> None:
    perms = (
        (PERM_PR, "bzg.pr.create", "pr_create"),
        (PERM_PO, "bzg.po.create", "po_create"),
        (PERM_RECV, "venue.receive", "receive"),
        (PERM_BILL, "bzg.bill.capture", "bill_capture"),
        (PERM_MATCH, "bzg.match.run", "match_run"),
        ("PERM-BZG-AP-VIEW", "bzg.ap.view", "ap_view"),
        (PERM_AP_MARK, "bzg.ap.mark_ready", "ap_mark_ready"),
        (PERM_PAY_LIST, "bzg.pay.list_ready", "pay_list_ready"),
        (PERM_PAY_MARK, "bzg.pay.mark_ready", "pay_mark_ready"),
        (PERM_PAY_RECORD, "bzg.pay.record", "pay_record"),
        (WORK_COMPLETE, "work.complete", "complete"),
        ("PERM-WORK-UPDATE", "work.update", "update"),
        ("PERM-FIN-READ", "finance.nota.read", "finance_read"),
        ("PERM-ATRIUM-BOARD-READ", "atrium.board.read", "board_read"),
    )
    for perm_id, code, action in perms:
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'bzg', ?, 'test seed', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
            """,
            (perm_id, code, action, TS, TS),
        )
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
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-GGV-ONLY', 'GGV Only', 'DEPT-GGV', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    for role_id, perm_ids in (
        (
            "ROLE-BZG-FB-OPS-LEAD",
            (PERM_PR, PERM_PO, PERM_RECV, PERM_BILL, PERM_MATCH, PERM_AP_MARK, PERM_PAY_MARK, PERM_PAY_LIST, WORK_COMPLETE),
        ),
        (
            "ROLE-BZG-FINANCIAL-CONTROLLER",
            (
                PERM_AP_MARK,
                PERM_PAY_LIST,
                PERM_PAY_MARK,
                PERM_PAY_RECORD,
                "PERM-FIN-READ",
                "PERM-ATRIUM-BOARD-READ",
            ),
        ),
    ):
        for perm_id in perm_ids:
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
                """,
                (role_id, perm_id, TS, TS),
            )
    for pos_id, role_id, label in (
        ("POS-BZG-FB-OPS-1", "ROLE-BZG-FB-OPS-LEAD", "Ops Lead"),
        ("POS-BZG-FB-OPS-2", "ROLE-BZG-FB-OPS-LEAD", "Ops Lead 2"),
        ("POS-BZG-FB-OPS-3", "ROLE-BZG-FB-OPS-LEAD", "Matcher"),
        ("POS-BZG-FB-OPS-4", "ROLE-BZG-FB-OPS-LEAD", "Controller"),
        ("POS-BZG-FIN-1", "ROLE-BZG-FINANCIAL-CONTROLLER", "Finance"),
        ("POS-GGV-ONLY-1", "ROLE-GGV-ONLY", "GGV desk"),
        ("POS-BZG-FB-OPS-5", "ROLE-BZG-FB-OPS-LEAD", "Ops 5"),
        ("POS-BZG-FB-OPS-6", "ROLE-BZG-FB-OPS-LEAD", "Ops 6"),
        ("POS-BZG-FB-OPS-7", "ROLE-BZG-FB-OPS-LEAD", "Ops 7"),
        ("POS-BZG-FB-OPS-8", "ROLE-BZG-FB-OPS-LEAD", "Ops 8"),
    ):
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (pos_id, role_id, label, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES ('ENT-BZG', 'Blu Zone Group', 'Blu Zone Group', 'OPERATING', 'ACTIVE', 0, ?, ?)
        ON CONFLICT(entity_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_brands (
          brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
        ) VALUES ('BZG-UMA', 'ENT-BZG', 'Uma Blu', 'VENUE', 'ACTIVE', ?, ?)
        ON CONFLICT(brand_id) DO NOTHING
        """,
        (TS, TS),
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
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES ('SCOPE-ENT-BZG', 'entity', 'BZG entity', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES ('SCOPE-ENT-BZG', 'entity', 'ENT-BZG', ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (TS,),
    )
    conn.commit()


def seed_auth_email(conn: sqlite3.Connection, person_id: str, email: str) -> None:
    auth_id = f"AUTH-{person_id}"
    conn.execute(
        """
        INSERT INTO org_auth_identities (
          auth_identity_id, person_id, provider, identifier, status, is_primary, created_at, updated_at
        ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(auth_identity_id) DO UPDATE SET identifier=excluded.identifier, status='ACTIVE'
        """,
        (auth_id, person_id, email, TS, TS),
    )
    conn.commit()


def seed_operator(conn: sqlite3.Connection, person_id: str, assignment_id: str, position_id: str) -> str:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
        """,
        (person_id, f"Test {person_id}", TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL
        """,
        (assignment_id, person_id, position_id, TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, assignment_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()
    return person_id


def seed_protected_closes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS venue_daily_closes (
          close_id TEXT PRIMARY KEY,
          business_date TEXT,
          state TEXT,
          declared_cash_amount REAL,
          variance_cash_amount REAL,
          submitted_by_person_id TEXT,
          taken_by_person_id TEXT,
          esb_totals_json TEXT,
          updated_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (
          close_id, business_date, state, declared_cash_amount, variance_cash_amount,
          submitted_by_person_id, taken_by_person_id, esb_totals_json, updated_at
        ) VALUES (?, '2026-10-03', 'EXCEPTION', 3225000, -125000, NULL, NULL, NULL, '2026-10-03T13:47:39Z')
        """,
        (PROTECTED_CLOSE,),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (close_id, business_date, state, updated_at)
        VALUES (?, '2026-10-01', 'CANCELLED', '2026-10-01T00:00:00Z')
        """,
        ("VDC-87202768-55af-4c8e-abc3-382a5496b8c6",),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (
          close_id, business_date, state, submitted_by_person_id, taken_by_person_id,
          declared_cash_amount, esb_totals_json, updated_at
        ) VALUES (?, '2026-10-04', 'OPEN', 'PERS-IZA', 'PERS-MATT', NULL, '{"locked":true}', '2026-10-04T00:00:00Z')
        """,
        ("VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",),
    )
    conn.commit()


def make_approved_pr(conn: sqlite3.Connection, *, pr_id: str, requester: str) -> str:
    from core import uma_ops_console as ops

    ops.insert_pr_row(pr_id=pr_id, state="APPROVED", purpose="Kitchen restock", example=False, conn=conn)
    conn.execute(
        """
        UPDATE bzg_ops_purchase_requests
        SET outlet_id=?, entity_id='ENT-BZG', requester_person_id=?, requester_assignment_id='ASG-X'
        WHERE pr_id=?
        """,
        ("BZG-UMA", requester, pr_id),
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
        VALUES (?, ?, 'Cooking oil', 10, 'L', ?)
        """,
        (f"PRL-{pr_id.replace('PR-UMA-', '')}", pr_id, TS),
    )
    conn.commit()
    return pr_id


def record_approver(conn: sqlite3.Connection, pr_id: str, approver: str) -> None:
    req_id = f"APR-{pr_id[-8:]}"
    dec_id = f"DEC-{pr_id[-8:]}"
    conn.execute(
        """
        INSERT INTO core_approval_requests (
          approval_request_id, request_type, title, owning_entity_id, brand_id,
          requested_by_person_id, required_permission_code, required_permission_id,
          source_type, source_id, status, requested_at, created_at, updated_at, correlation_id
        ) VALUES (?, 'GENERAL', 'Test approval', 'ENT-BZG', 'BZG-UMA',
                  'PERS-REQ', 'work.complete', ?, 'HUMAN', ?, 'APPROVED', ?, ?, ?, ?)
        ON CONFLICT(approval_request_id) DO NOTHING
        """,
        (req_id, WORK_COMPLETE, pr_id, TS, TS, TS, f"corr-{req_id}"),
    )
    conn.execute(
        """
        INSERT INTO core_approval_decisions (
          approval_decision_id, approval_request_id, decision, decided_by_person_id,
          decided_at, authority_allowed, reason, correlation_id, created_at
        ) VALUES (?, ?, 'APPROVED', ?, ?, 1, 'test', ?, ?)
        """,
        (dec_id, req_id, approver, TS, f"corr-{dec_id}", TS),
    )
    conn.commit()


def save_photo(bill_mod, td: Path) -> str:
    photo_dir = td / "nota-photos"
    bill_mod.NOTA_PHOTO_DIR = photo_dir
    saved = bill_mod.save_nota_photo_bytes(
        data=b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes-for-test",
        filename="nota.jpg",
        content_type="image/jpeg",
    )
    return saved["photo_object_ref"]


def build_ready_chain(
    conn,
    mods,
    td: Path,
    *,
    nota_number: str = "NOTA-PAY1",
    total: float = 1_000_000,
    finance: str = "PERS-FIN-API",
    approver_pos: str = "POS-BZG-FB-OPS-2",
    marker_pos: str = "POS-BZG-FB-OPS-3",
    controller_pos: str = "POS-BZG-FB-OPS-4",
    pay_marker_pos: str = "POS-BZG-FB-OPS-1",
) -> dict:
    po_mod, gr_mod, bill_mod, match_mod, ap_mod, rtp_mod = mods
    suffix = nota_number.replace("-", "").lower()[:6]
    approver = seed_operator(conn, f"PERS-APP-{suffix}", f"ASG-APP-{suffix}", approver_pos)
    marker = seed_operator(conn, f"PERS-MARK-{suffix}", f"ASG-MARK-{suffix}", marker_pos)
    controller = seed_operator(conn, f"PERS-CTRL-{suffix}", f"ASG-CTRL-{suffix}", controller_pos)
    pay_marker = seed_operator(conn, f"PERS-PAY-{suffix}", f"ASG-PAY-{suffix}", pay_marker_pos)
    photo_ref = save_photo(bill_mod, td)
    pr_id = f"PR-UMA-PAY-{suffix.upper()}"
    make_approved_pr(conn, pr_id=pr_id, requester=f"PERS-REQ-{suffix}")
    record_approver(conn, pr_id, approver)
    saved_po = po_mod.create_purchase_order(
        person_id=approver,
        pr_id=pr_id,
        supplier_id=TEST_SUPPLIER["supplier_id"],
        lines=[{"item": "Cooking oil", "qty": 10, "unit": "L"}],
        conn=conn,
        commit=True,
    )
    po_line_id = saved_po["lines"][0]["line_id"]
    full_gr = gr_mod.create_goods_receipt(
        person_id=marker,
        po_id=saved_po["po_id"],
        lines=[{"po_line_id": po_line_id, "received_qty": 10}],
        conn=conn,
        commit=True,
    )
    gr_line_id = full_gr["lines"][0]["line_id"]
    saved_bill = bill_mod.create_supplier_bill(
        person_id=marker,
        gr_id=full_gr["gr_id"],
        nota_number=nota_number,
        nota_date="2026-10-05",
        photo_object_ref=photo_ref,
        stated_total=total,
        lines=[{"gr_line_id": gr_line_id, "billed_qty": 10, "billed_unit_price": total / 10}],
        conn=conn,
        commit=True,
    )
    match_mod.run_three_way_match(person_id=marker, bill_id=saved_bill["bill_id"], conn=conn, commit=True)
    ap_mod.mark_ap_ready(person_id=controller, bill_id=saved_bill["bill_id"], conn=conn, commit=True)
    rtp_mod.mark_ready_to_pay(person_id=pay_marker, bill_id=saved_bill["bill_id"], conn=conn, commit=True)
    return {
        "bill_id": saved_bill["bill_id"],
        "controller": controller,
        "pay_marker": pay_marker,
        "finance": finance,
        "stated_total": total,
    }


def seed_bank_txn(conn: sqlite3.Connection, *, txn_id: str, amount: float, paid_date: str) -> None:
    from core import bzg_history_import1 as _hist

    _hist.ensure_history_schema(conn)
    conn.execute(
        """
        INSERT INTO bzg_bank_statement_imports (
          import_id, entity_id, bank_label, account_label, original_filename, original_path,
          content_sha256, uploaded_by_person_id, uploaded_at, period_start, period_end,
          txn_count, parse_status
        ) VALUES ('IMP-PAY-TEST', 'ENT-BZG', 'Mandiri', '1610555335558',
                  'test.csv', '/tmp/test.csv', 'sha-test-pay', 'PERS-FIN-API', ?,
                  '2026-10-01', '2026-10-31', 1, 'PARSED')
        ON CONFLICT(import_id) DO NOTHING
        """,
        (TS,),
    )
    conn.execute(
        """
        INSERT INTO bzg_bank_transactions (
          txn_id, import_id, entity_id, txn_date, description, debit, credit, bank_account,
          recon_status, matched_ledger_source_id, match_confidence, notes, created_at
        ) VALUES (?, 'IMP-PAY-TEST', 'ENT-BZG', ?, 'Supplier payment test', ?, 0,
                  'Mandiri-1610555335558', 'POSSIBLE MATCH', NULL, 'AMOUNT_DATE_SLACK', NULL, ?)
        """,
        (txn_id, paid_date, amount, TS),
    )
    conn.commit()


def forbidden_grant_counts(conn: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for code in ("payment.execute", "payment.approve"):
        row = conn.execute(
            """
            SELECT COUNT(*) FROM org_permissions p
            JOIN org_role_permissions rp ON p.permission_id=rp.permission_id
            WHERE p.code=? AND rp.effect='ALLOW'
            """,
            (code,),
        ).fetchone()
        out[code] = int(row[0]) if row else 0
    row = conn.execute(
        """
        SELECT COUNT(*) FROM org_permissions p
        JOIN org_role_permissions rp ON p.permission_id=rp.permission_id
        WHERE p.code LIKE '%vendor%bank%' AND rp.effect='ALLOW'
        """
    ).fetchone()
    out["vendor_bank_change"] = int(row[0]) if row else 0
    return out


def run_core_tests(conn, mods, td: Path) -> dict:
    from core import bzg_payment_record as pay

    pay_mod = mods[-1]
    chain = build_ready_chain(conn, mods[:-1], td)
    bid = chain["bill_id"]
    finance = chain["finance"]

    grants = forbidden_grant_counts(conn)
    check("payment.execute grants 0", grants.get("payment.execute", 0) == 0, str(grants))
    check("payment.approve grants 0", grants.get("payment.approve", 0) == 0, str(grants))
    check("vendor bank change grants 0", grants.get("vendor_bank_change", 0) == 0, str(grants))

    try:
        pay_mod.record_payment(
            person_id=chain["controller"],
            bill_id=bid,
            paid_date="2026-10-05",
            amount=500_000,
            from_account="Mandiri-1610555335558",
            bank_reference="REF-SOD-AP",
            conn=conn,
            commit=False,
        )
        check("ap marker cannot record", False, "should raise")
    except pay.PaymentRecordError as exc:
        check("ap marker cannot record", exc.code == "ap_marker_cannot_record_payment", str(exc))

    try:
        pay_mod.record_payment(
            person_id=chain["pay_marker"],
            bill_id=bid,
            paid_date="2026-10-05",
            amount=500_000,
            from_account="Mandiri-1610555335558",
            bank_reference="REF-SOD-RTP",
            conn=conn,
            commit=False,
        )
        check("rtp marker cannot record", False, "should raise")
    except pay.PaymentRecordError as exc:
        check("rtp marker cannot record", exc.code == "pay_ready_marker_cannot_record_payment", str(exc))

    proof_dir = td / "payment-proofs"
    pay_mod.PROOF_DIR = proof_dir
    proof = pay_mod.save_proof_bytes(data=b"%PDF-1.4 test proof", filename="proof.pdf", content_type="application/pdf")

    partial = pay_mod.record_payment(
        person_id=finance,
        bill_id=bid,
        paid_date="2026-10-05",
        amount=400_000,
        from_account="Mandiri-1610555335558",
        bank_reference="REF-PARTIAL-1",
        proof_object_ref=proof["proof_object_ref"],
        conn=conn,
        commit=True,
    )
    check("partial payment recorded", partial.get("status") == "claimed")
    check("partial status label", partial.get("status_label") == "Paid (claimed)")
    summary = pay_mod.bill_payment_summary(conn, bid)
    check("partial remaining balance", abs(summary["remaining_balance"] - 600_000) < 1, str(summary))

    again = pay_mod.record_payment(
        person_id=finance,
        bill_id=bid,
        paid_date="2026-10-05",
        amount=400_000,
        from_account="Mandiri-1610555335558",
        bank_reference="REF-PARTIAL-1",
        conn=conn,
        commit=True,
    )
    check("idempotent same bank ref", again.get("payment_record_id") == partial.get("payment_record_id"))

    final = pay_mod.record_payment(
        person_id=finance,
        bill_id=bid,
        paid_date="2026-10-05",
        amount=600_000,
        from_account="Mandiri-1610555335558",
        bank_reference="REF-FINAL-1",
        conn=conn,
        commit=True,
    )
    check("final payment recorded", final.get("status") == "claimed")
    cols = pay_mod.ap_payment_columns(conn, bid)
    check("claimed not yet seen in bank", cols.get("verified_label") == "Not yet seen in bank", str(cols))

    prid = str(final.get("payment_record_id") or partial.get("payment_record_id"))
    txn_id = "TXN-PAY-TEST-001"
    seed_bank_txn(conn, txn_id=txn_id, amount=600_000, paid_date="2026-10-05")
    conn.execute(
        """
        UPDATE bzg_bank_transactions
        SET recon_status='POSSIBLE MATCH', matched_ledger_source_id=?, match_confidence='EXACT_LEDGER_PAYMENT'
        WHERE txn_id=?
        """,
        (prid, txn_id),
    )
    conn.commit()
    _queue.confirm_match(
        conn,
        entity="ENT-BZG",
        txn_id=txn_id,
        person_id=finance,
        matched_ref=prid,
        commit=True,
    )
    verified = pay_mod.list_payments_for_bill(bid, conn=conn)
    check("bank confirm verifies payment", any(p.get("status") in {"verified", "closed"} for p in verified), str(verified))
    cols_after = pay_mod.ap_payment_columns(conn, bid)
    check("fully paid verified columns", cols_after.get("paid_claimed_label") == "Paid (claimed)", str(cols_after))

    audit = conn.execute(
        "SELECT action FROM core_audit_events WHERE resource_id=? AND action='bzg.pay.record'",
        (partial.get("payment_record_id"),),
    ).fetchone()
    check("audit append for record", audit is not None)

    for close_id in PROTECTED_IDS:
        row = conn.execute(
            "SELECT state FROM venue_daily_closes WHERE close_id=?", (close_id,)
        ).fetchone()
        check(f"protected close untouched {close_id}", row is not None)
    return chain


class HarnessApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.td = tempfile.mkdtemp(prefix="p2p-pay-rec1-", dir=str(ROOT / "state"))
        cls.db = Path(cls.td) / "content_library.sqlite"
        from core import audit as au
        from core import bzg_ap_ready as ap
        from core import bzg_finance_desk as desk
        from core import bzg_goods_receiving as gr
        from core import bzg_outlet_registry as outlets
        from core import bzg_payment_record as pay
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import bzg_ready_to_pay as rtp
        from core import bzg_supplier_bill as bill
        from core import bzg_three_way_match as match
        from core import rbac as rb
        from core import uma_devi_p0 as p0
        from core import uma_ops_console as ops

        cls.mods = (po, gr, bill, match, ap, rtp, pay)
        for mod in (ops, pr, po, gr, bill, match, ap, rtp, pay, rb, au, outlets, p0, desk):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = cls.db
        po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None

        conn = sqlite3.connect(str(cls.db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        outlets.ensure_schema(conn)
        outlets.seed_registry(conn, TS)
        pr.ensure_pr_columns(conn)
        po.ensure_po_schema(conn)
        gr.ensure_gr_schema(conn)
        bill.ensure_bill_schema(conn)
        match.ensure_match_schema(conn)
        ap.ensure_ap_schema(conn)
        rtp.ensure_ready_to_pay_schema(conn)
        pay.ensure_payment_record_schema(conn)
        seed_permissions(conn)
        seed_protected_closes(conn)
        finance = seed_operator(conn, "PERS-FIN-API", "ASG-FIN-API", "POS-BZG-FIN-1")
        from core.scope import upsert_assignment_scope

        upsert_assignment_scope(conn, "ASG-FIN-API", "SCOPE-ENT-BZG", TS, TS)
        seed_auth_email(conn, finance, FINANCE_TEST_EMAIL)
        amanda = seed_operator(conn, "PERS-AMANDA-T", "ASG-AMANDA-T", "POS-GGV-ONLY-1")
        seed_auth_email(conn, amanda, AMANDA_TEST_EMAIL)
        cls.chain = run_core_tests(conn, cls.mods, Path(cls.td))
        cls.api_chain = build_ready_chain(
            conn,
            cls.mods[:-1],
            Path(cls.td),
            nota_number="NOTA-API2",
            total=500_000,
            finance="PERS-FIN-API",
            approver_pos="POS-BZG-FB-OPS-5",
            marker_pos="POS-BZG-FB-OPS-6",
            controller_pos="POS-BZG-FB-OPS-7",
            pay_marker_pos="POS-BZG-FB-OPS-8",
        )
        conn.close()

        import serve_beta as sb
        from core import ggv_finance_nota as _ggv_fin
        from core import identity as _identity

        Handler = _http_handler()
        for mod in (sb, _ggv_fin, desk, _identity, ops):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = cls.db  # type: ignore[attr-defined]
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_finance_ap_columns_in_html(self) -> None:
        html = DASHBOARD.read_text(encoding="utf-8")
        self.assertIn("Paid (claimed)", html)
        self.assertIn("verified_label", html)
        self.assertNotIn("PAID_CLAIMED", html)
        self.assertNotIn("payment.execute", html)

    def test_record_payment_api(self) -> None:
        chain = self.api_chain
        status, raw = _call(
            self.base,
            "POST",
            "/api/bzg/finance/payments/record",
            FINANCE_TEST_EMAIL,
            body={
                "bill_id": chain["bill_id"],
                "paid_date": "2026-10-05",
                "amount": 250_000,
                "from_account": "Mandiri-1610555335558",
                "bank_reference": "REF-API-2",
            },
        )
        self.assertEqual(status, 200, raw.decode())
        body = json.loads(raw)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("payment", {}).get("status"), "claimed")

    def test_amanda_bzg_finance_denied(self) -> None:
        status, _ = _call(self.base, "GET", "/api/bzg/finance/ap", AMANDA_TEST_EMAIL)
        self.assertIn(status, (403, 401))

    def test_ap_api_has_payment_columns(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/ap?limit=5", FINANCE_TEST_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw)
        rows = body.get("ap_ready") or []
        if rows:
            self.assertIn("paid_claimed_label", rows[0])
            self.assertIn("verified_label", rows[0])


def main() -> int:
    global PASS, FAIL
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HarnessApiTests)
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    FAIL += len(result.failures) + len(result.errors)
    PASS += result.testsRun - len(result.failures) - len(result.errors)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
