#!/usr/bin/env python3
"""FINANCE-SWITCHER-REPAIR-2 — Matt AMG CoA/journals/ledger read grants (Beta only).

Grants read-only atrium.* permissions to ROLE-MATT so PERS-MATT can read
ENT-AMG books via ASG-MATT-OWNER-1 / SCOPE-AMG-FINANCE. Does not grant
approve/post/payment/vendor.bank.change. staff_ready / human_commissioned
stay false. No prod.
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

from core import rbac as _rbac  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "finance_switcher_repair2_20261005"
PACK = "FINANCE-SWITCHER-REPAIR-2"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

ROLE_MATT = "ROLE-MATT"
ASG_MATT_OWNER = "ASG-MATT-OWNER-1"
SCOPE_AMG_FINANCE = "SCOPE-AMG-FINANCE"
PERS_MATT = "PERS-MATT"
ENT_AMG = "ENT-AMG"

MATT_AMG_READ_PERMS = (
    "atrium.board.read",
    "atrium.coa.read",
    "atrium.ledger.read",
    "atrium.report.read",
    "atrium.journal.draft",
)

MATT_MUST_NOT_HAVE = (
    "atrium.journal.approve",
    "atrium.journal.post",
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
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


def _perm_id(conn: sqlite3.Connection, code: str) -> str:
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
        (code,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"REFUSE: missing ACTIVE permission {code}")
    return str(row[0])


def _grant(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> str:
    pid = _perm_id(conn, code)
    conn.execute(
        """
        INSERT INTO org_role_permissions (
          role_id, permission_id, effect, created_at, updated_at
        ) VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, pid, ts, ts),
    )
    return pid


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-finance-switcher-repair2-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")

        scope_row = conn.execute(
            """
            SELECT scope_id FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (ASG_MATT_OWNER, SCOPE_AMG_FINANCE),
        ).fetchone()
        if not scope_row:
            raise RuntimeError(f"REFUSE: {ASG_MATT_OWNER} missing {SCOPE_AMG_FINANCE}")

        granted: dict[str, str] = {}
        for code in MATT_AMG_READ_PERMS:
            granted[code] = _grant(conn, ROLE_MATT, code, ts)

        for code in MATT_MUST_NOT_HAVE:
            row = conn.execute(
                """
                SELECT rp.effect FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE rp.role_id=? AND p.code=? AND rp.effect='ALLOW'
                """,
                (ROLE_MATT, code),
            ).fetchone()
            if row:
                raise RuntimeError(f"REFUSE: ROLE-MATT must not have {code}")

        ctx = {"entity_id": ENT_AMG}
        for code in MATT_AMG_READ_PERMS:
            if not _rbac.can(PERS_MATT, code, ctx, conn=conn):
                raise RuntimeError(f"REFUSE: rbac.can({PERS_MATT}, {code}, ENT-AMG) false after grant")

        conn.commit()
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "matt_grant_path": {
                "role_id": ROLE_MATT,
                "assignment_id": ASG_MATT_OWNER,
                "scope_id": SCOPE_AMG_FINANCE,
                "entity_id": ENT_AMG,
                "permission_ids": granted,
            },
            "permissions_granted": list(MATT_AMG_READ_PERMS),
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
