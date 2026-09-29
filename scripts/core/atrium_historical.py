#!/usr/bin/env python3
"""Atrium historical ledger import model (ATRIUM-SOD-1).

NEW WOLF SOFTWARE MUST NOT MAKE AN EXISTING BUSINESS APPEAR EMPTY BECAUSE
ITS HISTORY PREDATES WOLF.

Discovery (state/atrium-sod/discovery.md): no authoritative historical AMG
ledger/TB/bank/P&L found. This module provides the idempotent import path +
provenance tables and cutover date. It imports nothing until an authoritative
source is presented. Fabrication is refused.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
DEFAULT_CUTOVER = "2026-09-29"

# Locations searched (read-only honesty for GL empty state).
SOURCES_SEARCHED = (
    "V1 wolf-system/atrium-finance/atrium_finance.sqlite (TEST/probe only — not SoR)",
    "sidecar beta atrium.sqlite (commissioning / chart only)",
    "~/atrium-finance/data/uncommissioned + owner_pool.json (FAKE — never use)",
    "state/atrium-books/amg.sqlite (COA only)",
    "V1 AMG bank statements folder (0 files)",
    "Notion AMG Supplier Invoices (0 rows); June P&L AMG — No data",
    "Xero snapshots (GGV only; AMG never connected; Xero cancelled 10 Sep)",
    "payments.db (BZG); atrium-payments/journal.jsonl (apartment sales, not hotel GL)",
    "Cloudbeds / Mews / Accurate / Jurnal / GL exports (none found)",
)

HONEST_EMPTY_MESSAGE = (
    "No authoritative historical Atrium (ENT-AMG) ledger was found. "
    "Sources searched: V1 atrium sqlite (test/probe only), Beta sidecar books, "
    "uncommissioned sample pool, AMG books COA-only, AMG bank statements (empty), "
    "Notion AMG invoices/P&L (no data), Xero (GGV only), payments.db (BZG), "
    "and no Cloudbeds/Mews/Accurate/Jurnal/GL export. "
    "Nothing authoritative was imported. Wolf cutover date: {cutover}. "
    "Posted Wolf-created commissioning lines may appear after Controller post; "
    "they are not historical hotel books."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_import_model(atrium_path: Path | None = None) -> dict[str, Any]:
    """Create provenance tables + cutover setting. Import nothing."""
    path = Path(atrium_path or ATRIUM_DB)
    if not path.is_file():
        return {"ok": False, "error": "atrium db missing", "path": str(path)}
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_import_batches (
              batch_id TEXT PRIMARY KEY,
              source_file TEXT NOT NULL,
              source_hash TEXT NOT NULL,
              period TEXT NOT NULL,
              imported_at TEXT NOT NULL,
              row_count INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        ss_cols = {r[1] for r in conn.execute("PRAGMA table_info(system_settings)").fetchall()}
        if "wolf_cutover_date" not in ss_cols:
            conn.execute(
                "ALTER TABLE system_settings ADD COLUMN wolf_cutover_date TEXT NOT NULL DEFAULT ?",
                (DEFAULT_CUTOVER,),
            )
        else:
            conn.execute(
                """
                UPDATE system_settings
                SET wolf_cutover_date=?
                WHERE wolf_cutover_date IS NULL OR TRIM(wolf_cutover_date)=''
                """,
                (DEFAULT_CUTOVER,),
            )
        # Marker batch: searched, nothing authoritative
        batch_id = "HIST-AMG-NONE-20260929"
        existing = conn.execute(
            "SELECT batch_id, status FROM historical_import_batches WHERE batch_id=?",
            (batch_id,),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO historical_import_batches (
                  batch_id, source_file, source_hash, period, imported_at, row_count, status, note
                ) VALUES (?, ?, ?, ?, ?, 0, 'NOTHING_AUTHORITATIVE', ?)
                """,
                (
                    batch_id,
                    "discovery:state/atrium-sod/discovery.md",
                    hashlib.sha256("\n".join(SOURCES_SEARCHED).encode()).hexdigest(),
                    "pre-cutover",
                    now_utc(),
                    "No authoritative historical ledger found; import refused (no fabrication).",
                ),
            )
        cutover = conn.execute(
            "SELECT wolf_cutover_date FROM system_settings LIMIT 1"
        ).fetchone()
        cut = (cutover[0] if cutover else DEFAULT_CUTOVER) or DEFAULT_CUTOVER
        conn.commit()
        return {
            "ok": True,
            "status": "NOTHING_AUTHORITATIVE",
            "imported_rows": 0,
            "wolf_cutover_date": cut,
            "sources_searched": list(SOURCES_SEARCHED),
            "honest_empty_message": HONEST_EMPTY_MESSAGE.format(cutover=cut),
            "batch_id": batch_id,
        }
    finally:
        conn.close()


def import_authoritative_ledger(
    source_file: Path,
    *,
    period: str,
    atrium_path: Path | None = None,
    allow: bool = False,
) -> dict[str, Any]:
    """Idempotent import gate. Refuses unless allow=True and file is real.

    ATRIUM-SOD-1: discovery found nothing authoritative — this path stays closed
    until a verified source is presented. Never fabricate journals.
    """
    if not allow:
        return {
            "ok": False,
            "error": "import_closed",
            "message": "No authoritative source authorised for import. Discovery found none.",
        }
    path = Path(source_file)
    if not path.is_file():
        return {"ok": False, "error": "source_missing", "path": str(path)}
    # Placeholder: real parser lands when an authoritative file is named by Matt.
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "ok": False,
        "error": "parser_not_configured",
        "source_file": str(path),
        "source_hash": digest,
        "period": period,
        "message": "Authoritative import parser not configured — refuse fabrication.",
    }


def gl_empty_state(atrium_path: Path | None = None) -> dict[str, Any]:
    """Payload for UI: posted counts + honest empty copy."""
    model = ensure_import_model(atrium_path)
    path = Path(atrium_path or ATRIUM_DB)
    posted = 0
    wolf_created = 0
    historical = 0
    if path.is_file():
        conn = sqlite3.connect(str(path))
        try:
            posted = int(
                conn.execute(
                    "SELECT COUNT(*) FROM journal_headers WHERE status='POSTED'"
                ).fetchone()[0]
            )
            cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_headers)").fetchall()}
            if "wolf_created" in cols:
                wolf_created = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM journal_headers WHERE status='POSTED' AND wolf_created=1"
                    ).fetchone()[0]
                )
            if "historical_import" in cols:
                historical = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM journal_headers WHERE historical_import=1"
                    ).fetchone()[0]
                )
        finally:
            conn.close()
    return {
        **model,
        "posted_journals": posted,
        "wolf_created_posted": wolf_created,
        "historical_imported": historical,
        "show_honest_empty": posted == 0,
    }
