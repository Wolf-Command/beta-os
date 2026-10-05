#!/usr/bin/env python3
"""BZG-EVIDENCE-LINK-1 — deterministic linkage of possessed BZG historical evidence files.

High-confidence auto-link only on exact keys. Ambiguous candidates go to reconciliation
queue. Unmatched stays UNLINKED. staff_ready stays false.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_history_import1 as _hist

PACK = "BZG-EVIDENCE-LINK-1"
MIGRATION_ID = "bzg_evidence_link1_20261005"
ENTITY = _hist.ENTITY
SCHEMA = "bzg.evidence.link.v1"
ALCHEMIST_DB = _hist.ALCHEMIST_DB
POSSESSED_SCHEME = "alchemist-possessed://"
TZ8 = timezone(timedelta(hours=8))

RECORD_TYPES = frozenset(
    {
        "purchase_order",
        "goods_receipt",
        "supplier_bill",
        "petty_cash",
        "bank_import",
    }
)

RECORD_PRIORITY = {
    "purchase_order": 0,
    "supplier_bill": 1,
    "goods_receipt": 2,
    "petty_cash": 3,
    "bank_import": 4,
}

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "payment_execute": False,
    "read_only": True,
    "entity_id": ENTITY,
    "auto_linked": True,
}


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def public(**extra: Any) -> dict[str, Any]:
    out = {**HONESTY}
    out.update(extra)
    out["staff_ready"] = False
    out["zayen_ready"] = False
    return out


def possessed_object_ref(file_path: str | Path) -> str:
    return f"{POSSESSED_SCHEME}{Path(file_path).name}"


def resolve_possessed_path(object_ref: str | None) -> Path | None:
    ref = (object_ref or "").strip()
    if not ref.startswith(POSSESSED_SCHEME):
        return None
    name = ref[len(POSSESSED_SCHEME) :].strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    for directory in (_hist.NOTAS_DIR, _hist.RECEIVE_DIR, _hist.NIGHTLY_DIR):
        if not directory.is_dir():
            continue
        candidate = (directory / name).resolve()
        try:
            candidate.relative_to(directory.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def ensure_evidence_link_schema(conn: sqlite3.Connection) -> list[str]:
    added: list[str] = []
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bzg_ops_evidence_links (
          link_id TEXT PRIMARY KEY,
          queue_id TEXT NOT NULL UNIQUE,
          file_path TEXT NOT NULL,
          file_kind TEXT NOT NULL,
          record_type TEXT NOT NULL,
          record_id TEXT NOT NULL,
          match_rule TEXT NOT NULL,
          confidence TEXT NOT NULL,
          provenance_json TEXT,
          linked_at TEXT NOT NULL,
          UNIQUE(file_path, record_type, record_id)
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_evidence_links_record
          ON bzg_ops_evidence_links(record_type, record_id);
        CREATE INDEX IF NOT EXISTS idx_bzg_evidence_links_file
          ON bzg_ops_evidence_links(file_path);

        CREATE TABLE IF NOT EXISTS bzg_ops_evidence_recon_queue (
          recon_id TEXT PRIMARY KEY,
          queue_id TEXT,
          file_path TEXT,
          record_type TEXT,
          match_rule TEXT NOT NULL,
          candidates_json TEXT NOT NULL,
          imported_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_evidence_recon_file
          ON bzg_ops_evidence_recon_queue(file_path);
        """
    )
    added.extend(["bzg_ops_evidence_links", "bzg_ops_evidence_recon_queue"])
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bzg_ops_evidence_unlinked)").fetchall()}
    if "linked_record_type" not in cols:
        conn.execute("ALTER TABLE bzg_ops_evidence_unlinked ADD COLUMN linked_record_type TEXT")
        conn.execute("ALTER TABLE bzg_ops_evidence_unlinked ADD COLUMN linked_record_id TEXT")
        conn.execute("ALTER TABLE bzg_ops_evidence_unlinked ADD COLUMN match_rule TEXT")
        added.append("bzg_ops_evidence_unlinked.linked_*")
    return added


@dataclass
class _QueueRow:
    queue_id: str
    file_path: str
    file_kind: str
    migration_status: str = "EVIDENCE UNLINKED"


def _basename(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text or text.startswith("http"):
        return None
    return Path(text).name or None


def _amount_key(value: Any) -> float:
    return round(float(value or 0), 2)


def _bill_unique_keys(conn: sqlite3.Connection) -> dict[tuple[str, str, float], list[str]]:
    out: dict[tuple[str, str, float], list[str]] = defaultdict(list)
    for row in conn.execute(
        "SELECT bill_id, supplier_id, nota_date, stated_total FROM bzg_ops_supplier_bills"
    ):
        key = (str(row["supplier_id"]), str(row["nota_date"]), _amount_key(row["stated_total"]))
        out[key].append(str(row["bill_id"]))
    return out


def _petty_unique_keys(conn: sqlite3.Connection) -> dict[tuple[str, str, float], list[str]]:
    tg_by_source: dict[str, str] = {}
    if ALCHEMIST_DB.is_file():
        src = sqlite3.connect(f"file:{ALCHEMIST_DB}?mode=ro", uri=True)
        try:
            for row in src.execute("SELECT id, logged_by_tg_id FROM petty_cash"):
                tg_by_source[str(row[0])] = str(row[1] if row[1] is not None else "")
        finally:
            src.close()
    out: dict[tuple[str, str, float], list[str]] = defaultdict(list)
    for row in conn.execute(
        """
        SELECT movement_id, business_date, amount, source_id
        FROM bzg_ops_petty_movements
        WHERE source_system=?
        """,
        (_hist.SOURCE_SYSTEM,),
    ):
        tg_val = tg_by_source.get(str(row["source_id"] or ""), "")
        key = (tg_val, str(row["business_date"]), _amount_key(row["amount"]))
        out[key].append(str(row["movement_id"]))
    return out


def _load_alchemist_filename_refs() -> dict[str, list[dict[str, str]]]:
    """Map basename -> alchemist-backed record hints (source_id + kind)."""
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not ALCHEMIST_DB.is_file():
        return out
    src = sqlite3.connect(f"file:{ALCHEMIST_DB}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        for row in src.execute(
            "SELECT id, photo_link FROM petty_cash WHERE photo_link IS NOT NULL AND TRIM(photo_link) != ''"
        ):
            name = _basename(row["photo_link"])
            if name:
                out[name].append({"kind": "petty_cash", "source_id": str(row["id"])})
        for row in src.execute(
            """
            SELECT id, receipt_photo_url FROM pr_orders
            WHERE receipt_photo_url IS NOT NULL AND TRIM(receipt_photo_url) != ''
            """
        ):
            name = _basename(row["receipt_photo_url"])
            if name:
                out[name].append({"kind": "purchase_order", "source_id": str(row["id"])})
    finally:
        src.close()
    return out


def _provenance_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in conn.execute(
        """
        SELECT record_type, beta_id, source_id, evidence_ref, source_pr_num, linked_po_id
        FROM bzg_ops_history_provenance
        WHERE record_type IN ('purchase_order','goods_receipt','supplier_bill','petty_cash')
        """
    ):
        rows.append(dict(row))
    for row in conn.execute(
        "SELECT import_id, original_filename, original_path FROM bzg_bank_statement_imports WHERE entity_id=?",
        (ENTITY,),
    ):
        rows.append(
            {
                "record_type": "bank_import",
                "beta_id": str(row["import_id"]),
                "source_id": str(row["import_id"]),
                "evidence_ref": str(row["original_path"] or ""),
                "source_pr_num": None,
                "linked_po_id": None,
                "filename": str(row["original_filename"] or ""),
            }
        )
    return rows


def _token_in_filename(token: str, filename: str) -> bool:
    if not token or not filename:
        return False
    pat = re.compile(r"(?:^|_)" + re.escape(token) + r"(?:[._-]|$)")
    return bool(pat.search(filename))


def _build_match_indexes(
    conn: sqlite3.Connection,
) -> tuple[dict[str, Any], dict[tuple[str, str], str]]:
    prov = _provenance_candidates(conn)
    alc_names = _load_alchemist_filename_refs()
    petty_keys = _petty_unique_keys(conn)

    source_to_beta = {
        (str(r["record_type"]), str(r["source_id"])): str(r["beta_id"]) for r in prov if r.get("source_id")
    }

    path_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    basename_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pr_doc_index: dict[str, str] = {}
    bill_doc_index: dict[str, str] = {}
    bill_unique_by_basename: dict[str, dict[str, Any]] = {}
    petty_unique_by_basename: dict[str, dict[str, Any]] = {}

    for row in prov:
        rt = str(row["record_type"])
        bid = str(row["beta_id"])
        ev = (row.get("evidence_ref") or "").strip()
        if ev and not ev.startswith("http"):
            path_index[ev].append(row)
            name = _basename(ev)
            if name:
                basename_index[name].append(row)
        if rt == "purchase_order" and row.get("source_pr_num"):
            pr_doc_index[str(row["source_pr_num"])] = bid

    bill_keys = _bill_unique_keys(conn)
    bill_prov = {str(r["beta_id"]): r for r in prov if r["record_type"] == "supplier_bill"}
    for row in conn.execute("SELECT bill_id, nota_number FROM bzg_ops_supplier_bills"):
        bill_doc_index[str(row["nota_number"])] = str(row["bill_id"])
    for key, bill_ids in bill_keys.items():
        if len(bill_ids) != 1:
            continue
        bill_id = bill_ids[0]
        bp = bill_prov.get(bill_id)
        if not bp:
            continue
        ev_name = _basename(bp.get("evidence_ref"))
        if ev_name:
            bill_unique_by_basename[ev_name] = {
                "bill_id": bill_id,
                "supplier_id": key[0],
                "nota_date": key[1],
                "amount": key[2],
            }

    for fname, hints in alc_names.items():
        petty_hint = next((h for h in hints if h["kind"] == "petty_cash"), None)
        if not petty_hint:
            continue
        beta_id = source_to_beta.get(("petty_cash", petty_hint["source_id"]))
        if not beta_id:
            continue
        row = conn.execute(
            "SELECT business_date, amount, source_id FROM bzg_ops_petty_movements WHERE movement_id=?",
            (beta_id,),
        ).fetchone()
        if not row:
            continue
        tg = ""
        if ALCHEMIST_DB.is_file() and row["source_id"]:
            src = sqlite3.connect(f"file:{ALCHEMIST_DB}?mode=ro", uri=True)
            try:
                tg_row = src.execute(
                    "SELECT logged_by_tg_id FROM petty_cash WHERE id=?", (int(row["source_id"]),)
                ).fetchone()
                tg = str(tg_row[0] if tg_row else "")
            except (ValueError, sqlite3.OperationalError):
                tg = ""
            finally:
                src.close()
        key = (tg, str(row["business_date"]), _amount_key(row["amount"]))
        ids = petty_keys.get(key, [])
        if len(ids) == 1 and ids[0] == beta_id:
            petty_unique_by_basename[fname] = {
                "movement_id": beta_id,
                "tg_id": tg,
                "business_date": key[1],
                "amount": key[2],
            }

    return {
        "prov": prov,
        "alc_names": alc_names,
        "source_to_beta": source_to_beta,
        "path_index": path_index,
        "basename_index": basename_index,
        "pr_doc_index": pr_doc_index,
        "bill_doc_index": bill_doc_index,
        "bill_unique_by_basename": bill_unique_by_basename,
        "petty_unique_by_basename": petty_unique_by_basename,
    }, source_to_beta


def _collect_rule_candidates(
    conn: sqlite3.Connection,
    queue_rows: list[Any],
    *,
    indexes: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (auto_candidates, recon_entries)."""
    if indexes is None:
        indexes, _ = _build_match_indexes(conn)

    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    recon: list[dict[str, Any]] = []

    for q in queue_rows:
        file_path = str(q["file_path"])
        queue_id = str(q["queue_id"])
        file_kind = str(q["file_kind"])
        fname = Path(file_path).name
        resolved = str(Path(file_path).resolve())

        def add_candidate(
            record_type: str,
            record_id: str,
            match_rule: str,
            confidence: str,
            provenance: dict[str, Any],
        ) -> None:
            by_file[file_path].append(
                {
                    "queue_id": queue_id,
                    "file_path": file_path,
                    "file_kind": file_kind,
                    "record_type": record_type,
                    "record_id": record_id,
                    "match_rule": match_rule,
                    "confidence": confidence,
                    "provenance": provenance,
                }
            )

        for row in indexes["path_index"].get(file_path, []):
            ev = (row.get("evidence_ref") or "").strip()
            if ev == file_path or ev == resolved:
                add_candidate(
                    str(row["record_type"]),
                    str(row["beta_id"]),
                    "exact_path_ref",
                    "HIGH",
                    {"evidence_ref": ev, "source": "provenance"},
                )

        for row in indexes["basename_index"].get(fname, []):
            add_candidate(
                str(row["record_type"]),
                str(row["beta_id"]),
                "exact_filename_ref",
                "HIGH",
                {"basename": fname, "source": "provenance.evidence_ref"},
            )
        for hint in indexes["alc_names"].get(fname, []):
            beta_id = indexes["source_to_beta"].get((hint["kind"], hint["source_id"]))
            if beta_id:
                add_candidate(
                    hint["kind"],
                    beta_id,
                    "exact_filename_ref",
                    "HIGH",
                    {"basename": fname, "source": f"alchemist.{hint['kind']}", "source_id": hint["source_id"]},
                )

        for token in re.findall(r"PR-\d+", fname):
            po_id = indexes["pr_doc_index"].get(token)
            if po_id and _token_in_filename(token, fname):
                add_candidate(
                    "purchase_order",
                    po_id,
                    "exact_document_number",
                    "HIGH",
                    {"document_number": token, "source": "source_pr_num"},
                )
        for token in re.findall(r"L-\d+", fname):
            bill_id = indexes["bill_doc_index"].get(token)
            if bill_id and _token_in_filename(token, fname):
                add_candidate(
                    "supplier_bill",
                    bill_id,
                    "exact_document_number",
                    "HIGH",
                    {"document_number": token, "source": "nota_number"},
                )

        bill_unique = indexes["bill_unique_by_basename"].get(fname)
        if bill_unique:
            add_candidate(
                "supplier_bill",
                bill_unique["bill_id"],
                "exact_supplier_date_amount_unique",
                "HIGH",
                {
                    "supplier_id": bill_unique["supplier_id"],
                    "nota_date": bill_unique["nota_date"],
                    "amount": bill_unique["amount"],
                    "source": "supplier_id+nota_date+stated_total",
                },
            )

        petty_unique = indexes["petty_unique_by_basename"].get(fname)
        if petty_unique and file_kind == "petty_nota" and fname.startswith(("petty_", "topup_")):
            add_candidate(
                "petty_cash",
                petty_unique["movement_id"],
                "exact_supplier_date_amount_unique",
                "HIGH",
                {
                    "tg_id": petty_unique["tg_id"],
                    "business_date": petty_unique["business_date"],
                    "amount": petty_unique["amount"],
                    "source": "tg_id+entry_date+amount",
                },
            )

    auto: list[dict[str, Any]] = []
    for file_path, candidates in by_file.items():
        # De-duplicate identical record targets
        dedup: dict[tuple[str, str], dict[str, Any]] = {}
        for c in candidates:
            key = (c["record_type"], c["record_id"])
            if key not in dedup or RECORD_PRIORITY.get(c["record_type"], 99) < RECORD_PRIORITY.get(
                dedup[key]["record_type"], 99
            ):
                dedup[key] = c
        unique = list(dedup.values())
        if not unique:
            continue
        if len(unique) == 1:
            auto.append(unique[0])
            continue

        # PO + child GR sharing one recv file -> PO wins deterministically
        po_ids = {c["record_id"] for c in unique if c["record_type"] == "purchase_order"}
        gr_only = [c for c in unique if c["record_type"] == "goods_receipt"]
        if len(po_ids) == 1 and gr_only and len(unique) == len(gr_only) + 1:
            po_candidate = next(c for c in unique if c["record_type"] == "purchase_order")
            gr_row = conn.execute(
                "SELECT linked_po_id FROM bzg_ops_history_provenance WHERE record_type='goods_receipt' AND beta_id=?",
                (gr_only[0]["record_id"],),
            ).fetchone()
            if gr_row and str(gr_row["linked_po_id"] or "") == po_candidate["record_id"]:
                auto.append(po_candidate)
                continue

        recon.append(
            {
                "queue_id": unique[0]["queue_id"],
                "file_path": file_path,
                "record_type": None,
                "match_rule": "ambiguous_multi_candidate",
                "candidates": [
                    {
                        "record_type": c["record_type"],
                        "record_id": c["record_id"],
                        "match_rule": c["match_rule"],
                        "confidence": c["confidence"],
                    }
                    for c in unique
                ],
            }
        )
    return auto, recon


def _apply_record_updates(conn: sqlite3.Connection, link: dict[str, Any]) -> None:
    record_type = link["record_type"]
    record_id = link["record_id"]
    file_path = link["file_path"]
    obj_ref = possessed_object_ref(file_path)

    conn.execute(
        """
        UPDATE bzg_ops_history_provenance
        SET evidence_ref=?
        WHERE record_type=? AND beta_id=?
        """,
        (file_path, record_type, record_id),
    )

    if record_type == "supplier_bill":
        row = conn.execute(
            "SELECT photo_object_ref FROM bzg_ops_supplier_bills WHERE bill_id=?",
            (record_id,),
        ).fetchone()
        if row and str(row["photo_object_ref"] or "").upper() == "UNKNOWN":
            conn.execute(
                "UPDATE bzg_ops_supplier_bills SET photo_object_ref=? WHERE bill_id=?",
                (obj_ref, record_id),
            )

    if record_type == "petty_cash":
        conn.execute(
            """
            UPDATE bzg_ops_petty_movements
            SET receipt_path=?
            WHERE movement_id=? AND (receipt_path IS NULL OR TRIM(receipt_path)='')
            """,
            (file_path, record_id),
        )

    if record_type == "bank_import":
        pass


def link_counts(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bzg_ops_evidence%'"
        ).fetchall()
    }
    unlinked = int(
        conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE migration_status='EVIDENCE UNLINKED'"
        ).fetchone()[0]
    )
    linked = 0
    recon = 0
    if "bzg_ops_evidence_links" in tables:
        linked = int(conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_links").fetchone()[0])
    if "bzg_ops_evidence_recon_queue" in tables:
        recon = int(conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue").fetchone()[0])
    by_rule: dict[str, int] = {}
    if "bzg_ops_evidence_links" in tables:
        for row in conn.execute(
            "SELECT match_rule, COUNT(*) AS n FROM bzg_ops_evidence_links GROUP BY match_rule"
        ):
            by_rule[str(row["match_rule"])] = int(row["n"])
    return {
        "unlinked": unlinked,
        "linked": linked,
        "needs_reconciliation": recon,
        "by_rule": by_rule,
    }


def matched_snapshot(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if conn.row_factory is None:
        conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT link_id, queue_id, file_path, file_kind, record_type, record_id,
               match_rule, confidence, provenance_json, linked_at
        FROM bzg_ops_evidence_links
        ORDER BY file_path, record_type, record_id
        """
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        if item.get("provenance_json"):
            try:
                item["provenance"] = json.loads(item["provenance_json"])
            except json.JSONDecodeError:
                item["provenance"] = {}
        out.append(item)
    return out


def reproduce_link(conn: sqlite3.Connection, link: dict[str, Any]) -> bool:
    """Verify one stored link is reproducible from its recorded rule."""
    file_path = str(link["file_path"])
    queue = conn.execute(
        "SELECT * FROM bzg_ops_evidence_unlinked WHERE file_path=? OR queue_id=?",
        (file_path, link.get("queue_id")),
    ).fetchone()
    if queue:
        rows = [queue]
    else:
        rows = [
            _QueueRow(
                queue_id=link.get("queue_id")
                or f"EVD-REPLAY-{hashlib.sha1(file_path.encode()).hexdigest()[:12].upper()}",
                file_path=file_path,
                file_kind=str(link.get("file_kind") or "receive"),
            )
        ]
    indexes, _ = _build_match_indexes(conn)
    auto, _recon = _collect_rule_candidates(conn, rows, indexes=indexes)
    for cand in auto:
        if (
            cand["file_path"] == file_path
            and cand["record_type"] == link["record_type"]
            and cand["record_id"] == link["record_id"]
            and cand["match_rule"] == link["match_rule"]
        ):
            return True
    return False


def apply_evidence_links(
    conn: sqlite3.Connection,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    ensure_evidence_link_schema(conn)
    ts = now_iso()

    queue_rows = conn.execute(
        """
        SELECT queue_id, file_path, file_kind, migration_status
        FROM bzg_ops_evidence_unlinked
        WHERE migration_status='EVIDENCE UNLINKED'
        ORDER BY file_path
        """
    ).fetchall()

    indexes, _ = _build_match_indexes(conn)
    auto_candidates, recon_entries = _collect_rule_candidates(conn, queue_rows, indexes=indexes)

    linked_ids: list[str] = []
    for cand in auto_candidates:
        link_id = f"EVL-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO bzg_ops_evidence_links (
              link_id, queue_id, file_path, file_kind, record_type, record_id,
              match_rule, confidence, provenance_json, linked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(queue_id) DO NOTHING
            """,
            (
                link_id,
                cand["queue_id"],
                cand["file_path"],
                cand["file_kind"],
                cand["record_type"],
                cand["record_id"],
                cand["match_rule"],
                cand["confidence"],
                json.dumps(cand.get("provenance") or {}, sort_keys=True),
                ts,
            ),
        )
        if not conn.total_changes:
            continue
        _apply_record_updates(conn, cand)
        conn.execute(
            """
            UPDATE bzg_ops_evidence_unlinked
            SET migration_status='EVIDENCE LINKED',
                linked_record_type=?,
                linked_record_id=?,
                match_rule=?
            WHERE queue_id=?
            """,
            (cand["record_type"], cand["record_id"], cand["match_rule"], cand["queue_id"]),
        )
        linked_ids.append(link_id)

    for entry in recon_entries:
        recon_id = f"EVR-{hashlib.sha1(entry['file_path'].encode()).hexdigest()[:12].upper()}"
        conn.execute(
            """
            INSERT INTO bzg_ops_evidence_recon_queue (
              recon_id, queue_id, file_path, record_type, match_rule, candidates_json, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recon_id) DO UPDATE SET
              candidates_json=excluded.candidates_json,
              imported_at=excluded.imported_at
            """,
            (
                recon_id,
                entry.get("queue_id"),
                entry.get("file_path"),
                entry.get("record_type"),
                entry["match_rule"],
                json.dumps(entry.get("candidates") or [], sort_keys=True),
                ts,
            ),
        )
        if entry.get("queue_id"):
            conn.execute(
                """
                UPDATE bzg_ops_evidence_unlinked
                SET migration_status='NEEDS RECONCILIATION'
                WHERE queue_id=? AND migration_status='EVIDENCE UNLINKED'
                """,
                (entry["queue_id"],),
            )

    if commit:
        conn.commit()

    counts = link_counts(conn)
    return public(
        ok=True,
        schema=SCHEMA,
        applied_at=ts,
        queue_before=len(queue_rows),
        auto_linked=len(linked_ids),
        recon_queued=len(recon_entries),
        **counts,
    )


def evidence_for_record(
    conn: sqlite3.Connection,
    record_type: str,
    record_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT file_path, match_rule, confidence, provenance_json, linked_at
        FROM bzg_ops_evidence_links
        WHERE record_type=? AND record_id=?
        """,
        (record_type, record_id),
    ).fetchone()
    if not row:
        return None
    prov = {}
    if row["provenance_json"]:
        try:
            prov = json.loads(row["provenance_json"])
        except json.JSONDecodeError:
            prov = {}
    path = str(row["file_path"])
    return {
        "linked": True,
        "file_path": path,
        "photo_object_ref": possessed_object_ref(path),
        "match_rule": row["match_rule"],
        "confidence": row["confidence"],
        "provenance": prov,
        "linked_at": row["linked_at"],
    }
