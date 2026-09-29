#!/usr/bin/env python3
"""CAP-BZG-02 venue P&L / management rollup skeleton (Beta only).

Decision served: 2026-09-20 PICK — CAP-BZG-02 venue P&L & management
rollup framework skeleton on Beta only
(docs/deliveries/GROK-PLAN-BZG-VENUE-PNL-V1-2026-09-20.md).
Extended 2026-09-29 by FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
BZG-VENUEPL-1 — per-outlet read-only rollup from registry + closes +
journal facts (honest empty/UNKNOWN when facts absent).
CR-1f136175afbcf7d4 stays OPEN. Bound beta-bzg-ops-safe.

Composes venue identity from org_outlet_registry and probes
venue_daily_closes + BZG journal_lines.outlet_id + ESB warehouse
presence (BLZ/Uma only). Does not invent revenue, cost, contribution,
rollup, budgets, or go-live numbers. Empty/UNKNOWN is not zero-as-success.
Does not write Production, Alchemist, Zayen books, a bank, a payment,
Cloudflare, Access, the Model C ledger, or the completion row.
CAP-BZG-02 stays SPECIFIED. Ceiling label BUILT. PROVEN and READY
are not invented. staff_ready=false · human_commissioned=false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "bzg_venue_pnl.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-1f136175afbcf7d4"
CAP_ID = "CAP-BZG-02"
SCHEMA_ID = "wolf.cap-bzg-02.venue-pnl.v1"
BOUND = "beta-bzg-ops-safe"
PACK = "BZG-VENUEPL-1"
LEGAL_ENTITY = "ENT-BZG"
BOARD_PERM = "atrium.board.read"
# ESB warehouse branch for Uma Blu — not a multi-outlet map.
ESB_UMA_BRANCH = "BLZ"
UMA_OUTLET_ID = "BZG-UMA"

PAGE_PATHS = frozenset(
    {
        "/bzg/venue-pnl",
        "/bzg/venue-pnl/",
        "/bzg-venue-pnl",
        "/bzg-venue-pnl/",
        "/bzg-venue-pnl.html",
        "/dashboards/bzg-venue-pnl.html",
    }
)

_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "venue",
        "Venue",
        "Named venue slot. Empty is not a venue and not a live venue P&L.",
    ),
    (
        "revenue",
        "Revenue",
        "Named revenue slot. Empty is not revenue and not a live venue P&L.",
    ),
    (
        "cost",
        "Cost",
        "Named cost slot. Empty is not a cost and not a live venue P&L.",
    ),
    (
        "contribution",
        "Contribution",
        "Named contribution slot. Empty is not contribution and not a live venue P&L.",
    ),
    (
        "rollup",
        "Rollup",
        "Named rollup slot. Empty is not a rollup and not proof of management rollup machinery.",
    ),
    (
        "notes",
        "Notes",
        "Named notes slot. Empty is not a P&L note and not a live venue P&L.",
    ),
)


def _empty_slot(kind: str, label: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "slot": "empty",
        "evidence": None,
        "venue": None,
        "revenue": None,
        "cost": None,
        "contribution": None,
        "rollup": None,
        "tax_treatment": None,
        "tax_claimed": False,
        "current": False,
        "live_pnl": False,
        "rollup_machinery": False,
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
    "An empty framework is not a live venue P&L.",
    "An empty framework is not proof of management rollup machinery.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "Revenue, cost, contribution, and rollup numbers are not invented.",
    "Tax treatment is not claimed.",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-BZG-02 stays SPECIFIED.",
    "The ceiling label is BUILT.",
    "Insufficient close/journal facts → UNKNOWN (not zero-as-success).",
    "ESB warehouse presence is not a live venue P&L until bound by a close.",
    "staff_ready stays false.",
    "human_commissioned stays false.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "pack": PACK,
    "slice": "bzg_venue_pnl_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_pnl": False,
    "empty_is_rollup_machinery": False,
    "empty_is_ready": False,
    "proved": False,
    "live_pnl": False,
    "rollup_machinery": False,
    "current": False,
    "venue": None,
    "revenue": None,
    "cost": None,
    "contribution": None,
    "rollup": None,
    "tax_treatment": None,
    "tax_claimed": False,
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
    "invented_revenue": False,
    "invented_cost": False,
    "invented_contribution": False,
    "invented_rollup": False,
    "invented_tax": False,
    "invented_sales": False,
    "invented_covers": False,
    "invented_budgets": False,
    "invented_allocations": False,
    "invented_go_live_numbers": False,
    "staff_ready": False,
    "human_commissioned": False,
    "ledger_write": False,
    "legal_entity_id": LEGAL_ENTITY,
}


class VenuePnlError(ValueError):
    """Fail closed. Does not invent P&L numbers, tax, or PROVEN."""

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
        raise VenuePnlError(
            "venue P&L framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise VenuePnlError(
            "venue P&L framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise VenuePnlError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "tax" in name:
        raise VenuePnlError(
            "Tax treatment is not claimed from this framework.",
            code="tax_refused",
        )
    # Do not match the empty skeleton filename bzg_venue_pnl.sqlite itself.
    if resolved not in {DEFAULT_DB.resolve(), LIVE_DEFAULT_DB} and (
        name.startswith("revenue")
        or name.startswith("cost")
        or name.startswith("contribution")
        or name.startswith("rollup")
        or name.startswith("venue")
        or name in {"pnl.sqlite", "live-pnl.sqlite", "live_pnl.sqlite"}
    ):
        raise VenuePnlError(
            "Revenue, cost, contribution, and rollup are not invented. Empty is not a live venue P&L.",
            code="current_refused",
        )
    if "bank" in name:
        raise VenuePnlError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise VenuePnlError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise VenuePnlError(
            "venue P&L framework refuses a production path",
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
        raise VenuePnlError(
            "venue P&L framework refuses a path outside Beta or a test fixture",
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
    """Read CAP-BZG-02. Does not write the ledger."""
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
    """Read CR-1f136175afbcf7d4. Does not upsert, resolve, or harvest."""
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
    flags["invented_revenue"] = False
    flags["invented_cost"] = False
    flags["invented_contribution"] = False
    flags["invented_rollup"] = False
    flags["invented_tax"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_pnl"] = False
    flags["empty_is_rollup_machinery"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_pnl"] = False
    flags["rollup_machinery"] = False
    flags["current"] = False
    flags["venue"] = None
    flags["revenue"] = None
    flags["cost"] = None
    flags["contribution"] = None
    flags["rollup"] = None
    flags["tax_treatment"] = None
    flags["tax_claimed"] = False
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
                "description": "Not accepted. A note would not be a live venue P&L.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "venue_property": False,
        "revenue_property": False,
        "cost_property": False,
        "contribution_property": False,
        "rollup_property": False,
        "tax_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live venue P&L."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_pnl": False,
        "empty_is_rollup_machinery": False,
        "empty_is_ready": False,
        "proved": False,
        "live_pnl": False,
        "rollup_machinery": False,
        "current": False,
        "venue": None,
        "revenue": None,
        "cost": None,
        "contribution": None,
        "rollup": None,
        "tax_treatment": None,
        "tax_claimed": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "invented_revenue": False,
        "invented_cost": False,
        "invented_contribution": False,
        "invented_rollup": False,
        "invented_tax": False,
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
    raise VenuePnlError("Unknown venue P&L slot.", code="not_found")


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
    raise VenuePnlError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_tax(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Tax treatment is not claimed from this framework.",
        code="tax_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Revenue, cost, contribution, and rollup are not invented. Empty is not a live venue P&L.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Resolving the completion row is refused. CR-1f136175afbcf7d4 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "The framework stays empty. A filled slot would not be a live venue P&L.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise VenuePnlError(
        "An Alchemist write is refused.",
        code="alchemist_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "transfer", "payout", "withdraw"}:
                refuse_bank(payload)
            if token in {"zayen", "books", "journal"}:
                refuse_books(payload)
            if token in {"tax", "tax-treatment", "gst", "vat"}:
                refuse_tax(payload)
            if token in {
                "venue",
                "venues",
                "revenue",
                "cost",
                "costs",
                "contribution",
                "rollup",
                "current",
                "live-pnl",
                "pnl",
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
    raise VenuePnlError(
        "This framework does not store a live venue P&L, revenue, cost, contribution, rollup, or a tax treatment.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise VenuePnlError(
            "venue P&L framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise VenuePnlError(
            "venue P&L framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_BZG_VENUE_PNL") or "").strip() != "1":
            raise VenuePnlError(
                "test mode refuses the live venue P&L framework path",
                code="live_guard",
            )
    raise VenuePnlError(
        "The framework stays empty. Empty is not a live venue P&L.",
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


def invent_revenue(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_cost(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_contribution(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_rollup(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_tax(*_args: Any, **_kwargs: Any) -> None:
    refuse_tax({})


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
    venue: str | None = None,
    revenue: str | None = None,
    cost: str | None = None,
    contribution: str | None = None,
    rollup: str | None = None,
    tax: str | None = None,
    current: str | None = None,
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
    if _present(tax):
        refuse_tax({})
    if (
        _present(venue)
        or _present(revenue)
        or _present(cost)
        or _present(contribution)
        or _present(rollup)
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


# --- BZG-VENUEPL-1: per-outlet read-only rollup (facts only) -----------------


def person_may_read_venue_pnl(
    person_id: str | None, conn: sqlite3.Connection | None = None
) -> bool:
    """Zayen (BZG board) + Owner progress.read. Amanda / Ext Acct fail closed."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    own = conn is None
    c = conn
    if c is None:
        uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
        c = sqlite3.connect(uri, uri=True)
        c.row_factory = sqlite3.Row
    try:
        if _rbac.can(pid, "progress.read", {}, conn=c):
            return True
        if _rbac.can(pid, BOARD_PERM, {"entity_id": LEGAL_ENTITY}, conn=c):
            return True
        return False
    finally:
        if own and c is not None:
            c.close()


def require_read(person_id: str | None, conn: sqlite3.Connection | None = None) -> None:
    if not person_may_read_venue_pnl(person_id, conn):
        raise VenuePnlError(
            "BZG Venue P&L is not on this assignment.",
            code="forbidden",
        )


def _unknown_slot(kind: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": kind.replace("_", " ").title(),
        "slot": "UNKNOWN",
        "value": None,
        "amount": None,
        "evidence": None,
        "live_pnl": False,
        "invented": False,
        "why": why,
    }


def _fact_slot(
    kind: str,
    *,
    value: Any,
    evidence: dict[str, Any] | None,
    why: str,
) -> dict[str, Any]:
    if value is None:
        return _unknown_slot(kind, why)
    return {
        "kind": kind,
        "label": kind.replace("_", " ").title(),
        "slot": "FACT",
        "value": value,
        "amount": value if isinstance(value, (int, float)) else None,
        "evidence": evidence,
        "live_pnl": False,
        "invented": False,
        "why": why,
    }


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not exists:
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _close_facts_for_outlet(
    outlet: dict[str, Any], conn: sqlite3.Connection
) -> dict[str, Any]:
    """Read venue_daily_closes for this outlet — never invent a close."""
    cols = _table_cols(conn, "venue_daily_closes")
    empty = {
        "close_count": 0,
        "closes": [],
        "revenue_from_esb_totals": None,
        "has_esb_totals_fact": False,
        "table_present": bool(cols),
    }
    if not cols:
        return empty
    oid = outlet["outlet_id"]
    brand = outlet.get("brand_id")
    clauses = ["outlet_id=?"]
    args: list[Any] = [oid]
    if brand and "venue_brand_id" in cols:
        clauses.append("venue_brand_id=?")
        args.append(brand)
    where = " OR ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT close_id, outlet_id, venue_brand_id, business_date, state,
               esb_totals_json, declared_cash_amount, variance_cash_amount
        FROM venue_daily_closes
        WHERE ({where})
        ORDER BY business_date DESC
        LIMIT 30
        """,
        tuple(args),
    ).fetchall()
    closes: list[dict[str, Any]] = []
    revenue_sum: float | None = None
    has_esb = False
    for r in rows:
        totals = None
        raw = r["esb_totals_json"]
        if raw:
            try:
                totals = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, json.JSONDecodeError):
                totals = None
        if isinstance(totals, dict) and totals:
            has_esb = True
            gt = totals.get("grand_total")
            if isinstance(gt, (int, float)):
                revenue_sum = (0.0 if revenue_sum is None else revenue_sum) + float(gt)
        closes.append(
            {
                "close_id": r["close_id"],
                "outlet_id": r["outlet_id"],
                "venue_brand_id": r["venue_brand_id"],
                "business_date": r["business_date"],
                "state": r["state"],
                "has_esb_totals": bool(totals),
                # Surface totals only when present on a real close row — not invented.
                "esb_grand_total": (
                    totals.get("grand_total")
                    if isinstance(totals, dict)
                    else None
                ),
            }
        )
    return {
        "close_count": len(closes),
        "closes": closes,
        "revenue_from_esb_totals": revenue_sum,
        "has_esb_totals_fact": has_esb,
        "table_present": True,
    }


def _journal_facts_for_outlet(outlet_id: str) -> dict[str, Any]:
    """Count BZG journal_lines for outlet_id — 0 journals is honest empty."""
    from core import entity_books as _books

    out: dict[str, Any] = {
        "journal_line_count": 0,
        "journal_header_count": 0,
        "books_shell_kind": None,
        "accounts": None,
        "db_file": None,
        "has_numeric_pnl_from_books": False,
    }
    try:
        stamp = _books.desk_stamp(LEGAL_ENTITY)
    except Exception:  # noqa: BLE001
        return out
    out["books_shell_kind"] = stamp.get("shell_kind")
    out["accounts"] = stamp.get("accounts")
    out["db_file"] = stamp.get("db_file")
    out["journal_header_count"] = int(stamp.get("journals") or 0)
    fname = _books.ENTITY_FILES.get(LEGAL_ENTITY, "atrium-bzg.sqlite")
    path = _books.BETA_DIR / fname
    if not path.is_file():
        return out
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_lines)").fetchall()}
        if "outlet_id" not in cols:
            return out
        n = conn.execute(
            "SELECT COUNT(*) FROM journal_lines WHERE outlet_id=?",
            (outlet_id,),
        ).fetchone()[0]
        out["journal_line_count"] = int(n)
        # Journals present would still not auto-compute contribution here —
        # only report count. Numeric P&L from books stays false until a
        # dedicated books rollup is proven (out of this pack).
        out["has_numeric_pnl_from_books"] = False
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    return out


def _esb_probe_for_outlet(outlet: dict[str, Any]) -> dict[str, Any]:
    """Warehouse presence for Uma/BLZ only. Totals are NOT rolled into P&L slots
    without a venue_daily_close binding (honest — avoids inventing contribution).
    """
    base = {
        "applicable": False,
        "branch": None,
        "warehouse_present": False,
        "status": "NOT_APPLICABLE",
        "distinct_biz_dates": None,
        "bound_to_close": False,
        "totals_in_pnl_slots": False,
        "note": "ESB BLZ branch maps to Uma Blu only; other outlets have no ESB branch fact.",
    }
    if outlet.get("outlet_id") != UMA_OUTLET_ID and outlet.get("brand_id") != UMA_OUTLET_ID:
        return base
    base["applicable"] = True
    base["branch"] = ESB_UMA_BRANCH
    try:
        from core import esb_close_snapshot as _esb
        from core import integration_health as _ih

        health = _ih._read_esb(None)
        base["status"] = health.get("status") or "UNKNOWN"
        base["warehouse_present"] = health.get("status") == "READ_OK"
        path = _esb.resolve_esb_path(None)
        if path.is_file():
            uri = path.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            try:
                row = conn.execute(
                    "SELECT COUNT(DISTINCT biz_date) FROM sales"
                ).fetchone()
                base["distinct_biz_dates"] = int(row[0]) if row else 0
            finally:
                conn.close()
        base["note"] = (
            "ESB warehouse readable for BLZ/Uma. Payment-line days are present as "
            "warehouse facts but are NOT placed into revenue/contribution slots "
            "until bound by a venue_daily_close (0 closes today)."
        )
    except Exception as exc:  # noqa: BLE001
        base["status"] = "ERROR"
        base["note"] = f"ESB probe failed closed: {type(exc).__name__}"
    return base


def outlet_card(
    outlet: dict[str, Any],
    *,
    catalog_conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Venue mini-business card — identity from registry; money slots from facts only."""
    own = catalog_conn is None
    conn = catalog_conn or _catalog_ro()
    try:
        closes = _close_facts_for_outlet(outlet, conn)
        journals = _journal_facts_for_outlet(outlet["outlet_id"])
        esb = _esb_probe_for_outlet(outlet)

        venue_slot = _fact_slot(
            "venue",
            value={
                "outlet_id": outlet["outlet_id"],
                "display_name": outlet.get("display_name"),
                "outlet_kind": outlet.get("outlet_kind"),
                "brand_id": outlet.get("brand_id"),
                "parent_outlet_id": outlet.get("parent_outlet_id"),
                "operating_unit_id": outlet.get("operating_unit_id"),
                "legal_entity_id": outlet.get("legal_entity_id") or LEGAL_ENTITY,
            },
            evidence={"source": "org_outlet_registry"},
            why="Registry identity is a fact. Not a live P&L.",
        )
        status_slot = _fact_slot(
            "status",
            value=outlet.get("status"),
            evidence={"source": "org_outlet_registry"},
            why="Registry status is a fact (OPEN / PRE-OPENING / …).",
        )

        if closes["has_esb_totals_fact"] and closes["revenue_from_esb_totals"] is not None:
            revenue = _fact_slot(
                "revenue",
                value=closes["revenue_from_esb_totals"],
                evidence={
                    "source": "venue_daily_closes.esb_totals_json",
                    "close_count": closes["close_count"],
                },
                why="Sum of esb_totals.grand_total on bound closes only.",
            )
        else:
            revenue = _unknown_slot(
                "revenue",
                "No venue_daily_close with esb_totals for this outlet. "
                "Empty/UNKNOWN — not zero-as-success."
                + (
                    " ESB warehouse days exist for BLZ/Uma but are unbound to a close."
                    if esb.get("applicable") and (esb.get("distinct_biz_dates") or 0) > 0
                    else ""
                ),
            )

        cost = _unknown_slot(
            "cost",
            "No cost fact on closes or outlet-scoped journal lines. UNKNOWN.",
        )
        contribution = _unknown_slot(
            "contribution",
            "Contribution requires revenue and cost facts. Insufficient facts.",
        )
        rollup = _unknown_slot(
            "rollup",
            "Per-outlet rollup stays UNKNOWN until revenue/cost facts exist.",
        )

        has_numeric = revenue["slot"] == "FACT"
        return {
            "outlet_id": outlet["outlet_id"],
            "display_name": outlet.get("display_name"),
            "status": outlet.get("status"),
            "outlet_kind": outlet.get("outlet_kind"),
            "brand_id": outlet.get("brand_id"),
            "parent_outlet_id": outlet.get("parent_outlet_id"),
            "operating_unit_id": outlet.get("operating_unit_id"),
            "legal_entity_id": outlet.get("legal_entity_id") or LEGAL_ENTITY,
            "cost_centre_id": outlet.get("cost_centre_id"),
            "revenue_centre_id": outlet.get("revenue_centre_id"),
            "note": outlet.get("note"),
            "slots": {
                "venue": venue_slot,
                "status": status_slot,
                "revenue": revenue,
                "cost": cost,
                "contribution": contribution,
                "rollup": rollup,
            },
            "sources_probed": {
                "venue_daily_closes": closes,
                "journal_lines": journals,
                "esb_warehouse": esb,
            },
            "has_numeric_pnl_facts": has_numeric,
            "live_pnl": False,
            "invented_revenue": False,
            "invented_cost": False,
            "invented_contribution": False,
            "invented_rollup": False,
            "staff_ready": False,
            "human_commissioned": False,
            "ready": False,
            "proven": False,
            "pack": PACK,
        }
    finally:
        if own:
            conn.close()


def build_outlet_rollup(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Master BZG rollup — aggregate only where facts exist; else insufficient_facts."""
    from core import bzg_outlet_registry as _outlets

    flags = honesty_flags(ledger_path, catalog_db)
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        outlets = _outlets.list_outlets(conn)
        cards = [outlet_card(o, catalog_conn=conn) for o in outlets]
    finally:
        conn.close()

    with_facts = [c for c in cards if c.get("has_numeric_pnl_facts")]
    if with_facts:
        # Sum only FACT revenue amounts — never invent missing outlets as zero.
        rev_parts = [
            c["slots"]["revenue"]["amount"]
            for c in with_facts
            if isinstance(c["slots"]["revenue"].get("amount"), (int, float))
        ]
        master_status = "partial_facts"
        master_revenue = round(sum(rev_parts), 2) if rev_parts else None
        master_message = (
            f"Aggregated revenue from {len(with_facts)} outlet(s) with close facts. "
            f"{len(cards) - len(with_facts)} outlet(s) still UNKNOWN — not treated as zero."
        )
    else:
        master_status = "insufficient_facts"
        master_revenue = None
        master_message = (
            "Insufficient facts for master BZG P&L rollup. "
            "No venue_daily_close esb_totals and no invented numbers toward any target."
        )

    uma = next((c for c in cards if c["outlet_id"] == UMA_OUTLET_ID), None)
    rain = next((c for c in cards if c["outlet_id"] == "BZG-RAIN"), None)
    pool = next((c for c in cards if c["outlet_id"] == "OU-BZG-RAIN-POOL"), None)

    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "pack": PACK,
        "schema_id": SCHEMA_ID,
        "title": "BZG Venue P&L rollup",
        "message": (
            "Per-outlet mini-business cards from outlet registry + close/journal "
            "fact probes. Empty/UNKNOWN when facts are absent — not a live P&L. "
            "Not PROVEN. Not READY. CAP-BZG-02 stays SPECIFIED."
        ),
        "legal_entity_id": LEGAL_ENTITY,
        "outlet_count": len(cards),
        "outlets_with_numeric_facts": len(with_facts),
        "outlets": cards,
        "master": {
            "status": master_status,
            "revenue": master_revenue,
            "cost": None,
            "contribution": None,
            "rollup": None,
            "slot": "UNKNOWN" if master_status == "insufficient_facts" else "PARTIAL",
            "message": master_message,
            "invented": False,
            "toward_target_pct": None,
            "target_note": "No invented progress toward any contribution target.",
        },
        "status_checks": {
            "uma_open": bool(uma and uma.get("status") == "OPEN"),
            "rainforest_pre_opening": bool(
                rain and rain.get("status") == "PRE-OPENING"
            ),
            "pool_bar_pre_opening": bool(
                pool and pool.get("status") == "PRE-OPENING"
            ),
        },
        "framework_skeleton": "BUILT",
        "empty": len(with_facts) == 0,
        "empty_is_pnl": False,
        "empty_is_rollup_machinery": False,
        "empty_is_ready": False,
        "proved": False,
        "live_pnl": False,
        "rollup_machinery": False,
        "current": False,
        "staff_ready": False,
        "human_commissioned": False,
        "ready": False,
        "proven": False,
        "invented_revenue": False,
        "invented_cost": False,
        "invented_contribution": False,
        "invented_rollup": False,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "gaps": list(GAPS),
        "honesty": flags,
        "href": "/bzg/venue-pnl",
        "api": "/api/bzg/venue-pnl/rollup",
    }


def rollup_panel_for_outlets() -> dict[str, Any]:
    """Thin teaser for /bzg/outlets overview — no invented totals."""
    full = build_outlet_rollup()
    return {
        "pack": PACK,
        "title": "Venue P&L rollup",
        "href": "/bzg/venue-pnl",
        "api": "/api/bzg/venue-pnl/rollup",
        "outlet_count": full["outlet_count"],
        "outlets_with_numeric_facts": full["outlets_with_numeric_facts"],
        "master_status": full["master"]["status"],
        "master_message": full["master"]["message"],
        "uma_open": full["status_checks"]["uma_open"],
        "rainforest_pre_opening": full["status_checks"]["rainforest_pre_opening"],
        "pool_bar_pre_opening": full["status_checks"]["pool_bar_pre_opening"],
        "staff_ready": False,
        "human_commissioned": False,
        "ready": False,
        "live_pnl": False,
        "message": (
            "Read-only venue mini-business cards. Insufficient close facts → "
            "UNKNOWN — not zero. See /bzg/venue-pnl."
        ),
    }
