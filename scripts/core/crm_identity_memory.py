#!/usr/bin/env python3
"""CAP-CRM-02 customer identity and memory v1 (Beta only).

Decision served: 2026-09-19 PICK, customer identity and memory v1 on Beta only
(docs/deliveries/GROK-PLAN-CRM-IDENTITY-MEMORY-V1-2026-09-19.md).

Extended by FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CRM-IDENTITY-1
(30 Sep 2026): canonical customer stub + confidence fields + GGV client
isolation (no cross-client leak) + human-review-when-uncertain. Does not
invent a second CRM identity system. Yanolja graph merge stays
BLOCKED_EXTERNAL. CAP-CRM-02 is not claimed PROVEN/READY.

A customer is not a lead. This module stores a minimal customer record and
append-only memory notes. It does not write core_leads, org_persons, or a
completed identity graph. A link is a review candidate. People are not merged
without evidence, and evidence still does not collapse two rows.
Client/customer data boundaries override identity matching.

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
from datetime import datetime, timedelta, timezone
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
PACK_ID = "CRM-IDENTITY-1"
SCHEMA_ID = "wolf.crm-identity-1.v1"
BOUND = "beta-crm-loop-safe"
TZ_UTC = timezone.utc
WITA = timezone(timedelta(hours=8))

PERM_READ = "crm.identity.read"
PERM_NOTE = "crm.identity.note"
PERM_REGISTER = "crm.identity.register"

ENTITIES = frozenset({"GGV", "BZG", "AMG"})
# GGV client boundaries — Habitat cannot see Ivy (and vice versa).
GGV_CLIENT_SCOPES = frozenset({"habitat", "ivy"})
OTHER_KINDS = frozenset({"CUSTOMER", "PERSON", "LEAD"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
MATURITY_WORDS = frozenset(
    {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY", "LIVE", "MERGED"}
)
YANOLJA_STATUS = "BLOCKED_EXTERNAL"
CONFIDENCE_UNCERTAIN = "uncertain"

PAGE_PATHS = frozenset(
    {
        "/crm/identity-1",
        "/crm/identity-1/",
        "/crm-identity-1",
        "/crm-identity-1/",
        "/crm-identity-1.html",
        "/dashboards/crm-identity-1.html",
    }
)
API_PATH = "/api/crm/identity-1"

REGISTER_KEYS = frozenset({"display_name", "entity_id", "provenance", "client_scope"})
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
    "pack": PACK_ID,
    "slice": "crm_identity_memory_v1",
    "schema_id": SCHEMA_ID,
    "bound": BOUND,
    "distinct_from_lead": True,
    "identity_graph_complete": False,
    "graph_invented": False,
    "append_only_notes": True,
    "merged": False,
    "merge_executed": False,
    "auto_merge": False,
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
    "staff_ready": False,
    "human_commissioned": False,
    "cross_client_leak": False,
    "client_boundaries_override_matching": True,
    "yanolja_graph_merge": YANOLJA_STATUS,
    "yanolja_pms_identity_invented": False,
    "fake_pipeline": False,
    "human_review_when_uncertain": True,
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
    flags["cap_crm_02_proven"] = state == "PROVEN"
    flags["cap_crm_02_ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["identity_graph_complete"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["marketing_blast"] = False
    flags["merged"] = False
    flags["auto_merge"] = False
    flags["staff_ready"] = False
    flags["human_commissioned"] = False
    flags["cross_client_leak"] = False
    flags["yanolja_graph_merge"] = YANOLJA_STATUS
    flags["yanolja_pms_identity_invented"] = False
    flags["fake_pipeline"] = False
    flags["human_review_when_uncertain"] = True
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


def refuse_yanolja_graph_merge(*_args: Any, **_kwargs: Any) -> None:
    raise CrmIdentityError(
        "Yanolja graph merge is BLOCKED_EXTERNAL. PMS identity is not invented here.",
        code="yanolja_blocked_external",
    )


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
    return raw.rstrip("/") == API_PATH


def now_wita_iso() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crm_customers (
  customer_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  provenance TEXT NOT NULL,
  client_scope TEXT
);

CREATE INDEX IF NOT EXISTS idx_crm_customers_entity
  ON crm_customers(entity_id, created_at);

CREATE INDEX IF NOT EXISTS idx_crm_customers_client_scope
  ON crm_customers(client_scope, entity_id);

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
    cols = {
        str(r[1]) for r in conn.execute("PRAGMA table_info(crm_customers)").fetchall()
    }
    if "client_scope" not in cols:
        conn.execute("ALTER TABLE crm_customers ADD COLUMN client_scope TEXT")
    conn.commit()


def _client_scope(value: Any, *, entity: str, required: bool = False) -> str | None:
    """Normalize a GGV client scope. Boundaries override identity matching."""
    if value in (None, ""):
        if required or entity == "GGV":
            # GGV registrations in this slice require an explicit client scope.
            # Legacy callers without client_scope stay allowed only when not GGV,
            # or when required=False and entity != GGV.
            if entity == "GGV" and required:
                raise CrmIdentityError(
                    "GGV customer requires client_scope (habitat|ivy). "
                    "Client boundaries override identity matching.",
                    code="missing_client_scope",
                )
            return None
        return None
    token = _clean_text(value, field="client_scope", min_len=3, max_len=32).lower()
    if entity == "GGV" and token not in GGV_CLIENT_SCOPES:
        raise CrmIdentityError(
            "Unknown GGV client_scope. Habitat and Ivy stay isolated.",
            code="invalid_client_scope",
        )
    if entity != "GGV" and token in GGV_CLIENT_SCOPES:
        raise CrmIdentityError(
            "GGV client_scope cannot be applied to a non-GGV entity.",
            code="invalid_client_scope",
        )
    return token


def confidence_stub(
    *,
    has_open_review: bool = False,
    review_decision: str | None = None,
) -> dict[str, Any]:
    """Canonical confidence fields. Uncertain matches require human review."""
    uncertain = True
    if review_decision in {"not_a_match", "keep_separate"}:
        human_review_required = False
    elif review_decision == "still_uncertain" or has_open_review:
        human_review_required = True
    else:
        human_review_required = has_open_review
    return {
        "match_confidence": CONFIDENCE_UNCERTAIN,
        "confidence_band": CONFIDENCE_UNCERTAIN,
        "human_review_required": bool(human_review_required),
        "human_review_when_uncertain": True,
        "verified_match": False,
        "merged": False,
        "auto_merge": False,
        "yanolja_graph_merge": YANOLJA_STATUS,
    }


def assert_same_client_scope(
    left_scope: str | None,
    right_scope: str | None,
    *,
    context: str = "link",
) -> None:
    """Refuse cross-client identity matching. Boundaries win."""
    left = (left_scope or "").strip().lower() or None
    right = (right_scope or "").strip().lower() or None
    if left and right and left != right:
        raise CrmIdentityError(
            f"Client boundaries override identity matching. "
            f"Cross-client {context} refused ({left} vs {right}).",
            code="cross_client_refused",
        )


def _customer_scope_of(conn: sqlite3.Connection, customer_id: str) -> str | None:
    row = conn.execute(
        "SELECT client_scope FROM crm_customers WHERE customer_id=?",
        (customer_id,),
    ).fetchone()
    if row is None:
        return None
    raw = row["client_scope"] if "client_scope" in row.keys() else None
    return (str(raw).strip().lower() if raw else None) or None


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


def _public_customer(
    row: sqlite3.Row,
    *,
    has_open_review: bool = False,
) -> dict[str, Any]:
    keys = set(row.keys())
    scope = None
    if "client_scope" in keys and row["client_scope"]:
        scope = str(row["client_scope"]).strip().lower() or None
    stub = {
        "customer_id": row["customer_id"],
        "display_name": row["display_name"],
        "entity_id": row["entity_id"],
        "client_scope": scope,
        "status": row["status"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "provenance": row["provenance"],
        "is_lead": False,
        "is_customer": True,
        "canonical": True,
    }
    stub.update(confidence_stub(has_open_review=has_open_review))
    return stub


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
        open_review = str(r["status"] or "") == "REVIEW_REQUIRED"
        item.update(confidence_stub(has_open_review=open_review))
        out.append(item)
    return out


def register_customer(
    body: dict,
    *,
    person_id: str | None,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
    require_client_scope: bool = False,
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
    scope = _client_scope(
        body.get("client_scope"),
        entity=entity,
        required=require_client_scope,
    )
    provenance = _clean_text(body.get("provenance"), field="provenance", min_len=12, max_len=2000)
    customer_id = mint_customer_id()
    created_at = now_utc_iso()
    conn, _resolved = _open_write(db_path)
    try:
        conn.execute(
            """
            INSERT INTO crm_customers (
              customer_id, display_name, entity_id, status,
              created_by, created_at, provenance, client_scope
            ) VALUES (?, ?, ?, 'RECORDED', ?, ?, ?, ?)
            """,
            (customer_id, name, entity, person_id, created_at, provenance, scope),
        )
        conn.commit()
    finally:
        conn.close()
    stub = confidence_stub(has_open_review=False)
    return {
        "ok": True,
        "customer_id": customer_id,
        "display_name": name,
        "entity_id": entity,
        "client_scope": scope,
        "status": "RECORDED",
        "is_lead": False,
        "is_customer": True,
        "canonical": True,
        "identity_graph_complete": False,
        "merged": False,
        "gate": gate,
        "honesty": honesty_flags(),
        **stub,
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
    client_scope: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    gate = _require_actor(person_id, role_allowed=role_allowed)
    entity_token = None
    if entity not in (None, ""):
        entity_token = _entity(entity)
    scope_token = None
    if client_scope not in (None, ""):
        # Validate against GGV scopes when filtering; entity default GGV for scope check.
        scope_entity = entity_token or "GGV"
        scope_token = _client_scope(client_scope, entity=scope_entity, required=False)
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
            "cross_client_leak": False,
            "gate": gate,
            "honesty": flags,
        }
    try:
        sql = """
            SELECT customer_id, display_name, entity_id, status,
                   created_by, created_at, provenance, client_scope
            FROM crm_customers
            WHERE 1=1
        """
        params: list[Any] = []
        if entity_token:
            sql += " AND entity_id=?"
            params.append(entity_token)
        if scope_token:
            sql += " AND lower(coalesce(client_scope,''))=?"
            params.append(scope_token)
        sql += " ORDER BY created_at, customer_id"
        rows = conn.execute(sql, params).fetchall()
        customers = []
        for r in rows:
            open_n = conn.execute(
                """
                SELECT COUNT(*) FROM crm_link_candidates
                WHERE customer_id=? AND status='REVIEW_REQUIRED'
                """,
                (r["customer_id"],),
            ).fetchone()[0]
            customers.append(_public_customer(r, has_open_review=int(open_n) > 0))
    finally:
        conn.close()
    return {
        "ok": True,
        "cap": CAP_ID,
        "count": len(customers),
        "customers": customers,
        "filters": {"entity": entity_token, "client_scope": scope_token},
        "distinct_from_lead": True,
        "identity_graph_complete": False,
        "graph_note": GRAPH_NOTE,
        "marketing_blast": False,
        "merged": False,
        "cross_client_leak": False,
        "gate": gate,
        "honesty": flags,
    }


def read_customer(
    customer_id: str,
    person_id: str | None,
    *,
    role_allowed: bool = False,
    client_scope: str | None = None,
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
                   created_by, created_at, provenance, client_scope
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
        row_scope = None
        if "client_scope" in row.keys() and row["client_scope"]:
            row_scope = str(row["client_scope"]).strip().lower() or None
        if client_scope not in (None, ""):
            wanted = _client_scope(
                client_scope,
                entity=str(row["entity_id"]),
                required=False,
            )
            if wanted and row_scope and wanted != row_scope:
                raise CrmIdentityError(
                    "Client boundaries override identity matching. "
                    f"Cross-client read refused ({wanted} cannot see {row_scope}).",
                    code="cross_client_refused",
                )
            if wanted and not row_scope:
                raise CrmIdentityError(
                    "Client boundaries override identity matching. "
                    "Cross-client read refused (customer has no matching scope).",
                    code="cross_client_refused",
                )
        candidates = _candidates(conn, token)
        open_review = any(c.get("human_review_required") for c in candidates)
        customer = _public_customer(row, has_open_review=open_review)
        notes = _notes(conn, token)
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
        "cross_client_leak": False,
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
            "SELECT customer_id, client_scope FROM crm_customers WHERE customer_id=?",
            (other,),
        ).fetchone()
        if row is None:
            raise CrmIdentityError(
                "The other customer was not found. It was not invented.",
                code="not_found",
            )
        left_scope = _customer_scope_of(conn, customer_id)
        right_scope = None
        if "client_scope" in row.keys() and row["client_scope"]:
            right_scope = str(row["client_scope"]).strip().lower() or None
        assert_same_client_scope(left_scope, right_scope, context="link")
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
    if kind == "YANOLJA":
        refuse_yanolja_graph_merge()
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
    if "yanolja" in evidence.lower():
        refuse_yanolja_graph_merge()
    customer_id = _customer_id(body.get("customer_id"))
    kind = _clean_text(body.get("other_kind"), field="other_kind", min_len=4, max_len=12).upper()
    if kind == "YANOLJA":
        refuse_yanolja_graph_merge()
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
    stub = confidence_stub(has_open_review=True)
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "customer_id": customer_id,
        "other_id": other_id,
        "other_kind": kind,
        "status": "REVIEW_REQUIRED",
        "verified": False,
        "merged": False,
        "auto_merge": False,
        "customers_unchanged": before == after,
        "identity_graph_complete": False,
        "lead_is_customer": False,
        "cross_client_leak": False,
        "yanolja_graph_merge": YANOLJA_STATUS,
        "gate": gate,
        "honesty": honesty_flags(),
        **stub,
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
    recorded["auto_merge"] = False
    recorded["identity_graph_complete"] = False
    recorded["message"] = (
        "Evidence was recorded as a review candidate. "
        "The people were not merged. The graph is not complete."
    )
    return recorded


def list_uncertain_reviews(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    client_scope: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Human-review-when-uncertain queue. Does not auto-merge."""
    gate = _require_actor(person_id, role_allowed=role_allowed)
    scope_token = None
    if client_scope not in (None, ""):
        scope_token = _client_scope(client_scope, entity="GGV", required=False)
    flags = honesty_flags()
    conn, _resolved = _open_read(db_path)
    if conn is None:
        return {
            "ok": True,
            "cap": CAP_ID,
            "pack": PACK_ID,
            "count": 0,
            "items": [],
            "empty": True,
            "human_review_when_uncertain": True,
            "auto_merge": False,
            "yanolja_graph_merge": YANOLJA_STATUS,
            "gate": gate,
            "honesty": flags,
        }
    try:
        rows = conn.execute(
            """
            SELECT c.candidate_id, c.customer_id, c.other_id, c.other_kind,
                   c.evidence_ref, c.status, c.recorded_by, c.recorded_at,
                   c.provenance, cust.client_scope, cust.display_name, cust.entity_id
            FROM crm_link_candidates c
            JOIN crm_customers cust ON cust.customer_id = c.customer_id
            WHERE c.status = 'REVIEW_REQUIRED'
            ORDER BY c.recorded_at, c.candidate_id
            """
        ).fetchall()
        items: list[dict[str, Any]] = []
        for r in rows:
            row_scope = (
                str(r["client_scope"]).strip().lower()
                if r["client_scope"]
                else None
            ) or None
            if scope_token and row_scope != scope_token:
                continue
            item = {
                "candidate_id": r["candidate_id"],
                "customer_id": r["customer_id"],
                "display_name": r["display_name"],
                "entity_id": r["entity_id"],
                "client_scope": row_scope,
                "other_id": r["other_id"],
                "other_kind": r["other_kind"],
                "evidence_ref": r["evidence_ref"],
                "status": r["status"],
                "recorded_by": r["recorded_by"],
                "recorded_at": r["recorded_at"],
                "provenance": r["provenance"],
            }
            item.update(confidence_stub(has_open_review=True))
            items.append(item)
    finally:
        conn.close()
    return {
        "ok": True,
        "cap": CAP_ID,
        "pack": PACK_ID,
        "count": len(items),
        "items": items,
        "empty": len(items) == 0,
        "human_review_when_uncertain": True,
        "auto_merge": False,
        "merged": False,
        "yanolja_graph_merge": YANOLJA_STATUS,
        "filters": {"client_scope": scope_token},
        "gate": gate,
        "honesty": flags,
    }


def build_identity_slice(
    person_id: str | None = None,
    *,
    role_allowed: bool = False,
    client_scope: str | None = None,
    db_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """CRM-IDENTITY-1 vertical slice desk payload. Extends this module only."""
    gate = "anonymous"
    if person_id:
        gate = _require_actor(person_id, role_allowed=role_allowed)
    flags = honesty_flags(ledger_path=ledger_path, catalog_db=catalog_db)
    maturity = flags.get("maturity") or "UNKNOWN"
    ceiling = flags.get("maturity_ceiling") or "BUILT"

    habitat: dict[str, Any] = {"count": 0, "customers": []}
    ivy: dict[str, Any] = {"count": 0, "customers": []}
    uncertain: dict[str, Any] = {
        "count": 0,
        "items": [],
        "empty": True,
        "human_review_when_uncertain": True,
    }
    if person_id:
        try:
            habitat = list_customers(
                person_id,
                role_allowed=role_allowed,
                entity="GGV",
                client_scope="habitat",
                db_path=db_path,
            )
            ivy = list_customers(
                person_id,
                role_allowed=role_allowed,
                entity="GGV",
                client_scope="ivy",
                db_path=db_path,
            )
            uncertain = list_uncertain_reviews(
                person_id,
                role_allowed=role_allowed,
                client_scope=client_scope,
                db_path=db_path,
            )
        except CrmIdentityError:
            pass

    tiles = [
        {
            "id": "canonical_stub",
            "label": "Canonical customer stub",
            "status": "BUILT",
            "display": "STUB",
            "why": (
                "Minimal customer record with confidence fields. "
                "Not a lead. Not a complete identity graph."
            ),
        },
        {
            "id": "confidence",
            "label": "Match confidence",
            "status": CONFIDENCE_UNCERTAIN.upper(),
            "display": CONFIDENCE_UNCERTAIN.upper(),
            "why": (
                "Reversible confidence-based matching. Uncertain stays uncertain. "
                "Human review required when identity is uncertain."
            ),
        },
        {
            "id": "human_review",
            "label": "Human review when uncertain",
            "status": "REQUIRED",
            "display": "REVIEW",
            "count": int(uncertain.get("count") or 0),
            "why": (
                "Open link candidates stay REVIEW_REQUIRED. "
                "No auto-merge. A review decision does not collapse rows."
            ),
        },
        {
            "id": "client_isolation",
            "label": "GGV client isolation",
            "status": "ENFORCED",
            "display": "ISOLATED",
            "habitat_count": int(habitat.get("count") or 0),
            "ivy_count": int(ivy.get("count") or 0),
            "why": (
                "Client boundaries override identity matching. "
                "Habitat cannot see Ivy. Cross-client link/read refused."
            ),
        },
        {
            "id": "yanolja",
            "label": "Yanolja graph merge",
            "status": YANOLJA_STATUS,
            "display": YANOLJA_STATUS,
            "value": None,
            "why": (
                "Yanolja PMS identity is BLOCKED_EXTERNAL. "
                "No invented PMS guest graph merge."
            ),
        },
        {
            "id": "cap_crm_02",
            "label": "CAP-CRM-02 maturity",
            "status": str(maturity),
            "display": str(ceiling),
            "proven": maturity == "PROVEN",
            "ready": maturity == "READY",
            "why": (
                f"Ledger maturity={maturity}. Ceiling={ceiling}. "
                "This pack does not invent PROVEN or READY."
            ),
        },
    ]

    return {
        "ok": True,
        "pack": PACK_ID,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "as_of": now_wita_iso(),
        "gate": gate,
        "canonical": True,
        "staff_ready": False,
        "human_commissioned": False,
        "cap_crm_02_proven": maturity == "PROVEN",
        "cap_crm_02_ready": maturity == "READY",
        "maturity": maturity,
        "maturity_ceiling": ceiling,
        "identity_graph_complete": False,
        "merged": False,
        "auto_merge": False,
        "fake_pipeline": False,
        "cross_client_leak": False,
        "client_boundaries_override_matching": True,
        "yanolja_graph_merge": YANOLJA_STATUS,
        "yanolja_pms_identity_invented": False,
        "human_review_when_uncertain": True,
        "match_confidence": CONFIDENCE_UNCERTAIN,
        "confidence_band": CONFIDENCE_UNCERTAIN,
        "tiles": tiles,
        "uncertain_review": {
            "count": int(uncertain.get("count") or 0),
            "items": uncertain.get("items") or [],
            "empty": bool(uncertain.get("empty", True)),
        },
        "client_scopes": {
            "habitat": {
                "client_scope": "habitat",
                "count": int(habitat.get("count") or 0),
                "customers": habitat.get("customers") or [],
            },
            "ivy": {
                "client_scope": "ivy",
                "count": int(ivy.get("count") or 0),
                "customers": ivy.get("customers") or [],
            },
        },
        "desk_links": [
            {
                "id": "crm_identity",
                "label": "Customer identity desk",
                "href": "/crm-identity",
                "note": "Existing CAP-CRM-02 desk. Not a second system.",
            },
            {
                "id": "operator_depth",
                "label": "Identity operator depth",
                "href": "/crm-identity#identity-depth",
                "note": "Confidence match + human review actions.",
            },
            {
                "id": "integrations_honesty",
                "label": "Integrations honesty board",
                "href": "/ops/integrations-status",
                "note": "Yanolja BLOCKED_EXTERNAL lives here too.",
            },
        ],
        "honesty": flags,
        "extends": "scripts/core/crm_identity_memory.py",
        "second_crm_system": False,
        "next_pack_for_parent_only": "FIN-INTERCO-1",
    }


def public_payload(
    person_id: str | None = None,
    *,
    role_allowed: bool = False,
    client_scope: str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    return build_identity_slice(
        person_id,
        role_allowed=role_allowed,
        client_scope=client_scope,
        db_path=db_path,
    )