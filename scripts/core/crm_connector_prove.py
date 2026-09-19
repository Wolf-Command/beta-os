#!/usr/bin/env python3
"""CAP-CRM-04 honest connector prove (Beta, read-only).

Decision served: 2026-09-19 plan
docs/deliveries/GROK-PLAN-CRM-CONNECTOR-HONEST-PROVE-2026-09-19.md.
CR-c8719063fb940ed4 next action is Honest connector prove. Owner lane
crm-connector-honest-prove. Wave-5 after DR failure-domains 9209284.

Names Klaviyo and ActiveCampaign as different connectors and documents
brand scopes. It does not import the Habitat reader, send mail, write an
external CRM, or invent PROVEN or READY. CAP-CRM-04 stays at the ledger
value. The ceiling is BUILT unless the ledger is already PROVEN or READY.
The CR is not resolved.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

CR_ID = "CR-c8719063fb940ed4"
CAP_ID = "CAP-CRM-04"
SCHEMA_ID = "wolf.cap-crm-04.connector-honest-log.v1"
NOT_RUN = "NOT_RUN"
EMPTY = "EMPTY"
DOCUMENTED = "DOCUMENTED"
ABSENT = "ABSENT"
REFUSED = "REFUSED"

KLAVIYO_READER_REL = "scripts/core/habitat_klaviyo_reader.py"
AC_READER_REL = "scripts/core/activecampaign_reader.py"

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

LOG_FIELDS = (
    "schema_id",
    "cap",
    "prove_id",
    "recorded_at",
    "status",
    "klaviyo_called",
    "ac_called",
    "conflated",
    "send",
    "external_crm_write",
    "klaviyo_write",
    "ac_write",
    "metricool_write",
    "production_mutated",
    "cr_resolved",
    "ready_claimed",
    "proven_claimed",
    "slots_filled",
    "sends",
    "subscribers",
    "profiles_inserted",
    "checklist",
    "connectors",
    "brands",
    "gaps",
    "result",
)

STEP_FIELDS = (
    "id",
    "order",
    "required",
    "title",
    "detail",
    "executed",
    "result",
    "slot",
)

_SUCCESS_STATUS = frozenset({
    "SUCCESS",
    "SENT",
    "PASS",
    "PASSED",
    "OK",
    "DONE",
    "COMPLETE",
    "COMPLETED",
    "PROVED",
    "WIRED",
    "LIVE",
})

CHECKLIST: tuple[dict[str, Any], ...] = (
    {
        "id": "CHK-NAME-KLAVIYO",
        "order": 1,
        "required": True,
        "title": "Name Klaviyo as its own connector",
        "detail": (
            "Klaviyo is a named connector. Naming it is not a live call "
            "and not a send."
        ),
    },
    {
        "id": "CHK-NAME-ACTIVECAMPAIGN",
        "order": 2,
        "required": True,
        "title": "Name ActiveCampaign as a different connector",
        "detail": "ActiveCampaign is not Klaviyo. Naming it is not a reader and not a send.",
    },
    {
        "id": "CHK-NOT-CONFLATED",
        "order": 3,
        "required": True,
        "title": "Keep Klaviyo and ActiveCampaign distinct",
        "detail": "A payload that marks them as the same connector is refused. This prove does not conflate them.",
    },
    {
        "id": "CHK-BRAND-SCOPES",
        "order": 4,
        "required": True,
        "title": "Document brand scopes without counting",
        "detail": (
            "Habitat is the only brand named on the Klaviyo reader. "
            "Other brands are ABSENT. Absence is not zero subscribers."
        ),
    },
    {
        "id": "CHK-DOCUMENT-GAPS",
        "order": 5,
        "required": True,
        "title": "Document the gaps",
        "detail": (
            "The ActiveCampaign reader is absent. The Klaviyo file is not called. "
            "A gap is not a send count."
        ),
    },
    {
        "id": "CHK-NO-SEND",
        "order": 6,
        "required": True,
        "title": "Do not send",
        "detail": "No campaign, no blast, and no transactional send. A refused send is not zero sends.",
    },
    {
        "id": "CHK-NO-KLAVIYO-CALL",
        "order": 7,
        "required": True,
        "title": "Do not call Klaviyo",
        "detail": "The Habitat reader file is not imported. No page is fetched. No profile is inserted.",
    },
    {
        "id": "CHK-NO-CRM-WRITE",
        "order": 8,
        "required": True,
        "title": "Do not write an external CRM",
        "detail": "No Klaviyo write, no ActiveCampaign write, and no Metricool write.",
    },
    {
        "id": "CHK-NO-PRODUCTION",
        "order": 9,
        "required": True,
        "title": "Do not write Production",
        "detail": "No write to Production or a production path.",
    },
    {
        "id": "CHK-NO-RESOLVE",
        "order": 10,
        "required": True,
        "title": "Do not resolve the CR or raise maturity",
        "detail": (
            "CAP-CRM-04 stays at the ledger value. The ceiling is BUILT unless "
            "the ledger is already higher. The CR stays open."
        ),
    },
)

CONNECTORS: tuple[dict[str, Any], ...] = (
    {
        "id": "CONN-KLAVIYO",
        "name": "Klaviyo",
        "order": 1,
        "source_system": "klaviyo",
        "not_same_as": ("CONN-ACTIVECAMPAIGN",),
        "brand_scope": ("habitat",),
        "entity_scope": ("ENT-GGV",),
        "reader_relpath": KLAVIYO_READER_REL,
        "role": "Habitat-named reader file. Not ActiveCampaign. Not called by this prove.",
    },
    {
        "id": "CONN-ACTIVECAMPAIGN",
        "name": "ActiveCampaign",
        "order": 2,
        "source_system": "activecampaign",
        "not_same_as": ("CONN-KLAVIYO",),
        "brand_scope": (),
        "entity_scope": (),
        "reader_relpath": AC_READER_REL,
        "role": "Named separately. No reader is part of this prove. Not Klaviyo.",
    },
)

BRANDS: tuple[dict[str, Any], ...] = (
    {
        "id": "BRAND-HABITAT",
        "brand_id": "habitat",
        "order": 1,
        "entity_id": "ENT-GGV",
        "klaviyo_scope": DOCUMENTED,
        "activecampaign_scope": ABSENT,
        "why": (
            "Habitat is the brand named on the Klaviyo reader mission, entity ENT-GGV. "
            "This prove does not open that module and does not read leads. "
            "Documented is not a live wire. ActiveCampaign is ABSENT, not zero."
        ),
    },
    {
        "id": "BRAND-UMABLU",
        "brand_id": "umablu",
        "order": 2,
        "entity_id": None,
        "klaviyo_scope": ABSENT,
        "activecampaign_scope": ABSENT,
        "why": "No Uma Blu email-marketing reader is named here. Absence is not zero subscribers.",
    },
    {
        "id": "BRAND-ATRIUM",
        "brand_id": "atrium",
        "order": 3,
        "entity_id": None,
        "klaviyo_scope": ABSENT,
        "activecampaign_scope": ABSENT,
        "why": (
            "Atrium lead sync is not this connector and is not opened. "
            "Absence is not zero subscribers."
        ),
    },
    {
        "id": "BRAND-SELO",
        "brand_id": "selo",
        "order": 4,
        "entity_id": None,
        "klaviyo_scope": ABSENT,
        "activecampaign_scope": ABSENT,
        "why": "No Selo email-marketing reader is named here. Absence is not zero subscribers.",
    },
    {
        "id": "BRAND-TROPIK",
        "brand_id": "tropik",
        "order": 5,
        "entity_id": None,
        "klaviyo_scope": ABSENT,
        "activecampaign_scope": ABSENT,
        "why": "No Tropik email-marketing reader is named here. Absence is not zero subscribers.",
    },
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "crm_connector_prove",
    "read_only": True,
    "external_writes": False,
    "external_crm_write": False,
    "production": False,
    "production_mutated": False,
    "alchemist_write": False,
    "network_calls": False,
    "klaviyo_called": False,
    "ac_called": False,
    "conflated": False,
    "send": False,
    "klaviyo_write": False,
    "ac_write": False,
    "metricool_write": False,
    "cr_mutated": False,
    "cr_resolved": False,
    "score_changed": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "slots_filled": False,
    "sends": None,
    "subscribers": None,
    "profiles_inserted": None,
    "evidence_invented": False,
    "anon_fail_closed": True,
}


class ConnectorProveError(ValueError):
    """Fail closed. Does not send, conflate connectors, or raise maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_send(_body: dict | None = None) -> None:
    """A send is not this slice. Refused is not a count of zero."""
    raise ConnectorProveError(
        "Send is refused. This prove does not send mail and does not invent a send count.",
        code="send_refused",
    )


def refuse_klaviyo_write(_body: dict | None = None) -> None:
    """Klaviyo is not called and not written."""
    raise ConnectorProveError(
        "Klaviyo write is refused. The reader is not called and no profile is inserted.",
        code="klaviyo_write_refused",
    )


def refuse_ac_write(_body: dict | None = None) -> None:
    """ActiveCampaign is not called and not written."""
    raise ConnectorProveError(
        "ActiveCampaign write is refused. ActiveCampaign is not Klaviyo and is not called.",
        code="ac_write_refused",
    )


def refuse_crm_write(_body: dict | None = None) -> None:
    """No external CRM write."""
    raise ConnectorProveError(
        "External CRM write is refused.",
        code="crm_write_refused",
    )


def refuse_metricool(_body: dict | None = None) -> None:
    """Metricool is not written."""
    raise ConnectorProveError(
        "Metricool write is refused.",
        code="metricool_write_refused",
    )


def refuse_conflate(_body: dict | None = None) -> None:
    """Klaviyo and ActiveCampaign stay different names."""
    raise ConnectorProveError(
        "Conflating Klaviyo and ActiveCampaign is refused.",
        code="conflate_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production stays untouched."""
    raise ConnectorProveError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    """READY is not claimed."""
    raise ConnectorProveError(
        "READY is refused. This prove does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    """PROVEN is not invented. The ceiling stays the ledger value."""
    raise ConnectorProveError(
        "A maturity raise is refused. This prove does not invent one.",
        code="proven_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    """The CR stays open."""
    raise ConnectorProveError(
        "Resolving the completion row is refused. The row stays open.",
        code="resolve_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Brand and connector slots stay empty."""
    raise ConnectorProveError(
        "Connector slots stay empty. This prove does not fill them.",
        code="slots_refused",
    )


def refuse_invent_metrics(_body: dict | None = None) -> None:
    """A number where the slot is empty is an invented metric."""
    raise ConnectorProveError(
        "A send or subscriber count is refused. Absence is not zero.",
        code="invent_metrics_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    _reject_claims(payload)
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("send") or payload.get("blast") or action in {"send", "blast", "email"}:
        refuse_send(payload)
    if payload.get("klaviyo") or payload.get("klaviyo_write") or action in {"klaviyo", "klaviyo_write"}:
        refuse_klaviyo_write(payload)
    if (
        payload.get("activecampaign")
        or payload.get("ac")
        or payload.get("ac_write")
        or action in {"activecampaign", "ac", "ac_write"}
    ):
        refuse_ac_write(payload)
    if payload.get("metricool") or action == "metricool":
        refuse_metricool(payload)
    if payload.get("conflate") or payload.get("same_connector") or action in {"conflate", "same"}:
        refuse_conflate(payload)
    if payload.get("production") or payload.get("production_mutate") or action == "production":
        refuse_production(payload)
    if payload.get("resolve") or payload.get("cr_resolved") or action == "resolve":
        refuse_resolve(payload)
    if payload.get("fill") or payload.get("slots_filled") or action == "fill":
        refuse_fill(payload)
    if payload.get("ready") or action == "ready":
        refuse_ready(payload)
    if payload.get("prove") or payload.get("proven") or action in {"prove", "proven"}:
        refuse_proven(payload)
    if payload.get("subscribers") is not None or payload.get("sends") is not None:
        refuse_invent_metrics(payload)
    if payload.get("write") or payload.get("external_crm_write") or action in {"write", "crm"}:
        refuse_crm_write(payload)
    raise ConnectorProveError(
        "Connector prove is read-only. No send, no external CRM write, no conflated connector.",
        code="writes_refused",
    )


def _truthy(value: str | None) -> bool:
    token = (value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def guard_query(
    *,
    send: str | None = None,
    write: str | None = None,
    klaviyo: str | None = None,
    ac: str | None = None,
    conflate: str | None = None,
    production: str | None = None,
    ready: str | None = None,
    proven: str | None = None,
    prove: str | None = None,
    resolve: str | None = None,
    metricool: str | None = None,
    fill: str | None = None,
    subscribers: str | None = None,
) -> None:
    """A read that asks to send, write, or prove is still a write. Refuse it."""
    if _truthy(send):
        refuse_send()
    if _truthy(klaviyo):
        refuse_klaviyo_write()
    if _truthy(ac):
        refuse_ac_write()
    if _truthy(metricool):
        refuse_metricool()
    if _truthy(conflate):
        refuse_conflate()
    if _truthy(production):
        refuse_production()
    if _truthy(resolve):
        refuse_resolve()
    if _truthy(fill):
        refuse_fill()
    if _truthy(ready):
        refuse_ready()
    if _truthy(proven) or _truthy(prove):
        refuse_proven()
    if _truthy(subscribers):
        refuse_invent_metrics()
    if _truthy(write):
        refuse_crm_write()


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise ConnectorProveError("connector prove refuses an Alchemist path", code="alchemist_refused")
    if "klaviyo.com" in low:
        raise ConnectorProveError("connector prove refuses a Klaviyo network path", code="klaviyo_write_refused")
    if "activecampaign.com" in low or "api-us1.com" in low:
        raise ConnectorProveError(
            "connector prove refuses an ActiveCampaign network path",
            code="ac_write_refused",
        )
    if "metricool" in low:
        raise ConnectorProveError("connector prove refuses a Metricool path", code="metricool_write_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise ConnectorProveError("connector prove refuses a production path", code="production_refused")
    resolved = path.resolve()
    try:
        resolved.relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise ConnectorProveError(
            "connector prove refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise ConnectorProveError("connector prove refuses a wolf-system fixture path", code="not_beta")


def _file_present(relpath: str) -> bool:
    path = (BETA_ROOT / relpath).resolve()
    _guard_path(path)
    return path.is_file()


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-CRM-04 from the ledger. Does not write it."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return _maturity(str(row[0]))


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-c8719063fb940ed4. Does not upsert, resolve, or harvest."""
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
    _guard_path(path)
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
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["framework_skeleton"] = "BUILT"
    flags["klaviyo_called"] = False
    flags["ac_called"] = False
    flags["conflated"] = False
    flags["send"] = False
    flags["external_crm_write"] = False
    flags["sends"] = None
    flags["subscribers"] = None
    flags["profiles_inserted"] = None
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def checklist() -> list[dict[str, Any]]:
    """The documented steps. None of them have been executed."""
    rows: list[dict[str, Any]] = []
    for row in CHECKLIST:
        item = {key: row[key] for key in STEP_FIELDS if key in row}
        item["executed"] = False
        item["result"] = NOT_RUN
        item["slot"] = EMPTY
        rows.append(item)
    return rows


def connector_rows() -> list[dict[str, Any]]:
    """Named connectors. Neither was called. They are not the same system."""
    rows: list[dict[str, Any]] = []
    for row in CONNECTORS:
        present = _file_present(str(row["reader_relpath"]))
        rows.append(
            {
                "id": row["id"],
                "name": row["name"],
                "order": row["order"],
                "source_system": row["source_system"],
                "not_same_as": list(row["not_same_as"]),
                "brand_scope": list(row["brand_scope"]),
                "entity_scope": list(row["entity_scope"]),
                "reader_relpath": row["reader_relpath"],
                "reader_present": present,
                "called": False,
                "network": False,
                "send": False,
                "external_write": False,
                "sends": None,
                "subscribers": None,
                "profiles_inserted": None,
                "slot": EMPTY,
                "conflated": False,
                "role": row["role"],
            }
        )
    return rows


def brand_rows() -> list[dict[str, Any]]:
    """Brand scopes. Habitat is documented. The others are ABSENT, not zero."""
    rows: list[dict[str, Any]] = []
    for row in BRANDS:
        rows.append(
            {
                "id": row["id"],
                "brand_id": row["brand_id"],
                "order": row["order"],
                "entity_id": row["entity_id"],
                "klaviyo_scope": row["klaviyo_scope"],
                "activecampaign_scope": row["activecampaign_scope"],
                "called": False,
                "send": False,
                "sends": None,
                "subscribers": None,
                "slot": EMPTY,
                "why": row["why"],
            }
        )
    return rows


def gap_rows() -> list[dict[str, Any]]:
    """Gaps. A missing reader is ABSENT, not zero. A present file is not a call."""
    klaviyo_present = _file_present(KLAVIYO_READER_REL)
    ac_present = _file_present(AC_READER_REL)
    if klaviyo_present:
        klaviyo_status = DOCUMENTED
        klaviyo_why = (
            "The Habitat reader file is present. This prove does not import it. "
            "A present file is not a live wire and not a profile insert."
        )
    else:
        klaviyo_status = ABSENT
        klaviyo_why = "The Habitat reader file is not present. Absence is not zero profiles."
    if ac_present:
        ac_status = DOCUMENTED
        ac_why = (
            "An ActiveCampaign file is present. This prove does not import it. "
            "A file is not a live wire and is not Klaviyo."
        )
    else:
        ac_status = ABSENT
        ac_why = "No ActiveCampaign reader file. Absence is not zero contacts and not a Klaviyo alias."
    return [
        {
            "id": "GAP-KLAVIYO-NOT-CALLED",
            "order": 1,
            "connector_id": "CONN-KLAVIYO",
            "status": klaviyo_status,
            "called": False,
            "sends": None,
            "why": klaviyo_why,
        },
        {
            "id": "GAP-AC-READER-ABSENT",
            "order": 2,
            "connector_id": "CONN-ACTIVECAMPAIGN",
            "status": ac_status,
            "called": False,
            "sends": None,
            "why": ac_why,
        },
        {
            "id": "GAP-NON-HABITAT-ABSENT",
            "order": 3,
            "connector_id": "CONN-KLAVIYO",
            "status": ABSENT,
            "called": False,
            "sends": None,
            "why": (
                "Uma Blu, Atrium, Selo, and Tropik have no email-marketing reader on this prove. "
                "Absence is not zero subscribers."
            ),
        },
        {
            "id": "GAP-SEND-NOT-A-COUNT",
            "order": 4,
            "connector_id": None,
            "status": REFUSED,
            "called": False,
            "sends": None,
            "why": "No send path is opened. A refused send is not a sent count of zero.",
        },
    ]


def distinction() -> dict[str, Any]:
    """Klaviyo and ActiveCampaign are different systems. The prove slot is empty."""
    return {
        "klaviyo": "CONN-KLAVIYO",
        "activecampaign": "CONN-ACTIVECAMPAIGN",
        "same_connector": False,
        "conflated": False,
        "distinction": DOCUMENTED,
        "slot": EMPTY,
        "why": (
            "Klaviyo source_system is klaviyo. ActiveCampaign source_system is activecampaign. "
            "This prove does not call either. Documented is not a live wire."
        ),
    }


def prove_log_schema() -> dict[str, Any]:
    """Machine-readable schema. The only accepted status is NOT_RUN."""
    return {
        "schema_id": SCHEMA_ID,
        "type": "object",
        "additionalProperties": False,
        "required": list(LOG_FIELDS),
        "status_enum": [NOT_RUN],
        "slot_enum": [EMPTY],
        "refused_status": sorted(_SUCCESS_STATUS | {"READY", "PROVEN", "RESOLVED"}),
        "properties": {
            "schema_id": {"const": SCHEMA_ID},
            "cap": {"const": CAP_ID},
            "prove_id": {"type": "null"},
            "recorded_at": {"type": "null"},
            "status": {"enum": [NOT_RUN]},
            "klaviyo_called": {"const": False},
            "ac_called": {"const": False},
            "conflated": {"const": False},
            "send": {"const": False},
            "external_crm_write": {"const": False},
            "klaviyo_write": {"const": False},
            "ac_write": {"const": False},
            "metricool_write": {"const": False},
            "production_mutated": {"const": False},
            "cr_resolved": {"const": False},
            "ready_claimed": {"const": False},
            "proven_claimed": {"const": False},
            "slots_filled": {"const": False},
            "sends": {"type": "null"},
            "subscribers": {"type": "null"},
            "profiles_inserted": {"type": "null"},
            "checklist": {"type": "array", "minItems": len(CHECKLIST), "maxItems": len(CHECKLIST)},
            "connectors": {"type": "array", "minItems": len(CONNECTORS), "maxItems": len(CONNECTORS)},
            "brands": {"type": "array", "minItems": len(BRANDS), "maxItems": len(BRANDS)},
            "gaps": {"type": "array", "minItems": 4, "maxItems": 4},
            "result": {"enum": [NOT_RUN]},
        },
    }


def not_run_log() -> dict[str, Any]:
    """The only log this prove emits. Nothing was called and no count was invented."""
    return {
        "schema_id": SCHEMA_ID,
        "cap": CAP_ID,
        "prove_id": None,
        "recorded_at": None,
        "status": NOT_RUN,
        "klaviyo_called": False,
        "ac_called": False,
        "conflated": False,
        "send": False,
        "external_crm_write": False,
        "klaviyo_write": False,
        "ac_write": False,
        "metricool_write": False,
        "production_mutated": False,
        "cr_resolved": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "slots_filled": False,
        "sends": None,
        "subscribers": None,
        "profiles_inserted": None,
        "checklist": checklist(),
        "connectors": connector_rows(),
        "brands": brand_rows(),
        "gaps": gap_rows(),
        "result": NOT_RUN,
    }


def _status_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _flag(payload: dict[str, Any], key: str) -> bool:
    return payload.get(key) is True


def _metric_dirty(item: dict[str, Any]) -> bool:
    for key in ("sends", "subscribers", "profiles_inserted"):
        if key in item and item.get(key) is not None:
            return True
    return False


def _rows_dirty(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if not isinstance(item, dict):
            continue
        if _metric_dirty(item):
            return "metrics"
        if item.get("executed") is True:
            return "write"
        token = _status_token(item.get("result")) or _status_token(item.get("status"))
        if token in {NOT_RUN, DOCUMENTED, ABSENT, REFUSED, ""}:
            token = _status_token(item.get("result"))
        if token in _SUCCESS_STATUS:
            return "success"
        if token in {"PROVEN", "READY"}:
            return token.lower()
        if token == "RESOLVED":
            return "resolve"
        gap_status = _status_token(item.get("status"))
        if gap_status in _SUCCESS_STATUS:
            return "success"
        if gap_status in {"PROVEN", "READY"}:
            return gap_status.lower()
        if gap_status == "RESOLVED":
            return "resolve"
        slot = item.get("slot")
        if slot is not None and slot != EMPTY:
            return "slots"
        if item.get("send") is True:
            return "send"
        if item.get("conflated") is True or item.get("same_connector") is True:
            return "conflate"
        sid = str(item.get("id") or "")
        src = str(item.get("source_system") or "")
        if sid == "CONN-ACTIVECAMPAIGN" and src == "klaviyo":
            return "conflate"
        if sid == "CONN-KLAVIYO" and src == "activecampaign":
            return "conflate"
        distinct = item.get("not_same_as")
        if isinstance(distinct, list) and not distinct and sid in {"CONN-KLAVIYO", "CONN-ACTIVECAMPAIGN"}:
            return "conflate"
        if item.get("called") is True or item.get("network") is True or item.get("external_write") is True:
            if "ACTIVECAMPAIGN" in sid or src == "activecampaign":
                return "ac"
            if "KLAVIYO" in sid or src == "klaviyo":
                return "klaviyo"
            return "write"
        scope = item.get("klaviyo_scope")
        if scope is not None and scope not in {DOCUMENTED, ABSENT}:
            return "metrics"
        ac_scope = item.get("activecampaign_scope")
        if ac_scope is not None and ac_scope not in {DOCUMENTED, ABSENT}:
            return "metrics"
    return None


def _reject_claims(payload: dict[str, Any]) -> None:
    """A claimed send, conflation, or maturity raise is refused. It is not rewritten into a pass."""
    if not isinstance(payload, dict):
        return
    status = _status_token(payload.get("status"))
    result = _status_token(payload.get("result"))
    dirty = (
        _rows_dirty(payload.get("checklist"))
        or _rows_dirty(payload.get("connectors"))
        or _rows_dirty(payload.get("brands"))
        or _rows_dirty(payload.get("gaps"))
    )
    if _metric_dirty(payload) or dirty == "metrics":
        refuse_invent_metrics(payload)
    if _flag(payload, "send") or dirty == "send" or status == "SENT" or result == "SENT":
        refuse_send(payload)
    if _flag(payload, "klaviyo_called") or _flag(payload, "klaviyo_write") or dirty == "klaviyo":
        refuse_klaviyo_write(payload)
    if _flag(payload, "ac_called") or _flag(payload, "ac_write") or dirty == "ac":
        refuse_ac_write(payload)
    if _flag(payload, "metricool_write"):
        refuse_metricool(payload)
    if _flag(payload, "external_crm_write") or dirty == "write":
        refuse_crm_write(payload)
    if _flag(payload, "conflated") or dirty == "conflate" or status == "CONFLATED":
        refuse_conflate(payload)
    if _flag(payload, "production_mutated") or status == "PRODUCTION" or dirty == "production":
        refuse_production(payload)
    if _flag(payload, "cr_resolved") or status == "RESOLVED" or result == "RESOLVED" or dirty == "resolve":
        refuse_resolve(payload)
    if _flag(payload, "ready_claimed") or status == "READY" or result == "READY" or dirty == "ready":
        refuse_ready(payload)
    if _flag(payload, "proven_claimed") or status == "PROVEN" or result == "PROVEN" or dirty == "proven":
        refuse_proven(payload)
    if _flag(payload, "slots_filled") or dirty == "slots" or status == "FILLED" or result == "FILLED":
        refuse_fill(payload)
    if status in _SUCCESS_STATUS or result in _SUCCESS_STATUS or dirty == "success":
        raise ConnectorProveError(
            "A connector-prove success is refused. This prove does not record one.",
            code="success_refused",
        )


def validate_log(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Accept only the NOT_RUN log. Anything else fails closed."""
    if not isinstance(payload, dict):
        raise ConnectorProveError("Connector prove log must be an object.", code="bad_log")
    _reject_claims(payload)
    missing = [name for name in LOG_FIELDS if name not in payload]
    if missing:
        raise ConnectorProveError("Connector prove log is missing required fields.", code="bad_log")
    extra = [name for name in payload if name not in LOG_FIELDS]
    if extra:
        raise ConnectorProveError("Connector prove log has fields this schema does not allow.", code="bad_log")
    if payload.get("schema_id") != SCHEMA_ID or payload.get("cap") != CAP_ID:
        raise ConnectorProveError("Connector prove log is not this schema.", code="bad_log")
    if payload.get("prove_id") is not None or payload.get("recorded_at") is not None:
        raise ConnectorProveError(
            "This prove does not assign a prove id or a recorded time.",
            code="bad_log",
        )
    if payload.get("status") != NOT_RUN or payload.get("result") != NOT_RUN:
        raise ConnectorProveError("Connector prove log status must stay NOT_RUN.", code="bad_log")
    for key in (
        "klaviyo_called",
        "ac_called",
        "conflated",
        "send",
        "external_crm_write",
        "klaviyo_write",
        "ac_write",
        "metricool_write",
        "production_mutated",
        "cr_resolved",
        "ready_claimed",
        "proven_claimed",
        "slots_filled",
    ):
        if payload.get(key) is not False:
            raise ConnectorProveError("Connector prove log flags must stay false.", code="bad_log")
    for key in ("sends", "subscribers", "profiles_inserted"):
        if payload.get(key) is not None:
            refuse_invent_metrics(payload)
    if payload.get("checklist") != checklist():
        raise ConnectorProveError("Checklist does not match the prove.", code="bad_log")
    if payload.get("connectors") != connector_rows():
        raise ConnectorProveError("Connectors do not match the prove.", code="bad_log")
    if payload.get("brands") != brand_rows():
        raise ConnectorProveError("Brand scopes do not match the prove.", code="bad_log")
    if payload.get("gaps") != gap_rows():
        raise ConnectorProveError("Gaps do not match the prove.", code="bad_log")
    return {
        "ok": True,
        "valid": True,
        "cap": CAP_ID,
        "status": NOT_RUN,
        "klaviyo_called": False,
        "ac_called": False,
        "conflated": False,
        "send": False,
        "external_crm_write": False,
        "cr_resolved": False,
        "sends": None,
        "subscribers": None,
        "ready_claimed": False,
        "proven_claimed": False,
        "log": payload,
    }


def _refuse_token(upper: str) -> None:
    if upper in {"SEND", "BLAST", "EMAIL"}:
        refuse_send()
    if upper in {"KLAVIYO", "KLAVIYO-WRITE", "CONN-KLAVIYO-WRITE"}:
        refuse_klaviyo_write()
    if upper in {"ACTIVECAMPAIGN", "AC", "AC-WRITE", "ACTIVE-CAMPAIGN"}:
        refuse_ac_write()
    if upper in {"WRITE", "CRM", "CRM-WRITE"}:
        refuse_crm_write()
    if upper in {"METRICOOL", "METRICOOL-WRITE"}:
        refuse_metricool()
    if upper in {"CONFLATE", "SAME", "SAME-CONNECTOR"}:
        refuse_conflate()
    if upper in {"PRODUCTION", "PROD"}:
        refuse_production()
    if upper in {"RESOLVE", "RESOLVED"}:
        refuse_resolve()
    if upper in {"FILL", "FILLED"}:
        refuse_fill()
    if upper == "READY":
        refuse_ready()
    if upper in {"PROVE", "PROVED", "PROVEN"}:
        refuse_proven()
    if upper in {"SUBSCRIBERS", "SENDS", "METRICS"}:
        refuse_invent_metrics()


def _bound(row_key: str, row: dict[str, Any], ledger_path: Path | str | None, catalog_db: Path | str | None) -> dict[str, Any]:
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "cap": CAP_ID,
        row_key: row,
        "klaviyo_called": False,
        "ac_called": False,
        "conflated": False,
        "send": False,
        "external_crm_write": False,
        "sends": None,
        "subscribers": None,
        "ledger_write": False,
        "cr_resolved": False,
        "honesty": flags,
    }


def read_step(
    step_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One checklist step. An unknown id is not invented."""
    token = (step_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "CONNECTORS", "BRANDS", "GAPS", "EXPORT"}:
        raise ConnectorProveError("That path is not a checklist step.", code="not_found")
    for row in checklist():
        if row["id"] == token:
            return _bound("step", row, ledger_path, catalog_db)
    raise ConnectorProveError(
        "Checklist step was not in the prove. It was not invented.",
        code="not_found",
    )


def read_connector(
    connector_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One named connector. An unknown id is not invented."""
    token = (connector_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "CONNECTORS", "BRANDS", "GAPS", "EXPORT"}:
        raise ConnectorProveError("That path is not a connector.", code="not_found")
    for row in connector_rows():
        if row["id"] == token:
            packed = _bound("connector", row, ledger_path, catalog_db)
            packed["distinction"] = distinction()
            return packed
    raise ConnectorProveError(
        "Connector was not in the prove. It was not invented.",
        code="not_found",
    )


def read_brand(
    brand_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One brand scope. An unknown brand is not invented and is not zero."""
    token = (brand_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "CONNECTORS", "BRANDS", "GAPS", "EXPORT"}:
        raise ConnectorProveError("That path is not a brand scope.", code="not_found")
    for row in brand_rows():
        if row["id"] == token or row["brand_id"] == token.lower():
            return _bound("brand", row, ledger_path, catalog_db)
    raise ConnectorProveError(
        "Brand scope was not in the prove. It was not invented.",
        code="not_found",
    )


def read_gap(
    gap_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One documented gap. An unknown gap is not invented."""
    token = (gap_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "CONNECTORS", "BRANDS", "GAPS", "EXPORT"}:
        raise ConnectorProveError("That path is not a gap.", code="not_found")
    for row in gap_rows():
        if row["id"] == token:
            return _bound("gap", row, ledger_path, catalog_db)
    raise ConnectorProveError(
        "Gap was not in the prove. It was not invented.",
        code="not_found",
    )


def read_ref(
    ref_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """A step, connector, brand, or gap. Unknown ids are not invented."""
    token = (ref_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    try:
        return read_step(token, ledger_path, catalog_db)
    except ConnectorProveError as exc:
        if exc.code != "not_found":
            raise
    try:
        return read_connector(token, ledger_path, catalog_db)
    except ConnectorProveError as exc:
        if exc.code != "not_found":
            raise
    try:
        return read_brand(token, ledger_path, catalog_db)
    except ConnectorProveError as exc:
        if exc.code != "not_found":
            raise
    return read_gap(token, ledger_path, catalog_db)


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Read-only prove. The log inside it is NOT_RUN. No send and no count."""
    flags = honesty_flags(ledger_path, catalog_db)
    steps = checklist()
    named = connector_rows()
    brands = brand_rows()
    gaps = gap_rows()
    log = not_run_log()
    checked = validate_log(log)
    split = distinction()
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "crm_connector_prove",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "klaviyo_called": False,
        "ac_called": False,
        "conflated": False,
        "send": False,
        "external_crm_write": False,
        "klaviyo_write": False,
        "ac_write": False,
        "metricool_write": False,
        "production_mutated": False,
        "cr_resolved": False,
        "slots_filled": False,
        "sends": None,
        "subscribers": None,
        "profiles_inserted": None,
        "ledger_write": False,
        "external_writes": False,
        "status": NOT_RUN,
        "checklist_count": len(steps),
        "checklist_executed": 0,
        "empty_slot_count": len(steps) + len(named) + len(brands),
        "checklist": steps,
        "connectors": named,
        "connector_count": len(named),
        "brands": brands,
        "brand_count": len(brands),
        "gaps": gaps,
        "gap_count": len(gaps),
        "distinction": split,
        "schema": prove_log_schema(),
        "log": log,
        "log_valid": checked["valid"] is True and checked["status"] == NOT_RUN,
        "honesty": flags,
    }
