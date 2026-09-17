#!/usr/bin/env python3
"""Wolf Core Decision Memory v1 (Beta) — CAP-INTEL-04.

INSERT-only decision records + bounded recall.
Reuses the append-only habit of scripts/core/audit.py (no silent rewrite).
Does NOT replace the audit spine. Does NOT invent approvers, amounts, or outcomes.

States: RECORDED | OUTCOME_UNKNOWN | NOT FOUND
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

STATUS_RECORDED = "RECORDED"
STATUS_OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
STATUS_NOT_FOUND = "NOT FOUND"

STATUSES = frozenset(
    {STATUS_RECORDED, STATUS_OUTCOME_UNKNOWN, STATUS_NOT_FOUND}
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
  provenance_json TEXT NULL
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
            out["brand"] = raw.lower()
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
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """INSERT one decision record. Fail closed. Never invents outcome/approver.

    options_considered may be empty only when empty_options_reason is recorded.
    Missing/blank outcome → status OUTCOME_UNKNOWN (never invented).
    """
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
              provenance_json
            ) VALUES (
              ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, ?, ?,
              ?, ?, ?, ?, ?, ?,
              ?
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
            ),
        )
        if commit:
            c.commit()
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
    q = (query or "").strip().lower()
    if not q:
        return True
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
    return q in blob


def recall(
    scope: str | dict[str, Any],
    query: str = "",
    *,
    limit: int = RECALL_MAX,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Return matching decisions with provenance. Bounded (max 50).

    Scope isolation: Habitat decisions are not returned for Uma (and vice versa).
    Empty match set → status NOT FOUND. Never invents outcomes.
    """
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
