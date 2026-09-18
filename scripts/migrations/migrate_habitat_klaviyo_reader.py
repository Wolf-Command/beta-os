#!/usr/bin/env python3
"""025 Habitat Klaviyo read-only ingest ledger — Beta only.

Creates core_lead_ingest_runs. Inserts no profiles. Grants no permissions.
No live network. No cutover. Does not edit the phase 2.6 migration.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core.habitat_klaviyo_reader import ensure_ledger  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "025_habitat_klaviyo_reader"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
STAFF_ROLES = (
    "ROLE-MATT",
    "ROLE-OWNER",
    "ROLE-AMANDA",
    "ROLE-HAIKAL",
    "ROLE-MISA",
    "ROLE-DEVI",
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def apply_schema(conn: sqlite3.Connection) -> None:
    ensure_ledger(conn)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _staff_grants(conn: sqlite3.Connection) -> int:
    if "org_role_permissions" not in _table_names(conn):
        return 0
    marks = ",".join("?" * len(STAFF_ROLES))
    return conn.execute(
        f"SELECT COUNT(*) FROM org_role_permissions WHERE role_id IN ({marks})",
        STAFF_ROLES,
    ).fetchone()[0]


def _klaviyo_leads(conn: sqlite3.Connection) -> int:
    if "core_leads" not in _table_names(conn):
        return 0
    return conn.execute(
        "SELECT COUNT(*) FROM core_leads WHERE source_system='klaviyo'"
    ).fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    db_path = Path(args[0]).resolve() if args else DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        grants_before = _staff_grants(conn)
        leads_before = _klaviyo_leads(conn)
        apply_schema(conn)
        print("DDL applied")
        grants_after = _staff_grants(conn)
        leads_after = _klaviyo_leads(conn)
        if grants_after != grants_before:
            print(
                f"REFUSE: staff grants changed {grants_before} -> {grants_after}",
                file=sys.stderr,
            )
            return 2
        if leads_after != leads_before:
            print(
                f"REFUSE: klaviyo leads changed {leads_before} -> {leads_after}",
                file=sys.stderr,
            )
            return 2

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                "Habitat Klaviyo read-only ingest ledger; no profiles; no role grants",
            ),
        )
        conn.commit()
        present = conn.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='core_lead_ingest_runs'
            """
        ).fetchone()[0]
        print(f"  core_lead_ingest_runs={present}")
        print(f"  klaviyo_leads={leads_after}")
        print(f"  staff_grants={grants_after}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if present != 1:
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
