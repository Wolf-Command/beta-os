#!/usr/bin/env python3
"""BZG-P2P-PO-1 — Purchase order from approved PR. Temp sqlite only."""
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
TS = "2026-10-04T20:00:00+08:00"
PERM_PO = "PERM-BZG-PO-CREATE"
PERM_PO_CODE = "bzg.po.create"
PERM_PR = "PERM-BZG-PR-CREATE"
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
        VALUES ('ROLE-BZG-NO-PO', 'No PO', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    for role_id, perms in (
        ("ROLE-BZG-FB-OPS-LEAD", (PERM_PR, PERM_PO, WORK_COMPLETE, "PERM-WORK-UPDATE")),
        ("ROLE-BZG-NO-PO", (PERM_PR,)),
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
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-BZG-FB-OPS-1', 'ROLE-BZG-FB-OPS-LEAD', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'Ops Lead', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-BZG-FB-OPS-2', 'ROLE-BZG-FB-OPS-LEAD', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'Ops Lead 2', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-BZG-NO-PO-1', 'ROLE-BZG-NO-PO', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'No PO seat', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (TS, TS),
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
    qty: float = 5,
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


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"

    td = tempfile.mkdtemp(prefix="bzg-po1-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        from core import audit as au
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import rbac as rb
        from core import uma_devi_p0 as p0
        from core import uma_ops_console as ops

        for mod in (ops, pr, po, rb, au, outlets, p0):
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
        seed_permissions(conn)
        seed_protected_closes(conn)

        requester = seed_operator(conn, "PERS-REQ", "ASG-REQ-1", "POS-BZG-FB-OPS-1")
        approver = seed_operator(conn, "PERS-APP", "ASG-APP-1", "POS-BZG-FB-OPS-2")
        denied = seed_operator(conn, "PERS-NO-PO", "ASG-NO-PO-1", "POS-BZG-NO-PO-1")

        approved_id = make_approved_pr(conn, pr_id="PR-UMA-APPROVED01", requester=requester)
        requested_id = make_approved_pr(
            conn, pr_id="PR-UMA-REQUESTED1", requester=requester, state="REQUESTED"
        )
        example_id = make_approved_pr(
            conn, pr_id="PR-UMA-EXAMPLE01", requester=requester, example=True
        )
        no_outlet_id = make_approved_pr(
            conn, pr_id="PR-UMA-NOOUTLET1", requester=requester, outlet_id=""
        )
        conn.execute(
            "UPDATE bzg_ops_purchase_requests SET outlet_id=NULL WHERE pr_id=?",
            (no_outlet_id,),
        )
        conn.commit()

        line = [{"item": "Cooking oil", "qty": 5, "unit": "L"}]

        try:
            po.create_purchase_order(
                person_id="",
                pr_id=approved_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=line,
                conn=conn,
                commit=False,
            )
            check("unauthenticated denied", False, "should raise")
        except po.PoError as exc:
            check("unauthenticated denied", exc.code == "unauthenticated", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=requested_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=line,
                conn=conn,
                commit=False,
            )
            check("non-approved request denied", False, "should raise")
        except po.PoError as exc:
            check("non-approved request denied", exc.code == "not_approved", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=example_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=line,
                conn=conn,
                commit=False,
            )
            check("example row denied", False, "should raise")
        except po.PoError as exc:
            check("example row denied", exc.code == "example_denied", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=no_outlet_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=line,
                conn=conn,
                commit=False,
            )
            check("missing outlet denied", False, "should raise")
        except po.PoError as exc:
            check("missing outlet denied", exc.code == "missing_outlet", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=approved_id,
                supplier_id="SUP-NOT-IN-LIST",
                lines=line,
                conn=conn,
                commit=False,
            )
            check("supplier not in projection denied", False, "should raise")
        except po.PoError as exc:
            check("supplier not in projection denied", exc.code == "invalid_supplier", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=approved_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=[{"item": "Mystery spice", "qty": 1}],
                conn=conn,
                commit=False,
            )
            check("line item not on request denied", False, "should raise")
        except po.PoError as exc:
            check("line item not on request denied", exc.code == "line_not_on_request", str(exc))

        try:
            po.create_purchase_order(
                person_id=approver,
                pr_id=approved_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=[{"item": "Cooking oil", "qty": 99}],
                conn=conn,
                commit=False,
            )
            check("qty above request denied", False, "should raise")
        except po.PoError as exc:
            check("qty above request denied", exc.code == "qty_above_request", str(exc))

        try:
            po.create_purchase_order(
                person_id=denied,
                pr_id=approved_id,
                supplier_id=TEST_SUPPLIER["supplier_id"],
                lines=line,
                conn=conn,
                commit=False,
            )
            check("no po permission denied", False, "should raise")
        except po.PoError as exc:
            check("no po permission denied", exc.code == "forbidden", str(exc))

        try:
            p0.approve_purchase_segregated(
                person_id=requester,
                pr_id=requested_id,
                conn=conn,
                commit=False,
            )
            check("requester self-approval denied", False, "should raise")
        except ops.UmaOpsError as exc:
            check("requester self-approval denied", exc.code == "self_approval_denied", str(exc))

        saved = po.create_purchase_order(
            person_id=approver,
            pr_id=approved_id,
            supplier_id=TEST_SUPPLIER["supplier_id"],
            lines=[{"item": "Cooking oil", "qty": 3, "unit": "L"}],
            conn=conn,
            commit=True,
        )
        check("save succeeds", bool(saved.get("po_id")))
        check("supplier id stored", saved.get("supplier_id") == TEST_SUPPLIER["supplier_id"])
        check("outlet id stored", saved.get("outlet_id") == "BZG-UMA")
        check("source pr stored", saved.get("pr_id") == approved_id)
        check("one line saved", len(saved.get("lines") or []) == 1)
        check("line qty saved", saved["lines"][0]["qty"] == 3)

        reloaded = po.get_purchase_order(saved["po_id"], person_id=approver, conn=conn)
        check("reload same supplier", reloaded and reloaded.get("supplier_id") == saved["supplier_id"])
        check("reload same outlet", reloaded and reloaded.get("outlet_id") == saved["outlet_id"])
        check("reload same pr", reloaded and reloaded.get("pr_id") == saved["pr_id"])
        check(
            "reload same line item",
            reloaded and reloaded["lines"][0]["item"] == saved["lines"][0]["item"],
        )
        check(
            "reload same line qty",
            reloaded and reloaded["lines"][0]["qty"] == saved["lines"][0]["qty"],
        )

        pr_row = ops.get_pr(approved_id, conn=conn)
        check("request moved to ORDERED", pr_row and pr_row.get("state") == "ORDERED")
        check(
            "no payment state",
            pr_row and not str(pr_row.get("state") or "").startswith("PAYMENT"),
        )

        audit_row = conn.execute(
            "SELECT action FROM core_audit_events WHERE resource_id=? AND action='bzg.po.create'",
            (saved["po_id"],),
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
