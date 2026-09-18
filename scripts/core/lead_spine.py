#!/usr/bin/env python3
"""Wolf Core Lead Spine v1 — Beta fixtures only.

LEAD is not PERSON, not CUSTOMER, not SALE, not REVENUE.
No live import. No external writes. Bound: beta-lead-spine-fixtures.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import rbac as _rbac
from core import scope as _scope

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

WOLF_STAGES = frozenset({"OPEN", "ACTIVE", "PARKED", "CLOSED"})
EVENT_TYPES = frozenset(
    {
        "observed",
        "assigned",
        "stage_changed",
        "human_touch_recorded",
        "note_recorded",
        "next_action_linked",
        "conversion_claimed",
        "conversion_verified",
        "correction",
        "match_candidate_recorded",
        "match_candidate_revoked",
    }
)
ACTOR_TYPES = frozenset({"PERSON", "SYSTEM"})
CONVERSION_STATUSES = frozenset({"CLAIMED", "VERIFIED"})
INFERENCE_KEYS = frozenset({"inference", "inferred", "ai_guess"})

STAGE_MAP_SEED: list[tuple[str, str, str | None]] = [
    # CONTENT-DEMAND-5
    ("CONTENT-DEMAND-5", "new", "OPEN"),
    ("CONTENT-DEMAND-5", "process", "ACTIVE"),
    ("CONTENT-DEMAND-5", "followup", "ACTIVE"),
    ("CONTENT-DEMAND-5", "parked", "PARKED"),
    ("CONTENT-DEMAND-5", "closed", "CLOSED"),
    # BAKE-8
    ("BAKE-8", "new", "OPEN"),
    ("BAKE-8", "contacted", "ACTIVE"),
    ("BAKE-8", "qualified", "ACTIVE"),
    ("BAKE-8", "viewing", "ACTIVE"),
    ("BAKE-8", "offer", "ACTIVE"),
    ("BAKE-8", "won", "CLOSED"),
    ("BAKE-8", "not_interested", "CLOSED"),
    ("BAKE-8", "parked", "PARKED"),
    # IMPORT-NOTE-2026-08-21 — words kept verbatim
    ("IMPORT-NOTE-2026-08-21", "new", "OPEN"),
    ("IMPORT-NOTE-2026-08-21", "in process", "ACTIVE"),
    ("IMPORT-NOTE-2026-08-21", "follow-up", "ACTIVE"),
    ("IMPORT-NOTE-2026-08-21", "parked", "PARKED"),
    ("IMPORT-NOTE-2026-08-21", "reserved/bought", "CLOSED"),
]

PERMS = (
    ("PERM-LEAD-READ", "lead.read", "lead", "read", "Read leads in brand scope"),
    ("PERM-LEAD-CREATE", "lead.create", "lead", "create", "Create / ingest lead observations"),
    (
        "PERM-LEAD-EVENT",
        "lead.event.append",
        "lead",
        "event.append",
        "Append lead events",
    ),
    ("PERM-LEAD-ASSIGN", "lead.assign", "lead", "assign", "Assign lead owner"),
)


class LeadSpineError(ValueError):
    """Fail-closed validation / permission error."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def db_connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    raw = str(path)
    # String check first so wolf-system paths are refused even if unresolvable.
    if "wolf-system" in raw:
        raise RuntimeError(f"lead_spine refuses wolf-system path: {path}")
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    s = str(resolved)
    if "wolf-system" in s:
        raise RuntimeError(f"lead_spine refuses wolf-system path: {resolved}")
    if "beta-os" not in s and "beta-os" not in raw:
        raise RuntimeError(f"lead_spine refuses non-beta DB: {resolved}")
    open_at = path if "beta-os" in raw else resolved
    conn = sqlite3.connect(str(open_at))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _open(db_path: Path | str | None) -> sqlite3.Connection:
    return db_connect(db_path)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_lead_id() -> str:
    return f"LEAD-{uuid.uuid4()}"


def mint_event_id() -> str:
    return f"LEADEVT-{uuid.uuid4()}"


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _refuse_inference(payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    for k in payload:
        if str(k).lower() in INFERENCE_KEYS or str(k) in INFERENCE_KEYS:
            raise LeadSpineError("inference payload refused", code="inference_refused")
        # also exact keys
        if k in INFERENCE_KEYS:
            raise LeadSpineError("inference payload refused", code="inference_refused")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create lead spine tables, triggers, stage maps, and permission codes."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS core_leads (
          lead_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          brand_id TEXT NOT NULL,
          source_system TEXT NOT NULL,
          source_id TEXT NOT NULL,
          source_observed_at TEXT NULL,
          wolf_ingested_at TEXT NOT NULL,
          provenance_json TEXT NOT NULL,
          source_stage TEXT NULL,
          wolf_stage TEXT NULL,
          owner_person_id TEXT NULL,
          owner_assignment_id TEXT NULL,
          first_human_touch_at TEXT NULL,
          current_work_item_id TEXT NULL,
          conversion_status TEXT NULL,
          conversion_evidence_id TEXT NULL,
          UNIQUE (entity_id, brand_id, source_system, source_id)
        );

        CREATE TABLE IF NOT EXISTS core_lead_events (
          event_id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          occurred_at TEXT NULL,
          recorded_at TEXT NOT NULL,
          actor_type TEXT NOT NULL,
          actor_person_id TEXT NULL,
          payload_json TEXT NOT NULL,
          supersedes_event_id TEXT NULL,
          observation_key TEXT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_core_lead_events_obs_key
          ON core_lead_events(lead_id, observation_key)
          WHERE observation_key IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_core_lead_events_lead
          ON core_lead_events(lead_id);

        CREATE TABLE IF NOT EXISTS core_lead_stage_maps (
          vocab_id TEXT NOT NULL,
          source_stage TEXT NOT NULL,
          wolf_stage TEXT NULL,
          PRIMARY KEY (vocab_id, source_stage)
        );
        """
    )
    # Append-only triggers
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_lead_events_no_update
        BEFORE UPDATE ON core_lead_events
        BEGIN
          SELECT RAISE(ABORT, 'core_lead_events is append-only');
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_lead_events_no_delete
        BEFORE DELETE ON core_lead_events
        BEGIN
          SELECT RAISE(ABORT, 'core_lead_events is append-only');
        END
        """
    )
    for vocab_id, source_stage, wolf_stage in STAGE_MAP_SEED:
        conn.execute(
            """
            INSERT INTO core_lead_stage_maps (vocab_id, source_stage, wolf_stage)
            VALUES (?, ?, ?)
            ON CONFLICT(vocab_id, source_stage) DO UPDATE SET
              wolf_stage=excluded.wolf_stage
            """,
            (vocab_id, source_stage, wolf_stage),
        )
    ts = now_utc_iso()
    for perm_id, code, resource, action, desc in PERMS:
        # org_permissions may not exist on a bare temp DB; skip if absent
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "org_permissions" not in tabs:
            continue
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              resource=excluded.resource,
              action=excluded.action,
              description=excluded.description,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (perm_id, code, resource, action, desc, ts, ts),
        )


def map_source_stage(conn: sqlite3.Connection, source_stage: str | None) -> str | None:
    """Return wolf_stage for a source_stage string, or None if unmapped."""
    if source_stage is None:
        return None
    ss = source_stage  # verbatim; do not strip to avoid rewriting words
    if ss == "":
        return None
    row = conn.execute(
        """
        SELECT wolf_stage FROM core_lead_stage_maps
        WHERE source_stage=? AND wolf_stage IS NOT NULL
        LIMIT 1
        """,
        (ss,),
    ).fetchone()
    return row[0] if row else None


def _brand_scope_targets_include(
    conn: sqlite3.Connection, scope_id: str, brand_id: str
) -> bool:
    """Entity-wide scope does not pass — brand target required."""
    targets = _scope.list_scope_targets(scope_id, conn=conn)
    return any(
        t.get("target_type") == "brand" and t.get("target_id") == brand_id for t in targets
    )


def _require_perm(
    conn: sqlite3.Connection,
    *,
    verified_person_id: str | None,
    permission_code: str,
    brand_id: str,
    entity_id: str | None = None,
) -> dict[str, Any]:
    pid = (verified_person_id or "").strip()
    if not pid:
        raise LeadSpineError("missing verified_person_id", code="denied")
    target: dict[str, Any] = {"brand_id": brand_id}
    if entity_id:
        target["entity_id"] = entity_id
    decision = _rbac.evaluate(pid, permission_code, target, conn=conn)
    if not decision.get("allowed"):
        raise LeadSpineError(
            f"denied {permission_code}: {decision.get('reason')}",
            code="denied",
        )
    matched = decision.get("matched") or {}
    scope_id = matched.get("scope_id")
    if not scope_id or not _brand_scope_targets_include(conn, scope_id, brand_id):
        raise LeadSpineError(
            "denied: winning scope must target brand_id (entity-wide insufficient)",
            code="denied",
        )
    return decision


def get_lead(
    lead_id: str,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or _open(db_path)
    try:
        return _row(
            c.execute("SELECT * FROM core_leads WHERE lead_id=?", (lead_id,)).fetchone()
        )
    finally:
        if own:
            c.close()


def read_lead(
    lead_id: str,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        _require_perm(
            c,
            verified_person_id=verified_person_id,
            permission_code="lead.read",
            brand_id=lead["brand_id"],
            entity_id=lead["entity_id"],
        )
        return lead
    finally:
        if own:
            c.close()


def _find_by_source(
    conn: sqlite3.Connection,
    entity_id: str,
    brand_id: str,
    source_system: str,
    source_id: str,
) -> dict[str, Any] | None:
    return _row(
        conn.execute(
            """
            SELECT * FROM core_leads
            WHERE entity_id=? AND brand_id=? AND source_system=? AND source_id=?
            """,
            (entity_id, brand_id, source_system, source_id),
        ).fetchone()
    )


def _find_event_by_obs_key(
    conn: sqlite3.Connection, lead_id: str, observation_key: str
) -> dict[str, Any] | None:
    return _row(
        conn.execute(
            """
            SELECT * FROM core_lead_events
            WHERE lead_id=? AND observation_key=?
            """,
            (lead_id, observation_key),
        ).fetchone()
    )


def append_event(
    lead_id: str,
    event_type: str,
    *,
    payload: dict[str, Any] | None = None,
    actor_type: str = "SYSTEM",
    actor_person_id: str | None = None,
    verified_person_id: str | None = None,
    occurred_at: str | None = None,
    observation_key: str | None = None,
    supersedes_event_id: str | None = None,
    require_perm: bool = True,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise LeadSpineError(f"unknown event_type {event_type}", code="invalid_event")
    if actor_type not in ACTOR_TYPES:
        raise LeadSpineError(f"unknown actor_type {actor_type}", code="invalid_actor")
    payload = dict(payload or {})
    _refuse_inference(payload)

    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")

        if require_perm and actor_type == "PERSON":
            vpid = (verified_person_id or "").strip()
            if not vpid:
                raise LeadSpineError("missing verified_person_id", code="denied")
            if actor_person_id and actor_person_id.strip() != vpid:
                raise LeadSpineError(
                    "actor_person_id must match verified_person_id",
                    code="denied",
                )
            code = "lead.assign" if event_type == "assigned" else "lead.event.append"
            _require_perm(
                c,
                verified_person_id=vpid,
                permission_code=code,
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
            actor_person_id = vpid

        if observation_key:
            existing = _find_event_by_obs_key(c, lead_id, observation_key)
            if existing:
                return existing

        eid = mint_event_id()
        recorded = now_utc_iso()
        c.execute(
            """
            INSERT INTO core_lead_events (
              event_id, lead_id, event_type, occurred_at, recorded_at,
              actor_type, actor_person_id, payload_json, supersedes_event_id,
              observation_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                lead_id,
                event_type,
                occurred_at,
                recorded,
                actor_type,
                actor_person_id,
                _json_dumps(payload),
                supersedes_event_id,
                observation_key,
            ),
        )
        c.commit()
        return get_event(eid, conn=c)  # type: ignore[return-value]
    finally:
        if own:
            c.close()


def get_event(
    event_id: str, *, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    own = conn is None
    c = conn
    if c is None:
        raise LeadSpineError("conn required for get_event", code="invalid")
    return _row(
        c.execute("SELECT * FROM core_lead_events WHERE event_id=?", (event_id,)).fetchone()
    )


def ingest_observation(
    *,
    entity_id: str,
    brand_id: str,
    source_system: str,
    source_id: str,
    source_observed_at: str | None = None,
    source_stage: str | None = None,
    provenance: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    observation_key: str | None = None,
    actor_type: str = "SYSTEM",
    actor_person_id: str | None = None,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    ss = (source_system or "").strip()
    sid = (source_id or "").strip()
    if not ss or not sid:
        raise LeadSpineError(
            "source_system and source_id required",
            code="missing_source",
        )
    eid = (entity_id or "").strip()
    bid = (brand_id or "").strip()
    if not eid or not bid:
        raise LeadSpineError("entity_id and brand_id required", code="missing_entity")

    payload = dict(payload or {})
    _refuse_inference(payload)
    provenance = dict(provenance or {})
    # email/phone are source attributes only — never merge keys
    for attr in ("email", "phone"):
        if attr in payload and attr not in provenance:
            provenance[attr] = payload[attr]

    own = conn is None
    c = conn or _open(db_path)
    try:
        ensure_schema(c)

        if actor_type == "PERSON":
            vpid = (verified_person_id or "").strip()
            if not vpid:
                raise LeadSpineError("missing verified_person_id", code="denied")
            if actor_person_id and actor_person_id.strip() != vpid:
                raise LeadSpineError(
                    "actor_person_id must match verified_person_id",
                    code="denied",
                )
            _require_perm(
                c,
                verified_person_id=vpid,
                permission_code="lead.create",
                brand_id=bid,
                entity_id=eid,
            )
            actor_person_id = vpid

        existing = _find_by_source(c, eid, bid, ss, sid)
        if existing:
            lead_id = existing["lead_id"]
            if observation_key:
                obs = _find_event_by_obs_key(c, lead_id, observation_key)
                if obs:
                    return {"lead": existing, "event": obs, "created": False}
            # Different observation_key → append observed event, same lead
            evt = append_event(
                lead_id,
                "observed",
                payload=payload or {"source_system": ss, "source_id": sid},
                actor_type=actor_type,
                actor_person_id=actor_person_id,
                verified_person_id=verified_person_id,
                occurred_at=source_observed_at,
                observation_key=observation_key,
                require_perm=False,
                conn=c,
            )
            return {"lead": get_lead(lead_id, conn=c), "event": evt, "created": False}

        # New lead — never insert into org_persons
        lead_id = mint_lead_id()
        ingested = now_utc_iso()
        wolf = map_source_stage(c, source_stage) if source_stage is not None else None
        # Keep source_stage verbatim including unmapped; wolf may be null
        stored_source_stage = source_stage  # may be None; never "UNKNOWN"
        if stored_source_stage == "":
            stored_source_stage = None

        c.execute(
            """
            INSERT INTO core_leads (
              lead_id, entity_id, brand_id, source_system, source_id,
              source_observed_at, wolf_ingested_at, provenance_json,
              source_stage, wolf_stage, owner_person_id, owner_assignment_id,
              first_human_touch_at, current_work_item_id,
              conversion_status, conversion_evidence_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL)
            """,
            (
                lead_id,
                eid,
                bid,
                ss,
                sid,
                source_observed_at,
                ingested,
                _json_dumps(provenance),
                stored_source_stage,
                wolf,
            ),
        )
        evt = append_event(
            lead_id,
            "observed",
            payload=payload or {"source_system": ss, "source_id": sid},
            actor_type=actor_type,
            actor_person_id=actor_person_id,
            verified_person_id=verified_person_id,
            occurred_at=source_observed_at,
            observation_key=observation_key,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt, "created": True}
    finally:
        if own:
            c.close()


def set_stage(
    lead_id: str,
    source_stage: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    actor_person_id: str | None = None,
    observation_key: str | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
            actor_person_id = (verified_person_id or "").strip()

        before_src = lead["source_stage"]
        before_wolf = lead["wolf_stage"]
        after_src = source_stage  # verbatim
        after_wolf = map_source_stage(c, source_stage)

        c.execute(
            """
            UPDATE core_leads
            SET source_stage=?, wolf_stage=?
            WHERE lead_id=?
            """,
            (after_src, after_wolf, lead_id),
        )
        evt = append_event(
            lead_id,
            "stage_changed",
            payload={
                "source_before": before_src,
                "source_after": after_src,
                "wolf_before": before_wolf,
                "wolf_after": after_wolf,
            },
            actor_type=actor_type,
            actor_person_id=actor_person_id,
            verified_person_id=verified_person_id,
            observation_key=observation_key,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def assign_owner(
    lead_id: str,
    owner_person_id: str | None,
    *,
    owner_assignment_id: str | None = None,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        _require_perm(
            c,
            verified_person_id=verified_person_id,
            permission_code="lead.assign",
            brand_id=lead["brand_id"],
            entity_id=lead["entity_id"],
        )
        # Blank stays null — never write UNKNOWN
        oid = (owner_person_id or "").strip() or None
        if oid and oid.upper() == "UNKNOWN":
            oid = None
        asg = (owner_assignment_id or "").strip() or None
        c.execute(
            """
            UPDATE core_leads
            SET owner_person_id=?, owner_assignment_id=?
            WHERE lead_id=?
            """,
            (oid, asg, lead_id),
        )
        evt = append_event(
            lead_id,
            "assigned",
            payload={"owner_person_id": oid, "owner_assignment_id": asg},
            actor_type="PERSON",
            actor_person_id=verified_person_id,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def link_work_item(
    lead_id: str,
    work_item_id: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    wid = (work_item_id or "").strip()
    if not wid:
        raise LeadSpineError("work_item_id required", code="invalid")
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        row = c.execute(
            "SELECT work_item_id FROM core_work_items WHERE work_item_id=?",
            (wid,),
        ).fetchone()
        if not row:
            raise LeadSpineError("work_item not found", code="invalid_work_item")
        c.execute(
            "UPDATE core_leads SET current_work_item_id=? WHERE lead_id=?",
            (wid, lead_id),
        )
        evt = append_event(
            lead_id,
            "next_action_linked",
            payload={"work_item_id": wid},
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def record_human_touch(
    lead_id: str,
    *,
    touched_at: str | None = None,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        ts = touched_at or now_utc_iso()
        if lead["first_human_touch_at"] is None:
            c.execute(
                "UPDATE core_leads SET first_human_touch_at=? WHERE lead_id=?",
                (ts, lead_id),
            )
        evt = append_event(
            lead_id,
            "human_touch_recorded",
            payload={"touched_at": ts},
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            occurred_at=ts,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def claim_conversion(
    lead_id: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    payload: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    payload = dict(payload or {})
    if "amount" in payload:
        raise LeadSpineError("amount key refused", code="amount_refused")
    _refuse_inference(payload)
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        c.execute(
            "UPDATE core_leads SET conversion_status=? WHERE lead_id=?",
            ("CLAIMED", lead_id),
        )
        evt = append_event(
            lead_id,
            "conversion_claimed",
            payload=payload,
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def verify_conversion(
    lead_id: str,
    evidence_id: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    evid = (evidence_id or "").strip()
    if not evid:
        raise LeadSpineError("evidence_id required", code="invalid")
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        row = c.execute(
            """
            SELECT evidence_id FROM core_evidence_records
            WHERE evidence_id=?
              AND verification_status='VERIFIED'
              AND status='ACTIVE'
              AND governed_object_id=?
            """,
            (evid, lead_id),
        ).fetchone()
        if not row:
            raise LeadSpineError(
                "evidence not VERIFIED+ACTIVE for this lead",
                code="evidence_required",
            )
        c.execute(
            """
            UPDATE core_leads
            SET conversion_status=?, conversion_evidence_id=?
            WHERE lead_id=?
            """,
            ("VERIFIED", evid, lead_id),
        )
        evt = append_event(
            lead_id,
            "conversion_verified",
            payload={"evidence_id": evid},
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt}
    finally:
        if own:
            c.close()


def record_match_candidate(
    lead_id: str,
    candidate_lead_id: str,
    *,
    reason: str | None = None,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Cross-source likeness — does not merge or overwrite."""
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        other = get_lead(candidate_lead_id, conn=c)
        if not other:
            raise LeadSpineError("candidate lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        evt = append_event(
            lead_id,
            "match_candidate_recorded",
            payload={
                "candidate_lead_id": candidate_lead_id,
                "reason": reason,
            },
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {
            "lead": get_lead(lead_id, conn=c),
            "candidate": get_lead(candidate_lead_id, conn=c),
            "event": evt,
        }
    finally:
        if own:
            c.close()


def revoke_match_candidate(
    lead_id: str,
    candidate_lead_id: str,
    *,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        evt = append_event(
            lead_id,
            "match_candidate_revoked",
            payload={"candidate_lead_id": candidate_lead_id},
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            require_perm=False,
            conn=c,
        )
        c.commit()
        return {
            "lead": get_lead(lead_id, conn=c),
            "candidate": get_lead(candidate_lead_id, conn=c),
            "event": evt,
        }
    finally:
        if own:
            c.close()


def correct_event(
    lead_id: str,
    supersedes_event_id: str,
    *,
    payload: dict[str, Any] | None = None,
    verified_person_id: str | None = None,
    actor_type: str = "SYSTEM",
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Append correction. Prior event stays byte-for-byte."""
    payload = dict(payload or {})
    _refuse_inference(payload)
    own = conn is None
    c = conn or _open(db_path)
    try:
        lead = get_lead(lead_id, conn=c)
        if not lead:
            raise LeadSpineError("lead not found", code="not_found")
        prior = _row(
            c.execute(
                "SELECT * FROM core_lead_events WHERE event_id=? AND lead_id=?",
                (supersedes_event_id, lead_id),
            ).fetchone()
        )
        if not prior:
            raise LeadSpineError("prior event not found", code="not_found")
        if actor_type == "PERSON":
            _require_perm(
                c,
                verified_person_id=verified_person_id,
                permission_code="lead.event.append",
                brand_id=lead["brand_id"],
                entity_id=lead["entity_id"],
            )
        prior_payload = prior["payload_json"]
        evt = append_event(
            lead_id,
            "correction",
            payload={**payload, "corrected_event_id": supersedes_event_id},
            actor_type=actor_type,
            actor_person_id=verified_person_id if actor_type == "PERSON" else None,
            verified_person_id=verified_person_id,
            supersedes_event_id=supersedes_event_id,
            require_perm=False,
            conn=c,
        )
        # Verify prior unchanged
        after = _row(
            c.execute(
                "SELECT payload_json FROM core_lead_events WHERE event_id=?",
                (supersedes_event_id,),
            ).fetchone()
        )
        if after and after["payload_json"] != prior_payload:
            raise LeadSpineError("prior event mutated", code="append_only_violation")
        c.commit()
        return {"lead": get_lead(lead_id, conn=c), "event": evt, "prior": prior}
    finally:
        if own:
            c.close()


def _parse_ts(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def response_time(
    lead: dict[str, Any] | str,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    if isinstance(lead, str):
        own = conn is None
        c = conn or _open(db_path)
        try:
            row = get_lead(lead, conn=c)
        finally:
            if own and conn is None:
                c.close()
        if not row:
            raise LeadSpineError("lead not found", code="not_found")
        lead = row
    touch = lead.get("first_human_touch_at")
    if not touch:
        return {"status": "UNAVAILABLE", "seconds": None}
    start = lead.get("source_observed_at") or lead.get("wolf_ingested_at")
    if not start:
        return {"status": "UNAVAILABLE", "seconds": None}
    seconds = (_parse_ts(touch) - _parse_ts(start)).total_seconds()
    return {"status": "MEASURED", "seconds": seconds}


def honesty_flags() -> dict[str, Any]:
    return {
        "append_only": True,
        "live_import": False,
        "external_writes": False,
        "hardcoded_people": False,
        "closed_implies_conversion": False,
    }
