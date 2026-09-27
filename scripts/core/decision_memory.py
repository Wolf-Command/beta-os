#!/usr/bin/env python3
"""Wolf Core Decision Memory v1 (Beta) — CAP-INTEL-04.

INSERT-only decision records + bounded recall.
Reuses the append-only habit of scripts/core/audit.py (no silent rewrite).
Does NOT replace the audit spine. Does NOT invent approvers, amounts, or outcomes.
Does NOT mint Approvals. Approval Engine stays the approval authority.

States: RECORDED | OUTCOME_UNKNOWN | NOT FOUND

Permissions (fail closed): decision.memory.read / decision.memory.record via
core.rbac.evaluate. Owner seed is the only live write path; it still calls
record_decision + audit.record_event (no second write path).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
# Dedicated Beta store — never Production / wolf-system / money.sqlite.
DEFAULT_DB = BETA_ROOT / "catalog" / "decision_memory.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
TZ_UTC = timezone.utc

RECALL_MAX = 50

PERM_READ = "decision.memory.read"
PERM_RECORD = "decision.memory.record"

STATUS_RECORDED = "RECORDED"
STATUS_OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
STATUS_NOT_FOUND = "NOT FOUND"

STATUSES = frozenset(
    {STATUS_RECORDED, STATUS_OUTCOME_UNKNOWN, STATUS_NOT_FOUND}
)

EMPTY_OPTIONS_REASON_OWNER = (
    "Owner stated the decision. No option list in the source."
)

HONESTY = {
    "decision_memory": "BUILT",
    "cap": "CAP-INTEL-04",
    "append_only": True,
    "silent_rewrite": False,
    "invent_approvers": False,
    "invent_amounts": False,
    "invent_outcomes": False,
    "replaces_audit": False,
    "recall_max": RECALL_MAX,
}


class DecisionMemoryError(ValueError):
    """Fail-closed validation for decision memory writes."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_decision_id() -> str:
    return f"DEC-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_db_writable(db_path: Path) -> None:
    """Refuse accidental live default DB writes from tests."""
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_DECISION_MEMORY") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise DecisionMemoryError(
            "test mode refuses writes to live decision_memory DB; "
            "point db_path at a temp file",
            code="live_guard",
        )


def _assert_beta_path(resolved: Path) -> None:
    s = str(resolved)
    if "beta-os" not in s:
        raise RuntimeError(f"decision_memory refuses non-beta DB: {resolved}")
    if "wolf-system" in s:
        raise RuntimeError(f"decision_memory refuses wolf-system path: {resolved}")
    if "/Production" in s or s.endswith("money.sqlite"):
        raise RuntimeError(f"decision_memory refuses production path: {resolved}")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS core_decision_memory (
  record_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  corrects_decision_id TEXT NULL,
  scope_entity TEXT NULL,
  scope_brand TEXT NULL,
  scope_object TEXT NULL,
  scope_raw TEXT NULL,
  title TEXT NOT NULL,
  options_json TEXT NOT NULL,
  empty_options_reason TEXT NULL,
  chosen_option TEXT NULL,
  approval_ref TEXT NULL,
  outcome TEXT NULL,
  status TEXT NOT NULL,
  actor TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  provenance_json TEXT NULL,
  query_keys_json TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_dm_decision_id ON core_decision_memory(decision_id);
CREATE INDEX IF NOT EXISTS idx_dm_scope_brand ON core_decision_memory(scope_brand);
CREATE INDEX IF NOT EXISTS idx_dm_scope_entity ON core_decision_memory(scope_entity);
CREATE INDEX IF NOT EXISTS idx_dm_occurred ON core_decision_memory(occurred_at);
CREATE INDEX IF NOT EXISTS idx_dm_corrects ON core_decision_memory(corrects_decision_id);

CREATE TRIGGER IF NOT EXISTS trg_core_decision_memory_no_update
BEFORE UPDATE ON core_decision_memory
BEGIN
  SELECT RAISE(ABORT, 'core_decision_memory is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_core_decision_memory_no_delete
BEFORE DELETE ON core_decision_memory
BEGIN
  SELECT RAISE(ABORT, 'core_decision_memory is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    cols = {
        str(r[1]) for r in conn.execute("PRAGMA table_info(core_decision_memory)")
    }
    if "query_keys_json" not in cols:
        conn.execute(
            "ALTER TABLE core_decision_memory ADD COLUMN query_keys_json TEXT"
        )
    conn.commit()


def db_connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _require_permission(
    permission_context: dict[str, Any] | None,
    permission_code: str,
) -> dict[str, Any]:
    """Fail closed unless rbac.evaluate allows the code for the caller."""
    from core import rbac as _rbac

    if not isinstance(permission_context, dict):
        raise DecisionMemoryError(
            "permission_context required", code="denied"
        )
    person_id = str(permission_context.get("person_id") or "").strip()
    if not person_id:
        raise DecisionMemoryError(
            "permission_context.person_id required", code="denied"
        )
    target = permission_context.get("target_context")
    if target is not None and not isinstance(target, dict):
        raise DecisionMemoryError(
            "permission_context.target_context must be a dict", code="denied"
        )
    rbac_conn = permission_context.get("rbac_conn")
    rbac_db_path = permission_context.get("rbac_db_path")
    own = False
    c = rbac_conn
    if c is None:
        path = Path(rbac_db_path) if rbac_db_path else None
        if path is not None:
            _assert_beta_path(path.resolve())
        c = _rbac.db_connect(path)
        own = True
    try:
        decision = _rbac.evaluate(
            person_id, permission_code, target, conn=c
        )
        if not decision.get("allowed"):
            raise DecisionMemoryError(
                f"denied {permission_code}: {decision.get('reason')}",
                code="denied",
            )
        return decision
    finally:
        if own:
            c.close()


def _audit_decision_recorded(
    *,
    decision_id: str,
    permission_context: dict[str, Any],
    occurred_at: str,
) -> None:
    """Append audit spine event. Does not modify audit history helpers."""
    from core import audit as _audit

    person_id = str(permission_context.get("person_id") or "").strip() or None
    audit_conn = permission_context.get("audit_conn")
    kwargs: dict[str, Any] = {
        "action": "decision.memory.record",
        "result": "SUCCEEDED",
        "source": "core.decision_memory",
        "resource_type": "decision",
        "resource_id": decision_id,
        "occurred_at": occurred_at,
        "metadata": {"decision": decision_id, "note": "decision recorded"},
        "commit": True,
    }
    if audit_conn is not None:
        kwargs["conn"] = audit_conn
    if person_id:
        kwargs["actor_type"] = "PERSON"
        kwargs["verified_person_id"] = person_id
        kwargs["actor_person_id"] = person_id
    else:
        kwargs["actor_type"] = "SYSTEM"
    _audit.record_event(**kwargs)


def _serialize_query_keys(query_keys: list[str] | None) -> str | None:
    if query_keys is None:
        return None
    if not isinstance(query_keys, list):
        raise DecisionMemoryError(
            "query_keys must be a list of strings", code="bad_query_keys"
        )
    cleaned: list[str] = []
    for k in query_keys:
        s = str(k).strip()
        if s:
            cleaned.append(s)
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))


def normalize_scope(scope: str | dict[str, Any] | None) -> dict[str, Any]:
    """Normalize entity/brand/object scope. Accepts 'brand:habitat' or dict."""
    if scope is None:
        return {"entity": None, "brand": None, "object": None, "raw": None}
    if isinstance(scope, str):
        raw = scope.strip()
        out: dict[str, Any] = {
            "entity": None,
            "brand": None,
            "object": None,
            "raw": raw,
        }
        if ":" in raw:
            kind, _, rest = raw.partition(":")
            kind = kind.strip().lower()
            rest = rest.strip().lower()
            if kind in ("entity", "brand", "object"):
                out[kind] = rest
            else:
                out["brand"] = raw.lower()
        else:
            # Multi-word Owner scopes (e.g. "Wolf system") → object token.
            token = raw.lower().replace(" / ", " ").replace("/", " ")
            token = " ".join(token.split())
            if " " in token:
                out["object"] = token.replace(" ", "-")
            else:
                out["brand"] = token
        return out
    if not isinstance(scope, dict):
        raise DecisionMemoryError("scope must be str or dict", code="bad_scope")
    return {
        "entity": _norm_id(scope.get("entity")),
        "brand": _norm_id(scope.get("brand")),
        "object": _norm_id(scope.get("object")),
        "raw": scope.get("raw"),
    }


def _norm_id(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    return s or None


def _outcome_status(outcome: str | None) -> str:
    """Empty / missing / explicit UNKNOWN → OUTCOME_UNKNOWN. Never invent."""
    if outcome is None:
        return STATUS_OUTCOME_UNKNOWN
    s = str(outcome).strip()
    if not s or s.upper() == "UNKNOWN":
        return STATUS_OUTCOME_UNKNOWN
    return STATUS_RECORDED


def _serialize_options(options_considered: list[Any]) -> str:
    if not isinstance(options_considered, list):
        raise DecisionMemoryError(
            "options_considered must be a list", code="bad_options"
        )
    return json.dumps(options_considered, ensure_ascii=False, separators=(",", ":"))


def _serialize_provenance(provenance: Any) -> str | None:
    if provenance is None:
        return None
    if isinstance(provenance, str):
        return provenance
    return json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))


def _row_to_dict(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    opts = d.get("options_json")
    try:
        d["options_considered"] = json.loads(opts) if opts else []
    except json.JSONDecodeError:
        d["options_considered"] = []
    prov = d.get("provenance_json")
    if isinstance(prov, str) and prov:
        try:
            d["provenance"] = json.loads(prov)
        except json.JSONDecodeError:
            d["provenance"] = prov
    else:
        d["provenance"] = None
    qk = d.get("query_keys_json")
    if isinstance(qk, str) and qk:
        try:
            parsed = json.loads(qk)
            d["query_keys"] = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            d["query_keys"] = []
    else:
        d["query_keys"] = []
    d["scope"] = {
        "entity": d.get("scope_entity"),
        "brand": d.get("scope_brand"),
        "object": d.get("scope_object"),
        "raw": d.get("scope_raw"),
    }
    return d


def update_decision(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError(
        "core_decision_memory is append-only; use correct_decision"
    )


def delete_decision(*_a, **_k):  # noqa: ANN001
    raise NotImplementedError(
        "core_decision_memory is append-only; corrections are INSERTs"
    )


def record_decision(
    *,
    title: str,
    scope: str | dict[str, Any],
    options_considered: list[Any],
    actor: str,
    chosen_option: str | None = None,
    approval_ref: str | None = None,
    outcome: str | None = None,
    occurred_at: str | None = None,
    provenance: Any = None,
    decision_id: str | None = None,
    corrects_decision_id: str | None = None,
    empty_options_reason: str | None = None,
    query_keys: list[str] | None = None,
    permission_context: dict[str, Any] | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """INSERT one decision record. Fail closed. Never invents outcome/approver.

    options_considered may be empty only when empty_options_reason is recorded.
    Missing/blank outcome → status OUTCOME_UNKNOWN (never invented).
    Requires permission_context that rbac.evaluate allows for decision.memory.record.
    """
    _require_permission(permission_context, PERM_RECORD)

    ttl = (title or "").strip()
    if not ttl:
        raise DecisionMemoryError("title required", code="bad_title")
    act = (actor or "").strip()
    if not act:
        raise DecisionMemoryError("actor required", code="bad_actor")

    if not isinstance(options_considered, list):
        raise DecisionMemoryError(
            "options_considered must be a list", code="bad_options"
        )
    if len(options_considered) == 0:
        reason = (empty_options_reason or "").strip()
        if not reason:
            raise DecisionMemoryError(
                "options_considered empty requires empty_options_reason",
                code="empty_options",
            )
    else:
        reason = (empty_options_reason or "").strip() or None

    # Never invent approval_ref — only store what caller supplied.
    appr = (approval_ref or "").strip() or None
    chosen = None if chosen_option is None else str(chosen_option).strip() or None

    # Outcome: store as given; blank/None → UNKNOWN status, value stays None.
    raw_outcome = outcome
    if raw_outcome is not None:
        raw_outcome = str(raw_outcome).strip()
        if not raw_outcome:
            raw_outcome = None
        elif raw_outcome.upper() == "UNKNOWN":
            # Explicit UNKNOWN is allowed; do not invent a concrete outcome.
            raw_outcome = "UNKNOWN"
    status = _outcome_status(raw_outcome)
    # Persist NULL for missing outcome; keep explicit "UNKNOWN" string if given.
    stored_outcome = raw_outcome

    sc = normalize_scope(scope)
    if not any((sc.get("entity"), sc.get("brand"), sc.get("object"))):
        raise DecisionMemoryError(
            "scope requires entity, brand, or object", code="bad_scope"
        )

    did = (decision_id or "").strip() or mint_decision_id()
    corrects = (corrects_decision_id or "").strip() or None
    ts = now_utc_iso()
    occurred = (occurred_at or "").strip() or ts
    record_id = str(uuid.uuid4())
    opts_json = _serialize_options(options_considered)
    prov_json = _serialize_provenance(provenance)
    qk_json = _serialize_query_keys(query_keys)

    own = conn is None
    c = conn or db_connect(db_path)
    try:
        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or DEFAULT_DB)
        assert_db_writable(db_file)

        if corrects:
            prior = c.execute(
                "SELECT decision_id FROM core_decision_memory WHERE decision_id=?",
                (corrects,),
            ).fetchone()
            if not prior:
                raise DecisionMemoryError(
                    f"corrects_decision_id not found: {corrects}",
                    code="prior_missing",
                )

        c.execute(
            """
            INSERT INTO core_decision_memory (
              record_id, decision_id, corrects_decision_id,
              scope_entity, scope_brand, scope_object, scope_raw,
              title, options_json, empty_options_reason, chosen_option,
              approval_ref, outcome, status, actor, occurred_at, recorded_at,
              provenance_json, query_keys_json
            ) VALUES (
              ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, ?, ?, ?, ?,
              ?, ?
            )
            """,
            (
                record_id,
                did,
                corrects,
                sc.get("entity"),
                sc.get("brand"),
                sc.get("object"),
                sc.get("raw"),
                ttl,
                opts_json,
                reason,
                chosen,
                appr,
                stored_outcome,
                status,
                act,
                occurred,
                ts,
                prov_json,
                qk_json,
            ),
        )
        if commit:
            c.commit()
        assert permission_context is not None
        _audit_decision_recorded(
            decision_id=did,
            permission_context=permission_context,
            occurred_at=occurred,
        )
        return get_decision(did, conn=c, db_path=db_path) or {
            "decision_id": did,
            "status": status,
        }
    finally:
        if own:
            c.close()


def correct_decision(
    prior_decision_id: str,
    *,
    title: str,
    scope: str | dict[str, Any],
    options_considered: list[Any],
    actor: str,
    chosen_option: str | None = None,
    approval_ref: str | None = None,
    outcome: str | None = None,
    occurred_at: str | None = None,
    provenance: Any = None,
    empty_options_reason: str | None = None,
    query_keys: list[str] | None = None,
    permission_context: dict[str, Any] | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """INSERT a correction row referencing a prior decision_id (append-only)."""
    return record_decision(
        title=title,
        scope=scope,
        options_considered=options_considered,
        actor=actor,
        chosen_option=chosen_option,
        approval_ref=approval_ref,
        outcome=outcome,
        occurred_at=occurred_at,
        provenance=provenance,
        corrects_decision_id=prior_decision_id,
        empty_options_reason=empty_options_reason,
        query_keys=query_keys,
        permission_context=permission_context,
        db_path=db_path,
        conn=conn,
    )


def get_decision(
    decision_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    did = (decision_id or "").strip()
    if not did:
        return None
    own = conn is None
    c = conn or db_connect(db_path)
    try:
        row = c.execute(
            "SELECT * FROM core_decision_memory WHERE decision_id=?",
            (did,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        if own:
            c.close()


def _scope_clause(
    scope: dict[str, Any],
) -> tuple[str, list[Any]]:
    """Build WHERE fragments that isolate by requested scope dimensions."""
    clauses: list[str] = []
    params: list[Any] = []
    brand = scope.get("brand")
    entity = scope.get("entity")
    obj = scope.get("object")
    if brand:
        clauses.append("scope_brand=?")
        params.append(brand)
    if entity:
        clauses.append("scope_entity=?")
        params.append(entity)
    if obj:
        clauses.append("scope_object=?")
        params.append(obj)
    if not clauses:
        raise DecisionMemoryError(
            "recall scope requires entity, brand, or object", code="bad_scope"
        )
    return " AND ".join(clauses), params


def _query_matches(row: dict[str, Any], query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return True
    keys = row.get("query_keys") or []
    if keys:
        # Exact casefolded equality only — a shared word is not a hit.
        q_cf = q.casefold()
        return any(str(k).casefold() == q_cf for k in keys)
    # Rows without query_keys keep substring match (legacy tests).
    q_lower = q.lower()
    haystacks: list[str] = [
        str(row.get("title") or ""),
        str(row.get("chosen_option") or ""),
        str(row.get("outcome") or ""),
        str(row.get("actor") or ""),
        str(row.get("decision_id") or ""),
    ]
    for opt in row.get("options_considered") or []:
        haystacks.append(str(opt))
    blob = " ".join(haystacks).lower()
    return q_lower in blob


def recall(
    scope: str | dict[str, Any],
    query: str = "",
    *,
    limit: int = RECALL_MAX,
    permission_context: dict[str, Any] | None = None,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Return matching decisions with provenance. Bounded (max 50).

    Scope isolation: Habitat decisions are not returned for Uma (and vice versa).
    Empty match set → status NOT FOUND. Never invents outcomes.
    Requires permission_context that rbac.evaluate allows for decision.memory.read.
    """
    _require_permission(permission_context, PERM_READ)

    sc = normalize_scope(scope)
    where, params = _scope_clause(sc)
    lim = max(1, min(int(limit or RECALL_MAX), RECALL_MAX))

    own = conn is None
    c = conn or db_connect(db_path)
    try:
        # Fetch a generous candidate set then filter by query in Python so
        # options_json matching stays simple and deterministic.
        rows = c.execute(
            f"""
            SELECT * FROM core_decision_memory
            WHERE {where}
            ORDER BY occurred_at DESC, recorded_at DESC
            LIMIT ?
            """,
            (*params, RECALL_MAX * 4),
        ).fetchall()
        matched: list[dict[str, Any]] = []
        for r in rows:
            d = _row_to_dict(r)
            if d and _query_matches(d, query):
                matched.append(d)
            if len(matched) >= lim:
                break

        if not matched:
            return {
                "status": STATUS_NOT_FOUND,
                "decisions": [],
                "count": 0,
                "scope": sc,
                "query": query,
                "limit": lim,
                "honesty": honesty_flags(),
            }

        return {
            "status": None,  # per-row status on each decision
            "decisions": matched,
            "count": len(matched),
            "scope": sc,
            "query": query,
            "limit": lim,
            "honesty": honesty_flags(),
        }
    finally:
        if own:
            c.close()


def install_owner_seed_rbac_fixture(conn: sqlite3.Connection) -> dict[str, str]:
    """Install fixture role/person/grants for Owner seed + tests.

    Does not grant live staff roles. Safe on temp DBs and seed sidecar DBs.
    Column shapes match Beta org registry so the fixture works on a live catalog
    copy and on a minimal sidecar.
    """
    ts = now_utc_iso()
    person_id = "PERS-DM-OWNER-SEED"
    role_id = "ROLE-DM-OWNER-SEED"
    position_id = "POS-DM-OWNER-SEED"
    assignment_id = "ASG-DM-OWNER-SEED"
    scope_id = "SCOPE-DM-OWNER-SEED"
    entity_id = "ENT-WOLF-SYSTEM"

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS org_entities (
          entity_id TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          entity_type TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_brands (
          brand_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          display_name TEXT,
          brand_type TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_locations (
          location_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          display_name TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_departments (
          department_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          display_name TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_persons (
          person_id TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          legal_name TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_roles (
          role_id TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          department_id TEXT,
          role_type TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_positions (
          position_id TEXT PRIMARY KEY,
          role_id TEXT NOT NULL,
          entity_id TEXT,
          display_name TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_assignments (
          assignment_id TEXT PRIMARY KEY,
          person_id TEXT NOT NULL,
          position_id TEXT NOT NULL,
          start_at TEXT NOT NULL,
          end_at TEXT,
          status TEXT NOT NULL,
          is_primary INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_scopes (
          scope_id TEXT PRIMARY KEY,
          scope_type TEXT,
          display_name TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_scope_targets (
          scope_id TEXT NOT NULL,
          target_type TEXT NOT NULL,
          target_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY (scope_id, target_type, target_id)
        );
        CREATE TABLE IF NOT EXISTS org_assignment_scopes (
          assignment_id TEXT NOT NULL,
          scope_id TEXT NOT NULL,
          start_at TEXT NOT NULL,
          end_at TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (assignment_id, scope_id, start_at)
        );
        CREATE TABLE IF NOT EXISTS org_permissions (
          permission_id TEXT PRIMARY KEY,
          code TEXT NOT NULL UNIQUE,
          resource TEXT NOT NULL,
          action TEXT NOT NULL,
          description TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS org_role_permissions (
          role_id TEXT NOT NULL,
          permission_id TEXT NOT NULL,
          effect TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (role_id, permission_id)
        );
        """
    )
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, display_name, entity_type, status, created_at, updated_at
        ) VALUES (?, 'Wolf system', 'system', 'ACTIVE', ?, ?)
        ON CONFLICT(entity_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (entity_id, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, 'Decision Memory Owner Seed', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (person_id, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Decision Memory Owner Seed', NULL, 'fixture', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (role_id, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, display_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, 'Decision Memory Owner Seed', 'ACTIVE', ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (position_id, role_id, entity_id, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL,
          updated_at=excluded.updated_at
        """,
        (assignment_id, person_id, position_id, ts, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'structural', 'Decision Memory Owner Seed', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (scope_id, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (scope_id, entity_id, ts),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, assignment_id, scope_id, ts, ts)
    for perm_id, code, resource, action, desc in (
        (
            "PERM-DECISION-MEMORY-READ",
            PERM_READ,
            "decision.memory",
            "read",
            "Recall / read Decision Memory rows",
        ),
        (
            "PERM-DECISION-MEMORY-RECORD",
            PERM_RECORD,
            "decision.memory",
            "record",
            "Record a Decision Memory row",
        ),
    ):
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code, status='ACTIVE', updated_at=excluded.updated_at
            """,
            (perm_id, code, resource, action, desc, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (role_id, perm_id, ts, ts),
        )
    conn.commit()
    return {
        "person_id": person_id,
        "role_id": role_id,
        "assignment_id": assignment_id,
        "scope_id": scope_id,
    }


def _lookup_matthew_person_id(catalog_db: Path | None = None) -> str | None:
    path = Path(catalog_db) if catalog_db else (
        BETA_ROOT / "catalog" / "content_library.sqlite"
    )
    if not path.exists():
        return None
    try:
        _assert_beta_path(path.resolve())
    except RuntimeError:
        return None
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            """
            SELECT person_id FROM org_persons
            WHERE display_name = 'Matthew Goss' AND status='ACTIVE'
            LIMIT 1
            """
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _credits_chosen_option_from_canon() -> str:
    """Copy locked credit table from canon file. STOP if values disagree."""
    path = BETA_ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
    text = path.read_text(encoding="utf-8")
    expected = {
        "ABSENT": "0.00",
        "SPECIFIED": "0.05",
        "BUILT": "0.25",
        "PROVEN": "0.80",
        "READY": "1.00",
    }
    found: dict[str, str] = {}
    for line in text.splitlines():
        for state in expected:
            if f"| {state} |" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2 and parts[0] == state:
                    found[state] = parts[1]
    if found != expected:
        raise DecisionMemoryError(
            f"MODEL-C credits mismatch: expected {expected}, found {found}",
            code="credits_mismatch",
        )
    # Verbatim table rows from the canon Credits section.
    return (
        "| State | Credit |\n"
        "| --- | ---: |\n"
        "| ABSENT | 0.00 |\n"
        "| SPECIFIED | 0.05 |\n"
        "| BUILT | 0.25 |\n"
        "| PROVEN | 0.80 |\n"
        "| READY | 1.00 |"
    )


def _correction_docs_qualify() -> bool:
    overnight = (
        BETA_ROOT
        / "docs"
        / "deliveries"
        / "OVERNIGHT-P1-MATURITY-UPDATES-2026-09-17.md"
    ).read_text(encoding="utf-8")
    remediation = (
        BETA_ROOT
        / "docs"
        / "deliveries"
        / "EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md"
    ).read_text(encoding="utf-8")
    claimed = (
        "CAP-DR-01" in overnight
        and "PROVEN" in overnight
        and "CAP-INTG-07" in overnight
        and "| CAP-DR-01 | SPECIFIED | PROVEN |" in overnight
        and "| CAP-INTG-07 | SPECIFIED | PROVEN |" in overnight
    )
    rejected = (
        "Both caps remain **SPECIFIED**" in remediation
        or "both remain **SPECIFIED**" in remediation.lower()
        or (
            "remain **SPECIFIED**" in remediation
            and "CAP-DR-01" in remediation
            and "CAP-INTG-07" in remediation
        )
    )
    # Overnight owner note also rejects; remediation is authoritative keep-SPECIFIED.
    rejected = rejected or (
        "REJECTED" in overnight
        and "CAP-DR-01" in overnight
        and "CAP-INTG-07" in overnight
        and "SPECIFIED" in overnight
    )
    return bool(claimed and rejected)


def seed_owner_decisions(
    *,
    db_path: Path | str | None = None,
    rbac_db_path: Path | str | None = None,
    audit_db_path: Path | str | None = None,
    catalog_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Owner-governed seed of the four (plus correction pair if qualified) decisions.

    Uses Beta path guard. Refuses non-Beta paths. Each row goes through
    record_decision + audit.record_event. No HTTP route. No skipped RBAC check —
    evaluate runs against an Owner-seed fixture role (not a live staff grant).
    """
    path = Path(db_path) if db_path else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    assert_db_writable(resolved)

    # Sidecar RBAC under beta-os — never grants live staff roles on content_library.
    rbac_path = Path(rbac_db_path) if rbac_db_path else (
        BETA_ROOT / "catalog" / "backups" / "decision-memory-owner-seed-rbac.sqlite"
    )
    rbac_resolved = rbac_path.resolve()
    _assert_beta_path(rbac_resolved)
    rbac_resolved.parent.mkdir(parents=True, exist_ok=True)
    rbac_conn = sqlite3.connect(str(rbac_resolved))
    rbac_conn.row_factory = sqlite3.Row
    try:
        fixture = install_owner_seed_rbac_fixture(rbac_conn)
    finally:
        rbac_conn.close()

    audit_path = Path(audit_db_path) if audit_db_path else (
        catalog_db_path
        if catalog_db_path
        else (BETA_ROOT / "catalog" / "content_library.sqlite")
    )
    audit_resolved = Path(audit_path).resolve()
    _assert_beta_path(audit_resolved)

    from core import audit as _audit

    audit_conn = _audit.db_connect(audit_resolved)
    try:
        # Ensure audit table exists (live catalog already has it; temp may need SQL).
        sql = (
            BETA_ROOT
            / "scripts"
            / "migrations"
            / "011_audit_evidence_spine.sql"
        )
        if sql.exists():
            audit_conn.executescript(sql.read_text(encoding="utf-8"))
            audit_conn.commit()

        person_matt = _lookup_matthew_person_id(
            Path(catalog_db_path) if catalog_db_path else None
        )
        perm_ctx: dict[str, Any] = {
            "person_id": fixture["person_id"],
            "rbac_db_path": rbac_resolved,
            "audit_conn": audit_conn,
            "target_context": {},
        }

        credits = _credits_chosen_option_from_canon()
        seeded: list[str] = []

        def _once(decision_id: str, **kwargs: Any) -> None:
            existing = get_decision(decision_id, db_path=resolved)
            if existing:
                seeded.append(decision_id)
                return
            record_decision(
                decision_id=decision_id,
                permission_context=perm_ctx,
                db_path=resolved,
                **kwargs,
            )
            seeded.append(decision_id)

        base_prov = {
            "source": "CURSOR-MISSION-DECISION-MEMORY-LIVE-2026-09-18",
            "actor_label": "Matthew Goss",
            "person_id": person_matt,
            "owner_audit": "2026-09-18",
        }

        _once(
            "DEC-ARCH-CLICKUP-2026-09-18",
            title=(
                "ClickUp is removed from Wolf's target architecture. "
                "Wolf Core Work Items are the future task primitive. "
                "Existing ClickUp remains legacy evidence until a controlled "
                "retirement. Retirement is not done in this slice."
            ),
            scope="Wolf system",
            options_considered=[],
            empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
            chosen_option=None,
            approval_ref=None,
            outcome=None,
            actor="Matthew Goss",
            occurred_at="2026-09-18",
            query_keys=["What is Wolf's ClickUp policy?"],
            provenance={
                **base_prov,
                "quote": "Owner audit 2026-09-18",
            },
        )

        lock_event = (
            BETA_ROOT
            / "docs"
            / "deliveries"
            / "MODEL-C-NUMERIC-CREDITS-LOCK-EVENT-2026-09-17.md"
        )
        _once(
            "DEC-MODEL-C-CREDITS-2026-09-17",
            title="SYSTEM maturity credits (Model C numeric lock)",
            scope="Wolf system",
            options_considered=[],
            empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
            chosen_option=credits,
            approval_ref=None,
            outcome=None,
            actor="Matthew Goss",
            occurred_at="2026-09-17",
            query_keys=["What are the current SYSTEM maturity credits?"],
            provenance={
                **base_prov,
                "docs": [
                    "docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md",
                    *([str(lock_event.relative_to(BETA_ROOT))] if lock_event.exists() else []),
                ],
            },
        )

        _once(
            "DEC-CRM-HABITAT-CUTOVER-2026-09-18",
            title=(
                "Historical lead archaeology is preserved. No fabricated "
                "first-touch history. A post-cutover clean book is later. "
                "CRM cutover is currently OFF. No cutover_at, no operator, "
                "no live lead ingestion, no staff grant, no Work Item "
                "creation. The old Habitat sync is unchanged."
            ),
            scope="GGV / Habitat",
            options_considered=[],
            empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
            chosen_option=None,
            approval_ref=None,
            outcome=None,
            actor="Matthew Goss",
            occurred_at="2026-09-18",
            query_keys=["Is Habitat CRM cut over?"],
            provenance={
                **base_prov,
                "quote": "Owner audit 2026-09-18",
            },
        )

        klaviyo_mission = (
            BETA_ROOT
            / "docs"
            / "deliveries"
            / "CURSOR-MISSION-HABITAT-KLAVIYO-READER-2026-09-18.md"
        )
        _once(
            "DEC-CRM-KLAVIYO-RECEIPT-2026-09-18",
            title=(
                "For Klaviyo-source Habitat leads, Klaviyo profile.created may "
                "be the receipt time. It is stored as source observed time with "
                "provenance RECEIVED_BY_KLAVIYO_SOURCE. It does not claim "
                "upstream form-submit time."
            ),
            scope="GGV / Habitat",
            options_considered=[],
            empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
            chosen_option=None,
            approval_ref=None,
            outcome=None,
            actor="Matthew Goss",
            occurred_at="2026-09-18",
            query_keys=[
                "What does Klaviyo created mean for Habitat lead receipt?"
            ],
            provenance={
                **base_prov,
                "quote": "Owner audit 2026-09-18",
                "docs": [
                    *([str(klaviyo_mission.relative_to(BETA_ROOT))]
                      if klaviyo_mission.exists() else []),
                ],
            },
        )

        correction_seeded = False
        if _correction_docs_qualify():
            prior_id = "DEC-MATURITY-DR01-INTG07-OVERNIGHT-2026-09-17"
            corr_id = "DEC-MATURITY-DR01-INTG07-CORRECTED-2026-09-18"
            maturity_key = "What is CAP-DR-01 and CAP-INTG-07 maturity?"
            _once(
                prior_id,
                title=(
                    "Overnight P1 proposed CAP-DR-01 and CAP-INTG-07 from "
                    "SPECIFIED to PROVEN."
                ),
                scope="Wolf system",
                options_considered=[],
                empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
                chosen_option="CAP-DR-01 PROVEN; CAP-INTG-07 PROVEN",
                approval_ref=None,
                outcome=None,
                actor="Matthew Goss",
                occurred_at="2026-09-17",
                query_keys=[maturity_key],
                provenance={
                    **base_prov,
                    "docs": [
                        "docs/deliveries/OVERNIGHT-P1-MATURITY-UPDATES-2026-09-17.md"
                    ],
                    "kind": "overnight_claim",
                },
            )
            existing_corr = get_decision(corr_id, db_path=resolved)
            if not existing_corr:
                record_decision(
                    decision_id=corr_id,
                    corrects_decision_id=prior_id,
                    title=(
                        "Owner rejected overnight PROVEN proposals for "
                        "CAP-DR-01 and CAP-INTG-07; both remain SPECIFIED."
                    ),
                    scope="Wolf system",
                    options_considered=[],
                    empty_options_reason=EMPTY_OPTIONS_REASON_OWNER,
                    chosen_option="CAP-DR-01 SPECIFIED; CAP-INTG-07 SPECIFIED",
                    approval_ref=None,
                    outcome=None,
                    actor="Matthew Goss",
                    occurred_at="2026-09-18",
                    query_keys=[maturity_key],
                    permission_context=perm_ctx,
                    db_path=resolved,
                    provenance={
                        **base_prov,
                        "docs": [
                            "docs/deliveries/EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md",
                            "docs/deliveries/OVERNIGHT-P1-MATURITY-UPDATES-2026-09-17.md",
                        ],
                        "kind": "correction",
                        "corrects_decision_id": prior_id,
                    },
                )
            seeded.append(corr_id)
            correction_seeded = True

        return {
            "db_path": str(resolved),
            "seeded_ids": seeded,
            "count": len(set(seeded)),
            "correction_pair": correction_seeded,
            "matthew_person_id": person_matt,
        }
    finally:
        audit_conn.close()


def main(argv: list[str] | None = None) -> int:
    # Allow `python3 scripts/core/decision_memory.py seed` without PYTHONPATH.
    scripts_root = Path(__file__).resolve().parents[1]
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "seed":
        print("usage: decision_memory.py seed [--db PATH]", file=sys.stderr)
        return 2
    db: Path | None = None
    if "--db" in args:
        i = args.index("--db")
        db = Path(args[i + 1])
    # Live seed from CLI is outside test mode; allow live decision DB + audit.
    os.environ.setdefault("WOLF_ALLOW_LIVE_DECISION_MEMORY", "1")
    os.environ.setdefault("WOLF_ALLOW_LIVE_AUDIT", "1")
    result = seed_owner_decisions(db_path=db)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())