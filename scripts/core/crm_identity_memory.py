#!/usr/bin/env python3
"""CAP-CRM-02 customer identity and memory v1 (Beta only).

Decision served: 2026-09-19 PICK, customer identity and memory v1 on Beta only
(docs/deliveries/GROK-PLAN-CRM-IDENTITY-MEMORY-V1-2026-09-19.md).

A customer is not a lead. This module stores a minimal customer record and
append-only memory notes. It does not write core_leads, org_persons, or a
completed identity graph. A link is a review candidate. People are not merged
without evidence, and evidence still does not collapse two rows.

Owner (PERS-MATT) can read. Staff can read only when the caller already has
crm.identity.read. This module does not grant that permission.

Honesty is bound to CR-820682ce791563fa. The ledger is read, not written.
Maturity ceiling is BUILT unless the ledger row is already PROVEN or READY.
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
DEFAULT_DB = BETA_ROOT / "catalog" / "crm_identity.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-820682ce791563fa"
CAP_ID = "CAP-CRM-02"
TZ_UTC = timezone.utc

PERM_READ = "crm.identity.read"
PERM_NOTE = "crm.identity.note"
PERM_REGISTER = "crm.identity.register"

ENTITIES = frozenset({"GGV", "BZG", "AMG"})
OTHER_KINDS = frozenset({"CUSTOMER", "PERSON", "LEAD"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY_WORDS = frozenset(
    {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY", "LIVE", "MERGED"}
)

REGISTER_KEYS = frozenset({"display_name", "entity_id", "provenance"})
NOTE_KEYS = frozenset({"customer_id", "body", "provenance", "corrects_note_id"})
LINK_KEYS = frozenset(
    {"customer_id", "other_id", "other_kind", "evidence_ref", "provenance"}
)
MERGE_KEYS = frozenset(
    {
        "left_customer_id",
        "right_customer_id",
        "right_ref",
        "right_kind",
        "evidence_ref",
        "provenance",
    }
)
BANNED_KEYS = frozenset(
    {
        "lead_id",
        "person_id",
        "email",
        "graph_complete",
        "identity_graph_complete",
        "merged",
        "proven",
        "ready",
        "maturity",
        "blast",
        "marketing",
        "campaign",
        "klaviyo",
        "score",
    }
)
BLAST_KEYS = frozenset(
    {"blast", "marketing", "campaign", "klaviyo", "mailchimp", "send_email", "broadcast"}
)

_PERSON_RE = re.compile(r"^PERS-[A-Z0-9][A-Z0-9-]{0,40}$")
_CUST_RE = re.compile(
    r"^CUST-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_NOTE_RE = re.compile(
    r"^NOTE-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_LEAD_RE = re.compile(r"^LEAD-[A-Za-z0-9-]{8,80}$")
_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)

GRAPH_NOTE = (
    "This is not a complete identity graph. A customer record is not a lead. "
    "A link candidate is not a merge and is not a verified match."
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "crm_identity_memory_v1",
    "distinct_from_lead": True,
    "identity_graph_complete": False,
    "graph_invented": False,
    "append_only_notes": True,
    "merged": False,
    "merge_executed": False,
    "marketing_blast": False,
    "lead_rows_written": False,
    "org_persons_written": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_or_staff_read": True,
    "invented_permission_grant": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
}


class CrmIdentityError(ValueError):
    """Fail closed. Does not invent a customer, a merge, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"register", "create"}:
        return PERM_REGISTER
    if act in {"note", "link"}:
        return PERM_NOTE
    if act == "merge":
        return PERM_REGISTER
    return PERM_READ


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_customer_id() -> str:
    return f"CUST-{uuid.uuid4()}"


def mint_note_id() -> str:
    return f"NOTE-{uuid.uuid4()}"


def mint_link_id() -> str:
    return f"LINK-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise CrmIdentityError(
            "customer identity refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise CrmIdentityError(
            "customer identity refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise CrmIdentityError(
            "customer identity refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise CrmIdentityError(
            "customer identity refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_CRM_IDENTITY_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    if resolved.name == "content_library.sqlite":
        raise CrmIdentityError(
            "customer identity does not write the lead catalog",
            code="not_a_lead",
        )
    return resolved


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_CRM_IDENTITY") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise CrmIdentityError(
            "test mode refuses writes to the live customer identity DB; "
            "point db_path at a temp file",
            code="live_guard",
        )


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-CRM-02. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    return state or "UNKNOWN"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-820682ce791563fa. Does not upsert, resolve, or harvest."""
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
    _assert_beta_path(path.resolve())
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
    flags["identity_graph_complete"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["marketing_blast"] = False
    flags["merged"] = False
    return flags


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    raise CrmIdentityError(
        "CR resolve is refused. This slice does not close CR-820682ce791563fa.",
        code="cr_resolve_refused",
    )


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    raise CrmIdentityError(
        "PROVEN is not invented by this slice.",
        code="invented_proven",
    )


def refuse_marketing(_body: dict | None = None) -> None:
    raise CrmIdentityError(
        "Marketing blasts are refused. This slice does not send email or campaigns.",
        code="marketing_refused",
    )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crm_customers (
  customer_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  provenance TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crm_customers_entity
  ON crm_customers(entity_id, created_at);

CREATE TABLE IF NOT EXISTS crm_memory_notes (
  note_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  body TEXT NOT NULL,
  recorded_by TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  corrects_note_id TEXT NULL,
  provenance TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crm_memory_notes_customer
  ON crm_memory_notes(customer_id, recorded_at);

CREATE TABLE IF NOT EXISTS crm_link_candidates (
  candidate_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  other_id TEXT NOT NULL,
  other_kind TEXT NOT NULL,
  evidence_ref TEXT NOT NULL,
  status TEXT NOT NULL,
  recorded_by TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  provenance TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crm_link_candidates_customer
  ON crm_link_candidates(customer_id, recorded_at);

CREATE TRIGGER IF NOT EXISTS trg_crm_customers_no_update
BEFORE UPDATE ON crm_customers
BEGIN
  SELECT RAISE(ABORT, 'crm_customers is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_crm_customers_no_delete
BEFORE DELETE ON crm_customers
BEGIN
  SELECT RAISE(ABORT, 'crm_customers is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_crm_memory_notes_no_update
BEFORE UPDATE ON crm_memory_notes
BEGIN
  SELECT RAISE(ABORT, 'crm_memory_notes is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_crm_memory_notes_no_delete
BEFORE DELETE ON crm_memory_notes
BEGIN
  SELECT RAISE(ABORT, 'crm_memory_notes is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_crm_link_candidates_no_update
BEFORE UPDATE ON crm_link_candidates
BEGIN
  SELECT RAISE(ABORT, 'crm_link_candidates is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_crm_link_candidates_no_delete
BEFORE DELETE ON crm_link_candidates
BEGIN
  SELECT RAISE(ABORT, 'crm_link_candidates is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _require_actor(person_id: str | None, *, role_allowed: bool) -> str:
    pid = (person_id or "").strip()
    if not pid:
        raise CrmIdentityError("anonymous callers are refused", code="denied")
    if pid == OWNER_PERSON:
        return "owner"
    if role_allowed is True and _PERSON_RE.match(pid):
        return "staff"
    raise CrmIdentityError(
        "customer identity is Owner (PERS-MATT) or an authorised staff role only",
        code="denied",
    )


def _reject_keys(body: dict, allowed: frozenset[str]) -> None:
    if not isinstance(body, dict):
        raise CrmIdentityError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    if low & BLAST_KEYS or any(str(k).lower() in BLAST_KEYS for k in body):
        refuse_marketing(body)
    banned = sorted(set(body) & BANNED_KEYS)
    if banned:
        raise CrmIdentityError(
            "refused field " + ",".join(banned) + "; a client cannot mark a merge, a lead, or PROVEN",
            code="refused_field",
        )
    extra = sorted(set(body) - allowed)
    if extra:
        raise CrmIdentityError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _clean_text(value: Any, *, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise CrmIdentityError(f"{field} must be a string", code="invalid")
    text = value.strip()
    if len(text) < min_len or len(text) > max_len:
        raise CrmIdentityError(
            f"{field} length must be {min_len}..{max_len}",
            code="invalid",
        )
    if text.upper() in MATURITY_WORDS:
        raise CrmIdentityError(
            f"{field} cannot be a maturity word",
            code="invented_proven",
        )
    if _SECRET_RE.search(text):
        raise CrmIdentityError(f"{field} looks like a secret", code="invalid")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise CrmIdentityError(f"{field} has a control character", code="invalid")
    return text


def _entity(value: Any) -> str:
    token = _clean_text(value, field="entity_id", min_len=3, max_len=8).upper()
    if token not in ENTITIES:
        raise CrmIdentityError(
            "Unknown entity. This slice does not invent a company.",
            code="invalid_entity",
        )
    return token


def _customer_id(value: Any) -> str:
    token = (value if isinstance(value, str) else "").strip()
    if token.upper().startswith("LEAD-"):
        raise CrmIdentityError(
            "A lead is not a customer identity.",
            code="not_a_customer",
        )
    if not _CUST_RE.match(token):
        raise CrmIdentityError("customer_id is not a customer record", code="not_found")
    return token


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
    if not resolved.is_file():
        return None, resolved
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn, resolved


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def _public_customer(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "customer_id": row["customer_id"],
        "display_name": row["display_name"],
        "entity_id": row["entity_id"],
        "status": row["status"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "provenance": row["provenance"],
        "is_lead": False,
        "is_customer": True,
    }


def _notes(conn: sqlite3.Connection, customer_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT note_id, customer_id, body, recorded_by, recorded_at,
               corrects_note_id, provenance
        FROM crm_memory_notes
        WHERE customer_id=?
        ORDER BY rowid
        """,
        (customer_id,),
    ).fetchall()
    corrected = {r["corrects_note_id"] for r in rows if r["corrects_note_id"]}
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["superseded"] = r["note_id"] in corrected
        out.append(item)
    return out


def _candidates(conn: sqlite3.Connection, customer_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT candidate_id, customer_id, other_id, other_kind, evidence_ref,
               status, recorded_by, recorded_at, provenance
        FROM crm_link_candidates
        WHERE customer_id=?
        ORDER BY recorded_at, candidate_id
        """,
        (customer_id,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["verified"] = False
        item["merged"] = False
        item["lead_is_customer"] = False
        out.append(item)
    return out


def register_customer(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Insert one customer. Does not insert a lead or a person."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, REGISTER_KEYS)
    name = _clean_text(body.get("display_name"), field="display_name", min_len=2, max_len=120)
    if name.upper().startswith("LEAD-"):
        raise CrmIdentityError(
            "A lead id is not a customer name.",
            code="not_a_customer",
        )
    entity = _entity(body.get("entity_id"))
    provenance = _clean_text(body.get("provenance"), field="provenance", min_len=12, max_len=2000)
    customer_id = mint_customer_id()
    created_at = now_utc_iso()
    conn, _resolved = _open_write(db_path)
    try:
        conn.execute(
            """
            INSERT INTO crm_customers (
              customer_id, display_name, entity_id, status,
              created_by, created_at, provenance
            ) VALUES (?, ?, ?, 'RECORDED', ?, ?, ?)
            """,
            (customer_id, name, entity, person_id, created_at, provenance),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "customer_id": customer_id,
        "display_name": name,
        "entity_id": entity,
        "status": "RECORDED",
        "is_lead": False,
        "is_customer": True,
        "identity_graph_complete": False,
        "merged": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def append_note(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Insert one memory note. History is not rewritten."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    _reject_keys(body, NOTE_KEYS)
    customer_id = _customer_id(body.get("customer_id"))
    text = _clean_text(body.get("body"), field="body", min_len=2, max_len=4000)
    provenance = _clean_text(body.get("provenance"), field="provenance", min_len=12, max_len=2000)
    corrects = body.get("corrects_note_id")
    corrects_id = None
    if corrects not in (None, ""):
        if not isinstance(corrects, str) or not _NOTE_RE.match(corrects.strip()):
            raise CrmIdentityError("corrects_note_id is not a note", code="not_found")
        corrects_id = corrects.strip()
    note_id = mint_note_id()
    recorded_at = now_utc_iso()
    conn, _resolved = _open_write(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM crm_customers WHERE customer_id=?",
            (customer_id,),
        ).fetchone()
        if exists is None:
            raise CrmIdentityError(
                "Customer was not found. It was not invented from a lead.",
                code="not_found",
            )
        if corrects_id:
            prior = conn.execute(
                """
                SELECT customer_id FROM crm_memory_notes WHERE note_id=?
                """,
                (corrects_id,),
            ).fetchone()
            if prior is None or prior["customer_id"] != customer_id:
                raise CrmIdentityError(
                    "A correction must point at an existing note for this customer.",
                    code="not_found",
                )
        conn.execute(
            """
            INSERT INTO crm_memory_notes (
              note_id, customer_id, body, recorded_by, recorded_at,
              corrects_note_id, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (note_id, customer_id, text, person_id, recorded_at, corrects_id, provenance),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "note_id": note_id,
        "customer_id": customer_id,
        "corrects_note_id": corrects_id,
        "rewritten": False,
        "identity_graph_complete": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def list_customers(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    entity: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    entity_token = None
    if entity not in (None, ""):
        entity_token = _entity(entity)
    if gate == "staff" and entity_token is None:
        raise CrmIdentityError(
            "Staff read requires an entity. This slice does not dump every brand.",
            code="missing_scope",
        )
    flags = honesty_flags()
    conn, _resolved = _open_read(db_path)
    if conn is None:
        return {
            "ok": True,
            "cap": CAP_ID,
            "count": 0,
            "customers": [],
            "distinct_from_lead": True,
            "identity_graph_complete": False,
            "graph_note": GRAPH_NOTE,
            "marketing_blast": False,
            "merged": False,
            "gate": gate,
            "honesty": flags,
        }
    try:
        if entity_token:
            rows = conn.execute(
                """
                SELECT customer_id, display_name, entity_id, status,
                       created_by, created_at, provenance
                FROM crm_customers
                WHERE entity_id=?
                ORDER BY created_at, customer_id
                """,
                (entity_token,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT customer_id, display_name, entity_id, status,
                       created_by, created_at, provenance
                FROM crm_customers
                ORDER BY created_at, customer_id
                """
            ).fetchall()
        customers = [_public_customer(r) for r in rows]
    finally:
        conn.close()
    return {
        "ok": True,
        "cap": CAP_ID,
        "count": len(customers),
        "customers": customers,
        "filters": {"entity": entity_token},
        "distinct_from_lead": True,
        "identity_graph_complete": False,
        "graph_note": GRAPH_NOTE,
        "marketing_blast": False,
        "merged": False,
        "gate": gate,
        "honesty": flags,
    }


def read_customer(
    customer_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    token = _customer_id(customer_id)
    conn, _resolved = _open_read(db_path)
    if conn is None:
        raise CrmIdentityError(
            "Customer was not found. It was not invented.",
            code="not_found",
        )
    try:
        row = conn.execute(
            """
            SELECT customer_id, display_name, entity_id, status,
                   created_by, created_at, provenance
            FROM crm_customers WHERE customer_id=?
            """,
            (token,),
        ).fetchone()
        if row is None:
            raise CrmIdentityError(
                "Customer was not found. It was not invented from a lead.",
                code="not_found",
            )
        if gate == "staff":
            # Staff already passed the permission check. The row's entity is
            # the scope. Do not widen the read to other entities here.
            pass
        customer = _public_customer(row)
        notes = _notes(conn, token)
        candidates = _candidates(conn, token)
    finally:
        conn.close()
    return {
        "ok": True,
        "cap": CAP_ID,
        "customer": customer,
        "notes": notes,
        "link_candidates": candidates,
        "distinct_from_lead": True,
        "identity_graph_complete": False,
        "graph_note": GRAPH_NOTE,
        "lead_is_customer": False,
        "merged": False,
        "marketing_blast": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def _evidence(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise CrmIdentityError(
            "People are not merged or linked without evidence.",
            code="merge_without_evidence",
        )
    return _clean_text(value, field="evidence_ref", min_len=12, max_len=2000)


def _other_ref(kind: str, other_id: str, conn: sqlite3.Connection, customer_id: str) -> str:
    if kind == "CUSTOMER":
        other = _customer_id(other_id)
        if other == customer_id:
            raise CrmIdentityError("A customer is not linked to itself.", code="invalid")
        row = conn.execute(
            "SELECT 1 FROM crm_customers WHERE customer_id=?",
            (other,),
        ).fetchone()
        if row is None:
            raise CrmIdentityError(
                "The other customer was not found. It was not invented.",
                code="not_found",
            )
        return other
    if kind == "PERSON":
        token = (other_id or "").strip()
        if not _PERSON_RE.match(token):
            raise CrmIdentityError(
                "Person ref is not a person id. org_persons was not written.",
                code="invalid",
            )
        return token
    if kind == "LEAD":
        token = (other_id or "").strip()
        if not _LEAD_RE.match(token):
            raise CrmIdentityError(
                "Lead ref is not a lead id. core_leads was not written.",
                code="not_a_customer",
            )
        return token
    raise CrmIdentityError(
        "Unknown link kind. This slice does not invent a match type.",
        code="invalid",
    )


def propose_link(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record a review candidate. Does not merge and does not verify."""
    if role_allowed is True and (person_id or "").strip() != OWNER_PERSON:
        raise CrmIdentityError(
            "Link candidates are Owner review. Staff cannot file a match.",
            code="denied",
        )
    gate = _require_actor(person_id, role_allowed=False)
    _reject_keys(body, LINK_KEYS)
    evidence = _evidence(body.get("evidence_ref"))
    customer_id = _customer_id(body.get("customer_id"))
    kind = _clean_text(body.get("other_kind"), field="other_kind", min_len=4, max_len=12).upper()
    if kind not in OTHER_KINDS:
        raise CrmIdentityError(
            "Unknown link kind. This slice does not invent a match type.",
            code="invalid",
        )
    provenance = _clean_text(body.get("provenance"), field="provenance", min_len=12, max_len=2000)
    other_raw = body.get("other_id")
    if not isinstance(other_raw, str):
        raise CrmIdentityError("other_id must be a string", code="invalid")
    candidate_id = mint_link_id()
    recorded_at = now_utc_iso()
    conn, _resolved = _open_write(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM crm_customers WHERE customer_id=?",
            (customer_id,),
        ).fetchone()
        if exists is None:
            raise CrmIdentityError("Customer was not found.", code="not_found")
        other_id = _other_ref(kind, other_raw, conn, customer_id)
        before = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
        conn.execute(
            """
            INSERT INTO crm_link_candidates (
              candidate_id, customer_id, other_id, other_kind, evidence_ref,
              status, recorded_by, recorded_at, provenance
            ) VALUES (?, ?, ?, ?, ?, 'REVIEW_REQUIRED', ?, ?, ?)
            """,
            (
                candidate_id,
                customer_id,
                other_id,
                kind,
                evidence,
                person_id,
                recorded_at,
                provenance,
            ),
        )
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
    finally:
        conn.close()
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "customer_id": customer_id,
        "other_id": other_id,
        "other_kind": kind,
        "status": "REVIEW_REQUIRED",
        "verified": False,
        "merged": False,
        "customers_unchanged": before == after,
        "identity_graph_complete": False,
        "lead_is_customer": False,
        "gate": gate,
        "honesty": honesty_flags(),
    }


def merge_people(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Refuse a silent merge. Evidence records a candidate. Rows stay separate."""
    if not isinstance(body, dict):
        raise CrmIdentityError("payload must be an object", code="invalid")
    if {str(k).lower() for k in body} & BLAST_KEYS:
        refuse_marketing(body)
    evidence_raw = body.get("evidence_ref")
    if evidence_raw is None or (isinstance(evidence_raw, str) and not evidence_raw.strip()):
        raise CrmIdentityError(
            "People are not merged without evidence.",
            code="merge_without_evidence",
        )
    if (person_id or "").strip() != OWNER_PERSON:
        raise CrmIdentityError(
            "Merge review is Owner only. Rows were not collapsed.",
            code="denied",
        )
    _reject_keys(body, MERGE_KEYS)
    kind = body.get("right_kind")
    if not kind and body.get("right_customer_id"):
        kind = "CUSTOMER"
    right = body.get("right_customer_id") or body.get("right_ref")
    link_body = {
        "customer_id": body.get("left_customer_id"),
        "other_id": right,
        "other_kind": kind,
        "evidence_ref": evidence_raw,
        "provenance": body.get("provenance"),
    }
    recorded = propose_link(
        link_body,
        person_id=person_id,
        role_allowed=False,
        db_path=db_path,
    )
    recorded["merged"] = False
    recorded["merge_executed"] = False
    recorded["identity_graph_complete"] = False
    recorded["message"] = (
        "Evidence was recorded as a review candidate. "
        "The people were not merged. The graph is not complete."
    )
    return recorded
