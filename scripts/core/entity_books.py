#!/usr/bin/env python3
"""CORE-BOOKS-1 — shared Finance Core opens per-entity SQLite books files.

ONE FINANCE PRODUCT · THREE ENTITY CONFIGS · SHARED CODE ≠ SHARED DATA.

Decision served: Matt-ordered Owner sprint CORE-BOOKS-1 (2026-09-29).
Prefer separate files under atrium-finance/data/beta/:
  ENT-AMG → atrium.sqlite (live, preserved)
  ENT-BZG → atrium-bzg.sqlite (empty shell)
  ENT-GGV → atrium-ggv.sqlite (empty shell)

No fake journals, sales, P&L, invoices, customers, or go-live numbers.
Never flips staff_ready / human_commissioned.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

ATRIUM_ROOT = Path("/Users/wolfterminal/atrium-finance")
BETA_DIR = ATRIUM_ROOT / "data" / "beta"
SCHEMA_SQL = ATRIUM_ROOT / "server" / "schema.sql"

ENTITY_FILES: dict[str, str] = {
    "ENT-AMG": "atrium.sqlite",
    "ENT-BZG": "atrium-bzg.sqlite",
    "ENT-GGV": "atrium-ggv.sqlite",
}

ENTITY_LABELS: dict[str, str] = {
    "ENT-AMG": "Atrium (AMG) — live books",
    "ENT-BZG": "Blu Zone Group — books shell (empty)",
    "ENT-GGV": "GGV — books shell (empty)",
}

SOD_COLS = (
    ("preparer_person_id", "TEXT NOT NULL DEFAULT ''"),
    ("posted_by", "TEXT NOT NULL DEFAULT ''"),
    ("return_reason", "TEXT NOT NULL DEFAULT ''"),
    ("wolf_created", "INTEGER NOT NULL DEFAULT 0"),
    ("historical_import", "INTEGER NOT NULL DEFAULT 0"),
    ("verified", "INTEGER NOT NULL DEFAULT 0"),
    ("archived_reason", "TEXT NOT NULL DEFAULT ''"),
    ("evidence_ref", "TEXT NOT NULL DEFAULT ''"),
)

LEGAL_ENTITY_TABLES = (
    "accounts",
    "departments",
    "journal_headers",
    "journal_lines",
    "revenue_transactions",
    "spending_transactions",
    "mapping_config",
    "system_settings",
    "report_config",
    "ar_settlements",
    "ap_payments",
    "inventory_categories",
    "inventory_storerooms",
    "inventory_items",
    "inventory_movements",
    "inventory_requisitions",
    "inventory_purchase_orders",
    "inventory_receipts",
    "inventory_count_sessions",
    "inventory_adjustments",
    "owner_pool_units",
    "owner_pool_batches",
    "owner_pool_rule_config",
    "owner_pool_rule_history",
    "service_charge_employees",
    "service_charge_collections",
    "service_charge_cycles",
    "tax_rules",
    "tax_obligations",
    "tax_closed_periods",
    "journal_evidence",
    "journal_workflow_audit",
    "historical_import_batches",
)


class EntityBooksError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def beta_dir() -> Path:
    override = os.environ.get("ATRIUM_BETA_DIR", "").strip()
    if override:
        return Path(override)
    return BETA_DIR


def db_path_for(legal_entity_id: str) -> Path:
    eid = (legal_entity_id or "").strip()
    if eid not in ENTITY_FILES:
        raise EntityBooksError(f"Unknown legal_entity_id: {eid}", code="unknown_entity")
    configured = os.environ.get("DATABASE_FILE", "").strip()
    if eid == "ENT-AMG" and configured:
        return Path(configured)
    return beta_dir() / ENTITY_FILES[eid]


def books_enabled_slots() -> dict[str, bool]:
    """Config contract: all three entity slots have books_enabled on this pack."""
    return {eid: True for eid in ENTITY_FILES}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _ensure_legal_entity(conn: sqlite3.Connection, entity_id: str) -> None:
    safe = entity_id.replace("'", "''")
    for table in LEGAL_ENTITY_TABLES:
        if not _table_exists(conn, table):
            continue
        cols = _columns(conn, table)
        if "legal_entity_id" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN legal_entity_id "
                f"TEXT NOT NULL DEFAULT '{safe}'"
            )
    if _table_exists(conn, "journal_lines"):
        cols = _columns(conn, "journal_lines")
        if "operating_unit_id" not in cols:
            conn.execute("ALTER TABLE journal_lines ADD COLUMN operating_unit_id TEXT")
        if "outlet_id" not in cols:
            conn.execute("ALTER TABLE journal_lines ADD COLUMN outlet_id TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS operating_unit_registry (
          operating_unit_id TEXT PRIMARY KEY,
          legal_entity_id TEXT NOT NULL,
          parent_brand_id TEXT,
          display_name TEXT NOT NULL,
          status TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        )
        """
    )


def _ensure_sod(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "journal_headers"):
        return
    cols = _columns(conn, "journal_headers")
    for name, decl in SOD_COLS:
        if name not in cols:
            conn.execute(f"ALTER TABLE journal_headers ADD COLUMN {name} {decl}")


def _ensure_meta(conn: sqlite3.Connection, entity_id: str) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books_slot_meta (
          legal_entity_id TEXT PRIMARY KEY,
          books_enabled INTEGER NOT NULL,
          shell_kind TEXT NOT NULL,
          db_file TEXT NOT NULL,
          note TEXT NOT NULL,
          staff_ready INTEGER NOT NULL DEFAULT 0,
          human_commissioned INTEGER NOT NULL DEFAULT 0,
          opened_at TEXT NOT NULL,
          pack TEXT NOT NULL
        )
        """
    )
    shell = "live" if entity_id == "ENT-AMG" else "empty_shell"
    note = (
        "AMG / Atrium live Beta books file. Existing journals preserved."
        if entity_id == "ENT-AMG"
        else "Honest empty books shell. No journals, sales, P&L, invoices, or go-live numbers."
    )
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO books_slot_meta (
          legal_entity_id, books_enabled, shell_kind, db_file, note,
          staff_ready, human_commissioned, opened_at, pack
        ) VALUES (?, 1, ?, ?, ?, 0, 0, ?, 'CORE-BOOKS-1')
        ON CONFLICT(legal_entity_id) DO UPDATE SET
          books_enabled=1,
          shell_kind=excluded.shell_kind,
          db_file=excluded.db_file,
          note=excluded.note,
          staff_ready=0,
          human_commissioned=0
        """,
        (entity_id, shell, ENTITY_FILES[entity_id], note, now),
    )
    if _table_exists(conn, "system_settings"):
        cols = _columns(conn, "system_settings")
        if "legal_entity_id" not in cols:
            safe = entity_id.replace("'", "''")
            conn.execute(
                f"ALTER TABLE system_settings ADD COLUMN legal_entity_id "
                f"TEXT NOT NULL DEFAULT '{safe}'"
            )
        row = conn.execute(
            "SELECT settings_id FROM system_settings WHERE settings_id=1"
        ).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO system_settings (
                  settings_id, property_name, room_count, base_currency,
                  fiscal_year, period_lock_date, controller_name, legal_entity_id
                ) VALUES (1, ?, 0, 'IDR', '', '', '', ?)
                """,
                (ENTITY_LABELS[entity_id], entity_id),
            )
        elif entity_id != "ENT-AMG":
            conn.execute(
                "UPDATE system_settings SET legal_entity_id=? WHERE settings_id=1",
                (entity_id,),
            )


def connect(legal_entity_id: str, *, readonly: bool = False) -> sqlite3.Connection:
    path = db_path_for(legal_entity_id)
    if readonly:
        if not path.is_file():
            raise EntityBooksError(
                f"Books file missing for {legal_entity_id}",
                code="missing",
                http_status=404,
            )
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_shell(legal_entity_id: str) -> dict[str, Any]:
    """Create/open entity books file. AMG preserved; BZG/GGV empty shells."""
    eid = (legal_entity_id or "").strip()
    if eid not in ENTITY_FILES:
        raise EntityBooksError(f"Unknown legal_entity_id: {eid}")
    path = db_path_for(eid)
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.is_file()
    conn = connect(eid, readonly=False)
    try:
        if eid != "ENT-AMG" or not existed:
            schema = SCHEMA_SQL.read_text(encoding="utf-8")
            conn.executescript(schema)
        _ensure_legal_entity(conn, eid)
        _ensure_sod(conn)
        _ensure_meta(conn, eid)
        # Pool Bar OU hook (registry only — no outlet totals).
        conn.execute(
            """
            INSERT INTO operating_unit_registry (
              operating_unit_id, legal_entity_id, parent_brand_id,
              display_name, status, note, created_at
            ) VALUES (
              'OU-BZG-RAIN-POOL', 'ENT-BZG', 'BZG-RAIN', 'Pool Bar',
              'PRE-OPENING',
              'Measurable BZG operating unit under Rainforest. Nullable on journal lines.',
              datetime('now')
            )
            ON CONFLICT(operating_unit_id) DO NOTHING
            """
        )
        accounts = int(conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0])
        journals = int(conn.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0])
        if eid != "ENT-AMG" and journals != 0 and not existed:
            raise EntityBooksError(
                f"Refusing non-empty fresh shell for {eid}",
                code="dirty_shell",
            )
        jl_cols = _columns(conn, "journal_lines")
        conn.commit()
        meta = conn.execute(
            "SELECT * FROM books_slot_meta WHERE legal_entity_id=?",
            (eid,),
        ).fetchone()
        return {
            "legal_entity_id": eid,
            "db_file": ENTITY_FILES[eid],
            "path": str(path),
            "books_enabled": True,
            "shell_kind": "live" if eid == "ENT-AMG" else "empty_shell",
            "accounts": accounts,
            "journals": journals,
            "outlet_id_nullable": "outlet_id" in jl_cols,
            "operating_unit_id_nullable": "operating_unit_id" in jl_cols,
            "preparer_person_id": "preparer_person_id"
            in _columns(conn, "journal_headers"),
            "staff_ready": False,
            "human_commissioned": False,
            "note": dict(meta)["note"] if meta else "",
            "pack": "CORE-BOOKS-1",
        }
    finally:
        conn.close()


def ensure_all_shells() -> list[dict[str, Any]]:
    return [ensure_shell(eid) for eid in ENTITY_FILES]


def snapshot(legal_entity_id: str) -> dict[str, Any]:
    path = db_path_for(legal_entity_id)
    if not path.is_file():
        return {
            "legal_entity_id": legal_entity_id,
            "exists": False,
            "books_enabled": books_enabled_slots().get(legal_entity_id, False),
            "staff_ready": False,
            "human_commissioned": False,
        }
    conn = connect(legal_entity_id, readonly=True)
    try:
        accounts = int(conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0])
        journals = int(conn.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0])
        meta = None
        if _table_exists(conn, "books_slot_meta"):
            meta = conn.execute(
                "SELECT * FROM books_slot_meta WHERE legal_entity_id=?",
                (legal_entity_id,),
            ).fetchone()
        jl_cols = _columns(conn, "journal_lines")
        return {
            "legal_entity_id": legal_entity_id,
            "exists": True,
            "db_file": ENTITY_FILES[legal_entity_id],
            "path": str(path),
            "books_enabled": True,
            "shell_kind": "live" if legal_entity_id == "ENT-AMG" else "empty_shell",
            "accounts": accounts,
            "journals": journals,
            "outlet_id_nullable": "outlet_id" in jl_cols,
            "operating_unit_id_nullable": "operating_unit_id" in jl_cols,
            "staff_ready": False,
            "human_commissioned": False,
            "meta": dict(meta) if meta else None,
            "pack": "CORE-BOOKS-1",
        }
    finally:
        conn.close()


def prove_isolation(probe_token: str) -> dict[str, Any]:
    """Write a non-money probe into BZG meta; prove AMG/GGV cannot see it."""
    token = (probe_token or "").strip()
    if not token or len(token) > 64:
        raise EntityBooksError("probe_token required", code="invalid")
    ensure_all_shells()
    bzg = connect("ENT-BZG", readonly=False)
    try:
        bzg.execute(
            """
            CREATE TABLE IF NOT EXISTS books_isolation_probe (
              token TEXT PRIMARY KEY,
              legal_entity_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        bzg.execute(
            """
            INSERT OR REPLACE INTO books_isolation_probe (token, legal_entity_id, created_at)
            VALUES (?, 'ENT-BZG', datetime('now'))
            """,
            (token,),
        )
        bzg.commit()
    finally:
        bzg.close()

    def has_token(eid: str) -> bool:
        c = connect(eid, readonly=True)
        try:
            if not _table_exists(c, "books_isolation_probe"):
                return False
            row = c.execute(
                "SELECT 1 FROM books_isolation_probe WHERE token=?",
                (token,),
            ).fetchone()
            return bool(row)
        finally:
            c.close()

    return {
        "token": token,
        "in_bzg": has_token("ENT-BZG"),
        "in_amg": has_token("ENT-AMG"),
        "in_ggv": has_token("ENT-GGV"),
        "isolated": has_token("ENT-BZG")
        and not has_token("ENT-AMG")
        and not has_token("ENT-GGV"),
    }


def desk_stamp(legal_entity_id: str) -> dict[str, Any]:
    """Honesty stamp for Beta finance desks — no READY / staff_ready claims."""
    snap = snapshot(legal_entity_id)
    empty = legal_entity_id != "ENT-AMG" or int(snap.get("journals") or 0) == 0
    if legal_entity_id == "ENT-AMG":
        message = (
            "AMG / Atrium books are live on the Beta sidecar file. "
            "Not staff_ready. Not human_commissioned."
        )
        empty = False
    else:
        message = (
            f"{ENTITY_LABELS.get(legal_entity_id, legal_entity_id)} is open. "
            "Empty shell — no journals or go-live figures. "
            "Not staff_ready. Not human_commissioned."
        )
        empty = True
    return {
        "ok": True,
        "legal_entity_id": legal_entity_id,
        "books_enabled": True,
        "books_opened": True,
        "shell_kind": snap.get("shell_kind") or "empty_shell",
        "empty": empty,
        "accounts": snap.get("accounts", 0),
        "journals": snap.get("journals", 0),
        "db_file": snap.get("db_file") or ENTITY_FILES.get(legal_entity_id),
        "staff_ready": False,
        "human_commissioned": False,
        "money_movement": False,
        "payment_execute": False,
        "bank_write": False,
        "proven": False,
        "message": message,
        "pack": "CORE-BOOKS-1",
        "outlet_id_nullable": snap.get("outlet_id_nullable", True),
    }
