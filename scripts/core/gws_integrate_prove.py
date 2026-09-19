#!/usr/bin/env python3
"""CAP-INTG-03 Google Workspace INTEGRATE prove (Beta, read-only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-INTG-GWS-INTEGRATE-PROVE-2026-09-20.md.
CR-260e724b776f2b89 next action is CAP-bound INTEGRATE prove pack. Owner
lane intg-gws-integrate-prove. Wave-6 after intel-approve-to-rule-v1
267618a.

Names Gmail, Calendar, Drive, and auth as different surfaces. It does not
probe them, import a reader, widen OAuth scopes, or invent GREEN, PROVEN,
or READY. A missing reader is ABSENT, not zero. CAP-INTG-03 stays at the
ledger value. The ceiling is BUILT unless the ledger is already PROVEN or
READY. The CR is not resolved.
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

CR_ID = "CR-260e724b776f2b89"
CAP_ID = "CAP-INTG-03"
SCHEMA_ID = "wolf.cap-intg-03.gws-integrate-log.v1"
NOT_RUN = "NOT_RUN"
EMPTY = "EMPTY"
DOCUMENTED = "DOCUMENTED"
ABSENT = "ABSENT"
REFUSED = "REFUSED"
NOT_PROBED = "NOT_PROBED"

GMAIL_READER_REL = "scripts/core/gmail_reader.py"
CALENDAR_READER_REL = "scripts/core/calendar_reader.py"
DRIVE_READER_REL = "scripts/core/drive_reader.py"
AUTH_READER_REL = "scripts/core/gws_oauth.py"

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
SURFACE_IDS = frozenset({"SURF-GMAIL", "SURF-CALENDAR", "SURF-DRIVE", "SURF-AUTH"})
EXPECTED_SOURCE = {
    "SURF-GMAIL": "gmail",
    "SURF-CALENDAR": "google-calendar",
    "SURF-DRIVE": "google-drive",
    "SURF-AUTH": "google-oauth",
}

LOG_FIELDS = (
    "schema_id",
    "cap",
    "prove_id",
    "recorded_at",
    "status",
    "gmail_called",
    "calendar_called",
    "drive_called",
    "auth_called",
    "conflated",
    "probed",
    "scopes_widened",
    "green_claimed",
    "gmail_write",
    "calendar_write",
    "drive_write",
    "oauth_write",
    "production_mutated",
    "cr_resolved",
    "ready_claimed",
    "proven_claimed",
    "slots_filled",
    "messages",
    "events",
    "files",
    "scopes",
    "checklist",
    "surfaces",
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
_GREEN_STATUS = frozenset({"GREEN", "READ_OK", "HEALTHY"})
_PROBE_STATUS = frozenset({"PROBED"})
_SCOPE_STATUS = frozenset({"WIDENED", "SCOPES"})

CHECKLIST: tuple[dict[str, Any], ...] = (
    {
        "id": "CHK-NAME-GMAIL",
        "order": 1,
        "required": True,
        "title": "Name Gmail as its own surface",
        "detail": "Gmail is mail. Naming it is not a probe and not a message count.",
    },
    {
        "id": "CHK-NAME-CALENDAR",
        "order": 2,
        "required": True,
        "title": "Name Calendar as a different surface",
        "detail": "Calendar is not Gmail. Naming it is not an event count.",
    },
    {
        "id": "CHK-NAME-DRIVE",
        "order": 3,
        "required": True,
        "title": "Name Drive as a different surface",
        "detail": "Drive is documents. It is not Gmail and not Calendar. Naming it is not a file count.",
    },
    {
        "id": "CHK-NAME-AUTH",
        "order": 4,
        "required": True,
        "title": "Name auth as a different surface",
        "detail": "Auth is not a mailbox. Naming it does not read a token and does not add a scope.",
    },
    {
        "id": "CHK-NOT-CONFLATED",
        "order": 5,
        "required": True,
        "title": "Keep the four surfaces distinct",
        "detail": "A payload that marks them as one connector is refused. This prove does not conflate them.",
    },
    {
        "id": "CHK-DOCUMENT-GAPS",
        "order": 6,
        "required": True,
        "title": "Document missing readers",
        "detail": "A missing Beta reader is ABSENT. Absence is not zero messages, events, files, or scopes.",
    },
    {
        "id": "CHK-NO-PROBE",
        "order": 7,
        "required": True,
        "title": "Do not probe Gmail, Calendar, or Drive",
        "detail": "No Google API call. Not probed is not GREEN.",
    },
    {
        "id": "CHK-NO-SCOPE-WIDEN",
        "order": 8,
        "required": True,
        "title": "Do not widen OAuth scopes",
        "detail": "No scope list is read. No scope is added. An unread list is not zero scopes.",
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
            "CAP-INTG-03 stays at the ledger value. The ceiling is BUILT unless "
            "the ledger is already higher. The CR stays open. GREEN is not a maturity."
        ),
    },
)

SURFACES: tuple[dict[str, Any], ...] = (
    {
        "id": "SURF-GMAIL",
        "name": "Gmail",
        "order": 1,
        "source_system": "gmail",
        "not_same_as": ("SURF-CALENDAR", "SURF-DRIVE", "SURF-AUTH"),
        "reader_relpath": GMAIL_READER_REL,
        "role": "Mail surface. Not Calendar, Drive, or auth. Not called by this prove.",
    },
    {
        "id": "SURF-CALENDAR",
        "name": "Google Calendar",
        "order": 2,
        "source_system": "google-calendar",
        "not_same_as": ("SURF-GMAIL", "SURF-DRIVE", "SURF-AUTH"),
        "reader_relpath": CALENDAR_READER_REL,
        "role": "Calendar surface. Not Gmail. Not called by this prove.",
    },
    {
        "id": "SURF-DRIVE",
        "name": "Google Drive",
        "order": 3,
        "source_system": "google-drive",
        "not_same_as": ("SURF-GMAIL", "SURF-CALENDAR", "SURF-AUTH"),
        "reader_relpath": DRIVE_READER_REL,
        "role": "Documents surface. Not Gmail and not Calendar. Not called by this prove.",
    },
    {
        "id": "SURF-AUTH",
        "name": "Google auth",
        "order": 4,
        "source_system": "google-oauth",
        "not_same_as": ("SURF-GMAIL", "SURF-CALENDAR", "SURF-DRIVE"),
        "reader_relpath": AUTH_READER_REL,
        "role": "Auth surface. Tokens are not read. Scopes are not widened. Not a mailbox.",
    },
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "gws_integrate_prove",
    "read_only": True,
    "external_writes": False,
    "production": False,
    "production_mutated": False,
    "alchemist_write": False,
    "network_calls": False,
    "gmail_called": False,
    "calendar_called": False,
    "drive_called": False,
    "auth_called": False,
    "conflated": False,
    "probed": False,
    "scopes_widened": False,
    "green_claimed": False,
    "gmail_write": False,
    "calendar_write": False,
    "drive_write": False,
    "oauth_write": False,
    "cr_mutated": False,
    "cr_resolved": False,
    "score_changed": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "slots_filled": False,
    "messages": None,
    "events": None,
    "files": None,
    "scopes": None,
    "evidence_invented": False,
    "anon_fail_closed": True,
}


class GwsProveError(ValueError):
    """Fail closed. Does not probe Google, widen scopes, or raise maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_gmail_write(_body: dict | None = None) -> None:
    """Gmail is not called and not written."""
    raise GwsProveError(
        "Gmail write is refused. The reader is not called and no message count is invented.",
        code="gmail_write_refused",
    )


def refuse_calendar_write(_body: dict | None = None) -> None:
    """Calendar is not called and not written."""
    raise GwsProveError(
        "Calendar write is refused. Calendar is not Gmail and is not called.",
        code="calendar_write_refused",
    )


def refuse_drive_write(_body: dict | None = None) -> None:
    """Drive is not called and not written."""
    raise GwsProveError(
        "Drive write is refused. Drive is not Gmail and is not called.",
        code="drive_write_refused",
    )


def refuse_oauth_write(_body: dict | None = None) -> None:
    """Auth tokens are not written."""
    raise GwsProveError(
        "OAuth write is refused. Tokens are not read and scopes are not stored.",
        code="oauth_write_refused",
    )


def refuse_probe(_body: dict | None = None) -> None:
    """No Google API call."""
    raise GwsProveError(
        "A Google probe is refused. Not probed is not GREEN and not a count of zero.",
        code="probe_refused",
    )


def refuse_scope_widen(_body: dict | None = None) -> None:
    """Scopes stay unread. None are added."""
    raise GwsProveError(
        "Widening OAuth scopes is refused. No scope list was read. Unread is not zero scopes.",
        code="scope_widen_refused",
    )


def refuse_green(_body: dict | None = None) -> None:
    """GREEN is not a result of this prove."""
    raise GwsProveError(
        "GREEN is refused. This prove does not invent a healthy connector.",
        code="green_refused",
    )


def refuse_conflate(_body: dict | None = None) -> None:
    """The four surfaces stay different names."""
    raise GwsProveError(
        "Conflating Gmail, Calendar, Drive, and auth is refused.",
        code="conflate_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production stays untouched."""
    raise GwsProveError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    """READY is not claimed."""
    raise GwsProveError(
        "READY is refused. This prove does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    """PROVEN is not invented. The ceiling stays the ledger value."""
    raise GwsProveError(
        "A maturity raise is refused. This prove does not invent one.",
        code="proven_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    """The CR stays open."""
    raise GwsProveError(
        "Resolving the completion row is refused. The row stays open.",
        code="resolve_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Surface slots stay empty."""
    raise GwsProveError(
        "Workspace slots stay empty. This prove does not fill them.",
        code="slots_refused",
    )


def refuse_invent_metrics(_body: dict | None = None) -> None:
    """A number where the slot is empty is an invented metric."""
    raise GwsProveError(
        "A message, event, file, or scope count is refused. Absence is not zero.",
        code="invent_metrics_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    _reject_claims(payload)
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("gmail") or payload.get("gmail_write") or action in {"gmail", "gmail_write", "mail"}:
        refuse_gmail_write(payload)
    if payload.get("calendar") or payload.get("calendar_write") or action in {"calendar", "calendar_write"}:
        refuse_calendar_write(payload)
    if payload.get("drive") or payload.get("drive_write") or action in {"drive", "drive_write", "docs"}:
        refuse_drive_write(payload)
    if payload.get("oauth") or payload.get("oauth_write") or payload.get("auth_write") or action in {"oauth", "auth", "token"}:
        refuse_oauth_write(payload)
    if payload.get("probe") or payload.get("probed") or action in {"probe", "probed"}:
        refuse_probe(payload)
    if payload.get("scopes_widened") or payload.get("widen") or action in {"widen", "scopes", "scope"}:
        refuse_scope_widen(payload)
    if payload.get("green") or payload.get("green_claimed") or action == "green":
        refuse_green(payload)
    if payload.get("conflate") or payload.get("same_surface") or action in {"conflate", "same"}:
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
    if (
        payload.get("messages") is not None
        or payload.get("events") is not None
        or payload.get("files") is not None
        or payload.get("scopes") is not None
    ):
        refuse_invent_metrics(payload)
    raise GwsProveError(
        "Google Workspace prove is read-only. No probe, no scope widen, no GREEN.",
        code="writes_refused",
    )


def _truthy(value: str | None) -> bool:
    token = (value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    gmail: str | None = None,
    calendar: str | None = None,
    drive: str | None = None,
    auth: str | None = None,
    probe: str | None = None,
    scopes: str | None = None,
    green: str | None = None,
    conflate: str | None = None,
    production: str | None = None,
    ready: str | None = None,
    proven: str | None = None,
    prove: str | None = None,
    resolve: str | None = None,
    fill: str | None = None,
    messages: str | None = None,
    events: str | None = None,
    files: str | None = None,
    write: str | None = None,
) -> None:
    """A read that asks to probe, widen, or prove is still a write. Refuse it."""
    if _truthy(gmail):
        refuse_gmail_write()
    if _truthy(calendar):
        refuse_calendar_write()
    if _truthy(drive):
        refuse_drive_write()
    if _truthy(auth):
        refuse_oauth_write()
    if _truthy(probe):
        refuse_probe()
    if _present(scopes):
        token = scopes.strip().lower()
        if token in {"widen", "add", "extra", "1", "true", "yes"}:
            refuse_scope_widen()
        refuse_invent_metrics()
    if _truthy(green):
        refuse_green()
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
    if _present(messages) or _present(events) or _present(files):
        refuse_invent_metrics()
    if _truthy(write):
        raise GwsProveError(
            "Google Workspace prove is read-only. No probe, no scope widen, no GREEN.",
            code="writes_refused",
        )


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise GwsProveError("workspace prove refuses an Alchemist path", code="alchemist_refused")
    if (
        "googleapis.com" in low
        or "gmail.google.com" in low
        or "calendar.google.com" in low
        or "drive.google.com" in low
        or "accounts.google.com" in low
    ):
        raise GwsProveError(
            "workspace prove refuses a Google network path",
            code="probe_refused",
        )
    if "client_secret" in low or "token.json" in low or "credentials.json" in low:
        raise GwsProveError(
            "workspace prove refuses a credential path",
            code="oauth_write_refused",
        )
    if "gmail.modify" in low or "gmail.readonly" in low or "/auth/gmail" in low or "/auth/calendar" in low or "/auth/drive" in low:
        raise GwsProveError(
            "workspace prove refuses a scope grant",
            code="scope_widen_refused",
        )
    if low.endswith("money.sqlite") or "/production" in low:
        raise GwsProveError("workspace prove refuses a production path", code="production_refused")
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
        raise GwsProveError(
            "workspace prove refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise GwsProveError("workspace prove refuses a wolf-system fixture path", code="not_beta")


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
    """Read CAP-INTG-03 from the ledger. Does not write it."""
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
    """Read CR-260e724b776f2b89. Does not upsert, resolve, or harvest."""
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
    flags["gmail_called"] = False
    flags["calendar_called"] = False
    flags["drive_called"] = False
    flags["auth_called"] = False
    flags["probed"] = False
    flags["scopes_widened"] = False
    flags["green_claimed"] = False
    flags["conflated"] = False
    flags["messages"] = None
    flags["events"] = None
    flags["files"] = None
    flags["scopes"] = None
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


def surface_rows() -> list[dict[str, Any]]:
    """Named surfaces. None were called. They are not the same system."""
    rows: list[dict[str, Any]] = []
    for row in SURFACES:
        present = _file_present(str(row["reader_relpath"]))
        rows.append(
            {
                "id": row["id"],
                "name": row["name"],
                "order": row["order"],
                "source_system": row["source_system"],
                "not_same_as": list(row["not_same_as"]),
                "reader_relpath": row["reader_relpath"],
                "reader_present": present,
                "called": False,
                "network": False,
                "probed": False,
                "write": False,
                "scopes_widened": False,
                "green": False,
                "health": NOT_PROBED,
                "messages": None,
                "events": None,
                "files": None,
                "scopes": None,
                "slot": EMPTY,
                "conflated": False,
                "role": row["role"],
            }
        )
    return rows


def _gap_for(relpath: str, gap_id: str, order: int, surface_id: str, noun: str) -> dict[str, Any]:
    present = _file_present(relpath)
    if present:
        status = DOCUMENTED
        why = (
            f"A {noun} file is present. This prove does not import it. "
            "A present file is not a probe, not GREEN, and not a count."
        )
    else:
        status = ABSENT
        why = f"No Beta {noun} file. Absence is not zero and not GREEN."
    return {
        "id": gap_id,
        "order": order,
        "surface_id": surface_id,
        "status": status,
        "called": False,
        "probed": False,
        "messages": None,
        "events": None,
        "files": None,
        "scopes": None,
        "why": why,
    }


def gap_rows() -> list[dict[str, Any]]:
    """Gaps. A missing reader is ABSENT, not zero. Not probed is not GREEN."""
    return [
        _gap_for(GMAIL_READER_REL, "GAP-GMAIL-ABSENT", 1, "SURF-GMAIL", "Gmail reader"),
        _gap_for(CALENDAR_READER_REL, "GAP-CALENDAR-ABSENT", 2, "SURF-CALENDAR", "Calendar reader"),
        _gap_for(DRIVE_READER_REL, "GAP-DRIVE-ABSENT", 3, "SURF-DRIVE", "Drive reader"),
        _gap_for(AUTH_READER_REL, "GAP-AUTH-ABSENT", 4, "SURF-AUTH", "auth reader"),
        {
            "id": "GAP-NOT-GREEN",
            "order": 5,
            "surface_id": None,
            "status": REFUSED,
            "called": False,
            "probed": False,
            "messages": None,
            "events": None,
            "files": None,
            "scopes": None,
            "why": "Health stays NOT_PROBED. GREEN is refused. Not probed is not a pass.",
        },
        {
            "id": "GAP-SCOPES-NOT-WIDENED",
            "order": 6,
            "surface_id": "SURF-AUTH",
            "status": REFUSED,
            "called": False,
            "probed": False,
            "messages": None,
            "events": None,
            "files": None,
            "scopes": None,
            "why": "No scope list was read and none were added. Unread is not zero scopes.",
        },
    ]


def distinction() -> dict[str, Any]:
    """The four surfaces are different. The prove slot is empty."""
    return {
        "gmail": "SURF-GMAIL",
        "calendar": "SURF-CALENDAR",
        "drive": "SURF-DRIVE",
        "auth": "SURF-AUTH",
        "same_surface": False,
        "conflated": False,
        "distinction": DOCUMENTED,
        "slot": EMPTY,
        "why": (
            "Gmail, Calendar, Drive, and auth have different source_system values. "
            "This prove does not call any of them. Documented is not a probe and not GREEN."
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
        "refused_status": sorted(_SUCCESS_STATUS | _GREEN_STATUS | {"READY", "PROVEN", "RESOLVED"}),
        "properties": {
            "schema_id": {"const": SCHEMA_ID},
            "cap": {"const": CAP_ID},
            "status": {"enum": [NOT_RUN]},
            "checklist": {"type": "array", "minItems": len(CHECKLIST), "maxItems": len(CHECKLIST)},
            "surfaces": {"type": "array", "minItems": len(SURFACES), "maxItems": len(SURFACES)},
            "gaps": {"type": "array", "minItems": 6, "maxItems": 6},
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
        "gmail_called": False,
        "calendar_called": False,
        "drive_called": False,
        "auth_called": False,
        "conflated": False,
        "probed": False,
        "scopes_widened": False,
        "green_claimed": False,
        "gmail_write": False,
        "calendar_write": False,
        "drive_write": False,
        "oauth_write": False,
        "production_mutated": False,
        "cr_resolved": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "slots_filled": False,
        "messages": None,
        "events": None,
        "files": None,
        "scopes": None,
        "checklist": checklist(),
        "surfaces": surface_rows(),
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
    for key in ("messages", "events", "files", "scopes"):
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
        if item.get("executed") is True or item.get("probed") is True or item.get("called") is True or item.get("network") is True:
            sid = str(item.get("id") or "")
            src = str(item.get("source_system") or "")
            if item.get("probed") is True or item.get("network") is True:
                return "probe"
            if "CALENDAR" in sid or src == "google-calendar":
                return "calendar"
            if "DRIVE" in sid or src == "google-drive":
                return "drive"
            if "AUTH" in sid or src == "google-oauth":
                return "auth"
            if "GMAIL" in sid or src == "gmail":
                return "gmail"
            return "probe"
        token = _status_token(item.get("result")) or _status_token(item.get("status"))
        health = _status_token(item.get("health"))
        if token in _GREEN_STATUS or health in _GREEN_STATUS or item.get("green") is True:
            return "green"
        if token in _PROBE_STATUS:
            return "probe"
        if token in _SCOPE_STATUS or item.get("scopes_widened") is True:
            return "scopes"
        if token in _SUCCESS_STATUS or health in _SUCCESS_STATUS:
            return "success"
        if token in {"PROVEN", "READY"}:
            return token.lower()
        if token == "RESOLVED":
            return "resolve"
        gap_status = _status_token(item.get("status"))
        if gap_status in _GREEN_STATUS:
            return "green"
        if gap_status in _SUCCESS_STATUS:
            return "success"
        if gap_status in {"PROVEN", "READY"}:
            return gap_status.lower()
        if gap_status == "RESOLVED":
            return "resolve"
        slot = item.get("slot")
        if slot is not None and slot != EMPTY:
            return "slots"
        if item.get("conflated") is True or item.get("same_surface") is True:
            return "conflate"
        sid = str(item.get("id") or "")
        src = str(item.get("source_system") or "")
        expected = EXPECTED_SOURCE.get(sid)
        if expected and src and src != expected:
            return "conflate"
        distinct = item.get("not_same_as")
        if isinstance(distinct, list) and not distinct and sid in SURFACE_IDS:
            return "conflate"
        if item.get("write") is True:
            if "CALENDAR" in sid:
                return "calendar"
            if "DRIVE" in sid:
                return "drive"
            if "AUTH" in sid:
                return "auth"
            return "gmail"
    return None


def _reject_claims(payload: dict[str, Any]) -> None:
    """A claimed probe, scope widen, GREEN, or maturity raise is refused. It is not rewritten into a pass."""
    if not isinstance(payload, dict):
        return
    status = _status_token(payload.get("status"))
    result = _status_token(payload.get("result"))
    dirty = (
        _rows_dirty(payload.get("checklist"))
        or _rows_dirty(payload.get("surfaces"))
        or _rows_dirty(payload.get("gaps"))
    )
    if _metric_dirty(payload) or dirty == "metrics":
        refuse_invent_metrics(payload)
    if status in _GREEN_STATUS or result in _GREEN_STATUS or _flag(payload, "green_claimed") or dirty == "green":
        refuse_green(payload)
    if _flag(payload, "probed") or dirty == "probe" or status in _PROBE_STATUS or result in _PROBE_STATUS:
        refuse_probe(payload)
    if _flag(payload, "scopes_widened") or dirty == "scopes" or status in _SCOPE_STATUS or result in _SCOPE_STATUS:
        refuse_scope_widen(payload)
    if _flag(payload, "gmail_called") or _flag(payload, "gmail_write") or dirty == "gmail":
        refuse_gmail_write(payload)
    if _flag(payload, "calendar_called") or _flag(payload, "calendar_write") or dirty == "calendar":
        refuse_calendar_write(payload)
    if _flag(payload, "drive_called") or _flag(payload, "drive_write") or dirty == "drive":
        refuse_drive_write(payload)
    if _flag(payload, "auth_called") or _flag(payload, "oauth_write") or dirty == "auth":
        refuse_oauth_write(payload)
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
        raise GwsProveError(
            "A workspace-prove success is refused. This prove does not record one.",
            code="success_refused",
        )


def validate_log(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Accept only the NOT_RUN log. Anything else fails closed."""
    if not isinstance(payload, dict):
        raise GwsProveError("Workspace prove log must be an object.", code="bad_log")
    _reject_claims(payload)
    missing = [name for name in LOG_FIELDS if name not in payload]
    if missing:
        raise GwsProveError("Workspace prove log is missing required fields.", code="bad_log")
    extra = [name for name in payload if name not in LOG_FIELDS]
    if extra:
        raise GwsProveError("Workspace prove log has fields this schema does not allow.", code="bad_log")
    if payload.get("schema_id") != SCHEMA_ID or payload.get("cap") != CAP_ID:
        raise GwsProveError("Workspace prove log is not this schema.", code="bad_log")
    if payload.get("prove_id") is not None or payload.get("recorded_at") is not None:
        raise GwsProveError(
            "This prove does not assign a prove id or a recorded time.",
            code="bad_log",
        )
    if payload.get("status") != NOT_RUN or payload.get("result") != NOT_RUN:
        raise GwsProveError("Workspace prove log status must stay NOT_RUN.", code="bad_log")
    for key in (
        "gmail_called",
        "calendar_called",
        "drive_called",
        "auth_called",
        "conflated",
        "probed",
        "scopes_widened",
        "green_claimed",
        "gmail_write",
        "calendar_write",
        "drive_write",
        "oauth_write",
        "production_mutated",
        "cr_resolved",
        "ready_claimed",
        "proven_claimed",
        "slots_filled",
    ):
        if payload.get(key) is not False:
            raise GwsProveError("Workspace prove log flags must stay false.", code="bad_log")
    for key in ("messages", "events", "files", "scopes"):
        if payload.get(key) is not None:
            refuse_invent_metrics(payload)
    if payload.get("checklist") != checklist():
        raise GwsProveError("Checklist does not match the prove.", code="bad_log")
    if payload.get("surfaces") != surface_rows():
        raise GwsProveError("Surfaces do not match the prove.", code="bad_log")
    if payload.get("gaps") != gap_rows():
        raise GwsProveError("Gaps do not match the prove.", code="bad_log")
    return {
        "ok": True,
        "valid": True,
        "cap": CAP_ID,
        "status": NOT_RUN,
        "gmail_called": False,
        "calendar_called": False,
        "drive_called": False,
        "auth_called": False,
        "conflated": False,
        "probed": False,
        "scopes_widened": False,
        "green_claimed": False,
        "cr_resolved": False,
        "messages": None,
        "events": None,
        "files": None,
        "scopes": None,
        "ready_claimed": False,
        "proven_claimed": False,
        "log": payload,
    }


def _refuse_token(upper: str) -> None:
    if upper in {"GMAIL", "GMAIL-WRITE", "MAIL"}:
        refuse_gmail_write()
    if upper in {"CALENDAR", "CALENDAR-WRITE"}:
        refuse_calendar_write()
    if upper in {"DRIVE", "DRIVE-WRITE", "DOCS"}:
        refuse_drive_write()
    if upper in {"AUTH", "OAUTH", "TOKEN", "OAUTH-WRITE"}:
        refuse_oauth_write()
    if upper in {"PROBE", "PROBED"}:
        refuse_probe()
    if upper in {"SCOPES", "WIDEN", "OAUTH-WIDEN", "SCOPE"}:
        refuse_scope_widen()
    if upper in {"GREEN", "READ_OK", "HEALTHY"}:
        refuse_green()
    if upper in {"CONFLATE", "SAME", "SAME-SURFACE"}:
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
    if upper in {"MESSAGES", "EVENTS", "FILES", "METRICS"}:
        refuse_invent_metrics()


def _bound(row_key: str, row: dict[str, Any], ledger_path: Path | str | None, catalog_db: Path | str | None) -> dict[str, Any]:
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "cap": CAP_ID,
        row_key: row,
        "gmail_called": False,
        "calendar_called": False,
        "drive_called": False,
        "auth_called": False,
        "conflated": False,
        "probed": False,
        "scopes_widened": False,
        "green_claimed": False,
        "messages": None,
        "events": None,
        "files": None,
        "scopes": None,
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
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "SURFACES", "GAPS", "EXPORT"}:
        raise GwsProveError("That path is not a checklist step.", code="not_found")
    for row in checklist():
        if row["id"] == token:
            return _bound("step", row, ledger_path, catalog_db)
    raise GwsProveError(
        "Checklist step was not in the prove. It was not invented.",
        code="not_found",
    )


def read_surface(
    surface_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One named surface. An unknown id is not invented."""
    token = (surface_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "SURFACES", "GAPS", "EXPORT"}:
        raise GwsProveError("That path is not a surface.", code="not_found")
    for row in surface_rows():
        if row["id"] == token:
            packed = _bound("surface", row, ledger_path, catalog_db)
            packed["distinction"] = distinction()
            return packed
    raise GwsProveError(
        "Surface was not in the prove. It was not invented.",
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
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "SURFACES", "GAPS", "EXPORT"}:
        raise GwsProveError("That path is not a gap.", code="not_found")
    for row in gap_rows():
        if row["id"] == token:
            return _bound("gap", row, ledger_path, catalog_db)
    raise GwsProveError(
        "Gap was not in the prove. It was not invented.",
        code="not_found",
    )


def read_ref(
    ref_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """A step, surface, or gap. Unknown ids are not invented."""
    token = (ref_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    try:
        return read_step(token, ledger_path, catalog_db)
    except GwsProveError as exc:
        if exc.code != "not_found":
            raise
    try:
        return read_surface(token, ledger_path, catalog_db)
    except GwsProveError as exc:
        if exc.code != "not_found":
            raise
    return read_gap(token, ledger_path, catalog_db)


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Read-only prove. The log inside it is NOT_RUN. No probe and no count."""
    flags = honesty_flags(ledger_path, catalog_db)
    steps = checklist()
    named = surface_rows()
    gaps = gap_rows()
    log = not_run_log()
    checked = validate_log(log)
    split = distinction()
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "gws_integrate_prove",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "gmail_called": False,
        "calendar_called": False,
        "drive_called": False,
        "auth_called": False,
        "conflated": False,
        "probed": False,
        "scopes_widened": False,
        "green_claimed": False,
        "gmail_write": False,
        "calendar_write": False,
        "drive_write": False,
        "oauth_write": False,
        "production_mutated": False,
        "cr_resolved": False,
        "slots_filled": False,
        "messages": None,
        "events": None,
        "files": None,
        "scopes": None,
        "ledger_write": False,
        "external_writes": False,
        "status": NOT_RUN,
        "checklist_count": len(steps),
        "checklist_executed": 0,
        "empty_slot_count": len(steps) + len(named),
        "checklist": steps,
        "surfaces": named,
        "surface_count": len(named),
        "gaps": gaps,
        "gap_count": len(gaps),
        "distinction": split,
        "schema": prove_log_schema(),
        "log": log,
        "log_valid": checked["valid"] is True and checked["status"] == NOT_RUN,
        "honesty": flags,
    }
