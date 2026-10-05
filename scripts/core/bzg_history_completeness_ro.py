#!/usr/bin/env python3
"""BZG-HISTORY-IMPORT-1 — owner completeness projection for BZG finance datasets."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_history_import1 as _hist

BETA_ROOT = Path(__file__).resolve().parents[2]
CATALOG = BETA_ROOT / "catalog" / "content_library.sqlite"
PACK = "BZG-HISTORY-IMPORT-1"
SCHEMA = "bzg.history.completeness.v1"
ALCHEMIST_DB = _hist.ALCHEMIST_DB


def _ro_conn(path: Path | None = None) -> sqlite3.Connection:
    p = path or CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _dataset(
    name: str,
    source_count: int | str,
    beta_count: int,
    *,
    earliest: str | None = None,
    latest: str | None = None,
    unresolved: int | str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    src_n = source_count if isinstance(source_count, int) else None
    unresolved_n = unresolved
    if unresolved_n is None and isinstance(source_count, int):
        unresolved_n = max(source_count - beta_count, 0)
    if isinstance(source_count, int) and beta_count >= source_count and (unresolved_n in (0, None, "0")):
        status = "COMPLETE"
        status_label = "Complete"
    else:
        status = "GAP"
        status_label = "Gap"
    return {
        "dataset": name,
        "status": status,
        "status_label": status_label,
        "source_count": source_count,
        "beta_count": beta_count,
        "earliest_date": earliest or "UNKNOWN",
        "latest_date": latest or "UNKNOWN",
        "unresolved": unresolved_n if unresolved_n is not None else "UNKNOWN",
        "detail": detail or "",
    }


def load_completeness(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    db = conn or _ro_conn()
    try:
        src = _hist._ro(ALCHEMIST_DB) if ALCHEMIST_DB.is_file() else None
        src_counts = _hist.source_counts(src) if src else {}
        if src:
            src.close()
        beta = _hist.beta_counts(db)

        datasets = [
            _dataset(
                "purchase_orders",
                src_counts.get("pr_orders", "UNKNOWN"),
                beta.get("bzg_ops_purchase_orders", 0),
                earliest="2026-07-27",
                latest="2026-09-30",
            ),
            _dataset(
                "po_lines",
                src_counts.get("pr_order_lines", "UNKNOWN"),
                beta.get("bzg_ops_po_lines", 0),
            ),
            _dataset(
                "goods_receipts",
                104,
                beta.get("bzg_ops_goods_receipts", 0),
                earliest="2026-07-28",
                latest="2026-09-22",
                detail="104 distinct parent PRs with receipt lines; 477 receipt lines",
            ),
            _dataset(
                "gr_lines",
                src_counts.get("pr_receipt_lines", "UNKNOWN"),
                beta.get("bzg_ops_gr_lines", 0),
            ),
            _dataset(
                "supplier_bills",
                src_counts.get("ledger", "UNKNOWN"),
                beta.get("bzg_ops_supplier_bills", 0),
                earliest="2026-08-02",
                latest="2026-09-30",
            ),
            _dataset(
                "ap_ready",
                106,
                beta.get("bzg_ops_ap_ready", 0),
                detail="Alchemist ledger payment_status=unpaid",
            ),
            _dataset(
                "petty_cash",
                src_counts.get("petty_cash", "UNKNOWN"),
                beta.get("bzg_ops_petty_movements_historical", 0),
                earliest="2026-07-20",
                latest="2026-10-01",
                detail="Beta live petty (17 rows) excluded from historical beta_count",
            ),
            _dataset(
                "suppliers",
                src_counts.get("suppliers", "UNKNOWN"),
                beta.get("bzg_shared_vendors", 0),
            ),
            _dataset(
                "bank_statements",
                15,
                beta.get("bzg_bank_statement_imports", 0),
                earliest="2026-03-01",
                latest="2026-08-31",
                detail="Sep/Oct 2026 absent on disk",
            ),
            _dataset(
                "bank_transactions",
                "UNKNOWN",
                beta.get("bzg_bank_transactions", 0),
                detail="Parsed txn count from safe CSV only; BNI XLS raw",
            ),
            _dataset(
                "evidence_files",
                1363,
                16,
                detail="Possessed jpgs minus live petty links; EVIDENCE UNLINKED queue",
                unresolved=beta.get("bzg_ops_evidence_unlinked", 0),
            ),
        ]

        gap_count = sum(1 for d in datasets if d["status"] == "GAP")
        return {
            "ok": True,
            "pack": PACK,
            "schema": SCHEMA,
            "staff_ready": False,
            "zayen_ready": False,
            "entity_id": _hist.ENTITY,
            "summary": {
                "datasets_total": len(datasets),
                "gap_count": gap_count,
                "complete_count": len(datasets) - gap_count,
            },
            "datasets": datasets,
            "source_counts_fresh": src_counts,
            "beta_counts": beta,
        }
    finally:
        if own:
            db.close()


def gap_detail(dataset_name: str, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    payload = load_completeness(conn)
    for row in payload.get("datasets") or []:
        if row.get("dataset") == dataset_name:
            return {"ok": True, "gap": row}
    return {"ok": False, "error": "not_found", "dataset": dataset_name}
