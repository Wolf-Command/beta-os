#!/usr/bin/env python3
"""013 Approval Engine — idempotent Beta-only migration.

core_approval_requests + core_approval_decisions + Matt-only approval.* permissions.
0 live requests/decisions. Does NOT seed Authority Limits (must remain 0).
No dual / SoD / delegation / UI / LLM / Production paths.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "013_approval_engine.sql"
MIGRATION_ID = "013_approval_engine"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
ROLE_MATT = "ROLE-MATT"

PERMS = (
    ("PERM-APPROVAL-READ", "approval.read", "approval", "read", "Read approval requests in scoped entities"),
    ("PERM-APPROVAL-REQUEST", "approval.request", "approval", "request", "Create approval requests"),
    ("PERM-APPROVAL-DECIDE", "approval.decide", "approval", "decide", "Approve or reject pending requests"),
    ("PERM-APPROVAL-CANCEL", "approval.cancel", "approval", "cancel", "Cancel pending approval requests"),
)


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

        for perm_id, code, resource, action, desc in PERMS:
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
                (perm_id, code, resource, action, desc, ts, ts),
            )
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect=excluded.effect,
                  updated_at=excluded.updated_at
                """,
                (ROLE_MATT, perm_id, ts, ts),
            )
            conn.execute(
                """
                DELETE FROM org_role_permissions
                WHERE permission_id=? AND role_id != ?
                """,
                (perm_id, ROLE_MATT),
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_req = conn.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0]
        n_dec = conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0]
        n_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        matt_codes = [
            r[0]
            for r in conn.execute(
                """
                SELECT p.code FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE rp.role_id=? AND p.code LIKE 'approval.%'
                ORDER BY p.code
                """,
                (ROLE_MATT,),
            ).fetchall()
        ]
        other_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              SELECT permission_id FROM org_permissions WHERE code LIKE 'approval.%'
            ) AND role_id != ?
            """,
            (ROLE_MATT,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"Approval engine; requests={n_req}; decisions={n_dec}; "
                    f"auth_limits={n_auth}; matt_approval_codes={len(matt_codes)}; "
                    f"other_grants={other_grants}; no dual/SoD"
                ),
            ),
        )
        conn.commit()

        print(f"  core_approval_requests={n_req}")
        print(f"  core_approval_decisions={n_dec}")
        print(f"  org_authority_limits={n_auth}")
        print(f"  Matt approval.* grants={matt_codes}")
        print(f"  other_role_grants={other_grants}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if other_grants != 0:
            print("WARN: approval.* granted to non-Matt roles", file=sys.stderr)
            return 2
        if len(matt_codes) != 4:
            print(f"WARN: expected 4 Matt approval.* grants, got {len(matt_codes)}", file=sys.stderr)
            return 2
        if n_auth != 0:
            print(f"REFUSE: live org_authority_limits must stay 0, got {n_auth}", file=sys.stderr)
            return 2
        if n_req != 0:
            print(f"NOTE: live approval requests already present: {n_req}")
        if n_dec != 0:
            print(f"NOTE: live approval decisions already present: {n_dec}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
