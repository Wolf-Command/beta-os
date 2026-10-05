#!/usr/bin/env python3
"""P2P-PAYMENT-RECORD-1 — payment record table + bzg.pay.record permission (Beta only).

Idempotent bzg_ops_payment_records. staff_ready / human_commissioned stay false.
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

from core import bzg_payment_record as pay  # noqa: E402
from core import bzg_p2p_grants as grants  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "bzg_p2p_payment_record1_20261005"
PACK = pay.PACK
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")
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


def _count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.OperationalError:
        return -1


def _forbidden_grants(conn: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for code in ("payment.execute", "payment.approve"):
        row = conn.execute(
            """
            SELECT COUNT(*) FROM org_permissions p
            JOIN org_role_permissions rp ON p.permission_id=rp.permission_id
            WHERE p.code=? AND rp.effect='ALLOW'
            """,
            (code,),
        ).fetchone()
        out[code] = int(row[0]) if row else 0
    return out


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-p2p-payment-record1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        before = {
            "bzg_ops_payment_records": _count(conn, "bzg_ops_payment_records"),
            "bzg_ops_ready_to_pay": _count(conn, "bzg_ops_ready_to_pay"),
            "forbidden_grants": _forbidden_grants(conn),
        }
        conn.execute("PRAGMA foreign_keys=ON")
        added_tables = pay.ensure_payment_record_schema(conn)

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
            (
                pay.PERM_PAY_RECORD_ID,
                pay.PERM_PAY_RECORD,
                "pay_record",
                "Record an outside-Wolf payment against a Ready-to-Pay bill",
                ts,
                ts,
            ),
        )

        granted: list[str] = []
        grant_note = "skipped: P2P_PERMISSION_MATRIX via grant_repair1"
        if not COPY_SEED_GRANTS_DISABLED:
            grants.apply_p2p_grant_matrix(conn, ts)
            granted = grants.P2P_PERMISSION_MATRIX.get(pay.PERM_PAY_RECORD, [])
            grant_note = "applied P2P_PERMISSION_MATRIX"

        conn.commit()
        after = {
            "bzg_ops_payment_records": _count(conn, "bzg_ops_payment_records"),
            "bzg_ops_ready_to_pay": _count(conn, "bzg_ops_ready_to_pay"),
            "forbidden_grants": _forbidden_grants(conn),
        }
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "added_tables": added_tables,
            "tables_reused": ["bzg_ops_ready_to_pay", "bzg_ops_ap_ready"],
            "tables_created": added_tables,
            "permissions": [pay.PERM_PAY_RECORD],
            "grant_copy_seed": grant_note,
            "granted_roles": list(granted),
            "before_counts": before,
            "after_counts": after,
            "staff_ready": False,
            "human_commissioned": False,
            "zayen_ready": False,
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
