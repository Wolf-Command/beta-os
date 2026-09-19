#!/usr/bin/env python3
"""CAP-GGV-03 client / contract profitability skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-GGV-CLIENT-PROFITABILITY-V1-2026-09-20.md.
CR-ccb3287dabe91d4b stays OPEN. Owner lane ggv-client-profitability-v1.
Wave-7 after intg-secrets-env-separation-v1 256ad67.
intel-learning-policy-v1 stays parked.
Bound beta-ggv-ops-safe.

Names the client, contract, and allocation slots and leaves every slot
empty. An empty framework is not a live P&L and not proof of profitability.
This module does not invent revenue, cost, margin, or FX. It does not
write Production, Alchemist, Zayen books, a bank, a payment, Cloudflare,
Access, the Model C ledger, or the completion row. CAP-GGV-03 stays at
the ledger value. The ceiling label is BUILT unless the ledger is already
PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "ggv_client_profitability.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-ccb3287dabe91d4b"
CAP_ID = "CAP-GGV-03"
SCHEMA_ID = "wolf.cap-ggv-03.client-profitability.v1"
BOUND = "beta-ggv-ops-safe"

KIND_IDS = ("client", "contract", "allocation")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "client",
        "label": "Client",
        "slot": "empty",
        "evidence": None,
        "revenue": None,
        "cost": None,
        "margin": None,
        "fx": None,
        "live_pnl": False,
        "current": False,
        "profitability_proved": False,
        "payment": None,
        "why": "Named client slot. Empty is not a client P&L and not proof of profitability.",
    },
    {
        "kind": "contract",
        "label": "Contract",
        "slot": "empty",
        "evidence": None,
        "revenue": None,
        "cost": None,
        "margin": None,
        "fx": None,
        "live_pnl": False,
        "current": False,
        "profitability_proved": False,
        "payment": None,
        "why": "Named contract slot. Empty is not a contract P&L and not proof of profitability.",
    },
    {
        "kind": "allocation",
        "label": "Allocation",
        "slot": "empty",
        "evidence": None,
        "revenue": None,
        "cost": None,
        "margin": None,
        "fx": None,
        "live_pnl": False,
        "current": False,
        "profitability_proved": False,
        "payment": None,
        "why": "Named allocation slot. Empty is not a staff or external cost allocation and not a margin.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live P&L.",
    "An empty framework is not proof of profitability.",
    "Revenue, cost, margin, and FX are not invented.",
    "A catalog target is not an actual margin.",
    "No payment is stored.",
    "No bank write.",
    "No Zayen or books write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-GGV-03 stays at the ledger value.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "ggv_client_profitability_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_pnl": False,
    "profitability_proved": False,
    "live_pnl": False,
    "revenue": None,
    "cost": None,
    "margin": None,
    "fx": None,
    "current": False,
    "target_is_actual": False,
    "payment": None,
    "money": None,
    "bank_write": False,
    "books_write": False,
    "zayen_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "wolf_system_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class ClientProfitabilityError(ValueError):
    """Fail closed. Does not invent a P&L, a margin, or PROVEN."""

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
        raise ClientProfitabilityError(
            "profitability framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise ClientProfitabilityError(
            "profitability framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise ClientProfitabilityError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "bank" in name:
        raise ClientProfitabilityError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise ClientProfitabilityError(
            "A payment is not stored on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise ClientProfitabilityError(
            "profitability framework refuses a production path",
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
        raise ClientProfitabilityError(
            "profitability framework refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-GGV-03. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ceiling_for(state: str) -> str:
    """BUILT label unless the ledger is already higher. Does not write it."""
    if state in HIGHER_THAN_BUILT:
        return state
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-ccb3287dabe91d4b. Does not upsert, resolve, or harvest."""
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
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_pnl"] = False
    flags["profitability_proved"] = False
    flags["live_pnl"] = False
    flags["revenue"] = None
    flags["cost"] = None
    flags["margin"] = None
    flags["fx"] = None
    flags["current"] = False
    flags["target_is_actual"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["bank_write"] = False
    flags["books_write"] = False
    flags["zayen_write"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["on_disk"] = False
    flags["bound"] = BOUND
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
                "description": "Not accepted. A note would not be a P&L.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "revenue_property": False,
        "cost_property": False,
        "margin_property": False,
        "fx_property": False,
        "live_pnl_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a P&L."""
    return [dict(row) for row in EVIDENCE_KINDS]


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                "empty": True,
                "empty_is_pnl": False,
                "profitability_proved": False,
                "live_pnl": False,
                "revenue": None,
                "cost": None,
                "margin": None,
                "fx": None,
                "current": False,
                "target_is_actual": False,
                "payment": None,
                "bank_write": False,
                "books_write": False,
                "zayen_write": False,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise ClientProfitabilityError("Unknown framework slot.", code="not_found")


def build_register(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a P&L file or invent numbers."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_pnl": False,
        "recorded_count": 0,
        "profitability_proved": False,
        "live_pnl": False,
        "revenue": None,
        "cost": None,
        "margin": None,
        "fx": None,
        "current": False,
        "target_is_actual": False,
        "payment": None,
        "money": None,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "score_changed": False,
        "on_disk": False,
        "kinds": slots,
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        "ledger_write": False,
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "A payment is not stored on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Revenue, cost, margin, and FX are not invented. Empty is not a live P&L and not proof of profitability.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "READY is refused. This framework does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Resolving the completion row is refused. CR-ccb3287dabe91d4b stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "The framework stays empty. A filled slot would not be a live P&L.",
        code="slots_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise ClientProfitabilityError(
        "Score and credits are not changed from this framework.",
        code="score_refused",
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
            if token in {
                "revenue",
                "cost",
                "margin",
                "fx",
                "forex",
                "live-pnl",
                "pnl",
                "current",
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
            if token in {"fill", "note", "evidence", "evidence-note", "slots-filled"}:
                refuse_fill(payload)
            if token in {"score", "credits"}:
                refuse_score(payload)
    raise ClientProfitabilityError(
        "This framework does not store a P&L, a payment, or a bank write.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file and does not invent numbers."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise ClientProfitabilityError(
            "profitability framework does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_GGV_PROFITABILITY") or "").strip() != "1":
            raise ClientProfitabilityError(
                "test mode refuses the live profitability framework path",
                code="live_guard",
            )
    raise ClientProfitabilityError(
        "The framework stays empty. Empty is not a live P&L and not proof of profitability.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def mark_live_pnl(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    revenue: str | None = None,
    cost: str | None = None,
    margin: str | None = None,
    fx: str | None = None,
    live_pnl: str | None = None,
    current: str | None = None,
    zayen: str | None = None,
    books: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    score: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(bank):
        refuse_bank({})
    if _present(zayen) or _present(books):
        refuse_books({})
    if (
        _present(revenue)
        or _present(cost)
        or _present(margin)
        or _present(fx)
        or _present(live_pnl)
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
    if _present(fill):
        refuse_fill({})
    if _present(score):
        refuse_score({})
    if _present(write):
        refuse_external_write({})
