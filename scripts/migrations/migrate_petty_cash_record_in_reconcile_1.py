#!/usr/bin/env python3
"""PETTY-OWNER-CASH-IN-1 — petty_cash.record_in + petty_cash.reconcile (Beta only).

Decision served: PETTY-OWNER-CASH-IN-1 Owner order 2026-10-05.
Adds PERM-PETTY-CASH-RECORD-IN and PERM-PETTY-CASH-RECONCILE.
Owner/Matt + BZG FC receive record_in and reconcile; Captain keeps record_out only.
Does not modify petty movements, closes, or production. staff_ready stays false.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "petty_cash_record_in_reconcile_1"
PACK = "PETTY-OWNER-CASH-IN-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PERM_IN_ID = "PERM-PETTY-CASH-RECORD-IN"
PERM_IN_CODE = "petty_cash.record_in"
PERM_RECON_ID = "PERM-PETTY-CASH-RECONCILE"
PERM_RECON_CODE = "petty_cash.reconcile"

OWNER_FINANCE_ROLES = (
    "ROLE-MATT",
    "ROLE-OWNER",
    "ROLE-BZG-FINANCIAL-CONTROLLER",
)
CAPTAIN_OUT_ONLY = (
    "ROLE-BZG-CAPTAIN",
    "ROLE-BZG-HFB",
    "ROLE-BZG-FB-OPS-LEAD",
)
DENY_IN_RECON = (
    "ROLE-BZG-CAPTAIN",
    "ROLE-BZG-CASHIER",
    "ROLE-BZG-CLOSER",
    "ROLE-BZG-HFB",
    "ROLE-BZG-FB-OPS-LEAD",
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _refuse_path(db_path: Path) -> str | None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            return frag
    if "beta-os" not in s:
        return "not-beta-os"
    return None


def _upsert_permission(
    conn: sqlite3.Connection,
    perm_id: str,
    code: str,
    action: str,
    description: str,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status,
          created_at, updated_at
        ) VALUES (?, ?, 'petty_cash', ?,
                  ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code,
          resource=excluded.resource,
          action=excluded.action,
          description=excluded.description,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (perm_id, code, action, description, ts, ts),
    )


def _grant(conn: sqlite3.Connection, role_id: str, perm_id: str, ts: str) -> bool:
    role = conn.execute(
        "SELECT role_id FROM org_roles WHERE role_id=?", (role_id,)
    ).fetchone()
    if not role:
        return False
    conn.execute(
        """
        INSERT INTO org_role_permissions (
          role_id, permission_id, effect, created_at, updated_at
        ) VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, perm_id, ts, ts),
    )
    return True


def _deny_remove(conn: sqlite3.Connection, role_id: str, perm_id: str) -> None:
    row = conn.execute(
        """
        SELECT effect FROM org_role_permissions
        WHERE role_id=? AND permission_id=?
        """,
        (role_id, perm_id),
    ).fetchone()
    if row is not None:
        conn.execute(
            "DELETE FROM org_role_permissions WHERE role_id=? AND permission_id=?",
            (role_id, perm_id),
        )


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-petty-cash-in-reconcile-1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        _upsert_permission(
            conn,
            PERM_IN_ID,
            PERM_IN_CODE,
            "record_in",
            "Record petty cash IN / top-up (Owner + authorised Finance; assignment-scoped)",
            ts,
        )
        _upsert_permission(
            conn,
            PERM_RECON_ID,
            PERM_RECON_CODE,
            "reconcile",
            "Physical cash count / reconciliation (Owner + authorised Finance)",
            ts,
        )

        granted_in: list[str] = []
        granted_recon: list[str] = []
        for role_id in OWNER_FINANCE_ROLES:
            if _grant(conn, role_id, PERM_IN_ID, ts):
                granted_in.append(role_id)
            if _grant(conn, role_id, PERM_RECON_ID, ts):
                granted_recon.append(role_id)
            # Finance FC also needs record_out if not already granted.
            if role_id == "ROLE-BZG-FINANCIAL-CONTROLLER":
                _grant(conn, role_id, "PERM-PETTY-CASH-RECORD-OUT", ts)

        for role_id in DENY_IN_RECON:
            _deny_remove(conn, role_id, PERM_IN_ID)
            _deny_remove(conn, role_id, PERM_RECON_ID)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, f"{PACK}; Owner+Finance IN/reconcile; Captain OUT only"),
        )
        conn.commit()

        return {
            "migration_id": MIGRATION_ID,
            "pack": PACK,
            "ran_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "permission_record_in": PERM_IN_CODE,
            "permission_reconcile": PERM_RECON_CODE,
            "granted_record_in_roles": granted_in,
            "granted_reconcile_roles": granted_recon,
            "captain_out_only_roles": list(CAPTAIN_OUT_ONLY),
            "denied_in_reconcile_roles": list(DENY_IN_RECON),
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
    print("RESULT: PASS")
