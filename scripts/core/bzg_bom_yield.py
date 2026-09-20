#!/usr/bin/env python3
"""CAP-BZG-06 Recipe / Cost Standards (BOM/yield) skeleton v1 (Beta only).

Decision served: 2026-09-20 PICK — CAP-BZG-06 Recipe / Cost Standards (BOM/yield)
framework skeleton on Beta only
(docs/deliveries/GROK-PLAN-BZG-BOM-YIELD-V1-2026-09-20.md).
Owner order KEEP BUILDING WITHOUT MATT. Lane bzg-bom-yield-v1 on
mission owner-autonomous-20260920-w10 after bzg-allocation-engine-v1 DONE
(62f4eca / 5006d1d). CR-bbabeb11ff864169 stays OPEN.
Bound beta-bzg-ops-safe.

Names the bom, yield, waste, theoretical_cost, menu_engineering, and notes slots
and leaves every slot empty. An empty framework is not live BOM/yield machinery
and not proof of recipe cost standards. This module does not invent BOM, yield,
waste, theoretical cost, or menu-engineering numbers. ESB remains transactional
SoT (read-only note only; no ESB mutate). It does not write Production, Alchemist,
Zayen books, a bank, a payment, Cloudflare, Access, the Model C ledger, or the
completion row. CAP-BZG-06 stays SPECIFIED. The ceiling label is BUILT. PROVEN
and READY are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "bzg_bom_yield.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-bbabeb11ff864169"
CAP_ID = "CAP-BZG-06"
SCHEMA_ID = "wolf.cap-bzg-06.bom-yield.v1"
BOUND = "beta-bzg-ops-safe"

_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "bom",
        "BOM",
        "Named bom slot. Empty is not a BOM and not live BOM/yield machinery.",
    ),
    (
        "yield",
        "Yield",
        "Named yield slot. Empty is not yield and not live BOM/yield machinery.",
    ),
    (
        "waste",
        "Waste",
        "Named waste slot. Empty is not waste and not proof of recipe cost standards.",
    ),
    (
        "theoretical_cost",
        "Theoretical cost",
        "Named theoretical_cost slot. Empty is not theoretical cost and not proof of recipe cost standards.",
    ),
    (
        "menu_engineering",
        "Menu engineering",
        "Named menu_engineering slot. Empty is not menu engineering and not proof of recipe cost standards.",
    ),
    (
        "notes",
        "Notes",
        "Named notes slot. Empty is not a recipe-cost note and not live BOM/yield machinery. ESB remains transactional SoT (read-only note only).",
    ),
)


def _empty_slot(kind: str, label: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "slot": "empty",
        "evidence": None,
        "bom": None,
        "yield": None,
        "waste": None,
        "theoretical_cost": None,
        "menu_engineering": None,
        "current": False,
        "live_bom_yield_machinery": False,
        "recipe_cost_standards": False,
        "esb_mutated": False,
        "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
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
    "An empty framework is not live BOM/yield machinery.",
    "An empty framework is not proof of recipe cost standards.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "BOM, yield, waste, theoretical cost, and menu-engineering numbers are not invented.",
    "ESB remains transactional SoT (read-only note only; no ESB mutate).",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-BZG-06 stays SPECIFIED.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "bzg_bom_yield_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_bom_yield_machinery": False,
    "empty_is_recipe_cost_standards": False,
    "empty_is_ready": False,
    "proved": False,
    "live_bom_yield_machinery": False,
    "recipe_cost_standards": False,
    "current": False,
    "bom": None,
    "yield": None,
    "waste": None,
    "theoretical_cost": None,
    "menu_engineering": None,
    "esb_mutated": False,
    "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
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
    "invented_bom": False,
    "invented_yield": False,
    "invented_waste": False,
    "invented_theoretical_cost": False,
    "invented_menu_engineering": False,
    "ledger_write": False,
}


class BomYieldError(ValueError):
    """Fail closed. Does not invent BOM/yield numbers or PROVEN."""

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
        raise BomYieldError(
            "BOM/yield framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise BomYieldError(
            "BOM/yield framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise BomYieldError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "esb" in name or "/esb/" in low or name.startswith("esb"):
        raise BomYieldError(
            "ESB is not mutated from this framework. ESB remains transactional SoT (read-only note only).",
            code="esb_refused",
        )
    # Do not match the empty skeleton filename bzg_bom_yield.sqlite itself.
    if resolved not in {DEFAULT_DB.resolve(), LIVE_DEFAULT_DB} and (
        name.startswith("bom")
        or name.startswith("yield")
        or name.startswith("waste")
        or name.startswith("theoretical")
        or name.startswith("menu")
        or name in {
            "bom-yield.sqlite",
            "live-bom.sqlite",
            "live_bom.sqlite",
            "recipe-cost.sqlite",
            "recipe_cost.sqlite",
        }
    ):
        raise BomYieldError(
            "BOM, yield, waste, theoretical cost, and menu-engineering numbers are not invented. Empty is not live BOM/yield machinery.",
            code="current_refused",
        )
    if "bank" in name:
        raise BomYieldError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise BomYieldError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise BomYieldError(
            "BOM/yield framework refuses a production path",
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
        raise BomYieldError(
            "BOM/yield framework refuses a path outside Beta or a test fixture",
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
    """Read CAP-BZG-06. Does not write the ledger."""
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
    """Read CR-bbabeb11ff864169. Does not upsert, resolve, or harvest."""
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
    flags["invented_bom"] = False
    flags["invented_yield"] = False
    flags["invented_waste"] = False
    flags["invented_theoretical_cost"] = False
    flags["invented_menu_engineering"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_bom_yield_machinery"] = False
    flags["empty_is_recipe_cost_standards"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_bom_yield_machinery"] = False
    flags["recipe_cost_standards"] = False
    flags["current"] = False
    flags["bom"] = None
    flags["yield"] = None
    flags["waste"] = None
    flags["theoretical_cost"] = None
    flags["menu_engineering"] = None
    flags["esb_mutated"] = False
    flags["esb_sot_note"] = "ESB remains transactional SoT (read-only note only; no ESB mutate)."
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
                "description": "Not accepted. A note would not be live BOM/yield machinery.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "bom_property": False,
        "yield_property": False,
        "waste_property": False,
        "theoretical_cost_property": False,
        "menu_engineering_property": False,
        "esb_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not live BOM/yield machinery."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_bom_yield_machinery": False,
        "empty_is_recipe_cost_standards": False,
        "empty_is_ready": False,
        "proved": False,
        "live_bom_yield_machinery": False,
        "recipe_cost_standards": False,
        "current": False,
        "bom": None,
        "yield": None,
        "waste": None,
        "theoretical_cost": None,
        "menu_engineering": None,
        "esb_mutated": False,
        "esb_sot_note": "ESB remains transactional SoT (read-only note only; no ESB mutate).",
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "invented_bom": False,
        "invented_yield": False,
        "invented_waste": False,
        "invented_theoretical_cost": False,
        "invented_menu_engineering": False,
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
    raise BomYieldError("Unknown BOM/yield slot.", code="not_found")


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
    raise BomYieldError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise BomYieldError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_esb(_body: dict | None = None) -> None:
    raise BomYieldError(
        "ESB is not mutated from this framework. ESB remains transactional SoT (read-only note only).",
        code="esb_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise BomYieldError(
        "BOM, yield, waste, theoretical cost, and menu-engineering numbers are not invented. Empty is not live BOM/yield machinery.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise BomYieldError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise BomYieldError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Resolving the completion row is refused. CR-bbabeb11ff864169 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise BomYieldError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise BomYieldError(
        "The framework stays empty. A filled slot would not be live BOM/yield machinery.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise BomYieldError(
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
            if token in {"esb", "esb-mutate", "esb-write"}:
                refuse_esb(payload)
            if token in {
                "bom",
                "yield",
                "waste",
                "theoretical-cost",
                "menu-engineering",
                "current",
                "live-bom",
                "recipe-cost",
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
    raise BomYieldError(
        "This framework does not store live BOM/yield machinery, BOM, yield, waste, theoretical cost, menu engineering, or an ESB mutation.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise BomYieldError(
            "BOM/yield framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise BomYieldError(
            "BOM/yield framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_BZG_BOM_YIELD") or "").strip() != "1":
            raise BomYieldError(
                "test mode refuses the live BOM/yield framework path",
                code="live_guard",
            )
    raise BomYieldError(
        "The framework stays empty. Empty is not live BOM/yield machinery.",
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


def invent_bom(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_yield(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_waste(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_theoretical_cost(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_menu_engineering(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def move_money(*_args: Any, **_kwargs: Any) -> None:
    refuse_payment({})


def mutate_esb(*_args: Any, **_kwargs: Any) -> None:
    refuse_esb({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    zayen: str | None = None,
    books: str | None = None,
    esb: str | None = None,
    bom: str | None = None,
    yield_: str | None = None,
    waste: str | None = None,
    theoretical_cost: str | None = None,
    menu_engineering: str | None = None,
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
    if _present(esb):
        refuse_esb({})
    if (
        _present(bom)
        or _present(yield_)
        or _present(waste)
        or _present(theoretical_cost)
        or _present(menu_engineering)
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
