#!/usr/bin/env python3
"""CORE-ENT-1 / BZG-FINANCE-USABILITY-1 — BZG Finance desk (entity-scoped browse + books shell)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from core import bzg_finance_usability_ro as _browse
from core import bzg_history_completeness_ro as _completeness
from core import bzg_receive_evidence1 as _recv_ev
from core import entity_books as _books
from core import finance_core_entity as _fce
from core import ggv_finance_invoice as _inv
from core import rbac as _rbac

ENTITY = "ENT-BZG"
BOARD_PERM = "atrium.board.read"
PACK = "FINANCE-CORE-BZG-PROVE-1"
USABILITY_PACK = "BZG-FINANCE-USABILITY-1"

PAGE_PREFIX = "/bzg/finance"
PAGE_PATHS = frozenset(
    {
        "/bzg/finance",
        "/bzg/finance/",
    }
)

# Uma Blu pages finance controllers may open without venue ops scope (read-only).
FINANCE_UMA_BLU_HTML_PAGES = frozenset(
    {
        "bzg-uma-blu-ap.html",
        "bzg-uma-blu-ready-to-pay.html",
        "bzg-uma-blu-bills.html",
        "bzg-uma-blu-evidence.html",
        "bzg-uma-blu-exceptions.html",
        "bzg-uma-blu-purchase-orders.html",
        "bzg-uma-blu-pr.html",
    }
)

_FINANCE_UMA_BLU_API_PREFIXES = (
    "/api/bzg/uma-blu/ap",
    "/api/bzg/uma-blu/ready-to-pay",
    "/api/bzg/uma-blu/purchase-orders",
    "/api/bzg/uma-blu/prs",
    "/api/bzg/uma-blu/evidence",
    "/api/bzg/uma-blu/exceptions",
    "/api/bzg/uma-blu/supplier-bills",
    "/api/bzg/uma-blu/goods-receipts",
    "/api/bzg/uma-blu/three-way-match",
)

_FINANCE_UMA_BLU_PAGE_PREFIXES = (
    "/bzg/uma-blu/ap",
    "/bzg/uma-blu/ready-to-pay",
    "/bzg/uma-blu/bills",
    "/bzg/uma-blu/evidence",
    "/bzg/uma-blu/exceptions",
    "/bzg/uma-blu/purchase-orders",
)


def finance_uma_blu_api_path(path: str) -> bool:
    trimmed = (path or "").split("?")[0].rstrip("/") or "/"
    return any(trimmed == prefix or trimmed.startswith(prefix + "/") for prefix in _FINANCE_UMA_BLU_API_PREFIXES)


def finance_uma_blu_page_path(path: str) -> bool:
    trimmed = (path or "").split("?")[0].rstrip("/") or "/"
    return any(trimmed == prefix or trimmed.startswith(prefix + "/") for prefix in _FINANCE_UMA_BLU_PAGE_PREFIXES)

HONESTY = {
    "staff_ready": False,
    "human_commissioned": False,
    "zayen_ready": False,
    "money_movement": False,
    "payment_execute": False,
    "bank_write": False,
    "proven": False,
    "read_only": True,
    "entity_id": ENTITY,
    "legal_entity_id": ENTITY,
    "pack": PACK,
}


class BzgFinanceError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _page_path(raw: str) -> bool:
    trimmed = raw.rstrip("/") or "/"
    if trimmed in PAGE_PATHS or raw in PAGE_PATHS:
        return True
    return trimmed.startswith(PAGE_PREFIX + "/") and not trimmed.startswith("/api/")


def matches(path: str) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    if trimmed.startswith("/api/bzg/finance"):
        return True
    return _page_path(trimmed) or _page_path(raw)


def _can_read_finance(person_id: str, conn: sqlite3.Connection) -> bool:
    ctx = {"entity_id": ENTITY}
    return bool(
        _rbac.can(person_id, "finance.nota.read", ctx, conn=conn)
        or _rbac.can(person_id, BOARD_PERM, ctx, conn=conn)
    )


def require_board(person_id: str | None, conn: sqlite3.Connection) -> None:
    pid = (person_id or "").strip()
    if not pid:
        raise BzgFinanceError("Sign in required.", code="unauthenticated", http_status=401)
    if not _can_read_finance(pid, conn):
        raise BzgFinanceError(
            "BZG Finance is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _qs_int(qs: dict[str, list[str]] | None, key: str, default: int) -> int:
    if not qs:
        return default
    raw = (qs.get(key) or [""])[0]
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return default


def _qs_str(qs: dict[str, list[str]] | None, key: str, default: str = "") -> str:
    if not qs:
        return default
    return str((qs.get(key) or [default])[0] or default)


def overview(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    require_board(person_id, conn)
    entities = _inv.finance_entities(person_id, conn)
    try:
        stamp = _books.desk_stamp(ENTITY)
    except Exception:
        stamp = {
            "books_enabled": True,
            "books_opened": True,
            "empty": True,
            "shell_kind": "empty_shell",
            "message": "Blu Zone Group books are unavailable to read right now.",
            "journals": 0,
            "accounts": 0,
            "db_file": "atrium-bzg.sqlite",
        }
    counts = _browse.desk_counts(conn)
    cfg = _fce.entity_config(ENTITY)
    return {
        **HONESTY,
        "pack": PACK,
        "usability_pack": USABILITY_PACK,
        "shared_core": {
            "entity_scope": "finance_core_entity",
            "statements": "finance_core_statements",
            "page_prefix": str(cfg.get("page_prefix") or PAGE_PREFIX),
            "api_prefix": str(cfg.get("api_prefix") or "/api/bzg/finance"),
        },
        "operational": True,
        "completeness_only": False,
        **{k: stamp[k] for k in (
            "books_enabled",
            "books_opened",
            "empty",
            "shell_kind",
            "journals",
            "accounts",
            "db_file",
            "outlet_id_nullable",
        ) if k in stamp},
        "ok": True,
        "title": "BZG Finance",
        "message": stamp.get("message") or (
            "Imported Blu Zone Group history. No journals posted yet."
        ),
        "finance_entities": entities,
        "active_entity": {"id": "BZG", "label": "BZG", "entity_id": ENTITY},
        "completeness": _completeness.load_completeness(conn),
        "counts": counts.get("counts") or {},
        "browse_nav": [
            {"label": "Suppliers", "href": "/bzg/finance/suppliers"},
            {"label": "Petty cash", "href": "/bzg/finance/petty"},
            {"label": "Bank", "href": "/bzg/finance/bank"},
            {"label": "AP ready", "href": "/bzg/finance/ap"},
            {"label": "Ready to pay", "href": "/bzg/finance/ready-to-pay"},
            {"label": "Exceptions", "href": "/bzg/finance/exceptions"},
            {"label": "Completeness", "href": "/bzg/finance/completeness"},
            {"label": "Photos to review", "href": "/bzg/finance/photos-to-review"},
        ],
        "operating_unit_hook": "OU-BZG-RAIN-POOL",
        "outlet_registry": "/bzg/outlets",
    }


def _recv_ev_error(exc: _recv_ev.ReceiveEvidenceError) -> BzgFinanceError:
    return BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status)


def dispatch(
    method: str,
    path: str,
    person_id: str | None,
    conn: sqlite3.Connection,
    qs: dict[str, list[str]] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = (path or "").split("?")[0]
    trimmed = raw.rstrip("/") or "/"
    if trimmed in {"/bzg/finance/photos-to-review", "/bzg/finance/photos-to-review/"}:
        require_board(person_id, conn)
        return {"_html": True}
    if _page_path(trimmed) or _page_path(raw):
        require_board(person_id, conn)
        return {"_html": True}
    if not trimmed.startswith("/api/bzg/finance"):
        raise BzgFinanceError("Not found.", code="not_found", http_status=404)
    if method == "POST":
        return _dispatch_post(trimmed, person_id, conn, body or {})
    if method != "GET":
        raise BzgFinanceError(
            "BZG Finance money writes are not opened on this pack.",
            code="method_not_allowed",
            http_status=405,
        )
    rest = trimmed[len("/api/bzg/finance") :] or "/"
    if rest in {"", "/", "/overview"}:
        return overview(person_id or "", conn)
    if rest == "/counts":
        require_board(person_id, conn)
        return _browse.desk_counts(conn)
    if rest == "/completeness":
        require_board(person_id, conn)
        return _completeness.load_completeness(conn)
    if rest.startswith("/completeness/"):
        require_board(person_id, conn)
        ds = rest[len("/completeness/") :].strip("/")
        return _completeness.gap_detail(ds, conn)
    if rest == "/books":
        require_board(person_id, conn)
        return {**HONESTY, **_books.desk_stamp(ENTITY), "ok": True}
    if rest == "/suppliers":
        require_board(person_id, conn)
        return _browse.search_suppliers(
            _qs_str(qs, "q"),
            conn,
            limit=_qs_int(qs, "limit", 50),
            offset=_qs_int(qs, "offset", 0),
            outlet_id=_qs_str(qs, "outlet") or None,
        )
    m_sup = re.fullmatch(r"/suppliers/([^/]+)", rest)
    if m_sup:
        require_board(person_id, conn)
        return _browse.supplier_detail(
            m_sup.group(1),
            conn,
            limit=_qs_int(qs, "limit", 100),
            outlet_id=_qs_str(qs, "outlet") or None,
        )
    m_po = re.fullmatch(r"/po/([^/]+)", rest)
    if m_po:
        require_board(person_id, conn)
        return _browse.po_detail(m_po.group(1), conn)
    m_gr = re.fullmatch(r"/receipts/([^/]+)", rest)
    if m_gr:
        require_board(person_id, conn)
        return _browse.receipt_detail(m_gr.group(1), conn)
    m_nota = re.fullmatch(r"/notas/([^/]+)", rest)
    if m_nota:
        require_board(person_id, conn)
        return _browse.nota_detail(m_nota.group(1), conn)
    if rest == "/petty":
        require_board(person_id, conn)
        hist = _qs_str(qs, "historical", "1").lower() not in {"0", "false", "no"}
        return _browse.list_petty(
            conn,
            outlet=_qs_str(qs, "outlet") or None,
            historical_only=hist,
            limit=_qs_int(qs, "limit", 100),
            offset=_qs_int(qs, "offset", 0),
        )
    if rest == "/bank":
        require_board(person_id, conn)
        return _browse.list_bank(
            conn,
            recon_status=_qs_str(qs, "recon_status") or None,
            limit=_qs_int(qs, "limit", 100),
            offset=_qs_int(qs, "offset", 0),
        )
    if rest in {"/bank/queue", "/bank/recon/queue"}:
        require_board(person_id, conn)
        from core import fc_recon_queues1 as _queue

        tab = _qs_str(qs, "tab", "possible") or "possible"
        month = _qs_str(qs, "month") or None
        try:
            return _queue.list_queue(
                conn,
                entity=ENTITY,
                tab=tab,
                month=month,
                limit=_qs_int(qs, "limit", 50),
                offset=_qs_int(qs, "offset", 0),
            )
        except _queue.ReconQueueError as exc:
            raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    if rest == "/bank/recon":
        require_board(person_id, conn)
        from core import bzg_bank_recon1 as _bank_recon

        return _bank_recon.recon_summary(conn)
    if rest in {"/statements", "/statements/library", "/bank-statements"}:
        require_board(person_id, conn)
        from core import finance_core_entity as _fce
        from core import finance_core_statements as _fcs

        with _fce.entity_scope(ENTITY):
            try:
                return _fcs.list_library(verified_person_id=person_id or "", conn=conn, entity_id=ENTITY)
            except _fcs.FinanceStatementError as exc:
                raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    if rest == "/statements/completeness":
        require_board(person_id, conn)
        from core import finance_core_entity as _fce
        from core import finance_core_statements as _fcs

        with _fce.entity_scope(ENTITY):
            try:
                return _fcs.month_completeness(
                    verified_person_id=person_id or "", conn=conn, entity_id=ENTITY
                )
            except _fcs.FinanceStatementError as exc:
                raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    m_stmt_orig = re.fullmatch(r"/statements/([^/]+)/original", rest)
    if m_stmt_orig and method == "GET":
        require_board(person_id, conn)
        from core import finance_core_entity as _fce
        from core import finance_core_statements as _fcs

        with _fce.entity_scope(ENTITY):
            try:
                raw, mime, fname = _fcs.original_bytes(
                    verified_person_id=person_id or "", import_id=m_stmt_orig.group(1), entity_id=ENTITY
                )
            except _fcs.FinanceStatementError as exc:
                raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
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
        require_board(person_id, conn)
        from core import finance_core_entity as _fce
        from core import finance_core_statements as _fcs

        with _fce.entity_scope(ENTITY):
            try:
                return _fcs.get_statement(
                    verified_person_id=person_id or "", import_id=m_stmt.group(1), entity_id=ENTITY
                )
            except _fcs.FinanceStatementError as exc:
                raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    if rest == "/ap":
        require_board(person_id, conn)
        return _browse.list_ap(
            conn,
            limit=_qs_int(qs, "limit", 100),
            offset=_qs_int(qs, "offset", 0),
            outlet_id=_qs_str(qs, "outlet") or None,
        )
    if rest == "/ready-to-pay":
        require_board(person_id, conn)
        return _browse.list_ready_to_pay(
            person_id or "",
            conn,
            limit=_qs_int(qs, "limit", 100),
            offset=_qs_int(qs, "offset", 0),
            outlet_id=_qs_str(qs, "outlet") or None,
        )
    if rest == "/exceptions":
        require_board(person_id, conn)
        return _browse.list_exceptions(
            conn, limit=_qs_int(qs, "limit", 100), offset=_qs_int(qs, "offset", 0)
        )
    if rest == "/evidence-review":
        try:
            _recv_ev.require_reviewer(person_id, conn)
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
        return _recv_ev.list_review_queue(
            conn,
            limit=_qs_int(qs, "limit", 50),
            offset=_qs_int(qs, "offset", 0),
        )
    m_review_photo = re.fullmatch(r"/evidence-review/([^/]+)/photo", rest)
    if m_review_photo:
        try:
            _recv_ev.require_reviewer(person_id, conn)
            raw, mime = _recv_ev.photo_bytes(conn, m_review_photo.group(1))
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
        return {
            "_file": {
                "data": raw,
                "content_type": mime,
                "filename": "photo.jpg",
                "disposition": "inline",
            }
        }
    m_review = re.fullmatch(r"/evidence-review/([^/]+)", rest)
    if m_review:
        try:
            _recv_ev.require_reviewer(person_id, conn)
            return _recv_ev.review_detail(conn, m_review.group(1))
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
    m_linked_photo = re.fullmatch(r"/evidence-photo/([^/]+)/([^/]+)", rest)
    if m_linked_photo:
        require_board(person_id, conn)
        try:
            raw, mime = _recv_ev.photo_bytes_for_record(
                conn, m_linked_photo.group(1), m_linked_photo.group(2)
            )
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
        return {
            "_file": {
                "data": raw,
                "content_type": mime,
                "filename": "photo.jpg",
                "disposition": "inline",
            }
        }
    raise BzgFinanceError("Not found.", code="not_found", http_status=404)


def _dispatch_post(
    trimmed: str,
    person_id: str | None,
    conn: sqlite3.Connection,
    body: dict[str, Any],
) -> dict[str, Any]:
    if not trimmed.startswith("/api/bzg/finance"):
        raise BzgFinanceError("Not found.", code="not_found", http_status=404)
    rest = trimmed[len("/api/bzg/finance") :] or "/"
    m_accept = re.fullmatch(r"/evidence-review/([^/]+)/accept", rest)
    if m_accept:
        try:
            return _recv_ev.accept_proposal(conn, m_accept.group(1), person_id or "", commit=True)
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
    m_reject = re.fullmatch(r"/evidence-review/([^/]+)/reject", rest)
    if m_reject:
        try:
            return _recv_ev.reject_proposal(
                conn,
                m_reject.group(1),
                person_id or "",
                str(body.get("reason") or ""),
                commit=True,
            )
        except _recv_ev.ReceiveEvidenceError as exc:
            raise _recv_ev_error(exc) from exc
    from core import fc_recon_queues1 as _queue

    m_bank_confirm = re.fullmatch(r"/bank/queue/([^/]+)/confirm", rest)
    if m_bank_confirm:
        require_board(person_id, conn)
        try:
            return _queue.confirm_match(
                conn,
                entity=ENTITY,
                txn_id=m_bank_confirm.group(1),
                person_id=person_id or "",
            )
        except _queue.ReconQueueError as exc:
            raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    m_bank_reject = re.fullmatch(r"/bank/queue/([^/]+)/reject", rest)
    if m_bank_reject:
        require_board(person_id, conn)
        try:
            return _queue.reject_match(
                conn,
                entity=ENTITY,
                txn_id=m_bank_reject.group(1),
                person_id=person_id or "",
                reason=str(body.get("reason") or ""),
            )
        except _queue.ReconQueueError as exc:
            raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    m_bank_exc = re.fullmatch(r"/bank/queue/([^/]+)/exception", rest)
    if m_bank_exc:
        require_board(person_id, conn)
        try:
            return _queue.mark_exception(
                conn,
                entity=ENTITY,
                txn_id=m_bank_exc.group(1),
                person_id=person_id or "",
                note=str(body.get("note") or body.get("reason") or ""),
            )
        except _queue.ReconQueueError as exc:
            raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    if rest == "/bank/queue/bulk-confirm":
        require_board(person_id, conn)
        try:
            return _queue.bulk_confirm(
                conn,
                entity=ENTITY,
                person_id=person_id or "",
                txn_ids=list(body.get("txn_ids") or []),
                rule=str(body.get("rule") or ""),
            )
        except _queue.ReconQueueError as exc:
            raise BzgFinanceError(str(exc), code=exc.code, http_status=exc.http_status) from exc
    raise BzgFinanceError(
        "BZG Finance money writes are not opened on this pack.",
        code="method_not_allowed",
        http_status=405,
    )


def page_path() -> Path:
    return Path(__file__).resolve().parents[2] / "dashboards" / "bzg-finance.html"
