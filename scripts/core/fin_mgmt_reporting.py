#!/usr/bin/env python3
"""CAP-FIN-05 Management Reporting prove skeleton v1 (Beta only).

Decision served: 2026-09-20 PICK — CAP-FIN-05 Management Reporting prove
framework skeleton on Beta only
(docs/deliveries/GROK-PLAN-FIN-MGMT-REPORTING-V1-2026-09-20.md).
Owner order KEEP BUILDING WITHOUT MATT. Lane fin-mgmt-reporting-v1 on
mission owner-autonomous-20260920-w12 after wave-11 hr-retention-signals-v1
DONE (e449b4e / e449b4e4d130467797a3c3eff752a1401cf01182).
CR-20b4dd71cc0fcc88 stays OPEN. Bound beta-fin-safe.

Names the pnl, balance_sheet, cash_flow, checklist, and notes slots and
leaves every slot empty. An empty framework is not a live
management-reporting pack and not proof of P&L/BS/CF machinery.
read_management_report reuses that framework and the accounting-core
books read. While that read leaves the books source unopened, the report
state is UNAVAILABLE. UNAVAILABLE is not a P&L, a balance sheet, a cash
figure, or zero. This module does not invent P&L, BS, or CF numbers. It
does not execute money move, payment, or bank write. It does not
guest-blast, staff-blast, or public-post. It does not write Production,
Alchemist, Zayen books, Cloudflare, Access, the Model C ledger, or the
completion row. CAP-FIN-05 stays SPECIFIED. The ceiling label is BUILT.
PROVEN and READY are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "fin_mgmt_reporting.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-20b4dd71cc0fcc88"
CAP_ID = "CAP-FIN-05"
SCHEMA_ID = "wolf.cap-fin-05.mgmt-reporting.v1"
BOUND = "beta-fin-safe"

_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "pnl",
        "P&L",
        "Named pnl slot. Empty is not a P&L and not a live management-reporting pack.",
    ),
    (
        "balance_sheet",
        "Balance sheet",
        "Named balance_sheet slot. Empty is not a balance sheet and not proof of P&L/BS/CF machinery.",
    ),
    (
        "cash_flow",
        "Cash flow",
        "Named cash_flow slot. Empty is not a cash-flow statement and not a live management-reporting pack.",
    ),
    (
        "checklist",
        "Checklist",
        "Named checklist slot. Empty is not a checklist and not proof of P&L/BS/CF machinery.",
    ),
    (
        "notes",
        "Notes",
        "Named notes slot. Empty is not a management-reporting note and not a live management-reporting pack.",
    ),
)


def _empty_slot(kind: str, label: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "slot": "empty",
        "evidence": None,
        "pnl": None,
        "pnl_number": None,
        "balance_sheet": None,
        "balance_sheet_number": None,
        "cash_flow": None,
        "cash_flow_number": None,
        "checklist": None,
        "current": False,
        "live_pnl": False,
        "live_balance_sheet": False,
        "live_cash_flow": False,
        "live_management_reporting": False,
        "pnl_bs_cf_machinery": False,
        "guest_blast": False,
        "staff_blast": False,
        "public_post": False,
        "payment": None,
        "payment_executed": False,
        "why": why,
    }


EVIDENCE_KINDS: tuple[dict[str, Any], ...] = tuple(
    _empty_slot(*row) for row in _SLOT_SPECS
)
KIND_IDS = tuple(row["kind"] for row in EVIDENCE_KINDS)
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live management-reporting pack.",
    "An empty framework is not proof of P&L/BS/CF machinery.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "P&L, BS, and CF numbers are not invented.",
    "No guest blast.",
    "No staff blast.",
    "No public post.",
    "No payment is executed.",
    "No bank write.",
    "No money move.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-FIN-05 stays SPECIFIED.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "fin_mgmt_reporting_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_management_reporting": False,
    "empty_is_pnl_bs_cf": False,
    "empty_is_ready": False,
    "proved": False,
    "live_pnl": False,
    "live_balance_sheet": False,
    "live_cash_flow": False,
    "live_management_reporting": False,
    "pnl_bs_cf_machinery": False,
    "current": False,
    "pnl": None,
    "pnl_number": None,
    "balance_sheet": None,
    "balance_sheet_number": None,
    "cash_flow": None,
    "cash_flow_number": None,
    "checklist": None,
    "guest_blast": False,
    "staff_blast": False,
    "public_post": False,
    "payment": None,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "books_write": False,
    "zayen_write": False,
    "alchemist_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "wolf_system_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_pnl": False,
    "invented_balance_sheet": False,
    "invented_cash_flow": False,
    "ledger_write": False,
}


class FinMgmtReportingError(ValueError):
    """Fail closed. Does not invent P&L/BS/CF numbers, money move, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "alchemist" in low:
        raise FinMgmtReportingError(
            "Management reporting framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise FinMgmtReportingError(
            "Management reporting framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise FinMgmtReportingError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if (
        "guest-blast" in name
        or "guest_blast" in name
        or name == "blast.sqlite"
        or name.startswith("blast-")
        or name.startswith("blast_")
    ):
        raise FinMgmtReportingError(
            "A guest blast is refused from this framework.",
            code="guest_blast_refused",
        )
    if "staff-blast" in name or "staff_blast" in name:
        raise FinMgmtReportingError(
            "A staff blast is refused from this framework.",
            code="staff_blast_refused",
        )
    if "public" in name or name.startswith("post") or "public-post" in name:
        raise FinMgmtReportingError(
            "A public post is refused from this framework.",
            code="public_post_refused",
        )
    if resolved not in {DEFAULT_DB.resolve(), LIVE_DEFAULT_DB} and (
        name.startswith("pnl")
        or name.startswith("balance_sheet")
        or name.startswith("balance-sheet")
        or name.startswith("cash_flow")
        or name.startswith("cash-flow")
        or name.startswith("checklist")
        or name
        in {
            "mgmt-reporting.sqlite",
            "management-reporting.sqlite",
            "live-pnl.sqlite",
            "live_pnl.sqlite",
            "live-bs.sqlite",
            "live-cf.sqlite",
            "fin-mgmt.sqlite",
            "fin_mgmt.sqlite",
        }
    ):
        raise FinMgmtReportingError(
            "P&L, BS, and CF numbers are not invented. "
            "Empty is not a live management-reporting pack.",
            code="current_refused",
        )
    if "bank" in name:
        raise FinMgmtReportingError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise FinMgmtReportingError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise FinMgmtReportingError(
            "Management reporting framework refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise FinMgmtReportingError(
            "Management reporting framework refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _row_state(data: Any) -> str:
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-FIN-05. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    return _row_state(data)


def ceiling_for(_state: str) -> str:
    """BUILT label only. At most BUILT. Does not write the ledger."""
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-20b4dd71cc0fcc88. Does not upsert, resolve, or harvest."""
    out: dict[str, Any] = {
        "cr_id": CR_ID,
        "cr_bound": True,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_ID,
        "cr_title": None,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    _assert_beta_path(path.resolve())
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_ID
    out["cr_title"] = row[3]
    out["cr_next_action"] = row[4]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling_for(state)
    flags["specified"] = state == "SPECIFIED"
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["invented_pnl"] = False
    flags["invented_balance_sheet"] = False
    flags["invented_cash_flow"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_management_reporting"] = False
    flags["empty_is_pnl_bs_cf"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_pnl"] = False
    flags["live_balance_sheet"] = False
    flags["live_cash_flow"] = False
    flags["live_management_reporting"] = False
    flags["pnl_bs_cf_machinery"] = False
    flags["current"] = False
    flags["pnl"] = None
    flags["pnl_number"] = None
    flags["balance_sheet"] = None
    flags["balance_sheet_number"] = None
    flags["cash_flow"] = None
    flags["cash_flow_number"] = None
    flags["checklist"] = None
    flags["guest_blast"] = False
    flags["staff_blast"] = False
    flags["public_post"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["payment_executed"] = False
    flags["bank_write"] = False
    flags["books_write"] = False
    flags["zayen_write"] = False
    flags["alchemist_write"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["on_disk"] = False
    flags["bound"] = BOUND
    flags["ledger_write"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["kind", "subject", "status", "evidence_note"],
        "properties": {
            "kind": {"type": "string", "enum": list(KIND_IDS)},
            "subject": {"type": "string"},
            "status": {"type": "string", "enum": ["NOTED"]},
            "evidence_note": {
                "type": "string",
                "description": (
                    "Not accepted. A note would not be a live management-reporting pack."
                ),
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "pnl_property": False,
        "balance_sheet_property": False,
        "cash_flow_property": False,
        "checklist_property": False,
        "guest_blast_property": False,
        "staff_blast_property": False,
        "public_post_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live management-reporting pack."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_management_reporting": False,
        "empty_is_pnl_bs_cf": False,
        "empty_is_ready": False,
        "proved": False,
        "live_pnl": False,
        "live_balance_sheet": False,
        "live_cash_flow": False,
        "live_management_reporting": False,
        "pnl_bs_cf_machinery": False,
        "current": False,
        "pnl": None,
        "pnl_number": None,
        "balance_sheet": None,
        "balance_sheet_number": None,
        "cash_flow": None,
        "cash_flow_number": None,
        "checklist": None,
        "guest_blast": False,
        "staff_blast": False,
        "public_post": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "invented_pnl": False,
        "invented_balance_sheet": False,
        "invented_cash_flow": False,
    }


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower().replace("-", "_")
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                **_quiet_read(),
                "honesty": honesty_flags(),
            }
    raise FinMgmtReportingError("Unknown management-reporting slot.", code="not_found")


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a framework file."""
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "recorded_count": 0,
        "money": None,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "score_changed": False,
        "on_disk": False,
        "kinds": kind_slots(),
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        **_quiet_read(),
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_guest_blast(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "A guest blast is refused from this framework.",
        code="guest_blast_refused",
    )


def refuse_staff_blast(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "A staff blast is refused from this framework.",
        code="staff_blast_refused",
    )


def refuse_public_post(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "A public post is refused from this framework.",
        code="public_post_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "P&L, BS, and CF numbers are not invented. "
        "Empty is not a live management-reporting pack.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Resolving the completion row is refused. CR-20b4dd71cc0fcc88 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "The framework stays empty. A filled slot would not be a live management-reporting pack.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise FinMgmtReportingError(
        "An Alchemist write is refused.",
        code="alchemist_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "transfer", "payout", "withdraw"}:
                refuse_bank(payload)
            if token in {"zayen", "books", "journal"}:
                refuse_books(payload)
            if token in {"guest-blast", "blast", "broadcast"}:
                refuse_guest_blast(payload)
            if token in {"staff-blast", "staff-broadcast"}:
                refuse_staff_blast(payload)
            if token in {"public-post", "public", "post", "publish"}:
                refuse_public_post(payload)
            if token in {
                "pnl",
                "pnl-number",
                "balance-sheet",
                "balance-sheet-number",
                "cash-flow",
                "cash-flow-number",
                "checklist",
                "current",
                "live-pnl",
                "live-balance-sheet",
                "live-cash-flow",
                "live-management-reporting",
            }:
                refuse_current(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf-access", "zero-trust"}:
                refuse_access(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr-resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production-mutate"}:
                refuse_production(payload)
            if token in {"score", "credits", "green"}:
                refuse_score(payload)
            if token in {"alchemist"}:
                refuse_alchemist(payload)
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "notes",
            }:
                refuse_fill(payload)
    raise FinMgmtReportingError(
        "This framework does not store a live management-reporting pack, P&L, "
        "balance sheet, cash flow, a payment, a bank write, a guest blast, a "
        "staff blast, or a public post.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise FinMgmtReportingError(
            "Management reporting framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise FinMgmtReportingError(
            "Management reporting framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_FIN_MGMT_REPORTING") or "").strip() != "1":
            raise FinMgmtReportingError(
                "test mode refuses the live management-reporting framework path",
                code="live_guard",
            )
    raise FinMgmtReportingError(
        "The framework stays empty. Empty is not a live management-reporting pack.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_ready(*_args: Any, **_kwargs: Any) -> None:
    refuse_ready({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_pnl(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_balance_sheet(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_cash_flow(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def blast_guests(*_args: Any, **_kwargs: Any) -> None:
    refuse_guest_blast({})


def blast_staff(*_args: Any, **_kwargs: Any) -> None:
    refuse_staff_blast({})


def post_public(*_args: Any, **_kwargs: Any) -> None:
    refuse_public_post({})


def move_money(*_args: Any, **_kwargs: Any) -> None:
    refuse_payment({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    zayen: str | None = None,
    books: str | None = None,
    pnl: str | None = None,
    balance_sheet: str | None = None,
    cash_flow: str | None = None,
    checklist: str | None = None,
    current: str | None = None,
    guest_blast: str | None = None,
    staff_blast: str | None = None,
    public_post: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    score: str | None = None,
    alchemist: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(bank):
        refuse_bank({})
    if _present(zayen) or _present(books):
        refuse_books({})
    if _present(guest_blast):
        refuse_guest_blast({})
    if _present(staff_blast):
        refuse_staff_blast({})
    if _present(public_post):
        refuse_public_post({})
    if (
        _present(pnl)
        or _present(balance_sheet)
        or _present(cash_flow)
        or _present(checklist)
        or _present(current)
    ):
        refuse_current({})
    if _present(cloudflare):
        refuse_cloudflare({})
    if _present(access):
        refuse_access({})
    if _present(proven) or _present(prove):
        refuse_proven({})
    if _present(ready):
        refuse_ready({})
    if _present(resolve):
        refuse_resolve({})
    if _present(production):
        refuse_production({})
    if _present(score):
        refuse_score({})
    if _present(alchemist):
        refuse_alchemist({})
    if _present(fill):
        refuse_fill({})
    if _present(write):
        refuse_external_write({})


def _figure_typed(value: Any) -> bool:
    """A supplied number, including zero. An empty string is not a figure."""
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return str(value).strip() != ""


def _flag_set(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return bool(value)
    return str(value).strip() != ""


def _resolved_rows(catalog: Path) -> int | None:
    if not catalog.is_file():
        return None
    uri = catalog.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM wolf_completion_items
            WHERE capability=? AND state='RESOLVED'
            """,
            (CAP_ID,),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None:
        return None
    return int(row[0])


def read_management_report(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    *,
    pnl: Any = None,
    pnl_number: Any = None,
    balance_sheet: Any = None,
    balance_sheet_number: Any = None,
    cash_flow: Any = None,
    cash_flow_number: Any = None,
    cash: Any = None,
    statement: Any = None,
    trial_balance: Any = None,
    balance: Any = None,
    amount: Any = None,
    payment: Any = None,
    open_books: Any = None,
) -> dict[str, Any]:
    """Report UNAVAILABLE while the books source stays unopened.

    Reuses the accounting-core read and this module's empty framework.
    A typed P&L, balance sheet, cash-flow, cash, or statement figure,
    including zero, is refused. Opening the books is refused. No slot is
    filled. CAP-FIN-05 stays SPECIFIED.
    """
    from core import fin_accounting_core as books

    if _flag_set(payment):
        refuse_payment({})
    if any(
        _figure_typed(item)
        for item in (
            pnl,
            pnl_number,
            balance_sheet,
            balance_sheet_number,
            cash_flow,
            cash_flow_number,
            cash,
            statement,
            trial_balance,
            balance,
            amount,
        )
    ):
        refuse_current({})
    if _flag_set(open_books):
        raise FinMgmtReportingError(
            "Opening the books is an owner act. This report does not open them.",
            code="books_open_refused",
        )

    catalog = Path(catalog_db) if catalog_db else CATALOG_DB
    ledger = Path(ledger_path) if ledger_path else LEDGER_JSON
    core = books.read_accounting_core(catalog, ledger)
    framework = build_framework(ledger, catalog)
    flags = framework["honesty"]
    books_source = str(core.get("books_source") or "UNKNOWN")
    report_state = "UNAVAILABLE" if core.get("books_opened") is not True else "UNKNOWN"
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "report_state": report_state,
        "unavailable_is_a_statement": False,
        "books_source": books_source,
        "books_opened": False,
        "statements_rendered": False,
        "green_test_renders_pack": False,
        "typed_figure_closes_row": False,
        "pnl": None,
        "pnl_number": None,
        "balance_sheet": None,
        "balance_sheet_number": None,
        "cash_flow": None,
        "cash_flow_number": None,
        "cash": None,
        "trial_balance": None,
        "statement": None,
        "kinds": framework["kinds"],
        "recorded_count": framework["recorded_count"],
        "empty_is_management_reporting": False,
        "finance_display": core.get("finance_display"),
        "finance_shown_as_current": core.get("finance_shown_as_current") is True,
        "commissioned_books_present": core.get("commissioned_books_present") is True,
        "sample_present": core.get("sample_present") is True,
        "sample_opened": False,
        "payment_executed": False,
        "books_written": False,
        "ledger_state": flags.get("ledger_maturity"),
        "ledger_write": False,
        "cr_id": flags.get("cr_id"),
        "cr_present": flags.get("cr_present") is True,
        "cr_state": flags.get("cr_state"),
        "cr_resolved": False,
        "resolved_rows": _resolved_rows(catalog),
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "proven": False,
        "ready": False,
        "score_changed": False,
    }
