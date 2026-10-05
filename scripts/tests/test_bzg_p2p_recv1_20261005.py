#!/usr/bin/env python3
"""BZG-P2P-RECV-1 — Goods receiving against saved PO. Temp sqlite only."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
PROTECTED_IDS = (
    PROTECTED_CLOSE,
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
TS = "2026-10-05T08:00:00+08:00"
PERM_PO = "PERM-BZG-PO-CREATE"
PERM_PO_CODE = "bzg.po.create"
PERM_PR = "PERM-BZG-PR-CREATE"
PERM_RECV = "PERM-VENUE-RECEIVE"
PERM_RECV_CODE = "venue.receive"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
TEST_SUPPLIER = {"supplier_id": "SUP-TEST-1", "name": "Test Supplier Co"}

sys.path.insert(0, str(SCRIPTS))

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
    for perm_id, code, action in (
        (PERM_PR, "bzg.pr.create", "pr_create"),
        (PERM_PO, PERM_PO_CODE, "po_create"),
        (PERM_RECV, PERM_RECV_CODE, "receive"),
        (WORK_COMPLETE, "work.complete", "complete"),
        ("PERM-WORK-UPDATE", "work.update", "update"),
    ):
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
        VALUES ('ROLE-BZG-NO-RECV', 'No receive', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    for role_id, perms in (
        ("ROLE-BZG-FB-OPS-LEAD", (PERM_PR, PERM_PO, PERM_RECV, WORK_COMPLETE, "PERM-WORK-UPDATE")),
        ("ROLE-BZG-NO-RECV", (PERM_PR, PERM_PO, WORK_COMPLETE)),
    ):
        for perm_id in perms:
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
        ("POS-BZG-FB-OPS-3", "ROLE-BZG-FB-OPS-LEAD", "Receiver"),
        ("POS-BZG-NO-RECV-1", "ROLE-BZG-NO-RECV", "No recv seat"),
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
    conn.commit()


def seed_operator(conn: sqlite3.Connection, person_id: str, assignment_id: str, position_id: str) -> str:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', display_name=excluded.display_name
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


def make_approved_pr(
    conn: sqlite3.Connection,
    *,
    pr_id: str,
    requester: str,
    state: str = "APPROVED",
    example: bool = False,
    outlet_id: str = "BZG-UMA",
    item: str = "Cooking oil",
    qty: float = 10,
) -> str:
    from core import uma_ops_console as ops

    ops.insert_pr_row(
        pr_id=pr_id,
        state=state,
        purpose="Kitchen restock",
        example=example,
        conn=conn,
    )
    conn.execute(
        """
        UPDATE bzg_ops_purchase_requests
        SET outlet_id=?, entity_id='ENT-BZG', requester_person_id=?, requester_assignment_id='ASG-X'
        WHERE pr_id=?
        """,
        (outlet_id, requester, pr_id),
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
        VALUES (?, ?, ?, ?, 'L', ?)
        """,
        (f"PRL-{pr_id[-6:]}", pr_id, item, qty, TS),
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


def make_po(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    pr_id: str,
    qty: float = 10,
) -> dict:
    from core import bzg_purchase_order as po

    return po.create_purchase_order(
        person_id=person_id,
        pr_id=pr_id,
        supplier_id=TEST_SUPPLIER["supplier_id"],
        lines=[{"item": "Cooking oil", "qty": qty, "unit": "L"}],
        conn=conn,
        commit=True,
    )


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"

    td = tempfile.mkdtemp(prefix="bzg-recv1-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        from core import audit as au
        from core import bzg_goods_receiving as gr
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import rbac as rb
        from core import uma_devi_p0 as p0
        from core import uma_ops_console as ops

        for mod in (ops, pr, po, gr, rb, au, outlets, p0):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db

        po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        outlets.ensure_schema(conn)
        outlets.seed_registry(conn, TS)
        pr.ensure_pr_columns(conn)
        po.ensure_po_schema(conn)
        gr.ensure_gr_schema(conn)
        seed_permissions(conn)
        seed_protected_closes(conn)

        requester = seed_operator(conn, "PERS-REQ", "ASG-REQ-1", "POS-BZG-FB-OPS-1")
        approver = seed_operator(conn, "PERS-APP", "ASG-APP-1", "POS-BZG-FB-OPS-2")
        receiver = seed_operator(conn, "PERS-RCV", "ASG-RCV-1", "POS-BZG-FB-OPS-3")
        denied = seed_operator(conn, "PERS-NO-RECV", "ASG-NO-RECV-1", "POS-BZG-NO-RECV-1")

        approved_id = make_approved_pr(conn, pr_id="PR-UMA-APPROVED01", requester=requester)
        example_id = make_approved_pr(
            conn, pr_id="PR-UMA-EXAMPLE01", requester=requester, example=True
        )
        record_approver(conn, approved_id, approver)

        saved_po = make_po(conn, person_id=approver, pr_id=approved_id, qty=10)
        po_id = saved_po["po_id"]
        po_line_id = saved_po["lines"][0]["line_id"]

        example_po_id = "PO-UMA-EXAMPLE01"
        conn.execute(
            """
            INSERT INTO bzg_ops_purchase_orders (
              po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              created_by_person_id, state, created_at, updated_at
            ) VALUES (?, ?, 'BZG-UMA', 'ENT-BZG', ?, ?, ?, 'OPEN', ?, ?)
            """,
            (
                example_po_id,
                example_id,
                TEST_SUPPLIER["supplier_id"],
                TEST_SUPPLIER["name"],
                approver,
                TS,
                TS,
            ),
        )
        conn.execute(
            """
            INSERT INTO bzg_ops_po_lines (line_id, po_id, item, qty, unit, created_at)
            VALUES ('POL-EXAMPLE1', ?, 'Cooking oil', 5, 'L', ?)
            """,
            (example_po_id, TS),
        )
        ops.transition_pr(example_id, "ORDERED", verified_person_id=approver, conn=conn, commit=True)
        conn.commit()

        try:
            gr.create_goods_receipt(person_id="", po_id=po_id, lines=[], conn=conn, commit=False)
            check("unauthenticated denied", False, "should raise")
        except gr.GrError as exc:
            check("unauthenticated denied", exc.code == "unauthenticated", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=denied,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 1}],
                conn=conn,
                commit=False,
            )
            check("no permission denied", False, "should raise")
        except gr.GrError as exc:
            check("no permission denied", exc.code == "forbidden", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id="PO-UMA-NOTREAL",
                lines=[{"po_line_id": po_line_id, "received_qty": 1}],
                conn=conn,
                commit=False,
            )
            check("non-existent order denied", False, "should raise")
        except gr.GrError as exc:
            check("non-existent order denied", exc.code == "not_found", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=example_po_id,
                lines=[{"po_line_id": "POL-EXAMPLE1", "received_qty": 1}],
                conn=conn,
                commit=False,
            )
            check("example order denied", False, "should raise")
        except gr.GrError as exc:
            check("example order denied", exc.code == "example_denied", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=po_id,
                lines=[{"po_line_id": "POL-FAKE", "received_qty": 1}],
                conn=conn,
                commit=False,
            )
            check("line not on order denied", False, "should raise")
        except gr.GrError as exc:
            check("line not on order denied", exc.code == "line_not_on_order", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 99}],
                conn=conn,
                commit=False,
            )
            check("qty above outstanding denied", False, "should raise")
        except gr.GrError as exc:
            check("qty above outstanding denied", exc.code == "qty_above_outstanding", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 1}],
                outlet_id="WRONG-OUTLET",
                conn=conn,
                commit=False,
            )
            check("client outlet mismatch rejected", False, "should raise")
        except gr.GrError as exc:
            check("client outlet mismatch rejected", exc.code == "outlet_mismatch", str(exc))

        try:
            gr.create_goods_receipt(
                person_id=approver,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 1}],
                conn=conn,
                commit=False,
            )
            check("approver-as-receiver denied", False, "should raise")
        except gr.GrError as exc:
            check("approver-as-receiver denied", exc.code == "approver_receive_denied", str(exc))

        state_before = ops.get_pr(approved_id, conn=conn)
        check("state before partial is ORDERED", state_before and state_before.get("state") == "ORDERED")
        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 20}],
                conn=conn,
                commit=False,
            )
            check("failed save leaves state unchanged", False, "should raise")
        except gr.GrError:
            pass
        state_after_fail = ops.get_pr(approved_id, conn=conn)
        check(
            "failed save leaves state unchanged",
            state_after_fail and state_after_fail.get("state") == "ORDERED",
            str(state_after_fail),
        )

        partial = gr.create_goods_receipt(
            person_id=receiver,
            po_id=po_id,
            lines=[{"po_line_id": po_line_id, "received_qty": 4, "shortfall_reason": "short"}],
            notes="first delivery",
            conn=conn,
            commit=True,
        )
        check("partial receipt saved", partial.get("status") == "PARTIAL")
        pr_partial = ops.get_pr(approved_id, conn=conn)
        check(
            "partial receipt keeps request not fully received",
            pr_partial and pr_partial.get("state") == "PARTIALLY_RECEIVED",
            str(pr_partial),
        )
        check(
            "no bill state on partial",
            pr_partial and pr_partial.get("state") not in ("BILL_RECEIVED", "PAYMENT_REQUESTED", "PAID_CLAIMED"),
        )

        try:
            gr.create_goods_receipt(
                person_id=receiver,
                po_id=po_id,
                lines=[{"po_line_id": po_line_id, "received_qty": 7}],
                conn=conn,
                commit=False,
            )
            check("qty above outstanding across receipts denied", False, "should raise")
        except gr.GrError as exc:
            check("qty above outstanding across receipts denied", exc.code == "qty_above_outstanding", str(exc))

        full = gr.create_goods_receipt(
            person_id=receiver,
            po_id=po_id,
            lines=[{"po_line_id": po_line_id, "received_qty": 6}],
            conn=conn,
            commit=True,
        )
        check("full receipt saved", full.get("status") == "COMPLETE")
        pr_full = ops.get_pr(approved_id, conn=conn)
        check("full receipt moves to RECEIVED", pr_full and pr_full.get("state") == "RECEIVED")
        check(
            "no payment state",
            pr_full and not str(pr_full.get("state") or "").startswith("PAYMENT"),
        )

        reloaded = gr.get_goods_receipt(partial["gr_id"], person_id=receiver, conn=conn)
        check("reload same receipt id", reloaded and reloaded.get("gr_id") == partial["gr_id"])
        check(
            "reload same line qty",
            reloaded and reloaded["lines"][0]["received_qty"] == 4,
            str(reloaded),
        )
        check(
            "reload shortfall reason",
            reloaded and reloaded["lines"][0].get("shortfall_reason") == "short",
        )

        audit_row = conn.execute(
            "SELECT action FROM core_audit_events WHERE resource_id=? AND action='bzg.receiving.create'",
            (partial["gr_id"],),
        ).fetchone()
        check("audit row for create", audit_row is not None)

        for close_id in PROTECTED_IDS:
            row = conn.execute(
                "SELECT state, declared_cash_amount, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
                (close_id,),
            ).fetchone()
            check(f"protected close untouched {close_id}", row is not None, str(close_id))

        live = ROOT / "catalog" / "content_library.sqlite"
        if live.is_file():
            live_conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
            try:
                row = live_conn.execute(
                    "SELECT close_id, state FROM venue_daily_closes WHERE close_id=?",
                    (PROTECTED_CLOSE,),
                ).fetchone()
                check("live protected close read-only ok", row is not None, str(row))
            finally:
                live_conn.close()

        conn.rollback()
    finally:
        pass

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
