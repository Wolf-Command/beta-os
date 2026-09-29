#!/usr/bin/env python3
"""FIN-INTERCO-1 — Intercompany billing skeleton GGV↔AMG/BZG (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-INTERCO-1
(armed 2026-09-30) plus 2026-09-20 PICK CAP-FIN-06 / CAP-GGV-06 skeletons.
Composes existing scripts/core/fin_intercompany_billing.py and
ggv_intercompany_client.py — does NOT invent a second billing system.
Does NOT invent invoice amounts, journals, settlements, or payments.
FC-SHELL-2 COA templates (BZG/GGV 200/0 journals) and AMG live books
are preserved read-only. CAP-FIN-06 / CAP-GGV-06 stay SPECIFIED.
staff_ready=false · human_commissioned=false. Ceiling BUILT only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import entity_books as _books
from core import fin_intercompany_billing as _fin_ic
from core import ggv_intercompany_client as _ggv_ic

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "FIN-INTERCO-1"
SCHEMA_ID = "wolf.fin-interco-1.v1"
BOUND = "beta-fin-safe"
CAP_FIN = "CAP-FIN-06"
CAP_GGV = "CAP-GGV-06"
OWNER_PERSON = "PERS-MATT"
WITA = timezone(timedelta(hours=8))

PAGE_PATHS = frozenset(
    {
        "/fin/interco-1",
        "/fin/interco-1/",
        "/fin-interco-1",
        "/fin-interco-1/",
        "/fin-interco-1.html",
        "/dashboards/fin-interco-1.html",
    }
)
API_PATH = "/api/fin/interco-1"

# Entity-pair invoice/service stubs — structure only; never invent money.
_PAIR_SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "ggv_to_amg_invoice",
        "GGV → AMG",
        "invoice",
        "EMPTY",
        "Named GGV→AMG invoice stub. Empty is not an invoice. Amount UNKNOWN. "
        "No journal invented. Not live intercompany billing.",
    ),
    (
        "ggv_to_bzg_invoice",
        "GGV → BZG",
        "invoice",
        "EMPTY",
        "Named GGV→BZG invoice stub. Empty is not an invoice. Amount UNKNOWN. "
        "No journal invented. Not live intercompany billing.",
    ),
    (
        "amg_to_ggv_service",
        "AMG → GGV",
        "service",
        "EMPTY",
        "Named AMG→GGV service stub. Empty is not a service record. Amount UNKNOWN. "
        "No settlement invented. Paired with CAP-GGV-06 client mode.",
    ),
    (
        "bzg_to_ggv_service",
        "BZG → GGV",
        "service",
        "EMPTY",
        "Named BZG→GGV service stub. Empty is not a service record. Amount UNKNOWN. "
        "No settlement invented. Paired with CAP-GGV-06 client mode.",
    ),
)

ENTITIES = ("GGV", "AMG", "BZG")


class FinInterco1Error(ValueError):
    """Fail closed. Does not invent amounts, journals, settlements, or PROVEN."""

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


def _pair_stub(
    stub_id: str,
    label: str,
    kind: str,
    status: str,
    why: str,
) -> dict[str, Any]:
    from_ent, _, to_ent = label.partition(" → ")
    return {
        "id": stub_id,
        "label": label,
        "kind": kind,
        "from_entity": from_ent.strip() or None,
        "to_entity": to_ent.strip() or None,
        "status": status,
        "display": status,
        "amount": None,
        "currency": None,
        "invoice_number": None,
        "journal_id": None,
        "settlement_id": None,
        "payment": None,
        "invented_amount": False,
        "invented_journal": False,
        "invented_settlement": False,
        "live_billing": False,
        "why": why,
    }


def _entity_pair_stubs() -> list[dict[str, Any]]:
    return [_pair_stub(*spec) for spec in _PAIR_SPECS]


def _slot_honesty_from_prior() -> dict[str, Any]:
    fin = _fin_ic.honesty_flags()
    ggv = _ggv_ic.honesty_flags()
    return {
        "fin_intercompany_billing": {
            "cap": fin.get("cap") or CAP_FIN,
            "maturity": fin.get("maturity") or "SPECIFIED",
            "maturity_ceiling": fin.get("maturity_ceiling") or "BUILT",
            "live_billing": fin.get("live_billing") is False,
            "invented_invoice": fin.get("invented_invoice") is False,
            "invented_ar_ap": fin.get("invented_ar_ap") is False,
            "payment_executed": fin.get("payment_executed") is False,
            "books_write": fin.get("books_write") is False,
            "ggv_client_mode_proven": fin.get("ggv_client_mode_proven") is False,
            "bound": fin.get("bound") or BOUND,
        },
        "ggv_intercompany_client": {
            "cap": ggv.get("cap") or CAP_GGV,
            "maturity": ggv.get("maturity") or "SPECIFIED",
            "maturity_ceiling": ggv.get("maturity_ceiling") or "BUILT",
            "live_billing": ggv.get("live_billing") is False,
            "client_machinery": ggv.get("client_machinery") is False,
            "invented_invoice": ggv.get("invented_invoice") is False,
            "payment_executed": ggv.get("payment_executed") is False,
            "books_write": ggv.get("books_write") is False,
            "bound": ggv.get("bound") or "beta-ggv-ops-safe",
        },
    }


def fc_shell2_books_preserved() -> dict[str, Any]:
    """Read-only check: BZG/GGV COA templates 200/0; AMG live untouched."""
    bzg = _books.snapshot("ENT-BZG")
    ggv = _books.snapshot("ENT-GGV")
    amg = _books.snapshot("ENT-AMG")
    bzg_accounts = int(bzg.get("accounts") if bzg.get("accounts") is not None else -1)
    bzg_journals = int(bzg.get("journals") if bzg.get("journals") is not None else -1)
    ggv_accounts = int(ggv.get("accounts") if ggv.get("accounts") is not None else -1)
    ggv_journals = int(ggv.get("journals") if ggv.get("journals") is not None else -1)
    amg_accounts = int(amg.get("accounts") if amg.get("accounts") is not None else -1)
    amg_journals = int(amg.get("journals") if amg.get("journals") is not None else -1)
    bzg_ok = (
        bzg.get("exists") is True
        and bzg_accounts == 200
        and bzg_journals == 0
        and bzg.get("shell_kind") == "coa_template_shell"
    )
    ggv_ok = (
        ggv.get("exists") is True
        and ggv_accounts == 200
        and ggv_journals == 0
        and ggv.get("shell_kind") == "coa_template_shell"
    )
    amg_ok = (
        amg.get("exists") is True
        and amg_accounts >= 200
        and amg.get("shell_kind") == "live"
        and amg_journals >= 1
    )
    return {
        "ok": bzg_ok and ggv_ok and amg_ok,
        "bzg": {
            "accounts": bzg.get("accounts"),
            "journals": bzg.get("journals"),
            "shell_kind": bzg.get("shell_kind"),
            "pack": bzg.get("pack"),
        },
        "ggv": {
            "accounts": ggv.get("accounts"),
            "journals": ggv.get("journals"),
            "shell_kind": ggv.get("shell_kind"),
            "pack": ggv.get("pack"),
        },
        "amg": {
            "accounts": amg.get("accounts"),
            "journals": amg.get("journals"),
            "shell_kind": amg.get("shell_kind"),
        },
        "journals_invented": False,
        "books_written": False,
        "why": (
            "FC-SHELL-2 preserved: BZG/GGV coa_template_shell 200 accounts / 0 journals. "
            "AMG live books read-only. This pack does not write journals or invent amounts."
        ),
    }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "fin_intercompany_billing",
            "label": "CAP-FIN-06 Intercompany Billing",
            "href": "/fin-intercompany-billing",
            "kind": "existing",
            "note": "Existing empty framework slots. Not live billing.",
        },
        {
            "id": "ggv_intercompany_client",
            "label": "CAP-GGV-06 Intercompany Client",
            "href": "/ggv-intercompany-client",
            "kind": "existing",
            "note": "Existing GGV client-mode skeleton. Not PROVEN.",
        },
        {
            "id": "ggv_finance",
            "label": "GGV finance desk",
            "href": "/ggv/finance",
            "kind": "existing",
            "note": "GGV books shell (FC-SHELL-2 COA template). Not intercompany settle.",
        },
        {
            "id": "amg_finance",
            "label": "AMG finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "AMG live books preserved. No intercompany journal from this pack.",
        },
        {
            "id": "bzg_finance",
            "label": "BZG finance desk",
            "href": "/bzg/finance",
            "kind": "existing",
            "note": "BZG COA template shell. Journals stay 0.",
        },
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    books = fc_shell2_books_preserved()
    return [
        {
            "id": "structure_only",
            "label": "Structure only",
            "status": "EMPTY",
            "value": None,
            "why": "Invoice/service stubs named. Amounts UNKNOWN. Not live billing.",
        },
        {
            "id": "zero_amounts",
            "label": "Amounts",
            "status": "UNKNOWN",
            "value": None,
            "why": "No fake invoice amounts. amount=null on every stub.",
        },
        {
            "id": "no_journals",
            "label": "Journals / settlements",
            "status": "EMPTY",
            "value": None,
            "why": "No journals invented. No settlements. books_write=false.",
        },
        {
            "id": "fc_shell2",
            "label": "FC-SHELL-2 books",
            "status": "PRESERVED" if books.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": books.get("why"),
        },
        {
            "id": "cap_fin_06",
            "label": "CAP-FIN-06",
            "status": "SPECIFIED",
            "value": None,
            "why": "Ceiling BUILT. Not claimed PROVEN or READY.",
        },
        {
            "id": "cap_ggv_06",
            "label": "CAP-GGV-06",
            "status": "SPECIFIED",
            "value": None,
            "why": "Client-mode not claimed PROVEN. Paired honesty with CAP-FIN-06.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    fin = _fin_ic.honesty_flags()
    ggv = _ggv_ic.honesty_flags()
    books = fc_shell2_books_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_06": CAP_FIN,
        "cap_ggv_06": CAP_GGV,
        "staff_ready": False,
        "human_commissioned": False,
        "live_billing": False,
        "billing_machinery": False,
        "client_machinery": False,
        "invented_amount": False,
        "invented_invoice": False,
        "invented_journal": False,
        "invented_settlement": False,
        "invented_proven": False,
        "invented_ready": False,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "amounts_unknown": True,
        "fc_shell2_preserved": books.get("ok") is True,
        "second_billing_system": False,
        "extends_existing_path": True,
        "cap_fin_06_proven": False,
        "cap_fin_06_ready": False,
        "cap_ggv_06_proven": False,
        "cap_ggv_06_ready": False,
        "cap_fin_06_maturity": fin.get("maturity") or "SPECIFIED",
        "cap_fin_06_ceiling": fin.get("maturity_ceiling") or "BUILT",
        "cap_ggv_06_maturity": ggv.get("maturity") or "SPECIFIED",
        "cap_ggv_06_ceiling": ggv.get("maturity_ceiling") or "BUILT",
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "INTEL-LEARN-1",
    }


def refuse_amount(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "Invoice amounts are not invented. Status stays UNKNOWN/EMPTY.",
        code="amount_refused",
    )


def refuse_journal(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "Journals are not invented. FC-SHELL-2 books stay untouched.",
        code="journal_refused",
    )


def refuse_settlement(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "Settlements are not invented. No payment is executed.",
        code="settlement_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "A payment is not executed on this skeleton.",
        code="payment_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "PROVEN is refused. CAP-FIN-06 and CAP-GGV-06 stay SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinInterco1Error(
        "READY is refused. An empty intercompany skeleton is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinInterco1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {"amount", "amounts", "price", "money", "total", "invoice-amount"}:
            refuse_amount(payload)
        if token in {"journal", "journals", "books", "zayen", "coa"}:
            refuse_journal(payload)
        if token in {"settlement", "settle", "clearing"}:
            refuse_settlement(payload)
        if token in {"payment", "payments", "paid", "bank", "transfer"}:
            refuse_payment(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise FinInterco1Error(
        "External writes are refused. Structure stubs only.",
        code="write_refused",
    )


def all_stubs_empty(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stubs = pack.get("entity_pair_stubs") or []
    if not stubs:
        return False
    return all(
        s.get("amount") is None
        and s.get("journal_id") is None
        and s.get("settlement_id") is None
        and s.get("payment") is None
        and s.get("invented_amount") is False
        and s.get("invented_journal") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        for s in stubs
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    stubs = _entity_pair_stubs()
    books = fc_shell2_books_preserved()
    fin_fw = _fin_ic.build_framework()
    ggv_fw = _ggv_ic.build_framework()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "entities": list(ENTITIES),
        "closes_toward": [CAP_FIN, CAP_GGV],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "live_billing": False,
        "billing_machinery": False,
        "invented_amount": False,
        "invented_journal": False,
        "invented_settlement": False,
        "payment_executed": False,
        "books_write": False,
        "fc_shell2_preserved": books.get("ok") is True,
        "second_billing_system": False,
        "cap_fin_06_proven": False,
        "cap_fin_06_ready": False,
        "cap_ggv_06_proven": False,
        "cap_ggv_06_ready": False,
        "cap_fin_06_maturity": flags["cap_fin_06_maturity"],
        "cap_fin_06_ceiling": flags["cap_fin_06_ceiling"],
        "cap_ggv_06_maturity": flags["cap_ggv_06_maturity"],
        "cap_ggv_06_ceiling": flags["cap_ggv_06_ceiling"],
        "entity_pair_stubs": stubs,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fc_shell2_books": books,
        "prior_frameworks": {
            "fin_intercompany_billing": {
                "schema_id": fin_fw.get("schema_id"),
                "recorded_count": fin_fw.get("recorded_count"),
                "kinds_count": len(fin_fw.get("kinds") or []),
                "money": fin_fw.get("money"),
                "framework_skeleton": fin_fw.get("framework_skeleton"),
            },
            "ggv_intercompany_client": {
                "schema_id": ggv_fw.get("schema_id"),
                "recorded_count": ggv_fw.get("recorded_count"),
                "kinds_count": len(ggv_fw.get("kinds") or []),
                "money": ggv_fw.get("money"),
                "framework_skeleton": ggv_fw.get("framework_skeleton"),
            },
        },
        "prior_path_honesty": _slot_honesty_from_prior(),
        "does_not_claim": [
            "live_intercompany_billing",
            "invoice_amounts",
            "journals",
            "settlements",
            "CAP-FIN-06 PROVEN",
            "CAP-GGV-06 PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "INTEL-LEARN-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "entity_pairs": [s[0] for s in _PAIR_SPECS],
        "entities": list(ENTITIES),
        "status_enum": ["EMPTY", "UNKNOWN"],
        "amount_property": False,
        "journal_property": False,
        "settlement_property": False,
        "payment_property": False,
        "writes_accepted": False,
        "extends": [
            "scripts/core/fin_intercompany_billing.py",
            "scripts/core/ggv_intercompany_client.py",
        ],
        "second_billing_system": False,
        "fc_shell2_preserved": True,
        "why": (
            "Structure stubs for GGV↔AMG/BZG intercompany invoice/service. "
            "Amounts UNKNOWN. Journals EMPTY. Not live billing."
        ),
    }
