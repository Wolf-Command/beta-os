#!/usr/bin/env python3
"""FIN-AP-AR-SHELL-1 — AP/AR desk shells with SoD honesty (no fake invoices).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-AP-AR-SHELL-1
(armed 2026-09-30 after BZG-WASTE-YIELD-1 PASS_VERIFIED). Thin Beta desks over
entity books (FC-SHELL-2 / FIN-INTERCO-1). Empty AP/AR queues stay empty —
no fake invoices, AR balances, or AP aging. SoD honesty: prepare ≠ approve
(ATRIUM-SOD preserved). staff_ready=false · human_commissioned=false.
Ceiling BUILT only. Does not auto-chain OWNER-NEEDS-YOU-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import fin_interco1 as _fin_interco1
from core import fin_recon_shell1 as _fin_recon

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "FIN-AP-AR-SHELL-1"
SCHEMA_ID = "wolf.fin-ap-ar-shell-1.v1"
BOUND = "beta-fin-safe"
CAP_FIN_AR = "CAP-FIN-04"  # Invoicing & Receivables (honest AR target)
CAP_QUEUE = "CAP-FIN AP/AR"  # Phase2 queue label — not a ledger CAP id invent
OWNER_PERSON = "PERS-MATT"
WITA = timezone(timedelta(hours=8))

PAGE_PATHS = frozenset(
    {
        "/fin/ap-ar-shell-1",
        "/fin/ap-ar-shell-1/",
        "/fin-ap-ar-shell-1",
        "/fin-ap-ar-shell-1/",
        "/fin-ap-ar-shell-1.html",
        "/dashboards/fin-ap-ar-shell-1.html",
    }
)
API_PATH = "/api/fin/ap-ar-shell-1"

# Entity desk stubs over FC-SHELL-2 books — structure only; never invent invoices.
_ENTITY_DESK_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "amg_ap_ar",
        "AMG · AP/AR",
        "AMG",
        "AMG live books + ATRIUM-SOD preparer seats. AP queue EMPTY. AR queue EMPTY. "
        "No fake invoices. prepare ≠ approve. Balance/aging UNKNOWN.",
    ),
    (
        "bzg_ap_ar",
        "BZG · AP/AR",
        "BZG",
        "BZG COA template shell (FC-SHELL-2). Journals stay 0. AP/AR queues EMPTY. "
        "No invented aging or invoices.",
    ),
    (
        "ggv_ap_ar",
        "GGV · AP/AR",
        "GGV",
        "GGV COA template shell (FC-SHELL-2). Journals stay 0. AP/AR queues EMPTY. "
        "No invented AR balances or invoices.",
    ),
)

# SoD seat honesty — people ≠ roles; preparer seats cannot self-approve.
_SOD_SEAT_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "ap_preparer",
        "AP preparer",
        "ROLE-AMG-ACCOUNTS-PAYABLE",
        "Preparer seat (ATRIUM-SOD). May prepare. Must NOT approve own prepare.",
    ),
    (
        "ar_preparer",
        "AR preparer",
        "ROLE-AMG-ACCOUNTS-RECEIVABLE",
        "Preparer seat (ATRIUM-SOD). May prepare. Must NOT approve own prepare.",
    ),
    (
        "fc_approver",
        "FC approver",
        "ROLE-AMG-FINANCIAL-CONTROLLER",
        "Approver/poster with SoD. Distinct person from preparer. prepare ≠ approve.",
    ),
)

PRESERVED_PACKS = ("FC-SHELL-2", "FIN-INTERCO-1", "ATRIUM-SOD")


class FinApArShell1Error(ValueError):
    """Fail closed. Does not invent invoices, aging, balances, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == API_PATH


def _entity_desk(
    stub_id: str,
    label: str,
    entity: str,
    why: str,
) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "entity": entity,
        "kind": "ap_ar_desk_stub",
        "status": "EMPTY",
        "display": "EMPTY",
        "ap_count": 0,
        "ar_count": 0,
        "invoice_count": 0,
        "ap_aging": None,
        "ar_balance": None,
        "currency": None,
        "invented_invoice": False,
        "invented_aging": False,
        "invented_balance": False,
        "why": why,
    }


def _entity_desks() -> list[dict[str, Any]]:
    return [_entity_desk(*spec) for spec in _ENTITY_DESK_SPECS]


def _sod_seats() -> list[dict[str, Any]]:
    return [
        {
            "id": seat_id,
            "label": label,
            "role_id": role_id,
            "prepare": seat_id.endswith("preparer"),
            "approve": seat_id == "fc_approver",
            "self_approve_allowed": False,
            "prepare_equals_approve": False,
            "why": why,
        }
        for seat_id, label, role_id, why in _SOD_SEAT_SPECS
    ]


def _ap_queue() -> list[dict[str, Any]]:
    """AP invoices awaiting prepare/pay. Empty list is honest — no fake invoices."""
    return []


def _ar_queue() -> list[dict[str, Any]]:
    """AR invoices / receivables. Empty list is honest — no fake balances."""
    return []


def fc_shell2_books_preserved() -> dict[str, Any]:
    return _fin_interco1.fc_shell2_books_preserved()


def fin_interco1_preserved() -> dict[str, Any]:
    return _fin_recon.fin_interco1_preserved()


def atrium_sod_preserved() -> dict[str, Any]:
    return _fin_recon.atrium_sod_preserved()


def sod_honesty() -> dict[str, Any]:
    """prepare ≠ approve pin — ATRIUM-SOD rule surface, not a live mutation."""
    seats = _sod_seats()
    preparers = [s for s in seats if s.get("prepare")]
    approvers = [s for s in seats if s.get("approve")]
    return {
        "ok": True,
        "prepare_equals_approve": False,
        "self_approve_allowed": False,
        "preparer_seat_count": len(preparers),
        "approver_seat_count": len(approvers),
        "seats": seats,
        "rule": "preparer_person_id != approver_person_id",
        "why": (
            "SoD honesty: prepare ≠ approve. AP/AR preparer seats cannot "
            "self-approve. ATRIUM-SOD preserved; this pack does not mutate SoD."
        ),
    }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "amg_finance",
            "label": "AMG finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "AMG live books + ATRIUM-SOD. prepare ≠ approve.",
        },
        {
            "id": "ggv_finance",
            "label": "GGV finance desk",
            "href": "/ggv/finance",
            "kind": "existing",
            "note": "GGV COA template shell (FC-SHELL-2).",
        },
        {
            "id": "bzg_finance",
            "label": "BZG finance desk",
            "href": "/bzg/finance",
            "kind": "existing",
            "note": "BZG COA template shell. Journals stay 0.",
        },
        {
            "id": "fin_interco_1",
            "label": "FIN Interco-1",
            "href": "/fin/interco-1",
            "kind": "existing",
            "note": "Preserved structure stubs. Not AP/AR invoices.",
        },
        {
            "id": "fin_recon_shell_1",
            "label": "FIN Recon Shell-1",
            "href": "/fin/recon-shell-1",
            "kind": "existing",
            "note": "Bank FILE_IMPORT_ONLY. Not AP/AR.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    return [
        {
            "id": "ap_queue",
            "label": "AP queue",
            "status": "EMPTY",
            "value": 0,
            "why": "No AP invoices on disk. Empty is honest — not a fake aging board.",
        },
        {
            "id": "ar_queue",
            "label": "AR queue",
            "status": "EMPTY",
            "value": 0,
            "why": "No AR invoices/balances invented. Empty is honest.",
        },
        {
            "id": "sod_prepare_approve",
            "label": "SoD prepare ≠ approve",
            "status": "HONEST",
            "value": None,
            "why": "Preparer seats ≠ FC approver. Self-approve refused.",
        },
        {
            "id": "invoices",
            "label": "Invoices / aging / balances",
            "status": "UNKNOWN",
            "value": None,
            "why": "No fake invoices. AP aging UNKNOWN. AR balance UNKNOWN (not zero).",
        },
        {
            "id": "fc_shell2",
            "label": "FC-SHELL-2 books",
            "status": "PRESERVED" if books.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": books.get("why"),
        },
        {
            "id": "fin_interco1",
            "label": "FIN-INTERCO-1",
            "status": "PRESERVED" if interco.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": interco.get("why"),
        },
        {
            "id": "atrium_sod",
            "label": "ATRIUM-SOD",
            "status": "PRESERVED" if sod.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": sod.get("why"),
        },
        {
            "id": "cap_fin_04",
            "label": "CAP-FIN-04",
            "status": "SPECIFIED",
            "value": None,
            "why": "Invoicing & receivables shell only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_04": CAP_FIN_AR,
        "cap_queue_label": CAP_QUEUE,
        "staff_ready": False,
        "human_commissioned": False,
        "live_ap": False,
        "live_ar": False,
        "live_invoicing": False,
        "invented_invoice": False,
        "invented_aging": False,
        "invented_balance": False,
        "invented_proven": False,
        "invented_ready": False,
        "payment_executed": False,
        "payment_write": False,
        "invoice_write": False,
        "books_write": False,
        "sod_mutate": False,
        "prepare_equals_approve": False,
        "self_approve_allowed": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "ap_aging_unknown": True,
        "ar_balance_unknown": True,
        "fc_shell2_preserved": books.get("ok") is True,
        "fin_interco1_preserved": interco.get("ok") is True,
        "atrium_sod_preserved": sod.get("ok") is True,
        "second_ap_ar_system": False,
        "extends_atrium_sod": True,
        "cap_fin_04_proven": False,
        "cap_fin_04_ready": False,
        "cap_fin_04_maturity": "SPECIFIED",
        "cap_fin_04_ceiling": "BUILT",
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "OWNER-NEEDS-YOU-1",
    }


def refuse_invoice(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "Fake invoices are refused. AP/AR queues stay empty until real source docs land.",
        code="invoice_refused",
    )


def refuse_aging(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "AP aging is UNKNOWN. Not invented as zero or fabricated buckets.",
        code="aging_refused",
    )


def refuse_balance(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "AR balances are UNKNOWN until real receivables land. Not invented.",
        code="balance_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "A payment is not executed on this AP/AR shell.",
        code="payment_refused",
    )


def refuse_self_approve(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "SoD: prepare ≠ approve. Self-approve is refused.",
        code="sod_self_approve",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "PROVEN is refused. CAP-FIN-04 stays SPECIFIED. Empty queues are not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinApArShell1Error(
        "READY is refused. An empty AP/AR shell is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinApArShell1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "invoice",
            "invoices",
            "fake-invoice",
            "ar-invoice",
            "ap-invoice",
            "bill",
            "bills",
        }:
            refuse_invoice(payload)
        if token in {"aging", "ap-aging", "aged", "buckets"}:
            refuse_aging(payload)
        if token in {"balance", "balances", "ar-balance", "amount", "amounts", "money"}:
            refuse_balance(payload)
        if token in {"payment", "payments", "paid", "pay", "transfer", "payout"}:
            refuse_payment(payload)
        if token in {
            "self-approve",
            "self_approve",
            "approve-own",
            "approve_own",
            "sod-bypass",
        }:
            refuse_self_approve(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise FinApArShell1Error(
        "External writes are refused. AP/AR desks are read-only shells.",
        code="write_refused",
    )


def queues_are_empty(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    ap = pack.get("ap_queue") or []
    ar = pack.get("ar_queue") or []
    return (
        len(ap) == 0
        and len(ar) == 0
        and int(pack.get("ap_count") or 0) == 0
        and int(pack.get("ar_count") or 0) == 0
        and int(pack.get("invoice_count") or 0) == 0
    )


def all_entity_desks_empty(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    desks = pack.get("entity_desks") or []
    if not desks:
        return False
    return all(
        d.get("ap_count") == 0
        and d.get("ar_count") == 0
        and d.get("invoice_count") == 0
        and d.get("ap_aging") is None
        and d.get("ar_balance") is None
        and d.get("invented_invoice") is False
        and d.get("invented_aging") is False
        and d.get("invented_balance") is False
        and d.get("status") in ("EMPTY", "UNKNOWN")
        for d in desks
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    desks = _entity_desks()
    ap = _ap_queue()
    ar = _ar_queue()
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    sod_h = sod_honesty()
    ap_count = len(ap)
    ar_count = len(ar)
    invoice_count = ap_count + ar_count
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_FIN_AR, CAP_QUEUE],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "live_ap": False,
        "live_ar": False,
        "live_invoicing": False,
        "ap_count": ap_count,
        "ar_count": ar_count,
        "invoice_count": invoice_count,
        "queues_empty": invoice_count == 0,
        "invented_invoice": False,
        "invented_aging": False,
        "invented_balance": False,
        "payment_executed": False,
        "payment_write": False,
        "invoice_write": False,
        "books_write": False,
        "sod_mutate": False,
        "prepare_equals_approve": False,
        "self_approve_allowed": False,
        "ap_aging": None,
        "ar_balance": None,
        "fc_shell2_preserved": books.get("ok") is True,
        "fin_interco1_preserved": interco.get("ok") is True,
        "atrium_sod_preserved": sod.get("ok") is True,
        "cap_fin_04_proven": False,
        "cap_fin_04_ready": False,
        "cap_fin_04_maturity": flags["cap_fin_04_maturity"],
        "cap_fin_04_ceiling": flags["cap_fin_04_ceiling"],
        "entity_desks": desks,
        "ap_queue": ap,
        "ar_queue": ar,
        "sod_honesty": sod_h,
        "sod_seats": sod_h.get("seats") or [],
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fc_shell2_books": books,
        "fin_interco1": interco,
        "atrium_sod": sod,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_invoices",
            "ap_aging_buckets",
            "ar_balances",
            "payment_write",
            "prepare_equals_approve",
            "CAP-FIN-04 PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "OWNER-NEEDS-YOU-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "entity_desks": [s[0] for s in _ENTITY_DESK_SPECS],
        "sod_seats": [s[0] for s in _SOD_SEAT_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "HONEST", "PRESERVED"],
        "invoice_property": False,
        "aging_property": False,
        "balance_property": False,
        "payment_property": False,
        "prepare_equals_approve": False,
        "writes_accepted": False,
        "extends": [
            "scripts/core/fin_interco1.py",
            "scripts/core/fin_recon_shell1.py",
            "ATRIUM-SOD",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_ap_ar_system": False,
        "why": (
            "AP/AR desk shells over entity books. Empty queues honest. "
            "SoD prepare ≠ approve. No fake invoices."
        ),
    }
