#!/usr/bin/env python3
"""FIN-TAX-SHELL-1 — Tax calendar shell honesty (no fake filings).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-TAX-SHELL-1
(armed 2026-09-30 after SOP-LESSON-LIVE-1 PASS_VERIFIED). Calendar stubs stay
UNKNOWN until facts — no invented due amounts or fake filings. Preserves
FC-SHELL-2. staff_ready=false · human_commissioned=false. Ceiling BUILT.
Does not auto-chain BZG-INVENTORY-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core import fin_recon_shell1 as _recon

BETA_ROOT = __import__("pathlib").Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "FIN-TAX-SHELL-1"
SCHEMA_ID = "wolf.fin-tax-shell-1.v1"
BOUND = "beta-fin-safe"
CAP_FIN_TAX = "CAP-FIN tax"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/fin/tax-shell-1",
        "/fin/tax-shell-1/",
        "/fin/tax-shell",
        "/fin/tax-shell/",
        "/fin-tax-shell-1",
        "/fin-tax-shell-1/",
        "/fin-tax-shell",
        "/fin-tax-shell/",
        "/fin-tax-shell-1.html",
        "/dashboards/fin-tax-shell-1.html",
    }
)
API_PATH = "/api/fin/tax-shell-1"

# Entity tax-calendar stubs — structure only. Due amounts stay null/UNKNOWN
# until a real filing fact lands. Never invent dues or filed stamps.
_CALENDAR_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "tax_cal_bzg",
        "Tax calendar · BZG",
        "BZG",
        "BZG tax calendar stub. No filing facts. Dues UNKNOWN. "
        "Never invent amounts or filed timestamps.",
    ),
    (
        "tax_cal_ggv",
        "Tax calendar · GGV",
        "GGV",
        "GGV tax calendar stub. No filing facts. Dues UNKNOWN. "
        "Never invent amounts or filed timestamps.",
    ),
    (
        "tax_cal_amg",
        "Tax calendar · AMG",
        "AMG",
        "AMG tax calendar stub. No filing facts. Dues UNKNOWN. "
        "Never invent amounts or filed timestamps.",
    ),
)

# Named obligation categories (calendar types only — not computed dues).
_OBLIGATION_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "ppn_monthly",
        "PPN (VAT) monthly return",
        "Named PPN obligation slot. due_amount=null · due_on=null · filed=false. "
        "UNKNOWN until a real return fact exists.",
    ),
    (
        "pph21_monthly",
        "PPh 21 monthly withholding",
        "Named PPh 21 obligation slot. due_amount=null · due_on=null · filed=false. "
        "UNKNOWN until payroll/tax facts exist.",
    ),
    (
        "pph23_withholding",
        "PPh 23 withholding",
        "Named PPh 23 obligation slot. due_amount=null · due_on=null · filed=false. "
        "UNKNOWN until withholding facts exist.",
    ),
    (
        "spt_tahunan_badan",
        "SPT Tahunan Badan",
        "Named annual corporate return slot. due_amount=null · due_on=null · filed=false. "
        "UNKNOWN until books/facts exist. Not a fake filing.",
    ),
)

PRESERVED_PACKS = ("FC-SHELL-2",)


class FinTaxShell1Error(ValueError):
    """Fail closed. Does not invent filings, dues, or PROVEN."""

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


def _calendar_stub(stub_id: str, label: str, entity: str, why: str) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "entity": entity,
        "kind": "tax_calendar_stub",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "due_amount": None,
        "currency": None,
        "due_on": None,
        "filed": False,
        "filed_at": None,
        "filing_count": 0,
        "last_filed_at": None,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "why": why,
    }


def _obligation_stub(stub_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "kind": "tax_obligation_stub",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "due_amount": None,
        "currency": None,
        "due_on": None,
        "filed": False,
        "filed_at": None,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "why": why,
    }


def _calendar_stubs() -> list[dict[str, Any]]:
    return [_calendar_stub(*spec) for spec in _CALENDAR_SPECS]


def _obligation_stubs() -> list[dict[str, Any]]:
    return [_obligation_stub(*spec) for spec in _OBLIGATION_SPECS]


def fc_shell2_books_preserved() -> dict[str, Any]:
    """Read-only: BZG/GGV COA templates; AMG live untouched."""
    return _recon.fc_shell2_books_preserved()


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "fin_cash_truth_1",
            "label": "FIN Cash Truth-1",
            "href": "/fin/cash-truth-1",
            "kind": "existing",
            "note": "Cash/bank UNKNOWN · FILE_IMPORT_ONLY. Adjacent honesty desk.",
        },
        {
            "id": "fin_recon_shell_1",
            "label": "FIN Recon Shell-1",
            "href": "/fin/recon-shell-1",
            "kind": "existing",
            "note": "FILE_IMPORT_ONLY recon queue. Preserved upstream.",
        },
        {
            "id": "amg_finance",
            "label": "AMG finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "AMG live books. No tax invent from this shell.",
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
    ]


def _honesty_tiles() -> list[dict[str, Any]]:
    books = fc_shell2_books_preserved()
    return [
        {
            "id": "tax_calendar",
            "label": "Tax calendar",
            "status": "UNKNOWN",
            "value": None,
            "why": "No filing facts → dues UNKNOWN (not zero). No fake filings.",
        },
        {
            "id": "invented_filing",
            "label": "Invented filings",
            "status": "REFUSED",
            "value": False,
            "why": "Invent-filing / fake-due writes are refused. Empty is honest.",
        },
        {
            "id": "invented_amount",
            "label": "Invented tax amounts",
            "status": "REFUSED",
            "value": False,
            "why": "due_amount stays null until facts. Never invent a tax bill.",
        },
        {
            "id": "fc_shell2",
            "label": "FC-SHELL-2 books",
            "status": "PRESERVED" if books.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": books.get("why"),
        },
        {
            "id": "cap_fin_tax",
            "label": "CAP-FIN tax",
            "status": "SPECIFIED",
            "value": None,
            "why": "Tax calendar shell only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    books = fc_shell2_books_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_tax": CAP_FIN_TAX,
        "staff_ready": False,
        "human_commissioned": False,
        "live_tax": False,
        "live_filing": False,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "fake_filings": False,
        "fake_tax_amounts": False,
        "invented_proven": False,
        "invented_ready": False,
        "tax_write": False,
        "filing_write": False,
        "books_write": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "dues_unknown": True,
        "fc_shell2_preserved": books.get("ok") is True,
        "cap_fin_tax_proven": False,
        "cap_fin_tax_ready": False,
        "cap_fin_tax_maturity": "SPECIFIED",
        "cap_fin_tax_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "BZG-INVENTORY-TRUTH-1",
    }


def refuse_invent_filing(_body: dict | None = None) -> None:
    raise FinTaxShell1Error(
        "Filings stay unfiled until a real fact lands. Not invented.",
        code="invent_filing_refused",
    )


def refuse_invent_amount(_body: dict | None = None) -> None:
    raise FinTaxShell1Error(
        "Tax due amounts are UNKNOWN until facts. Not invented.",
        code="invent_amount_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinTaxShell1Error(
        "PROVEN is refused. CAP-FIN tax stays SPECIFIED. Empty calendar is not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinTaxShell1Error(
        "READY is refused. An empty tax calendar shell is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinTaxShell1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "filing",
            "filings",
            "file",
            "filed",
            "filed-at",
            "invent-filing",
            "fake-filing",
            "fake-filings",
            "spt",
            "submit",
        }:
            refuse_invent_filing(payload)
        if token in {
            "amount",
            "amounts",
            "due",
            "dues",
            "due-amount",
            "due_amount",
            "tax",
            "tax-amount",
            "invent-amount",
            "fake-amount",
            "fake-tax",
        }:
            refuse_invent_amount(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise FinTaxShell1Error(
        "External writes are refused. Tax calendar shell is read-only.",
        code="write_refused",
    )


def all_calendars_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stubs = pack.get("calendars") or []
    if not stubs:
        return False
    return all(
        s.get("due_amount") is None
        and s.get("due_on") is None
        and s.get("filed") is False
        and s.get("filed_at") is None
        and s.get("filing_count") == 0
        and s.get("invented_filing") is False
        and s.get("invented_amount") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        for s in stubs
    )


def all_obligations_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stubs = pack.get("obligations") or []
    if not stubs:
        return False
    return all(
        s.get("due_amount") is None
        and s.get("due_on") is None
        and s.get("filed") is False
        and s.get("invented_filing") is False
        and s.get("invented_amount") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        for s in stubs
    )


def no_fake_filings(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    return (
        pack.get("invented_filing") is False
        and pack.get("fake_filings") is False
        and pack.get("invented_amount") is False
        and all_calendars_unknown(pack)
        and all_obligations_unknown(pack)
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    calendars = _calendar_stubs()
    obligations = _obligation_stubs()
    books = fc_shell2_books_preserved()
    filing_count = sum(int(c.get("filing_count") or 0) for c in calendars)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_FIN_TAX],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "live_tax": False,
        "live_filing": False,
        "filing_count": filing_count,
        "dues_unknown": filing_count == 0,
        "calendars_unknown": filing_count == 0,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "fake_filings": False,
        "fake_tax_amounts": False,
        "tax_write": False,
        "filing_write": False,
        "books_write": False,
        "fc_shell2_preserved": books.get("ok") is True,
        "cap_fin_tax_proven": False,
        "cap_fin_tax_ready": False,
        "cap_fin_tax_maturity": flags["cap_fin_tax_maturity"],
        "cap_fin_tax_ceiling": flags["cap_fin_tax_ceiling"],
        "calendars": calendars,
        "obligations": obligations,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fc_shell2_books": books,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_filings",
            "tax_due_amounts",
            "filed_stamps",
            "CAP-FIN tax PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "BZG-INVENTORY-TRUTH-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "calendars": [s[0] for s in _CALENDAR_SPECS],
        "obligations": [s[0] for s in _OBLIGATION_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "REFUSED"],
        "due_amount_property": False,
        "filing_property": False,
        "writes_accepted": False,
        "preserved": list(PRESERVED_PACKS),
        "why": (
            "Tax calendar shell. UNKNOWN until facts. "
            "No invented dues. No fake filings."
        ),
    }
