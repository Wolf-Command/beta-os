#!/usr/bin/env python3
"""ATRIUM-OPS-SECURITY-EVIDENCE-1 — Security / CCTV evidence workflow (Beta only).

Decision served: 2026-10-02 PICK ATRIUM-OPS-SECURITY-EVIDENCE-1 in
~/.openclaw/wolf-output/decisions.md (Owner order ATRIUM-OPS-FOUR-20261002 /
OWNER law 2 Oct 2026; brief BRIEF-ATRIUM-OPS-SECURITY-EVIDENCE-1.md).

Builds the job, not a board: incident → time/location → people/asset →
evidence reference → optional CCTV timestamp/camera ref → responsible →
severity/escalation → action → follow-up → closure → immutable audit log.

CCTV live stream = EXTERNAL / UNAVAILABLE. Timestamp + camera ref are text
fields only. V1 incidents.db is read-only historical seed. Writes on Beta
:8788 only. No Production :8787. staff_ready stays false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "state" / "security-evidence" / "security_evidence.sqlite"
V1_INCIDENTS_DB = (
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "state" / "incidents.db"
)
ENV_DB = "WOLF_SECURITY_EVIDENCE_DB"

PACK_ID = "ATRIUM-OPS-SECURITY-EVIDENCE-1"
SCHEMA_ID = "wolf.atrium-ops-security-evidence-1.v1"
BOUND = "beta-atrium-ops-security-evidence"
PROD_PORT = 8787
PROD_PID_HELD = 15975
REGISTER_ID = "need.security"

API_PREFIX = "/api/msc/security-evidence"
PAGE_PATHS = frozenset(
    {
        "/msc/security-evidence",
        "/msc/security-evidence/",
        "/msc-security-evidence",
        "/msc-security-evidence/",
        "/msc-security-evidence.html",
        "/atrium-ops-security-evidence-1",
        "/atrium-ops-security-evidence-1/",
        "/atrium-ops-security-evidence-1.html",
        "/dashboards/atrium-ops-security-evidence-1.html",
    }
)

# Mapped from Interview R1/R2/R8 + V1 incidents categories — not invented fantasy.
CATEGORIES = frozenset(
    {
        "cash_theft",
        "anti_theft",
        "access",
        "injury",
        "slip",
        "cut",
        "medical",
        "fire",
        "damage",
        "security",
        "other",
    }
)
SEVERITIES = frozenset({"near-miss", "incident", "critical"})
STATUSES = frozenset(
    {"open", "investigating", "escalated", "actioned", "closed"}
)
EVIDENCE_KINDS = frozenset(
    {
        "note",
        "photo_ref",
        "document_ref",
        "cash_control_ref",
        "access_log_ref",
        "cctv_timestamp_ref",
        "other_ref",
    }
)

HONESTY: dict[str, Any] = {
    "pack": PACK_ID,
    "schema": SCHEMA_ID,
    "bound": BOUND,
    "register_id": REGISTER_ID,
    "staff_ready": False,
    "human_commissioned": False,
    "human_proven": False,
    "proven_claimed": False,
    "ready_claimed": False,
    "cctv_stream": False,
    "cctv_stream_status": "EXTERNAL_UNAVAILABLE",
    "cctv_inventory_invented": False,
    "footage_invented": False,
    "prod_mutate": False,
    "prod_port": PROD_PORT,
    "prod_pid_held": PROD_PID_HELD,
    "v1_incidents_writable": False,
    "writes_beta_only": True,
    "evidence_append_only": True,
    "audit_append_only": True,
    "delete_evidence_refused": True,
}


class SecurityEvidenceError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def db_path(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    env = (os.environ.get(ENV_DB) or "").strip()
    if env:
        return Path(env)
    return DEFAULT_DB


def assert_beta_db(path: Path) -> Path:
    resolved = path.resolve()
    text = str(resolved)
    if "beta-os" not in text and ENV_DB not in os.environ:
        # Temp test DBs are allowed when ENV override or explicit path is under /tmp
        if "/tmp" not in text and "TemporaryDirectory" not in text and not text.startswith("/var/folders"):
            raise SecurityEvidenceError(
                "security evidence refuses a non-beta database",
                code="bad_db",
                http_status=500,
            )
    if "wolf-system" in text or "/Production" in text:
        raise SecurityEvidenceError(
            "security evidence refuses production path",
            code="production_refused",
            http_status=500,
        )
    return resolved


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = assert_beta_db(db_path(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS security_incidents (
  incident_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  reported_by TEXT NOT NULL,
  business TEXT,
  venue TEXT,
  severity TEXT NOT NULL,
  category TEXT NOT NULL,
  details TEXT NOT NULL,
  people_involved TEXT,
  asset_ref TEXT,
  cctv_timestamp TEXT,
  cctv_camera_ref TEXT,
  responsible_person TEXT,
  actions_taken TEXT,
  follow_up TEXT,
  status TEXT NOT NULL,
  closed_at TEXT,
  closed_by TEXT,
  provenance TEXT NOT NULL,
  source_v1_id INTEGER,
  notion_page_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sec_inc_status
  ON security_incidents(status, ts);
CREATE INDEX IF NOT EXISTS idx_sec_inc_category
  ON security_incidents(category, severity);

CREATE TABLE IF NOT EXISTS security_evidence (
  evidence_id TEXT PRIMARY KEY,
  incident_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  ref_text TEXT NOT NULL,
  note TEXT,
  recorded_by TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  provenance TEXT NOT NULL,
  FOREIGN KEY (incident_id) REFERENCES security_incidents(incident_id)
);

CREATE INDEX IF NOT EXISTS idx_sec_ev_incident
  ON security_evidence(incident_id, recorded_at);

CREATE TABLE IF NOT EXISTS security_audit (
  audit_id TEXT PRIMARY KEY,
  incident_id TEXT,
  action TEXT NOT NULL,
  actor_person_id TEXT NOT NULL,
  detail_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sec_audit_incident
  ON security_audit(incident_id, created_at);

CREATE TRIGGER IF NOT EXISTS trg_sec_evidence_no_update
BEFORE UPDATE ON security_evidence
BEGIN
  SELECT RAISE(ABORT, 'security_evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sec_evidence_no_delete
BEFORE DELETE ON security_evidence
BEGIN
  SELECT RAISE(ABORT, 'security_evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sec_audit_no_update
BEFORE UPDATE ON security_audit
BEGIN
  SELECT RAISE(ABORT, 'security_audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sec_audit_no_delete
BEFORE DELETE ON security_audit
BEGIN
  SELECT RAISE(ABORT, 'security_audit is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def stamp(**extra: Any) -> dict[str, Any]:
    out = dict(HONESTY)
    out["ok"] = True
    out.update(extra)
    out["staff_ready"] = False
    out["human_commissioned"] = False
    out["human_proven"] = False
    out["cctv_stream"] = False
    out["cctv_stream_status"] = "EXTERNAL_UNAVAILABLE"
    out["prod_mutate"] = False
    return out


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw == API_PREFIX or raw.startswith(API_PREFIX + "/")


def _audit(
    conn: sqlite3.Connection,
    *,
    incident_id: str | None,
    action: str,
    actor: str,
    detail: dict[str, Any] | None = None,
) -> str:
    audit_id = _new_id("AUD")
    conn.execute(
        """
        INSERT INTO security_audit (
          audit_id, incident_id, action, actor_person_id, detail_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            incident_id,
            action,
            actor,
            json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
            _now(),
        ),
    )
    return audit_id


def _row_incident(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    people = d.get("people_involved")
    if isinstance(people, str) and people:
        try:
            d["people_involved"] = json.loads(people)
        except json.JSONDecodeError:
            d["people_involved"] = [people]
    else:
        d["people_involved"] = []
    d["cctv_stream"] = False
    d["cctv_stream_status"] = "EXTERNAL_UNAVAILABLE"
    return d


def _get_incident(conn: sqlite3.Connection, incident_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM security_incidents WHERE incident_id=?",
        (incident_id,),
    ).fetchone()
    return _row_incident(row) if row else None


def _evidence_rows(conn: sqlite3.Connection, incident_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM security_evidence
        WHERE incident_id=?
        ORDER BY recorded_at, evidence_id
        """,
        (incident_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _audit_rows(conn: sqlite3.Connection, incident_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM security_audit
        WHERE incident_id=?
        ORDER BY created_at, audit_id
        """,
        (incident_id,),
    ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["detail"] = json.loads(item.pop("detail_json") or "{}")
        except json.JSONDecodeError:
            item["detail"] = {"raw": item.pop("detail_json", None)}
        out.append(item)
    return out


def _normalize_category(raw: str | None) -> str:
    cat = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    # V1 used slip/cut/fire/medical/security/damage/other
    aliases = {
        "cash": "cash_theft",
        "theft": "anti_theft",
        "cash_control": "cash_theft",
        "near_miss": "other",
    }
    cat = aliases.get(cat, cat)
    if cat not in CATEGORIES:
        raise SecurityEvidenceError(
            f"category must be one of {sorted(CATEGORIES)}",
            code="invalid_category",
        )
    return cat


def _normalize_severity(raw: str | None) -> str:
    sev = (raw or "").strip().lower()
    if sev not in SEVERITIES:
        raise SecurityEvidenceError(
            f"severity must be one of {sorted(SEVERITIES)}",
            code="invalid_severity",
        )
    return sev


def refuse_cctv_stream(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="cctv_stream_unavailable",
        message=(
            "CCTV live stream is EXTERNAL / UNAVAILABLE. "
            "Use cctv_timestamp + cctv_camera_ref text fields only."
        ),
        http_hint=405,
    )


def refuse_prod_mutate(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="prod_mutate_refused",
        message="Prod :8787 mutate refused. This desk writes Beta state only.",
        http_hint=403,
    )


def refuse_delete_evidence(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="evidence_append_only",
        message="Evidence rows are append-only. Silent delete is refused.",
        http_hint=405,
    )


def _guard_forbidden_keys(body: dict[str, Any]) -> None:
    for key in body:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "cctv-stream",
            "cctv-live",
            "stream-url",
            "footage-url",
            "camera-feed",
            "live-view",
            "invent-camera",
            "camera-inventory",
        }:
            raise SecurityEvidenceError(
                "CCTV stream / invented camera inventory refused.",
                code="cctv_stream_unavailable",
                http_status=405,
            )
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "kill-prod",
            "restart-8787",
        }:
            raise SecurityEvidenceError(
                "Prod mutate refused.",
                code="prod_mutate_refused",
                http_status=403,
            )


def import_v1_seed(
    *,
    db: Path | None = None,
    v1_path: Path | None = None,
    actor: str = "SYSTEM-SEED",
) -> dict[str, Any]:
    """Read-only mirror of V1 incidents rows into Beta with provenance labels."""
    src = v1_path or V1_INCIDENTS_DB
    if not src.is_file():
        return stamp(
            ok=False,
            error="v1_incidents_missing",
            v1_path=str(src),
            imported=0,
            skipped=0,
        )
    before = src.stat()
    ro = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=8)
    ro.row_factory = sqlite3.Row
    try:
        rows = ro.execute(
            """
            SELECT id, ts, reported_by, business, venue, severity, category,
                   details, actions_taken, status, notion_page_id
            FROM incidents
            ORDER BY id
            """
        ).fetchall()
    finally:
        ro.close()
    after = src.stat()
    if before.st_mtime_ns != after.st_mtime_ns:
        raise SecurityEvidenceError(
            "V1 incidents.db mtime changed during read — aborting seed",
            code="v1_mtime_changed",
            http_status=500,
        )

    conn = connect(db)
    imported = 0
    skipped = 0
    seeded: list[str] = []
    try:
        for row in rows:
            v1_id = int(row["id"])
            existing = conn.execute(
                "SELECT incident_id FROM security_incidents WHERE source_v1_id=?",
                (v1_id,),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            cat_raw = (row["category"] or "other").strip().lower()
            try:
                category = _normalize_category(cat_raw)
            except SecurityEvidenceError:
                category = "other"
            sev_raw = (row["severity"] or "incident").strip().lower()
            try:
                severity = _normalize_severity(sev_raw)
            except SecurityEvidenceError:
                severity = "incident"
            status_raw = (row["status"] or "open").strip().lower()
            status = status_raw if status_raw in STATUSES else "open"
            incident_id = _new_id("SEC")
            ts = row["ts"] or _now()
            provenance = f"v1:incidents.db#id={v1_id}"
            conn.execute(
                """
                INSERT INTO security_incidents (
                  incident_id, ts, reported_by, business, venue, severity, category,
                  details, people_involved, asset_ref, cctv_timestamp, cctv_camera_ref,
                  responsible_person, actions_taken, follow_up, status,
                  closed_at, closed_by, provenance, source_v1_id, notion_page_id,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    ts,
                    row["reported_by"] or "unknown",
                    row["business"],
                    row["venue"],
                    severity,
                    category,
                    row["details"] or "",
                    "[]",
                    None,
                    None,
                    None,
                    None,
                    row["actions_taken"],
                    None,
                    status,
                    None,
                    None,
                    provenance,
                    v1_id,
                    row["notion_page_id"],
                    _now(),
                    _now(),
                ),
            )
            _audit(
                conn,
                incident_id=incident_id,
                action="seed_from_v1",
                actor=actor,
                detail={"source_v1_id": v1_id, "provenance": provenance},
            )
            imported += 1
            seeded.append(incident_id)
        conn.commit()
    finally:
        conn.close()

    final_mtime = src.stat().st_mtime_ns
    return stamp(
        imported=imported,
        skipped=skipped,
        seeded_ids=seeded,
        v1_path=str(src),
        v1_open_mode="ro",
        v1_mtime_unchanged=final_mtime == before.st_mtime_ns,
        provenance_label="v1:incidents.db#id=<n>",
    )


def create_incident(
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    reported_by = str(body.get("reported_by") or actor or "").strip()
    details = str(body.get("details") or "").strip()
    if not reported_by:
        raise SecurityEvidenceError("reported_by is required", code="missing_reported_by")
    if not details:
        raise SecurityEvidenceError("details is required", code="missing_details")
    category = _normalize_category(str(body.get("category") or ""))
    severity = _normalize_severity(str(body.get("severity") or "incident"))
    venue = str(body.get("venue") or "").strip() or None
    business = str(body.get("business") or "").strip() or None
    if not venue:
        raise SecurityEvidenceError(
            "venue / location is required for the security evidence job",
            code="missing_venue",
        )
    people = body.get("people_involved") or body.get("people") or []
    if isinstance(people, str):
        people = [p.strip() for p in people.split(",") if p.strip()]
    if not isinstance(people, list):
        raise SecurityEvidenceError("people_involved must be a list", code="invalid_people")
    asset_ref = str(body.get("asset_ref") or "").strip() or None
    cctv_timestamp = str(body.get("cctv_timestamp") or "").strip() or None
    cctv_camera_ref = str(body.get("cctv_camera_ref") or "").strip() or None
    responsible = str(body.get("responsible_person") or "").strip() or None
    ts = str(body.get("ts") or "").strip() or _now()
    incident_id = _new_id("SEC")
    conn = connect(db)
    try:
        conn.execute(
            """
            INSERT INTO security_incidents (
              incident_id, ts, reported_by, business, venue, severity, category,
              details, people_involved, asset_ref, cctv_timestamp, cctv_camera_ref,
              responsible_person, actions_taken, follow_up, status,
              closed_at, closed_by, provenance, source_v1_id, notion_page_id,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                ts,
                reported_by,
                business,
                venue,
                severity,
                category,
                details,
                json.dumps(people, ensure_ascii=False),
                asset_ref,
                cctv_timestamp,
                cctv_camera_ref,
                responsible,
                None,
                None,
                "open",
                None,
                None,
                "beta:security-evidence",
                None,
                None,
                _now(),
                _now(),
            ),
        )
        _audit(
            conn,
            incident_id=incident_id,
            action="create",
            actor=actor,
            detail={
                "category": category,
                "severity": severity,
                "venue": venue,
                "cctv_refs_present": bool(cctv_timestamp or cctv_camera_ref),
            },
        )
        conn.commit()
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(incident=incident, workflow_step="created")


def update_incident(
    incident_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    conn = connect(db)
    try:
        current = _get_incident(conn, incident_id)
        if current is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise SecurityEvidenceError(
                "closed incidents cannot be updated; open a follow-up instead",
                code="already_closed",
            )
        fields: dict[str, Any] = {}
        if "people_involved" in body or "people" in body:
            people = body.get("people_involved", body.get("people"))
            if isinstance(people, str):
                people = [p.strip() for p in people.split(",") if p.strip()]
            if not isinstance(people, list):
                raise SecurityEvidenceError("people_involved must be a list", code="invalid_people")
            fields["people_involved"] = json.dumps(people, ensure_ascii=False)
        for key in (
            "venue",
            "business",
            "asset_ref",
            "cctv_timestamp",
            "cctv_camera_ref",
            "responsible_person",
            "follow_up",
            "actions_taken",
            "details",
        ):
            if key in body and body[key] is not None:
                fields[key] = str(body[key]).strip()
        if "category" in body and body["category"] is not None:
            fields["category"] = _normalize_category(str(body["category"]))
        if "severity" in body and body["severity"] is not None:
            fields["severity"] = _normalize_severity(str(body["severity"]))
        if "status" in body and body["status"] is not None:
            status = str(body["status"]).strip().lower()
            if status not in STATUSES - {"closed"}:
                raise SecurityEvidenceError(
                    "use /close to close; status must be open|investigating|escalated|actioned",
                    code="invalid_status",
                )
            fields["status"] = status
        if not fields:
            raise SecurityEvidenceError("no updatable fields provided", code="empty_update")
        fields["updated_at"] = _now()
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE security_incidents SET {sets} WHERE incident_id=?",
            (*fields.values(), incident_id),
        )
        _audit(
            conn,
            incident_id=incident_id,
            action="update",
            actor=actor,
            detail={"fields": sorted(fields.keys())},
        )
        conn.commit()
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(incident=incident, workflow_step="updated")


def add_evidence(
    incident_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    kind = str(body.get("kind") or "note").strip().lower()
    if kind not in EVIDENCE_KINDS:
        raise SecurityEvidenceError(
            f"kind must be one of {sorted(EVIDENCE_KINDS)}",
            code="invalid_evidence_kind",
        )
    ref_text = str(body.get("ref_text") or body.get("ref") or "").strip()
    if not ref_text:
        raise SecurityEvidenceError("ref_text is required", code="missing_ref")
    note = str(body.get("note") or "").strip() or None
    # Optional CCTV refs may also be attached via evidence kind.
    if kind == "cctv_timestamp_ref" and not (
        body.get("cctv_timestamp") or "T" in ref_text or ref_text
    ):
        pass
    conn = connect(db)
    try:
        current = _get_incident(conn, incident_id)
        if current is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise SecurityEvidenceError(
                "cannot add evidence to a closed incident",
                code="already_closed",
            )
        evidence_id = _new_id("EVD")
        conn.execute(
            """
            INSERT INTO security_evidence (
              evidence_id, incident_id, kind, ref_text, note,
              recorded_by, recorded_at, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                incident_id,
                kind,
                ref_text,
                note,
                actor,
                _now(),
                "beta:security-evidence",
            ),
        )
        # Mirror optional CCTV text refs onto the incident when provided.
        cctv_ts = str(body.get("cctv_timestamp") or "").strip()
        cctv_cam = str(body.get("cctv_camera_ref") or "").strip()
        if cctv_ts or cctv_cam or kind == "cctv_timestamp_ref":
            conn.execute(
                """
                UPDATE security_incidents
                SET cctv_timestamp=COALESCE(?, cctv_timestamp),
                    cctv_camera_ref=COALESCE(?, cctv_camera_ref),
                    updated_at=?
                WHERE incident_id=?
                """,
                (
                    cctv_ts or (ref_text if kind == "cctv_timestamp_ref" else None),
                    cctv_cam or None,
                    _now(),
                    incident_id,
                ),
            )
        if current["status"] == "open":
            conn.execute(
                "UPDATE security_incidents SET status=?, updated_at=? WHERE incident_id=?",
                ("investigating", _now(), incident_id),
            )
        _audit(
            conn,
            incident_id=incident_id,
            action="add_evidence",
            actor=actor,
            detail={"evidence_id": evidence_id, "kind": kind},
        )
        conn.commit()
        evidence = dict(
            conn.execute(
                "SELECT * FROM security_evidence WHERE evidence_id=?",
                (evidence_id,),
            ).fetchone()
        )
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(
        evidence=evidence,
        incident=incident,
        workflow_step="evidence_added",
        cctv_stream=False,
    )


def record_action(
    incident_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    action_text = str(body.get("actions_taken") or body.get("action") or "").strip()
    if not action_text:
        raise SecurityEvidenceError("actions_taken is required", code="missing_action")
    follow_up = str(body.get("follow_up") or "").strip() or None
    responsible = str(body.get("responsible_person") or "").strip() or None
    conn = connect(db)
    try:
        current = _get_incident(conn, incident_id)
        if current is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise SecurityEvidenceError("closed incident", code="already_closed")
        prev = current.get("actions_taken") or ""
        merged = (prev + "\n" + action_text).strip() if prev else action_text
        conn.execute(
            """
            UPDATE security_incidents
            SET actions_taken=?,
                follow_up=COALESCE(?, follow_up),
                responsible_person=COALESCE(?, responsible_person),
                status=?,
                updated_at=?
            WHERE incident_id=?
            """,
            (merged, follow_up, responsible, "actioned", _now(), incident_id),
        )
        _audit(
            conn,
            incident_id=incident_id,
            action="record_action",
            actor=actor,
            detail={"actions_taken": action_text, "follow_up": follow_up},
        )
        conn.commit()
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(incident=incident, workflow_step="actioned")


def escalate(
    incident_id: str,
    body: dict[str, Any] | None = None,
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    payload = body or {}
    _guard_forbidden_keys(payload)
    reason = str(payload.get("reason") or payload.get("note") or "").strip()
    severity = payload.get("severity")
    conn = connect(db)
    try:
        current = _get_incident(conn, incident_id)
        if current is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise SecurityEvidenceError("closed incident", code="already_closed")
        new_sev = current["severity"]
        if severity is not None:
            new_sev = _normalize_severity(str(severity))
        elif current["severity"] == "near-miss":
            new_sev = "incident"
        elif current["severity"] == "incident":
            new_sev = "critical"
        conn.execute(
            """
            UPDATE security_incidents
            SET status=?, severity=?, updated_at=?
            WHERE incident_id=?
            """,
            ("escalated", new_sev, _now(), incident_id),
        )
        _audit(
            conn,
            incident_id=incident_id,
            action="escalate",
            actor=actor,
            detail={"reason": reason, "severity": new_sev},
        )
        conn.commit()
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(incident=incident, workflow_step="escalated")


def close_incident(
    incident_id: str,
    body: dict[str, Any] | None = None,
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    payload = body or {}
    _guard_forbidden_keys(payload)
    closure_note = str(payload.get("closure_note") or payload.get("note") or "").strip()
    if not closure_note:
        raise SecurityEvidenceError(
            "closure_note is required to close",
            code="missing_closure_note",
        )
    conn = connect(db)
    try:
        current = _get_incident(conn, incident_id)
        if current is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            return stamp(ok=True, incident=current, workflow_step="already_closed", idempotent=True)
        evidence_count = conn.execute(
            "SELECT COUNT(*) AS n FROM security_evidence WHERE incident_id=?",
            (incident_id,),
        ).fetchone()["n"]
        if int(evidence_count) < 1 and not (current.get("cctv_timestamp") or current.get("actions_taken")):
            raise SecurityEvidenceError(
                "close requires at least one evidence row, CCTV timestamp ref, or actions_taken",
                code="missing_evidence_for_close",
            )
        follow = current.get("follow_up") or ""
        if closure_note:
            follow = (follow + "\n" + f"CLOSE: {closure_note}").strip() if follow else f"CLOSE: {closure_note}"
        closed_at = _now()
        conn.execute(
            """
            UPDATE security_incidents
            SET status=?, closed_at=?, closed_by=?, follow_up=?, updated_at=?
            WHERE incident_id=?
            """,
            ("closed", closed_at, actor, follow, closed_at, incident_id),
        )
        _audit(
            conn,
            incident_id=incident_id,
            action="close",
            actor=actor,
            detail={"closure_note": closure_note, "evidence_count": int(evidence_count)},
        )
        conn.commit()
        incident = _get_incident(conn, incident_id)
    finally:
        conn.close()
    return stamp(incident=incident, workflow_step="closed")


def list_incidents(*, db: Path | None = None, status: str | None = None) -> dict[str, Any]:
    conn = connect(db)
    try:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM security_incidents
                WHERE status=?
                ORDER BY ts DESC, incident_id
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM security_incidents
                ORDER BY ts DESC, incident_id
                """
            ).fetchall()
        incidents = [_row_incident(r) for r in rows]
        counts = {
            s: conn.execute(
                "SELECT COUNT(*) AS n FROM security_incidents WHERE status=?",
                (s,),
            ).fetchone()["n"]
            for s in sorted(STATUSES)
        }
        evidence_total = conn.execute("SELECT COUNT(*) AS n FROM security_evidence").fetchone()["n"]
        audit_total = conn.execute("SELECT COUNT(*) AS n FROM security_audit").fetchone()["n"]
    finally:
        conn.close()
    openish = sum(counts[s] for s in ("open", "investigating", "escalated", "actioned"))
    register_state = "PARTIAL" if incidents else "MISSING"
    return stamp(
        incidents=incidents,
        count=len(incidents),
        status_counts=counts,
        evidence_total=int(evidence_total),
        audit_total=int(audit_total),
        open_workflow_count=openish,
        register_state=register_state,
        workflow=(
            "incident → time/location → people/asset → evidence → "
            "optional CCTV timestamp/camera ref → responsible → "
            "severity/escalation → action → follow-up → closure → audit"
        ),
        categories=sorted(CATEGORIES),
        severities=sorted(SEVERITIES),
        statuses=sorted(STATUSES),
        evidence_kinds=sorted(EVIDENCE_KINDS),
    )


def get_incident_detail(incident_id: str, *, db: Path | None = None) -> dict[str, Any]:
    conn = connect(db)
    try:
        incident = _get_incident(conn, incident_id)
        if incident is None:
            raise SecurityEvidenceError("incident not found", code="not_found", http_status=404)
        evidence = _evidence_rows(conn, incident_id)
        audit = _audit_rows(conn, incident_id)
    finally:
        conn.close()
    return stamp(
        incident=incident,
        evidence=evidence,
        audit=audit,
        workflow_step=incident.get("status"),
    )


def desk(*, db: Path | None = None, seed: bool = True) -> dict[str, Any]:
    seed_result = None
    if seed:
        seed_result = import_v1_seed(db=db)
    listing = list_incidents(db=db)
    listing["v1_seed"] = seed_result
    listing["page"] = "/msc/security-evidence"
    listing["api"] = API_PREFIX
    return listing


def handle_get(path: str, *, db: Path | None = None) -> dict[str, Any]:
    raw = path.split("?")[0]
    rest = raw[len(API_PREFIX) :].strip("/")
    if not rest:
        return desk(db=db)
    if rest == "meta":
        return stamp(
            categories=sorted(CATEGORIES),
            severities=sorted(SEVERITIES),
            statuses=sorted(STATUSES),
            evidence_kinds=sorted(EVIDENCE_KINDS),
            workflow=desk(db=db, seed=False).get("workflow"),
        )
    if rest == "stream" or rest.startswith("stream/") or rest == "cctv" or rest.startswith("cctv/"):
        return refuse_cctv_stream()
    if rest == "import-v1":
        return import_v1_seed(db=db)
    # detail
    incident_id = rest.split("/", 1)[0]
    return get_incident_detail(incident_id, db=db)


def handle_post(
    path: str,
    body: dict[str, Any] | None,
    *,
    actor: str = "PERS-MATT",
    db: Path | None = None,
) -> tuple[dict[str, Any], int]:
    payload = body if isinstance(body, dict) else {}
    raw = path.split("?")[0]
    rest = raw[len(API_PREFIX) :].strip("/")

    try:
        _guard_forbidden_keys(payload)
        if rest in {"stream", "cctv", "live", "footage"} or rest.startswith("stream/") or rest.startswith("cctv/"):
            out = refuse_cctv_stream(payload)
            return out, 405
        if rest in {"prod", "prod-mutate"} or "prod-mutate" in rest:
            out = refuse_prod_mutate(payload)
            return out, 403
        if rest.endswith("/delete") or rest.endswith("/purge"):
            out = refuse_delete_evidence(payload)
            return out, 405

        if not rest:
            result = create_incident(payload, actor=actor, db=db)
            return result, 200 if result.get("ok") else 400

        if rest == "import-v1":
            return import_v1_seed(db=db, actor=actor), 200

        parts = rest.split("/")
        incident_id = parts[0]
        action = parts[1] if len(parts) > 1 else ""

        if action == "evidence":
            result = add_evidence(incident_id, payload, actor=actor, db=db)
            return result, 200
        if action == "escalate":
            result = escalate(incident_id, payload, actor=actor, db=db)
            return result, 200
        if action == "action":
            result = record_action(incident_id, payload, actor=actor, db=db)
            return result, 200
        if action == "close":
            result = close_incident(incident_id, payload, actor=actor, db=db)
            return result, 200
        if action in {"delete", "purge"}:
            return refuse_delete_evidence(payload), 405
        if action == "":
            result = update_incident(incident_id, payload, actor=actor, db=db)
            return result, 200
        return stamp(ok=False, error="unknown_path", path=path), 404
    except SecurityEvidenceError as exc:
        return (
            stamp(ok=False, error=exc.code, message=str(exc)),
            exc.http_status,
        )
    except sqlite3.Error as exc:
        msg = str(exc)
        if "append-only" in msg:
            return refuse_delete_evidence({"detail": msg}), 405
        return stamp(ok=False, error="db_error", message=msg), 500
