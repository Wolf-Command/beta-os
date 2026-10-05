#!/usr/bin/env python3
"""BZG-P2P-READY-TO-PAY-1 — ready-to-pay table + bzg.pay.* permissions (Beta only).

Idempotent bzg_ops_ready_to_pay. staff_ready / human_commissioned stay false.
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

from core import bzg_ready_to_pay as rtp  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "bzg_p2p_ready_to_pay1_20261005"
PACK = rtp.PACK
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

LIST_PERM_ID = rtp.PERM_PAY_LIST_ID
LIST_PERM_CODE = rtp.PERM_PAY_LIST
MARK_PERM_ID = rtp.PERM_PAY_MARK_ID
MARK_PERM_CODE = rtp.PERM_PAY_MARK
PERM_AP_MARK = "PERM-BZG-AP-MARK-READY"
# Grant authority: migrate_bzg_p2p_grant_repair1_20261005.py + P2P_PERMISSION_MATRIX.
COPY_SEED_GRANTS_DISABLED = True


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
    bak = BACKUP_DIR / f"pre-bzg-p2p-ready-to-pay1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        added_tables = rtp.ensure_ready_to_pay_schema(conn)

        for perm_id, code, action, desc in (
            (
                LIST_PERM_ID,
                LIST_PERM_CODE,
                "pay_list_ready",
                "View BZG Ready to Pay list — matched bills allowed to be paid later",
            ),
            (
                MARK_PERM_ID,
                MARK_PERM_CODE,
                "pay_mark_ready",
                "Mark an AP-ready matched bill allowed to be paid later",
            ),
        ):
            conn.execute(
                """
                INSERT INTO org_permissions (
                  permission_id, code, resource, action, description, status,
                  created_at, updated_at
                ) VALUES (?, ?, 'bzg', ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT(permission_id) DO UPDATE SET
                  code=excluded.code,
                  resource=excluded.resource,
                  action=excluded.action,
                  description=excluded.description,
                  status='ACTIVE',
                  updated_at=excluded.updated_at
                """,
                (perm_id, code, action, desc, ts, ts),
            )

        granted: list[str] = []
        grant_note = "skipped: P2P_PERMISSION_MATRIX via grant_repair1"
        if not COPY_SEED_GRANTS_DISABLED:
            role_rows = conn.execute(
                """
                SELECT DISTINCT role_id FROM org_role_permissions
                WHERE permission_id=? AND effect='ALLOW'
                """,
                (PERM_AP_MARK,),
            ).fetchall()
            for row in role_rows:
                role_id = str(row["role_id"])
                for perm_id in (LIST_PERM_ID, MARK_PERM_ID):
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
                granted.append(role_id)
            granted = sorted(set(granted))
            grant_note = "copy-seed from ap.mark_ready (legacy)"

        conn.commit()
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "added_tables": added_tables,
            "tables_reused": ["bzg_ops_ap_ready", "bzg_ops_supplier_bills"],
            "tables_created": added_tables,
            "permissions": [LIST_PERM_CODE, MARK_PERM_CODE],
            "grant_copy_seed": grant_note,
            "granted_roles": granted,
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
