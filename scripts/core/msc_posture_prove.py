#!/usr/bin/env python3
"""CAP-MSC-02 automated posture prove framework skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-MSC-POSTURE-PROVE-V1-2026-09-20.md.
CR-80296d7bc9c35452 stays OPEN. Owner lane msc-posture-prove-v1.
Mission owner-autonomous-20260920-w8 after wave-7 ggv-client-profitability-v1
1af6c36. intel-learning-policy-v1 stays parked.

Names the posture, control, and evidence slots and leaves every slot empty.
An empty framework is not a prove and not READY. A live posture score is
not invented as current. This module does not write Production, Alchemist,
Cloudflare, Access, the Model C ledger, or the completion row.
CAP-MSC-02 stays at the ledger value. The ceiling label is BUILT unless
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
DEFAULT_DB = BETA_ROOT / "catalog" / "msc_posture_prove.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-80296d7bc9c35452"
CAP_ID = "CAP-MSC-02"
SCHEMA_ID = "wolf.cap-msc-02.posture-prove.v1"

KIND_IDS = ("posture", "control", "evidence")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "posture",
        "label": "Posture",
        "slot": "empty",
        "evidence": None,
        "posture_score": None,
        "control": None,
        "current": False,
        "proved": False,
        "payment": None,
        "why": "Named posture slot. Empty is not a live posture score and not a prove.",
    },
    {
        "kind": "control",
        "label": "Control",
        "slot": "empty",
        "evidence": None,
        "posture_score": None,
        "control": None,
        "current": False,
        "proved": False,
        "payment": None,
        "why": "Named control slot. Empty is not a control and not a prove.",
    },
    {
        "kind": "evidence",
        "label": "Evidence",
        "slot": "empty",
        "evidence": None,
        "posture_score": None,
        "control": None,
        "current": False,
        "proved": False,
        "payment": None,
        "why": "Named evidence slot. Empty is not stored evidence and not a prove.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a prove.",
    "An empty framework is not READY.",
    "A live posture score is not invented as current.",
    "Control is not invented as current.",
    "Evidence is not stored.",
    "No payment is stored.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-MSC-02 stays at the ledger value.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "msc_posture_prove_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_prove": False,
    "empty_is_ready": False,
    "proved": False,
    "posture_score": None,
    "current": False,
    "control": None,
    "evidence": None,
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


class PostureProveError(ValueError):
    """Fail closed. Does not invent a prove, a live score, or PROVEN."""

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
        raise PostureProveError(
            "posture prove refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise PostureProveError(
            "posture prove refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise PostureProveError(
            "posture prove refuses a production path",
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
        raise PostureProveError(
            "posture prove refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-MSC-02. Does not write the ledger."""
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
    """Read CR-80296d7bc9c35452. Does not upsert, resolve, or harvest."""
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
    flags["empty_is_prove"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["posture_score"] = None
    flags["current"] = False
    flags["control"] = None
    flags["evidence"] = None
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
                "description": "Not accepted. A note would not be a prove.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "posture_score_property": False,
        "current_property": False,
        "control_property": False,
        "evidence_property": False,
        "cloudflare_property": False,
        "access_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a prove."""
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
                "proved": False,
                "posture_score": None,
                "current": False,
                "control": None,
                "evidence": None,
                "payment": None,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise PostureProveError("Unknown posture slot.", code="not_found")


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
        "recorded_count": 0,
        "proved": False,
        "posture_score": None,
        "current": False,
        "control": None,
        "evidence": None,
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
    raise PostureProveError(
        "A payment is not stored on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise PostureProveError(
        "A live posture score is not invented as current. Empty is not a prove.",
        code="score_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise PostureProveError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise PostureProveError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise PostureProveError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise PostureProveError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise PostureProveError(
        "Resolving the completion row is refused. CR-80296d7bc9c35452 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise PostureProveError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise PostureProveError(
        "The framework stays empty. A filled slot would not be a prove.",
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
                "score",
                "posture-score",
                "live-score",
                "current",
                "posture",
            }:
                refuse_score(payload)
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
                "control",
            }:
                refuse_fill(payload)
    raise PostureProveError(
        "This framework does not store evidence, a payment, or a live posture score.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise PostureProveError(
            "posture prove does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_MSC_POSTURE") or "").strip() != "1":
            raise PostureProveError(
                "test mode refuses the live posture prove path",
                code="live_guard",
            )
    raise PostureProveError(
        "The framework stays empty. Empty is not a prove.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_score({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    score: str | None = None,
    posture_score: str | None = None,
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
    if _present(score) or _present(posture_score) or _present(current):
        refuse_score({})
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
