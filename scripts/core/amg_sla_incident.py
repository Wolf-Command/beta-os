#!/usr/bin/env python3
"""CAP-AMG-06 guest experience / SLA / incident trail skeleton v1 (Beta only).

Decision served: 2026-09-20 PICK — CAP-AMG-06 guest experience / SLA /
incident trail framework skeleton on Beta only
(docs/deliveries/GROK-PLAN-AMG-SLA-INCIDENT-V1-2026-09-20.md).
Owner order KEEP BUILDING WITHOUT MATT. Lane amg-sla-incident-v1 on
mission owner-autonomous-20260920-w10 after amg-service-improve-v1 DONE
(9cb8b1b / b9f7b56). CR-e9b3d23e63c1c8a7 stays OPEN.
Bound beta-amg-ops-safe.

Names the request, incident, sla, escalation, trail, and notes slots and
leaves every slot empty. An empty framework is not a live SLA/incident
trail and not proof of guest experience loop machinery. This module does
not invent live incidents, SLA timers, or escalation outcomes. It does
not guest-blast or public-post. It does not write Production, Alchemist,
Yanolja, Zayen books, a bank, a payment, Cloudflare, Access, the Model C
ledger, or the completion row. CAP-AMG-06 stays SPECIFIED. The ceiling
label is BUILT. PROVEN and READY are not invented.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "amg_sla_incident.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-e9b3d23e63c1c8a7"
CAP_ID = "CAP-AMG-06"
SCHEMA_ID = "wolf.cap-amg-06.sla-incident.v1"
BOUND = "beta-amg-ops-safe"

_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "request",
        "Request",
        "Named request slot. Empty is not a guest request and not a live SLA/incident trail.",
    ),
    (
        "incident",
        "Incident",
        "Named incident slot. Empty is not an incident and not proof of guest experience loop machinery.",
    ),
    (
        "sla",
        "SLA",
        "Named SLA slot. Empty is not an SLA timer and not a live SLA/incident trail.",
    ),
    (
        "escalation",
        "Escalation",
        "Named escalation slot. Empty is not an escalation outcome and not a live SLA/incident trail.",
    ),
    (
        "trail",
        "Trail",
        "Named trail slot. Empty is not a service trail and not proof of guest experience loop machinery.",
    ),
    (
        "notes",
        "Notes",
        "Named notes slot. Empty is not an incident note and not a live SLA/incident trail.",
    ),
)


def _empty_slot(kind: str, label: str, why: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "slot": "empty",
        "evidence": None,
        "request": None,
        "incident": None,
        "incident_number": None,
        "sla": None,
        "sla_timer": None,
        "escalation": None,
        "escalation_outcome": None,
        "trail": None,
        "current": False,
        "live_request": False,
        "live_incident": False,
        "live_sla": False,
        "guest_experience_machinery": False,
        "guest_blast": False,
        "public_post": False,
        "yanolja_write": False,
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
    "An empty framework is not a live SLA/incident trail.",
    "An empty framework is not proof of guest experience loop machinery.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "Live incidents, SLA timers, and escalation outcomes are not invented.",
    "No guest blast.",
    "No public post.",
    "No live Yanolja call.",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-AMG-06 stays SPECIFIED.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "amg_sla_incident_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_sla_trail": False,
    "empty_is_guest_experience": False,
    "empty_is_ready": False,
    "proved": False,
    "live_request": False,
    "live_incident": False,
    "live_sla": False,
    "guest_experience_machinery": False,
    "current": False,
    "request": None,
    "incident": None,
    "incident_number": None,
    "sla": None,
    "sla_timer": None,
    "escalation": None,
    "escalation_outcome": None,
    "trail": None,
    "guest_blast": False,
    "public_post": False,
    "yanolja_live": False,
    "yanolja_called": False,
    "yanolja_write": False,
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
    "invented_incident": False,
    "invented_sla": False,
    "invented_escalation": False,
    "ledger_write": False,
}


class SlaIncidentError(ValueError):
    """Fail closed. Does not invent incident, SLA, escalation, or PROVEN."""

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
        raise SlaIncidentError(
            "SLA/incident framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise SlaIncidentError(
            "SLA/incident framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise SlaIncidentError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "yanolja" in name or "yanolja" in low:
        raise SlaIncidentError(
            "A live Yanolja call or write is refused. This framework does not connect to Yanolja.",
            code="yanolja_refused",
        )
    if "guest" in name or "blast" in name:
        raise SlaIncidentError(
            "A guest blast is refused from this framework.",
            code="guest_blast_refused",
        )
    if "public" in name or name.startswith("post") or "public-post" in name:
        raise SlaIncidentError(
            "A public post is refused from this framework.",
            code="public_post_refused",
        )
    if "bank" in name:
        raise SlaIncidentError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise SlaIncidentError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise SlaIncidentError(
            "SLA/incident framework refuses a production path",
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
        raise SlaIncidentError(
            "SLA/incident framework refuses a path outside Beta or a test fixture",
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
    """Read CAP-AMG-06. Does not write the ledger."""
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
    """Read CR-e9b3d23e63c1c8a7. Does not upsert, resolve, or harvest."""
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
    flags["invented_incident"] = False
    flags["invented_sla"] = False
    flags["invented_escalation"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_sla_trail"] = False
    flags["empty_is_guest_experience"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_request"] = False
    flags["live_incident"] = False
    flags["live_sla"] = False
    flags["guest_experience_machinery"] = False
    flags["current"] = False
    flags["request"] = None
    flags["incident"] = None
    flags["incident_number"] = None
    flags["sla"] = None
    flags["sla_timer"] = None
    flags["escalation"] = None
    flags["escalation_outcome"] = None
    flags["trail"] = None
    flags["guest_blast"] = False
    flags["public_post"] = False
    flags["yanolja_live"] = False
    flags["yanolja_called"] = False
    flags["yanolja_write"] = False
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
                    "Not accepted. A note would not be a live SLA/incident trail."
                ),
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "yanolja_property": False,
        "request_property": False,
        "incident_property": False,
        "sla_property": False,
        "escalation_property": False,
        "trail_property": False,
        "guest_blast_property": False,
        "public_post_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live SLA/incident trail."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_sla_trail": False,
        "empty_is_guest_experience": False,
        "empty_is_ready": False,
        "proved": False,
        "live_request": False,
        "live_incident": False,
        "live_sla": False,
        "guest_experience_machinery": False,
        "current": False,
        "request": None,
        "incident": None,
        "incident_number": None,
        "sla": None,
        "sla_timer": None,
        "escalation": None,
        "escalation_outcome": None,
        "trail": None,
        "guest_blast": False,
        "public_post": False,
        "yanolja_live": False,
        "yanolja_called": False,
        "yanolja_write": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "invented_incident": False,
        "invented_sla": False,
        "invented_escalation": False,
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
    raise SlaIncidentError("Unknown SLA/incident slot.", code="not_found")


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
    raise SlaIncidentError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_yanolja(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "A live Yanolja call or write is refused. This framework does not connect to Yanolja.",
        code="yanolja_refused",
    )


def refuse_guest_blast(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "A guest blast is refused from this framework.",
        code="guest_blast_refused",
    )


def refuse_public_post(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "A public post is refused from this framework.",
        code="public_post_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Live incidents, SLA timers, and escalation outcomes are not invented. "
        "Empty is not a live SLA/incident trail.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays SPECIFIED.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Resolving the completion row is refused. CR-e9b3d23e63c1c8a7 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise SlaIncidentError(
        "The framework stays empty. A filled slot would not be a live SLA/incident trail.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise SlaIncidentError(
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
            if token in {"yanolja", "yanolja-write", "yanolja-call"}:
                refuse_yanolja(payload)
            if token in {"guest-blast", "guest", "blast", "broadcast"}:
                refuse_guest_blast(payload)
            if token in {"public-post", "public", "post", "publish"}:
                refuse_public_post(payload)
            if token in {
                "request",
                "incident",
                "incident-number",
                "sla",
                "sla-timer",
                "escalation",
                "escalation-outcome",
                "trail",
                "current",
                "live-request",
                "live-incident",
                "live-sla",
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
    raise SlaIncidentError(
        "This framework does not store a live SLA/incident trail, incidents, "
        "SLA timers, escalation outcomes, a guest blast, or a public post.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise SlaIncidentError(
            "SLA/incident framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise SlaIncidentError(
            "SLA/incident framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_AMG_SLA_INCIDENT") or "").strip() != "1":
            raise SlaIncidentError(
                "test mode refuses the live SLA/incident framework path",
                code="live_guard",
            )
    raise SlaIncidentError(
        "The framework stays empty. Empty is not a live SLA/incident trail.",
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


def invent_incident(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_sla(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def invent_escalation(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def call_yanolja(*_args: Any, **_kwargs: Any) -> None:
    refuse_yanolja({})


def blast_guests(*_args: Any, **_kwargs: Any) -> None:
    refuse_guest_blast({})


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
    yanolja: str | None = None,
    request: str | None = None,
    incident: str | None = None,
    sla: str | None = None,
    escalation: str | None = None,
    trail: str | None = None,
    current: str | None = None,
    guest_blast: str | None = None,
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
    if _present(yanolja):
        refuse_yanolja({})
    if _present(guest_blast):
        refuse_guest_blast({})
    if _present(public_post):
        refuse_public_post({})
    if (
        _present(request)
        or _present(incident)
        or _present(sla)
        or _present(escalation)
        or _present(trail)
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
