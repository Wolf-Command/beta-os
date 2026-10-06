#!/usr/bin/env python3
"""GGV-BILLS-605 — import money.sqlite bill rows into Beta catalog ggv_bills.

Read-only source: wolf-system ggv-finance money.sqlite.
Preserves source ids, amounts, and provenance. Idempotent on bill_id.
Does not move money, write bank rows, or call Xero. staff_ready stays false.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import ggv_finance_nota as fin

BETA_ROOT = Path(__file__).resolve().parents[2]
LIVE_CATALOG = BETA_ROOT / "catalog" / "content_library.sqlite"
SOURCE_DB = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/ggv-finance/money.sqlite"
)
PACK = "GGV-BILLS-605"
MIGRATION_ID = "ggv_bills_605_20261005"
IMPORT_ACTOR = "PERS-MATT"
SOURCE_TABLE = "bill"
TZ8 = timezone(timedelta(hours=8))

PROVENANCE_FIELDS = (
    "source_id",
    "source_table",
    "source_file_path",
    "source_status",
    "source",
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _col(row: sqlite3.Row, name: str) -> Any:
    try:
        return row[name]
    except (IndexError, KeyError):
        return None


def _entity_id(raw: str | None) -> str:
    entity = (raw or "").strip().upper()
    if entity in ("GGV", "ENT-GGV"):
        return fin.ENTITY_GGV
    return entity or fin.ENTITY_GGV


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ggv_bills (
          bill_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          contact_id TEXT,
          bill_number TEXT,
          issued_on TEXT,
          due_on TEXT,
          status TEXT,
          amount TEXT,
          currency TEXT,
          notes TEXT,
          created_at TEXT NOT NULL,
          created_by TEXT,
          amount_due TEXT,
          amount_paid TEXT,
          contact_name TEXT,
          reference TEXT,
          source_id TEXT NOT NULL,
          source_table TEXT NOT NULL,
          source_file_path TEXT NOT NULL,
          source_status TEXT,
          source TEXT,
          imported_at TEXT NOT NULL,
          imported_by_person_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ggv_bills_entity ON ggv_bills(entity_id, issued_on);
        CREATE INDEX IF NOT EXISTS idx_ggv_bills_source ON ggv_bills(source_id, source_table);
        """
    )


def target_counts(target_conn: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for name in ("ggv_invoices", "ggv_bills", "ggv_notas", "ggv_vendors", "fin_counterparties"):
        if not _table(target_conn, name):
            out[name] = 0
            continue
        out[name] = int(target_conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
    return out


def source_bill_count(source_conn: sqlite3.Connection) -> int:
    if not _table(source_conn, SOURCE_TABLE):
        return 0
    return int(source_conn.execute(f"SELECT COUNT(*) FROM {SOURCE_TABLE}").fetchone()[0])


def import_bills(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    *,
    source_path: Path | str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path or SOURCE_DB).resolve()
    imported = 0
    skipped: dict[str, int] = {}
    source_status_counts: dict[str, int] = {}

    rows = source.execute(
        f"""
        SELECT *
        FROM {SOURCE_TABLE}
        WHERE COALESCE(entity, '') IN ('GGV', 'ENT-GGV')
        ORDER BY issued_on, created_at, id
        """
    ).fetchall()

    ts = now_iso()
    for row in rows:
        bill_id = str(row["id"])
        source_status = _blank(_col(row, "status")) or "UNKNOWN"
        source_status_counts[source_status] = source_status_counts.get(source_status, 0) + 1

        if target.execute(
            "SELECT 1 FROM ggv_bills WHERE bill_id=?",
            (bill_id,),
        ).fetchone():
            skipped["already_exists"] = skipped.get("already_exists", 0) + 1
            continue

        target.execute(
            """
            INSERT INTO ggv_bills (
              bill_id, entity_id, contact_id, bill_number, issued_on, due_on, status,
              amount, currency, notes, created_at, created_by, amount_due, amount_paid,
              contact_name, reference, source_id, source_table, source_file_path,
              source_status, source, imported_at, imported_by_person_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_id,
                _entity_id(_col(row, "entity")),
                _blank(_col(row, "contact_id")),
                _blank(_col(row, "number")),
                _blank(_col(row, "issued_on")),
                _blank(_col(row, "due_on")),
                source_status,
                _blank(_col(row, "amount")),
                _blank(_col(row, "currency")),
                _blank(_col(row, "notes")),
                _col(row, "created_at") or ts,
                _blank(_col(row, "created_by")),
                _blank(_col(row, "amount_due")),
                _blank(_col(row, "amount_paid")),
                _blank(_col(row, "contact_name")),
                _blank(_col(row, "reference")),
                bill_id,
                SOURCE_TABLE,
                str(source_path),
                source_status,
                _blank(_col(row, "source")),
                ts,
                IMPORT_ACTOR,
            ),
        )
        imported += 1

    return {
        "source_rows": len(rows),
        "imported": imported,
        "skipped": skipped,
        "source_status_split": source_status_counts,
        "target_table": "ggv_bills",
        "provenance_fields": list(PROVENANCE_FIELDS),
    }


def run_import(
    target_db: Path,
    *,
    source_db: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    target_path = Path(target_db).resolve()
    source_path = Path(source_db or SOURCE_DB).resolve()
    fin.assert_catalog_writable(target_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"source missing: {source_path}")

    source = _ro(source_path)
    target = sqlite3.connect(str(target_path), timeout=60)
    target.row_factory = sqlite3.Row
    try:
        before = target_counts(target)
        src_bills = source_bill_count(source)

        ensure_schema(target)

        if dry_run:
            return {
                "pack": PACK,
                "dry_run": True,
                "source_db": str(source_path),
                "target_db": str(target_path),
                "source_bill_count": src_bills,
                "target_counts_before": before,
            }

        bills = import_bills(target, source, source_path=source_path)
        target.commit()

        after = target_counts(target)
        return {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": now_iso(),
            "source_db": str(source_path),
            "target_db": str(target_path),
            "source_bill_count": src_bills,
            "target_counts_before": before,
            "target_counts_after": after,
            "bills": bills,
            "staff_ready": False,
            "human_commissioned": False,
        }
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()


BILL_STATUS_LABELS = {
    "DRAFT": "Draft — not approved",
    "DELETED": "Deleted",
    "VOID": "Void",
    "VOIDED": "Void",
    "AUTHORISED": "Approved",
    "PAID": "Paid",
    "SUBMITTED": "Submitted",
}


def bill_public(row: sqlite3.Row) -> dict[str, Any]:
    status = str(row["status"] or "")
    src_path = str(row["source_file_path"] or "")
    has_doc = bool(src_path) and not src_path.endswith("money.sqlite")
    return {
        "bill_id": row["bill_id"],
        "bill_number": row["bill_number"],
        "contact_name": row["contact_name"],
        "issued_on": row["issued_on"],
        "due_on": row["due_on"],
        "status": status,
        "status_label": BILL_STATUS_LABELS.get(status.upper(), status.replace("_", " ").title()),
        "amount": row["amount"],
        "currency": row["currency"],
        "amount_due": row["amount_due"],
        "amount_paid": row["amount_paid"],
        "reference": row["reference"],
        "notes": row["notes"],
        "source_status": row["source_status"],
        "source": row["source"],
        "has_original_document": has_doc,
        "source_note": (
            "No original document — imported from old finance records"
            if not has_doc
            else None
        ),
    }
