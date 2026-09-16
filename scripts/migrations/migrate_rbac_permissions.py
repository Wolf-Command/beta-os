#!/usr/bin/env python3
"""009 RBAC / Permissions — idempotent Beta-only migration.

Seeds canonical permissions + Role grants from evidence (legacy Content
permissions + known Assignments). Does NOT build Authority Limits or real auth.
Does NOT delete transitional email `permissions` rows.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "009_rbac_permissions.sql"
MIGRATION_ID = "009_rbac_permissions"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

PERMS = [
    # (id, code, resource, action, description)
    ("PERM-CONTENT-PLAN-READ", "content.plan.read", "content.plan", "read", "View content plans"),
    ("PERM-CONTENT-PLAN-CREATE", "content.plan.create", "content.plan", "create", "Create content plans"),
    ("PERM-CONTENT-PLAN-EDIT", "content.plan.edit", "content.plan", "edit", "Edit content plans"),
    ("PERM-CONTENT-PLAN-APPROVE", "content.plan.approve", "content.plan", "approve", "Approve content plans"),
    ("PERM-CONTENT-PROD-UPDATE", "content.production.update", "content.production", "update", "Update production status"),
    ("PERM-CONTENT-ASSET-UPLOAD", "content.asset.upload", "content.asset", "upload", "Upload content assets"),
    ("PERM-CONTENT-INTEL-USE", "content.intelligence.use", "content.intelligence", "use", "Use Wolf Intelligence helpers"),
    ("PERM-ORG-ENTITY-READ", "organisation.entity.read", "organisation.entity", "read", "Read org entities/brands/locations/depts"),
    ("PERM-ORG-PERSON-READ", "organisation.person.read", "organisation.person", "read", "Read org persons (minimal fields)"),
    ("PERM-ORG-ROLE-READ", "organisation.role.read", "organisation.role", "read", "Read org roles/positions/assignments"),
    ("PERM-ORG-SCOPE-READ", "organisation.scope.read", "organisation.scope", "read", "Read org scopes"),
]

LEGACY_MAP = {
    "can_view_plan": "PERM-CONTENT-PLAN-READ",
    "can_create_plan": "PERM-CONTENT-PLAN-CREATE",
    "can_edit_plan": "PERM-CONTENT-PLAN-EDIT",
    "can_approve_plan": "PERM-CONTENT-PLAN-APPROVE",
    "can_update_production": "PERM-CONTENT-PROD-UPDATE",
    "can_upload": "PERM-CONTENT-ASSET-UPLOAD",
    "can_use_wolf_intelligence": "PERM-CONTENT-INTEL-USE",
}

# Role grants from evidence (legacy email grants + Assignment roles)
# ROLE-MATT / ROLE-CONTENT-MGMT: full content set + org reads
# ROLE-GGV-EDIT / ROLE-CONTENT-CREW: no create/approve
CONTENT_FULL = [
    "PERM-CONTENT-PLAN-READ", "PERM-CONTENT-PLAN-CREATE", "PERM-CONTENT-PLAN-EDIT",
    "PERM-CONTENT-PLAN-APPROVE", "PERM-CONTENT-PROD-UPDATE", "PERM-CONTENT-ASSET-UPLOAD",
    "PERM-CONTENT-INTEL-USE",
]
CONTENT_CREW = [
    "PERM-CONTENT-PLAN-READ", "PERM-CONTENT-PLAN-EDIT", "PERM-CONTENT-PROD-UPDATE",
    "PERM-CONTENT-ASSET-UPLOAD", "PERM-CONTENT-INTEL-USE",
]
ORG_READS = [
    "PERM-ORG-ENTITY-READ", "PERM-ORG-PERSON-READ", "PERM-ORG-ROLE-READ", "PERM-ORG-SCOPE-READ",
]

ROLE_GRANTS = {
    "ROLE-MATT": CONTENT_FULL + ORG_READS,
    "ROLE-CONTENT-MGMT": CONTENT_FULL + ["PERM-ORG-ENTITY-READ", "PERM-ORG-SCOPE-READ", "PERM-ORG-ROLE-READ"],
    "ROLE-GGV-EDIT": CONTENT_CREW + ["PERM-ORG-ENTITY-READ", "PERM-ORG-SCOPE-READ"],
    "ROLE-CONTENT-CREW": CONTENT_CREW + ["PERM-ORG-ENTITY-READ", "PERM-ORG-SCOPE-READ"],
    # AMG/BZG/ENG roles exist but have no Beta Assignments — no grants yet (deny default)
}


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        for pid, code, resource, action, desc in PERMS:
            conn.execute(
                """
                INSERT INTO org_permissions (
                  permission_id, code, resource, action, description, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT(permission_id) DO UPDATE SET
                  code=excluded.code,
                  resource=excluded.resource,
                  action=excluded.action,
                  description=excluded.description,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (pid, code, resource, action, desc, ts, ts),
            )

        for legacy, pid in LEGACY_MAP.items():
            conn.execute(
                """
                INSERT INTO org_permission_legacy_map (legacy_code, permission_id, note, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(legacy_code) DO UPDATE SET
                  permission_id=excluded.permission_id,
                  note=excluded.note
                """,
                (legacy, pid, "TRANSITIONAL Content Machine map", ts),
            )

        for role_id, pids in ROLE_GRANTS.items():
            for pid in pids:
                conn.execute(
                    """
                    INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                    VALUES (?, ?, 'ALLOW', ?, ?)
                    ON CONFLICT(role_id, permission_id) DO UPDATE SET
                      effect=excluded.effect,
                      updated_at=excluded.updated_at
                    """,
                    (role_id, pid, ts, ts),
                )

        # Label legacy permissions table note via schema_migrations only — do not alter rows
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        legacy_n = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                f"RBAC; legacy permissions rows remain TRANSITIONAL n={legacy_n}; no Authority Limits",
            ),
        )
        conn.commit()

        for t in ("org_permissions", "org_role_permissions", "org_permission_legacy_map", "permissions"):
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}={n}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
