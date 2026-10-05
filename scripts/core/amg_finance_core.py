#!/usr/bin/env python3
"""FINANCE-CORE-AMG-PROVE-1 — AMG Finance Core dispatch (entity ENT-AMG).

Operational finance paths reuse ggv_finance_nota + bank modules under ENT-AMG scope.
Does not replace the Atrium ledger desk at /amg/finance (board/ledger/journals).
"""
from __future__ import annotations

import base64
import re
from typing import Any

from core import amg_finance_desk as _desk
from core import finance_core_entity as _fce
from core import ggv_finance_nota as _nota
from core import rbac as _rbac

ENTITY = "ENT-AMG"
PACK = "FINANCE-CORE-AMG-PROVE-1"

PAGE_PATHS = frozenset(
    {
        "/amg/finance/invoices",
        "/amg/finance/notas",
        "/amg/finance/bills",
        "/amg/finance/vendors",
        "/amg/finance/suppliers",
        "/amg/finance/customers",
        "/amg/finance/history",
        "/amg/finance/reports",
        "/amg/finance/receipts",
        "/amg/finance/banking",
        "/amg/finance/statements",
        "/amg/finance/transactions",
        "/amg/finance/reconciliation",
        "/amg/finance/missing-evidence",
        "/amg/finance/audit",
        "/amg-finance-ops",
        "/amg/finance-ops",
        "/amg-finance-ops.html",
        "/dashboards/amg-finance-ops.html",
    }
)

OPERATIONAL_API_SUFFIXES = frozenset(
    {
        "",
        "/",
        "/overview",
        "/desk",
        "/reconciliation",
        "/reconciliation/queue",
        "/audit",
        "/notas",
        "/bills",
        "/vendors",
        "/history",
        "/search",
        "/bank-statements",
        "/bank-statements/import",
        "/bank-transactions",
        "/statements",
        "/statements/library",
        "/statements/completeness",
        "/uploads",
    }
)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "proven": False,
    "entity_id": ENTITY,
    "pack": PACK,
}


FinanceNotaError = _nota.FinanceNotaError


def matches(path: str) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
        return True
    if trimmed.startswith("/amg/finance/") and not trimmed.startswith("/api/"):
        return True
    if not trimmed.startswith("/api/amg/finance"):
        return False
    rest = trimmed[len("/api/amg/finance") :] or "/"
    if rest in OPERATIONAL_API_SUFFIXES:
        return True
    if rest.startswith("/uploads") or rest.startswith("/notas") or rest.startswith("/vendors"):
        return True
    if rest.startswith("/bank-statements") or rest.startswith("/bank-transactions"):
        return True
    if rest.startswith("/statements/"):
        return True
    return False


def _payload(data: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    out = dict(HONESTY)
    if data:
        out.update(data)
    out.update(extra)
    out["staff_ready"] = False
    out["human_commissioned"] = False
    out["entity_id"] = ENTITY
    return out


def dispatch(
    method: str,
    path: str,
    qs: dict[str, list[str]],
    body: dict | None,
    person_id: str | None,
) -> dict[str, Any]:
    with _fce.entity_scope(ENTITY):
        raw = (path or "").split("?")[0]
        trimmed = raw.rstrip("/") or "/"
        if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
            conn = _nota.db_connect()
            try:
                _desk.require_amg_finance(person_id, conn)
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
            return {"_html": True}
        if not trimmed.startswith("/api/amg/finance"):
            raise FinanceNotaError("Not found.", code="not_found", http_status=404)
        rest = trimmed[len("/api/amg/finance") :] or "/"
        body = body or {}
        if method == "GET" and rest in {"", "/"}:
            conn = _nota.db_connect()
            try:
                return _payload(_desk.desk_overview(person_id or "", conn))
            finally:
                conn.close()
        if method == "GET" and rest == "/desk":
            conn = _nota.db_connect()
            try:
                return _payload(_desk.desk_overview(person_id or "", conn))
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        if method == "GET" and rest == "/overview":
            conn = _nota.db_connect()
            try:
                _desk.require_amg_finance(person_id or "", conn)
                ctx = {"entity_id": ENTITY}
                if _rbac.can(person_id or "", "finance.nota.read", ctx, conn=conn):
                    return _nota.overview(person_id or "", conn=conn)
                desk = _desk.desk_overview(person_id or "", conn)
                entities = desk.get("finance_entities") or []
                counts = desk.get("counts") or {}
                return _payload(
                    {
                        **desk,
                        "needs_review": 0,
                        "waiting_approval": 0,
                        "payment_unverified": 0,
                        "vendor_issues": 0,
                        "bill_count": counts.get("bills", 0),
                        "recently_added": [],
                        "invoice_desk": {"finance_entities": entities},
                    }
                )
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        if method == "GET" and rest in {"/reconciliation", "/reconciliation/queue"}:
            conn = _nota.db_connect()
            try:
                tab = ((qs.get("tab") or ["possible"])[0] or "possible").strip()
                month = ((qs.get("month") or [""])[0] or "").strip() or None
                lim_raw = (qs.get("limit") or ["50"])[0]
                off_raw = (qs.get("offset") or ["0"])[0]
                try:
                    lim = int(lim_raw or 50)
                except (TypeError, ValueError):
                    lim = 50
                try:
                    off = int(off_raw or 0)
                except (TypeError, ValueError):
                    off = 0
                return _payload(
                    _desk.reconciliation_board(
                        person_id or "",
                        conn,
                        tab=tab,
                        month=month,
                        limit=lim,
                        offset=off,
                    )
                )
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        m_recon_act = re.fullmatch(r"/reconciliation/queue/([^/]+)/(confirm|reject|exception)", rest)
        if m_recon_act and method == "POST":
            conn = _nota.db_connect()
            try:
                return _payload(
                    _desk.reconciliation_action(
                        person_id or "",
                        conn,
                        action=m_recon_act.group(2),
                        txn_id=m_recon_act.group(1),
                        body=body,
                    )
                )
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        if method == "POST" and rest == "/reconciliation/queue/bulk-confirm":
            conn = _nota.db_connect()
            try:
                return _payload(
                    _desk.reconciliation_action(
                        person_id or "",
                        conn,
                        action="bulk_confirm",
                        txn_id="",
                        body=body,
                    )
                )
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        if method == "GET" and rest == "/audit":
            conn = _nota.db_connect()
            try:
                lim_raw = (qs.get("limit") or ["50"])[0]
                try:
                    lim = int(lim_raw or 50)
                except (TypeError, ValueError):
                    lim = 50
                return _payload(_desk.audit_tail(person_id or "", conn, limit=lim))
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
        if method == "GET" and rest == "/notas":
            return _nota.list_notas(person_id)
        if method == "GET" and rest == "/bills":
            conn = _nota.db_connect()
            try:
                _desk.require_amg_finance(person_id, conn)
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
            payload = _nota.list_bills(person_id)
            payload["historical"] = _desk.historical_notice()
            return _payload(payload)
        if method == "GET" and rest == "/vendors":
            conn = _nota.db_connect()
            try:
                payload = _desk.list_vendors_readonly(
                    person_id or "",
                    ((qs.get("q") or [""])[0]),
                    conn,
                )
            except _desk.AmgFinanceDeskError as exc:
                raise FinanceNotaError(str(exc), code=exc.code, http_status=exc.http_status) from exc
            finally:
                conn.close()
            return _payload(payload)
        if method == "GET" and rest in {"/history", "/search"}:
            return _nota.search_history(person_id, qs)
        if method == "GET" and rest in {"/bank-statements", "/statements", "/statements/library"}:
            from core import finance_core_statements as _fcs

            try:
                return _payload(_fcs.list_library(verified_person_id=person_id or "", entity_id=ENTITY))
            except _fcs.FinanceStatementError as exc:
                raise FinanceNotaError(
                    str(exc), code=exc.code, http_status=exc.http_status, extra=exc.details
                ) from exc
        m_stmt_orig = re.fullmatch(r"/statements/([^/]+)/original", rest)
        if m_stmt_orig and method == "GET":
            from core import finance_core_statements as _fcs

            try:
                raw, mime, fname = _fcs.original_bytes(
                    verified_person_id=person_id or "", import_id=m_stmt_orig.group(1), entity_id=ENTITY
                )
            except _fcs.FinanceStatementError as exc:
                raise FinanceNotaError(
                    str(exc), code=exc.code, http_status=exc.http_status, extra=exc.details
                ) from exc
            return {
                "_file": {
                    "data": raw,
                    "content_type": mime,
                    "filename": fname,
                    "disposition": "attachment",
                }
            }
        m_stmt = re.fullmatch(r"/statements/([^/]+)", rest)
        if m_stmt and method == "GET":
            from core import finance_core_statements as _fcs

            try:
                return _payload(
                    _fcs.get_statement(
                        verified_person_id=person_id or "", import_id=m_stmt.group(1), entity_id=ENTITY
                    )
                )
            except _fcs.FinanceStatementError as exc:
                raise FinanceNotaError(
                    str(exc), code=exc.code, http_status=exc.http_status, extra=exc.details
                ) from exc
        if method == "GET" and rest == "/statements/completeness":
            from core import finance_core_statements as _fcs

            try:
                return _payload(_fcs.month_completeness(verified_person_id=person_id or "", entity_id=ENTITY))
            except _fcs.FinanceStatementError as exc:
                raise FinanceNotaError(
                    str(exc), code=exc.code, http_status=exc.http_status, extra=exc.details
                ) from exc
        if method == "GET" and rest == "/bank-transactions":
            from core import amg_bank_statement1 as _abs

            iid = ((qs.get("import_id") or [""])[0] or "").strip() or None
            st = ((qs.get("recon_status") or [""])[0] or "").strip() or None
            lim_raw = (qs.get("limit") or ["200"])[0]
            try:
                lim = int(lim_raw or 200)
            except (TypeError, ValueError):
                lim = 200
            return _payload(
                _abs.list_transactions(
                    verified_person_id=person_id or "",
                    import_id=iid,
                    recon_status=st,
                    limit=lim,
                )
            )
        if method == "POST" and rest == "/bank-statements/import":
            from core import amg_bank_statement1 as _abs

            fname = str(body.get("filename") or body.get("original_filename") or "").strip()
            b64 = body.get("content_base64") or body.get("content_b64")
            if not fname or not b64:
                raise FinanceNotaError(
                    "filename and content_base64 required for bank statement import.",
                    code="missing_file",
                    http_status=400,
                )
            try:
                raw_bytes = base64.b64decode(str(b64), validate=False)
            except Exception as exc:  # noqa: BLE001
                raise FinanceNotaError(
                    "content_base64 is not valid base64",
                    code="invalid_base64",
                    http_status=400,
                ) from exc
            conn = _nota.db_connect()
            try:
                return _payload(
                    _abs.import_statement(
                        verified_person_id=person_id or "",
                        filename=fname,
                        content=raw_bytes,
                        conn=conn,
                    )
                )
            finally:
                conn.close()
        m_upload = re.fullmatch(r"/uploads/([^/]+)", rest)
        if m_upload and method == "GET":
            return _nota.read_upload(person_id or "", m_upload.group(1))
        if method == "POST" and rest == "/uploads":
            conn = _nota.db_connect()
            try:
                return _nota.create_upload(person_id or "", list(body.get("files") or []), conn=conn)
            finally:
                conn.close()
        m_read = re.fullmatch(r"/uploads/([^/]+)/read", rest)
        if m_read and method == "POST":
            return _nota.read_upload(person_id or "", m_read.group(1))
        if method == "POST" and rest == "/notas":
            return _nota.save_nota(person_id or "", body)
        raise FinanceNotaError("That action is not on this screen.", code="not_found", http_status=404)
