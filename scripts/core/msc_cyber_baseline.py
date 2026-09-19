#!/usr/bin/env python3
"""CAP-MSC-04 cybersecurity baseline skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-MSC-CYBER-BASELINE-V1-2026-09-20.md.
CR-7dae8b389cce6f9a stays OPEN. Owner lane msc-cyber-baseline-v1.
Wave-7 after msc-compliance-pack-v1 6561ac6.
intel-learning-policy-v1 stays parked.

Names the MFA, device posture, and audited-access slots and leaves every
slot empty. An empty baseline is not proof of security. MFA and device
posture are not invented as current. This module does not write Production,
Alchemist, Cloudflare, Access, the Model C ledger, or the completion row.
CAP-MSC-04 stays at the ledger value. The ceiling label is BUILT unless
the ledger is already PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "msc_cyber_baseline.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-7dae8b389cce6f9a"
CAP_ID = "CAP-MSC-04"
SCHEMA_ID = "wolf.cap-msc-04.cyber-baseline.v1"

KIND_IDS = ("mfa", "device-posture", "audited-access")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "mfa",
        "label": "MFA",
        "slot": "empty",
        "evidence": None,
        "mfa_status": None,
        "device_posture": None,
        "audited_access": None,
        "current": False,
        "security_proved": False,
        "payment": None,
        "why": "Named MFA slot. Empty is not current MFA and not proof of security.",
    },
    {
        "kind": "device-posture",
        "label": "Device posture",
        "slot": "empty",
        "evidence": None,
        "mfa_status": None,
        "device_posture": None,
        "audited_access": None,
        "current": False,
        "security_proved": False,
        "payment": None,
        "why": "Named device posture slot. Empty is not current posture and not proof of security.",
    },
    {
        "kind": "audited-access",
        "label": "Audited access",
        "slot": "empty",
        "evidence": None,
        "mfa_status": None,
        "device_posture": None,
        "audited_access": None,
        "current": False,
        "security_proved": False,
        "payment": None,
        "why": "Named audited-access slot. Empty is not an access audit and not proof of security.",
    },
)

GAPS: tuple[str, ...] = (
    "The baseline is empty.",
    "An empty baseline is not proof of security.",
    "MFA is not invented as current.",
    "Device posture is not invented as current.",
    "Audited access is not invented as current.",
    "No payment is stored.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-MSC-04 stays at the ledger value.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "msc_cyber_baseline_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_security": False,
    "security_proved": False,
    "mfa_status": None,
    "device_posture": None,
    "audited_access": None,
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


class CyberBaselineError(ValueError):
    """Fail closed. Does not invent security, current MFA, or PROVEN."""

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
        raise CyberBaselineError(
            "cyber baseline refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise CyberBaselineError(
            "cyber baseline refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise CyberBaselineError(
            "cyber baseline refuses a production path",
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
        raise CyberBaselineError(
            "cyber baseline refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-MSC-04. Does not write the ledger."""
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
    """Read CR-7dae8b389cce6f9a. Does not upsert, resolve, or harvest."""
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
    flags["empty_is_security"] = False
    flags["security_proved"] = False
    flags["mfa_status"] = None
    flags["device_posture"] = None
    flags["audited_access"] = None
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
        "mfa_status_property": False,
        "device_posture_property": False,
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
                "empty_is_security": False,
                "security_proved": False,
                "mfa_status": None,
                "device_posture": None,
                "audited_access": None,
                "current": False,
                "payment": None,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise CyberBaselineError("Unknown baseline slot.", code="not_found")


def build_baseline(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a baseline file."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_security": False,
        "recorded_count": 0,
        "security_proved": False,
        "mfa_status": None,
        "device_posture": None,
        "audited_access": None,
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
    raise CyberBaselineError(
        "A payment is not stored on this baseline. No amount is kept.",
        code="payment_refused",
    )


def refuse_posture(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "MFA and device posture are not invented as current. Empty is not proof of security.",
        code="posture_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "Cloudflare is not mutated from this baseline.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "Access is not mutated from this baseline.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "READY is refused. This baseline does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "Resolving the completion row is refused. CR-7dae8b389cce6f9a stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise CyberBaselineError(
        "The baseline stays empty. A filled slot would not be proof of security.",
        code="slots_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {
                "mfa",
                "mfa-status",
                "device-posture",
                "device-posture-status",
                "posture",
                "current",
                "enrolled",
            }:
                refuse_posture(payload)
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
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "audited-access",
            }:
                refuse_fill(payload)
    raise CyberBaselineError(
        "This baseline does not store evidence, a payment, or current MFA.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise CyberBaselineError(
            "cyber baseline does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_MSC_CYBER") or "").strip() != "1":
            raise CyberBaselineError(
                "test mode refuses the live cyber baseline path",
                code="live_guard",
            )
    raise CyberBaselineError(
        "The baseline stays empty. Empty is not proof of security.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_posture({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    mfa: str | None = None,
    mfa_status: str | None = None,
    device_posture: str | None = None,
    posture: str | None = None,
    current: str | None = None,
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
    if (
        _present(mfa)
        or _present(mfa_status)
        or _present(device_posture)
        or _present(posture)
        or _present(current)
    ):
        refuse_posture({})
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
