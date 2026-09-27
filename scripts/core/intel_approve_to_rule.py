#!/usr/bin/env python3
"""CAP-INTEL-05 approve-to-rule learning loop skeleton (Beta only).

Decision served: 2026-09-20 PICK, approve-to-rule learning loop skeleton on
Beta only (docs/deliveries/GROK-PLAN-INTEL-APPROVE-TO-RULE-V1-2026-09-19.md).

Experiment note → Owner or role approve → versioned rule stub. All three
tables are append-only. A stub is not executed and is not promoted.

Does not write the Model C ledger, resolve CR-be51980bd1194448, or invent
PROVEN or READY. The in-code ceiling is BUILT unless the ledger row is
already PROVEN or READY. CAP-INTEL-05 stays at the ledger state.
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
DEFAULT_DB = BETA_ROOT / "catalog" / "intel_approve_to_rule.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-be51980bd1194448"
CAP_ID = "CAP-INTEL-05"
TZ_UTC = timezone.utc

PERM_NOTE = "intel.rule.note"
PERM_APPROVE = "intel.rule.approve"
PERM_READ = "intel.rule.read"

STATE_NOTED = "NOTED"
STATE_APPROVED = "APPROVED"
STATE_STUB = "STUB"
DECISION_APPROVED = "APPROVED"
GATE_OWNER = "owner"
GATE_ROLE = "role"

OWNER_PROVE_PATH = "GET /api/intel/approve-to-rule"

HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY_WORDS = frozenset(
    {"PROVEN", "READY", "BUILT", "SPECIFIED", "ABSENT", "LIVE", "APPROVED"}
)
SCORE_WORDS = frozenset({"PROVEN", "READY"})

NOTE_KEYS = frozenset({"experiment_note", "experiment_id"})
APPROVE_KEYS = frozenset({"note_id"})
RULE_KEYS = frozenset({"note_id", "rule_text"})
SCORE_KEYS = frozenset({"proven", "ready", "maturity", "cap_proven", "score"})
PROMOTE_KEYS = frozenset(
    {"promote", "auto_promote", "production", "operational", "live_rule"}
)
EXECUTE_KEYS = frozenset({"execute", "run", "live"})
BANNED_KEYS = SCORE_KEYS | PROMOTE_KEYS | EXECUTE_KEYS | frozenset(
    {"state", "status", "approved"}
)

_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")
_EXP_RE = re.compile(
    r"^EXP-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_NOTE_RE = re.compile(
    r"^NOTE-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_STUB_RE = re.compile(
    r"^RULE-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)

GAPS: tuple[str, ...] = (
    "A rule stub is not a live operating rule.",
    "Approval does not create a rule and does not promote one.",
    "No rule is executed.",
    "Auto-promote to production rules is refused.",
    "CAP-INTEL-05 stays at the ledger state. This skeleton does not write it.",
    "CR-be51980bd1194448 stays OPEN.",
    "Noise suppression and performance learning are not this slice.",
    "Chat agents are not this slice.",
)

RED_TEAM: tuple[dict[str, str], ...] = (
    {
        "case": "invent_proven",
        "result": "REFUSED",
        "code": "score_refused",
    },
    {
        "case": "auto_promote",
        "result": "REFUSED",
        "code": "promote_refused",
    },
    {
        "case": "anon",
        "result": "FAIL_CLOSED",
        "code": "denied",
    },
    {
        "case": "write_without_approve",
        "result": "REFUSED",
        "code": "approve_required",
    },
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "intel_approve_to_rule_v1",
    "append_only": True,
    "full_loop": False,
    "framework_skeleton": "BUILT",
    "auto_promote": False,
    "rule_execution": False,
    "production_rules": False,
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


class IntelRuleError(ValueError):
    """Fail closed. Does not invent a production rule or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act == "approve":
        return PERM_APPROVE
    if act in {"note", "rule"}:
        return PERM_NOTE
    return PERM_READ


def ceiling_for(state: str) -> str:
    """In-code label only. Does not write the ledger."""
    cleaned = (state or "").strip().upper()
    if cleaned in HIGHER_THAN_BUILT:
        return cleaned
    return "BUILT"


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def ledger_cap_state() -> str:
    """Read CAP-INTEL-05. Does not write it."""
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
    """Read CR-be51980bd1194448. Does not upsert, resolve, or harvest."""
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
    ceiling = ceiling_for(state)
    flags = dict(HONESTY)
    flags.update(load_cr_binding())
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["framework_skeleton"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["auto_promote"] = False
    flags["rule_execution"] = False
    flags["production_rules"] = False
    return flags


def red_team_table() -> list[dict[str, str]]:
    return [dict(row) for row in RED_TEAM]


def gaps() -> list[str]:
    return list(GAPS)


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise IntelRuleError(
            "test mode refuses writes to the live approve-to-rule ledger; "
            "point db_path at a temp file",
            code="live_guard",
        )


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise IntelRuleError(
            "approve-to-rule refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise IntelRuleError(
            "approve-to-rule refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise IntelRuleError(
            "approve-to-rule refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
    except ValueError as exc:
        raise IntelRuleError(
            "approve-to-rule refuses a non-beta path",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_INTEL_RULE_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    return resolved


def refuse_promote(_body: dict | None = None) -> None:
    """A stub is not promoted. Production rules are not written."""
    raise IntelRuleError(
        "Auto-promote is refused. A rule stub is not a production rule.",
        code="promote_refused",
    )


def refuse_execute(_body: dict | None = None) -> None:
    """This skeleton does not execute a rule."""
    raise IntelRuleError(
        "Rule execution is refused. A stub does not change operating behaviour.",
        code="execute_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    """PROVEN and READY are not invented here."""
    raise IntelRuleError(
        "Inventing PROVEN or READY is refused. The ledger is not written.",
        code="score_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production is not this Beta skeleton."""
    raise IntelRuleError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_method(_body: dict | None = None) -> None:
    """PUT and PATCH cannot skip the note, approve, then stub steps."""
    raise IntelRuleError(
        "This method cannot write a rule. Use the note, approve, then rule steps.",
        code="writes_refused",
    )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intel_experiment_notes (
  note_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  note_n INTEGER NOT NULL,
  experiment_note TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state = 'NOTED'),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (experiment_id, note_n)
);

CREATE INDEX IF NOT EXISTS idx_intel_notes_exp
  ON intel_experiment_notes(experiment_id, note_n);

CREATE TABLE IF NOT EXISTS intel_note_approvals (
  approval_id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL UNIQUE,
  experiment_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision = 'APPROVED'),
  decided_by TEXT NOT NULL,
  gate TEXT NOT NULL,
  decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_intel_approvals_exp
  ON intel_note_approvals(experiment_id);

CREATE TABLE IF NOT EXISTS intel_rule_stubs (
  stub_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  note_id TEXT NOT NULL,
  approval_id TEXT NOT NULL,
  version_n INTEGER NOT NULL,
  rule_text TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state = 'STUB'),
  promoted INTEGER NOT NULL CHECK (promoted = 0),
  executed INTEGER NOT NULL CHECK (executed = 0),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (experiment_id, version_n)
);

CREATE INDEX IF NOT EXISTS idx_intel_stubs_exp
  ON intel_rule_stubs(experiment_id, version_n);

CREATE TRIGGER IF NOT EXISTS trg_intel_notes_no_update
BEFORE UPDATE ON intel_experiment_notes
BEGIN
  SELECT RAISE(ABORT, 'intel_experiment_notes is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_notes_no_delete
BEFORE DELETE ON intel_experiment_notes
BEGIN
  SELECT RAISE(ABORT, 'intel_experiment_notes is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_approvals_no_update
BEFORE UPDATE ON intel_note_approvals
BEGIN
  SELECT RAISE(ABORT, 'intel_note_approvals is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_approvals_no_delete
BEFORE DELETE ON intel_note_approvals
BEGIN
  SELECT RAISE(ABORT, 'intel_note_approvals is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_stubs_no_update
BEFORE UPDATE ON intel_rule_stubs
BEGIN
  SELECT RAISE(ABORT, 'intel_rule_stubs is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_stubs_no_delete
BEFORE DELETE ON intel_rule_stubs
BEGIN
  SELECT RAISE(ABORT, 'intel_rule_stubs is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _require_actor(person_id: str | None, *, role_allowed: bool) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise IntelRuleError("anonymous callers are refused", code="denied")
    if pid == OWNER_PERSON:
        return GATE_OWNER
    if role_allowed is True and _PERSON_RE.match(pid):
        return GATE_ROLE
    raise IntelRuleError(
        "approve-to-rule is Owner (PERS-MATT) or an authorised role only",
        code="denied",
    )


def _reject_keys(body: dict, allowed: frozenset[str]) -> None:
    if not isinstance(body, dict):
        raise IntelRuleError("payload must be an object", code="invalid")
    if set(body) & SCORE_KEYS:
        raise IntelRuleError(
            "Inventing PROVEN or READY is refused. The ledger is not written.",
            code="score_refused",
        )
    if set(body) & PROMOTE_KEYS:
        raise IntelRuleError(
            "Auto-promote is refused. A rule stub is not a production rule.",
            code="promote_refused",
        )
    if set(body) & EXECUTE_KEYS:
        raise IntelRuleError(
            "Rule execution is refused. A stub does not change operating behaviour.",
            code="execute_refused",
        )
    banned = sorted(set(body) & BANNED_KEYS)
    if banned:
        raise IntelRuleError(
            "refused field " + ",".join(banned),
            code="refused_field",
        )
    extra = sorted(set(body) - allowed)
    if extra:
        raise IntelRuleError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _clean_text(value: Any, *, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise IntelRuleError(f"{field} must be a string", code="invalid")
    text = value.strip()
    upper = text.upper()
    if upper in SCORE_WORDS:
        raise IntelRuleError(
            f"{field} cannot invent PROVEN or READY",
            code="score_refused",
        )
    if upper in MATURITY_WORDS:
        raise IntelRuleError(
            f"{field} cannot be a maturity word",
            code="missing_evidence",
        )
    if len(text) < min_len or len(text) > max_len:
        raise IntelRuleError(
            f"{field} length must be {min_len}..{max_len}",
            code="invalid",
        )
    if _SECRET_RE.search(text):
        raise IntelRuleError(f"{field} looks like a secret", code="invalid")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise IntelRuleError(f"{field} has a control character", code="invalid")
    return text


def _experiment_note(value: Any) -> str:
    return _clean_text(value, field="experiment_note", min_len=12, max_len=4000)


def _rule_text(value: Any) -> str:
    return _clean_text(value, field="rule_text", min_len=12, max_len=4000)


def _optional_experiment_id(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not _EXP_RE.match(value.strip()):
        raise IntelRuleError("experiment_id is not an approve-to-rule id", code="invalid")
    return value.strip()


def _note_id(value: Any) -> str:
    text = str(value or "").strip()
    if not _NOTE_RE.match(text):
        raise IntelRuleError("note_id is not an approve-to-rule id", code="invalid")
    return text


def _stub_id(value: Any) -> str:
    text = str(value or "").strip()
    if not _STUB_RE.match(text):
        raise IntelRuleError("stub_id is not an approve-to-rule id", code="invalid")
    return text


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


def _require_existing(db_path: Path | str | None) -> tuple[sqlite3.Connection, Path]:
    resolved = _resolve_db(db_path)
    if not resolved.exists():
        raise IntelRuleError("experiment note not found", code="not_found")
    return _open_write(db_path)


def _empty_summary() -> dict[str, Any]:
    return {
        "count": 0,
        "note_count": 0,
        "approval_count": 0,
        "stub_count": 0,
        "experiments": [],
        "gaps": gaps(),
        "red_team": red_team_table(),
        "owner_prove_path": OWNER_PROVE_PATH,
        "promoted_count": 0,
        "executed_count": 0,
        "auto_promote": False,
        "live": False,
        "honesty": honesty_flags(),
    }


def _experiment_row(conn: sqlite3.Connection, experiment_id: str) -> dict[str, Any]:
    notes = conn.execute(
        """
        SELECT note_id, note_n
        FROM intel_experiment_notes
        WHERE experiment_id=?
        ORDER BY note_n
        """,
        (experiment_id,),
    ).fetchall()
    approvals = conn.execute(
        "SELECT approval_id, note_id FROM intel_note_approvals WHERE experiment_id=?",
        (experiment_id,),
    ).fetchall()
    stubs = conn.execute(
        """
        SELECT stub_id, version_n, promoted, executed
        FROM intel_rule_stubs
        WHERE experiment_id=?
        ORDER BY version_n
        """,
        (experiment_id,),
    ).fetchall()
    if stubs:
        state = STATE_STUB
    elif approvals:
        state = STATE_APPROVED
    else:
        state = STATE_NOTED
    latest = int(stubs[-1]["version_n"]) if stubs else None
    promoted = any(int(row["promoted"]) != 0 for row in stubs)
    executed = any(int(row["executed"]) != 0 for row in stubs)
    return {
        "experiment_id": experiment_id,
        "state": state,
        "note_count": len(notes),
        "approval_count": len(approvals),
        "stub_count": len(stubs),
        "latest_stub_version": latest,
        "promoted": promoted,
        "executed": executed,
        "live": False,
    }


def list_experiments(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    _require_actor(person_id, role_allowed=role_allowed)
    conn, _path = _open_read(db_path)
    if conn is None:
        return _empty_summary()
    try:
        ids = [
            str(row[0])
            for row in conn.execute(
                """
                SELECT experiment_id
                FROM intel_experiment_notes
                GROUP BY experiment_id
                ORDER BY MAX(created_at) DESC
                LIMIT 50
                """
            )
        ]
        experiments = [_experiment_row(conn, exp_id) for exp_id in ids]
        note_count = int(
            conn.execute("SELECT COUNT(*) FROM intel_experiment_notes").fetchone()[0]
        )
        approval_count = int(
            conn.execute("SELECT COUNT(*) FROM intel_note_approvals").fetchone()[0]
        )
        stub_count = int(
            conn.execute("SELECT COUNT(*) FROM intel_rule_stubs").fetchone()[0]
        )
        promoted_count = int(
            conn.execute(
                "SELECT COALESCE(SUM(promoted), 0) FROM intel_rule_stubs"
            ).fetchone()[0]
        )
        executed_count = int(
            conn.execute(
                "SELECT COALESCE(SUM(executed), 0) FROM intel_rule_stubs"
            ).fetchone()[0]
        )
    finally:
        conn.close()
    return {
        "count": len(experiments),
        "note_count": note_count,
        "approval_count": approval_count,
        "stub_count": stub_count,
        "experiments": experiments,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "owner_prove_path": OWNER_PROVE_PATH,
        "promoted_count": promoted_count,
        "executed_count": executed_count,
        "auto_promote": False,
        "live": False,
        "honesty": honesty_flags(),
    }


def read_experiment(
    experiment_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    _require_actor(person_id, role_allowed=role_allowed)
    exp_id = _optional_experiment_id(experiment_id)
    if exp_id is None:
        raise IntelRuleError("experiment_id is not an approve-to-rule id", code="invalid")
    conn, _path = _open_read(db_path)
    if conn is None:
        raise IntelRuleError("experiment not found", code="not_found")
    try:
        found = conn.execute(
            "SELECT 1 FROM intel_experiment_notes WHERE experiment_id=? LIMIT 1",
            (exp_id,),
        ).fetchone()
        if found is None:
            raise IntelRuleError("experiment not found", code="not_found")
        approved_ids = {
            str(row[0])
            for row in conn.execute(
                "SELECT note_id FROM intel_note_approvals WHERE experiment_id=?",
                (exp_id,),
            )
        }
        notes = []
        for row in conn.execute(
            """
            SELECT note_id, note_n, experiment_note, created_by, created_at, state
            FROM intel_experiment_notes
            WHERE experiment_id=?
            ORDER BY note_n
            """,
            (exp_id,),
        ):
            notes.append(
                {
                    "note_id": row["note_id"],
                    "note_n": int(row["note_n"]),
                    "experiment_note": row["experiment_note"],
                    "created_by": row["created_by"],
                    "created_at": row["created_at"],
                    "state": row["state"],
                    "approved": row["note_id"] in approved_ids,
                }
            )
        approvals = [
            {
                "approval_id": row["approval_id"],
                "note_id": row["note_id"],
                "decision": row["decision"],
                "gate": row["gate"],
                "decided_by": row["decided_by"],
                "decided_at": row["decided_at"],
            }
            for row in conn.execute(
                """
                SELECT approval_id, note_id, decision, gate, decided_by, decided_at
                FROM intel_note_approvals
                WHERE experiment_id=?
                ORDER BY decided_at
                """,
                (exp_id,),
            )
        ]
        stubs = [
            {
                "stub_id": row["stub_id"],
                "version_n": int(row["version_n"]),
                "note_id": row["note_id"],
                "approval_id": row["approval_id"],
                "rule_text": row["rule_text"],
                "state": row["state"],
                "promoted": bool(row["promoted"]),
                "executed": bool(row["executed"]),
                "created_by": row["created_by"],
                "created_at": row["created_at"],
            }
            for row in conn.execute(
                """
                SELECT stub_id, version_n, note_id, approval_id, rule_text, state,
                       promoted, executed, created_by, created_at
                FROM intel_rule_stubs
                WHERE experiment_id=?
                ORDER BY version_n
                """,
                (exp_id,),
            )
        ]
        summary = _experiment_row(conn, exp_id)
    finally:
        conn.close()
    return {
        **summary,
        "notes": notes,
        "approvals": approvals,
        "stubs": stubs,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "owner_prove_path": OWNER_PROVE_PATH,
        "auto_promote": False,
        "honesty": honesty_flags(),
    }


def record_note(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, NOTE_KEYS)
    text = _experiment_note(body.get("experiment_note"))
    experiment_id = _optional_experiment_id(body.get("experiment_id"))
    if experiment_id is not None and not _resolve_db(db_path).exists():
        raise IntelRuleError("experiment not found", code="not_found")
    note_id = f"NOTE-{uuid.uuid4()}"
    conn, _path = _open_write(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if experiment_id is None:
            experiment_id = f"EXP-{uuid.uuid4()}"
            note_n = 1
        else:
            row = conn.execute(
                "SELECT MAX(note_n) FROM intel_experiment_notes WHERE experiment_id=?",
                (experiment_id,),
            ).fetchone()
            if row is None or row[0] is None:
                raise IntelRuleError("experiment not found", code="not_found")
            note_n = int(row[0]) + 1
        conn.execute(
            """
            INSERT INTO intel_experiment_notes (
              note_id, experiment_id, note_n, experiment_note, state,
              created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                experiment_id,
                note_n,
                text,
                STATE_NOTED,
                person_id,
                now_utc_iso(),
            ),
        )
        conn.commit()
    except IntelRuleError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "note_id": note_id,
        "experiment_id": experiment_id,
        "note_n": note_n,
        "state": STATE_NOTED,
        "approved": False,
        "rule_created": False,
        "promoted": False,
        "executed": False,
        "live": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def approve_note(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, APPROVE_KEYS)
    note_id = _note_id(body.get("note_id"))
    approval_id = f"APR-{uuid.uuid4()}"
    conn, _path = _require_existing(db_path)
    try:
        before = conn.execute(
            """
            SELECT note_id, experiment_id, note_n, experiment_note, state,
                   created_by, created_at
            FROM intel_experiment_notes WHERE note_id=?
            """,
            (note_id,),
        ).fetchone()
        if before is None:
            raise IntelRuleError("experiment note not found", code="not_found")
        if not str(before["experiment_note"] or "").strip():
            raise IntelRuleError(
                "cannot approve a note with no experiment note",
                code="missing_evidence",
            )
        existing = conn.execute(
            "SELECT approval_id FROM intel_note_approvals WHERE note_id=?",
            (note_id,),
        ).fetchone()
        if existing is not None:
            raise IntelRuleError(
                "this note is already approved",
                code="already_approved",
            )
        snapshot = tuple(before)
        stub_before = int(
            conn.execute("SELECT COUNT(*) FROM intel_rule_stubs").fetchone()[0]
        )
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO intel_note_approvals (
              approval_id, note_id, experiment_id, decision, decided_by, gate, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                note_id,
                before["experiment_id"],
                DECISION_APPROVED,
                person_id,
                gate,
                now_utc_iso(),
            ),
        )
        after = conn.execute(
            """
            SELECT note_id, experiment_id, note_n, experiment_note, state,
                   created_by, created_at
            FROM intel_experiment_notes WHERE note_id=?
            """,
            (note_id,),
        ).fetchone()
        if tuple(after) != snapshot:
            raise IntelRuleError(
                "approve must not rewrite the experiment note",
                code="invalid",
            )
        stub_after = int(
            conn.execute("SELECT COUNT(*) FROM intel_rule_stubs").fetchone()[0]
        )
        if stub_after != stub_before:
            raise IntelRuleError(
                "approve must not create a rule stub",
                code="promote_refused",
            )
        conn.commit()
        experiment_id = str(before["experiment_id"])
    except IntelRuleError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise IntelRuleError(
            "this note is already approved",
            code="already_approved",
        ) from exc
    finally:
        conn.close()
    return {
        "appended": True,
        "approval_id": approval_id,
        "note_id": note_id,
        "experiment_id": experiment_id,
        "decision": DECISION_APPROVED,
        "gate": gate,
        "approved": True,
        "rule_created": False,
        "promoted": False,
        "executed": False,
        "live": False,
        "note_unchanged": True,
        "honesty": honesty_flags(),
    }


def stub_rule(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, RULE_KEYS)
    note_id = _note_id(body.get("note_id"))
    text = _rule_text(body.get("rule_text"))
    stub_id = f"RULE-{uuid.uuid4()}"
    conn, _path = _require_existing(db_path)
    try:
        note = conn.execute(
            """
            SELECT note_id, experiment_id, experiment_note, state
            FROM intel_experiment_notes WHERE note_id=?
            """,
            (note_id,),
        ).fetchone()
        if note is None:
            raise IntelRuleError("experiment note not found", code="not_found")
        note_snapshot = tuple(note)
        approval = conn.execute(
            """
            SELECT approval_id, decision
            FROM intel_note_approvals WHERE note_id=?
            """,
            (note_id,),
        ).fetchone()
        if approval is None:
            raise IntelRuleError(
                "a rule stub requires an Owner or role approval. Nothing was written.",
                code="approve_required",
            )
        if str(approval["decision"]) != DECISION_APPROVED:
            raise IntelRuleError(
                "a rule stub requires an Owner or role approval. Nothing was written.",
                code="approve_required",
            )
        experiment_id = str(note["experiment_id"])
        approval_id = str(approval["approval_id"])
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT MAX(version_n) FROM intel_rule_stubs WHERE experiment_id=?",
            (experiment_id,),
        ).fetchone()
        version_n = 1 if row is None or row[0] is None else int(row[0]) + 1
        conn.execute(
            """
            INSERT INTO intel_rule_stubs (
              stub_id, experiment_id, note_id, approval_id, version_n, rule_text,
              state, promoted, executed, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                stub_id,
                experiment_id,
                note_id,
                approval_id,
                version_n,
                text,
                STATE_STUB,
                person_id,
                now_utc_iso(),
            ),
        )
        after = conn.execute(
            """
            SELECT note_id, experiment_id, experiment_note, state
            FROM intel_experiment_notes WHERE note_id=?
            """,
            (note_id,),
        ).fetchone()
        if tuple(after) != note_snapshot:
            raise IntelRuleError(
                "a rule stub must not rewrite the experiment note",
                code="invalid",
            )
        conn.commit()
    except IntelRuleError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "appended": True,
        "stub_id": stub_id,
        "experiment_id": experiment_id,
        "note_id": note_id,
        "approval_id": approval_id,
        "version_n": version_n,
        "state": STATE_STUB,
        "promoted": False,
        "executed": False,
        "live": False,
        "production": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def _stub_row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "stub_id": row["stub_id"],
        "experiment_id": row["experiment_id"],
        "note_id": row["note_id"],
        "approval_id": row["approval_id"],
        "version_n": int(row["version_n"]),
        "rule_text": row["rule_text"],
        "state": row["state"],
        "promoted": bool(row["promoted"]),
        "executed": bool(row["executed"]),
        "live": False,
        "production": False,
        "auto_promote": False,
        "created_by": row["created_by"],
        "created_at": row["created_at"],
    }


def list_stubs(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    experiment_id: str | None = None,
    note_id: str | None = None,
    limit: int = 50,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """List versioned rule stubs. Filterable. A stub is not a live rule."""
    _require_actor(person_id, role_allowed=role_allowed)
    try:
        lim = int(limit)
    except (TypeError, ValueError) as exc:
        raise IntelRuleError("limit must be an integer", code="invalid") from exc
    if lim < 1 or lim > 200:
        raise IntelRuleError("limit must be 1..200", code="invalid")
    exp_filter: str | None = None
    if experiment_id is not None and str(experiment_id).strip():
        exp_filter = _optional_experiment_id(experiment_id)
        if exp_filter is None:
            raise IntelRuleError(
                "experiment_id is not an approve-to-rule id",
                code="invalid",
            )
    note_filter: str | None = None
    if note_id is not None and str(note_id).strip():
        note_filter = _note_id(note_id)
    conn, _path = _open_read(db_path)
    if conn is None:
        return {
            "count": 0,
            "stubs": [],
            "filters": {
                "experiment_id": exp_filter,
                "note_id": note_filter,
                "limit": lim,
            },
            "promoted_count": 0,
            "executed_count": 0,
            "auto_promote": False,
            "live": False,
            "gaps": gaps(),
            "red_team": red_team_table(),
            "honesty": honesty_flags(),
        }
    try:
        clauses: list[str] = []
        args: list[Any] = []
        if exp_filter is not None:
            clauses.append("experiment_id=?")
            args.append(exp_filter)
        if note_filter is not None:
            clauses.append("note_id=?")
            args.append(note_filter)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"""
            SELECT stub_id, experiment_id, note_id, approval_id, version_n,
                   rule_text, state, promoted, executed, created_by, created_at
            FROM intel_rule_stubs
            {where}
            ORDER BY created_at DESC, version_n DESC
            LIMIT ?
            """,
            (*args, lim),
        ).fetchall()
        stubs = [_stub_row_dict(row) for row in rows]
        promoted_count = int(
            conn.execute(
                "SELECT COALESCE(SUM(promoted), 0) FROM intel_rule_stubs"
            ).fetchone()[0]
        )
        executed_count = int(
            conn.execute(
                "SELECT COALESCE(SUM(executed), 0) FROM intel_rule_stubs"
            ).fetchone()[0]
        )
    finally:
        conn.close()
    return {
        "count": len(stubs),
        "stubs": stubs,
        "filters": {
            "experiment_id": exp_filter,
            "note_id": note_filter,
            "limit": lim,
        },
        "promoted_count": promoted_count,
        "executed_count": executed_count,
        "auto_promote": False,
        "live": False,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "honesty": honesty_flags(),
    }


def get_stub(
    stub_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read one versioned rule stub. Not promoted. Not executed."""
    _require_actor(person_id, role_allowed=role_allowed)
    sid = _stub_id(stub_id)
    conn, _path = _open_read(db_path)
    if conn is None:
        raise IntelRuleError("rule stub not found", code="not_found")
    try:
        row = conn.execute(
            """
            SELECT stub_id, experiment_id, note_id, approval_id, version_n,
                   rule_text, state, promoted, executed, created_by, created_at
            FROM intel_rule_stubs WHERE stub_id=?
            """,
            (sid,),
        ).fetchone()
        if row is None:
            raise IntelRuleError("rule stub not found", code="not_found")
        out = _stub_row_dict(row)
    finally:
        conn.close()
    return {
        **out,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "owner_prove_path": OWNER_PROVE_PATH,
        "honesty": honesty_flags(),
    }
