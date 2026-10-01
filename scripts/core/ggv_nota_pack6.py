#!/usr/bin/env python3
"""Pack 6 — GGV nota capture on a catalog copy. Issue stays blocked.

Amanda-shaped upload, one canonical supplier name, and a saved nota are
proved against a caller-supplied copy of the catalog. The live catalog is
read only. The built-in invoice seed is not allocated. Xero is not called.
staff_ready stays false. Phone commission stays open.
"""
from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from typing import Any

from core import evidence as evidence
from core import ggv_finance_nota as fin
from core import rbac

AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
ALIAS_FILE = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/ggv_nota_supplier_aliases.json"
)
BOOKS = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
PACK = "PACK-06"
PHONE_RESIDUAL = (
    "HUMAN_PROVEN residual stays open: Matt and Amanda phone commission is not done."
)
COUNT_TABLES = ("ggv_notas", "ggv_uploads", "ggv_invoices", "ggv_vendors")


def _honesty(**extra: Any) -> dict[str, Any]:
    payload = fin.public_payload(
        {
            "ok": True,
            "pack": PACK,
            "human_proven": False,
            "xero_write": False,
            "issue_blocked": True,
            "allocated": False,
            "invoice_number": None,
            "phone_commission": PHONE_RESIDUAL,
            "telegram_retired": False,
        }
    )
    payload.update(extra)
    payload["staff_ready"] = False
    payload["proven"] = False
    payload["ready"] = False
    payload["commissioned"] = False
    payload["telegram_retired"] = False
    payload["human_proven"] = False
    payload["xero_write"] = False
    return payload


def _conn_path(conn: sqlite3.Connection) -> Path:
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = row[2] if row else ""
    if not raw:
        raise fin.FinanceNotaError(
            "Catalog connection has no file path.",
            code="bad_db",
            http_status=500,
        )
    return Path(raw).resolve()


def _assert_copy(conn: sqlite3.Connection) -> Path:
    path = _conn_path(conn)
    if path == fin.LIVE_CATALOG_DB:
        raise fin.FinanceNotaError(
            "Pack 6 capture refuses the live catalog. Use a copy.",
            code="live_write_refused",
            http_status=500,
        )
    return path


def _ro(path: Path | None = None) -> sqlite3.Connection:
    src = path or fin.LIVE_CATALOG_DB
    conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def canonical_supplier() -> str:
    if not ALIAS_FILE.is_file():
        raise fin.FinanceNotaError(
            f"Supplier alias file is missing: {ALIAS_FILE}",
            code="alias_missing",
            http_status=500,
        )
    data = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
    for group in data.get("groups") or []:
        if group.get("id") == "m-mart":
            name = str(group.get("canonical") or "").strip()
            if name:
                return name
    raise fin.FinanceNotaError(
        "M-Mart canonical name is missing from the alias file.",
        code="alias_missing",
        http_status=500,
    )


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for table in COUNT_TABLES:
        out[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return out


def _sequence(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT format, next_value FROM fin_invoice_sequences WHERE entity_id=?",
        (fin.ENTITY_GGV,),
    ).fetchone()
    if row is None:
        return {
            "present": False,
            "format": None,
            "next_value": None,
            "rendered_seed": None,
            "allocated": False,
            "reason": "GGV invoice sequence row is absent. Nothing was allocated.",
        }
    fmt = str(row["format"] or "")
    value = int(row["next_value"])
    try:
        rendered = fmt.format(n=value)
    except (IndexError, KeyError, ValueError):
        rendered = None
    return {
        "present": True,
        "format": fmt,
        "next_value": value,
        "rendered_seed": rendered,
        "allocated": False,
        "reason": (
            "This is the built-in seed, not a Xero series and not an issued number. "
            "Issue stays blocked so the seed is not consumed."
        ),
    }


def _seats(conn: sqlite3.Connection) -> dict[str, bool]:
    ggv = {"entity_id": fin.ENTITY_GGV}
    amg = {"entity_id": "ENT-AMG"}
    return {
        "amanda_nota_create": bool(rbac.can(AMANDA, "finance.nota.create", ggv, conn=conn)),
        "amanda_nota_read": bool(rbac.can(AMANDA, "finance.nota.read", ggv, conn=conn)),
        "amanda_invoice_issue": bool(rbac.can(AMANDA, "finance.invoice.issue", ggv, conn=conn)),
        "amanda_amg_board": bool(rbac.can(AMANDA, "atrium.board.read", amg, conn=conn)),
        "zayen_nota_create": bool(rbac.can(ZAYEN, "finance.nota.create", ggv, conn=conn)),
        "zayen_nota_read": bool(rbac.can(ZAYEN, "finance.nota.read", ggv, conn=conn)),
        "zayen_invoice_create": bool(rbac.can(ZAYEN, "finance.invoice.create", ggv, conn=conn)),
    }


def live_snapshot() -> dict[str, Any]:
    conn = _ro()
    try:
        return {
            "catalog": str(fin.LIVE_CATALOG_DB),
            "counts": _counts(conn),
            "sequence": _sequence(conn),
            "seats": _seats(conn),
        }
    finally:
        conn.close()


def books_mtime_ns() -> int | None:
    if not BOOKS.is_file():
        return None
    return BOOKS.stat().st_mtime_ns


def _slip(supplier: str) -> dict[str, Any]:
    text = (
        f"Supplier: {supplier}\n"
        "Amount: not printed\n"
        "Invoice number: not printed\n"
    )
    return {
        "filename": "m-mart-slip.txt",
        "content_type": "text/plain",
        "data_base64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }


def _refuse_other_entity(entity_id: str | None) -> dict[str, Any] | None:
    entity = (entity_id or fin.ENTITY_GGV).strip() or fin.ENTITY_GGV
    if entity in {fin.ENTITY_GGV, "GGV"}:
        return None
    return _honesty(
        ok=False,
        error="entity_denied",
        message="GGV nota capture does not write another entity.",
        entity_id=entity,
        _status=403,
    )


def capture(
    conn: sqlite3.Connection,
    media_root: Path,
    *,
    entity_id: str | None = None,
    person_id: str = AMANDA,
) -> dict[str, Any]:
    """Save one Amanda-shaped nota on a catalog copy. Does not allocate a number."""
    denied = _refuse_other_entity(entity_id)
    if denied:
        return denied
    copy_path = _assert_copy(conn)
    if not media_root.is_dir():
        raise fin.FinanceNotaError(
            "Pack 6 media root is missing. Nothing was written to the NAS.",
            code="media_root_missing",
            http_status=503,
        )
    supplier = canonical_supplier()
    previous_media = fin._MEDIA_ROOT
    previous_catalog = evidence.CATALOG_DB
    fin.set_media_root(media_root)
    evidence.CATALOG_DB = copy_path
    try:
        uploaded = fin.create_upload(person_id, [_slip(supplier)], conn=conn)
        vendor = fin.create_vendor(
            person_id,
            {
                "display_name": supplier,
                "notes": "Pack 6 used the alias-file canonical spelling. No supplier merge was run.",
            },
            conn=conn,
        )
        if vendor.get("error") == "possible_duplicate_vendor":
            matches = vendor.get("matches") or []
            if not matches:
                raise fin.FinanceNotaError(
                    "Vendor duplicate check returned no row.",
                    code="possible_duplicate_vendor",
                    http_status=409,
                )
            vendor = fin.create_vendor(
                person_id,
                {
                    "display_name": supplier,
                    "duplicate_decision": "use_existing",
                    "existing_vendor_id": matches[0]["vendor_id"],
                },
                conn=conn,
            )
        vendor_row = vendor.get("vendor") or {}
        vendor_id = vendor_row.get("vendor_id")
        if not vendor.get("ok") or not vendor_id:
            raise fin.FinanceNotaError(
                "Vendor was not saved on the catalog copy.",
                code="vendor_not_saved",
                http_status=500,
            )
        saved = fin.save_nota(
            person_id,
            {
                "upload_id": uploaded["upload_id"],
                "vendor_id": vendor_id,
                "notes": "Pack 6 capture. Amount not confirmed. Invoice number not assigned.",
                "confirm": {
                    "vendor": True,
                    "amount": False,
                    "invoice_no": False,
                    "date": False,
                },
            },
            conn=conn,
        )
        listed = fin.list_notas(person_id, conn=conn)
        nota = (saved.get("nota") or {})
        return _honesty(
            capture="copy",
            catalog_copy=str(copy_path),
            supplier=supplier,
            upload_id=uploaded.get("upload_id"),
            vendor_id=vendor_id,
            nota=nota,
            listed=len(listed.get("notas") or []),
            counts=_counts(conn),
            sequence=_sequence(conn),
            workflow_state=nota.get("state"),
            amount=nota.get("amount"),
            amount_confirmed=nota.get("amount_confirmed"),
            invoice_no=nota.get("invoice_no") or "",
            entity_id=fin.ENTITY_GGV,
        )
    finally:
        evidence.CATALOG_DB = previous_catalog
        fin.set_media_root(previous_media)


def issue_lane(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Refuse allocation. Read the sequence when a connection is supplied."""
    sequence = None
    if conn is not None:
        sequence = _sequence(conn)
    return _honesty(
        ok=False,
        error="issue_blocked",
        message="Issue is blocked. The seed number was not allocated.",
        sequence=sequence,
        _status=405,
    )


def refuse_xero() -> dict[str, Any]:
    return _honesty(
        ok=False,
        error="xero_write_blocked",
        message="Xero was not called.",
        _status=405,
    )


def http(method: str, path: str, body: dict | None, person_id: str | None) -> dict[str, Any]:
    """Live read and explicit refusals. Does not capture onto the live catalog."""
    if not (person_id or "").strip():
        raise fin.FinanceNotaError(
            "Sign in is required.",
            code="missing_auth",
            http_status=403,
        )
    rest = (path or "").split("?")[0].rstrip("/") or "/"
    if rest.startswith("/api/ggv/finance"):
        rest = rest[len("/api/ggv/finance"):] or "/"
    verb = (method or "GET").upper()
    body = body or {}
    if verb == "POST" and rest in {"/pack6/issue", "/pack6/xero"}:
        conn = _ro()
        try:
            fin.require(person_id, "finance.nota.read", conn)
            if rest.endswith("/xero"):
                return refuse_xero()
            return issue_lane(conn)
        finally:
            conn.close()
    if verb == "POST":
        return _honesty(
            ok=False,
            error="live_capture_refused",
            message="Live catalog capture is refused. Pack 6 proves capture on a copy only.",
            _status=405,
        )
    if verb != "GET" or rest != "/pack6":
        raise fin.FinanceNotaError("That action is not on this screen.", code="not_found", http_status=404)
    conn = _ro()
    try:
        fin.require(person_id, "finance.nota.read", conn)
        snap = {
            "counts": _counts(conn),
            "sequence": _sequence(conn),
            "seats": _seats(conn),
        }
    finally:
        conn.close()
    counts = snap["counts"]
    return _honesty(
        surface="live",
        catalog=str(fin.LIVE_CATALOG_DB),
        counts=counts,
        live_notas=counts["ggv_notas"],
        live_uploads=counts["ggv_uploads"],
        live_invoices=counts["ggv_invoices"],
        live_vendors=counts["ggv_vendors"],
        sequence=snap["sequence"],
        seats=snap["seats"],
        capture="not_run_on_live",
        books_written=False,
        nas_written=False,
    )
