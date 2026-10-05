#!/usr/bin/env python3
"""HEAD-CHEF-REVOKE-WORK-UPDATE-1 — Head Chef denied work.update cash gates.

Temp sqlite only — never copies catalog/content_library.sqlite.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"

from core import rbac  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402

PASS = 0
FAIL = 0
TS = "2026-10-04T12:00:00+08:00"
TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}

ROLE_HEAD = "ROLE-BZG-HEAD-CHEF"
ROLE_CAPTAIN = "ROLE-BZG-CAPTAIN"
PERS_HEAD = "PERS-TEST-HEAD-CHEF"
PERS_CAPTAIN = "PERS-TEST-CAPTAIN"
ASG_HEAD = "ASG-TEST-HEAD-CHEF"
ASG_CAPTAIN = "ASG-TEST-CAPTAIN"
SCOPE_FB = "SCOPE-BZG-FB"

HEAD_GRANTS = (
    "recipe.read",
    "recipe.create",
    "recipe.edit",
    "recipe.cost.read",
    "recipe.exceptions.read",
    "ingredient.read",
    "menu.price.read",
    "supplier.product.read",
    "work.read",
    "work.create",
    "work.complete",
    "evidence.record.read",
    "evidence.record.submit",
    "approval.request",
)
CAPTAIN_GRANTS = ("work.update", "work.read", "work.complete")


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _migrations_sql() -> str:
    parts = []
    for name in (
        "005_org_registry.sql",
        "006_person_auth_identity.sql",
        "007_role_position_assignment.sql",
        "008_assignment_scope.sql",
        "009_rbac_permissions.sql",
    ):
        parts.append((ROOT / "scripts" / "migrations" / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


def _perm_id(code: str) -> str:
    return "PERM-" + code.upper().replace(".", "-")


def _ensure_role(conn: sqlite3.Connection, role_id: str) -> None:
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, ?, 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (role_id, role_id, TS, TS),
    )


def _grant_role(conn: sqlite3.Connection, role_id: str, codes: tuple[str, ...]) -> None:
    _ensure_role(conn, role_id)
    for code in codes:
        pid = _perm_id(code)
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO NOTHING
            """,
            (pid, code, code.split(".")[0], code.split(".")[-1], code, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (role_id, pid, TS, TS),
        )


def _seat(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    role_id: str,
    position_id: str,
    assignment_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        """,
        (person_id, person_id, TS, TS),
    )
    _ensure_role(conn, role_id)
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, 'ENT-BZG', NULL, NULL, 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
        """,
        (position_id, role_id, position_id, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (assignment_id, person_id, position_id, TS, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
        """,
        (assignment_id, SCOPE_FB, TS, TS, TS),
    )


def bootstrap_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_migrations_sql())
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable,
          created_at, updated_at
        ) VALUES ('ENT-BZG', 'BZG', 'BZG', 'OPERATING', 'ACTIVE', 1, ?, ?)
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_brands (
          brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
        ) VALUES ('BZG-UMA', 'ENT-BZG', 'Uma Blu', 'VENUE', 'ACTIVE', ?, ?)
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_departments (
          department_id, entity_id, ownership, display_name, status, created_at, updated_at
        ) VALUES ('DEPT-BZG-FB', 'ENT-BZG', 'ENTITY', 'F&B', 'ACTIVE', ?, ?)
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'entity', 'BZG F&B', 'ACTIVE', ?, ?)
        """,
        (SCOPE_FB, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', 'ENT-BZG', ?)
        """,
        (SCOPE_FB, TS),
    )
    _grant_role(conn, ROLE_HEAD, HEAD_GRANTS)
    _grant_role(conn, ROLE_CAPTAIN, CAPTAIN_GRANTS)
    _seat(
        conn,
        person_id=PERS_HEAD,
        role_id=ROLE_HEAD,
        position_id="POS-TEST-HEAD-CHEF",
        assignment_id=ASG_HEAD,
    )
    _seat(
        conn,
        person_id=PERS_CAPTAIN,
        role_id=ROLE_CAPTAIN,
        position_id="POS-TEST-CAPTAIN",
        assignment_id=ASG_CAPTAIN,
    )
    conn.commit()
    return conn


def patch_catalog(db_path: Path) -> None:
    ops.CATALOG_DB = db_path
    rbac.CATALOG_DB = db_path


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="headchef-perm-", dir=str(ROOT / "state")))
    db_path = td / "catalog.sqlite"
    conn = bootstrap_db(db_path)
    patch_catalog(db_path)
    try:
        check(
            "Head Chef recipe.read ALLOW",
            rbac.can(PERS_HEAD, "recipe.read", TARGET, conn=conn),
        )
        check(
            "Head Chef work.update DENY",
            not rbac.can(PERS_HEAD, "work.update", TARGET, conn=conn),
        )
        check(
            "Captain work.update ALLOW",
            rbac.can(PERS_CAPTAIN, "work.update", TARGET, conn=conn),
        )

        float_denied = False
        try:
            ops.set_opening_float_ops(
                person_id=PERS_HEAD,
                amount=500000,
                business_date="2099-10-04",
                conn=conn,
                commit=False,
            )
        except ops.UmaOpsError as exc:
            float_denied = exc.code == "forbidden" and exc.http_status == 403
        check("set_opening_float_ops refused for Head Chef", float_denied)

        count_denied = False
        try:
            ops.count_petty_ops(
                person_id=PERS_HEAD,
                business_date="2099-10-04",
                counted_amount=500000,
                conn=conn,
                commit=False,
            )
        except ops.UmaOpsError as exc:
            count_denied = exc.code == "forbidden" and exc.http_status == 403
        check("count_petty_ops refused for Head Chef", count_denied)

        check(
            "Captain still passes work.update gate",
            rbac.can(PERS_CAPTAIN, "work.update", TARGET, conn=conn),
        )
    finally:
        conn.close()

    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else "RESULT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
