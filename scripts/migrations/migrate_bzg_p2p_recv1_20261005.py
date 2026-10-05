#!/usr/bin/env python3
"""BZG-P2P-RECV-1 — Goods receiving against saved PO (Beta only).

Idempotent bzg_ops_goods_receipts / bzg_ops_gr_lines. Reuses venue.receive when present.
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

from core import bzg_goods_receiving as gr  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "bzg_p2p_recv1_20261005"
PACK = gr.PACK
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PO_PERM = "PERM-BZG-PO-CREATE"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
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
    bak = BACKUP_DIR / f"pre-bzg-p2p-recv1-{stamp()}.sqlite"
    bak = premig_backup(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        added_tables = gr.ensure_gr_schema(conn)

        receive_code = p0.discover_receive_permission(conn)
        granted: list[str] = []
        grant_note = "skipped: P2P_PERMISSION_MATRIX via grant_repair1"
        if receive_code:
            role_rows = conn.execute(
                """
                SELECT DISTINCT rp.role_id
                FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE p.code=? AND rp.effect='ALLOW'
                """,
                (receive_code,),
            ).fetchall()
            granted = [str(r["role_id"]) for r in role_rows]
            grant_note = "reused existing venue.receive roles (no copy-seed)"
        else:
            recv_id = "PERM-BZG-RECEIVING-CREATE"
            recv_code = "bzg.receiving.create"
            conn.execute(
                """
                INSERT INTO org_permissions (
                  permission_id, code, resource, action, description, status,
                  created_at, updated_at
                ) VALUES (?, ?, 'bzg', 'receiving_create',
                          'Record BZG goods receipts against purchase orders',
                          'ACTIVE', ?, ?)
                ON CONFLICT(permission_id) DO UPDATE SET
                  code=excluded.code,
                  resource=excluded.resource,
                  action=excluded.action,
                  description=excluded.description,
                  status='ACTIVE',
                  updated_at=excluded.updated_at
                """,
                (recv_id, recv_code, ts, ts),
            )
            receive_code = recv_code
            if not COPY_SEED_GRANTS_DISABLED:
                for perm_seed in (PO_PERM, WORK_COMPLETE):
                    role_rows = conn.execute(
                        """
                        SELECT DISTINCT role_id FROM org_role_permissions
                        WHERE permission_id=? AND effect='ALLOW'
                        """,
                        (perm_seed,),
                    ).fetchall()
                    for row in role_rows:
                        role_id = str(row["role_id"])
                        conn.execute(
                            """
                            INSERT INTO org_role_permissions (
                              role_id, permission_id, effect, created_at, updated_at
                            ) VALUES (?, ?, 'ALLOW', ?, ?)
                            ON CONFLICT(role_id, permission_id) DO UPDATE SET
                              effect='ALLOW', updated_at=excluded.updated_at
                            """,
                            (role_id, recv_id, ts, ts),
                        )
                        granted.append(role_id)
                granted = sorted(set(granted))
                grant_note = "copy-seed from po.create/work.complete (legacy)"

        conn.commit()
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "added_tables": added_tables,
            "permission": receive_code,
            "grant_copy_seed": grant_note if receive_code else "n/a",
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
