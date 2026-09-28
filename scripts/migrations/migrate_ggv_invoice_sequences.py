#!/usr/bin/env python3
"""031 GGV invoice sequence — idempotent Beta-only migration.

Seeds ENT-GGV at 067 with format {n:03d}A. Records the Owner decision.
Does not create invoices 064A, 065A, or 066A. Never rewinds next_value.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "031_ggv_invoice_sequences"
NEXT_STEP = "Generate Gmail draft with PDF attachment — human review/send, never automatic"
CR_IDS = ("CR-8f20b066fac63445", "CR-214e370b5b96cbd1")
FORBIDDEN = ("wolf-system", "money.sqlite")
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def refuse(path: Path) -> None:
    text = str(path.resolve())
    for bad in FORBIDDEN:
        if bad in text:
            raise SystemExit(f"refuses path containing {bad}: {path}")
    if "beta-os" not in text:
        raise SystemExit(f"refuses non-beta path: {path}")


def _table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _record_next_step(conn: sqlite3.Connection, ts: str) -> None:
    if not _table(conn, "wolf_completion_items"):
        return
    for item_id in CR_IDS:
        row = conn.execute(
            "SELECT next_action FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
        if row is None:
            continue
        current = str(row[0] or "")
        if NEXT_STEP in current:
            continue
        updated = f"{current} | {NEXT_STEP}".strip(" |")
        conn.execute(
            """
            UPDATE wolf_completion_items
            SET next_action=?, last_checked=?
            WHERE id=?
            """,
            (updated, ts, item_id),
        )


def apply(conn: sqlite3.Connection) -> dict:
    from core import ggv_finance_invoice as inv

    before = 0
    if _table(conn, "ggv_invoices"):
        before = int(conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0])
    inv.ensure_schema(conn)
    after = int(conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0])
    if after != before:
        raise RuntimeError("GGV sequence migration created or removed an invoice")
    ts = now_iso()
    _record_next_step(conn, ts)
    row = conn.execute(
        "SELECT next_value, format FROM fin_invoice_sequences WHERE entity_id='ENT-GGV'"
    ).fetchone()
    detail = (
        f"ggv invoice sequence; next={row[0]}; format={row[1]}; "
        f"invoices_unchanged={before}; historical_064_066_not_seeded=1; "
        f"next_step={NEXT_STEP}"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL,
          note TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO schema_migrations (id, applied_at, note)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          applied_at=excluded.applied_at,
          note=excluded.note
        """,
        (MIGRATION_ID, ts, detail),
    )
    return {"next_value": int(row[0]), "format": str(row[1]), "invoices": before, "detail": detail}


def main() -> int:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        print(f"SKIP {MIGRATION_ID}: test mode does not write the live catalog")
        return 0
    refuse(DB)
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        result = apply(conn)
        conn.commit()
        print(f"OK {MIGRATION_ID}: {result['detail']}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
