#!/usr/bin/env python3
"""CAP-INTG-01 connector contract/tests framework skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-INTG-CONNECTOR-CONTRACT-V1-2026-09-20.md
and the same-day PICK in decisions.md.
CR-227e2514ac8dcd02 stays OPEN. Owner lane intg-connector-contract-v1.
Mission owner-autonomous-20260920-w8 after msc-posture-prove-v1 DONE
(01858ec / 463d84a). intel-learning-policy-v1 stays parked.

Names the contract, fixture, and refuse slots and leaves every slot empty.
An empty framework is not a live connector prove and not Yanolja or ESB.
This module does not call Yanolja, does not call ESB, and does not write
Production, Alchemist, Cloudflare, Access, the Model C ledger, or the
completion row. CAP-INTG-01 stays ABSENT. The ceiling label is BUILT
unless the ledger is already PROVEN or READY. SPECIFIED, PROVEN, and READY
are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "intg_connector_contract.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-227e2514ac8dcd02"
CAP_ID = "CAP-INTG-01"
SCHEMA_ID = "wolf.cap-intg-01.connector-contract.v1"

KIND_IDS = ("contract", "fixture", "refuse")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "contract",
        "label": "Contract",
        "slot": "empty",
        "evidence": None,
        "contract": None,
        "fixture": None,
        "current": False,
        "proved": False,
        "payment": None,
        "yanolja_called": False,
        "esb_called": False,
        "why": "Named contract slot. Empty is not a connector contract and not a live prove.",
    },
    {
        "kind": "fixture",
        "label": "Fixture",
        "slot": "empty",
        "evidence": None,
        "contract": None,
        "fixture": None,
        "current": False,
        "proved": False,
        "payment": None,
        "yanolja_called": False,
        "esb_called": False,
        "why": "Named fixture slot. Empty is not a test fixture and not a live prove.",
    },
    {
        "kind": "refuse",
        "label": "Refuse",
        "slot": "empty",
        "evidence": None,
        "contract": None,
        "fixture": None,
        "current": False,
        "proved": False,
        "payment": None,
        "yanolja_called": False,
        "esb_called": False,
        "why": "Named refuse slot. Empty is not a live refuse of Yanolja or ESB.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live connector prove.",
    "An empty framework is not Yanolja.",
    "An empty framework is not ESB.",
    "An empty framework is not READY.",
    "SPECIFIED is not invented.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "No live Yanolja call.",
    "No live ESB call.",
    "No payment is stored.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-INTG-01 stays ABSENT.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "intg_connector_contract_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_prove": False,
    "empty_is_ready": False,
    "empty_is_yanolja": False,
    "empty_is_esb": False,
    "proved": False,
    "live_connector": False,
    "current": False,
    "contract": None,
    "fixture": None,
    "yanolja_called": False,
    "esb_called": False,
    "payment": None,
    "money": None,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_specified": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class ConnectorContractError(ValueError):
    """Fail closed. Does not invent a connector, Yanolja, ESB, or PROVEN."""

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
    if "alchemist" in low:
        raise ConnectorContractError(
            "connector contract refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise ConnectorContractError(
            "connector contract refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise ConnectorContractError(
            "connector contract refuses a production path",
            code="not_beta",
        )
    name = resolved.name.lower()
    if "esb" in name:
        raise ConnectorContractError(
            "A live ESB call is refused. An empty framework is not ESB.",
            code="esb_refused",
        )
    if "yanolja" in name:
        raise ConnectorContractError(
            "A live Yanolja call is refused. An empty framework is not Yanolja.",
            code="yanolja_refused",
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
        raise ConnectorContractError(
            "connector contract refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-INTG-01. Does not write the ledger."""
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
    """Read CR-227e2514ac8dcd02. Does not upsert, resolve, or harvest."""
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
    flags["specified"] = state == "SPECIFIED"
    flags["absent"] = state == "ABSENT"
    flags["invented_specified"] = False
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_prove"] = False
    flags["empty_is_ready"] = False
    flags["empty_is_yanolja"] = False
    flags["empty_is_esb"] = False
    flags["proved"] = False
    flags["live_connector"] = False
    flags["current"] = False
    flags["contract"] = None
    flags["fixture"] = None
    flags["yanolja_called"] = False
    flags["esb_called"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["on_disk"] = False
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
                "description": "Not accepted. A note would not be a live connector prove.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "yanolja_property": False,
        "esb_property": False,
        "contract_property": False,
        "fixture_property": False,
        "specified_property": False,
        "cloudflare_property": False,
        "access_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live connector prove."""
    return [dict(row) for row in EVIDENCE_KINDS]


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                "empty": True,
                "empty_is_prove": False,
                "empty_is_ready": False,
                "empty_is_yanolja": False,
                "empty_is_esb": False,
                "proved": False,
                "live_connector": False,
                "current": False,
                "contract": None,
                "fixture": None,
                "yanolja_called": False,
                "esb_called": False,
                "payment": None,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise ConnectorContractError("Unknown connector slot.", code="not_found")


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a framework file."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_prove": False,
        "empty_is_ready": False,
        "empty_is_yanolja": False,
        "empty_is_esb": False,
        "recorded_count": 0,
        "proved": False,
        "live_connector": False,
        "current": False,
        "contract": None,
        "fixture": None,
        "yanolja_called": False,
        "esb_called": False,
        "payment": None,
        "money": None,
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
    raise ConnectorContractError(
        "A payment is not stored on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_yanolja(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "A live Yanolja call is refused. An empty framework is not Yanolja.",
        code="yanolja_refused",
    )


def refuse_esb(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "A live ESB call is refused. An empty framework is not ESB.",
        code="esb_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_specified(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "SPECIFIED is refused. The ceiling label is BUILT. The live ledger stays ABSENT.",
        code="specified_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "Resolving the completion row is refused. CR-227e2514ac8dcd02 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise ConnectorContractError(
        "The framework stays empty. A filled slot would not be a live connector prove.",
        code="slots_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"yanolja", "live-yanolja"}:
                refuse_yanolja(payload)
            if token in {"esb", "live-esb"}:
                refuse_esb(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf-access", "zero-trust"}:
                refuse_access(payload)
            if token in {"specified", "specify"}:
                refuse_specified(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr-resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production-mutate"}:
                refuse_production(payload)
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "contract",
                "fixture",
                "connector",
                "refuse",
            }:
                refuse_fill(payload)
    raise ConnectorContractError(
        "This framework does not store a contract, a fixture, a payment, or a live connector.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise ConnectorContractError(
            "connector contract does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_INTG_CONNECTOR") or "").strip() != "1":
            raise ConnectorContractError(
                "test mode refuses the live connector contract path",
                code="live_guard",
            )
    raise ConnectorContractError(
        "The framework stays empty. Empty is not a live connector prove.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_specified(*_args: Any, **_kwargs: Any) -> None:
    refuse_specified({})


def call_yanolja(*_args: Any, **_kwargs: Any) -> None:
    refuse_yanolja({})


def call_esb(*_args: Any, **_kwargs: Any) -> None:
    refuse_esb({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    yanolja: str | None = None,
    esb: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    specified: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(yanolja):
        refuse_yanolja({})
    if _present(esb):
        refuse_esb({})
    if _present(cloudflare):
        refuse_cloudflare({})
    if _present(access):
        refuse_access({})
    if _present(specified):
        refuse_specified({})
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
    if _present(write):
        refuse_external_write({})
