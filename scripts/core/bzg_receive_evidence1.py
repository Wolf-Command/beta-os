#!/usr/bin/env python3
"""FC-BZG-RECEIVE-EVIDENCE-1 — human review queue for historical receive photos.

Deterministic proposals for file_kind=receive only. Never auto-links beyond exact rules.
staff_ready stays false.
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

from core import audit as _audit
from core import bzg_evidence_link1 as _evlink
from core import bzg_finance_desk as _desk
from core import bzg_history_import1 as _hist

PACK = "FC-BZG-RECEIVE-EVIDENCE-1"
MIGRATION_ID = "fc_bzg_receive_evidence1_20261005"
ENTITY = _hist.ENTITY
SCHEMA = "bzg.receive.evidence.review.v1"
TZ8 = timezone(timedelta(hours=8))

REVIEWERS = frozenset({"PERS-MATT", "PERS-ZAYEN"})
TARGET_RECORD_TYPES = frozenset({"purchase_order", "goods_receipt", "supplier_bill"})
RECORD_PRIORITY = {
    "supplier_bill": 0,
    "goods_receipt": 1,
    "purchase_order": 2,
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
}


class ReceiveEvidenceError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def public(**extra: Any) -> dict[str, Any]:
    out = {**HONESTY}
    out.update(extra)
    out["staff_ready"] = False
    out["zayen_ready"] = False
    return out


def require_reviewer(person_id: str | None, conn: sqlite3.Connection) -> None:
    pid = (person_id or "").strip()
    if not pid:
        raise ReceiveEvidenceError("Sign in required.", code="unauthenticated", http_status=401)
    if pid not in REVIEWERS:
        raise ReceiveEvidenceError(
            "Photo review is for finance reviewers only.",
            code="forbidden",
            http_status=403,
        )
    _desk.require_board(pid, conn)


def ensure_receive_review_schema(conn: sqlite3.Connection) -> list[str]:
    _evlink.ensure_evidence_link_schema(conn)
    added: list[str] = []
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bzg_ops_evidence_recon_queue)").fetchall()}
    migrations = [
        ("status", "TEXT NOT NULL DEFAULT 'ambiguous'"),
        ("file_kind", "TEXT"),
        ("proposed_record_type", "TEXT"),
        ("proposed_record_id", "TEXT"),
        ("proposal_rule", "TEXT"),
        ("proposal_confidence", "TEXT"),
        ("reviewer_person_id", "TEXT"),
        ("reviewed_at", "TEXT"),
        ("reject_reason", "TEXT"),
        ("proposed_at", "TEXT"),
    ]
    for col, ddl in migrations:
        if col not in cols:
            conn.execute(f"ALTER TABLE bzg_ops_evidence_recon_queue ADD COLUMN {col} {ddl}")
            added.append(f"bzg_ops_evidence_recon_queue.{col}")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bzg_evidence_recon_status
          ON bzg_ops_evidence_recon_queue(status)
        """
    )
    return added


def _parse_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    text = str(value).strip()
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _file_date(file_path: str, file_mtime: str | None) -> datetime.date | None:
    from_path = _parse_date(file_path)
    if from_path:
        return from_path
    return _parse_date(file_mtime)


def _norm_token(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _supplier_in_path(supplier_name: str | None, file_path: str) -> bool:
    name = (supplier_name or "").strip()
    if len(name) < 4:
        return False
    tok = _norm_token(name)
    if len(tok) < 4:
        return False
    return tok in _norm_token(file_path)


def _token_in_filename(token: str, filename: str) -> bool:
    if not token or not filename:
        return False
    pat = re.compile(r"(?:^|_)" + re.escape(token) + r"(?:[._-]|$)")
    return bool(pat.search(filename))


def _load_indexes(conn: sqlite3.Connection) -> dict[str, Any]:
    prov_rows = conn.execute(
        """
        SELECT record_type, beta_id, source_id, source_pr_num, linked_po_id
        FROM bzg_ops_history_provenance
        WHERE record_type IN ('purchase_order','goods_receipt','supplier_bill')
        """
    ).fetchall()
    prov_by_beta = {(str(r["record_type"]), str(r["beta_id"])): dict(r) for r in prov_rows}
    pr_doc_index: dict[str, str] = {}
    for row in prov_rows:
        if row["record_type"] == "purchase_order" and row["source_pr_num"]:
            pr_doc_index[str(row["source_pr_num"])] = str(row["beta_id"])

    bills = [dict(r) for r in conn.execute(
        "SELECT bill_id, nota_date, nota_number, supplier_name, po_id, gr_id, stated_total FROM bzg_ops_supplier_bills"
    ).fetchall()]
    bill_doc_index = {str(b["nota_number"]): str(b["bill_id"]) for b in bills if b.get("nota_number")}

    pos = [dict(r) for r in conn.execute(
        "SELECT po_id, created_at, supplier_name FROM bzg_ops_purchase_orders"
    ).fetchall()]
    grs = [dict(r) for r in conn.execute(
        "SELECT gr_id, po_id, supplier_name, created_at FROM bzg_ops_goods_receipts"
    ).fetchall()]
    return {
        "prov_by_beta": prov_by_beta,
        "pr_doc_index": pr_doc_index,
        "bill_doc_index": bill_doc_index,
        "bills": bills,
        "pos": pos,
        "grs": grs,
    }


def _collect_receive_candidates(
    file_path: str,
    file_mtime: str | None,
    indexes: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Return unique (record_type, record_id) -> {match_rule, confidence, provenance}."""
    fname = Path(file_path).name
    fd = _file_date(file_path, file_mtime)
    out: dict[tuple[str, str], dict[str, Any]] = {}

    def add(record_type: str, record_id: str, match_rule: str, confidence: str, provenance: dict[str, Any]) -> None:
        key = (record_type, record_id)
        prev = out.get(key)
        if not prev or confidence == "HIGH":
            out[key] = {
                "record_type": record_type,
                "record_id": record_id,
                "match_rule": match_rule,
                "confidence": confidence,
                "provenance": provenance,
            }

    for token in re.findall(r"PR-\d+", fname):
        po_id = indexes["pr_doc_index"].get(token)
        if po_id and _token_in_filename(token, fname):
            add("purchase_order", po_id, "pr_in_filename", "HIGH", {"document_number": token})

    for token in re.findall(r"PO-\d+", fname):
        po_id = indexes["pr_doc_index"].get(token)
        if po_id and _token_in_filename(token, fname):
            add("purchase_order", po_id, "po_in_filename", "HIGH", {"document_number": token})

    for token in re.findall(r"L-\d+", fname):
        bill_id = indexes["bill_doc_index"].get(token)
        if bill_id and _token_in_filename(token, fname):
            add("supplier_bill", bill_id, "nota_in_filename", "HIGH", {"document_number": token})

    if fd:
        for bill in indexes["bills"]:
            bd = _parse_date(bill.get("nota_date"))
            if not bd or abs((fd - bd).days) > 1:
                continue
            supplier = bill.get("supplier_name")
            if _supplier_in_path(supplier, file_path):
                add(
                    "supplier_bill",
                    str(bill["bill_id"]),
                    "date_and_supplier_in_path",
                    "HIGH",
                    {"nota_date": str(bd), "supplier_name": supplier},
                )
            else:
                add(
                    "supplier_bill",
                    str(bill["bill_id"]),
                    "date_near_nota",
                    "MEDIUM",
                    {"nota_date": str(bd)},
                )
            gr_id = bill.get("gr_id")
            if gr_id:
                add(
                    "goods_receipt",
                    str(gr_id),
                    "date_near_nota_receipt",
                    "MEDIUM",
                    {"nota_date": str(bd), "via_bill_id": str(bill["bill_id"])},
                )

        for po in indexes["pos"]:
            pd = _parse_date(po.get("created_at"))
            if not pd or abs((fd - pd).days) > 1:
                continue
            supplier = po.get("supplier_name")
            if _supplier_in_path(supplier, file_path):
                add(
                    "purchase_order",
                    str(po["po_id"]),
                    "date_and_supplier_in_path",
                    "HIGH",
                    {"order_date": str(pd), "supplier_name": supplier},
                )
            else:
                add(
                    "purchase_order",
                    str(po["po_id"]),
                    "date_near_po",
                    "MEDIUM",
                    {"order_date": str(pd)},
                )

    filtered = {k: v for k, v in out.items() if k[0] in TARGET_RECORD_TYPES}
    return filtered


def _recon_id_for_path(file_path: str) -> str:
    return f"EVR-RECV-{hashlib.sha1(file_path.encode()).hexdigest()[:12].upper()}"


def propose_receive_evidence(conn: sqlite3.Connection, *, commit: bool = True) -> dict[str, Any]:
    ensure_receive_review_schema(conn)
    ts = now_iso()
    indexes = _load_indexes(conn)

    rows = conn.execute(
        """
        SELECT queue_id, file_path, file_kind, file_mtime, migration_status
        FROM bzg_ops_evidence_unlinked
        WHERE file_kind='receive' AND migration_status='EVIDENCE UNLINKED'
        ORDER BY file_path
        """
    ).fetchall()

    proposed = 0
    skipped_linked = 0
    skipped_ambiguous = 0
    skipped_existing = 0

    for row in rows:
        file_path = str(row["file_path"])
        queue_id = str(row["queue_id"])

        linked = conn.execute(
            "SELECT 1 FROM bzg_ops_evidence_links WHERE file_path=?",
            (file_path,),
        ).fetchone()
        if linked:
            skipped_linked += 1
            continue

        existing = conn.execute(
            """
            SELECT status FROM bzg_ops_evidence_recon_queue
            WHERE file_path=? AND status IN ('proposed','accepted','rejected')
            ORDER BY imported_at DESC LIMIT 1
            """,
            (file_path,),
        ).fetchone()
        if existing:
            skipped_existing += 1
            continue

        candidates = _collect_receive_candidates(file_path, row["file_mtime"], indexes)
        if len(candidates) != 1:
            if len(candidates) > 1:
                skipped_ambiguous += 1
            continue

        cand = next(iter(candidates.values()))
        recon_id = _recon_id_for_path(file_path)
        conn.execute(
            """
            INSERT INTO bzg_ops_evidence_recon_queue (
              recon_id, queue_id, file_path, file_kind, record_type,
              match_rule, candidates_json, imported_at, status,
              proposed_record_type, proposed_record_id, proposal_rule,
              proposal_confidence, proposed_at
            ) VALUES (?, ?, ?, 'receive', ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?)
            ON CONFLICT(recon_id) DO NOTHING
            """,
            (
                recon_id,
                queue_id,
                file_path,
                cand["record_type"],
                cand["match_rule"],
                json.dumps([cand], sort_keys=True),
                ts,
                cand["record_type"],
                cand["record_id"],
                cand["match_rule"],
                cand["confidence"],
                ts,
            ),
        )
        if conn.total_changes:
            proposed += 1

    if commit:
        conn.commit()

    counts = queue_counts(conn)
    return public(
        ok=True,
        schema=SCHEMA,
        applied_at=ts,
        receive_scanned=len(rows),
        newly_proposed=proposed,
        skipped_linked=skipped_linked,
        skipped_ambiguous=skipped_ambiguous,
        skipped_existing=skipped_existing,
        queue_counts=counts,
    )


def queue_counts(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bzg_ops_evidence_recon_queue'"
        ).fetchall()
    }
    if "bzg_ops_evidence_recon_queue" not in tables:
        return {"proposed": 0, "accepted": 0, "rejected": 0, "ambiguous": 0}
    out: dict[str, int] = {}
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bzg_ops_evidence_recon_queue)").fetchall()}
    if "status" not in cols:
        return {"proposed": 0, "accepted": 0, "rejected": 0, "ambiguous": int(
            conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue").fetchone()[0]
        )}
    for row in conn.execute(
        """
        SELECT status, COUNT(*) AS n FROM bzg_ops_evidence_recon_queue
        WHERE file_kind='receive' OR file_kind IS NULL
        GROUP BY status
        """
    ):
        out[str(row["status"])] = int(row["n"])
    return {
        "proposed": out.get("proposed", 0),
        "accepted": out.get("accepted", 0),
        "rejected": out.get("rejected", 0),
        "ambiguous": out.get("ambiguous", 0),
    }


def _record_summary(conn: sqlite3.Connection, record_type: str, record_id: str) -> dict[str, Any]:
    rt = (record_type or "").strip()
    rid = (record_id or "").strip()
    if rt == "supplier_bill":
        row = conn.execute(
            "SELECT bill_id, nota_number, nota_date, supplier_name, stated_total, po_id, gr_id FROM bzg_ops_supplier_bills WHERE bill_id=?",
            (rid,),
        ).fetchone()
        if not row:
            return {"found": False}
        return {
            "found": True,
            "kind": "Nota",
            "label": str(row["nota_number"] or "Nota"),
            "supplier_name": row["supplier_name"],
            "date": row["nota_date"],
            "amount": float(row["stated_total"] or 0),
            "href": f"/bzg/finance/notas/{row['bill_id']}",
        }
    if rt == "goods_receipt":
        row = conn.execute(
            "SELECT gr_id, supplier_name, po_id, created_at FROM bzg_ops_goods_receipts WHERE gr_id=?",
            (rid,),
        ).fetchone()
        if not row:
            return {"found": False}
        return {
            "found": True,
            "kind": "Receipt",
            "label": "Goods receipt",
            "supplier_name": row["supplier_name"],
            "date": str(row["created_at"] or "")[:10],
            "href": f"/bzg/finance/receipts/{row['gr_id']}",
        }
    if rt == "purchase_order":
        row = conn.execute(
            "SELECT po_id, supplier_name, created_at FROM bzg_ops_purchase_orders WHERE po_id=?",
            (rid,),
        ).fetchone()
        prov = conn.execute(
            "SELECT source_pr_num FROM bzg_ops_history_provenance WHERE record_type='purchase_order' AND beta_id=?",
            (rid,),
        ).fetchone()
        if not row:
            return {"found": False}
        return {
            "found": True,
            "kind": "Purchase order",
            "label": str(prov["source_pr_num"] if prov else "Purchase order"),
            "supplier_name": row["supplier_name"],
            "date": str(row["created_at"] or "")[:10],
            "href": f"/bzg/finance/po/{row['po_id']}",
        }
    return {"found": False}


def list_review_queue(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT recon_id, queue_id, file_path, proposed_record_type, proposed_record_id,
               proposal_rule, proposal_confidence, proposed_at, status
        FROM bzg_ops_evidence_recon_queue
        WHERE status='proposed' AND file_kind='receive'
        ORDER BY proposed_at, recon_id
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    total = conn.execute(
        """
        SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue
        WHERE status='proposed' AND file_kind='receive'
        """
    ).fetchone()[0]
    items = []
    for row in rows:
        summary = _record_summary(conn, row["proposed_record_type"], row["proposed_record_id"])
        items.append(
            {
                "recon_id": row["recon_id"],
                "photo_href": f"/api/bzg/finance/evidence-review/{row['recon_id']}/photo",
                "proposal_rule_label": _human_rule(row["proposal_rule"]),
                "confidence": row["proposal_confidence"],
                "proposed_at": row["proposed_at"],
                "proposed_record": summary,
            }
        )
    return public(ok=True, items=items, total=int(total), limit=limit, offset=offset)


def review_detail(conn: sqlite3.Connection, recon_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM bzg_ops_evidence_recon_queue
        WHERE recon_id=? AND file_kind='receive'
        """,
        ((recon_id or "").strip(),),
    ).fetchone()
    if not row:
        return public(ok=False, error="not_found")
    summary = _record_summary(conn, row["proposed_record_type"], row["proposed_record_id"])
    return public(
        ok=True,
        recon_id=row["recon_id"],
        status=row["status"],
        photo_href=f"/api/bzg/finance/evidence-review/{row['recon_id']}/photo",
        proposal_rule_label=_human_rule(row["proposal_rule"]),
        proposed_record=summary,
    )


def _human_rule(rule: str | None) -> str:
    labels = {
        "pr_in_filename": "PR number in photo name",
        "po_in_filename": "PO number in photo name",
        "nota_in_filename": "Nota number in photo name",
        "date_and_supplier_in_path": "Date and supplier in folder name",
        "date_near_nota": "Photo date near nota date",
        "date_near_nota_receipt": "Photo date near receipt nota date",
        "date_near_po": "Photo date near purchase order date",
        "date_and_supplier_in_path_po": "Date and supplier in folder name",
    }
    return labels.get(str(rule or ""), "Suggested match")


def _resolve_photo_path(conn: sqlite3.Connection, file_path: str) -> Path | None:
    path = Path(file_path)
    if path.is_file():
        return path
    name = path.name
    for directory in (_hist.RECEIVE_DIR, _hist.NOTAS_DIR, _hist.NIGHTLY_DIR):
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


def photo_bytes(conn: sqlite3.Connection, recon_id: str) -> tuple[bytes, str]:
    row = conn.execute(
        "SELECT file_path, status FROM bzg_ops_evidence_recon_queue WHERE recon_id=?",
        ((recon_id or "").strip(),),
    ).fetchone()
    if not row:
        raise ReceiveEvidenceError("Photo not found.", code="not_found", http_status=404)
    resolved = _resolve_photo_path(conn, str(row["file_path"]))
    if not resolved:
        raise ReceiveEvidenceError("Photo file is not available.", code="not_found", http_status=404)
    data = resolved.read_bytes()
    mime = "image/jpeg" if resolved.suffix.lower() in {".jpg", ".jpeg"} else "application/octet-stream"
    return data, mime


def photo_bytes_for_record(conn: sqlite3.Connection, record_type: str, record_id: str) -> tuple[bytes, str]:
    link = _evlink.evidence_for_record(conn, record_type, record_id)
    if not link or not link.get("file_path"):
        raise ReceiveEvidenceError("No linked photo.", code="not_found", http_status=404)
    resolved = _resolve_photo_path(conn, str(link["file_path"]))
    if not resolved:
        raise ReceiveEvidenceError("Photo file is not available.", code="not_found", http_status=404)
    data = resolved.read_bytes()
    mime = "image/jpeg" if resolved.suffix.lower() in {".jpg", ".jpeg"} else "application/octet-stream"
    return data, mime


def accept_proposal(
    conn: sqlite3.Connection,
    recon_id: str,
    person_id: str,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    require_reviewer(person_id, conn)
    ensure_receive_review_schema(conn)
    row = conn.execute(
        """
        SELECT * FROM bzg_ops_evidence_recon_queue
        WHERE recon_id=? AND status='proposed' AND file_kind='receive'
        """,
        ((recon_id or "").strip(),),
    ).fetchone()
    if not row:
        raise ReceiveEvidenceError("Review item not found or already decided.", code="not_found", http_status=404)

    file_path = str(row["file_path"])
    queue_id = str(row["queue_id"] or "")
    record_type = str(row["proposed_record_type"] or "")
    record_id = str(row["proposed_record_id"] or "")
    match_rule = str(row["proposal_rule"] or "human_accepted_proposal")
    confidence = str(row["proposal_confidence"] or "MEDIUM")

    if not queue_id:
        queue_id = f"EVD-RECV-{hashlib.sha1(file_path.encode()).hexdigest()[:12].upper()}"

    ts = now_iso()
    link_id = f"EVL-{uuid.uuid4().hex[:12].upper()}"
    provenance = {
        "source": "human_review_accept",
        "reviewer_person_id": person_id,
        "recon_id": recon_id,
        "proposal_rule": match_rule,
    }

    conn.execute(
        """
        INSERT INTO bzg_ops_evidence_links (
          link_id, queue_id, file_path, file_kind, record_type, record_id,
          match_rule, confidence, provenance_json, linked_at
        ) VALUES (?, ?, ?, 'receive', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path, record_type, record_id) DO NOTHING
        """,
        (
            link_id,
            queue_id,
            file_path,
            record_type,
            record_id,
            match_rule,
            confidence,
            json.dumps(provenance, sort_keys=True),
            ts,
        ),
    )
    if not conn.total_changes:
        existing = conn.execute(
            "SELECT link_id FROM bzg_ops_evidence_links WHERE file_path=? AND record_type=? AND record_id=?",
            (file_path, record_type, record_id),
        ).fetchone()
        if not existing:
            raise ReceiveEvidenceError("Could not create link.", code="conflict", http_status=409)
        link_id = str(existing["link_id"])

    link_row = {
        "file_path": file_path,
        "record_type": record_type,
        "record_id": record_id,
    }
    _evlink._apply_record_updates(conn, link_row)

    conn.execute(
        """
        UPDATE bzg_ops_evidence_unlinked
        SET migration_status='EVIDENCE LINKED',
            linked_record_type=?,
            linked_record_id=?,
            match_rule=?
        WHERE queue_id=? OR file_path=?
        """,
        (record_type, record_id, match_rule, queue_id, file_path),
    )
    conn.execute(
        """
        UPDATE bzg_ops_evidence_recon_queue
        SET status='accepted', reviewer_person_id=?, reviewed_at=?, record_type=?
        WHERE recon_id=?
        """,
        (person_id, ts, record_type, recon_id),
    )

    _audit.safe_record(
        action="bzg.evidence.review.accept",
        result="SUCCEEDED",
        source="bzg_receive_evidence1",
        actor_type="PERSON",
        actor_person_id=person_id,
        verified_person_id=person_id,
        resource_type="bzg_ops_evidence_recon_queue",
        resource_id=recon_id,
        metadata={
            "record_type": record_type,
            "record_id": record_id,
            "link_id": link_id,
            "file_kind": "receive",
        },
        conn=conn,
        commit=False,
    )

    if commit:
        conn.commit()

    return public(
        ok=True,
        recon_id=recon_id,
        link_id=link_id,
        record_type=record_type,
        record_id=record_id,
        reviewed_at=ts,
    )


def reject_proposal(
    conn: sqlite3.Connection,
    recon_id: str,
    person_id: str,
    reason: str,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    require_reviewer(person_id, conn)
    ensure_receive_review_schema(conn)
    text = (reason or "").strip()
    if not text:
        raise ReceiveEvidenceError("A reason is required to reject.", code="invalid", http_status=400)

    row = conn.execute(
        """
        SELECT recon_id, file_path FROM bzg_ops_evidence_recon_queue
        WHERE recon_id=? AND status='proposed' AND file_kind='receive'
        """,
        ((recon_id or "").strip(),),
    ).fetchone()
    if not row:
        raise ReceiveEvidenceError("Review item not found or already decided.", code="not_found", http_status=404)

    ts = now_iso()
    conn.execute(
        """
        UPDATE bzg_ops_evidence_recon_queue
        SET status='rejected', reviewer_person_id=?, reviewed_at=?, reject_reason=?
        WHERE recon_id=?
        """,
        (person_id, ts, text, recon_id),
    )

    _audit.safe_record(
        action="bzg.evidence.review.reject",
        result="SUCCEEDED",
        source="bzg_receive_evidence1",
        actor_type="PERSON",
        actor_person_id=person_id,
        verified_person_id=person_id,
        resource_type="bzg_ops_evidence_recon_queue",
        resource_id=recon_id,
        metadata={"reason": text[:200], "file_kind": "receive"},
        conn=conn,
        commit=False,
    )

    if commit:
        conn.commit()

    return public(ok=True, recon_id=recon_id, status="rejected", reviewed_at=ts)


def precision_sample(conn: sqlite3.Connection, n: int = 20) -> dict[str, Any]:
    """Manual-review sample: basename only, no paths in output."""
    rows = conn.execute(
        """
        SELECT recon_id, file_path, proposed_record_type, proposed_record_id, proposal_rule
        FROM bzg_ops_evidence_recon_queue
        WHERE status='proposed' AND file_kind='receive'
        ORDER BY proposed_at, recon_id
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    samples = []
    for row in rows:
        summary = _record_summary(conn, row["proposed_record_type"], row["proposed_record_id"])
        samples.append(
            {
                "basename": Path(str(row["file_path"])).name,
                "proposal_rule": row["proposal_rule"],
                "proposed_kind": summary.get("kind"),
                "proposed_label": summary.get("label"),
                "supplier_name": summary.get("supplier_name"),
                "date": summary.get("date"),
                "precision_verified": None,
            }
        )
    return {
        "sample_size": len(samples),
        "samples": samples,
        "note": (
            "Receive photo names are recv_{chat}_{hash}.jpg with no PR, nota, or supplier tokens. "
            "Most proposals rely on photo date alone and are ambiguous; only unique date matches are queued."
            if not samples
            else "Manual precision review required — verify each proposed match against the photo."
        ),
    }
