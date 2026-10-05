#!/usr/bin/env python3
"""BZG-P2P-PR-1 — Purchase Request vertical slice. Schema-only temp sqlite.

Never copies catalog/content_library.sqlite. Protected closes not touched.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
BILLS_HTML = ROOT / "dashboards" / "bzg-uma-blu-bills.html"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
TS = "2026-10-04T18:00:00+08:00"
PERM_ID = "PERM-BZG-PR-CREATE"
PERM_CODE = "bzg.pr.create"

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


def _ensure_approval_columns(conn: sqlite3.Connection) -> None:
    cols = {
        str(r[1])
        for r in conn.execute("PRAGMA table_info(core_approval_requests)").fetchall()
    }
    for name, decl in (
        ("required_decision_count", "INTEGER NOT NULL DEFAULT 1"),
        ("governing_policy_id", "TEXT"),
        ("governing_policy_version", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE core_approval_requests ADD COLUMN {name} {decl}")


def seed_pr_permission(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, 'bzg', 'pr_create', 'test seed', 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (PERM_ID, PERM_CODE, TS, TS),
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
        VALUES ('ROLE-BZG-NO-PR', 'No PR', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
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
        ) VALUES ('POS-BZG-NO-PR-1', 'ROLE-BZG-NO-PR', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'No PR seat', 'ACTIVE', 1.0, ?, ?)
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
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES ('PERM-WORK-COMPLETE', 'work.complete', 'work', 'complete', 'test', 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-BZG-FB-OPS-LEAD', ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
        """,
        (PERM_ID, TS, TS),
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


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"

    html = BILLS_HTML.read_text(encoding="utf-8")
    check("bills page has outlet select", 'id="outlet"' in html)
    check("bills page posts outlet_id", "outlet_id:" in html)
    check("bills page has unit field", 'id="unit"' in html)
    create_panel = html.split('id="createPanel"')[1].split("</form>")[0] if 'id="createPanel"' in html else ""
    check(
        "no hardcoded person name in create panel",
        "Hariyanto" not in create_panel and "Devi" not in create_panel,
    )

    td = tempfile.mkdtemp(prefix="bzg-pr1-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        from core import approvals as appr
        from core import audit as au
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_request as pr
        from core import rbac as rb
        from core import scope as sc
        from core import uma_ops_console as ops
        from core import work_items as wi

        for mod in (ops, pr, rb, au, sc, wi, outlets, appr):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        _ensure_approval_columns(conn)
        ops.ensure_schema(conn)
        outlets.ensure_schema(conn)
        outlets.seed_registry(conn, TS)
        pr.ensure_pr_columns(conn)
        seed_pr_permission(conn)
        operator = seed_operator(conn, "PERS-TEST-OPS", "ASG-TEST-OPS-1", "POS-BZG-FB-OPS-1")
        denied = seed_operator(conn, "PERS-TEST-NOPE", "ASG-TEST-NOPE-1", "POS-BZG-NO-PR-1")
        conn.commit()

        check("seven outlets in registry", len(outlets.list_outlets(conn)) == 7)

        try:
            pr.create_purchase_request(
                person_id="",
                outlet_id="BZG-UMA",
                purpose="test",
                lines=[{"item": "Rice", "qty": 1, "unit": "kg"}],
                conn=conn,
                commit=False,
            )
            check("unauthenticated denied", False, "should raise")
        except pr.PrError as exc:
            check("unauthenticated denied", exc.code == "unauthenticated", str(exc))

        try:
            pr.create_purchase_request(
                person_id=operator,
                outlet_id="",
                purpose="test",
                lines=[{"item": "Rice", "qty": 1}],
                conn=conn,
                commit=False,
            )
            check("missing outlet validation", False, "should raise")
        except pr.PrError as exc:
            check("missing outlet validation", exc.code == "missing_outlet", str(exc))

        try:
            pr.create_purchase_request(
                person_id=denied,
                outlet_id="BZG-UMA",
                purpose="test",
                lines=[{"item": "Rice", "qty": 1}],
                conn=conn,
                commit=False,
            )
            check("deny without scope/permission", False, "should raise")
        except pr.PrError as exc:
            check("deny without scope/permission", exc.code == "forbidden", str(exc))

        created = pr.create_purchase_request(
            person_id=operator,
            outlet_id="BZG-UMA",
            purpose="Kitchen supplies for service",
            supplier_name="Test Vendor",
            lines=[{"item": "Cooking oil", "qty": 2, "unit": "L"}],
            submitted=False,
            conn=conn,
            commit=True,
        )
        check("authenticated create succeeds", created.get("pr_id"))
        check("outlet stored", created.get("outlet_id") == "BZG-UMA")
        check("requester person bound", created.get("requester_person_id") == operator)
        check("assignment bound", created.get("requester_assignment_id") == "ASG-TEST-OPS-1")
        check("draft state", created.get("state") == "DRAFT")
        check("one line stored", len(created.get("lines") or []) == 1)

        audit_row = conn.execute(
            """
            SELECT action FROM core_audit_events
            WHERE resource_id=? AND action='bzg.pr.create'
            """,
            (created["pr_id"],),
        ).fetchone()
        check("audit row for create", audit_row is not None)

        try:
            pr.create_purchase_request(
                person_id=operator,
                outlet_id="OU-BZG-RAIN-POOL",
                purpose="Pool bar restock",
                lines=[{"item": "Napkins", "qty": 5, "unit": "pack"}],
                conn=conn,
                commit=False,
            )
            check("outlet outside scope denied", False, "should raise")
        except pr.PrError as exc:
            check("outlet outside scope denied", exc.code == "forbidden", str(exc))

        submitted = pr.create_purchase_request(
            person_id=operator,
            outlet_id="BZG-UMA",
            purpose="Uma restock",
            lines=[{"item": "Napkins", "qty": 5, "unit": "pack"}],
            submitted=True,
            conn=conn,
            commit=True,
        )
        check("submitted state", submitted.get("state") == "REQUESTED")
        check("submitted_at set", bool(submitted.get("submitted_at")))
        appr = conn.execute(
            """
            SELECT status FROM core_approval_requests WHERE source_id=?
            """,
            (submitted["pr_id"],),
        ).fetchone()
        check("approval enqueued on submit", appr is not None and appr[0] == "PENDING")

        live = ROOT / "catalog" / "content_library.sqlite"
        live_conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
        try:
            row = live_conn.execute(
                "SELECT close_id, state FROM venue_daily_closes WHERE close_id=?",
                (PROTECTED_CLOSE,),
            ).fetchone()
            check("protected close still exists on live catalog", row is not None, str(row))
        finally:
            live_conn.close()

        conn.rollback()
    finally:
        pass

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
