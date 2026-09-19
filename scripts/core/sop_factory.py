#!/usr/bin/env python3
"""SOP Factory v1 (Beta only) — CAP-CORE-11 slice, not the full loop.

Decision served: 2026-09-19 PICK, SOP Factory v1 on Beta only
(docs/deliveries/GROK-PLAN-CORE-SOP-FACTORY-V1-2026-09-19.md).

Draft from an evidence note → append-only version → Owner/role approve →
list/read. A version is not live until an approval row exists. Versions and
approvals are append-only. Anonymous callers fail closed.

Does not train staff, mark a draft live, write Model C, or resolve
CR-c4ed4e3fa9f15a40. Honesty is bound to that CR and to the ledger row.
Maturity is never raised here. PROVEN and READY are not invented.
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
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-c4ed4e3fa9f15a40"
CAP_ID = "CAP-CORE-11"
TZ_UTC = timezone.utc

PERM_DRAFT = "core.sop.draft"
PERM_APPROVE = "core.sop.approve"
PERM_READ = "core.sop.read"

STATE_DRAFT = "DRAFT"
DECISION_APPROVED = "APPROVED"
GATE_OWNER = "owner"
GATE_ROLE = "role"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
FAKE_NOTES = frozenset(
    {"PROVEN", "READY", "BUILT", "SPECIFIED", "ABSENT", "LIVE", "APPROVED"}
)

DRAFT_KEYS = frozenset({"title", "body", "evidence_note"})
VERSION_KEYS = frozenset({"sop_id", "title", "body", "evidence_note"})
APPROVE_KEYS = frozenset({"version_id"})
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
    }
)

_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")
_SOP_RE = re.compile(
    r"^SOP-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_VER_RE = re.compile(
    r"^VER-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "sop_factory_v1",
    "append_only": True,
    "full_loop": False,
    "train_staff": False,
    "auto_train": False,
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
}


class SopFactoryError(ValueError):
    """Fail-closed validation. Does not invent a live SOP or a row."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act == "approve":
        return PERM_APPROVE
    if act in {"draft", "version"}:
        return PERM_DRAFT
    return PERM_READ


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
            "v1 lists drafts and the highest approved version. "
            "Training and operational use are not this slice."
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
    if sid in {"draft", "version", "approve"}:
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
