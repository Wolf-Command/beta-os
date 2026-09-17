#!/usr/bin/env python3
"""017 SoD Constraints — idempotent Beta-only migration.

Creates core_sod_constraints + core_sod_participation.
Seeds sod.constraint.read / .manage permission codes
(Matt read grant only; no manage grant; no live SoD rows).
Live org_authority_limits / governance policies / SoD must stay 0.
Backs up Beta DB before apply and prints SHA-256.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "017_sod_constraints.sql"
MIGRATION_ID = "017_sod_constraints"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"
ROLE_MATT = "ROLE-MATT"

PERMS = (
    (
        "PERM-SOD-CONSTRAINT-READ",
        "sod.constraint.read",
        "sod",
        "read",
        "Read segregation-of-duties constraints in scoped entities",
    ),
    (
        "PERM-SOD-CONSTRAINT-MANAGE",
        "sod.constraint.manage",
        "sod",
        "manage",
        "Manage SoD constraints (Matt/test only; no live grant)",
    ),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup(db_path: Path) -> tuple[Path, str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-sod-constraints-{stamp()}.sqlite"
    shutil.copy2(db_path, dest)
    digest = _sha256(dest)
    sha_path = (
        ROOT
        / "state"
        / f"sod-constraints-backup-{dest.stem.replace('pre-sod-constraints-', '')}.sha256"
    )
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def _seed_permission_codes(conn: sqlite3.Connection, ts: str) -> None:
    """Catalog codes only. Matt gets read; manage stays ungranted on live."""
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
            DELETE FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (perm_id, ROLE_MATT),
        )

    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, 'PERM-SOD-CONSTRAINT-READ', 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect=excluded.effect,
          updated_at=excluded.updated_at
        """,
        (ROLE_MATT, ts, ts),
    )
    conn.execute(
        """
        DELETE FROM org_role_permissions
        WHERE permission_id='PERM-SOD-CONSTRAINT-MANAGE'
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
    is_live = db_path == (ROOT / "catalog" / "content_library.sqlite").resolve()
    if is_live:
        probe = sqlite3.connect(str(db_path))
        try:
            tabs = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            need_backup = True
            mig_done = (
                probe.execute(
                    "SELECT 1 FROM schema_migrations WHERE id=? LIMIT 1",
                    (MIGRATION_ID,),
                ).fetchone()
                if "schema_migrations" in tabs
                else None
            )
            if (
                "core_sod_constraints" in tabs
                and "core_sod_participation" in tabs
                and mig_done
            ):
                need_backup = False
            if need_backup:
                _backup(db_path)
        finally:
            probe.close()

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

        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied (core_sod_constraints + core_sod_participation)")

        if "org_permissions" in tabs:
            _seed_permission_codes(conn, ts)
            print("sod.constraint.* permission codes seeded (no manage grant)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_sod = conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
        n_part = conn.execute("SELECT COUNT(*) FROM core_sod_participation").fetchone()[0]
        n_auth2 = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        n_pol = (
            conn.execute("SELECT COUNT(*) FROM core_governance_policies").fetchone()[0]
            if "core_governance_policies" in tabs
            else 0
        )
        manage_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id='PERM-SOD-CONSTRAINT-MANAGE'
            """
        ).fetchone()[0]
        read_matt = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE role_id=? AND permission_id='PERM-SOD-CONSTRAINT-READ'
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
                    f"SoD constraints; sod={n_sod}; participation={n_part}; "
                    f"auth_limits={n_auth2}; gov_policies={n_pol}; "
                    f"read_matt={read_matt}; manage_grants={manage_grants}; no live SoD seed"
                ),
            ),
        )
        conn.commit()

        print(f"  core_sod_constraints={n_sod}")
        print(f"  core_sod_participation={n_part}")
        print(f"  org_authority_limits={n_auth2}")
        print(f"  core_governance_policies={n_pol}")
        print(f"  matt_sod_read_grant={read_matt}")
        print(f"  manage_grants={manage_grants}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if n_auth2 != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth2}",
                file=sys.stderr,
            )
            return 2
        if n_sod != 0 and is_live:
            print(
                f"REFUSE: live SoD constraints must stay 0, got {n_sod}",
                file=sys.stderr,
            )
            return 2
        if n_pol != 0 and is_live:
            print(
                f"REFUSE: live governance policies must stay 0, got {n_pol}",
                file=sys.stderr,
            )
            return 2
        if manage_grants != 0:
            print(
                f"REFUSE: sod.constraint.manage must have 0 live grants, got {manage_grants}",
                file=sys.stderr,
            )
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
