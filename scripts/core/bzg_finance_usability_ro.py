#!/usr/bin/env python3
"""BZG-FINANCE-USABILITY-1 — read-only browse for imported BZG finance history."""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from core import bzg_bank_recon1 as _bank_recon
from core import bzg_evidence_link1 as _evlink
from core import bzg_history_import1 as _hist
from core import bzg_three_way_match as _match

PACK = "BZG-FINANCE-USABILITY-1"
ENTITY = _hist.ENTITY
SCHEMA = "bzg.finance.usability.v1"

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

OUTLET_LABELS = {
    "BZG-UMA": "Uma Blu",
    "BZG-RAIN": "Rainforest",
    "BZG-RAIN-POOL": "Pool Bar",
}

REBUILT_RECEIPT_LABEL = "Rebuilt from the bill — no receiving record"

MATCH_RESULT_LABELS = {
    "HISTORICAL_UNPAID": "Historical unpaid",
    "MATCHED": "Matched",
    "MATCH": "Matched",
    "DIFFERENCE": "Difference",
    "NEEDS_RECONCILIATION": "Needs reconciliation",
}

PREVIOUS_SYSTEM_MATCH_LABEL = _match.PREVIOUS_SYSTEM_MATCH_LABEL

RECON_STATUS_LABELS = {
    "UNMATCHED": "Unmatched",
    "MATCHED": "Matched",
    "NEEDS_RECEIPT": "Needs receipt",
    "NEEDS_REVIEW": "Needs review",
    "UNIDENTIFIED": "Unidentified",
    "NEEDS_RECONCILIATION": "Needs reconciliation",
}

COMPLETENESS_STATUS_LABELS = {
    "COMPLETE": "Complete",
    "GAP": "Gap",
}


def _human_match_result(code: str | None) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        return "Unknown"
    return MATCH_RESULT_LABELS.get(raw, raw.replace("_", " ").title())


def _ap_match_label(match_id: str | None, match_result: str | None = None) -> str | None:
    hist = _match.historical_match_label(match_id)
    if hist:
        return hist
    return None


def _ap_status_label(match_id: str | None, match_result: str | None) -> str:
    hist = _ap_match_label(match_id, match_result)
    if hist:
        payment = _human_match_result(match_result)
        if payment and payment != "Unknown":
            return f"{payment} · {hist}"
        return hist
    return _human_match_result(match_result)


def _human_recon_status(code: str | None) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        return "Unknown"
    return RECON_STATUS_LABELS.get(raw, raw.replace("_", " ").title())


def _human_completeness_status(code: str | None) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        return "Unknown"
    return COMPLETENESS_STATUS_LABELS.get(raw, raw.replace("_", " ").title())


def _is_rebuilt_receipt(gr_id: str, notes: str | None = None, prov: dict[str, Any] | None = None) -> bool:
    gid = (gr_id or "").strip()
    if gid.startswith("GR-HIST-LEDGER"):
        return True
    note = (notes or "").lower()
    if "synthetic gr" in note or "without receipt" in note:
        return True
    if prov and str(prov.get("record_type") or "") == "goods_receipt_synthetic":
        return True
    return False


def _computed_bill_total(bill: dict[str, Any], lines: list[dict[str, Any]]) -> float | None:
    if lines:
        total = 0.0
        for line in lines:
            amt = line.get("line_amount")
            if amt is None:
                qty = float(line.get("billed_qty") or 0)
                price = float(line.get("billed_unit_price") or 0)
                amt = qty * price
            total += float(amt or 0)
        return total
    stated = bill.get("stated_total")
    if stated is not None:
        return float(stated)
    return None


def _bank_txns_for_refs(refs: list[str], conn: sqlite3.Connection, *, limit: int = 20) -> list[dict[str, Any]]:
    cleaned = [r.strip() for r in refs if (r or "").strip()]
    if not cleaned:
        return []
    placeholders = ",".join("?" * len(cleaned))
    rows = conn.execute(
        f"""
        SELECT txn_id, txn_date, description, debit, credit, recon_status, bank_account
        FROM bzg_bank_transactions
        WHERE entity_id=? AND matched_ledger_source_id IN ({placeholders})
        ORDER BY txn_date DESC, txn_id DESC
        LIMIT ?
        """,
        (ENTITY, *cleaned, max(1, min(limit, 100))),
    ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d["href"] = "/bzg/finance/bank"
        d["status_label"] = _human_recon_status(str(d.get("recon_status") or "UNMATCHED"))
        out.append(d)
    return out


def public(**extra: Any) -> dict[str, Any]:
    out = {**HONESTY}
    out.update(extra)
    out["staff_ready"] = False
    out["zayen_ready"] = False
    return out


def _norm_q(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip())


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().upper())


def resolve_vendor_id(supplier_id: str, conn: sqlite3.Connection) -> str | None:
    sid = (supplier_id or "").strip()
    if not sid:
        return None
    row = conn.execute(
        "SELECT vendor_id FROM bzg_shared_vendors WHERE vendor_id=?",
        (sid,),
    ).fetchone()
    if row:
        return str(row[0])
    alt = f"SUP-ALC-{sid}"
    row = conn.execute(
        "SELECT vendor_id FROM bzg_shared_vendors WHERE vendor_id=?",
        (alt,),
    ).fetchone()
    if row:
        return str(row[0])
    return None


def _vendor_row(vendor_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    vid = (vendor_id or "").strip()
    if not vid:
        return None
    row = conn.execute(
        "SELECT * FROM bzg_shared_vendors WHERE vendor_id=?",
        (vid,),
    ).fetchone()
    if row:
        return dict(row)
    resolved = resolve_vendor_id(vid, conn)
    if resolved and resolved != vid:
        row = conn.execute(
            "SELECT * FROM bzg_shared_vendors WHERE vendor_id=?",
            (resolved,),
        ).fetchone()
        return dict(row) if row else None
    return None


def _provenance(beta_id: str, record_type: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM bzg_ops_history_provenance
        WHERE beta_id=? AND record_type=?
        """,
        (beta_id, record_type),
    ).fetchone()
    return dict(row) if row else None


def _evidence_photo_href(record_type: str | None, record_id: str | None) -> str | None:
    rt = (record_type or "").strip()
    rid = (record_id or "").strip()
    if rt and rid:
        return f"/api/bzg/finance/evidence-photo/{rt}/{rid}"
    return None


def _evidence_status(
    photo_object_ref: str | None,
    evidence_ref: str | None = None,
    *,
    link: dict[str, Any] | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    ref = (photo_object_ref or "").strip()
    ev = (evidence_ref or "").strip()
    if link and link.get("linked"):
        rt = record_type or link.get("record_type")
        rid = record_id or link.get("record_id")
        return {
            "linked": True,
            "status": "linked",
            "photo_object_ref": link.get("photo_object_ref") or ref or None,
            "evidence_ref": link.get("file_path") or ev or None,
            "photo_href": _evidence_photo_href(rt, rid),
            "match_rule": link.get("match_rule"),
            "confidence": link.get("confidence"),
            "message": "Evidence linked",
        }
    if ref and ref.upper() != "UNKNOWN":
        resolved = _evlink.resolve_possessed_path(ref)
        return {
            "linked": True,
            "status": "linked",
            "photo_object_ref": ref,
            "evidence_ref": str(resolved) if resolved else ev or None,
            "message": "Evidence linked",
        }
    if ev and not ev.startswith("http"):
        return {
            "linked": True,
            "status": "linked",
            "evidence_ref": ev,
            "message": "Evidence linked",
        }
    return {
        "linked": False,
        "status": "missing",
        "photo_object_ref": ref or None,
        "message": "no evidence linked",
    }


def desk_counts(conn: sqlite3.Connection) -> dict[str, Any]:
    beta = _hist.beta_counts(conn)
    needs_recon = conn.execute(
        "SELECT COUNT(*) FROM bzg_ops_history_provenance WHERE migration_status='NEEDS RECONCILIATION'"
    ).fetchone()[0]
    unmatched_bank = conn.execute(
        "SELECT COUNT(*) FROM bzg_bank_transactions WHERE recon_status='UNMATCHED'"
    ).fetchone()[0]
    recon_counts = _bank_recon.state_counts(conn)
    ev_counts = _evlink.link_counts(conn)
    unlinked_ev = conn.execute(
        "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE migration_status='EVIDENCE UNLINKED'"
    ).fetchone()[0]
    return public(
        ok=True,
        schema=SCHEMA,
        counts={
            "purchase_orders": beta.get("bzg_ops_purchase_orders", 0),
            "po_lines": beta.get("bzg_ops_po_lines", 0),
            "goods_receipts": beta.get("bzg_ops_goods_receipts", 0),
            "gr_lines": beta.get("bzg_ops_gr_lines", 0),
            "supplier_bills": beta.get("bzg_ops_supplier_bills", 0),
            "ap_ready": beta.get("bzg_ops_ap_ready", 0),
            "suppliers": beta.get("bzg_shared_vendors", 0),
            "petty_historical": beta.get("bzg_ops_petty_movements_historical", 0),
            "bank_imports": beta.get("bzg_bank_statement_imports", 0),
            "bank_transactions": beta.get("bzg_bank_transactions", 0),
            "evidence_unlinked": int(unlinked_ev),
            "evidence_linked": ev_counts.get("linked", 0),
            "evidence_recon_queue": ev_counts.get("needs_reconciliation", 0),
            "needs_reconciliation": int(needs_recon),
            "bank_unmatched": int(unmatched_bank),
            "bank_recon": recon_counts,
        },
        beta_counts=beta,
        evidence_link=ev_counts,
    )


def search_suppliers(
    query: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
    outlet_id: str | None = None,
) -> dict[str, Any]:
    q = _norm_q(query)
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))
    params: list[Any] = []
    clauses = ["legal_entity_id=?"]
    params.append(ENTITY)
    if outlet_id:
        clauses.append("(outlet_id=? OR outlet_id IS NULL)")
        params.append(outlet_id.strip())
    if q:
        like = f"%{q.upper()}%"
        clauses.append("(name_norm LIKE ? OR display_name LIKE ? OR vendor_id LIKE ?)")
        params.extend([like, f"%{q}%", f"%{q}%"])
    where = " AND ".join(clauses)
    total = conn.execute(
        f"SELECT COUNT(*) FROM bzg_shared_vendors WHERE {where}",
        params,
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT vendor_id, display_name, outlet_id, status, name_norm
        FROM bzg_shared_vendors
        WHERE {where}
        ORDER BY display_name
        LIMIT ? OFFSET ?
        """,
        (*params, lim, off),
    ).fetchall()
    suppliers = []
    for row in rows:
        vid = str(row["vendor_id"])
        po_n = conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_purchase_orders WHERE supplier_id=? OR supplier_id=?",
            (vid, vid.replace("SUP-ALC-", "")),
        ).fetchone()[0]
        bill_n = conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_supplier_bills WHERE supplier_id=? OR supplier_id=?",
            (vid, vid.replace("SUP-ALC-", "")),
        ).fetchone()[0]
        suppliers.append(
            {
                "vendor_id": vid,
                "display_name": row["display_name"],
                "outlet_id": row["outlet_id"],
                "outlet_label": OUTLET_LABELS.get(row["outlet_id"] or "", row["outlet_id"]),
                "status": row["status"],
                "po_count": int(po_n),
                "nota_count": int(bill_n),
                "href": f"/bzg/finance/suppliers/{vid}",
            }
        )
    return public(
        ok=True,
        query=q,
        suppliers=suppliers,
        count=len(suppliers),
        total=int(total),
        limit=lim,
        offset=off,
        has_more=(off + len(suppliers)) < int(total),
    )


def supplier_detail(
    vendor_id: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    outlet_id: str | None = None,
) -> dict[str, Any]:
    vendor = _vendor_row(vendor_id, conn)
    if not vendor:
        return public(ok=False, error="not_found", vendor_id=vendor_id)
    vid = str(vendor["vendor_id"])
    short_id = vid.replace("SUP-ALC-", "")
    prov = _provenance(vid, "supplier", conn)
    outlet_clause = ""
    outlet_params: list[Any] = []
    if outlet_id:
        outlet_clause = " AND outlet_id=?"
        outlet_params = [outlet_id.strip()]
    pos = conn.execute(
        f"""
        SELECT po_id, pr_id, outlet_id, state, created_at, supplier_name
        FROM bzg_ops_purchase_orders
        WHERE supplier_id IN (?, ?){outlet_clause}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (vid, short_id, *outlet_params, max(1, min(limit, 500))),
    ).fetchall()
    purchase_orders = []
    for row in pos:
        po_id = str(row["po_id"])
        p = _provenance(po_id, "purchase_order", conn)
        purchase_orders.append(
            {
                **dict(row),
                "outlet_label": OUTLET_LABELS.get(row["outlet_id"] or "", row["outlet_id"]),
                "source_pr_num": (p or {}).get("source_pr_num"),
                "migration_status": (p or {}).get("migration_status"),
                "href": f"/bzg/finance/po/{po_id}",
            }
        )
    bills = conn.execute(
        f"""
        SELECT bill_id, po_id, nota_number, nota_date, stated_total, photo_object_ref
        FROM bzg_ops_supplier_bills
        WHERE supplier_id IN (?, ?){outlet_clause}
        ORDER BY nota_date DESC, bill_id
        LIMIT ?
        """,
        (vid, short_id, *outlet_params, max(1, min(limit, 500))),
    ).fetchall()
    notas = []
    bill_refs: list[str] = []
    for row in bills:
        bill_id = str(row["bill_id"])
        bill_refs.append(bill_id)
        ev = _evidence_status(row["photo_object_ref"])
        notas.append(
            {
                **dict(row),
                "evidence": ev,
                "href": f"/bzg/finance/notas/{bill_id}",
            }
        )
    ap_rows_raw = conn.execute(
        f"""
        SELECT ap_ready_id, bill_id, nota_number, nota_date, stated_total, match_result,
               match_id, outlet_id
        FROM bzg_ops_ap_ready
        WHERE supplier_id IN (?, ?){outlet_clause}
        ORDER BY nota_date DESC, ap_ready_id
        LIMIT ?
        """,
        (vid, short_id, *outlet_params, max(1, min(limit, 500))),
    ).fetchall()
    ap_rows = []
    for row in ap_rows_raw:
        bill_id = str(row["bill_id"])
        bill_refs.append(bill_id)
        match_id = str(row["match_id"] or "")
        ap_rows.append(
            {
                "ap_ready_id": row["ap_ready_id"],
                "bill_id": bill_id,
                "nota_number": row["nota_number"],
                "nota_date": row["nota_date"],
                "stated_total": row["stated_total"],
                "match_result": row["match_result"],
                "outlet_id": row["outlet_id"],
                "outlet_label": OUTLET_LABELS.get(row["outlet_id"] or "", row["outlet_id"]),
                "status_label": _ap_status_label(match_id, str(row["match_result"] or "")),
                "match_label": _ap_match_label(match_id, str(row["match_result"] or "")),
                "nota_href": f"/bzg/finance/notas/{bill_id}",
            }
        )
    prov_refs = [
        str(r[0])
        for r in conn.execute(
            f"""
            SELECT linked_ledger_id FROM bzg_ops_history_provenance
            WHERE linked_ledger_id IS NOT NULL AND beta_id IN (
                SELECT bill_id FROM bzg_ops_supplier_bills WHERE supplier_id IN (?, ?){outlet_clause}
            )
            """,
            (vid, short_id, *outlet_params),
        ).fetchall()
        if r[0]
    ]
    bank_matches = _bank_txns_for_refs(bill_refs + prov_refs, conn, limit=30)
    return public(
        ok=True,
        vendor={
            **vendor,
            "outlet_label": OUTLET_LABELS.get(vendor.get("outlet_id") or "", vendor.get("outlet_id")),
        },
        reconciliation={
            "migration_status": (prov or {}).get("migration_status"),
            "source_id": (prov or {}).get("source_id"),
        },
        purchase_orders=purchase_orders,
        notas=notas,
        ap_rows=ap_rows,
        bank_matches=bank_matches,
        po_count=len(purchase_orders),
        nota_count=len(notas),
        ap_count=len(ap_rows),
        list_href="/bzg/finance/suppliers",
    )


def po_detail(po_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM bzg_ops_purchase_orders WHERE po_id=?",
        ((po_id or "").strip(),),
    ).fetchone()
    if not row:
        return public(ok=False, error="not_found", po_id=po_id)
    po = dict(row)
    lines = conn.execute(
        """
        SELECT line_id, pr_line_id, item, qty, unit
        FROM bzg_ops_po_lines WHERE po_id=? ORDER BY created_at, line_id
        """,
        (po["po_id"],),
    ).fetchall()
    prov = _provenance(po["po_id"], "purchase_order", conn)
    po_link = _evlink.evidence_for_record(conn, "purchase_order", po["po_id"])
    gr_rows = conn.execute(
        "SELECT gr_id, status, created_at, notes FROM bzg_ops_goods_receipts WHERE po_id=?",
        (po["po_id"],),
    ).fetchall()
    bills = conn.execute(
        "SELECT bill_id, nota_number, nota_date, stated_total, photo_object_ref FROM bzg_ops_supplier_bills WHERE po_id=?",
        (po["po_id"],),
    ).fetchall()
    notas = [
        {
            **dict(b),
            "evidence": _evidence_status(
                b["photo_object_ref"],
                link=_evlink.evidence_for_record(conn, "supplier_bill", str(b["bill_id"])),
                record_type="supplier_bill",
                record_id=str(b["bill_id"]),
            ),
            "href": f"/bzg/finance/notas/{b['bill_id']}",
        }
        for b in bills
    ]
    vendor = _vendor_row(str(po.get("supplier_id") or ""), conn)
    line_rows = [dict(l) for l in lines]
    line_total = sum(float(l.get("qty") or 0) for l in line_rows)
    receipts_out = []
    for g in gr_rows:
        gdict = dict(g)
        gprov = _provenance(str(g["gr_id"]), "goods_receipt", conn)
        if not gprov:
            gprov = _provenance(str(g["gr_id"]), "goods_receipt_synthetic", conn)
        rebuilt = _is_rebuilt_receipt(str(g["gr_id"]), gdict.get("notes"), gprov)
        receipts_out.append(
            {
                **gdict,
                "href": f"/bzg/finance/receipts/{g['gr_id']}",
                "rebuilt": rebuilt,
                "title": REBUILT_RECEIPT_LABEL if rebuilt else f"Receipt {gdict.get('nota_number') or ''}".strip() or "Goods receipt",
                "rebuild_label": REBUILT_RECEIPT_LABEL if rebuilt else None,
            }
        )
    vendor_href = f"/bzg/finance/suppliers/{vendor['vendor_id']}" if vendor else None
    return public(
        ok=True,
        po={
            **po,
            "outlet_label": OUTLET_LABELS.get(po.get("outlet_id") or "", po.get("outlet_id")),
            "lines": line_rows,
            "line_count": len(line_rows),
            "line_qty_total": line_total,
            "evidence": _evidence_status(
                None,
                (prov or {}).get("evidence_ref"),
                link=po_link,
                record_type="purchase_order",
                record_id=str(po["po_id"]),
            ),
        },
        vendor=vendor,
        vendor_href=vendor_href,
        reconciliation={
            "migration_status": (prov or {}).get("migration_status"),
            "source_pr_num": (prov or {}).get("source_pr_num"),
            "source_id": (prov or {}).get("source_id"),
            "alchemist_status": (prov or {}).get("alchemist_status"),
            "linked_ledger_id": (prov or {}).get("linked_ledger_id"),
            "needs_reconciliation": (prov or {}).get("migration_status") == "NEEDS RECONCILIATION",
        },
        receipts=receipts_out,
        notas=notas,
        po_href=f"/bzg/finance/po/{po['po_id']}",
    )


def receipt_detail(gr_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM bzg_ops_goods_receipts WHERE gr_id=?",
        ((gr_id or "").strip(),),
    ).fetchone()
    if not row:
        return public(ok=False, error="not_found", gr_id=gr_id)
    gr = dict(row)
    lines = conn.execute(
        """
        SELECT line_id, po_line_id, item, received_qty, shortfall_reason, unit
        FROM bzg_ops_gr_lines WHERE gr_id=? ORDER BY created_at, line_id
        """,
        (gr["gr_id"],),
    ).fetchall()
    prov = _provenance(gr["gr_id"], "goods_receipt", conn)
    if not prov:
        prov = _provenance(gr["gr_id"], "goods_receipt_synthetic", conn)
    gr_link = _evlink.evidence_for_record(conn, "goods_receipt", gr["gr_id"])
    if not gr_link and prov and prov.get("linked_po_id"):
        gr_link = _evlink.evidence_for_record(conn, "purchase_order", str(prov["linked_po_id"]))
    bill = conn.execute(
        "SELECT bill_id, nota_number, nota_date, stated_total, photo_object_ref FROM bzg_ops_supplier_bills WHERE gr_id=?",
        (gr["gr_id"],),
    ).fetchone()
    rebuilt = _is_rebuilt_receipt(str(gr["gr_id"]), gr.get("notes"), prov)
    return public(
        ok=True,
        receipt={
            **gr,
            "outlet_label": OUTLET_LABELS.get(gr.get("outlet_id") or "", gr.get("outlet_id")),
            "lines": [dict(l) for l in lines],
            "line_count": len(lines),
            "rebuilt": rebuilt,
            "rebuild_label": REBUILT_RECEIPT_LABEL if rebuilt else None,
            "title": REBUILT_RECEIPT_LABEL if rebuilt else "Goods receipt",
            "evidence": _evidence_status(
                None,
                (prov or {}).get("evidence_ref"),
                link=gr_link,
                record_type="goods_receipt",
                record_id=str(gr["gr_id"]),
            ),
        },
        po_href=f"/bzg/finance/po/{gr['po_id']}",
        bill=(
            {
                **dict(bill),
                "evidence": _evidence_status(
                    bill["photo_object_ref"],
                    link=_evlink.evidence_for_record(conn, "supplier_bill", str(bill["bill_id"])),
                    record_type="supplier_bill",
                    record_id=str(bill["bill_id"]),
                ),
                "href": f"/bzg/finance/notas/{bill['bill_id']}",
            }
            if bill
            else None
        ),
        reconciliation={
            "migration_status": (prov or {}).get("migration_status"),
            "source_id": (prov or {}).get("source_id"),
            "needs_reconciliation": (prov or {}).get("migration_status") == "NEEDS RECONCILIATION",
        },
    )


def nota_detail(bill_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM bzg_ops_supplier_bills WHERE bill_id=?",
        ((bill_id or "").strip(),),
    ).fetchone()
    if not row:
        return public(ok=False, error="not_found", bill_id=bill_id)
    bill = dict(row)
    lines = conn.execute(
        """
        SELECT line_id, item, billed_qty, billed_unit_price, line_amount, unit
        FROM bzg_ops_bill_lines WHERE bill_id=? ORDER BY created_at, line_id
        """,
        (bill["bill_id"],),
    ).fetchall()
    prov = _provenance(bill["bill_id"], "supplier_bill", conn)
    ap = conn.execute(
        "SELECT ap_ready_id, match_id, match_result, created_at FROM bzg_ops_ap_ready WHERE bill_id=?",
        (bill["bill_id"],),
    ).fetchone()
    ev = _evidence_status(
        bill.get("photo_object_ref"),
        (prov or {}).get("evidence_ref"),
        link=_evlink.evidence_for_record(conn, "supplier_bill", bill["bill_id"]),
        record_type="supplier_bill",
        record_id=str(bill["bill_id"]),
    )
    if not ev.get("linked"):
        ev["message"] = "No evidence linked yet"
    line_rows = [dict(l) for l in lines]
    computed_total = _computed_bill_total(bill, line_rows)
    stated_total = float(bill.get("stated_total") or 0)
    bank_refs = [str(bill["bill_id"])]
    if prov and prov.get("linked_ledger_id"):
        bank_refs.append(str(prov["linked_ledger_id"]))
    bank_matches = _bank_txns_for_refs(bank_refs, conn, limit=10)
    vendor = _vendor_row(str(bill.get("supplier_id") or ""), conn)
    ap_row = None
    if ap:
        match_id = str(ap["match_id"] or "")
        ap_row = {
            "ap_ready_id": ap["ap_ready_id"],
            "match_result": ap["match_result"],
            "created_at": ap["created_at"],
            "status_label": _ap_status_label(match_id, str(ap["match_result"] or "")),
            "match_label": _ap_match_label(match_id, str(ap["match_result"] or "")),
        }
    return public(
        ok=True,
        nota={
            **bill,
            "outlet_label": OUTLET_LABELS.get(bill.get("outlet_id") or "", bill.get("outlet_id")),
            "lines": line_rows,
            "line_count": len(line_rows),
            "stated_total": stated_total,
            "computed_total": computed_total,
            "totals_match": computed_total is not None and abs(stated_total - computed_total) < 1.0,
            "evidence": ev,
        },
        po_href=f"/bzg/finance/po/{bill['po_id']}",
        receipt_href=f"/bzg/finance/receipts/{bill['gr_id']}",
        vendor_href=f"/bzg/finance/suppliers/{vendor['vendor_id']}" if vendor else None,
        ap_ready=ap_row,
        ap_href="/bzg/finance/ap",
        bank_matches=bank_matches,
        reconciliation={
            "migration_status": (prov or {}).get("migration_status"),
            "source_id": (prov or {}).get("source_id"),
            "linked_ledger_id": (prov or {}).get("linked_ledger_id"),
            "needs_reconciliation": (prov or {}).get("migration_status") == "NEEDS RECONCILIATION",
        },
    )


def list_petty(
    conn: sqlite3.Connection,
    *,
    outlet: str | None = None,
    historical_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit or 100), 500))
    off = max(0, int(offset or 0))
    clauses = ["entity_id=?"]
    params: list[Any] = [ENTITY]
    if historical_only:
        clauses.append("source_system=?")
        params.append(_hist.SOURCE_SYSTEM)
    if outlet:
        clauses.append("(outlet LIKE ? OR venue=?)")
        params.extend([f"%{outlet}%", outlet])
    where = " AND ".join(clauses)
    total = conn.execute(
        f"SELECT COUNT(*) FROM bzg_ops_petty_movements WHERE {where}",
        params,
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT movement_id, business_date, direction, amount, currency, purpose,
               outlet, venue, migration_status, receipt_path, photo_evidence_id, source_id
        FROM bzg_ops_petty_movements
        WHERE {where}
        ORDER BY business_date DESC, movement_id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, lim, off),
    ).fetchall()
    movements = []
    for row in rows:
        rp = (row["receipt_path"] or "").strip()
        pe = (row["photo_evidence_id"] or "").strip()
        ev = _evidence_status(
            None,
            pe or rp,
            link=_evlink.evidence_for_record(conn, "petty_cash", str(row["movement_id"])),
        )
        movements.append(
            {
                **dict(row),
                "evidence": ev,
                "unresolved": row["migration_status"] == "NEEDS RECONCILIATION"
                or (row["movement_id"] == "PETTY-HIST-317"),
            }
        )
    return public(
        ok=True,
        movements=movements,
        total=int(total),
        limit=lim,
        offset=off,
        historical_only=historical_only,
    )


def list_bank(
    conn: sqlite3.Connection,
    *,
    recon_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit or 100), 500))
    off = max(0, int(offset or 0))
    clauses = ["entity_id=?"]
    params: list[Any] = [ENTITY]
    status_filter = (recon_status or "").strip().upper()
    if status_filter:
        if status_filter == "POSSIBLE":
            status_filter = "POSSIBLE MATCH"
        clauses.append("recon_status=?")
        params.append(status_filter)
    where = " AND ".join(clauses)
    total = conn.execute(
        f"SELECT COUNT(*) FROM bzg_bank_transactions WHERE {where}",
        params,
    ).fetchone()[0]
    unmatched = conn.execute(
        "SELECT COUNT(*) FROM bzg_bank_transactions WHERE entity_id=? AND recon_status='UNMATCHED'",
        (ENTITY,),
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT txn_id, txn_date, value_date, description, reference,
               debit, credit, running_balance, recon_status, bank_account,
               matched_ledger_source_id, match_confidence, notes
        FROM bzg_bank_transactions
        WHERE {where}
        ORDER BY txn_date DESC, txn_id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, lim, off),
    ).fetchall()
    summary = _bank_recon.recon_summary(conn)
    return public(
        ok=True,
        transactions=[_bank_recon.enrich_transaction_row(r) for r in rows],
        total=int(total),
        unmatched_total=int(unmatched),
        state_counts=summary.get("state_counts") or {},
        missing_statement_months=summary.get("missing_statement_months") or [],
        parsed_import_count=summary.get("parsed_import_count") or 0,
        transaction_count=summary.get("transaction_count") or 0,
        limit=lim,
        offset=off,
        honest_empty=total == 0,
        recon_filter=status_filter or None,
    )


def list_ap(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    offset: int = 0,
    outlet_id: str | None = None,
) -> dict[str, Any]:
    lim = max(1, min(int(limit or 100), 200))
    off = max(0, int(offset or 0))
    clauses = ["entity_id=?"]
    params: list[Any] = [ENTITY]
    if outlet_id:
        clauses.append("outlet_id=?")
        params.append(outlet_id.strip())
    where = " AND ".join(clauses)
    total = conn.execute(f"SELECT COUNT(*) FROM bzg_ops_ap_ready WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT ap_ready_id, bill_id, supplier_name, nota_number, nota_date,
               stated_total, match_result, match_id, outlet_id, created_at
        FROM bzg_ops_ap_ready
        WHERE {where}
        ORDER BY nota_date DESC, ap_ready_id
        LIMIT ? OFFSET ?
        """,
        (*params, lim, off),
    ).fetchall()
    items = []
    for row in rows:
        match_id = str(row["match_id"] or "")
        items.append(
            {
                "ap_ready_id": row["ap_ready_id"],
                "bill_id": row["bill_id"],
                "supplier_name": row["supplier_name"],
                "nota_number": row["nota_number"],
                "nota_date": row["nota_date"],
                "stated_total": row["stated_total"],
                "match_result": row["match_result"],
                "outlet_id": row["outlet_id"],
                "created_at": row["created_at"],
                "outlet_label": OUTLET_LABELS.get(row["outlet_id"] or "", row["outlet_id"]),
                "status_label": _ap_status_label(match_id, str(row["match_result"] or "")),
                "match_label": _ap_match_label(match_id, str(row["match_result"] or "")),
                "nota_href": f"/bzg/finance/notas/{row['bill_id']}",
                "read_only": True,
            }
        )
    return public(
        ok=True,
        ap_ready=items,
        total=int(total),
        limit=lim,
        offset=off,
        has_more=(off + len(items)) < int(total),
        read_only=True,
    )


def list_ready_to_pay(
    person_id: str,
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    offset: int = 0,
    outlet_id: str | None = None,
) -> dict[str, Any]:
    from core import bzg_ready_to_pay as _rtp

    lim = max(1, min(int(limit or 100), 200))
    off = max(0, int(offset or 0))
    rows = _rtp.list_ready_to_pay(person_id, limit=lim + off + 50, conn=conn)
    if outlet_id:
        oid = outlet_id.strip()
        rows = [r for r in rows if str(r.get("outlet_id") or "") == oid]
    total = len(rows)
    page = rows[off : off + lim]
    items = []
    for row in page:
        items.append(
            {
                **row,
                "outlet_label": OUTLET_LABELS.get(row.get("outlet_id") or "", row.get("outlet_id")),
                "status_label": "Ready to pay",
                "nota_href": f"/bzg/finance/notas/{row.get('bill_id')}",
                "read_only": True,
            }
        )
    return public(
        ok=True,
        ready_to_pay=items,
        total=total,
        limit=lim,
        offset=off,
        has_more=(off + len(items)) < total,
        read_only=True,
        not_a_payment=True,
        payment_execution=False,
    )


def list_exceptions(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit or 100), 500))
    off = max(0, int(offset or 0))
    total = conn.execute(
        "SELECT COUNT(*) FROM bzg_ops_history_provenance WHERE migration_status='NEEDS RECONCILIATION'"
    ).fetchone()[0]
    rows = conn.execute(
        """
        SELECT record_type, beta_id, source_id, source_pr_num, business_date,
               alchemist_status, linked_ledger_id, linked_po_id, linked_gr_id, evidence_ref
        FROM bzg_ops_history_provenance
        WHERE migration_status='NEEDS RECONCILIATION'
        ORDER BY business_date DESC, record_type, beta_id
        LIMIT ? OFFSET ?
        """,
        (lim, off),
    ).fetchall()
    items = []
    for row in rows:
        rt = str(row["record_type"])
        bid = str(row["beta_id"])
        href = None
        if rt == "purchase_order":
            href = f"/bzg/finance/po/{bid}"
        elif rt == "supplier_bill":
            href = f"/bzg/finance/notas/{bid}"
        elif rt in {"goods_receipt", "goods_receipt_synthetic"}:
            href = f"/bzg/finance/receipts/{bid}"
        elif rt == "supplier":
            href = f"/bzg/finance/suppliers/{bid}"
        items.append({**dict(row), "href": href, "read_only": True})
    return public(
        ok=True,
        exceptions=items,
        total=int(total),
        limit=lim,
        offset=off,
        read_only=True,
    )
