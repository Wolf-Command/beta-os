#!/usr/bin/env python3
"""032 BZG Daily Close Multi-EDC Vision — idempotent Beta-only migration.

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner order
BZG-DAILY-CLOSE-MULTI-EDC-VISION-20261002.

Schema for 0..N EDC receipts (separate EDC card + QRIS), ESB closing receipt
dual-source, vision draft audit. Does NOT invent terminal TIDs or seed ACTIVE
variance policies. Does NOT flip staff_ready / human_commissioned.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "032_bzg_daily_close_multi_edc_vision.sql"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "032_bzg_daily_close_multi_edc_vision"
PACK = "BZG-DAILY-CLOSE-MULTI-EDC-VISION-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

EVIDENCE_TYPES = (
    (
        "edc_settlement_slip",
        "EDC/QRIS settlement receipt photo — separate card + QRIS amounts; not ESB payments",
    ),
    (
        "esb_closing_receipt",
        "ESB POS closing receipt photo — dual source with live ESB API; mismatch visible",
    ),
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


def apply(conn: sqlite3.Connection) -> dict[str, Any]:
    sql = SQL.read_text(encoding="utf-8")
    conn.executescript(sql)
    ts = now_iso()

    for et, desc in EVIDENCE_TYPES:
        conn.execute(
            """
            INSERT INTO core_evidence_types (
              evidence_type, description, status, created_at, updated_at
            ) VALUES (?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(evidence_type) DO UPDATE SET
              description=excluded.description,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (et, desc, ts, ts),
        )

    # Never invent terminals; never seed ACTIVE variance policies.
    term_n = int(
        conn.execute("SELECT COUNT(*) FROM venue_close_edc_terminals").fetchone()[0]
    )
    active_pol = int(
        conn.execute(
            "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
        ).fetchone()[0]
    )
    enabled = int(
        conn.execute(
            "SELECT COUNT(*) FROM venue_close_outlet_config WHERE human_close_enabled=1"
        ).fetchone()[0]
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='venue_close_outlet_config'"
        ).fetchone()
        else 0
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
        (
            MIGRATION_ID,
            ts,
            "Multi EDC receipts + vision draft + ESB closing receipt dual-source",
        ),
    )

    return {
        "migration_id": MIGRATION_ID,
        "pack": PACK,
        "edc_terminal_rows": term_n,
        "active_variance_policies": active_pol,
        "human_close_enabled_count": enabled,
        "staff_ready": False,
        "human_commissioned": False,
        "invented_terminals": False,
        "invented_tolerance": False,
    }


def main(db_path: Path | None = None) -> int:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        print(json.dumps({"ok": False, "error": f"refused path ({bad})", "db": str(path)}))
        return 2
    if not path.is_file():
        print(json.dumps({"ok": False, "error": "db missing", "db": str(path)}))
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"content_library-pre-{MIGRATION_ID}-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    bak_sha = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        out = apply(conn)
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(json.dumps({"ok": False, "error": str(exc), "backup": str(bak)}))
        return 1
    finally:
        conn.close()

    print(
        json.dumps(
            {
                "ok": True,
                **out,
                "backup": str(bak),
                "backup_sha256": bak_sha,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
