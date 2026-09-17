#!/usr/bin/env python3
"""011 Audit / Evidence Spine — idempotent Beta-only migration.

Append-only core_audit_events + Matt-only audit.event.read.
No admin UI / event bus / hash-chain / production paths.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "011_audit_evidence_spine.sql"
MIGRATION_ID = "011_audit_evidence_spine"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

PERM_ID = "PERM-AUDIT-EVENT-READ"
PERM_CODE = "audit.event.read"
ROLE_MATT = "ROLE-MATT"


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
            (
                PERM_ID,
                PERM_CODE,
                "audit.event",
                "read",
                "Read audit / evidence spine events (Owner / Matt only)",
                ts,
                ts,
            ),
        )

        # Matt / Owner only — do not grant other roles.
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect=excluded.effect,
              updated_at=excluded.updated_at
            """,
            (ROLE_MATT, PERM_ID, ts, ts),
        )

        # Ensure non-Matt roles do not retain a grant if re-run after a bad seed.
        conn.execute(
            """
            DELETE FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (PERM_ID, ROLE_MATT),
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_events = conn.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0]
        matt_grant = conn.execute(
            """
            SELECT effect FROM org_role_permissions
            WHERE role_id=? AND permission_id=?
            """,
            (ROLE_MATT, PERM_ID),
        ).fetchone()
        other_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (PERM_ID, ROLE_MATT),
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
                    f"Audit evidence spine; events={n_events}; "
                    f"matt_grant={matt_grant[0] if matt_grant else None}; "
                    f"other_grants={other_grants}; no hash-chain; no admin UI"
                ),
            ),
        )
        conn.commit()

        print(f"  core_audit_events={n_events}")
        print(f"  {PERM_CODE} → {ROLE_MATT} effect={matt_grant[0] if matt_grant else None}")
        print(f"  other_role_grants={other_grants}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if other_grants != 0:
            print("WARN: audit.event.read granted to non-Matt roles", file=sys.stderr)
            return 2
        if not matt_grant or matt_grant[0] != "ALLOW":
            print("WARN: Matt grant missing", file=sys.stderr)
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
