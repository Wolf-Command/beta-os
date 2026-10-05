#!/usr/bin/env python3
"""PETTY-CASH-RECORD-OUT-1 — petty_cash.record_out for Captains+ (Beta only).

Decision served: CAPTAIN-PETTY-CASH-OUT-2026-10-04.
Adds PERM-PETTY-CASH-RECORD-OUT. Grants to Captain and above — NOT Cashier/CLOSER.
Does not modify closes, petty movements, or production. staff_ready stays false.
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
MIGRATION_ID = "petty_cash_record_out_1"
PACK = "PETTY-CASH-RECORD-OUT-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PERM_ID = "PERM-PETTY-CASH-RECORD-OUT"
PERM_CODE = "petty_cash.record_out"

GRANT_ROLES = (
    "ROLE-BZG-CAPTAIN",
    "ROLE-BZG-HFB",
    "ROLE-BZG-FB-OPS-LEAD",
    "ROLE-MATT",
    "ROLE-OWNER",
)
DENY_ROLES = (
    "ROLE-BZG-CASHIER",
    "ROLE-BZG-CLOSER",
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


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-petty-cash-record-out-1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status,
              created_at, updated_at
            ) VALUES (?, ?, 'petty_cash', 'record_out',
                      'Record petty cash OUT from till (Captain+; assignment-scoped)',
                      'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              resource=excluded.resource,
              action=excluded.action,
              description=excluded.description,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (PERM_ID, PERM_CODE, ts, ts),
        )

        granted: list[str] = []
        for role_id in GRANT_ROLES:
            role = conn.execute(
                "SELECT role_id FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone()
            if not role:
                continue
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, PERM_ID, ts, ts),
            )
            granted.append(role_id)

        for role_id in DENY_ROLES:
            row = conn.execute(
                """
                SELECT effect FROM org_role_permissions
                WHERE role_id=? AND permission_id=?
                """,
                (role_id, PERM_ID),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    DELETE FROM org_role_permissions
                    WHERE role_id=? AND permission_id=?
                    """,
                    (role_id, PERM_ID),
                )

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
            (MIGRATION_ID, ts, f"{PACK}; Captain+ only; Cashier/CLOSER denied"),
        )
        conn.commit()

        return {
            "migration_id": MIGRATION_ID,
            "pack": PACK,
            "ran_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "permission_code": PERM_CODE,
            "granted_roles": granted,
            "denied_roles": list(DENY_ROLES),
            "staff_ready": False,
            "human_commissioned": False,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
    print("RESULT: PASS")
