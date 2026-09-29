#!/usr/bin/env python3
"""FIN-CASH-TRUTH-1 — Cash / bank truth desk deepen (file-import only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-CASH-TRUTH-1
(armed 2026-09-30 after BACKUP-HEALTH-1 PASS_VERIFIED). Deepens cash/bank
honesty over FIN-RECON-SHELL-1. FILE_IMPORT_ONLY — no live bank scrape, no
invented balances. Empty/UNKNOWN when no import. Preserves FIN-RECON-SHELL-1
and FC-SHELL-2. staff_ready=false · human_commissioned=false. Ceiling BUILT.
Does not auto-chain BZG-LABOR-COST-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core import fin_recon_shell1 as _recon

BETA_ROOT = __import__("pathlib").Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "FIN-CASH-TRUTH-1"
SCHEMA_ID = "wolf.fin-cash-truth-1.v1"
BOUND = "beta-fin-safe"
CAP_FIN_CASH = "CAP-FIN cash"
CAP_FIN_02 = "CAP-FIN-02"
INT_BANK = "INT-BANK"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/fin/cash-truth-1",
        "/fin/cash-truth-1/",
        "/fin/cash-truth",
        "/fin/cash-truth/",
        "/fin-cash-truth-1",
        "/fin-cash-truth-1/",
        "/fin-cash-truth",
        "/fin-cash-truth/",
        "/fin-cash-truth-1.html",
        "/dashboards/fin-cash-truth-1.html",
    }
)
API_PATH = "/api/fin/cash-truth-1"

# Entity cash-position stubs — structure only. Balance stays null/UNKNOWN
# until a real statement file import lands on FIN-RECON-SHELL-1.
_CASH_POSITION_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "cash_bzg",
        "Cash position · BZG",
        "BZG",
        "BZG cash/bank position stub. No file import. Balance UNKNOWN. "
        "FILE_IMPORT_ONLY over FIN-RECON-SHELL-1 — never invent.",
    ),
    (
        "cash_ggv",
        "Cash position · GGV",
        "GGV",
        "GGV cash/bank position stub. No file import. Balance UNKNOWN. "
        "FILE_IMPORT_ONLY over FIN-RECON-SHELL-1 — never invent.",
    ),
    (
        "cash_amg",
        "Cash position · AMG",
        "AMG",
        "AMG cash/bank position stub. No file import. Balance UNKNOWN. "
        "FILE_IMPORT_ONLY over FIN-RECON-SHELL-1 — never invent.",
    ),
)

PRESERVED_PACKS = ("FIN-RECON-SHELL-1", "FC-SHELL-2")


class FinCashTruth1Error(ValueError):
    """Fail closed. Does not invent balances, scrapes, or PROVEN."""

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


def _cash_position_stub(
    stub_id: str,
    label: str,
    entity: str,
    why: str,
) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "entity": entity,
        "kind": "cash_position_stub",
        "status": "UNKNOWN",
        "display": "UNKNOWN",
        "balance": None,
        "currency": None,
        "cash_on_hand": None,
        "bank_available": None,
        "import_count": 0,
        "last_import_at": None,
        "last_success": None,
        "bank_api": False,
        "live_scrape": False,
        "file_import_only": True,
        "invented_balance": False,
        "invented_scrape": False,
        "why": why,
    }


def _cash_position_stubs() -> list[dict[str, Any]]:
    return [_cash_position_stub(*spec) for spec in _CASH_POSITION_SPECS]


def fin_recon_shell1_preserved() -> dict[str, Any]:
    """Read-only: FIN-RECON-SHELL-1 still EMPTY/FILE_IMPORT_ONLY."""
    try:
        slice_ = _recon.build_slice()
        empty = _recon.queue_is_empty(slice_) and _recon.all_account_stubs_empty(slice_)
        return {
            "ok": (
                empty
                and slice_.get("ok") is True
                and slice_.get("file_import_only") is True
                and slice_.get("last_success") is None
                and slice_.get("invented_balance") is False
            ),
            "queue_empty": empty,
            "import_count": slice_.get("import_count"),
            "file_import_only": slice_.get("file_import_only"),
            "last_success": slice_.get("last_success"),
            "invented_balance": slice_.get("invented_balance"),
            "why": (
                "FIN-RECON-SHELL-1 preserved: recon queue EMPTY, "
                "FILE_IMPORT_ONLY, last_success=null, no invented balances. "
                "This pack deepens cash honesty over that shell — does not replace it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-RECON-SHELL-1 check failed — pack must not break recon shell.",
        }


def fc_shell2_books_preserved() -> dict[str, Any]:
    """Read-only: BZG/GGV COA templates; AMG live untouched."""
    return _recon.fc_shell2_books_preserved()


def bank_path_honesty() -> dict[str, Any]:
    """Reuse INTG-TRUTH-1 bank probe via FIN-RECON-SHELL-1."""
    return _recon.bank_path_honesty()


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "fin_recon_shell_1",
            "label": "FIN Recon Shell-1",
            "href": "/fin/recon-shell-1",
            "kind": "existing",
            "note": "Upstream FILE_IMPORT_ONLY recon queue. Preserved.",
        },
        {
            "id": "integrations_status",
            "label": "Integrations honesty (INTG-TRUTH-1)",
            "href": "/ops/integrations-status",
            "kind": "existing",
            "note": "INT-BANK FILE_IMPORT_ONLY · last_success null.",
        },
        {
            "id": "amg_finance",
            "label": "AMG finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "AMG live books. No cash invent from this desk.",
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
    bank = bank_path_honesty()
    recon = fin_recon_shell1_preserved()
    books = fc_shell2_books_preserved()
    return [
        {
            "id": "cash_positions",
            "label": "Cash positions",
            "status": "UNKNOWN",
            "value": None,
            "why": "No statement imports → cash/bank balances UNKNOWN (not zero).",
        },
        {
            "id": "bank_path",
            "label": "Bank path",
            "status": "FILE_IMPORT_ONLY",
            "value": None,
            "why": bank.get("why"),
        },
        {
            "id": "invented_balance",
            "label": "Invented balances",
            "status": "REFUSED",
            "value": False,
            "why": "Balance invent / live scrape writes are refused. Empty is honest.",
        },
        {
            "id": "fin_recon_shell1",
            "label": "FIN-RECON-SHELL-1",
            "status": "PRESERVED" if recon.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": recon.get("why"),
        },
        {
            "id": "fc_shell2",
            "label": "FC-SHELL-2 books",
            "status": "PRESERVED" if books.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": books.get("why"),
        },
        {
            "id": "cap_fin_cash",
            "label": "CAP-FIN cash",
            "status": "SPECIFIED",
            "value": None,
            "why": "Cash/bank truth desk deepen only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    bank = bank_path_honesty()
    recon = fin_recon_shell1_preserved()
    books = fc_shell2_books_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_cash": CAP_FIN_CASH,
        "cap_fin_02": CAP_FIN_02,
        "int_bank": INT_BANK,
        "staff_ready": False,
        "human_commissioned": False,
        "live_cash": False,
        "live_scrape": False,
        "invented_balance": False,
        "invented_scrape": False,
        "invented_cash_position": False,
        "invented_proven": False,
        "invented_ready": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "file_import_only": True,
        "books_write": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "balances_unknown": True,
        "last_success_null": bank.get("last_success") is None,
        "fin_recon_shell1_preserved": recon.get("ok") is True,
        "fc_shell2_preserved": books.get("ok") is True,
        "extends_fin_recon_shell1": True,
        "second_cash_system": False,
        "cap_fin_cash_proven": False,
        "cap_fin_cash_ready": False,
        "cap_fin_02_proven": False,
        "cap_fin_cash_maturity": "SPECIFIED",
        "cap_fin_cash_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "BZG-LABOR-COST-1",
    }


def refuse_invent_balance(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "Cash/bank balances are UNKNOWN until a real file import lands. Not invented.",
        code="invent_balance_refused",
    )


def refuse_live_scrape(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "Live bank scrape invent is refused. FILE_IMPORT_ONLY.",
        code="scrape_refused",
    )


def refuse_bank_write(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "Bank writes are refused. FILE_IMPORT_ONLY — no bank API mutate.",
        code="bank_write_refused",
    )


def refuse_payment(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "A payment is not executed on this cash truth desk.",
        code="payment_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "PROVEN is refused. CAP-FIN cash stays SPECIFIED. Empty cash is not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinCashTruth1Error(
        "READY is refused. An empty cash truth desk is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinCashTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "balance",
            "balances",
            "amount",
            "amounts",
            "money",
            "cash",
            "cash-on-hand",
            "cash_on_hand",
            "bank-available",
            "bank_available",
            "invent-balance",
            "invent_balance",
            "fake-balance",
            "fake_balance",
        }:
            refuse_invent_balance(payload)
        if token in {
            "scrape",
            "live-scrape",
            "live_scrape",
            "bank-scrape",
            "bank_scrape",
        }:
            refuse_live_scrape(payload)
        if token in {"bank", "bank-write", "bank-api", "wire"}:
            refuse_bank_write(payload)
        if token in {"payment", "payments", "paid", "pay", "transfer", "payout"}:
            refuse_payment(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise FinCashTruth1Error(
        "External writes are refused. Cash truth desk is read-only deepen.",
        code="write_refused",
    )


def all_cash_positions_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stubs = pack.get("cash_positions") or []
    if not stubs:
        return False
    return all(
        s.get("balance") is None
        and s.get("cash_on_hand") is None
        and s.get("bank_available") is None
        and s.get("import_count") == 0
        and s.get("last_success") is None
        and s.get("invented_balance") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        and s.get("file_import_only") is True
        for s in stubs
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    positions = _cash_position_stubs()
    bank = bank_path_honesty()
    recon = fin_recon_shell1_preserved()
    books = fc_shell2_books_preserved()
    recon_slice = _recon.build_slice()
    account_stubs = recon_slice.get("account_stubs") or []
    import_count = sum(int(p.get("import_count") or 0) for p in positions)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_FIN_CASH, CAP_FIN_02, INT_BANK],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "live_cash": False,
        "live_scrape": False,
        "import_count": import_count,
        "positions_unknown": import_count == 0,
        "invented_balance": False,
        "invented_scrape": False,
        "invented_cash_position": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "file_import_only": True,
        "books_write": False,
        "last_success": None,
        "fin_recon_shell1_preserved": recon.get("ok") is True,
        "fc_shell2_preserved": books.get("ok") is True,
        "cap_fin_cash_proven": False,
        "cap_fin_cash_ready": False,
        "cap_fin_02_proven": False,
        "cap_fin_cash_maturity": flags["cap_fin_cash_maturity"],
        "cap_fin_cash_ceiling": flags["cap_fin_cash_ceiling"],
        "bank_path": bank,
        "cash_positions": positions,
        "account_stubs": account_stubs,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fin_recon_shell1": recon,
        "fc_shell2_books": books,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_bank_scrape",
            "cash_balances",
            "bank_available",
            "payment_write",
            "CAP-FIN cash PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "BZG-LABOR-COST-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "cash_positions": [s[0] for s in _CASH_POSITION_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "FILE_IMPORT_ONLY", "REFUSED"],
        "balance_property": False,
        "scrape_property": False,
        "bank_api_property": False,
        "writes_accepted": False,
        "file_import_only": True,
        "extends": [
            "scripts/core/fin_recon_shell1.py",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_cash_system": False,
        "why": (
            "Cash/bank truth desk deepen over FIN-RECON-SHELL-1. "
            "UNKNOWN when no import. No invented balances. No live scrape."
        ),
    }
