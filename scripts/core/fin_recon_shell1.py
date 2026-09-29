#!/usr/bin/env python3
"""FIN-RECON-SHELL-1 — Finance reconciliation shell (bank FILE_IMPORT_ONLY).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-RECON-SHELL-1
(armed 2026-09-30 after BZG-OPS-DESK-1 PASS_VERIFIED). Bank path is
FILE_IMPORT_ONLY per INTG-TRUTH-1 — no live statement feed, no payment write,
no invented last_success timestamps. Recon queue shows EMPTY/UNKNOWN when no
imports exist. Preserves FC-SHELL-2 / FIN-INTERCO-1 / ATRIUM-SOD.
staff_ready=false · human_commissioned=false. Ceiling BUILT only.
Does not auto-chain DASH-LIVE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import fin_interco1 as _fin_interco1
from core import intg_truth_board as _intg_truth

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "FIN-RECON-SHELL-1"
SCHEMA_ID = "wolf.fin-recon-shell-1.v1"
BOUND = "beta-fin-safe"
CAP_FIN = "CAP-FIN-02"  # Bank Statement Ingest & Reconcile (honest target)
CAP_QUEUE_LISTED = "CAP-FIN-08"  # listed in Phase2 queue; profit leakage NOT this shell
INT_BANK = "INT-BANK"
OWNER_PERSON = "PERS-MATT"
WITA = timezone(timedelta(hours=8))

PAGE_PATHS = frozenset(
    {
        "/fin/recon-shell-1",
        "/fin/recon-shell-1/",
        "/fin-recon-shell-1",
        "/fin-recon-shell-1/",
        "/fin-recon-shell-1.html",
        "/dashboards/fin-recon-shell-1.html",
    }
)
API_PATH = "/api/fin/recon-shell-1"

# Named bank-account stubs for Mandiri/BNI/BRI file-import path — structure only.
# No invented imports, balances, or last_success stamps.
_ACCOUNT_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "mandiri_ggv",
        "Mandiri · GGV",
        "GGV",
        "Named Mandiri GGV statement-import stub. No file imported. "
        "Balance UNKNOWN. last_success=null. FILE_IMPORT_ONLY — no bank API.",
    ),
    (
        "bni_amg",
        "BNI · AMG",
        "AMG",
        "Named BNI AMG statement-import stub. No file imported. "
        "Balance UNKNOWN. last_success=null. FILE_IMPORT_ONLY — no bank API.",
    ),
    (
        "bri_bzg",
        "BRI · BZG",
        "BZG",
        "Named BRI BZG statement-import stub. No file imported. "
        "Balance UNKNOWN. last_success=null. FILE_IMPORT_ONLY — no bank API.",
    ),
)

PRESERVED_PACKS = ("FC-SHELL-2", "FIN-INTERCO-1", "ATRIUM-SOD", "INTG-TRUTH-1")


class FinReconShell1Error(ValueError):
    """Fail closed. Does not invent statement feeds, payments, or PROVEN."""

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


def _account_stub(
    stub_id: str,
    label: str,
    entity: str,
    why: str,
) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "entity": entity,
        "kind": "statement_import_stub",
        "status": "EMPTY",
        "display": "EMPTY",
        "import_count": 0,
        "imported_rows": 0,
        "matched_count": None,
        "unmatched_count": None,
        "balance": None,
        "currency": None,
        "last_success": None,
        "last_import_at": None,
        "statement_feed": None,
        "bank_api": False,
        "file_import_only": True,
        "payment": None,
        "invented_import": False,
        "invented_balance": False,
        "invented_last_success": False,
        "why": why,
    }


def _account_stubs() -> list[dict[str, Any]]:
    return [_account_stub(*spec) for spec in _ACCOUNT_SPECS]


def _imported_statement_stubs() -> list[dict[str, Any]]:
    """Recon queue rows from imports. Empty list when no imports exist — honest."""
    return []


def bank_path_honesty() -> dict[str, Any]:
    """INTG-TRUTH-1 bank probe: FILE_IMPORT_ONLY, last_success null."""
    board = _intg_truth.build_board(persist_audit=False)
    connectors = board.get("connectors") or []
    bank = next(
        (
            c
            for c in connectors
            if c.get("integration_id") in ("INT-BANK-WOLF", "INT-BANK", "CAP-INTG-04")
            or "bank" in str(c.get("integration_id") or "").lower()
        ),
        None,
    )
    probe = (bank or {}).get("probe_status") or "FILE_IMPORT_ONLY"
    last_success = (bank or {}).get("last_success")
    return {
        "ok": probe == "FILE_IMPORT_ONLY" and last_success is None,
        "integration_id": (bank or {}).get("integration_id") or INT_BANK,
        "probe_status": probe,
        "last_success": last_success,
        "invented_last_success": False,
        "bank_api": False,
        "payment_write": False,
        "file_import_only": True,
        "why": (
            "INTG-TRUTH-1: bank path FILE_IMPORT_ONLY. "
            "No live statement feed. last_success stays null until a real file import lands."
        ),
    }


def fc_shell2_books_preserved() -> dict[str, Any]:
    """Read-only: BZG/GGV COA templates 200/0; AMG live untouched."""
    return _fin_interco1.fc_shell2_books_preserved()


def fin_interco1_preserved() -> dict[str, Any]:
    """Read-only: FIN-INTERCO-1 stubs still EMPTY; no second billing invent."""
    try:
        slice_ = _fin_interco1.build_slice()
        empty = _fin_interco1.all_stubs_empty(slice_)
        return {
            "ok": empty and slice_.get("ok") is True and slice_.get("invented_amount") is False,
            "stubs_empty": empty,
            "stub_count": len(slice_.get("entity_pair_stubs") or []),
            "invented_amount": slice_.get("invented_amount"),
            "live_billing": slice_.get("live_billing"),
            "why": (
                "FIN-INTERCO-1 preserved: entity-pair stubs EMPTY, amounts UNKNOWN. "
                "This pack does not invent intercompany billing."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "stubs_empty": False,
            "error": type(exc).__name__,
            "why": "FIN-INTERCO-1 check failed — pack must not break interco.",
        }


def atrium_sod_preserved() -> dict[str, Any]:
    """Read-only: commissioning journal JRN-ATRIUMSOD1B-COMM1 still POSTED if books present."""
    candidates = [
        Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite"),
        BETA_ROOT / "state" / "atrium-books" / "amg.sqlite",
    ]
    db_path = next((p for p in candidates if p.is_file()), None)
    if db_path is None:
        return {
            "ok": True,
            "checked": False,
            "why": (
                "ATRIUM-SOD books file not on this path — pack did not write SoD state. "
                "Preservation treated as untouched (no atrium sqlite found to mutate)."
            ),
            "books_written": False,
        }
    try:
        import sqlite3

        con = sqlite3.connect(str(db_path))
        try:
            row = con.execute(
                "SELECT status, preparer_person_id, wolf_created FROM journal_headers "
                "WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
            ).fetchone()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "checked": True,
            "error": type(exc).__name__,
            "books_written": False,
            "why": "ATRIUM-SOD read failed.",
        }
    if row is None:
        return {
            "ok": True,
            "checked": True,
            "journal_found": False,
            "books_written": False,
            "path": str(db_path),
            "why": (
                "JRN-ATRIUMSOD1B-COMM1 not in this sqlite — pack did not invent or clear it. "
                "No SoD mutate."
            ),
        }
    status, preparer, wolf_created = row[0], row[1], row[2]
    ok = status == "POSTED" and preparer == "PERS-ZENITALFATHAN"
    return {
        "ok": ok,
        "checked": True,
        "journal_found": True,
        "status": status,
        "preparer_person_id": preparer,
        "wolf_created": wolf_created,
        "books_written": False,
        "path": str(db_path),
        "why": (
            "ATRIUM-SOD preserved: JRN-ATRIUMSOD1B-COMM1 POSTED by PERS-ZENITALFATHAN. "
            "This pack does not approve/post/pay or change SoD."
            if ok
            else "ATRIUM-SOD journal state unexpected — investigate; pack did not write."
        ),
    }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "integrations_status",
            "label": "Integrations honesty (INTG-TRUTH-1)",
            "href": "/ops/integrations-status",
            "kind": "existing",
            "note": "INT-BANK FILE_IMPORT_ONLY · last_success null.",
        },
        {
            "id": "fin_interco_1",
            "label": "FIN Interco-1",
            "href": "/fin/interco-1",
            "kind": "existing",
            "note": "Preserved structure stubs. Not bank recon.",
        },
        {
            "id": "amg_finance",
            "label": "AMG finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "AMG live books + ATRIUM-SOD. No payment from this shell.",
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
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    return [
        {
            "id": "recon_queue",
            "label": "Recon queue",
            "status": "EMPTY",
            "value": 0,
            "why": "No statement imports on disk. Empty is honest — not a live recon loop.",
        },
        {
            "id": "bank_path",
            "label": "Bank path",
            "status": "FILE_IMPORT_ONLY",
            "value": None,
            "why": bank.get("why"),
        },
        {
            "id": "last_success",
            "label": "last_success",
            "status": "UNKNOWN",
            "value": None,
            "why": "last_success=null. Never invent a feed success timestamp.",
        },
        {
            "id": "balances",
            "label": "Balances / matches",
            "status": "UNKNOWN",
            "value": None,
            "why": "No imported rows → balance/matched/unmatched UNKNOWN (not zero).",
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
            "id": "cap_fin_02",
            "label": "CAP-FIN-02",
            "status": "SPECIFIED",
            "value": None,
            "why": "Bank ingest & reconcile shell only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    bank = bank_path_honesty()
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_02": CAP_FIN,
        "cap_fin_08_queue_listed": CAP_QUEUE_LISTED,
        "int_bank": INT_BANK,
        "staff_ready": False,
        "human_commissioned": False,
        "live_recon": False,
        "recon_machinery": False,
        "invented_import": False,
        "invented_balance": False,
        "invented_last_success": False,
        "invented_statement_feed": False,
        "invented_proven": False,
        "invented_ready": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "file_import_only": True,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "empty_honest": True,
        "balances_unknown": True,
        "last_success_null": bank.get("last_success") is None,
        "fc_shell2_preserved": books.get("ok") is True,
        "fin_interco1_preserved": interco.get("ok") is True,
        "atrium_sod_preserved": sod.get("ok") is True,
        "second_recon_system": False,
        "extends_intg_truth": True,
        "cap_fin_02_proven": False,
        "cap_fin_02_ready": False,
        "cap_fin_08_proven": False,
        "cap_fin_08_closed_by_this_pack": False,
        "cap_fin_02_maturity": "SPECIFIED",
        "cap_fin_02_ceiling": "BUILT",
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "DASH-LIVE-1",
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "A payment is not executed on this recon shell.",
        code="payment_refused",
    )


def refuse_bank_write(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "Bank writes are refused. FILE_IMPORT_ONLY — no bank API mutate.",
        code="bank_write_refused",
    )


def refuse_invented_feed(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "Statement feeds and last_success timestamps are not invented.",
        code="feed_refused",
    )


def refuse_balance(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "Balances are UNKNOWN until a real file import lands. Not invented.",
        code="balance_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "PROVEN is refused. CAP-FIN-02 stays SPECIFIED. Empty recon is not proven.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinReconShell1Error(
        "READY is refused. An empty recon shell is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinReconShell1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {"payment", "payments", "paid", "pay", "transfer", "payout"}:
            refuse_payment(payload)
        if token in {"bank", "bank-write", "bank-api", "wire"}:
            refuse_bank_write(payload)
        if token in {
            "feed",
            "statement-feed",
            "last-success",
            "last_success",
            "live-feed",
        }:
            refuse_invented_feed(payload)
        if token in {"balance", "balances", "amount", "amounts", "money"}:
            refuse_balance(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready"}:
            refuse_ready(payload)
    raise FinReconShell1Error(
        "External writes are refused. Recon queue is read-only shell.",
        code="write_refused",
    )


def queue_is_empty(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    queue = pack.get("recon_queue") or []
    imports = int(pack.get("import_count") or 0)
    return len(queue) == 0 and imports == 0


def all_account_stubs_empty(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    stubs = pack.get("account_stubs") or []
    if not stubs:
        return False
    return all(
        s.get("import_count") == 0
        and s.get("balance") is None
        and s.get("last_success") is None
        and s.get("payment") is None
        and s.get("invented_import") is False
        and s.get("invented_last_success") is False
        and s.get("status") in ("EMPTY", "UNKNOWN")
        and s.get("file_import_only") is True
        for s in stubs
    )


def build_slice() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    flags = honesty_flags()
    accounts = _account_stubs()
    queue = _imported_statement_stubs()
    bank = bank_path_honesty()
    books = fc_shell2_books_preserved()
    interco = fin_interco1_preserved()
    sod = atrium_sod_preserved()
    import_count = sum(int(a.get("import_count") or 0) for a in accounts) + len(queue)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_FIN, INT_BANK],
        "queue_also_listed": [CAP_QUEUE_LISTED],
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "live_recon": False,
        "recon_machinery": False,
        "import_count": import_count,
        "queue_empty": import_count == 0 and len(queue) == 0,
        "invented_import": False,
        "invented_balance": False,
        "invented_last_success": False,
        "invented_statement_feed": False,
        "payment_executed": False,
        "payment_write": False,
        "bank_write": False,
        "bank_api": False,
        "file_import_only": True,
        "books_write": False,
        "last_success": None,
        "fc_shell2_preserved": books.get("ok") is True,
        "fin_interco1_preserved": interco.get("ok") is True,
        "atrium_sod_preserved": sod.get("ok") is True,
        "cap_fin_02_proven": False,
        "cap_fin_02_ready": False,
        "cap_fin_08_proven": False,
        "cap_fin_08_closed_by_this_pack": False,
        "cap_fin_02_maturity": flags["cap_fin_02_maturity"],
        "cap_fin_02_ceiling": flags["cap_fin_02_ceiling"],
        "bank_path": bank,
        "account_stubs": accounts,
        "recon_queue": queue,
        "honesty_tiles": _honesty_tiles(),
        "desk_links": _desk_links(),
        "fc_shell2_books": books,
        "fin_interco1": interco,
        "atrium_sod": sod,
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_bank_feed",
            "last_success_timestamp",
            "imported_statement_rows",
            "balances",
            "payment_write",
            "CAP-FIN-02 PROVEN",
            "CAP-FIN-08 closed",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "DASH-LIVE-1",
    }


def public_payload() -> dict[str, Any]:
    return build_slice()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "account_stubs": [s[0] for s in _ACCOUNT_SPECS],
        "status_enum": ["EMPTY", "UNKNOWN", "FILE_IMPORT_ONLY"],
        "last_success_property": False,
        "balance_property": False,
        "payment_property": False,
        "bank_api_property": False,
        "writes_accepted": False,
        "file_import_only": True,
        "extends": [
            "scripts/core/intg_truth_board.py",
            "scripts/core/fin_interco1.py",
        ],
        "preserved": list(PRESERVED_PACKS),
        "second_recon_system": False,
        "why": (
            "Recon queue shell for bank statement file imports. "
            "Empty when no imports. last_success null. No payment write."
        ),
    }
