#!/usr/bin/env python3
"""CAP-MSC-03 compliance pack skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-MSC-COMPLIANCE-PACK-V1-2026-09-20.md.
CR-1f93c785c88e9564 stays OPEN. Owner lane msc-compliance-pack-v1.
Wave-7 after msc-asset-register-v1 49aa4df.
intel-learning-policy-v1 stays parked.

Names the licence, statutory, and policy slots and leaves every slot empty.
An empty pack is not proof of compliance. A licence status is not invented
as current. This module does not write Production, Alchemist, Cloudflare,
Access, the Model C ledger, or the completion row. CAP-MSC-03 stays at the
ledger value. The ceiling label is BUILT unless the ledger is already
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
DEFAULT_DB = BETA_ROOT / "catalog" / "msc_compliance_pack.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-1f93c785c88e9564"
CAP_ID = "CAP-MSC-03"
SCHEMA_ID = "wolf.cap-msc-03.compliance-pack.v1"

KIND_IDS = ("licence", "statutory", "policy")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "licence",
        "label": "Licence",
        "slot": "empty",
        "evidence": None,
        "licence_status": None,
        "current": False,
        "compliance_proved": False,
        "payment": None,
        "why": "Named licence slot. Empty is not a current licence and not proof of compliance.",
    },
    {
        "kind": "statutory",
        "label": "Statutory",
        "slot": "empty",
        "evidence": None,
        "licence_status": None,
        "current": False,
        "compliance_proved": False,
        "payment": None,
        "why": "Named statutory slot. Empty is not a filing and not proof of compliance.",
    },
    {
        "kind": "policy",
        "label": "Policy",
        "slot": "empty",
        "evidence": None,
        "licence_status": None,
        "current": False,
        "compliance_proved": False,
        "payment": None,
        "why": "Named policy slot. Empty is not a policy in force and not proof of compliance.",
    },
)

GAPS: tuple[str, ...] = (
    "The pack is empty.",
    "An empty pack is not proof of compliance.",
    "A licence status is not invented as current.",
    "No payment is stored.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-MSC-03 stays at the ledger value.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "msc_compliance_pack_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_compliance": False,
    "compliance_proved": False,
    "licence_status": None,
    "current": False,
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
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class CompliancePackError(ValueError):
    """Fail closed. Does not invent compliance, a current licence, or PROVEN."""

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
        raise CompliancePackError(
            "compliance pack refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise CompliancePackError(
            "compliance pack refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise CompliancePackError(
            "compliance pack refuses a production path",
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
        raise CompliancePackError(
            "compliance pack refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-MSC-03. Does not write the ledger."""
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
    """Read CR-1f93c785c88e9564. Does not upsert, resolve, or harvest."""
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
    flags["empty_is_compliance"] = False
    flags["compliance_proved"] = False
    flags["licence_status"] = None
    flags["current"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
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
                "description": "Not accepted. A note would not be proof.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "licence_status_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not proof."""
    return [dict(row) for row in EVIDENCE_KINDS]


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                "empty": True,
                "empty_is_compliance": False,
                "compliance_proved": False,
                "licence_status": None,
                "current": False,
                "payment": None,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise CompliancePackError("Unknown evidence slot.", code="not_found")


def build_pack(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a pack file."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_compliance": False,
        "recorded_count": 0,
        "compliance_proved": False,
        "licence_status": None,
        "current": False,
        "payment": None,
        "money": None,
        "cloudflare_mutated": False,
        "access_mutated": False,
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
    raise CompliancePackError(
        "A payment is not stored on this pack. No amount is kept.",
        code="payment_refused",
    )


def refuse_licence_status(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "A licence status is not invented as current. Empty is not proof of compliance.",
        code="licence_status_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "Cloudflare is not mutated from this pack.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "Access is not mutated from this pack.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "READY is refused. This pack does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "Resolving the completion row is refused. CR-1f93c785c88e9564 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise CompliancePackError(
        "The pack stays empty. A filled slot would not be proof of compliance.",
        code="slots_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower()
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"licence_status", "license_status", "current", "compliant", "licensed", "valid"}:
                refuse_licence_status(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf_access", "zero_trust"}:
                refuse_access(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr_resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production_mutate"}:
                refuse_production(payload)
            if token in {"fill", "note", "evidence", "evidence_note", "slots_filled"}:
                refuse_fill(payload)
    raise CompliancePackError(
        "This pack does not store evidence, a payment, or a current licence.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise CompliancePackError(
            "compliance pack does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_MSC_COMPLIANCE") or "").strip() != "1":
            raise CompliancePackError(
                "test mode refuses the live compliance pack path",
                code="live_guard",
            )
    raise CompliancePackError(
        "The pack stays empty. Empty is not proof of compliance.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_licence_status({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    licence_status: str | None = None,
    current: str | None = None,
    compliant: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
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
    if _present(licence_status) or _present(current) or _present(compliant):
        refuse_licence_status({})
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
    if _present(write):
        refuse_external_write({})
