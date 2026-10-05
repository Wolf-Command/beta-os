#!/usr/bin/env python3
"""BZG-P2P-PR-1 — Purchase Request vertical slice (Beta only).

Adds bzg.pr.create permission, PR requester/outlet columns, idempotent schema.
Serves God Mode GM-024 / BZG-PROCURE-TO-PAY-1 (DESIGNED — not full P2P).
staff_ready / human_commissioned stay false. No prod. No push.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import bzg_purchase_request as pr  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "bzg_p2p_pr1_20261004"
PACK = "BZG-P2P-PR-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PERM_ID = pr.PERM_PR_CREATE_ID
PERM_CODE = pr.PERM_PR_CREATE

GRANT_ROLES = (
    "ROLE-BZG-FB-OPS-LEAD",
    "ROLE-BZG-HFB",
    "ROLE-BZG-CAPTAIN",
    "ROLE-MATT",
    "ROLE-OWNER",
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
    bak = BACKUP_DIR / f"pre-bzg-p2p-pr1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        outlets.ensure_schema(conn)
        outlets.seed_registry(conn, ts)
        added_cols = pr.ensure_pr_columns(conn)

        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status,
              created_at, updated_at
            ) VALUES (?, ?, 'bzg', 'pr_create',
                      'Create BZG purchase requests (assignment + outlet scoped)',
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

        outlet_count = len(outlets.list_outlets(conn))
        if outlet_count != 7:
            raise RuntimeError(f"expected 7 outlets in registry, got {outlet_count}")

        conn.commit()
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "added_columns": added_cols,
            "permission": PERM_CODE,
            "granted_roles": granted,
            "outlet_count": outlet_count,
            "staff_ready": False,
            "human_commissioned": False,
        }
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        (RESULT_DIR / f"{PACK}-MIGRATION-{stamp()}.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        return result
    finally:
        conn.close()


def main() -> int:
    try:
        out = run()
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
