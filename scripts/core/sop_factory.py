#!/usr/bin/env python3
"""SOP Factory (Beta only) — CAP-CORE-11 loop on the existing factory.

Decision served: 2026-09-19 PICK, SOP Factory v1 on Beta only, extended by
the 28 Sep 2026 owner brief item 5 and SOP-FACTORY-1 (30 Sep 2026). This is
the same factory, not a second SOP system.

Evidence note → lesson candidate → human review gate → (only after APPROVE)
versioned approved draft. Learning / acknowledgement / use remain on the
same append-only spine. A version is not live until an approval row exists.
Review DENY leaves the candidate refused and does not mint a live rule.
Versions, learnings, candidates, review decisions, approvals, acknowledgements,
and uses are append-only. A rewritten file is not a version. Anonymous
callers fail closed. No auto-approve of production rules.

Acknowledgement is not staff training and not staff readiness. A use row is
not operating adoption and not human commissioning. Does not write Model C
or resolve CR-c4ed4e3fa9f15a40. Maturity is never raised here.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "sop_factory.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
DEMO_DB = (
    BETA_ROOT / "state" / "build-factory" / "tmp-sop-factory-1" / "sop_factory.sqlite"
)
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-c4ed4e3fa9f15a40"
CAP_ID = "CAP-CORE-11"
PACK_ID = "SOP-FACTORY-1"
TZ_UTC = timezone.utc

PERM_DRAFT = "core.sop.draft"
PERM_APPROVE = "core.sop.approve"
PERM_READ = "core.sop.read"

STATE_DRAFT = "DRAFT"
DECISION_APPROVED = "APPROVED"
DECISION_APPROVE = "APPROVE"
DECISION_DENY = "DENY"
CANDIDATE_PENDING = "PENDING_REVIEW"
CANDIDATE_APPROVED = "APPROVED"
CANDIDATE_DENIED = "DENIED"
GATE_OWNER = "owner"
GATE_ROLE = "role"
DEMO_LABEL = "DEMO / NOT LIVE STAFF ADOPTION"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
FAKE_NOTES = frozenset(
    {
        "PROVEN",
        "READY",
        "BUILT",
        "SPECIFIED",
        "ABSENT",
        "LIVE",
        "APPROVED",
        "STAFF_READY",
        "COMMISSIONED",
        "ADOPTED",
    }
)

DRAFT_KEYS = frozenset({"title", "body", "evidence_note"})
VERSION_KEYS = frozenset({"sop_id", "title", "body", "evidence_note"})
APPROVE_KEYS = frozenset({"version_id"})
LEARN_KEYS = frozenset({"version_id", "learning_note"})
ACK_KEYS = frozenset({"version_id"})
USE_KEYS = frozenset({"version_id", "use_note"})
CANDIDATE_KEYS = frozenset(
    {"version_id", "lesson_note", "learning_id", "title", "demo"}
)
REVIEW_KEYS = frozenset({"candidate_id", "decision", "decision_note"})
BANNED_KEYS = frozenset(
    {
        "state",
        "status",
        "live",
        "approved",
        "proven",
        "ready",
        "maturity",
        "train",
        "auto_train",
        "operational",
        "score",
        "staff_ready",
        "human_commissioned",
        "operating_adoption",
    }
)

_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")
_SOP_RE = re.compile(
    r"^SOP-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_VER_RE = re.compile(
    r"^VER-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
RESERVED_SOPS = frozenset(
    {
        "draft",
        "version",
        "approve",
        "learn",
        "acknowledge",
        "use",
        "lesson-candidate",
        "review-decision",
        "review-queue",
        "candidates",
    }
)
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)

HONESTY = {
    "cap": CAP_ID,
    "pack": PACK_ID,
    "slice": "sop_loop",
    "append_only": True,
    "full_loop": True,
    "human_review_gate": True,
    "auto_approve": False,
    "train_staff": False,
    "auto_train": False,
    "staff_ready": False,
    "human_commissioned": False,
    "operating_adoption": False,
    "file_rewrite_is_version": False,
    "live_without_approve": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_or_role": True,
    "invented_permission_grant": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "demo_is_live_adoption": False,
}


class SopFactoryError(ValueError):
    """Fail-closed validation. Does not invent a live SOP or a row."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"approve", "review-decision", "review"}:
        return PERM_APPROVE
    if act in {"draft", "version", "learn", "lesson-candidate", "candidate"}:
        return PERM_DRAFT
    return PERM_READ


def runtime_db_path() -> Path:
    """Prefer env override, then catalog DB if present, else DEMO fixture DB.

    Never invents catalog/sop_factory.sqlite. Demo path is labeled
    DEMO / NOT LIVE STAFF ADOPTION and is not staff readiness.
    """
    override = (os.environ.get("WOLF_SOP_FACTORY_DB") or "").strip()
    if override:
        return Path(override).resolve()
    if DEFAULT_DB.is_file():
        return LIVE_DEFAULT_DB
    return DEMO_DB.resolve()


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def ledger_cap_state() -> str:
    """Read CAP-CORE-11 from the Model C ledger. Does not write it."""
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID)
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    return state or "UNKNOWN"


def load_cr_binding() -> dict[str, Any]:
    """Read CR-c4ed4e3fa9f15a40. Does not upsert, resolve, or harvest."""
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
    if not CATALOG_DB.is_file():
        return out
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action,
                   resolution_evidence
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


def honesty_flags() -> dict[str, Any]:
    state = ledger_cap_state()
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags.update(load_cr_binding())
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    return flags


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_SOP_FACTORY") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise SopFactoryError(
            "test mode refuses writes to the live SOP factory; "
            "point db_path at a temp file",
            code="live_guard",
        )


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise SopFactoryError(
            "SOP factory refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise SopFactoryError(
            "SOP factory refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise SopFactoryError(
            "SOP factory refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
    except ValueError as exc:
        raise SopFactoryError(
            "SOP factory refuses a non-beta path",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_SOP_FACTORY_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    return resolved


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sop_versions (
  version_id TEXT PRIMARY KEY,
  sop_id TEXT NOT NULL,
  version_n INTEGER NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  evidence_note TEXT NOT NULL,
  state TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(sop_id, version_n)
);

CREATE INDEX IF NOT EXISTS idx_sop_versions_sop ON sop_versions(sop_id, version_n);

CREATE TABLE IF NOT EXISTS sop_approvals (
  approval_id TEXT PRIMARY KEY,
  version_id TEXT NOT NULL UNIQUE,
  sop_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  decided_by TEXT NOT NULL,
  gate TEXT NOT NULL,
  decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sop_approvals_sop ON sop_approvals(sop_id);

CREATE TRIGGER IF NOT EXISTS trg_sop_versions_no_update
BEFORE UPDATE ON sop_versions
BEGIN
  SELECT RAISE(ABORT, 'sop_versions is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_versions_no_delete
BEFORE DELETE ON sop_versions
BEGIN
  SELECT RAISE(ABORT, 'sop_versions is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_approvals_no_update
BEFORE UPDATE ON sop_approvals
BEGIN
  SELECT RAISE(ABORT, 'sop_approvals is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_approvals_no_delete
BEFORE DELETE ON sop_approvals
BEGIN
  SELECT RAISE(ABORT, 'sop_approvals is append-only');
END;

CREATE TABLE IF NOT EXISTS sop_learnings (
  learning_id TEXT PRIMARY KEY,
  sop_id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  learning_note TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sop_learnings_version ON sop_learnings(version_id);

CREATE TABLE IF NOT EXISTS sop_acknowledgements (
  acknowledgement_id TEXT PRIMARY KEY,
  version_id TEXT NOT NULL,
  sop_id TEXT NOT NULL,
  person_id TEXT NOT NULL,
  acknowledged_at TEXT NOT NULL,
  UNIQUE(version_id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_sop_ack_version ON sop_acknowledgements(version_id);

CREATE TABLE IF NOT EXISTS sop_uses (
  use_id TEXT PRIMARY KEY,
  version_id TEXT NOT NULL,
  sop_id TEXT NOT NULL,
  use_note TEXT NOT NULL,
  recorded_by TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sop_uses_version ON sop_uses(version_id);

CREATE TRIGGER IF NOT EXISTS trg_sop_learnings_no_update
BEFORE UPDATE ON sop_learnings
BEGIN
  SELECT RAISE(ABORT, 'sop_learnings is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_learnings_no_delete
BEFORE DELETE ON sop_learnings
BEGIN
  SELECT RAISE(ABORT, 'sop_learnings is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_acknowledgements_no_update
BEFORE UPDATE ON sop_acknowledgements
BEGIN
  SELECT RAISE(ABORT, 'sop_acknowledgements is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_acknowledgements_no_delete
BEFORE DELETE ON sop_acknowledgements
BEGIN
  SELECT RAISE(ABORT, 'sop_acknowledgements is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_uses_no_update
BEFORE UPDATE ON sop_uses
BEGIN
  SELECT RAISE(ABORT, 'sop_uses is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_uses_no_delete
BEFORE DELETE ON sop_uses
BEGIN
  SELECT RAISE(ABORT, 'sop_uses is append-only');
END;

CREATE TABLE IF NOT EXISTS sop_lesson_candidates (
  candidate_id TEXT PRIMARY KEY,
  sop_id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  learning_id TEXT,
  title TEXT NOT NULL,
  lesson_note TEXT NOT NULL,
  evidence_note TEXT NOT NULL,
  demo_label TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sop_candidates_version
  ON sop_lesson_candidates(version_id);
CREATE INDEX IF NOT EXISTS idx_sop_candidates_sop
  ON sop_lesson_candidates(sop_id);

CREATE TABLE IF NOT EXISTS sop_review_decisions (
  decision_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL UNIQUE,
  sop_id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  decided_by TEXT NOT NULL,
  gate TEXT NOT NULL,
  decision_note TEXT NOT NULL,
  decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sop_review_candidate
  ON sop_review_decisions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_sop_review_sop
  ON sop_review_decisions(sop_id);

CREATE TRIGGER IF NOT EXISTS trg_sop_candidates_no_update
BEFORE UPDATE ON sop_lesson_candidates
BEGIN
  SELECT RAISE(ABORT, 'sop_lesson_candidates is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_candidates_no_delete
BEFORE DELETE ON sop_lesson_candidates
BEGIN
  SELECT RAISE(ABORT, 'sop_lesson_candidates is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_review_no_update
BEFORE UPDATE ON sop_review_decisions
BEGIN
  SELECT RAISE(ABORT, 'sop_review_decisions is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_sop_review_no_delete
BEFORE DELETE ON sop_review_decisions
BEGIN
  SELECT RAISE(ABORT, 'sop_review_decisions is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _require_actor(person_id: str | None, *, role_allowed: bool) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise SopFactoryError("anonymous callers are refused", code="denied")
    if pid == OWNER_PERSON:
        return GATE_OWNER
    if role_allowed is True and _PERSON_RE.match(pid):
        return GATE_ROLE
    raise SopFactoryError(
        "SOP factory is Owner (PERS-MATT) or an authorised role only",
        code="denied",
    )


def _reject_keys(body: dict, allowed: frozenset[str]) -> None:
    if not isinstance(body, dict):
        raise SopFactoryError("payload must be an object", code="invalid")
    banned = sorted(set(body) & BANNED_KEYS)
    if banned:
        raise SopFactoryError(
            "refused field " + ",".join(banned) + "; a client cannot mark an SOP live",
            code="refused_field",
        )
    extra = sorted(set(body) - allowed)
    if extra:
        raise SopFactoryError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _clean_text(value: Any, *, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise SopFactoryError(f"{field} must be a string", code="invalid")
    text = value.strip()
    if len(text) < min_len or len(text) > max_len:
        raise SopFactoryError(
            f"{field} length must be {min_len}..{max_len}",
            code="invalid",
        )
    if _SECRET_RE.search(text):
        raise SopFactoryError(f"{field} looks like a secret", code="invalid")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise SopFactoryError(f"{field} has a control character", code="invalid")
    return text


def _evidence_note(value: Any) -> str:
    if isinstance(value, str) and value.strip().upper() in FAKE_NOTES:
        raise SopFactoryError(
            "evidence note cannot be a maturity word",
            code="missing_evidence",
        )
    note = _clean_text(value, field="evidence_note", min_len=12, max_len=4000)
    if note.upper() in FAKE_NOTES:
        raise SopFactoryError(
            "evidence note cannot be a maturity word",
            code="missing_evidence",
        )
    return note


def _title(value: Any) -> str:
    return _clean_text(value, field="title", min_len=3, max_len=160)


def _body(value: Any) -> str:
    return _clean_text(value, field="body", min_len=12, max_len=12000)


def _open_write(db_path: Path | str | None) -> tuple[sqlite3.Connection, Path]:
    resolved = _resolve_db(db_path)
    assert_db_writable(resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn, resolved


def _open_read(db_path: Path | str | None) -> tuple[sqlite3.Connection | None, Path]:
    resolved = _resolve_db(db_path)
    if not resolved.exists():
        return None, resolved
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    return conn, resolved


def _approved_ids(conn: sqlite3.Connection, sop_id: str | None = None) -> set[str]:
    if sop_id is None:
        rows = conn.execute("SELECT version_id FROM sop_approvals").fetchall()
    else:
        rows = conn.execute(
            "SELECT version_id FROM sop_approvals WHERE sop_id=?",
            (sop_id,),
        ).fetchall()
    return {str(r[0]) for r in rows}


def _live_version_id(conn: sqlite3.Connection, sop_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT v.version_id
        FROM sop_versions v
        JOIN sop_approvals a ON a.version_id = v.version_id
        WHERE v.sop_id=?
        ORDER BY v.version_n DESC
        LIMIT 1
        """,
        (sop_id,),
    ).fetchone()
    return str(row[0]) if row else None


def create_draft(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, DRAFT_KEYS)
    title = _title(body.get("title"))
    text = _body(body.get("body"))
    note = _evidence_note(body.get("evidence_note"))
    sop_id = f"SOP-{uuid.uuid4()}"
    version_id = f"VER-{uuid.uuid4()}"
    conn, _path = _open_write(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_versions (
              version_id, sop_id, version_n, title, body, evidence_note,
              state, created_by, created_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                sop_id,
                title,
                text,
                note,
                STATE_DRAFT,
                person_id,
                now_utc_iso(),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "sop_id": sop_id,
        "version_id": version_id,
        "version_n": 1,
        "state": STATE_DRAFT,
        "live": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def append_version(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, VERSION_KEYS)
    sop_id = str(body.get("sop_id") or "").strip()
    if not _SOP_RE.match(sop_id):
        raise SopFactoryError("sop_id is not a SOP factory id", code="invalid")
    title = _title(body.get("title"))
    text = _body(body.get("body"))
    note = _evidence_note(body.get("evidence_note"))
    resolved = _resolve_db(db_path)
    if not resolved.exists():
        raise SopFactoryError("SOP not found", code="not_found")
    version_id = f"VER-{uuid.uuid4()}"
    conn, _path = _open_write(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT MAX(version_n) FROM sop_versions WHERE sop_id=?",
            (sop_id,),
        ).fetchone()
        if row is None or row[0] is None:
            raise SopFactoryError("SOP not found", code="not_found")
        version_n = int(row[0]) + 1
        conn.execute(
            """
            INSERT INTO sop_versions (
              version_id, sop_id, version_n, title, body, evidence_note,
              state, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                sop_id,
                version_n,
                title,
                text,
                note,
                STATE_DRAFT,
                person_id,
                now_utc_iso(),
            ),
        )
        conn.commit()
        live_id = _live_version_id(conn, sop_id)
    except SopFactoryError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "sop_id": sop_id,
        "version_id": version_id,
        "version_n": version_n,
        "state": STATE_DRAFT,
        "live": False,
        "live_version_id": live_id,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def approve(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, APPROVE_KEYS)
    version_id = str(body.get("version_id") or "").strip()
    if not _VER_RE.match(version_id):
        raise SopFactoryError("version_id is not a SOP factory id", code="invalid")
    approval_id = f"APR-{uuid.uuid4()}"
    conn, path = _open_write(db_path) if Path(_resolve_db(db_path)).exists() else (None, None)
    if conn is None:
        # Opening a missing file would create a schema with no version. Refuse.
        raise SopFactoryError("SOP version not found", code="not_found")
    try:
        before = conn.execute(
            "SELECT sop_id, version_n, title, body, evidence_note, state "
            "FROM sop_versions WHERE version_id=?",
            (version_id,),
        ).fetchone()
        if before is None:
            raise SopFactoryError("SOP version not found", code="not_found")
        if not str(before["evidence_note"] or "").strip():
            raise SopFactoryError(
                "cannot approve a version with no evidence note",
                code="missing_evidence",
            )
        existing = conn.execute(
            "SELECT approval_id FROM sop_approvals WHERE version_id=?",
            (version_id,),
        ).fetchone()
        if existing is not None:
            raise SopFactoryError(
                "this version is already approved",
                code="already_approved",
            )
        snapshot = tuple(before)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_approvals (
              approval_id, version_id, sop_id, decision, decided_by, gate, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                version_id,
                before["sop_id"],
                DECISION_APPROVED,
                person_id,
                gate,
                now_utc_iso(),
            ),
        )
        after = conn.execute(
            "SELECT sop_id, version_n, title, body, evidence_note, state "
            "FROM sop_versions WHERE version_id=?",
            (version_id,),
        ).fetchone()
        if tuple(after) != snapshot:
            raise SopFactoryError(
                "approve must not rewrite the version",
                code="invalid",
            )
        conn.commit()
        sop_id = str(before["sop_id"])
        version_n = int(before["version_n"])
        live_id = _live_version_id(conn, sop_id)
    except SopFactoryError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SopFactoryError(
            "this version is already approved",
            code="already_approved",
        ) from exc
    finally:
        conn.close()
    return {
        "appended": True,
        "approval_id": approval_id,
        "version_id": version_id,
        "sop_id": sop_id,
        "version_n": version_n,
        "decision": DECISION_APPROVED,
        "gate": gate,
        "live": live_id == version_id,
        "live_version_id": live_id,
        "version_unchanged": True,
        "honesty": honesty_flags(),
    }


def refuse_unversioned_rewrite(body: dict) -> None:
    """A file path or a raw rewrite is not a SOP version. Writes nothing."""
    if not isinstance(body, dict):
        raise SopFactoryError("payload must be an object", code="unversioned")
    raise SopFactoryError(
        "a rewritten file is not a version; append a version",
        code="unversioned",
    )


def _open_existing(db_path: Path | str | None) -> sqlite3.Connection:
    resolved = _resolve_db(db_path)
    if not resolved.exists():
        raise SopFactoryError("SOP version not found", code="not_found")
    conn, _path = _open_write(db_path)
    return conn


def _version_row(conn: sqlite3.Connection, version_id: str) -> sqlite3.Row:
    if not _VER_RE.match(version_id):
        raise SopFactoryError("version_id is not a SOP factory id", code="invalid")
    row = conn.execute(
        """
        SELECT version_id, sop_id, version_n, title, body, evidence_note, state,
               created_by, created_at
        FROM sop_versions WHERE version_id=?
        """,
        (version_id,),
    ).fetchone()
    if row is None:
        raise SopFactoryError("SOP version not found", code="not_found")
    return row


def _approval_row(conn: sqlite3.Connection, version_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT approval_id, decided_by, gate FROM sop_approvals WHERE version_id=?",
        (version_id,),
    ).fetchone()


def _unchanged(before: sqlite3.Row, after: sqlite3.Row | None) -> None:
    if after is None or tuple(after) != tuple(before):
        raise SopFactoryError(
            "the loop must not rewrite the version",
            code="invalid",
        )


def _loop_flags() -> dict[str, bool]:
    return {
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "version_unchanged": True,
    }


def record_learning(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, LEARN_KEYS)
    version_id = str(body.get("version_id") or "").strip()
    note = _evidence_note(body.get("learning_note"))
    learning_id = f"LRN-{uuid.uuid4()}"
    conn = _open_existing(db_path)
    try:
        before = _version_row(conn, version_id)
        if not str(before["evidence_note"] or "").strip():
            raise SopFactoryError(
                "cannot learn from a version with no evidence note",
                code="missing_evidence",
            )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_learnings (
              learning_id, sop_id, version_id, learning_note, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                learning_id,
                before["sop_id"],
                version_id,
                note,
                person_id,
                now_utc_iso(),
            ),
        )
        _unchanged(before, _version_row(conn, version_id))
        conn.commit()
        sop_id = str(before["sop_id"])
    except SopFactoryError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "learning_id": learning_id,
        "version_id": version_id,
        "sop_id": sop_id,
        "gate": gate,
        "live": False,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def acknowledge(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, ACK_KEYS)
    version_id = str(body.get("version_id") or "").strip()
    acknowledgement_id = f"ACK-{uuid.uuid4()}"
    conn = _open_existing(db_path)
    try:
        before = _version_row(conn, version_id)
        approval = _approval_row(conn, version_id)
        if approval is None:
            raise SopFactoryError(
                "cannot acknowledge a version with no approver",
                code="not_approved",
            )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_acknowledgements (
              acknowledgement_id, version_id, sop_id, person_id, acknowledged_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                acknowledgement_id,
                version_id,
                before["sop_id"],
                person_id,
                now_utc_iso(),
            ),
        )
        _unchanged(before, _version_row(conn, version_id))
        conn.commit()
        sop_id = str(before["sop_id"])
    except SopFactoryError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SopFactoryError(
            "this person already acknowledged this version",
            code="already_acknowledged",
        ) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "acknowledgement_id": acknowledgement_id,
        "version_id": version_id,
        "sop_id": sop_id,
        "gate": gate,
        "approver_recorded": True,
        "trains_staff": False,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def record_use(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, USE_KEYS)
    version_id = str(body.get("version_id") or "").strip()
    note = _evidence_note(body.get("use_note"))
    use_id = f"USE-{uuid.uuid4()}"
    conn = _open_existing(db_path)
    try:
        before = _version_row(conn, version_id)
        live_id = _live_version_id(conn, str(before["sop_id"]))
        if live_id != version_id:
            raise SopFactoryError(
                "use records the current live version only",
                code="not_live",
            )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_uses (
              use_id, version_id, sop_id, use_note, recorded_by, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                use_id,
                version_id,
                before["sop_id"],
                note,
                person_id,
                now_utc_iso(),
            ),
        )
        _unchanged(before, _version_row(conn, version_id))
        conn.commit()
        sop_id = str(before["sop_id"])
    except SopFactoryError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "use_id": use_id,
        "version_id": version_id,
        "sop_id": sop_id,
        "gate": gate,
        "live": True,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _stage_count(conn: sqlite3.Connection, table: str, sop_id: str) -> int | None:
    if table not in _table_names(conn):
        return None
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE sop_id=?",
        (sop_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def loop_status(
    sop_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read the loop stages for one SOP. Does not insert a row."""
    _require_actor(person_id, role_allowed=role_allowed)
    sid = (sop_id or "").strip()
    if not _SOP_RE.match(sid):
        raise SopFactoryError("sop_id is not a SOP factory id", code="invalid")
    absent = {
        "evidence": "ABSENT",
        "learning": "ABSENT",
        "proposed_change": "ABSENT",
        "approval": "ABSENT",
        "versioning": "ABSENT",
        "acknowledgement": "ABSENT",
        "use": "ABSENT",
    }
    conn, path = _open_read(db_path)
    if conn is None:
        return {
            "sop_id": sid,
            "db_exists": False,
            "found": False,
            "version_count": None,
            "learning_count": None,
            "approval_count": None,
            "acknowledgement_count": None,
            "use_count": None,
            "approver_recorded": False,
            "prior_body_retained": None,
            "live_version_id": None,
            "stages": absent,
            **_loop_flags(),
            "honesty": honesty_flags(),
        }
    try:
        versions = conn.execute(
            """
            SELECT version_id, version_n, body, evidence_note
            FROM sop_versions WHERE sop_id=?
            ORDER BY version_n ASC
            """,
            (sid,),
        ).fetchall()
        if not versions:
            raise SopFactoryError("SOP not found", code="not_found")
        names = _table_names(conn)
        learning_count = _stage_count(conn, "sop_learnings", sid)
        approval_count = _stage_count(conn, "sop_approvals", sid)
        ack_count = _stage_count(conn, "sop_acknowledgements", sid)
        use_count = _stage_count(conn, "sop_uses", sid)
        evidence_ok = all(str(row["evidence_note"] or "").strip() for row in versions)
        prior_retained = None
        if len(versions) >= 2:
            prior_retained = int(versions[0]["version_n"]) < int(versions[-1]["version_n"])
        live_id = _live_version_id(conn, sid) if "sop_approvals" in names else None

        def _mark(count: int | None, *, present_if: bool) -> str:
            if count is None:
                return "ABSENT"
            if present_if and count > 0:
                return "PRESENT"
            if count == 0:
                return "EMPTY"
            return "EMPTY"

        stages = {
            "evidence": "PRESENT" if evidence_ok else "EMPTY",
            "learning": _mark(learning_count, present_if=True),
            "proposed_change": "PRESENT" if len(versions) >= 1 else "EMPTY",
            "approval": _mark(approval_count, present_if=True),
            "versioning": "PRESENT" if len(versions) >= 2 else "EMPTY",
            "acknowledgement": _mark(ack_count, present_if=True),
            "use": _mark(use_count, present_if=True),
        }
    finally:
        conn.close()
    return {
        "sop_id": sid,
        "db_exists": path.exists(),
        "found": True,
        "version_count": len(versions),
        "learning_count": learning_count,
        "approval_count": approval_count,
        "acknowledgement_count": ack_count,
        "use_count": use_count,
        "approver_recorded": bool(approval_count and approval_count > 0),
        "prior_body_retained": prior_retained,
        "live_version_id": live_id,
        "stages": stages,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def _summary_row(conn: sqlite3.Connection, sop_id: str) -> dict[str, Any]:
    latest = conn.execute(
        """
        SELECT version_id, version_n, title, state
        FROM sop_versions WHERE sop_id=?
        ORDER BY version_n DESC LIMIT 1
        """,
        (sop_id,),
    ).fetchone()
    live_id = _live_version_id(conn, sop_id)
    live_n = None
    if live_id:
        nrow = conn.execute(
            "SELECT version_n FROM sop_versions WHERE version_id=?",
            (live_id,),
        ).fetchone()
        live_n = int(nrow[0]) if nrow else None
    return {
        "sop_id": sop_id,
        "title": latest["title"],
        "latest_version_id": latest["version_id"],
        "latest_version_n": int(latest["version_n"]),
        "latest_state": latest["state"],
        "live_version_id": live_id,
        "live_version_n": live_n,
        "live": live_id is not None,
    }


def list_sops(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    _require_actor(person_id, role_allowed=role_allowed)
    conn, path = _open_read(db_path)
    if conn is None:
        return {
            "count": 0,
            "sops": [],
            "db_exists": False,
            "summary": (
                "No SOP file yet. Nothing was invented. "
                "A draft is not live until the approve gate writes an approval."
            ),
            "honesty": honesty_flags(),
        }
    try:
        ids = [
            str(r[0])
            for r in conn.execute(
                "SELECT DISTINCT sop_id FROM sop_versions ORDER BY sop_id"
            )
        ]
        sops = [_summary_row(conn, sop_id) for sop_id in ids]
    finally:
        conn.close()
    return {
        "count": len(sops),
        "sops": sops,
        "db_exists": path.exists(),
        "summary": (
            "Lists drafts and the highest approved version. "
            "An acknowledgement is not staff readiness. "
            "A use row is not operating adoption."
        ),
        "honesty": honesty_flags(),
    }


def read_sop(
    sop_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    _require_actor(person_id, role_allowed=role_allowed)
    sid = (sop_id or "").strip()
    if sid in RESERVED_SOPS:
        raise SopFactoryError("reserved path", code="not_found")
    if not _SOP_RE.match(sid):
        raise SopFactoryError("sop_id is not a SOP factory id", code="invalid")
    conn, _path = _open_read(db_path)
    if conn is None:
        raise SopFactoryError("SOP not found", code="not_found")
    try:
        rows = conn.execute(
            """
            SELECT version_id, version_n, title, body, evidence_note, state,
                   created_by, created_at
            FROM sop_versions WHERE sop_id=?
            ORDER BY version_n ASC
            """,
            (sid,),
        ).fetchall()
        if not rows:
            raise SopFactoryError("SOP not found", code="not_found")
        approved = _approved_ids(conn, sid)
        live_id = _live_version_id(conn, sid)
        versions = []
        for row in rows:
            vid = str(row["version_id"])
            versions.append(
                {
                    "version_id": vid,
                    "version_n": int(row["version_n"]),
                    "title": row["title"],
                    "body": row["body"],
                    "evidence_note": row["evidence_note"],
                    "state": row["state"],
                    "created_by": row["created_by"],
                    "created_at": row["created_at"],
                    "approved": vid in approved,
                    "live": vid == live_id,
                }
            )
    finally:
        conn.close()
    return {
        "sop_id": sid,
        "versions": versions,
        "live_version_id": live_id,
        "live": live_id is not None,
        "honesty": honesty_flags(),
    }


_CAND_RE = re.compile(
    r"^CND-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_LRN_RE = re.compile(
    r"^LRN-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _lesson_note(value: Any) -> str:
    note = _clean_text(value, field="lesson_note", min_len=12, max_len=4000)
    if note.upper() in FAKE_NOTES:
        raise SopFactoryError(
            "lesson note cannot be a maturity word",
            code="missing_evidence",
        )
    return note


def _decision_note(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "human review decision recorded"
    return _clean_text(value, field="decision_note", min_len=3, max_len=2000)


def _candidate_review_status(
    conn: sqlite3.Connection, candidate_id: str
) -> tuple[str, dict[str, Any] | None]:
    row = conn.execute(
        """
        SELECT decision_id, decision, decided_by, gate, decision_note, decided_at
        FROM sop_review_decisions WHERE candidate_id=?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return CANDIDATE_PENDING, None
    decision = str(row["decision"])
    status = (
        CANDIDATE_APPROVED if decision == DECISION_APPROVE else CANDIDATE_DENIED
    )
    return status, {
        "decision_id": row["decision_id"],
        "decision": decision,
        "decided_by": row["decided_by"],
        "gate": row["gate"],
        "decision_note": row["decision_note"],
        "decided_at": row["decided_at"],
    }


def propose_lesson_candidate(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Evidence-backed version → lesson candidate awaiting human review.

    Does not approve. Does not mark live. Does not train staff.
    """
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, CANDIDATE_KEYS)
    version_id = str(body.get("version_id") or "").strip()
    lesson = _lesson_note(body.get("lesson_note"))
    learning_id = body.get("learning_id")
    if learning_id is None or (
        isinstance(learning_id, str) and not learning_id.strip()
    ):
        learning_id = None
    else:
        learning_id = str(learning_id).strip()
        if not _LRN_RE.match(learning_id):
            raise SopFactoryError("learning_id is not a factory id", code="invalid")
    demo_flag = body.get("demo")
    if demo_flag is True or (
        isinstance(demo_flag, str) and demo_flag.strip().upper() in {"1", "TRUE", "DEMO"}
    ):
        demo_label = DEMO_LABEL
    else:
        demo_label = ""
    title_override = body.get("title")
    candidate_id = f"CND-{uuid.uuid4()}"
    conn = _open_existing(db_path)
    try:
        before = _version_row(conn, version_id)
        evidence = str(before["evidence_note"] or "").strip()
        if not evidence:
            raise SopFactoryError(
                "cannot propose a lesson without an evidence note",
                code="missing_evidence",
            )
        if learning_id is not None:
            lrow = conn.execute(
                "SELECT learning_id FROM sop_learnings WHERE learning_id=? AND version_id=?",
                (learning_id, version_id),
            ).fetchone()
            if lrow is None:
                raise SopFactoryError(
                    "learning_id does not belong to this version",
                    code="not_found",
                )
        title = (
            _title(title_override)
            if title_override is not None
            else str(before["title"])
        )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_lesson_candidates (
              candidate_id, sop_id, version_id, learning_id, title,
              lesson_note, evidence_note, demo_label, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                before["sop_id"],
                version_id,
                learning_id,
                title,
                lesson,
                evidence,
                demo_label,
                person_id,
                now_utc_iso(),
            ),
        )
        _unchanged(before, _version_row(conn, version_id))
        conn.commit()
        sop_id = str(before["sop_id"])
    except SopFactoryError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "candidate_id": candidate_id,
        "sop_id": sop_id,
        "version_id": version_id,
        "review_status": CANDIDATE_PENDING,
        "demo_label": demo_label or None,
        "live": False,
        "approved_rule": False,
        "gate": gate,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def review_decision(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Human review gate. APPROVE mints approval on the version; DENY refuses.

    Append-only. Does not rewrite the candidate or version body. No auto-approve.
    """
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, REVIEW_KEYS)
    candidate_id = str(body.get("candidate_id") or "").strip()
    if not _CAND_RE.match(candidate_id):
        raise SopFactoryError("candidate_id is not a factory id", code="invalid")
    decision_raw = str(body.get("decision") or "").strip().upper()
    if decision_raw in {DECISION_APPROVE, DECISION_APPROVED}:
        decision = DECISION_APPROVE
    elif decision_raw == DECISION_DENY:
        decision = DECISION_DENY
    else:
        raise SopFactoryError(
            "decision must be APPROVE or DENY",
            code="invalid",
        )
    note = _decision_note(body.get("decision_note"))
    decision_id = f"REV-{uuid.uuid4()}"
    approval_id = None
    conn = _open_existing(db_path)
    try:
        cand = conn.execute(
            """
            SELECT candidate_id, sop_id, version_id, lesson_note, evidence_note,
                   demo_label, title
            FROM sop_lesson_candidates WHERE candidate_id=?
            """,
            (candidate_id,),
        ).fetchone()
        if cand is None:
            raise SopFactoryError("lesson candidate not found", code="not_found")
        existing = conn.execute(
            "SELECT decision_id FROM sop_review_decisions WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        if existing is not None:
            raise SopFactoryError(
                "this candidate already has a review decision",
                code="already_reviewed",
            )
        version_id = str(cand["version_id"])
        before = _version_row(conn, version_id)
        if not str(before["evidence_note"] or "").strip():
            raise SopFactoryError(
                "cannot review a version with no evidence note",
                code="missing_evidence",
            )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO sop_review_decisions (
              decision_id, candidate_id, sop_id, version_id, decision,
              decided_by, gate, decision_note, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                candidate_id,
                cand["sop_id"],
                version_id,
                decision,
                person_id,
                gate,
                note,
                now_utc_iso(),
            ),
        )
        live_id = None
        if decision == DECISION_APPROVE:
            prior_apr = conn.execute(
                "SELECT approval_id FROM sop_approvals WHERE version_id=?",
                (version_id,),
            ).fetchone()
            if prior_apr is not None:
                raise SopFactoryError(
                    "this version is already approved",
                    code="already_approved",
                )
            approval_id = f"APR-{uuid.uuid4()}"
            conn.execute(
                """
                INSERT INTO sop_approvals (
                  approval_id, version_id, sop_id, decision, decided_by, gate, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    version_id,
                    cand["sop_id"],
                    DECISION_APPROVED,
                    person_id,
                    gate,
                    now_utc_iso(),
                ),
            )
            live_id = _live_version_id(conn, str(cand["sop_id"]))
        _unchanged(before, _version_row(conn, version_id))
        # Candidate row must remain byte-identical (append-only; no status rewrite).
        after_cand = conn.execute(
            """
            SELECT candidate_id, sop_id, version_id, lesson_note, evidence_note,
                   demo_label, title
            FROM sop_lesson_candidates WHERE candidate_id=?
            """,
            (candidate_id,),
        ).fetchone()
        if after_cand is None or tuple(after_cand) != tuple(cand):
            raise SopFactoryError(
                "review must not rewrite the candidate",
                code="invalid",
            )
        conn.commit()
        sop_id = str(cand["sop_id"])
        demo_label_out = str(cand["demo_label"] or "") or None
        status = (
            CANDIDATE_APPROVED if decision == DECISION_APPROVE else CANDIDATE_DENIED
        )
    except SopFactoryError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SopFactoryError(
            "this candidate already has a review decision",
            code="already_reviewed",
        ) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "decision_id": decision_id,
        "candidate_id": candidate_id,
        "sop_id": sop_id,
        "version_id": version_id,
        "decision": decision,
        "review_status": status,
        "approval_id": approval_id,
        "approved_rule": decision == DECISION_APPROVE,
        "live": bool(live_id == version_id) if decision == DECISION_APPROVE else False,
        "live_version_id": live_id if decision == DECISION_APPROVE else None,
        "version_unchanged": True,
        "candidate_unchanged": True,
        "gate": gate,
        "demo_label": demo_label_out,
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def _candidate_payload(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    cid = str(row["candidate_id"])
    status, review = _candidate_review_status(conn, cid)
    approved = _approved_ids(conn, str(row["sop_id"]))
    live_id = _live_version_id(conn, str(row["sop_id"]))
    vid = str(row["version_id"])
    demo = str(row["demo_label"] or "")
    return {
        "candidate_id": cid,
        "sop_id": row["sop_id"],
        "version_id": vid,
        "learning_id": row["learning_id"],
        "title": row["title"],
        "lesson_note": row["lesson_note"],
        "evidence_note": row["evidence_note"],
        "demo_label": demo or None,
        "demo": bool(demo),
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "review_status": status,
        "review": review,
        "version_approved": vid in approved,
        "live": vid == live_id,
        "approved_rule": status == CANDIDATE_APPROVED and vid in approved,
    }


def list_lesson_candidates(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
    pending_only: bool = False,
) -> dict[str, Any]:
    _require_actor(person_id, role_allowed=role_allowed)
    conn, path = _open_read(db_path)
    if conn is None:
        return {
            "count": 0,
            "candidates": [],
            "pending_count": 0,
            "db_exists": False,
            "db_path": str(path),
            "demo_path": str(DEMO_DB),
            "summary": (
                "No SOP factory file yet. Nothing was invented. "
                "A lesson candidate is not an approved rule."
            ),
            "honesty": honesty_flags(),
        }
    try:
        names = _table_names(conn)
        if "sop_lesson_candidates" not in names:
            return {
                "count": 0,
                "candidates": [],
                "pending_count": 0,
                "db_exists": path.exists(),
                "db_path": str(path),
                "demo_path": str(DEMO_DB),
                "summary": (
                    "Factory file has no lesson-candidate table yet. "
                    "A draft is not an approved rule."
                ),
                "honesty": honesty_flags(),
            }
        rows = conn.execute(
            """
            SELECT candidate_id, sop_id, version_id, learning_id, title,
                   lesson_note, evidence_note, demo_label, created_by, created_at
            FROM sop_lesson_candidates
            ORDER BY created_at DESC
            """
        ).fetchall()
        all_candidates = [_candidate_payload(conn, row) for row in rows]
        pending_count = sum(
            1 for c in all_candidates if c["review_status"] == CANDIDATE_PENDING
        )
        candidates = (
            [c for c in all_candidates if c["review_status"] == CANDIDATE_PENDING]
            if pending_only
            else all_candidates
        )
    finally:
        conn.close()
    return {
        "count": len(candidates),
        "candidates": candidates,
        "pending_count": pending_count,
        "db_exists": path.exists(),
        "db_path": str(path),
        "demo_path": str(DEMO_DB),
        "summary": (
            "Lesson candidates await a human review decision. "
            "APPROVE writes an approval; DENY refuses the rule. "
            "DEMO rows are not live staff adoption."
        ),
        "honesty": honesty_flags(),
    }


def list_review_queue(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Pending lesson candidates only — the human review gate inbox."""
    out = list_lesson_candidates(
        person_id,
        role_allowed=role_allowed,
        db_path=db_path,
        pending_only=True,
    )
    out["queue"] = "human_review"
    out["summary"] = (
        "Human review queue. Nothing here is an approved rule until APPROVE. "
        "Unsigned callers are refused. Auto-approve is off."
    )
    return out


def seed_demo_vertical_slice(
    *,
    person_id: str | None = OWNER_PERSON,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Seed one DEMO evidence → candidate → pending review path.

    Writes only under the demo/tmp path by default. Does not create
    catalog/sop_factory.sqlite. Not staff readiness. Not live adoption.
    """
    path = Path(db_path) if db_path is not None else DEMO_DB
    resolved = path.resolve()
    if resolved == LIVE_DEFAULT_DB:
        raise SopFactoryError(
            "demo seed refuses the live catalog SOP factory path",
            code="live_guard",
        )
    if resolved.exists():
        # Re-open and report existing pending demo candidates if any.
        listed = list_review_queue(person_id, db_path=resolved)
        if listed.get("pending_count", 0) > 0:
            return {
                "seeded": False,
                "already_present": True,
                "db_path": str(resolved),
                "demo_label": DEMO_LABEL,
                **listed,
                "honesty": honesty_flags(),
            }

    draft = create_draft(
        {
            "title": "DEMO tin-count close line",
            "body": (
                "DEMO ONLY — Count the tin before the drawer is closed and "
                "write the number on the close card. Not live staff adoption."
            ),
            "evidence_note": (
                "DEMO evidence note: tin count was skipped on a fixture Uma close. "
                "This is a factory demo path, not operating adoption."
            ),
        },
        person_id=person_id,
        db_path=resolved,
    )
    learned = record_learning(
        {
            "version_id": draft["version_id"],
            "learning_note": (
                "DEMO lesson precursor: the miss was the missing line on the "
                "close card, not the count itself."
            ),
        },
        person_id=person_id,
        db_path=resolved,
    )
    candidate = propose_lesson_candidate(
        {
            "version_id": draft["version_id"],
            "learning_id": learned["learning_id"],
            "lesson_note": (
                "DEMO lesson candidate: require the tin-count line on the close "
                "card before lockup. Awaiting human review. Not an approved rule."
            ),
            "title": "DEMO tin-count close line",
            "demo": True,
        },
        person_id=person_id,
        db_path=resolved,
    )
    queue = list_review_queue(person_id, db_path=resolved)
    return {
        "seeded": True,
        "already_present": False,
        "db_path": str(resolved),
        "demo_label": DEMO_LABEL,
        "sop_id": draft["sop_id"],
        "version_id": draft["version_id"],
        "learning_id": learned["learning_id"],
        "candidate_id": candidate["candidate_id"],
        "review_status": CANDIDATE_PENDING,
        "live": False,
        "approved_rule": False,
        "pending_count": queue.get("pending_count"),
        "candidates": queue.get("candidates"),
        **_loop_flags(),
        "honesty": honesty_flags(),
    }


def refuse_history_rewrite(body: dict) -> None:
    """Explicit refuse for update/delete that would rewrite SOP history."""
    if not isinstance(body, dict):
        raise SopFactoryError("payload must be an object", code="unversioned")
    action = str(body.get("action") or body.get("op") or "rewrite").strip().lower()
    raise SopFactoryError(
        f"refused {action or 'rewrite'}: SOP factory history is append-only; "
        "append a version or a review decision instead",
        code="append_only",
    )

