#!/usr/bin/env python3
"""BZG-P2P-GRANT-REPAIR-1 — explicit P2P role matrix (Beta only).

Revokes copy-from-work.complete grants and applies explicit matrix.
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

from core import bzg_p2p_grants as grants  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = "bzg_p2p_grant_repair1_20261005"
PACK = grants.PACK
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")


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
    bak = BACKUP_DIR / f"pre-bzg-p2p-grant-repair1-{stamp()}.sqlite"
    bak = premig_backup(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        revoked = grants.revoke_all_p2p_grants(conn, ts)
        granted = grants.apply_p2p_grant_matrix(conn, ts)
        conn.commit()
        result = {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "permissions": list(grants.P2P_PERMISSION_CODES),
            "revoked_count": len(revoked),
            "granted_roles": granted,
            "role_matrix": {
                code: list(roles) for code, roles in grants.P2P_PERMISSION_MATRIX.items()
            },
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
