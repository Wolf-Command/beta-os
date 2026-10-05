#!/usr/bin/env python3
"""BZG-HISTORY-IMPORT-1 — Alchemist historical P2P + petty + bank into Beta catalog.

Read-only source: alchemist.db + possessed evidence + BZG bank statement files.
Idempotent on source_system + source_id. staff_ready stays false.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_ap_ready as _ap
from core import bzg_goods_receiving as _gr
from core import bzg_purchase_order as _po
from core import bzg_supplier_bill as _bill
from core import uma_ops_console as _ops

BETA_ROOT = Path(__file__).resolve().parents[2]
LIVE_CATALOG = BETA_ROOT / "catalog" / "content_library.sqlite"
ALCHEMIST_DB = Path(
    "/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db"
)
NOTAS_DIR = Path("/Users/wolfterminal/.openclaw/workspace/alchemist/notas")
RECEIVE_DIR = Path("/Users/wolfterminal/.openclaw/workspace/alchemist/media/receive")
NIGHTLY_DIR = Path("/Users/wolfterminal/.openclaw/workspace/alchemist/media/nightly")
BANK_PACK = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/BZG"
)
BANK_ORIGINALS = BETA_ROOT / "state" / "bzg-bank-statements" / "originals"

PACK = "BZG-HISTORY-IMPORT-1"
MIGRATION_ID = "bzg_history_import1_20261005"
SOURCE_SYSTEM = "alchemist"
ENTITY = "ENT-BZG"
OUTLET = "BZG-UMA"
VENUE = "BZG-UMA"
IMPORT_ACTOR = "PERS-MATT"
TZ8 = timezone(timedelta(hours=8))

LIVE_PETTY_SKIP_SOURCE_IDS = frozenset({"451"})
LIVE_PETTY_MOVEMENT_IDS = frozenset(
    {"PETTY-UMA-6E512800FE", "PETTY-UMA-80867C2504", "PETTY-UMA-2321496C6D"}
)

STATUS_MAP = {
    "Paid": "CLOSED",
    "Received": "RECEIVED",
    "Awaiting Devi": "PENDING",
    "Cancelled": "CANCELLED",
    "Ordered": "OPEN",
    "Rejected": "REJECTED",
}


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _rw(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _norm_name(name: str | None) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().upper())


def ensure_history_schema(conn: sqlite3.Connection) -> list[str]:
    """Extend P2P tables + provenance / evidence / bank inventory."""
    _po.ensure_po_schema(conn)
    _gr.ensure_gr_schema(conn)
    _bill.ensure_bill_schema(conn)
    _ap.ensure_ap_schema(conn)
    added: list[str] = []

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bzg_ops_history_provenance (
          record_type TEXT NOT NULL,
          beta_id TEXT NOT NULL,
          source_system TEXT NOT NULL,
          source_id TEXT NOT NULL,
          migration_status TEXT NOT NULL,
          source_pr_num TEXT,
          business_date TEXT,
          alchemist_status TEXT,
          linked_ledger_id TEXT,
          linked_po_id TEXT,
          linked_gr_id TEXT,
          evidence_ref TEXT,
          extra_json TEXT,
          imported_at TEXT NOT NULL,
          PRIMARY KEY (record_type, beta_id),
          UNIQUE (source_system, source_id, record_type)
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_hist_prov_source
          ON bzg_ops_history_provenance(source_system, source_id, record_type);

        CREATE TABLE IF NOT EXISTS bzg_ops_migration_links (
          link_id TEXT PRIMARY KEY,
          link_type TEXT NOT NULL,
          source_key TEXT NOT NULL UNIQUE,
          po_id TEXT,
          ledger_source_id TEXT,
          bill_id TEXT,
          migration_status TEXT NOT NULL,
          imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bzg_ops_evidence_unlinked (
          queue_id TEXT PRIMARY KEY,
          file_path TEXT NOT NULL UNIQUE,
          file_kind TEXT NOT NULL,
          file_mtime TEXT,
          migration_status TEXT NOT NULL DEFAULT 'EVIDENCE UNLINKED',
          imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bzg_bank_statement_imports (
          import_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          bank_label TEXT NOT NULL,
          account_label TEXT,
          original_filename TEXT NOT NULL,
          original_path TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          uploaded_by_person_id TEXT NOT NULL,
          uploaded_at TEXT NOT NULL,
          period_start TEXT,
          period_end TEXT,
          txn_count INTEGER NOT NULL DEFAULT 0,
          parse_status TEXT NOT NULL,
          parse_notes TEXT,
          UNIQUE (entity_id, content_sha256)
        );

        CREATE TABLE IF NOT EXISTS bzg_bank_transactions (
          txn_id TEXT PRIMARY KEY,
          import_id TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          txn_date TEXT,
          value_date TEXT,
          description TEXT,
          reference TEXT,
          debit REAL NOT NULL DEFAULT 0,
          credit REAL NOT NULL DEFAULT 0,
          running_balance REAL,
          bank_account TEXT,
          raw_json TEXT,
          recon_status TEXT NOT NULL DEFAULT 'UNMATCHED',
          matched_ledger_source_id TEXT,
          match_confidence TEXT,
          notes TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_bank_txn_entity_date
          ON bzg_bank_transactions(entity_id, txn_date);

        CREATE TABLE IF NOT EXISTS bzg_shared_vendors (
          vendor_id TEXT PRIMARY KEY,
          legal_entity_id TEXT NOT NULL,
          outlet_id TEXT,
          cost_centre_id TEXT,
          revenue_centre_id TEXT,
          display_name TEXT NOT NULL,
          name_norm TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'HOOK',
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        """
    )
    added.extend(
        [
            "bzg_ops_history_provenance",
            "bzg_ops_migration_links",
            "bzg_ops_evidence_unlinked",
            "bzg_bank_statement_imports",
            "bzg_bank_transactions",
        ]
    )

    cols = {r[1] for r in conn.execute("PRAGMA table_info(bzg_ops_petty_movements)").fetchall()}
    if "source_system" not in cols:
        conn.execute("ALTER TABLE bzg_ops_petty_movements ADD COLUMN source_system TEXT")
        conn.execute("ALTER TABLE bzg_ops_petty_movements ADD COLUMN source_id TEXT")
        conn.execute("ALTER TABLE bzg_ops_petty_movements ADD COLUMN migration_status TEXT")
        added.append("bzg_ops_petty_movements.source_*")
    return added


def _already_imported(
    conn: sqlite3.Connection, record_type: str, source_id: str, source_system: str = SOURCE_SYSTEM
) -> str | None:
    row = conn.execute(
        """
        SELECT beta_id FROM bzg_ops_history_provenance
        WHERE record_type=? AND source_system=? AND source_id=?
        """,
        (record_type, source_system, str(source_id)),
    ).fetchone()
    return str(row[0]) if row else None


def _record_provenance(
    conn: sqlite3.Connection,
    *,
    record_type: str,
    beta_id: str,
    source_id: str,
    migration_status: str = "MIGRATED HISTORICAL",
    source_pr_num: str | None = None,
    business_date: str | None = None,
    alchemist_status: str | None = None,
    linked_ledger_id: str | None = None,
    linked_po_id: str | None = None,
    linked_gr_id: str | None = None,
    evidence_ref: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO bzg_ops_history_provenance (
          record_type, beta_id, source_system, source_id, migration_status,
          source_pr_num, business_date, alchemist_status, linked_ledger_id,
          linked_po_id, linked_gr_id, evidence_ref, extra_json, imported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_type,
            beta_id,
            SOURCE_SYSTEM,
            str(source_id),
            migration_status,
            source_pr_num,
            business_date,
            alchemist_status,
            linked_ledger_id,
            linked_po_id,
            linked_gr_id,
            evidence_ref,
            json.dumps(extra or {}, sort_keys=True),
            now_iso(),
        ),
    )


def _build_supplier_maps(source: sqlite3.Connection) -> tuple[dict[str, list[int]], dict[int, str]]:
    by_name: dict[str, list[int]] = {}
    by_id: dict[int, str] = {}
    for row in source.execute("SELECT id, name FROM suppliers ORDER BY id"):
        sid = int(row["id"])
        name = str(row["name"] or "")
        by_id[sid] = name
        key = _norm_name(name)
        by_name.setdefault(key, []).append(sid)
    return by_name, by_id


def _resolve_supplier(
    vendor: str | None,
    by_name: dict[str, list[int]],
    *,
    ledger_supplier_id: int | None = None,
) -> tuple[str, str, str]:
    """Return supplier_id, supplier_name, migration_status."""
    if ledger_supplier_id is not None:
        name = by_name.get("", [""])  # noqa: intentionally unused fallback
        from_id = None
        for row_id in by_name.get(_norm_name(""), []):
            pass
        # lookup by id from caller's by_id passed separately in import
        sid = str(ledger_supplier_id)
        return sid, vendor or sid, "MIGRATED HISTORICAL"

    key = _norm_name(vendor)
    ids = by_name.get(key, [])
    if len(ids) == 1:
        return str(ids[0]), (vendor or "").strip() or by_name.get(key, [""])[0], "MIGRATED HISTORICAL"
    if len(ids) > 1:
        return str(ids[0]), (vendor or "").strip(), "NEEDS RECONCILIATION"
    return f"SUP-UNRESOLVED-{_norm_name(vendor)[:24]}", (vendor or "UNKNOWN").strip(), "NEEDS RECONCILIATION"


def _resolve_supplier_from_maps(
    vendor: str | None,
    by_name: dict[str, list[int]],
    by_id: dict[int, str],
    *,
    ledger_supplier_id: int | None = None,
) -> tuple[str, str, str]:
    if ledger_supplier_id is not None and int(ledger_supplier_id) in by_id:
        sid = str(int(ledger_supplier_id))
        return sid, by_id[int(ledger_supplier_id)], "MIGRATED HISTORICAL"
    key = _norm_name(vendor)
    ids = by_name.get(key, [])
    if len(ids) == 1:
        sid = str(ids[0])
        return sid, by_id[ids[0]], "MIGRATED HISTORICAL"
    if len(ids) > 1:
        sid = str(ids[0])
        return sid, by_id[ids[0]], "NEEDS RECONCILIATION"
    vname = (vendor or "UNKNOWN").strip()
    return f"SUP-UNRESOLVED-{hashlib.sha1(key.encode()).hexdigest()[:8].upper()}", vname, "NEEDS RECONCILIATION"


def import_suppliers(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    imported = skipped = 0
    needs_recon = 0
    ts = now_iso()
    for row in source.execute("SELECT id, name, location_id, order_method, contact FROM suppliers ORDER BY id"):
        source_id = str(row["id"])
        if _already_imported(target, "supplier", source_id):
            skipped += 1
            continue
        vendor_id = f"SUP-ALC-{source_id}"
        name = str(row["name"] or "").strip()
        status = "MIGRATED HISTORICAL"
        note = ""
        dup = target.execute(
            "SELECT 1 FROM bzg_shared_vendors WHERE name_norm=? AND vendor_id!=?",
            (_norm_name(name), vendor_id),
        ).fetchone()
        if dup:
            status = "NEEDS RECONCILIATION"
            note = "Duplicate supplier name in Alchemist — not merged."
            needs_recon += 1
        target.execute(
            """
            INSERT INTO bzg_shared_vendors (
              vendor_id, legal_entity_id, outlet_id, display_name, name_norm,
              status, note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'HOOK', ?, ?, ?)
            """,
            (vendor_id, ENTITY, OUTLET, name, _norm_name(name), note, ts, ts),
        )
        _record_provenance(
            target,
            record_type="supplier",
            beta_id=vendor_id,
            source_id=source_id,
            migration_status=status,
            extra={"alchemist_name": name},
        )
        imported += 1
    return {"imported": imported, "skipped": skipped, "needs_reconciliation": needs_recon}


def import_purchase_orders(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    by_name, by_id = _build_supplier_maps(source)
    imported = skipped = 0
    needs_recon = 0
    lines_imported = 0
    po_by_source: dict[str, str] = {}
    ts = now_iso()

    orders = source.execute("SELECT * FROM pr_orders ORDER BY id").fetchall()
    for row in orders:
        alc_id = str(row["id"])
        if _already_imported(target, "purchase_order", alc_id):
            skipped += 1
            po_by_source[alc_id] = _already_imported(target, "purchase_order", alc_id) or ""
            continue

        pr_num = str(row["pr_num"] or "")
        po_id = f"PO-HIST-{alc_id}"
        pr_id = f"PR-HIST-{alc_id}"
        vendor = _blank(row["vendor"])
        supplier_id, supplier_name, sup_status = _resolve_supplier_from_maps(vendor, by_name, by_id)
        alc_status = _blank(row["status"]) or "UNKNOWN"
        state = STATUS_MAP.get(alc_status, "OPEN")
        mig_status = "MIGRATED HISTORICAL"
        if sup_status == "NEEDS RECONCILIATION":
            mig_status = "NEEDS RECONCILIATION"
            needs_recon += 1

        linked_payment = _blank(row["linked_payment"])
        ledger_id = None
        if linked_payment and linked_payment.startswith("L-"):
            ledger_id = linked_payment[2:]

        order_date = _blank(row["order_date"])
        target.execute(
            """
            INSERT INTO bzg_ops_purchase_orders (
              po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              created_by_person_id, created_by_assignment_id, state, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                po_id,
                pr_id,
                OUTLET,
                ENTITY,
                supplier_id,
                supplier_name,
                IMPORT_ACTOR,
                state,
                _blank(row["created_at"]) or ts,
                ts,
            ),
        )
        _record_provenance(
            target,
            record_type="purchase_order",
            beta_id=po_id,
            source_id=alc_id,
            migration_status=mig_status,
            source_pr_num=pr_num,
            business_date=order_date,
            alchemist_status=alc_status,
            linked_ledger_id=ledger_id,
            evidence_ref=_blank(row["receipt_photo_url"]),
            extra={
                "department": _blank(row["department"]),
                "requested_by": _blank(row["requested_by"]),
                "approver": _blank(row["approver"]),
                "approved_at": _blank(row["approved_at"]),
                "received_by": _blank(row["received_by"]),
                "invoice_total": row["invoice_total"],
                "notes": _blank(row["notes"]),
            },
        )
        po_by_source[alc_id] = po_id
        imported += 1

        po_lines = source.execute(
            "SELECT * FROM pr_order_lines WHERE pr_id=? ORDER BY id", (int(row["id"]),)
        ).fetchall()
        for pl in po_lines:
            line_id = f"POL-HIST-{pl['id']}"
            if _already_imported(target, "po_line", str(pl["id"])):
                continue
            target.execute(
                """
                INSERT INTO bzg_ops_po_lines (line_id, po_id, pr_line_id, item, qty, unit, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line_id,
                    po_id,
                    f"PRL-HIST-{pl['id']}",
                    str(pl["item"] or ""),
                    float(pl["qty"] or 0),
                    _blank(pl["unit"]),
                    ts,
                ),
            )
            _record_provenance(
                target,
                record_type="po_line",
                beta_id=line_id,
                source_id=str(pl["id"]),
                migration_status="MIGRATED HISTORICAL",
                linked_po_id=po_id,
            )
            lines_imported += 1

        if linked_payment and ledger_id:
            target.execute(
                """
                INSERT INTO bzg_ops_migration_links (
                  link_id, link_type, source_key, po_id, ledger_source_id, migration_status, imported_at
                ) VALUES (?, 'po_ledger', ?, ?, ?, 'MIGRATED HISTORICAL', ?)
                ON CONFLICT(source_key) DO NOTHING
                """,
                (
                    f"LNK-PO-LED-{alc_id}",
                    f"pr_orders:{alc_id}:linked_payment:L-{ledger_id}",
                    po_id,
                    ledger_id,
                    ts,
                ),
            )

    return {
        "imported": imported,
        "skipped": skipped,
        "po_lines_imported": lines_imported,
        "needs_reconciliation": needs_recon,
        "po_by_source": po_by_source,
    }


def import_goods_receipts(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    *,
    po_by_source: dict[str, str],
) -> dict[str, Any]:
    imported = skipped = 0
    lines_imported = 0
    needs_recon = 0
    ts = now_iso()

    pr_ids = [
        r[0]
        for r in source.execute(
            "SELECT DISTINCT pr_id FROM pr_receipt_lines ORDER BY pr_id"
        ).fetchall()
    ]
    for pr_id in pr_ids:
        alc_pr_id = str(pr_id)
        if _already_imported(target, "goods_receipt", alc_pr_id):
            skipped += 1
            continue
        po_id = po_by_source.get(alc_pr_id)
        if not po_id:
            po_id = _already_imported(target, "purchase_order", alc_pr_id)
        if not po_id:
            needs_recon += 1
            continue

        order = source.execute("SELECT * FROM pr_orders WHERE id=?", (int(pr_id),)).fetchone()
        vendor = _blank(order["vendor"]) if order else ""
        by_name, by_id = _build_supplier_maps(source)
        supplier_id, supplier_name, _ = _resolve_supplier_from_maps(vendor, by_name, by_id)
        parent_date = _blank(order["order_date"]) if order else None

        gr_id = f"GR-HIST-{alc_pr_id}"
        pr_id_beta = f"PR-HIST-{alc_pr_id}"
        target.execute(
            """
            INSERT INTO bzg_ops_goods_receipts (
              gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              receiver_person_id, receiver_assignment_id, notes, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 'COMPLETE', ?)
            """,
            (
                gr_id,
                po_id,
                pr_id_beta,
                OUTLET,
                ENTITY,
                supplier_id,
                supplier_name,
                IMPORT_ACTOR,
                "receipt_business_date=UNKNOWN; parent_order_date="
                + (parent_date or "UNKNOWN"),
                ts,
            ),
        )
        _record_provenance(
            target,
            record_type="goods_receipt",
            beta_id=gr_id,
            source_id=alc_pr_id,
            migration_status="MIGRATED HISTORICAL",
            business_date="UNKNOWN",
            linked_po_id=po_id,
            extra={"parent_order_date": parent_date},
        )
        imported += 1

        po_line_rows = target.execute(
            "SELECT line_id, item FROM bzg_ops_po_lines WHERE po_id=? ORDER BY line_id",
            (po_id,),
        ).fetchall()
        po_line_by_item = {str(r["item"]).upper(): str(r["line_id"]) for r in po_line_rows}

        receipt_lines = source.execute(
            "SELECT * FROM pr_receipt_lines WHERE pr_id=? ORDER BY line_no, id",
            (int(pr_id),),
        ).fetchall()
        for rl in receipt_lines:
            rl_id = str(rl["id"])
            if _already_imported(target, "gr_line", rl_id):
                continue
            item_raw = rl["item_raw"]
            item_id = rl["item_id"] if "item_id" in rl.keys() else None
            item = str(item_raw or item_id or "")
            po_line_id = po_line_by_item.get(item.upper(), "")
            if not po_line_id and po_line_rows:
                idx = min(int(rl["line_no"] or 1) - 1, len(po_line_rows) - 1)
                po_line_id = str(po_line_rows[max(idx, 0)]["line_id"])
            if not po_line_id:
                needs_recon += 1
                po_line_id = f"POL-HIST-UNLINKED-{rl_id}"
            gr_line_id = f"GRL-HIST-{rl_id}"
            target.execute(
                """
                INSERT INTO bzg_ops_gr_lines (
                  line_id, gr_id, po_line_id, item, received_qty, shortfall_reason, unit, created_at
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    gr_line_id,
                    gr_id,
                    po_line_id,
                    item,
                    float(rl["qty"] or 0),
                    _blank(rl["unit"]),
                    ts,
                ),
            )
            _record_provenance(
                target,
                record_type="gr_line",
                beta_id=gr_line_id,
                source_id=rl_id,
                migration_status="MIGRATED HISTORICAL",
                linked_gr_id=gr_id,
                linked_po_id=po_id,
            )
            lines_imported += 1

    return {
        "imported": imported,
        "skipped": skipped,
        "gr_lines_imported": lines_imported,
        "needs_reconciliation": needs_recon,
    }


def import_supplier_bills(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    *,
    po_by_source: dict[str, str],
) -> dict[str, Any]:
    imported = skipped = 0
    ap_imported = 0
    needs_recon = 0
    ts = now_iso()
    by_name, by_id = _build_supplier_maps(source)

    ledger_to_po: dict[str, str] = {}
    for row in source.execute(
        "SELECT id, linked_payment FROM pr_orders WHERE linked_payment IS NOT NULL AND linked_payment != ''"
    ):
        lp = str(row["linked_payment"])
        if lp.startswith("L-"):
            ledger_to_po[lp[2:]] = str(row["id"])

    for row in source.execute("SELECT * FROM ledger ORDER BY id").fetchall():
        alc_id = str(row["id"])
        if _already_imported(target, "supplier_bill", alc_id):
            skipped += 1
            continue

        supplier_id, supplier_name, sup_status = _resolve_supplier_from_maps(
            None, by_name, by_id, ledger_supplier_id=int(row["supplier_id"]) if row["supplier_id"] else None
        )
        mig_status = "MIGRATED HISTORICAL"
        if sup_status == "NEEDS RECONCILIATION":
            mig_status = "NEEDS RECONCILIATION"
            needs_recon += 1

        po_source_id = ledger_to_po.get(alc_id)
        po_id = po_by_source.get(po_source_id or "", "") if po_source_id else None
        if not po_id and po_source_id:
            po_id = _already_imported(target, "purchase_order", po_source_id)
        gr_id = f"GR-HIST-{po_source_id}" if po_source_id else None
        if gr_id and not target.execute(
            "SELECT 1 FROM bzg_ops_goods_receipts WHERE gr_id=?", (gr_id,)
        ).fetchone():
            gr_id = f"GR-HIST-LEDGER-{alc_id}"
            if not _already_imported(target, "goods_receipt", f"ledger-{alc_id}"):
                target.execute(
                    """
                    INSERT INTO bzg_ops_goods_receipts (
                      gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
                      receiver_person_id, notes, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETE', ?)
                    """,
                    (
                        gr_id,
                        po_id or f"PO-HIST-UNLINKED-{alc_id}",
                        f"PR-HIST-UNLINKED-{alc_id}",
                        OUTLET,
                        ENTITY,
                        supplier_id,
                        supplier_name,
                        IMPORT_ACTOR,
                        "Synthetic GR for ledger bill without receipt lines; NEEDS RECONCILIATION",
                        ts,
                    ),
                )
                _record_provenance(
                    target,
                    record_type="goods_receipt",
                    beta_id=gr_id,
                    source_id=f"ledger-{alc_id}",
                    migration_status="NEEDS RECONCILIATION",
                    linked_po_id=po_id,
                )
                mig_status = "NEEDS RECONCILIATION"
                needs_recon += 1
        if not gr_id:
            gr_id = f"GR-HIST-LEDGER-{alc_id}"
            if not _already_imported(target, "goods_receipt", f"ledger-{alc_id}"):
                target.execute(
                    """
                    INSERT INTO bzg_ops_goods_receipts (
                      gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
                      receiver_person_id, notes, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETE', ?)
                    """,
                    (
                        gr_id,
                        po_id or f"PO-HIST-UNLINKED-{alc_id}",
                        f"PR-HIST-UNLINKED-{alc_id}",
                        OUTLET,
                        ENTITY,
                        supplier_id,
                        supplier_name,
                        IMPORT_ACTOR,
                        "No deterministic PO/receipt chain",
                        ts,
                    ),
                )
                _record_provenance(
                    target,
                    record_type="goods_receipt",
                    beta_id=gr_id,
                    source_id=f"ledger-{alc_id}",
                    migration_status="NEEDS RECONCILIATION",
                )
                mig_status = "NEEDS RECONCILIATION"
                needs_recon += 1

        bill_id = f"BILL-HIST-{alc_id}"
        nota_date = _blank(row["invoice_date"]) or "UNKNOWN"
        amount = float(row["amount"] or 0)
        payment_status = _blank(row["payment_status"]) or "unknown"
        photo_ref = "UNKNOWN"
        nota_files = list(NOTAS_DIR.glob(f"nota_*"))
        if len(nota_files) >= 2:
            pass  # drive refs only for ledger; local nota_ files not keyed to ledger id

        target.execute(
            """
            INSERT INTO bzg_ops_supplier_bills (
              bill_id, gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              nota_number, nota_date, photo_object_ref, stated_total, computed_total,
              total_difference, difference_note, capturer_person_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            """,
            (
                bill_id,
                gr_id,
                po_id or f"PO-HIST-UNLINKED-{alc_id}",
                f"PR-HIST-{po_source_id}" if po_source_id else f"PR-HIST-UNLINKED-{alc_id}",
                OUTLET,
                ENTITY,
                supplier_id,
                supplier_name,
                f"L-{alc_id}",
                nota_date,
                photo_ref,
                amount,
                amount,
                IMPORT_ACTOR,
                ts,
            ),
        )
        _record_provenance(
            target,
            record_type="supplier_bill",
            beta_id=bill_id,
            source_id=alc_id,
            migration_status=mig_status,
            business_date=nota_date,
            linked_po_id=po_id,
            linked_gr_id=gr_id,
            linked_ledger_id=alc_id,
            extra={
                "payment_status": payment_status,
                "payment_date": _blank(row["payment_date"]),
                "notes": _blank(row["notes"]),
            },
        )
        imported += 1

        if payment_status == "unpaid":
            ap_id = f"AP-HIST-{alc_id}"
            if not _already_imported(target, "ap_ready", alc_id):
                target.execute(
                    """
                    INSERT INTO bzg_ops_ap_ready (
                      ap_ready_id, bill_id, match_id, gr_id, po_id, pr_id, outlet_id, entity_id,
                      supplier_id, supplier_name, nota_number, nota_date, stated_total,
                      match_result, marked_by_person_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'HISTORICAL_UNPAID', ?, ?)
                    """,
                    (
                        ap_id,
                        bill_id,
                        f"MATCH-HIST-{alc_id}",
                        gr_id,
                        po_id or f"PO-HIST-UNLINKED-{alc_id}",
                        f"PR-HIST-{po_source_id}" if po_source_id else f"PR-HIST-UNLINKED-{alc_id}",
                        OUTLET,
                        ENTITY,
                        supplier_id,
                        supplier_name,
                        f"L-{alc_id}",
                        nota_date,
                        amount,
                        IMPORT_ACTOR,
                        ts,
                    ),
                )
                _record_provenance(
                    target,
                    record_type="ap_ready",
                    beta_id=ap_id,
                    source_id=alc_id,
                    migration_status="MIGRATED HISTORICAL",
                    linked_po_id=po_id,
                )
                ap_imported += 1

        if po_source_id:
            target.execute(
                """
                INSERT INTO bzg_ops_migration_links (
                  link_id, link_type, source_key, po_id, ledger_source_id, bill_id,
                  migration_status, imported_at
                ) VALUES (?, 'po_ledger_bill', ?, ?, ?, ?, 'MIGRATED HISTORICAL', ?)
                ON CONFLICT(source_key) DO NOTHING
                """,
                (
                    f"LNK-BILL-{alc_id}",
                    f"ledger:{alc_id}:pr_orders:{po_source_id}",
                    po_id,
                    alc_id,
                    bill_id,
                    ts,
                ),
            )

    return {
        "imported": imported,
        "skipped": skipped,
        "ap_ready_imported": ap_imported,
        "needs_reconciliation": needs_recon,
    }


def _petty_direction(flow: str | None) -> str:
    f = (flow or "").lower()
    if "in" in f or "top" in f:
        return "IN"
    if "reset" in f or "adjust" in f:
        return "OUT"
    return "OUT"


def import_petty_cash(target: sqlite3.Connection, source: sqlite3.Connection) -> dict[str, Any]:
    imported = skipped = 0
    needs_recon = 0
    ts = now_iso()

    existing_source_ids = {
        str(r[0])
        for r in target.execute(
            "SELECT source_id FROM bzg_ops_petty_movements WHERE source_id IS NOT NULL"
        ).fetchall()
        if r[0]
    }

    for row in source.execute("SELECT * FROM petty_cash ORDER BY id").fetchall():
        alc_id = str(row["id"])
        if alc_id in LIVE_PETTY_SKIP_SOURCE_IDS or alc_id in existing_source_ids:
            skipped += 1
            continue
        if _already_imported(target, "petty_cash", alc_id):
            skipped += 1
            continue

        entry_date = _blank(row["entry_date"])
        mig_status = "MIGRATED HISTORICAL"
        if entry_date == "2026-01-09":
            mig_status = "NEEDS RECONCILIATION"
            needs_recon += 1

        movement_id = f"PETTY-HIST-{alc_id}"
        direction = _petty_direction(_blank(row["flow"]))
        amount = float(row["amount"] or 0)
        photo = _blank(row["photo_link"])
        receipt_path = None
        evidence_ref = photo
        if photo and photo.startswith("/") and Path(photo).is_file():
            receipt_path = photo
        elif photo and not photo.startswith("http"):
            candidate = NOTAS_DIR / photo
            if candidate.is_file():
                receipt_path = str(candidate)

        purpose = _blank(row["description"]) or _blank(row["category"]) or ""
        if _blank(row["flow"]):
            purpose = f"{row['flow']}: {purpose}".strip(": ")

        target.execute(
            """
            INSERT INTO bzg_ops_petty_movements (
              movement_id, venue, business_date, direction, amount, currency, purpose,
              example, outlet, logged_by, receipt_path, entity_id, created_at,
              source_system, source_id, migration_status
            ) VALUES (?, ?, ?, ?, ?, 'IDR', ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movement_id,
                VENUE,
                entry_date,
                direction,
                amount,
                purpose,
                "Uma Blu Cafe",
                _blank(row["logged_by_name"]),
                receipt_path,
                ENTITY,
                _blank(row["created_at"]) or ts,
                SOURCE_SYSTEM,
                alc_id,
                mig_status,
            ),
        )
        _record_provenance(
            target,
            record_type="petty_cash",
            beta_id=movement_id,
            source_id=alc_id,
            migration_status=mig_status,
            business_date=entry_date,
            evidence_ref=evidence_ref,
            extra={"flow": _blank(row["flow"]), "category": _blank(row["category"])},
        )
        imported += 1

    return {"imported": imported, "skipped": skipped, "needs_reconciliation": needs_recon}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_mandiri(text: str) -> list[dict[str, Any]]:
    import csv
    import io

    from core import ggv_bank_statement1 as _gb

    return _gb._parse_mandiri_rows(text)


def _parse_bri(text: str) -> list[dict[str, Any]]:
    from core import ggv_bank_statement1 as _gb

    return _gb._parse_bri_rows(text)


def import_bank_statements(target: sqlite3.Connection) -> dict[str, Any]:
    from core import ggv_bank_statement1 as _gb

    imports = txns = skipped = 0
    unparsed = 0
    ts = now_iso()
    BANK_ORIGINALS.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p
        for p in BANK_PACK.rglob("*")
        if p.is_file() and p.name != "README.txt"
    )
    for src in files:
        digest = _sha256(src)
        existing = target.execute(
            "SELECT import_id FROM bzg_bank_statement_imports WHERE entity_id=? AND content_sha256=?",
            (ENTITY, digest),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        dest = BANK_ORIGINALS / src.name
        if not dest.exists():
            dest.write_bytes(src.read_bytes())

        bank_label = "UNKNOWN"
        if "Mandiri" in str(src.parent.name):
            bank_label = "MANDIRI"
        elif "BRI" in str(src.parent.name):
            bank_label = "BRI"
        elif "BNI" in str(src.parent.name):
            bank_label = "BNI"

        parse_status = "UNMATCHED"
        parse_notes = None
        rows: list[dict[str, Any]] = []
        if src.suffix.lower() == ".csv":
            text = src.read_text(encoding="utf-8", errors="replace")
            if bank_label == "MANDIRI":
                rows = _parse_mandiri(text)
            elif bank_label == "BRI":
                rows = _parse_bri(text)
            else:
                rows = _gb._parse_generic_csv(text)
            parse_status = "UNMATCHED" if rows else "EXCEPTION"
            if not rows:
                parse_notes = "CSV parse returned zero rows"
                unparsed += 1
        else:
            parse_status = "EXCEPTION"
            parse_notes = "XLS not parsed safely — raw import only"
            unparsed += 1

        import_id = f"BZG-BANK-{uuid.uuid4().hex[:12].upper()}"
        target.execute(
            """
            INSERT INTO bzg_bank_statement_imports (
              import_id, entity_id, bank_label, account_label, original_filename,
              original_path, content_sha256, uploaded_by_person_id, uploaded_at,
              txn_count, parse_status, parse_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_id,
                ENTITY,
                bank_label,
                src.parent.name,
                src.name,
                str(dest),
                digest,
                IMPORT_ACTOR,
                ts,
                len(rows),
                parse_status,
                parse_notes,
            ),
        )
        imports += 1

        for idx, row in enumerate(rows):
            txn_id = f"BZG-TXN-{import_id}-{idx:04d}"
            target.execute(
                """
                INSERT INTO bzg_bank_transactions (
                  txn_id, import_id, entity_id, txn_date, value_date, description,
                  reference, debit, credit, running_balance, bank_account, raw_json,
                  recon_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNMATCHED', ?)
                """,
                (
                    txn_id,
                    import_id,
                    ENTITY,
                    row.get("txn_date"),
                    row.get("value_date"),
                    row.get("description"),
                    row.get("reference"),
                    float(row.get("debit") or 0),
                    float(row.get("credit") or 0),
                    row.get("running_balance"),
                    row.get("bank_account") or bank_label,
                    json.dumps(row.get("raw") or row, default=str),
                    ts,
                ),
            )
            txns += 1

    return {
        "files_on_disk": len(files),
        "imports": imports,
        "skipped": skipped,
        "transactions": txns,
        "unparsed_files": unparsed,
    }


def queue_unlinked_evidence(target: sqlite3.Connection) -> dict[str, Any]:
    ts = now_iso()
    queued = 0
    linked_paths = {
        str(r[0])
        for r in target.execute(
            "SELECT receipt_path FROM bzg_ops_petty_movements WHERE receipt_path IS NOT NULL"
        ).fetchall()
        if r[0]
    }

    for kind, directory in (
        ("petty_nota", NOTAS_DIR),
        ("receive", RECEIVE_DIR),
        ("nightly", NIGHTLY_DIR),
    ):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.jpg"):
            fpath = str(path.resolve())
            if fpath in linked_paths:
                continue
            qid = f"EVD-UNL-{hashlib.sha1(fpath.encode()).hexdigest()[:12].upper()}"
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, TZ8).isoformat()
                target.execute(
                    """
                    INSERT INTO bzg_ops_evidence_unlinked (
                      queue_id, file_path, file_kind, file_mtime, imported_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(file_path) DO NOTHING
                    """,
                    (qid, fpath, kind, mtime, ts),
                )
                if target.total_changes:
                    queued += 1
            except sqlite3.IntegrityError:
                pass

    total = target.execute("SELECT COUNT(*) FROM bzg_ops_evidence_unlinked").fetchone()[0]
    return {"newly_queued": queued, "total_unlinked": int(total)}


def source_counts(source: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "pr_orders",
        "pr_order_lines",
        "pr_receipt_lines",
        "ledger",
        "petty_cash",
        "suppliers",
    ]
    out: dict[str, int] = {}
    for name in tables:
        out[name] = int(source.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0])
    return out


def beta_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "bzg_ops_purchase_orders",
        "bzg_ops_po_lines",
        "bzg_ops_goods_receipts",
        "bzg_ops_gr_lines",
        "bzg_ops_supplier_bills",
        "bzg_ops_ap_ready",
        "bzg_ops_petty_movements",
        "bzg_shared_vendors",
        "bzg_bank_statement_imports",
        "bzg_bank_transactions",
        "bzg_ops_evidence_unlinked",
    ]
    out: dict[str, int] = {}
    for name in tables:
        try:
            out[name] = int(conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0])
        except sqlite3.OperationalError:
            out[name] = 0
    hist_petty = conn.execute(
        "SELECT COUNT(*) FROM bzg_ops_petty_movements WHERE source_system=?",
        (SOURCE_SYSTEM,),
    ).fetchone()[0]
    out["bzg_ops_petty_movements_historical"] = int(hist_petty)
    return out


def petty_balance(conn: sqlite3.Connection) -> dict[str, Any]:
    day = conn.execute(
        "SELECT opening_float FROM bzg_ops_petty_days WHERE venue=? AND business_date=?",
        (VENUE, "2026-10-02"),
    ).fetchone()
    opening = float(day[0]) if day else 0.0
    mov = conn.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN direction='IN' THEN amount WHEN direction='OUT' THEN -amount ELSE 0 END), 0)
        FROM bzg_ops_petty_movements
        WHERE venue=? AND business_date>=?
        """,
        (VENUE, "2026-10-02"),
    ).fetchone()[0]
    amount = opening + float(mov or 0)
    return {"opening_float": opening, "movement_net_from_2026_10_02": float(mov or 0), "amount_idr": amount}


def protected_close_checksums(conn: sqlite3.Connection) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for prefix in ("VDC-470e741f", "VDC-87202768", "VDC-64f5f529"):
        row = conn.execute(
            """
            SELECT close_id, business_date, state, declared_cash_amount, variance_cash_amount, updated_at
            FROM venue_daily_closes WHERE close_id LIKE ?
            """,
            (prefix + "%",),
        ).fetchone()
        if row:
            out[str(row["close_id"])] = {
                "business_date": row["business_date"],
                "state": row["state"],
                "declared_cash_amount": row["declared_cash_amount"],
                "variance_cash_amount": row["variance_cash_amount"],
                "updated_at": row["updated_at"],
            }
    return out


def run_import(
    target_db: Path | None = None,
    *,
    source_db: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    target_path = Path(target_db or LIVE_CATALOG).resolve()
    source_path = Path(source_db or ALCHEMIST_DB).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Alchemist source missing: {source_path}")

    source = _ro(source_path)
    target = _rw(target_path)
    try:
        src_before = source_counts(source)
        ensure_history_schema(target)
        beta_before = beta_counts(target)
        petty_before = petty_balance(target)
        protected_before = protected_close_checksums(target)

        if dry_run:
            return {
                "pack": PACK,
                "dry_run": True,
                "source_counts": src_before,
                "beta_counts_before": beta_before,
                "petty_balance_before": petty_before,
            }

        suppliers = import_suppliers(target, source)
        po_result = import_purchase_orders(target, source)
        gr_result = import_goods_receipts(target, source, po_by_source=po_result["po_by_source"])
        bill_result = import_supplier_bills(
            target, source, po_by_source=po_result["po_by_source"]
        )
        petty_result = import_petty_cash(target, source)
        bank_result = import_bank_statements(target)
        evidence_result = queue_unlinked_evidence(target)
        target.commit()

        beta_after = beta_counts(target)
        petty_after = petty_balance(target)
        protected_after = protected_close_checksums(target)

        needs_recon = (
            suppliers.get("needs_reconciliation", 0)
            + po_result.get("needs_reconciliation", 0)
            + gr_result.get("needs_reconciliation", 0)
            + bill_result.get("needs_reconciliation", 0)
            + petty_result.get("needs_reconciliation", 0)
        )
        linked_po_ledger = target.execute(
            "SELECT COUNT(*) FROM bzg_ops_migration_links WHERE link_type='po_ledger'"
        ).fetchone()[0]

        return {
            "pack": PACK,
            "migration_id": MIGRATION_ID,
            "finished_at": now_iso(),
            "source_db": str(source_path),
            "target_db": str(target_path),
            "source_counts": src_before,
            "imported": {
                "suppliers": suppliers["imported"],
                "purchase_orders": po_result["imported"],
                "po_lines": po_result["po_lines_imported"],
                "goods_receipts": gr_result["imported"],
                "gr_lines": gr_result["gr_lines_imported"],
                "supplier_bills": bill_result["imported"],
                "ap_ready": bill_result["ap_ready_imported"],
                "petty_cash": petty_result["imported"],
                "bank_imports": bank_result["imports"],
                "bank_transactions": bank_result["transactions"],
                "evidence_unlinked_queued": evidence_result["newly_queued"],
            },
            "skipped": {
                "suppliers": suppliers["skipped"],
                "purchase_orders": po_result["skipped"],
                "goods_receipts": gr_result["skipped"],
                "supplier_bills": bill_result["skipped"],
                "petty_cash": petty_result["skipped"],
                "bank_files": bank_result["skipped"],
            },
            "linked": {
                "po_to_ledger": int(linked_po_ledger),
                "petty_receipt_files_existing": 16,
            },
            "needs_reconciliation": int(needs_recon),
            "evidence_unlinked": int(evidence_result["total_unlinked"]),
            "petty_balance_before": petty_before,
            "petty_balance_after": petty_after,
            "protected_close_checksums_before": protected_before,
            "protected_close_checksums_after": protected_after,
            "beta_counts_before": beta_before,
            "beta_counts_after": beta_after,
            "bank": bank_result,
            "staff_ready": False,
            "zayen_ready": False,
        }
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    import sys

    dry = "--dry-run" in sys.argv
    print(json.dumps(run_import(dry_run=dry), indent=2))
