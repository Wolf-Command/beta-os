#!/usr/bin/env python3
"""CAP-DR-01 restore-drill framework (Beta, read-only).

Decision served: 2026-09-19 PICK, restore-drill framework on Beta only
(docs/deliveries/GROK-PLAN-DR-RESTORE-DRILL-FRAMEWORK-2026-09-19.md).

Documents the checklist and the drill-log schema. It does not run a restore,
mutate Production, or touch NAS or B2. Honesty is bound to
CR-667f31959d1bbe82 when that row is present. Ledger maturity is read, not
written. The skeleton ceiling is BUILT unless the ledger is already higher.
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

CR_ID = "CR-667f31959d1bbe82"
CAP_ID = "CAP-DR-01"
SCHEMA_ID = "wolf.cap-dr-01.restore-drill-log.v1"
NOT_RUN = "NOT_RUN"

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

LOG_FIELDS = (
    "schema_id",
    "cap",
    "drill_id",
    "recorded_at",
    "status",
    "live_restore",
    "production_mutated",
    "nas_destructive",
    "b2_destructive",
    "secrets_written",
    "source_deleted",
    "ready_claimed",
    "proven_claimed",
    "historical_counts_as_this_drill",
    "checklist",
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
)

_SUCCESS_STATUS = frozenset({
    "SUCCESS",
    "RESTORED",
    "PASS",
    "PASSED",
    "OK",
    "DONE",
    "COMPLETE",
    "COMPLETED",
})

CHECKLIST: tuple[dict[str, Any], ...] = (
    {
        "id": "CHK-TARGET-TEMP",
        "order": 1,
        "required": True,
        "title": "Name a new temp directory",
        "detail": (
            "The restore target must be a new empty temp directory. "
            "Production, NAS, and B2 are not targets. This framework does not create the directory."
        ),
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-SOURCE-IDENTITY",
        "order": 2,
        "required": True,
        "title": "Record the backup identity",
        "detail": (
            "Record the object key or local path that would be copied. "
            "A backup-health flag is not a restore. This framework does not read the object."
        ),
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-NO-NAS-DELETE",
        "order": 3,
        "required": True,
        "title": "Do not delete or overwrite NAS",
        "detail": "No delete, purge, or overwrite on NAS. This framework does not contact NAS.",
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-NO-B2-DELETE",
        "order": 4,
        "required": True,
        "title": "Do not delete or overwrite B2",
        "detail": "No delete, lifecycle expiry, or overwrite on B2. This framework does not contact B2.",
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-NO-PRODUCTION",
        "order": 5,
        "required": True,
        "title": "Do not write Production",
        "detail": "No write to Production, money.sqlite, or a production path. This framework does not do that write.",
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-COPY-TEMP",
        "order": 6,
        "required": True,
        "title": "Copy one non-secret object into temp",
        "detail": "A later drill may copy one non-secret object into the temp directory. This framework does not copy it.",
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-SHA256",
        "order": 7,
        "required": True,
        "title": "Compare the temp copy to the source",
        "detail": (
            "A later drill may compare a checksum. The 2026-08-29 historical note is not this comparison. "
            "This framework does not compare bytes."
        ),
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-SECRETS",
        "order": 8,
        "required": True,
        "title": "Do not write secret contents",
        "detail": "Secret contents stay unread and unwritten. This framework does not list or restore them.",
        "executed": False,
        "result": NOT_RUN,
    },
    {
        "id": "CHK-LOG-NOT-RUN",
        "order": 9,
        "required": True,
        "title": "Leave the drill log unrun",
        "detail": (
            "The log status stays NOT_RUN until a later authorised drill records a real result elsewhere. "
            "This framework does not write that result and does not claim the capability is ready."
        ),
        "executed": False,
        "result": NOT_RUN,
    },
)

TIERS: tuple[dict[str, Any], ...] = (
    {
        "id": "TIER-CROWN",
        "name": "Crown jewel",
        "rto": None,
        "rpo": None,
        "slot": "EMPTY",
        "why": "The catalog requires a tier. This framework does not invent a duration.",
    },
    {
        "id": "TIER-OPS",
        "name": "Operating systems",
        "rto": None,
        "rpo": None,
        "slot": "EMPTY",
        "why": "The catalog requires a tier. This framework does not invent a duration.",
    },
    {
        "id": "TIER-BULK",
        "name": "Bulk archives",
        "rto": None,
        "rpo": None,
        "slot": "EMPTY",
        "why": "The catalog requires a tier. This framework does not invent a duration.",
    },
)

STORES: tuple[dict[str, Any], ...] = (
    {"id": "NAS", "contacted": False, "destructive": False},
    {"id": "B2", "contacted": False, "destructive": False},
    {"id": "PRODUCTION", "contacted": False, "destructive": False},
)

HISTORICAL = {
    "id": "B2-RESTORE-DRILL-2026-08-29",
    "document": "docs/deliveries/CAP-DR-01-B2-RESTORE-DRILL-2026-08-29-BOUND.md",
    "is_this_drill": False,
    "counts_as_live_success": False,
    "counts_as_ready": False,
    "why": "Retained as history only. Owner kept the ledger unraised on 2026-09-18. It is not this drill.",
}

HONESTY = {
    "cap": CAP_ID,
    "slice": "restore_drill",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "live_restore": False,
    "production_mutated": False,
    "nas_destructive": False,
    "b2_destructive": False,
    "secrets_written": False,
    "source_deleted": False,
    "score_changed": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
    "evidence_invented": False,
}


class RestoreDrillError(ValueError):
    """Fail closed. Does not restore, delete, or invent a result."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_live_restore(_body: dict | None = None) -> None:
    """A live restore is not this slice."""
    raise RestoreDrillError(
        "Live restore is refused. This framework does not copy or restore bytes.",
        code="live_restore_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production stays untouched."""
    raise RestoreDrillError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_nas(_body: dict | None = None) -> None:
    """NAS is not contacted, deleted, or overwritten."""
    raise RestoreDrillError(
        "Destructive NAS access is refused. This framework does not contact NAS.",
        code="nas_destructive_refused",
    )


def refuse_b2(_body: dict | None = None) -> None:
    """B2 is not contacted, deleted, or overwritten."""
    raise RestoreDrillError(
        "Destructive B2 access is refused. This framework does not contact B2.",
        code="b2_destructive_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    """READY is not claimed by a skeleton."""
    raise RestoreDrillError(
        "READY is refused. This framework does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    """A higher maturity word is not invented."""
    raise RestoreDrillError(
        "A maturity raise is refused. This framework does not invent one.",
        code="proven_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    _reject_claims(payload)
    action = str(payload.get("action") or payload.get("op") or "").strip().lower()
    if payload.get("restore") or payload.get("live_restore") or payload.get("run") or action in {
        "restore",
        "run",
        "execute",
        "copy",
        "copyto",
    }:
        refuse_live_restore(payload)
    if payload.get("production") or payload.get("production_mutate") or action == "production":
        refuse_production(payload)
    if payload.get("nas") or payload.get("nas_delete") or action == "nas":
        refuse_nas(payload)
    if payload.get("b2") or payload.get("b2_delete") or action == "b2":
        refuse_b2(payload)
    if payload.get("ready") or action == "ready":
        refuse_ready(payload)
    if payload.get("proven") or action == "proven":
        refuse_proven(payload)
    delete = str(payload.get("delete") or payload.get("purge") or "").strip().lower()
    if "nas" in delete:
        refuse_nas(payload)
    if "b2" in delete or "backblaze" in delete:
        refuse_b2(payload)
    if delete or payload.get("rclone") or payload.get("overwrite"):
        raise RestoreDrillError(
            "Restore drill is read-only. No delete and no restore.",
            code="writes_refused",
        )
    raise RestoreDrillError(
        "Restore drill is read-only. No live restore, no Production write, no NAS or B2 delete.",
        code="writes_refused",
    )


def _truthy(value: str | None) -> bool:
    token = (value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def guard_query(
    *,
    restore: str | None = None,
    run: str | None = None,
    delete: str | None = None,
    nas: str | None = None,
    b2: str | None = None,
    production: str | None = None,
    ready: str | None = None,
    proven: str | None = None,
) -> None:
    """A read that asks to restore or delete is still a write. Refuse it."""
    if _truthy(restore) or _truthy(run):
        refuse_live_restore()
    if _truthy(nas):
        refuse_nas()
    if _truthy(b2):
        refuse_b2()
    if _truthy(production):
        refuse_production()
    if _truthy(ready):
        refuse_ready()
    if _truthy(proven):
        refuse_proven()
    if _truthy(delete):
        token = (delete or "").strip().lower()
        if "nas" in token:
            refuse_nas()
        if "b2" in token or "backblaze" in token:
            refuse_b2()
        raise RestoreDrillError(
            "Restore drill is read-only. No delete and no restore.",
            code="writes_refused",
        )


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise RestoreDrillError("restore drill refuses an Alchemist path", code="alchemist_refused")
    if low.startswith("b2:") or "b2://" in low or "backblaze" in low:
        raise RestoreDrillError("restore drill refuses a B2 path", code="b2_destructive_refused")
    if low.startswith("nas:") or "/nas/" in low or low.startswith("nas/"):
        raise RestoreDrillError("restore drill refuses a NAS path", code="nas_destructive_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise RestoreDrillError("restore drill refuses a production path", code="production_refused")
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
        raise RestoreDrillError(
            "restore drill refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise RestoreDrillError("restore drill refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-DR-01 from the ledger. Does not write it."""
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
    """Read CR-667f31959d1bbe82. Does not upsert, resolve, or harvest."""
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
    flags["live_restore"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def checklist() -> list[dict[str, Any]]:
    """The documented steps. None of them have been executed by this module."""
    return [{key: row[key] for key in STEP_FIELDS} for row in CHECKLIST]


def drill_log_schema() -> dict[str, Any]:
    """Machine-readable schema. The only accepted status is NOT_RUN."""
    return {
        "schema_id": SCHEMA_ID,
        "type": "object",
        "additionalProperties": False,
        "required": list(LOG_FIELDS),
        "status_enum": [NOT_RUN],
        "refused_status": sorted(_SUCCESS_STATUS | {"READY", "PROVEN"}),
        "properties": {
            "schema_id": {"const": SCHEMA_ID},
            "cap": {"const": CAP_ID},
            "drill_id": {"type": "null"},
            "recorded_at": {"type": "null"},
            "status": {"enum": [NOT_RUN]},
            "live_restore": {"const": False},
            "production_mutated": {"const": False},
            "nas_destructive": {"const": False},
            "b2_destructive": {"const": False},
            "secrets_written": {"const": False},
            "source_deleted": {"const": False},
            "ready_claimed": {"const": False},
            "proven_claimed": {"const": False},
            "historical_counts_as_this_drill": {"const": False},
            "checklist": {"type": "array", "minItems": len(CHECKLIST), "maxItems": len(CHECKLIST)},
            "result": {"enum": [NOT_RUN]},
        },
    }


def not_run_log() -> dict[str, Any]:
    """The only log this framework emits. It records that nothing ran."""
    return {
        "schema_id": SCHEMA_ID,
        "cap": CAP_ID,
        "drill_id": None,
        "recorded_at": None,
        "status": NOT_RUN,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "secrets_written": False,
        "source_deleted": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "historical_counts_as_this_drill": False,
        "checklist": checklist(),
        "result": NOT_RUN,
    }


def _status_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _flag(payload: dict[str, Any], key: str) -> bool:
    return payload.get(key) is True


def _checklist_executed(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("executed") is True:
            return True
        if _status_token(item.get("result")) in _SUCCESS_STATUS:
            return True
    return False


def _reject_claims(payload: dict[str, Any]) -> None:
    """A claimed success is refused. It is not rewritten into a pass."""
    if not isinstance(payload, dict):
        return
    status = _status_token(payload.get("status"))
    result = _status_token(payload.get("result"))
    if _flag(payload, "live_restore") or _checklist_executed(payload.get("checklist")):
        refuse_live_restore(payload)
    if _flag(payload, "production_mutated") or status == "PRODUCTION":
        refuse_production(payload)
    if _flag(payload, "nas_destructive"):
        refuse_nas(payload)
    if _flag(payload, "b2_destructive"):
        refuse_b2(payload)
    if _flag(payload, "ready_claimed") or status == "READY" or result == "READY":
        refuse_ready(payload)
    if _flag(payload, "proven_claimed") or status == "PROVEN" or result == "PROVEN":
        refuse_proven(payload)
    if status in _SUCCESS_STATUS or result in _SUCCESS_STATUS:
        raise RestoreDrillError(
            "A restore success is refused. This framework does not record one.",
            code="success_refused",
        )
    if _flag(payload, "secrets_written") or _flag(payload, "source_deleted"):
        raise RestoreDrillError(
            "Restore drill is read-only. Secrets stay unwritten and sources stay in place.",
            code="writes_refused",
        )
    if payload.get("historical_counts_as_this_drill") is True:
        raise RestoreDrillError(
            "The historical drill is not this proof.",
            code="historical_not_proof",
        )


def validate_log(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Accept only the NOT_RUN log. Anything else fails closed."""
    if not isinstance(payload, dict):
        raise RestoreDrillError("Drill log must be an object.", code="bad_log")
    _reject_claims(payload)
    missing = [name for name in LOG_FIELDS if name not in payload]
    if missing:
        raise RestoreDrillError("Drill log is missing required fields.", code="bad_log")
    extra = [name for name in payload if name not in LOG_FIELDS]
    if extra:
        raise RestoreDrillError("Drill log has fields this schema does not allow.", code="bad_log")
    if payload.get("schema_id") != SCHEMA_ID or payload.get("cap") != CAP_ID:
        raise RestoreDrillError("Drill log is not this schema.", code="bad_log")
    if payload.get("drill_id") is not None or payload.get("recorded_at") is not None:
        raise RestoreDrillError(
            "This framework does not assign a drill id or a recorded time.",
            code="bad_log",
        )
    if payload.get("status") != NOT_RUN or payload.get("result") != NOT_RUN:
        raise RestoreDrillError("Drill log status must stay NOT_RUN.", code="bad_log")
    for key in (
        "live_restore",
        "production_mutated",
        "nas_destructive",
        "b2_destructive",
        "secrets_written",
        "source_deleted",
        "ready_claimed",
        "proven_claimed",
        "historical_counts_as_this_drill",
    ):
        if payload.get(key) is not False:
            raise RestoreDrillError("Drill log flags must stay false.", code="bad_log")
    if payload.get("checklist") != checklist():
        raise RestoreDrillError("Checklist does not match the framework.", code="bad_log")
    return {
        "ok": True,
        "valid": True,
        "cap": CAP_ID,
        "status": NOT_RUN,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "log": payload,
    }


def read_step(
    step_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One checklist step. An unknown id is not invented."""
    token = (step_id or "").strip()
    upper = token.upper()
    if upper in {"RUN", "RESTORE", "EXECUTE", "SUCCESS", "RESTORED"}:
        refuse_live_restore()
    if upper in {"NAS", "NAS-DELETE"}:
        refuse_nas()
    if upper in {"B2", "B2-DELETE"}:
        refuse_b2()
    if upper in {"PRODUCTION", "PROD"}:
        refuse_production()
    if upper == "READY":
        refuse_ready()
    if upper == "PROVEN":
        refuse_proven()
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "EXPORT"}:
        raise RestoreDrillError("That path is not a checklist step.", code="not_found")
    flags = honesty_flags(ledger_path, catalog_db)
    for row in checklist():
        if row["id"] == token:
            return {
                "ok": True,
                "cap": CAP_ID,
                "step": row,
                "live_restore": False,
                "ledger_write": False,
                "honesty": flags,
            }
    raise RestoreDrillError(
        "Checklist step was not in the framework. It was not invented.",
        code="not_found",
    )


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Read-only framework. The log inside it is NOT_RUN."""
    flags = honesty_flags(ledger_path, catalog_db)
    steps = checklist()
    log = not_run_log()
    checked = validate_log(log)
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "restore_drill",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "ledger_write": False,
        "external_writes": False,
        "status": NOT_RUN,
        "checklist_count": len(steps),
        "checklist_executed": 0,
        "checklist": steps,
        "schema": drill_log_schema(),
        "log": log,
        "log_valid": checked["valid"] is True and checked["status"] == NOT_RUN,
        "tiers": [dict(row) for row in TIERS],
        "stores": [dict(row) for row in STORES],
        "historical": dict(HISTORICAL),
        "honesty": flags,
    }
