#!/usr/bin/env python3
"""BZG-P2P-NOTA-BILL-1 — Supplier nota / bill against a saved goods receipt (Beta).

Persists bzg_ops_supplier_bills / bzg_ops_bill_lines. RECEIVED → BILL_RECEIVED
via uma_ops_console.transition_pr when the request is fully received and the
goods receipt is complete. Not payment, not approval to pay, no AP ledger.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from core import audit as _audit
from core import bzg_goods_receiving as _gr
from core import bzg_outlet_registry as _outlets
from core import bzg_purchase_order as _po
from core import bzg_purchase_request as _pr
from core import rbac as _rbac
from core import uma_ops_console as _ops
from core import wolf_evidence_guard as _weg

PACK = "BZG-P2P-NOTA-BILL-1"
LEGAL_ENTITY = "ENT-BZG"
PERM_BILL_CAPTURE = "bzg.bill.capture"
PERM_BILL_CAPTURE_ID = "PERM-BZG-BILL-CAPTURE"
AUDIT_SOURCE = "bzg_supplier_bill"
NOTA_PHOTO_DIR = _weg.resolve_nota_photo_dir()
NOTA_PHOTO_SCHEME = "bzg-nota://"
REFUSED_PR = _gr.REFUSED_PR
QTY_EPS = _po.QTY_EPS
PRICE_EPS = 1e-2

HONESTY = {
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
    "proven": False,
    "eng_proved": False,
    "payment_execution": False,
    "supplier_bill_capture": True,
    "not_a_payment": True,
    "not_approval_to_pay": True,
    "no_ap_ledger": True,
}


class BillError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def db_connect(db_path=None) -> sqlite3.Connection:
    return _ops.db_connect(db_path)


def mint_bill_id() -> str:
    return f"BILL-UMA-{uuid.uuid4().hex[:12].upper()}"


def ensure_bill_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotent supplier-bill tables."""
    _gr.ensure_gr_schema(conn)
    added: list[str] = []
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bzg_ops_supplier_bills'"
    ).fetchone()
    if not exists:
        conn.executescript(
            """
            CREATE TABLE bzg_ops_supplier_bills (
              bill_id TEXT PRIMARY KEY,
              gr_id TEXT NOT NULL,
              po_id TEXT NOT NULL,
              pr_id TEXT NOT NULL,
              outlet_id TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              supplier_id TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              nota_number TEXT NOT NULL,
              nota_date TEXT NOT NULL,
              photo_object_ref TEXT NOT NULL,
              stated_total REAL NOT NULL,
              computed_total REAL NOT NULL,
              total_difference REAL NOT NULL DEFAULT 0,
              difference_note TEXT,
              capturer_person_id TEXT NOT NULL,
              capturer_assignment_id TEXT,
              created_at TEXT NOT NULL,
              UNIQUE (outlet_id, supplier_id, nota_number)
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_bill_gr ON bzg_ops_supplier_bills(gr_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_bill_po ON bzg_ops_supplier_bills(po_id);
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_bill_pr ON bzg_ops_supplier_bills(pr_id);

            CREATE TABLE IF NOT EXISTS bzg_ops_bill_lines (
              line_id TEXT PRIMARY KEY,
              bill_id TEXT NOT NULL,
              gr_line_id TEXT NOT NULL,
              po_line_id TEXT NOT NULL,
              item TEXT NOT NULL,
              billed_qty REAL NOT NULL,
              billed_unit_price REAL NOT NULL,
              line_amount REAL NOT NULL,
              unit TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bzg_ops_bill_lines_bill ON bzg_ops_bill_lines(bill_id);
            """
        )
        added.extend(["bzg_ops_supplier_bills", "bzg_ops_bill_lines"])
    return added


def bill_capture_permission(conn: sqlite3.Connection) -> str:
    return PERM_BILL_CAPTURE


def _assignment(person_id: str, conn: sqlite3.Connection) -> dict[str, Any] | None:
    return _pr.resolve_active_assignment(person_id, conn)


def can_capture_bill(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> tuple[bool, dict[str, Any] | None]:
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False, None
    outlet = _outlets.get_outlet(oid, conn=conn)
    if not outlet:
        return False, None
    target = _pr.outlet_rbac_target(oid, conn)
    if not _rbac.can(pid, PERM_BILL_CAPTURE, target, conn=conn):
        return False, None
    return True, _assignment(pid, conn)


def require_capture_bill(
    person_id: str, outlet_id: str, conn: sqlite3.Connection
) -> dict[str, Any]:
    ok, asg = can_capture_bill(person_id, outlet_id, conn)
    if not ok or not asg:
        raise BillError(
            "You cannot record a supplier nota for this outlet.",
            code="forbidden",
            http_status=403,
        )
    return asg


def save_nota_photo_bytes(
    *,
    data: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Persist nota photo under Beta state. Returns object_ref for bill save."""
    if not data:
        raise BillError("Nota photo required.", code="missing_photo")
    if len(data) > 8_000_000:
        raise BillError("Photo too large.", code="photo_too_large", http_status=413)
    _weg.assert_live_evidence_writable(NOTA_PHOTO_DIR, label="nota photo")
    NOTA_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".png") or "png" in ctype:
        ext = ".png"
    elif name.endswith(".webp") or "webp" in ctype:
        ext = ".webp"
    elif name.endswith(".heic") or "heic" in ctype:
        ext = ".heic"
    eid = f"EVD-NOTA-{uuid.uuid4().hex[:12].upper()}"
    dest = NOTA_PHOTO_DIR / f"{eid}{ext}"
    dest.write_bytes(data)
    ch = hashlib.sha256(data).hexdigest()
    ref = f"{NOTA_PHOTO_SCHEME}{eid}{ext}"
    out = {
        "ok": True,
        "evidence_id": eid,
        "photo_object_ref": ref,
        "object_ref": ref,
        "content_hash": ch,
        "bytes": len(data),
        "mime_type": content_type or f"image/{ext.lstrip('.')}",
        "filename": filename or dest.name,
        "path": str(dest),
    }
    try:
        idx = NOTA_PHOTO_DIR / "photo-index.jsonl"
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "object_ref": ref,
                        "content_hash": ch,
                        "mime_type": out["mime_type"],
                        "filename": out["filename"],
                        "bytes": out["bytes"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    except OSError:
        pass
    return out


def resolve_nota_photo_path(object_ref: str | None) -> Path | None:
    ref = (object_ref or "").strip()
    if not ref.startswith(NOTA_PHOTO_SCHEME):
        return None
    token = ref[len(NOTA_PHOTO_SCHEME) :].strip()
    if not token or "/" in token or "\\" in token or ".." in token:
        return None
    path = (NOTA_PHOTO_DIR / token).resolve()
    try:
        path.relative_to(NOTA_PHOTO_DIR.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def load_nota_photo_bytes(object_ref: str | None) -> tuple[bytes | None, str | None]:
    path = resolve_nota_photo_path(object_ref)
    if not path:
        return None, None
    data = path.read_bytes()
    ext = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
    }.get(ext, "application/octet-stream")
    return data, mime


def photo_url(object_ref: str | None) -> str | None:
    ref = (object_ref or "").strip()
    if not ref:
        return None
    from urllib.parse import quote

    return f"/api/bzg/uma-blu/supplier-bills/photo?ref={quote(ref, safe='')}"


def _bill_row(conn: sqlite3.Connection, bill_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bzg_ops_supplier_bills WHERE bill_id=?", (bill_id,)
    ).fetchone()
    return dict(row) if row else None


def _bill_lines(conn: sqlite3.Connection, bill_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT line_id, gr_line_id, po_line_id, item, billed_qty,
               billed_unit_price, line_amount, unit
        FROM bzg_ops_bill_lines
        WHERE bill_id=?
        ORDER BY created_at, line_id
        """,
        (bill_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _enrich_bill(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    out = {**row, "lines": _bill_lines(conn, row["bill_id"]), **HONESTY}
    oid = (row.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            out["outlet_display_name"] = outlet.get("display_name")
    ref = row.get("photo_object_ref")
    out["photo_url"] = photo_url(ref)
    diff = float(row.get("total_difference") or 0)
    if abs(diff) > PRICE_EPS:
        out["difference_display"] = f"difference Rp {abs(diff):,.0f}".replace(",", ".")
    else:
        out["difference_display"] = None
    try:
        from core import bzg_three_way_match as _match

        _match.ensure_match_schema(conn)
        m = _match.match_for_bill(conn, row["bill_id"])
        if m:
            out["three_way_match"] = {
                "result": m.get("result"),
                "summary": m.get("summary"),
                "created_at": m.get("created_at"),
                "is_match": m.get("is_match"),
                "is_difference": m.get("is_difference"),
                "exception_accepted": m.get("exception_accepted"),
                "difference_pending_acceptance": m.get("difference_pending_acceptance"),
                "ap_eligible": m.get("ap_eligible"),
                "acceptance_display": m.get("acceptance_display"),
                "line_details": m.get("line_details"),
            }
    except Exception:
        pass
    return out


def list_bills_for_gr(conn: sqlite3.Connection, gr_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM bzg_ops_supplier_bills
        WHERE gr_id=?
        ORDER BY created_at DESC, bill_id DESC
        """,
        (gr_id,),
    ).fetchall()
    return [_enrich_bill(dict(r), conn) for r in rows]


def enrich_gr_with_bills(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    gr_id = str(row.get("gr_id") or "")
    bills = list_bills_for_gr(conn, gr_id) if gr_id else []
    return {**row, "supplier_bills": bills}


def _validate_source_gr(gr_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    key = (gr_id or "").strip()
    row = conn.execute(
        "SELECT * FROM bzg_ops_goods_receipts WHERE gr_id=?", (key,)
    ).fetchone()
    if not row:
        raise BillError("Goods receipt not found.", code="not_found", http_status=404)
    gr = dict(row)
    pr_id = str(gr.get("pr_id") or "")
    if pr_id == REFUSED_PR:
        raise BillError("This receipt cannot be billed.", code="refused_pr", http_status=400)
    pr_row = _ops.get_pr(pr_id, conn=conn)
    if not pr_row:
        raise BillError("Source request not found.", code="not_found", http_status=404)
    if pr_row.get("example"):
        raise BillError("Example receipts cannot be billed.", code="example_denied", http_status=400)
    gr_lines = _gr._gr_lines(conn, key)  # noqa: SLF001
    if not gr_lines:
        raise BillError("Receipt has no lines.", code="missing_lines", http_status=400)
    return {**gr, "pr_row": pr_row, "gr_lines": gr_lines}


def _validate_bill_lines(
    requested: list[dict[str, Any]] | None,
    gr_lines: list[dict[str, Any]],
    *,
    client_outlet: str | None = None,
    client_supplier: str | None = None,
    client_po_id: str | None = None,
    stored_outlet: str,
    stored_supplier: str,
    stored_po_id: str,
) -> list[dict[str, Any]]:
    if client_outlet and client_outlet.strip() != stored_outlet:
        raise BillError(
            "Outlet does not match the goods receipt.",
            code="outlet_mismatch",
            http_status=400,
        )
    if client_supplier and client_supplier.strip() != stored_supplier:
        raise BillError(
            "Supplier does not match the goods receipt.",
            code="supplier_mismatch",
            http_status=400,
        )
    if client_po_id and client_po_id.strip() != stored_po_id:
        raise BillError(
            "Order does not match the goods receipt.",
            code="po_mismatch",
            http_status=400,
        )
    if not requested:
        raise BillError("At least one billed line is required.", code="missing_lines")
    by_gr_line: dict[str, dict[str, Any]] = {}
    for gl in gr_lines:
        lid = str(gl.get("line_id") or "").strip()
        if lid:
            by_gr_line[lid] = gl
    out: list[dict[str, Any]] = []
    for raw in requested:
        if not isinstance(raw, dict):
            raise BillError("Each line must be an object.", code="invalid_line")
        gr_line_id = str(
            raw.get("gr_line_id") or raw.get("line_id") or raw.get("receipt_line_id") or ""
        ).strip()
        if not gr_line_id or gr_line_id not in by_gr_line:
            raise BillError(
                "Line is not on this goods receipt.",
                code="line_not_on_receipt",
            )
        try:
            qty = float(raw.get("billed_qty", raw.get("qty")))
            unit_price = float(raw.get("billed_unit_price", raw.get("unit_price")))
        except (TypeError, ValueError) as exc:
            raise BillError("Billed qty and unit price must be numeric.", code="invalid_qty") from exc
        if qty < 0 or unit_price < 0:
            raise BillError("Billed qty and unit price cannot be negative.", code="invalid_qty")
        if qty <= QTY_EPS:
            raise BillError("Enter a billed quantity on each line.", code="invalid_qty")
        gl = by_gr_line[gr_line_id]
        received = float(gl.get("received_qty") or 0)
        if qty - received > QTY_EPS:
            raise BillError(
                f"Billed qty for {gl.get('item')} exceeds received qty ({received}).",
                code="qty_above_received",
            )
        amount = qty * unit_price
        out.append(
            {
                "gr_line_id": gr_line_id,
                "po_line_id": gl["po_line_id"],
                "item": gl["item"],
                "billed_qty": qty,
                "billed_unit_price": unit_price,
                "line_amount": amount,
                "unit": gl.get("unit"),
            }
        )
    return out


def _format_difference(stated: float, computed: float) -> tuple[float, str | None]:
    diff = stated - computed
    if abs(diff) <= PRICE_EPS:
        return 0.0, None
    note = f"difference Rp {abs(diff):,.0f}".replace(",", ".")
    return diff, note


def create_supplier_bill(
    *,
    person_id: str,
    gr_id: str,
    nota_number: str,
    nota_date: str,
    photo_object_ref: str,
    stated_total: float,
    lines: list[dict[str, Any]],
    outlet_id: str | None = None,
    supplier_id: str | None = None,
    po_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise BillError("Authentication required.", code="unauthenticated", http_status=401)
    nota_num = (nota_number or "").strip()
    if not nota_num:
        raise BillError("Supplier nota number is required.", code="missing_nota_number")
    nota_dt = (nota_date or "").strip()
    if not nota_dt:
        raise BillError("Nota date is required.", code="missing_nota_date")
    photo_ref = (photo_object_ref or "").strip()
    if not photo_ref or not resolve_nota_photo_path(photo_ref):
        raise BillError("Nota photo is required.", code="missing_photo")
    try:
        stated = float(stated_total)
    except (TypeError, ValueError) as exc:
        raise BillError("Nota total must be numeric.", code="invalid_total") from exc
    if stated < 0:
        raise BillError("Nota total cannot be negative.", code="invalid_total")

    own = conn is None
    c = conn or db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_bill_schema(c)
        source = _validate_source_gr(gr_id, c)
        oid = str(source["outlet_id"])
        asg = require_capture_bill(pid, oid, c)
        validated = _validate_bill_lines(
            lines,
            source["gr_lines"],
            client_outlet=(outlet_id or "").strip() or None,
            client_supplier=(supplier_id or "").strip() or None,
            client_po_id=(po_id or "").strip() or None,
            stored_outlet=oid,
            stored_supplier=str(source["supplier_id"]),
            stored_po_id=str(source["po_id"]),
        )
        dup = c.execute(
            """
            SELECT bill_id FROM bzg_ops_supplier_bills
            WHERE outlet_id=? AND supplier_id=? AND nota_number=?
            """,
            (oid, source["supplier_id"], nota_num),
        ).fetchone()
        if dup:
            raise BillError(
                "This supplier nota number is already saved for this outlet.",
                code="duplicate_nota",
                http_status=409,
            )
        computed = sum(ln["line_amount"] for ln in validated)
        diff, diff_note = _format_difference(stated, computed)
        ts = _ops.now_utc_iso()
        bill_id = mint_bill_id()
        c.execute(
            """
            INSERT INTO bzg_ops_supplier_bills (
              bill_id, gr_id, po_id, pr_id, outlet_id, entity_id,
              supplier_id, supplier_name, nota_number, nota_date,
              photo_object_ref, stated_total, computed_total, total_difference,
              difference_note, capturer_person_id, capturer_assignment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_id,
                source["gr_id"],
                source["po_id"],
                source["pr_id"],
                oid,
                source["entity_id"],
                source["supplier_id"],
                source["supplier_name"],
                nota_num,
                nota_dt,
                photo_ref,
                stated,
                computed,
                diff,
                diff_note,
                pid,
                asg.get("assignment_id"),
                ts,
            ),
        )
        for line in validated:
            c.execute(
                """
                INSERT INTO bzg_ops_bill_lines (
                  line_id, bill_id, gr_line_id, po_line_id, item,
                  billed_qty, billed_unit_price, line_amount, unit, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"BLN-{uuid.uuid4().hex[:12].upper()}",
                    bill_id,
                    line["gr_line_id"],
                    line["po_line_id"],
                    line["item"],
                    line["billed_qty"],
                    line["billed_unit_price"],
                    line["line_amount"],
                    line.get("unit"),
                    ts,
                ),
            )
        pr_state = str(source["pr_row"].get("state") or "")
        gr_status = str(source.get("status") or "")
        if pr_state == "RECEIVED" and gr_status == "COMPLETE":
            try:
                _ops.transition_pr(
                    str(source["pr_id"]),
                    "BILL_RECEIVED",
                    verified_person_id=pid,
                    actor_type="PERSON",
                    bill_reference=nota_num,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _ops.UmaOpsError as exc:
                raise BillError(str(exc), code=getattr(exc, "code", "transition_failed")) from exc
        _audit.record_event(
            action="bzg.supplier_bill.create",
            result="SUCCEEDED",
            source=AUDIT_SOURCE,
            actor_type="PERSON",
            verified_person_id=pid,
            actor_person_id=pid,
            entity_id=LEGAL_ENTITY,
            brand_id=source["pr_row"].get("venue"),
            resource_type="bzg_supplier_bill",
            resource_id=bill_id,
            metadata={
                "gr_id": source["gr_id"],
                "po_id": source["po_id"],
                "pr_id": source["pr_id"],
                "outlet_id": oid,
                "nota_number": nota_num,
                "stated_total": stated,
                "computed_total": computed,
                "total_difference": diff,
                "line_count": len(validated),
            },
            conn=c,
            commit=False,
            actor_auth_identity_id=(identity or {}).get("auth_identity_id"),
            identity_assurance=(identity or {}).get("assurance"),
        )
        if commit:
            c.commit()
        row = _bill_row(c, bill_id)
        assert row
        return _enrich_bill(row, c)
    except Exception:
        if own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()


def get_supplier_bill(
    bill_id: str,
    *,
    person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or db_connect()
    try:
        ensure_bill_schema(c)
        row = _bill_row(c, (bill_id or "").strip())
        if not row:
            return None
        if person_id:
            oid = str(row.get("outlet_id") or "")
            if oid and not can_capture_bill(person_id, oid, c)[0]:
                allowed = {o["outlet_id"] for o in _pr.person_outlets(person_id, c)}
                if oid not in allowed:
                    return None
        return _enrich_bill(row, c)
    finally:
        if own:
            c.close()
