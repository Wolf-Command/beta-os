#!/usr/bin/env python3
"""CAP-DR-02 independent failure-domain prove (Beta, read-only).

Decision served: 2026-09-20 PICK, independent failure-domain prove on Beta only
(docs/deliveries/GROK-PLAN-DR-FAILURE-DOMAINS-PROVE-2026-09-19.md).

Names Beta and Production as separate failure domains and leaves every
independence slot empty. It does not run a restore, contact NAS or B2, write
Production, or invent PROVEN or READY.

Honesty is bound to CR-01fc21cfe028333b when that row is present. Ledger
maturity is read, not written. The skeleton ceiling is BUILT unless the
ledger is already PROVEN or READY.
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

CR_ID = "CR-01fc21cfe028333b"
CAP_ID = "CAP-DR-02"
SCHEMA_ID = "wolf.cap-dr-02.failure-domain-log.v1"
NOT_RUN = "NOT_RUN"
EMPTY = "EMPTY"

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

LOG_FIELDS = (
    "schema_id",
    "cap",
    "prove_id",
    "recorded_at",
    "status",
    "live_restore",
    "production_mutated",
    "nas_destructive",
    "b2_destructive",
    "beta_equals_production",
    "domains_collapsed",
    "independence_proved",
    "slots_filled",
    "playbook_read",
    "playbook_copied",
    "ready_claimed",
    "proven_claimed",
    "checklist",
    "domains",
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

DOMAIN_FIELDS = (
    "id",
    "name",
    "order",
    "role",
    "contacted",
    "mutated",
    "independence_proved",
    "slot",
    "distinct_from",
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
    "PROVED",
    "INDEPENDENT",
    "FILLED",
})

CHECKLIST: tuple[dict[str, Any], ...] = (
    {
        "id": "CHK-NAME-BETA",
        "order": 1,
        "required": True,
        "title": "Name Beta as its own failure domain",
        "detail": (
            "Beta is a named failure domain. Naming it is not a failover test. "
            "This framework does not probe the Beta listener."
        ),
    },
    {
        "id": "CHK-NAME-PRODUCTION",
        "order": 2,
        "required": True,
        "title": "Name Production as a separate failure domain",
        "detail": (
            "Production is a different failure domain from Beta. "
            "This framework does not open Production and does not write it."
        ),
    },
    {
        "id": "CHK-BETA-NE-PRODUCTION",
        "order": 3,
        "required": True,
        "title": "Record that Beta is not Production",
        "detail": (
            "The split is documented. The independence slot stays empty. "
            "A shared host is not evidence that one failure takes the other, and it is not a proof that it does not."
        ),
    },
    {
        "id": "CHK-NO-COLLAPSE",
        "order": 4,
        "required": True,
        "title": "Do not collapse Beta and Production into one domain",
        "detail": "A payload that marks them as the same failure domain is refused. This framework does not collapse them.",
    },
    {
        "id": "CHK-NO-LIVE-RESTORE",
        "order": 5,
        "required": True,
        "title": "Do not run a live restore",
        "detail": "No copy, no restore, and no drill execution. This framework does not move bytes.",
    },
    {
        "id": "CHK-NO-NAS",
        "order": 6,
        "required": True,
        "title": "Do not contact NAS",
        "detail": "NAS is a named domain only. No delete, purge, or overwrite. This framework does not contact NAS.",
    },
    {
        "id": "CHK-NO-B2",
        "order": 7,
        "required": True,
        "title": "Do not contact B2",
        "detail": "B2 is a named domain only. No delete, lifecycle expiry, or overwrite. This framework does not contact B2.",
    },
    {
        "id": "CHK-NO-PRODUCTION-WRITE",
        "order": 8,
        "required": True,
        "title": "Do not write Production",
        "detail": "No write to Production, money.sqlite, or a production path. This framework does not do that write.",
    },
    {
        "id": "CHK-INDEPENDENCE-SLOT",
        "order": 9,
        "required": True,
        "title": "Leave the independence proof empty",
        "detail": (
            "An empty slot is not a passed failover. "
            "This framework does not invent a correlation result or a failure injection."
        ),
    },
    {
        "id": "CHK-PLAYBOOK-UNREAD",
        "order": 10,
        "required": True,
        "title": "Leave the Matt-only playbook unread",
        "detail": (
            "The full backup playbook stays Matt-only. "
            "This framework does not open it and does not copy it into the checklist."
        ),
    },
)

DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "DOMAIN-BETA",
        "name": "Beta",
        "order": 1,
        "role": "Beta process and tree. Named here. Not probed.",
        "distinct_from": ("DOMAIN-PRODUCTION", "DOMAIN-NAS", "DOMAIN-B2"),
    },
    {
        "id": "DOMAIN-PRODUCTION",
        "name": "Production",
        "order": 2,
        "role": "Production process and tree. Named as separate. Not opened.",
        "distinct_from": ("DOMAIN-BETA", "DOMAIN-NAS", "DOMAIN-B2"),
    },
    {
        "id": "DOMAIN-NAS",
        "name": "NAS",
        "order": 3,
        "role": "NAS store. Named only. Not contacted.",
        "distinct_from": ("DOMAIN-BETA", "DOMAIN-PRODUCTION", "DOMAIN-B2"),
    },
    {
        "id": "DOMAIN-B2",
        "name": "B2",
        "order": 4,
        "role": "B2 store. Named only. Not contacted.",
        "distinct_from": ("DOMAIN-BETA", "DOMAIN-PRODUCTION", "DOMAIN-NAS"),
    },
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "failure_domains",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "live_restore": False,
    "production_mutated": False,
    "nas_destructive": False,
    "b2_destructive": False,
    "beta_equals_production": False,
    "domains_collapsed": False,
    "independence_proved": False,
    "slots_filled": False,
    "playbook_read": False,
    "playbook_copied": False,
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


class FailureDomainError(ValueError):
    """Fail closed. Does not restore, collapse domains, or fill a slot."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_live_restore(_body: dict | None = None) -> None:
    """A live restore is not this slice."""
    raise FailureDomainError(
        "Live restore is refused. This framework does not copy or restore bytes.",
        code="live_restore_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production stays untouched."""
    raise FailureDomainError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_nas(_body: dict | None = None) -> None:
    """NAS is not contacted, deleted, or overwritten."""
    raise FailureDomainError(
        "Destructive NAS access is refused. This framework does not contact NAS.",
        code="nas_destructive_refused",
    )


def refuse_b2(_body: dict | None = None) -> None:
    """B2 is not contacted, deleted, or overwritten."""
    raise FailureDomainError(
        "Destructive B2 access is refused. This framework does not contact B2.",
        code="b2_destructive_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    """READY is not claimed by a skeleton."""
    raise FailureDomainError(
        "READY is refused. This framework does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    """A higher maturity word is not invented."""
    raise FailureDomainError(
        "A maturity raise is refused. This framework does not invent one.",
        code="proven_refused",
    )


def refuse_collapse(_body: dict | None = None) -> None:
    """Beta and Production stay separate names. They are not one domain."""
    raise FailureDomainError(
        "Collapsing Beta and Production into one failure domain is refused.",
        code="collapse_refused",
    )


def refuse_independence(_body: dict | None = None) -> None:
    """An empty slot is not a passed independence proof."""
    raise FailureDomainError(
        "An independence proof is refused. The slot stays empty.",
        code="independence_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Slots are not filled by this framework."""
    raise FailureDomainError(
        "Failure-domain slots stay empty. This framework does not fill them.",
        code="slots_refused",
    )


def refuse_playbook(_body: dict | None = None) -> None:
    """The Matt-only playbook is not opened or copied."""
    raise FailureDomainError(
        "The Matt-only playbook stays unread. This framework does not copy it.",
        code="playbook_refused",
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
    }:
        refuse_live_restore(payload)
    if payload.get("production") or payload.get("production_mutate") or action == "production":
        refuse_production(payload)
    if payload.get("nas") or payload.get("nas_delete") or action == "nas":
        refuse_nas(payload)
    if payload.get("b2") or payload.get("b2_delete") or action == "b2":
        refuse_b2(payload)
    if payload.get("collapse") or payload.get("beta_equals_production") or payload.get("domains_collapsed") or action == "collapse":
        refuse_collapse(payload)
    if payload.get("prove") or payload.get("independence") or payload.get("independence_proved") or action in {
        "prove",
        "independence",
    }:
        refuse_independence(payload)
    if payload.get("fill") or payload.get("slots_filled") or action == "fill":
        refuse_fill(payload)
    if payload.get("playbook") or payload.get("playbook_read") or payload.get("playbook_copied") or action == "playbook":
        refuse_playbook(payload)
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
        raise FailureDomainError(
            "Failure-domain prove is read-only. No delete and no restore.",
            code="writes_refused",
        )
    raise FailureDomainError(
        "Failure-domain prove is read-only. No live restore, no Production write, no NAS or B2 delete, no filled slot.",
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
    prove: str | None = None,
    collapse: str | None = None,
    fill: str | None = None,
    playbook: str | None = None,
) -> None:
    """A read that asks to restore, prove, or fill is still a write. Refuse it."""
    if _truthy(restore) or _truthy(run):
        refuse_live_restore()
    if _truthy(nas):
        refuse_nas()
    if _truthy(b2):
        refuse_b2()
    if _truthy(production):
        refuse_production()
    if _truthy(collapse):
        refuse_collapse()
    if _truthy(prove):
        refuse_independence()
    if _truthy(fill):
        refuse_fill()
    if _truthy(playbook):
        refuse_playbook()
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
        raise FailureDomainError(
            "Failure-domain prove is read-only. No delete and no restore.",
            code="writes_refused",
        )


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise FailureDomainError("failure domains refuses an Alchemist path", code="alchemist_refused")
    if low.startswith("b2:") or "b2://" in low or "backblaze" in low:
        raise FailureDomainError("failure domains refuses a B2 path", code="b2_destructive_refused")
    if low.startswith("nas:") or "/nas/" in low or low.startswith("nas/"):
        raise FailureDomainError("failure domains refuses a NAS path", code="nas_destructive_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise FailureDomainError("failure domains refuses a production path", code="production_refused")
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
        raise FailureDomainError(
            "failure domains refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise FailureDomainError("failure domains refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-DR-02 from the ledger. Does not write it."""
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
    """Read CR-01fc21cfe028333b. Does not upsert, resolve, or harvest."""
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
    flags["independence_proved"] = False
    flags["beta_equals_production"] = False
    flags["domains_collapsed"] = False
    flags["slots_filled"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def checklist() -> list[dict[str, Any]]:
    """The documented steps. None of them have been executed. Every slot is empty."""
    rows: list[dict[str, Any]] = []
    for row in CHECKLIST:
        item = {key: row[key] for key in STEP_FIELDS if key in row}
        item["executed"] = False
        item["result"] = NOT_RUN
        item["slot"] = EMPTY
        rows.append(item)
    return rows


def domain_rows() -> list[dict[str, Any]]:
    """Named domains. None were contacted. Independence is not proved. Slots stay empty."""
    rows: list[dict[str, Any]] = []
    for row in DOMAINS:
        rows.append(
            {
                "id": row["id"],
                "name": row["name"],
                "order": row["order"],
                "role": row["role"],
                "contacted": False,
                "mutated": False,
                "independence_proved": False,
                "slot": EMPTY,
                "distinct_from": list(row["distinct_from"]),
            }
        )
    return rows


def separation() -> dict[str, Any]:
    """Beta and Production are named as different domains. The prove slot is empty."""
    return {
        "beta": "DOMAIN-BETA",
        "production": "DOMAIN-PRODUCTION",
        "beta_equals_production": False,
        "same_failure_domain": False,
        "separation": "DOCUMENTED",
        "independence_proved": False,
        "slot": EMPTY,
        "why": (
            "Spec section 25 separates development, Beta, and production. "
            "This framework records that Beta is not Production. "
            "It does not inject a failure and it does not prove independence."
        ),
    }


def playbook() -> dict[str, Any]:
    """The Matt-only playbook is cited as unread. It is not opened."""
    return {
        "id": "MATT-ONLY-PLAYBOOK",
        "read": False,
        "copied": False,
        "slot": EMPTY,
        "why": "Spec section 25 keeps the full backup playbook Matt-only. This framework does not open it.",
    }


def prove_log_schema() -> dict[str, Any]:
    """Machine-readable schema. The only accepted status is NOT_RUN. Slots stay empty."""
    return {
        "schema_id": SCHEMA_ID,
        "type": "object",
        "additionalProperties": False,
        "required": list(LOG_FIELDS),
        "status_enum": [NOT_RUN],
        "slot_enum": [EMPTY],
        "refused_status": sorted(_SUCCESS_STATUS | {"READY", "PROVEN"}),
        "properties": {
            "schema_id": {"const": SCHEMA_ID},
            "cap": {"const": CAP_ID},
            "prove_id": {"type": "null"},
            "recorded_at": {"type": "null"},
            "status": {"enum": [NOT_RUN]},
            "live_restore": {"const": False},
            "production_mutated": {"const": False},
            "nas_destructive": {"const": False},
            "b2_destructive": {"const": False},
            "beta_equals_production": {"const": False},
            "domains_collapsed": {"const": False},
            "independence_proved": {"const": False},
            "slots_filled": {"const": False},
            "playbook_read": {"const": False},
            "playbook_copied": {"const": False},
            "ready_claimed": {"const": False},
            "proven_claimed": {"const": False},
            "checklist": {"type": "array", "minItems": len(CHECKLIST), "maxItems": len(CHECKLIST)},
            "domains": {"type": "array", "minItems": len(DOMAINS), "maxItems": len(DOMAINS)},
            "result": {"enum": [NOT_RUN]},
        },
    }


def not_run_log() -> dict[str, Any]:
    """The only log this framework emits. It records that nothing ran and no slot was filled."""
    return {
        "schema_id": SCHEMA_ID,
        "cap": CAP_ID,
        "prove_id": None,
        "recorded_at": None,
        "status": NOT_RUN,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "beta_equals_production": False,
        "domains_collapsed": False,
        "independence_proved": False,
        "slots_filled": False,
        "playbook_read": False,
        "playbook_copied": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "checklist": checklist(),
        "domains": domain_rows(),
        "result": NOT_RUN,
    }


def _status_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _flag(payload: dict[str, Any], key: str) -> bool:
    return payload.get(key) is True


def _rows_dirty(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("executed") is True:
            return "live_restore"
        if _status_token(item.get("result")) in _SUCCESS_STATUS:
            return "live_restore"
        slot = item.get("slot")
        if slot is not None and slot != EMPTY:
            return "slots"
        if item.get("independence_proved") is True:
            return "independence"
        if item.get("contacted") is True or item.get("mutated") is True:
            name = str(item.get("id") or "")
            if "NAS" in name:
                return "nas"
            if "B2" in name:
                return "b2"
            if "PRODUCTION" in name:
                return "production"
            return "write"
        distinct = item.get("distinct_from")
        if isinstance(distinct, list) and not distinct and item.get("id") in {"DOMAIN-BETA", "DOMAIN-PRODUCTION"}:
            return "collapse"
    return None


def _reject_claims(payload: dict[str, Any]) -> None:
    """A claimed success, collapse, or filled slot is refused. It is not rewritten into a pass."""
    if not isinstance(payload, dict):
        return
    status = _status_token(payload.get("status"))
    result = _status_token(payload.get("result"))
    dirty = _rows_dirty(payload.get("checklist")) or _rows_dirty(payload.get("domains"))
    if _flag(payload, "live_restore") or dirty == "live_restore":
        refuse_live_restore(payload)
    if _flag(payload, "production_mutated") or status == "PRODUCTION" or dirty == "production":
        refuse_production(payload)
    if _flag(payload, "nas_destructive") or dirty == "nas":
        refuse_nas(payload)
    if _flag(payload, "b2_destructive") or dirty == "b2":
        refuse_b2(payload)
    if dirty == "write":
        raise FailureDomainError(
            "Failure-domain prove is read-only. Domains are named, not contacted.",
            code="writes_refused",
        )
    if (
        _flag(payload, "beta_equals_production")
        or _flag(payload, "domains_collapsed")
        or dirty == "collapse"
        or status == "COLLAPSED"
    ):
        refuse_collapse(payload)
    if (
        _flag(payload, "independence_proved")
        or dirty == "independence"
        or status in {"PROVED", "INDEPENDENT"}
        or result in {"PROVED", "INDEPENDENT"}
    ):
        refuse_independence(payload)
    if _flag(payload, "ready_claimed") or status == "READY" or result == "READY":
        refuse_ready(payload)
    if _flag(payload, "proven_claimed") or status == "PROVEN" or result == "PROVEN":
        refuse_proven(payload)
    if _flag(payload, "slots_filled") or dirty == "slots" or status == "FILLED" or result == "FILLED":
        refuse_fill(payload)
    if _flag(payload, "playbook_read") or _flag(payload, "playbook_copied"):
        refuse_playbook(payload)
    if status in _SUCCESS_STATUS or result in _SUCCESS_STATUS:
        raise FailureDomainError(
            "A failure-domain success is refused. This framework does not record one.",
            code="success_refused",
        )


def validate_log(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Accept only the NOT_RUN log. Anything else fails closed."""
    if not isinstance(payload, dict):
        raise FailureDomainError("Failure-domain log must be an object.", code="bad_log")
    _reject_claims(payload)
    missing = [name for name in LOG_FIELDS if name not in payload]
    if missing:
        raise FailureDomainError("Failure-domain log is missing required fields.", code="bad_log")
    extra = [name for name in payload if name not in LOG_FIELDS]
    if extra:
        raise FailureDomainError("Failure-domain log has fields this schema does not allow.", code="bad_log")
    if payload.get("schema_id") != SCHEMA_ID or payload.get("cap") != CAP_ID:
        raise FailureDomainError("Failure-domain log is not this schema.", code="bad_log")
    if payload.get("prove_id") is not None or payload.get("recorded_at") is not None:
        raise FailureDomainError(
            "This framework does not assign a prove id or a recorded time.",
            code="bad_log",
        )
    if payload.get("status") != NOT_RUN or payload.get("result") != NOT_RUN:
        raise FailureDomainError("Failure-domain log status must stay NOT_RUN.", code="bad_log")
    for key in (
        "live_restore",
        "production_mutated",
        "nas_destructive",
        "b2_destructive",
        "beta_equals_production",
        "domains_collapsed",
        "independence_proved",
        "slots_filled",
        "playbook_read",
        "playbook_copied",
        "ready_claimed",
        "proven_claimed",
    ):
        if payload.get(key) is not False:
            raise FailureDomainError("Failure-domain log flags must stay false.", code="bad_log")
    if payload.get("checklist") != checklist():
        raise FailureDomainError("Checklist does not match the framework.", code="bad_log")
    if payload.get("domains") != domain_rows():
        raise FailureDomainError("Domains do not match the framework.", code="bad_log")
    return {
        "ok": True,
        "valid": True,
        "cap": CAP_ID,
        "status": NOT_RUN,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "beta_equals_production": False,
        "independence_proved": False,
        "slots_filled": False,
        "ready_claimed": False,
        "proven_claimed": False,
        "log": payload,
    }


def _refuse_token(upper: str) -> None:
    if upper in {"RUN", "RESTORE", "EXECUTE"}:
        refuse_live_restore()
    if upper in {"NAS", "NAS-DELETE"}:
        refuse_nas()
    if upper in {"B2", "B2-DELETE"}:
        refuse_b2()
    if upper in {"PRODUCTION", "PROD"}:
        refuse_production()
    if upper in {"COLLAPSE", "SAME"}:
        refuse_collapse()
    if upper in {"PROVE", "PROVED", "INDEPENDENT", "INDEPENDENCE"}:
        refuse_independence()
    if upper in {"FILL", "FILLED"}:
        refuse_fill()
    if upper in {"PLAYBOOK", "MATT-ONLY-PLAYBOOK"}:
        refuse_playbook()
    if upper == "READY":
        refuse_ready()
    if upper == "PROVEN":
        refuse_proven()


def read_step(
    step_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One checklist step. An unknown id is not invented."""
    token = (step_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "DOMAINS", "EXPORT"}:
        raise FailureDomainError("That path is not a checklist step.", code="not_found")
    flags = honesty_flags(ledger_path, catalog_db)
    for row in checklist():
        if row["id"] == token:
            return {
                "ok": True,
                "cap": CAP_ID,
                "step": row,
                "live_restore": False,
                "independence_proved": False,
                "ledger_write": False,
                "honesty": flags,
            }
    raise FailureDomainError(
        "Checklist step was not in the framework. It was not invented.",
        code="not_found",
    )


def read_domain(
    domain_id: str,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One named domain. An unknown id is not invented. The slot stays empty."""
    token = (domain_id or "").strip()
    upper = token.upper()
    _refuse_token(upper)
    if not token or upper in {"LOG", "SCHEMA", "CHECKLIST", "DOMAINS", "EXPORT"}:
        raise FailureDomainError("That path is not a failure domain.", code="not_found")
    flags = honesty_flags(ledger_path, catalog_db)
    for row in domain_rows():
        if row["id"] == token:
            return {
                "ok": True,
                "cap": CAP_ID,
                "domain": row,
                "beta_equals_production": False,
                "independence_proved": False,
                "live_restore": False,
                "ledger_write": False,
                "honesty": flags,
            }
    raise FailureDomainError(
        "Failure domain was not in the framework. It was not invented.",
        code="not_found",
    )


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Read-only framework. The log inside it is NOT_RUN and every slot is empty."""
    flags = honesty_flags(ledger_path, catalog_db)
    steps = checklist()
    named = domain_rows()
    log = not_run_log()
    checked = validate_log(log)
    split = separation()
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "failure_domains",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "live_restore": False,
        "production_mutated": False,
        "nas_destructive": False,
        "b2_destructive": False,
        "beta_equals_production": False,
        "domains_collapsed": False,
        "independence_proved": False,
        "slots_filled": False,
        "ledger_write": False,
        "external_writes": False,
        "status": NOT_RUN,
        "checklist_count": len(steps),
        "checklist_executed": 0,
        "empty_slot_count": len(steps) + len(named),
        "checklist": steps,
        "domains": named,
        "domain_count": len(named),
        "separation": split,
        "playbook": playbook(),
        "schema": prove_log_schema(),
        "log": log,
        "log_valid": checked["valid"] is True and checked["status"] == NOT_RUN,
        "honesty": flags,
    }
