#!/usr/bin/env python3
"""014 Delegation — idempotent Beta-only migration.

core_delegations + approval decision authority_basis_* columns + Matt-only
delegation.* permissions. Live org_authority_limits must stay 0.
Live core_delegations seeded count = 0. No dual/SoD/UI/LLM/Production.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "014_delegation.sql"
MIGRATION_ID = "014_delegation"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
ROLE_MATT = "ROLE-MATT"

PERMS = (
    ("PERM-DELEGATION-READ", "delegation.read", "delegation", "read", "Read delegations in scoped entities"),
    ("PERM-DELEGATION-CREATE", "delegation.create", "delegation", "create", "Create delegations"),
    ("PERM-DELEGATION-REVOKE", "delegation.revoke", "delegation", "revoke", "Revoke delegations"),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_approval_basis_columns(conn: sqlite3.Connection) -> None:
    """Add authority_basis_* to core_approval_decisions; keep append-only triggers."""
    cols = _column_names(conn, "core_approval_decisions")
    if "authority_basis_type" in cols and "authority_basis_delegation_id" in cols:
        return

    conn.execute("DROP TRIGGER IF EXISTS trg_core_approval_decisions_no_update")
    conn.execute("DROP TRIGGER IF EXISTS trg_core_approval_decisions_no_delete")

    conn.execute(
        """
        CREATE TABLE core_approval_decisions__dlg (
          approval_decision_id TEXT PRIMARY KEY,
          approval_request_id TEXT NOT NULL,
          decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
          decided_by_person_id TEXT NOT NULL,
          decided_by_assignment_id TEXT NULL,
          identity_assurance TEXT NULL,
          reason TEXT NULL,
          decided_at TEXT NOT NULL,
          authority_allowed INTEGER NOT NULL,
          authority_reason TEXT NULL,
          authority_matched_limit_id TEXT NULL,
          authority_basis_type TEXT NOT NULL DEFAULT 'NATIVE'
            CHECK (authority_basis_type IN ('NATIVE', 'DELEGATION')),
          authority_basis_delegation_id TEXT NULL,
          correlation_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    old_cols = _column_names(conn, "core_approval_decisions")
    base = [
        "approval_decision_id",
        "approval_request_id",
        "decision",
        "decided_by_person_id",
        "decided_by_assignment_id",
        "identity_assurance",
        "reason",
        "decided_at",
        "authority_allowed",
        "authority_reason",
        "authority_matched_limit_id",
        "correlation_id",
        "created_at",
    ]
    select_bits = []
    for c in base:
        if c in old_cols:
            select_bits.append(c)
        else:
            select_bits.append(f"NULL AS {c}")
    if "authority_basis_type" in old_cols:
        select_bits.append("authority_basis_type")
    else:
        select_bits.append("'NATIVE' AS authority_basis_type")
    if "authority_basis_delegation_id" in old_cols:
        select_bits.append("authority_basis_delegation_id")
    else:
        select_bits.append("NULL AS authority_basis_delegation_id")

    conn.execute(
        f"""
        INSERT INTO core_approval_decisions__dlg (
          approval_decision_id, approval_request_id, decision,
          decided_by_person_id, decided_by_assignment_id, identity_assurance,
          reason, decided_at, authority_allowed, authority_reason,
          authority_matched_limit_id, correlation_id, created_at,
          authority_basis_type, authority_basis_delegation_id
        )
        SELECT
          {", ".join(select_bits[:13])},
          {select_bits[13]},
          {select_bits[14]}
        FROM core_approval_decisions
        """
    )
    conn.execute("DROP TABLE core_approval_decisions")
    conn.execute("ALTER TABLE core_approval_decisions__dlg RENAME TO core_approval_decisions")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_core_approval_dec_request
          ON core_approval_decisions(approval_request_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_core_approval_dec_decider
          ON core_approval_decisions(decided_by_person_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_core_approval_dec_corr
          ON core_approval_decisions(correlation_id)
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_approval_decisions_no_update
        BEFORE UPDATE ON core_approval_decisions
        BEGIN
          SELECT RAISE(ABORT, 'core_approval_decisions is append-only');
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_approval_decisions_no_delete
        BEFORE DELETE ON core_approval_decisions
        BEGIN
          SELECT RAISE(ABORT, 'core_approval_decisions is append-only');
        END
        """
    )


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
        n_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        if n_auth != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth}",
                file=sys.stderr,
            )
            return 2

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied (core_delegations)")

        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_approval_decisions" not in tabs:
            print("REFUSE: core_approval_decisions missing (run 013 first)", file=sys.stderr)
            return 2
        _ensure_approval_basis_columns(conn)
        print("approval decision basis columns ensured")

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
        n_dlg = conn.execute("SELECT COUNT(*) FROM core_delegations").fetchone()[0]
        n_auth2 = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        matt_codes = [
            r[0]
            for r in conn.execute(
                """
                SELECT p.code FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE rp.role_id=? AND p.code LIKE 'delegation.%'
                ORDER BY p.code
                """,
                (ROLE_MATT,),
            ).fetchall()
        ]
        other_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              SELECT permission_id FROM org_permissions WHERE code LIKE 'delegation.%'
            ) AND role_id != ?
            """,
            (ROLE_MATT,),
        ).fetchone()[0]
        basis_cols = _column_names(conn, "core_approval_decisions")
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"Delegation; rows={n_dlg}; auth_limits={n_auth2}; "
                    f"matt_delegation_codes={len(matt_codes)}; other_grants={other_grants}; "
                    f"basis_cols={('authority_basis_type' in basis_cols)}; "
                    f"no redelegation/dual/SoD"
                ),
            ),
        )
        conn.commit()

        print(f"  core_delegations={n_dlg}")
        print(f"  org_authority_limits={n_auth2}")
        print(f"  Matt delegation.* grants={matt_codes}")
        print(f"  other_role_grants={other_grants}")
        print(f"  authority_basis_type_col={'authority_basis_type' in basis_cols}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if other_grants != 0:
            print("WARN: delegation.* granted to non-Matt roles", file=sys.stderr)
            return 2
        if len(matt_codes) != 3:
            print(
                f"WARN: expected 3 Matt delegation.* grants, got {len(matt_codes)}",
                file=sys.stderr,
            )
            return 2
        if n_auth2 != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth2}",
                file=sys.stderr,
            )
            return 2
        if n_dlg != 0:
            print(f"REFUSE: live core_delegations must be 0 after migrate, got {n_dlg}", file=sys.stderr)
            return 2
        if "authority_basis_type" not in basis_cols:
            print("REFUSE: authority_basis_type column missing", file=sys.stderr)
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
