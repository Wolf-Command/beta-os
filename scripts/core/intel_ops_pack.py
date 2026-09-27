#!/usr/bin/env python3
"""Owner Intel Ops pack v2 — Beta :8788 only.

Decision served: bound beta-intel-safe (Intelligence / Decision Memory
productize) under 2026-09-19 owner release keep_building_without_matt, composing
the 2026-09-20 CAP-INTEL-05 PICK and already-BUILT/PROVEN intel primitives
(docs/deliveries/GROK-PLAN-SPRINT-TRACK-D-INTEL-OPS-PACK-V2-2026-09-22.md).

One Owner desk. Today → ask → provenance → Decision Memory recall →
approve-to-rule experiment-note handoff. No auto-promote. No rule execution.
No money. Does not invent PROVEN/READY. Does not resolve CRs. Does not raise
CAP-INTEL-01/05. AU-INTEL-02-WOLF stays NOT STARTED.

Bound beta-intel-safe. Owner, or an existing intel.rule / decision.memory
holder. No finance, bank, payment, Zayen, HR, payroll, tax, or trading.

Intel Ops × Needs-You connective projects Intel-scoped commissioning,
intel connective, and learning-policy rows onto this desk. Owner sees the
full Intel-scoped set. A non-Owner intel seat sees in-scope rows only.
EMPTY when none. next_action prefers an in-scope row over the generic pack
href. Detail and acknowledge reuse the Needs-You operator state, or the
existing connective / learning-policy handoff. No second mutate store.
No invented staff_ready, Haikal done, Devi done, PROVEN, or READY.
No auto-promote. No rule execute.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import decision_memory as dm
from core import intel_approve_to_rule as rules
from core import intel_orchestration as intel
from core import rbac as _rbac

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "intel_ops_pack.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
DM_DB = BETA_ROOT / "catalog" / "decision_memory.sqlite"

BOUND = "beta-intel-safe"
SCHEMA_ID = "wolf.intel-ops-pack.v2"
OWNER = "PERS-MATT"
SLICE = "intel_ops_pack_v2"
CAP_01 = "CAP-INTEL-01"
CAP_02 = "CAP-INTEL-02"
CAP_03 = "CAP-INTEL-03"
CAP_04 = "CAP-INTEL-04"
CAP_05 = "CAP-INTEL-05"
CR_05 = "CR-be51980bd1194448"
CR_AU = "CR-dca0ad62e1b0032e"
AU_WOLF = "AU-INTEL-02-WOLF"

CONNECTIVE_SCHEMA_ID = "wolf.intel-ops-needs-you-connective.v1"
CONNECTIVE_SLICE = "intel_ops_needs_you_connective"
CONNECTIVE_RUN_ID = "BF-intel-ops-needs-you-connective-20260923"
CONNECTIVE_CLAIM_ID = "bf-intel-ops-needs-you-connective-20260923"
CONNECTIVE_BOUND = "beta-intel-safe"
CONNECTIVE_KINDS: tuple[str, ...] = (
    "morning_seed",
    "waiting_others",
    "needs_you",
    "policy",
    "intel_connective",
    "learning_policy",
)
CONNECTIVE_DEPTH_KINDS = frozenset(
    {"morning_seed", "waiting_others", "needs_you", "policy"}
)
INTEL_SURFACES = frozenset(
    {
        "intel",
        "intel_ops",
        "intel_connective",
        "learning_policy",
        "decision_memory",
        "approve_to_rule",
    }
)
_NAME_RE = re.compile(r"[a-z0-9]+")
_SEAT_NAME_TOKENS: dict[str, frozenset[str]] = {
    OWNER: frozenset({"matt", "owner"}),
}

PERM_DM_READ = dm.PERM_READ
PERM_DM_RECORD = dm.PERM_RECORD
PERM_RULE_READ = rules.PERM_READ
PERM_RULE_NOTE = rules.PERM_NOTE
PERM_RULE_APPROVE = rules.PERM_APPROVE

INTEL_PERMS = frozenset(
    {
        PERM_DM_READ,
        PERM_DM_RECORD,
        PERM_RULE_READ,
        PERM_RULE_NOTE,
        PERM_RULE_APPROVE,
    }
)

HIDDEN = (
    "finance",
    "zayen",
    "hr",
    "trading",
    "bank",
    "payment",
    "payroll",
    "tax",
)

MONEY_KEYS = frozenset(
    {
        "money",
        "amount",
        "payment",
        "bank",
        "folio",
        "zayen",
        "payroll",
        "tax",
        "trading",
        "finance",
        "pay",
        "settle",
        "transfer",
    }
)

SCORE_KEYS = frozenset({"proven", "ready", "maturity", "cap_proven", "score"})
PROMOTE_KEYS = frozenset(
    {"promote", "auto_promote", "production", "operational", "live_rule", "execute", "run"}
)
RESOLVE_KEYS = frozenset({"resolve", "cr_resolve", "close_cr"})

REFUSE_VIEWS = {
    "payment": "payment",
    "money": "payment",
    "pay": "payment",
    "bank": "bank",
    "transfer": "bank",
    "finance": "finance",
    "zayen": "finance",
    "payroll": "finance",
    "tax": "finance",
    "folio": "finance",
    "hr": "hr",
    "hris": "hr",
    "trading": "trading",
    "proven": "proven",
    "ready": "ready",
    "resolve": "resolve",
    "promote": "promote",
    "auto-promote": "promote",
    "execute": "execute",
    "run": "execute",
    "production": "production",
    "cloudflare": "production",
}

TZ_UTC = timezone.utc

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intel_ops_asks (
  ask_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  question TEXT NOT NULL,
  scope_raw TEXT NOT NULL,
  status TEXT NOT NULL,
  summary TEXT NOT NULL,
  next_human_action TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  honesty_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_intel_ops_asks_created
  ON intel_ops_asks(created_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_intel_ops_asks_no_update
BEFORE UPDATE ON intel_ops_asks
BEGIN
  SELECT RAISE(ABORT, 'intel_ops_asks is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_intel_ops_asks_no_delete
BEFORE DELETE ON intel_ops_asks
BEGIN
  SELECT RAISE(ABORT, 'intel_ops_asks is append-only');
END;
"""


class IntelOpsPackError(ValueError):
    """Fail closed. Does not invent maturity, money, or a live rule."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _under_test() -> bool:
    return (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1"


def _resolve_rule_db(rule_db_path: Path | str | None) -> Path | str | None:
    if rule_db_path is not None:
        return rule_db_path
    if _under_test():
        # Keep WOLF_TEST_MODE off the live approve-to-rule ledger.
        path = BETA_ROOT / "catalog" / "backups" / "intel-ops-pack-test-rules.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return None


def _resolve_pack_db(db_path: Path | str | None) -> Path | str | None:
    if db_path is not None:
        return db_path
    if _under_test():
        path = BETA_ROOT / "catalog" / "backups" / "intel-ops-pack-test-asks.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return None


def refuse_payment(_body: dict | None = None) -> None:
    raise IntelOpsPackError("Intel Ops does not move money.", code="payment_refused")


def refuse_bank(_body: dict | None = None) -> None:
    raise IntelOpsPackError("Intel Ops does not touch a bank.", code="bank_refused")


def refuse_finance(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Finance, Zayen, payroll, and tax stay off this desk.",
        code="finance_refused",
    )


def refuse_hr(_body: dict | None = None) -> None:
    raise IntelOpsPackError("HR stays off this desk.", code="hr_refused")


def refuse_trading(_body: dict | None = None) -> None:
    raise IntelOpsPackError("Trading stays off this desk.", code="trading_refused")


def refuse_proven(_body: dict | None = None) -> None:
    raise IntelOpsPackError("Intel Ops does not mark PROVEN.", code="proven_refused")


def refuse_ready(_body: dict | None = None) -> None:
    raise IntelOpsPackError("Intel Ops does not mark READY.", code="ready_refused")


def refuse_resolve(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops does not resolve a completion row.",
        code="resolve_refused",
    )


def refuse_promote(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses auto-promote. A stub is not a live rule.",
        code="promote_refused",
    )


def refuse_execute(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses rule execution. A stub does not run.",
        code="execute_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses a production write.",
        code="production_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    keys = {str(key).strip().lower() for key in payload.keys()}
    if keys & MONEY_KEYS or payload.get("pay") or payload.get("settle"):
        if keys & {"bank", "transfer"}:
            refuse_bank(payload)
        if keys & {"hr", "hris"}:
            refuse_hr(payload)
        if keys & {"trading"}:
            refuse_trading(payload)
        if keys & {"zayen", "payroll", "tax", "finance", "folio"}:
            refuse_finance(payload)
        refuse_payment(payload)
    if keys & SCORE_KEYS or payload.get("proven") or payload.get("ready"):
        if payload.get("ready") or "ready" in keys:
            refuse_ready(payload)
        refuse_proven(payload)
    if keys & RESOLVE_KEYS or payload.get("resolve"):
        refuse_resolve(payload)
    if keys & PROMOTE_KEYS or payload.get("promote") or payload.get("auto_promote"):
        if payload.get("execute") or payload.get("run") or "execute" in keys or "run" in keys:
            refuse_execute(payload)
        if payload.get("production") or "production" in keys:
            refuse_production(payload)
        refuse_promote(payload)
    if payload.get("production") or payload.get("cloudflare"):
        refuse_production(payload)
    raise IntelOpsPackError(
        "Intel Ops refuses this write on the pack surface.",
        code="writes_refused",
    )


def refuse_code(path: str) -> str | None:
    low = (path or "").rstrip("/")
    prefix = "/api/intel/ops-pack/"
    if not low.startswith(prefix):
        return None
    view = low[len(prefix) :].split("/", 1)[0].strip().lower()
    return REFUSE_VIEWS.get(view)


def _ledger_state(cap_id: str, ledger_path: Path | str | None = None) -> str:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(cap_id) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return str(row[0]).strip().upper() or "UNKNOWN"


def _cr_state(cr_id: str, catalog: Path | str | None = None) -> dict[str, Any]:
    out = {
        "cr_id": cr_id,
        "cr_present": False,
        "cr_state": None,
        "cr_resolved": False,
    }
    path = Path(catalog) if catalog else CATALOG_DB
    if not path.is_file():
        return out
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?",
                (cr_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return out
    if row is None:
        return out
    state = str(row[0] or "").strip().upper() or None
    out["cr_present"] = True
    out["cr_state"] = state
    out["cr_resolved"] = state == "RESOLVED"
    return out


def honesty_flags(ledger_path: Path | str | None = None) -> dict[str, Any]:
    c01 = _ledger_state(CAP_01, ledger_path)
    c02 = _ledger_state(CAP_02, ledger_path)
    c03 = _ledger_state(CAP_03, ledger_path)
    c04 = _ledger_state(CAP_04, ledger_path)
    c05 = _ledger_state(CAP_05, ledger_path)
    cr05 = _cr_state(CR_05)
    cr_au = _cr_state(CR_AU)
    return {
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "cap": CAP_01,
        "cap_intel_01": c01,
        "cap_intel_02": c02,
        "cap_intel_03": c03,
        "cap_intel_04": c04,
        "cap_intel_05": c05,
        "caps_raised": False,
        "invented_proven": False,
        "invented_ready": False,
        "proven": False,
        "ready": False,
        "auto_promote": False,
        "rule_execution": False,
        "live_rule": False,
        "cr_05_id": CR_05,
        "cr_05_state": cr05.get("cr_state"),
        "cr_05_resolved": bool(cr05.get("cr_resolved")),
        "cr_au_id": CR_AU,
        "cr_au_state": cr_au.get("cr_state"),
        "cr_au_resolved": bool(cr_au.get("cr_resolved")),
        "au_intel_02_wolf": AU_WOLF,
        "au_intel_02_wolf_started": False,
        "cr_mutated": False,
        "ledger_write": False,
        "model_c_write": False,
        "model_c_maturity_raised": False,
        "permission_grant_invented": False,
        "live_rbac_mutated": False,
        "decision_memory_silent_rewrite": False,
        "money": None,
        "payment_executed": False,
        "bank_write": False,
        "finance_controls": False,
        "hr": False,
        "trading": False,
        "production": False,
        "production_write": False,
        "cloudflare_mutated": False,
        "llm_as_evidence": False,
        "anon_fail_closed": True,
        "hidden": list(HIDDEN),
        "staff_ready": False,
        "invented_staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "false_resolve_cr": False,
        "duplicate_mutate_surface": False,
        "auto_execute": False,
        "intel_ops_needs_you_connective": True,
        "connective_bound": CONNECTIVE_BOUND,
        "connective_schema": CONNECTIVE_SCHEMA_ID,
        "connective_claim_id": CONNECTIVE_CLAIM_ID,
        "connective_run_id": CONNECTIVE_RUN_ID,
    }


def _rbac_allows(person_id: str, code: str) -> bool:
    try:
        return bool(_rbac.can(person_id, code))
    except Exception:  # noqa: BLE001 — fail closed
        return False


def seat_for(person_id: str | None) -> dict[str, Any] | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    if pid == OWNER:
        return {
            "person_id": OWNER,
            "seat": "owner",
            "can_read": True,
            "can_ask": True,
            "can_recall": True,
            "can_note": True,
            "gate": "owner",
            "money": False,
            "finance": False,
            "hr": False,
            "trading": False,
        }
    held = sorted(code for code in INTEL_PERMS if _rbac_allows(pid, code))
    if not held:
        return None
    return {
        "person_id": pid,
        "seat": "intel_holder",
        "can_read": True,
        "can_ask": True,
        "can_recall": PERM_DM_READ in held or PERM_DM_RECORD in held,
        "can_note": PERM_RULE_NOTE in held or PERM_RULE_APPROVE in held or pid == OWNER,
        "gate": "role",
        "permissions": held,
        "money": False,
        "finance": False,
        "hr": False,
        "trading": False,
    }


def require_actor(person_id: str | None) -> dict[str, Any]:
    seat = seat_for(person_id)
    if seat is None:
        raise IntelOpsPackError(
            "Intel Ops is Owner (PERS-MATT) or an existing intel.rule / "
            "decision.memory holder only.",
            code="forbidden",
        )
    return seat


def _assert_beta_path(resolved: Path) -> Path:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "wolf-system" in low or "8787" in low:
        raise IntelOpsPackError("Intel Ops refuses a non-beta path.", code="not_beta")
    if "alchemist" in low or "zayen" in low or "/production" in low:
        raise IntelOpsPackError("Intel Ops refuses that path.", code="not_beta")
    if "bank" in name or "payment" in name or name == "money.sqlite":
        raise IntelOpsPackError("Intel Ops refuses a money path.", code="not_beta")
    try:
        resolved.relative_to(BETA_ROOT)
        return resolved
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise IntelOpsPackError(
            "Intel Ops refuses a path outside Beta or a test fixture.",
            code="not_beta",
        ) from exc
    return resolved


def pack_db(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return _assert_beta_path(resolved)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def _open_write(db_path: Path | str | None = None) -> tuple[sqlite3.Connection, Path]:
    path = pack_db(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn, path


def _open_read(db_path: Path | str | None = None) -> tuple[sqlite3.Connection | None, Path]:
    path = pack_db(db_path)
    if not path.is_file():
        return None, path
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn, path


def _reject_ask_keys(body: dict) -> None:
    if not isinstance(body, dict):
        raise IntelOpsPackError("payload must be an object", code="invalid")
    keys = {str(k).strip().lower() for k in body.keys()}
    if (
        keys & (MONEY_KEYS | SCORE_KEYS | PROMOTE_KEYS | RESOLVE_KEYS)
        or body.get("pay")
        or body.get("settle")
        or body.get("proven")
        or body.get("ready")
        or body.get("resolve")
        or body.get("promote")
        or body.get("production")
        or body.get("cloudflare")
    ):
        refuse_external_write(body)
    allowed = {
        "question",
        "scope",
        "kind",
        "work_item_id",
        "experiment_note",
        "experiment_id",
    }
    extra = sorted(set(body) - allowed)
    if extra:
        raise IntelOpsPackError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def last_ask(db_path: Path | str | None = None) -> dict[str, Any]:
    conn, _path = _open_read(db_path)
    empty = {
        "ok": True,
        "empty": True,
        "loud": True,
        "ask": None,
        "why": (
            "No ask has been recorded on this desk yet. EMPTY is not an invented outcome."
        ),
    }
    if conn is None:
        return empty
    try:
        row = conn.execute(
            """
            SELECT ask_id, person_id, question, scope_raw, status, summary,
                   next_human_action, provenance_json, honesty_json, created_at
            FROM intel_ops_asks
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return empty
    try:
        provenance = json.loads(row["provenance_json"] or "[]")
    except json.JSONDecodeError:
        provenance = []
    try:
        ask_honesty = json.loads(row["honesty_json"] or "{}")
    except json.JSONDecodeError:
        ask_honesty = {}
    return {
        "ok": True,
        "empty": False,
        "loud": False,
        "ask": {
            "ask_id": row["ask_id"],
            "person_id": row["person_id"],
            "question": row["question"],
            "scope": row["scope_raw"],
            "status": row["status"],
            "summary": row["summary"],
            "next_human_action": row["next_human_action"],
            "provenance": provenance if isinstance(provenance, list) else [],
            "honesty": ask_honesty if isinstance(ask_honesty, dict) else {},
            "created_at": row["created_at"],
        },
        "why": "Last recorded orchestration on this desk. Honesty flags stay visible.",
    }


def today_strip(db_path: Path | str | None = None) -> dict[str, Any]:
    last = last_ask(_resolve_pack_db(db_path))
    ask = last.get("ask")
    flags = honesty_flags()
    return {
        "ok": True,
        "empty": bool(last.get("empty")),
        "loud": bool(last.get("loud")),
        "status": None if not ask else ask.get("status"),
        "summary": None if not ask else ask.get("summary"),
        "next_human_action": None if not ask else ask.get("next_human_action"),
        "provenance": [] if not ask else ask.get("provenance") or [],
        "question": None if not ask else ask.get("question"),
        "scope": None if not ask else ask.get("scope"),
        "created_at": None if not ask else ask.get("created_at"),
        "honesty": {
            "cap_intel_01": flags["cap_intel_01"],
            "cap_intel_05": flags["cap_intel_05"],
            "proven": False,
            "ready": False,
            "llm_as_evidence": False,
            "auto_promote": False,
        },
        "why": last.get("why"),
    }


def _persist_ask(
    *,
    person_id: str,
    out: dict[str, Any],
    scope_raw: str,
    db_path: Path | str | None,
) -> dict[str, Any]:
    ask_id = f"ASK-{uuid.uuid4()}"
    conn, _path = _open_write(db_path)
    try:
        conn.execute(
            """
            INSERT INTO intel_ops_asks (
              ask_id, person_id, question, scope_raw, status, summary,
              next_human_action, provenance_json, honesty_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ask_id,
                person_id,
                str(out.get("question") or ""),
                scope_raw,
                str(out.get("status") or intel.OUTCOME_UNKNOWN),
                str(out.get("summary") or ""),
                str(out.get("next_human_action") or intel.ACTION_NONE),
                json.dumps(out.get("provenance") or [], ensure_ascii=False),
                json.dumps(out.get("honesty") or {}, ensure_ascii=False),
                now_utc_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ask_id": ask_id}


def ask_question(
    *,
    question: str,
    scope: str | dict[str, Any] | None = None,
    verified_person_id: str | None = None,
    kind: str | None = None,
    work_item_id: str | None = None,
    persist: bool = True,
    db_path: Path | str | None = None,
    dm_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    q = (question or "").strip()
    if not q:
        raise IntelOpsPackError("question required", code="bad_question")
    scope_raw = "Wolf system"
    if isinstance(scope, str) and scope.strip():
        scope_raw = scope.strip()
    elif isinstance(scope, dict) and scope:
        scope_raw = json.dumps(scope, ensure_ascii=False, sort_keys=True)
    actor: dict[str, Any] = {
        "person_id": seat["person_id"],
    }
    if seat["person_id"] == OWNER:
        actor["permission_context"] = _ephemeral_owner_dm_permission_context()
        actor["db_path"] = Path(dm_db_path) if dm_db_path else DM_DB
    else:
        actor["permission_context"] = {
            "person_id": seat["person_id"],
            "target_context": {},
        }
        if dm_db_path:
            actor["db_path"] = Path(dm_db_path)
    if kind and str(kind).strip():
        actor["kind"] = str(kind).strip()
    try:
        out = intel.orchestrate_institutional_question(
            q,
            scope_raw,
            actor_context=actor,
            work_item_id=(work_item_id or "").strip() or None,
        )
    except intel.IntelOrchestrationError as exc:
        raise IntelOpsPackError(str(exc), code=exc.code) from exc
    stored = None
    if persist:
        stored = _persist_ask(
            person_id=seat["person_id"],
            out=out,
            scope_raw=scope_raw,
            db_path=_resolve_pack_db(db_path),
        )
    return {
        "ok": True,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "gate": seat["gate"],
        "ask_id": None if stored is None else stored["ask_id"],
        "persisted": bool(stored),
        **out,
        "pack_honesty": honesty_flags(),
        "money": None,
        "promoted": False,
        "executed": False,
        "live_rule": False,
    }


def _ephemeral_owner_dm_permission_context() -> dict[str, Any]:
    """Temp RBAC under beta-os backups only. Does not write the live catalog."""
    root = BETA_ROOT / "catalog" / "backups"
    root.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix="intel-ops-dm-", dir=str(root)))
    path = td / "rbac.sqlite"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    fixture = dm.install_owner_seed_rbac_fixture(conn)
    ts = now_utc_iso()
    row = conn.execute(
        "SELECT position_id FROM org_assignments WHERE assignment_id=?",
        (fixture["assignment_id"],),
    ).fetchone()
    position_id = row["position_id"] if row else "POS-DM-OWNER-SEED"
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, status, created_at, updated_at
        ) VALUES (?, 'Matthew Goss', 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
          status='ACTIVE', updated_at=excluded.updated_at
        """,
        (OWNER, ts, ts),
    )
    asg = f"ASG-INTEL-OPS-{uuid.uuid4().hex[:8].upper()}"
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at,
          status, is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (asg, OWNER, position_id, ts, ts, ts),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, asg, fixture["scope_id"], ts, ts)
    conn.commit()
    conn.close()
    return {
        "person_id": OWNER,
        "rbac_db_path": path,
        "target_context": {},
    }


def recall_decisions(
    *,
    scope: str | dict[str, Any] | None = None,
    query: str = "",
    verified_person_id: str | None = None,
    limit: int = 20,
    dm_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    if not seat.get("can_recall") and seat.get("seat") != "owner":
        raise IntelOpsPackError(
            "Decision Memory recall requires decision.memory permission.",
            code="forbidden",
        )
    scope_raw: str | dict[str, Any] = scope if scope else "Wolf system"
    if isinstance(scope_raw, str) and not scope_raw.strip():
        scope_raw = "Wolf system"
    lim = max(1, min(int(limit or 20), dm.RECALL_MAX))
    db = Path(dm_db_path) if dm_db_path else DM_DB
    if seat["person_id"] == OWNER:
        ctx = _ephemeral_owner_dm_permission_context()
        via = "owner_gate_ephemeral_rbac"
    else:
        ctx = {"person_id": seat["person_id"], "target_context": {}}
        via = "live_rbac"
    try:
        hit = dm.recall(
            scope_raw,
            query or "",
            permission_context=ctx,
            db_path=db,
            limit=lim,
        )
    except dm.DecisionMemoryError as exc:
        if exc.code == "denied":
            return {
                "ok": True,
                "empty": True,
                "loud": True,
                "status": dm.STATUS_NOT_FOUND,
                "decisions": [],
                "count": 0,
                "scope": dm.normalize_scope(scope_raw),
                "query": query or "",
                "via": via,
                "inaccessible": True,
                "why": (
                    "Decision Memory was inaccessible for this caller. "
                    "EMPTY is not invented history."
                ),
                "honesty": dm.honesty_flags(),
                "pack_honesty": honesty_flags(),
            }
        raise IntelOpsPackError(str(exc), code=exc.code) from exc
    decisions = hit.get("decisions") or []
    empty = len(decisions) == 0
    return {
        "ok": True,
        "empty": empty,
        "loud": empty,
        "status": hit.get("status"),
        "decisions": decisions,
        "count": int(hit.get("count") or 0),
        "scope": hit.get("scope"),
        "query": hit.get("query") or "",
        "via": via,
        "inaccessible": False,
        "permission_grant_invented": False,
        "live_rbac_mutated": False,
        "why": (
            "No matching Decision Memory rows for this scope/query. "
            "EMPTY is not invented history."
            if empty
            else "Scoped Decision Memory recall. Append-only rows. No silent rewrite."
        ),
        "honesty": hit.get("honesty") or dm.honesty_flags(),
        "pack_honesty": honesty_flags(),
    }


def queue_summary(
    *,
    verified_person_id: str | None = None,
    rule_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    role_allowed = seat.get("gate") == "role"
    try:
        listed = rules.list_experiments(
            seat["person_id"],
            role_allowed=role_allowed,
            db_path=_resolve_rule_db(rule_db_path),
        )
    except rules.IntelRuleError as exc:
        raise IntelOpsPackError(str(exc), code=exc.code) from exc
    experiments = listed.get("experiments") or []
    noted = sum(1 for row in experiments if row.get("state") == rules.STATE_NOTED)
    approved = sum(1 for row in experiments if row.get("state") == rules.STATE_APPROVED)
    stub = sum(1 for row in experiments if row.get("state") == rules.STATE_STUB)
    return {
        "ok": True,
        "count": int(listed.get("count") or 0),
        "note_count": int(listed.get("note_count") or 0),
        "approval_count": int(listed.get("approval_count") or 0),
        "stub_count": int(listed.get("stub_count") or 0),
        "state_counts": {
            "NOTED": noted,
            "APPROVED": approved,
            "STUB": stub,
        },
        "experiments": experiments[:20],
        "promoted_count": int(listed.get("promoted_count") or 0),
        "executed_count": int(listed.get("executed_count") or 0),
        "auto_promote": False,
        "live": False,
        "live_rule": False,
        "why": (
            "Approve-to-rule queue summary. STUB is not a live rule. "
            "No auto-promote. CAP-INTEL-05 stays at the ledger state."
        ),
        "gaps": listed.get("gaps") or rules.gaps(),
        "honesty": listed.get("honesty") or rules.honesty_flags(),
        "pack_honesty": honesty_flags(),
        "href": "/api/intel/approve-to-rule",
    }


def handoff_note(
    body: dict | None,
    *,
    verified_person_id: str | None = None,
    rule_db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    payload = dict(body or {})
    _reject_ask_keys(payload)
    note_text = str(payload.get("experiment_note") or "").strip()
    if not note_text:
        raise IntelOpsPackError("experiment_note required", code="bad_note")
    role_allowed = seat.get("gate") == "role" and (
        PERM_RULE_NOTE in (seat.get("permissions") or [])
        or PERM_RULE_APPROVE in (seat.get("permissions") or [])
    )
    if seat["person_id"] != OWNER and not role_allowed:
        raise IntelOpsPackError(
            "Experiment note requires intel.rule.note (or Owner).",
            code="forbidden",
        )
    try:
        out = rules.record_note(
            {
                "experiment_note": note_text,
                **(
                    {"experiment_id": payload["experiment_id"]}
                    if payload.get("experiment_id")
                    else {}
                ),
            },
            person_id=seat["person_id"],
            role_allowed=role_allowed or seat["person_id"] == OWNER,
            db_path=_resolve_rule_db(rule_db_path),
        )
    except rules.IntelRuleError as exc:
        raise IntelOpsPackError(str(exc), code=exc.code) from exc
    return {
        "ok": True,
        "person_id": seat["person_id"],
        "handoff": "approve-to-rule",
        "appended": True,
        "promoted": False,
        "executed": False,
        "live_rule": False,
        "auto_promote": False,
        **out,
        "pack_honesty": honesty_flags(),
        "why": (
            "Append-only experiment note. Not approved. Not a stub. "
            "Not a live rule. No auto-promote."
        ),
    }


def build_desk(
    *,
    verified_person_id: str | None = None,
    db_path: Path | str | None = None,
    dm_db_path: Path | str | None = None,
    rule_db_path: Path | str | None = None,
    recall_scope: str | None = None,
    recall_query: str = "",
) -> dict[str, Any]:
    seat = require_actor(verified_person_id)
    today = today_strip(_resolve_pack_db(db_path))
    recall = recall_decisions(
        scope=recall_scope or "Wolf system",
        query=recall_query,
        verified_person_id=seat["person_id"],
        dm_db_path=dm_db_path,
    )
    queue = queue_summary(
        verified_person_id=seat["person_id"],
        rule_db_path=_resolve_rule_db(rule_db_path),
    )
    learning_policy: dict[str, Any] = {
        "ok": True,
        "stub_count": int(queue.get("stub_count") or 0),
        "recommendations": [],
        "empty": True,
        "auto_apply": False,
        "auto_promote": False,
        "href": "/api/intel/learning-policy",
    }
    try:
        from core import intel_learning_policy as ilp

        role_allowed = seat.get("gate") == "role"
        learning_policy = {
            **ilp.stub_recommendations(
                seat["person_id"],
                role_allowed=role_allowed or seat["person_id"] == OWNER,
                db_path=_resolve_rule_db(rule_db_path),
            ),
            "next_action": ilp.operator_next_action(
                seat["person_id"],
                role_allowed=role_allowed or seat["person_id"] == OWNER,
                db_path=_resolve_rule_db(rule_db_path),
            ),
            "href": "/api/intel/learning-policy",
        }
    except Exception:  # noqa: BLE001
        pass
    flags = honesty_flags()
    board = {
        "ok": True,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "person_id": seat["person_id"],
        "seat": seat,
        "today": today,
        "recall": recall,
        "queue": queue,
        "learning_policy": learning_policy,
        "loop": {
            "ask": "/api/intel/ops-pack/ask",
            "recall": "/api/intel/ops-pack/recall",
            "queue": "/api/intel/ops-pack/queue",
            "note": "/api/intel/ops-pack/note",
            "approve_to_rule": "/api/intel/approve-to-rule",
            "learning_policy": "/api/intel/learning-policy",
            "needs_you": "/api/intel/ops-pack/needs-you",
            "auto_promote": False,
            "rule_execution": False,
        },
        "caps": {
            CAP_01: flags["cap_intel_01"],
            CAP_02: flags["cap_intel_02"],
            CAP_03: flags["cap_intel_03"],
            CAP_04: flags["cap_intel_04"],
            CAP_05: flags["cap_intel_05"],
        },
        "crs": {
            CR_05: {
                "state": flags["cr_05_state"],
                "resolved": flags["cr_05_resolved"],
            },
            CR_AU: {
                "state": flags["cr_au_state"],
                "resolved": flags["cr_au_resolved"],
                "au": AU_WOLF,
                "started": False,
            },
        },
        "hidden": list(HIDDEN),
        "money": None,
        "payment_executed": False,
        "finance_controls": False,
        "honesty": flags,
    }
    connective = needs_you_connective_strip(
        verified_person_id=seat["person_id"],
        db_path=db_path,
        rule_db_path=rule_db_path,
    )
    pack_next = _pack_href_next()
    preferred = connective.get("next_action") if connective.get("count") else None
    board["needs_you_connective"] = connective
    board["pack_next_action"] = pack_next
    board["next_action"] = preferred if isinstance(preferred, dict) else pack_next
    board["staff_ready"] = False
    board["haikal_human"] = "not_started"
    board["devi_retest"] = "parked"
    board["auto_promote"] = False
    board["auto_execute"] = False
    return board


def schema_document() -> dict[str, Any]:
    return {
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "views": [
            "",
            "today",
            "ask",
            "recall",
            "queue",
            "note",
            "schema",
            "permissions",
            "needs-you",
        ],
        "refused": sorted(REFUSE_VIEWS.keys()),
        "auto_promote": False,
        "rule_execution": False,
        "money": False,
        "connective_schema": CONNECTIVE_SCHEMA_ID,
    }


def refuse_staff_ready(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses inventing staff_ready.",
        code="staff_ready_refused",
        http_status=405,
    )


def refuse_haikal_done(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses inventing Haikal human done.",
        code="haikal_done_refused",
        http_status=405,
    )


def refuse_devi_done(_body: dict | None = None) -> None:
    raise IntelOpsPackError(
        "Intel Ops refuses inventing Devi done.",
        code="devi_done_refused",
        http_status=405,
    )


def connective_refuse_code(path: str) -> str | None:
    """Refuse invent paths on the Intel Needs-You connective surface."""
    low = (path or "").rstrip("/")
    refused = {
        "/api/intel/ops-pack/haikal-done": "haikal_done",
        "/api/intel/ops-pack/haikal_done": "haikal_done",
        "/api/intel/ops-pack/devi-done": "devi_done",
        "/api/intel/ops-pack/devi_done": "devi_done",
        "/api/intel/ops-pack/staff_ready": "staff_ready",
        "/api/intel/ops-pack/needs-you/staff-ready": "staff_ready",
        "/api/intel/ops-pack/needs-you/haikal-done": "haikal_done",
        "/api/intel/ops-pack/needs-you/devi-done": "devi_done",
        "/api/intel/ops-pack/needs-you/proven": "proven",
        "/api/intel/ops-pack/needs-you/ready": "ready",
        "/api/intel/ops-pack/needs-you/promote": "promote",
        "/api/intel/ops-pack/needs-you/execute": "execute",
        "/api/intel/ops-pack/needs-you/auto-promote": "promote",
    }
    return refused.get(low)


def _needs_you_module():
    from core import owner_progress_needs_you_depth as nye

    return nye


def _morning_meta() -> dict[str, dict[str, Any]]:
    from core import owner_commissioning_queue as ocq

    return {str(t.get("id")): t for t in ocq.seed_templates() if t.get("id")}


def _name_tokens(*parts: Any) -> set[str]:
    blob = " ".join(str(p or "") for p in parts).lower()
    return set(_NAME_RE.findall(blob))


def _seat_tokens(seat: dict[str, Any]) -> set[str]:
    pid = str(seat.get("person_id") or "")
    tokens = set(_SEAT_NAME_TOKENS.get(pid, frozenset()))
    tokens |= _name_tokens(pid)
    return tokens


def _is_intel_scoped(item: dict[str, Any]) -> bool:
    """Intel commissioning, connective, or learning-policy. Other businesses stay out."""
    kind = str(item.get("kind") or "")
    if kind in {"intel_connective", "learning_policy"}:
        return True
    cap = str(item.get("capability") or "")
    if cap.startswith("CAP-INTEL") or cap.startswith("AU-INTEL"):
        return True
    biz = str(item.get("business") or "").upper()
    if biz in {"INTEL", "INTELLIGENCE"}:
        return True
    domain = str(item.get("domain") or "").upper()
    if domain in {"INTEL", "INTELLIGENCE"}:
        return True
    surface = str(item.get("surface") or "").lower()
    if surface in INTEL_SURFACES:
        return True
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("open_href", "route", "href", "object_id", "source")
    ).lower()
    if "/intel-ops" in blob or "/api/intel/" in blob or "cap-intel" in blob:
        return True
    return False


def _in_scope_for_seat(item: dict[str, Any], seat: dict[str, Any]) -> bool:
    """Owner sees every Intel-scoped row. Other intel seats see in-scope rows only."""
    if seat.get("person_id") == OWNER or seat.get("seat") == "owner":
        return True
    audience = str(item.get("audience") or "").upper()
    if audience == "NEEDS_MATT":
        return False
    kind = str(item.get("kind") or "")
    if kind in {"intel_connective", "learning_policy"}:
        return True
    owner_pid = str(item.get("owner_person_id") or item.get("opened_by") or "").strip()
    if owner_pid and owner_pid == seat.get("person_id"):
        return True
    allowed = _seat_tokens(seat)
    if not allowed:
        return False
    tokens = _name_tokens(
        item.get("who"),
        item.get("person_to_test"),
        item.get("owner_person_id"),
    )
    if tokens & allowed:
        return True
    return False


def _handoff_block(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    kind = str(item.get("kind") or "")
    block: dict[str, Any] = {
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": kind in CONNECTIVE_DEPTH_KINDS,
        "reuse_intel_connective": kind == "intel_connective",
        "reuse_learning_policy": kind == "learning_policy",
        "auto_promote": False,
        "auto_execute": False,
    }
    if kind in CONNECTIVE_DEPTH_KINDS:
        block.update(
            {
                "detail": f"/api/progress/needs-you/items/{oid}",
                "acknowledge": f"/api/progress/needs-you/items/{oid}/acknowledge",
                "intel_detail": f"/api/intel/ops-pack/needs-you/items/{oid}",
                "intel_acknowledge": f"/api/intel/ops-pack/needs-you/items/{oid}/acknowledge",
            }
        )
    elif kind == "intel_connective":
        block.update(
            {
                "detail": f"/api/intel/connective/recommendations/{oid}/operator",
                "action": f"/api/intel/connective/recommendations/{oid}/operator-action",
                "intel_detail": f"/api/intel/ops-pack/needs-you/items/{oid}",
                "read_only_ack": True,
            }
        )
    elif kind == "learning_policy":
        block.update(
            {
                "detail": "/api/intel/learning-policy",
                "stubs": "/api/intel/learning-policy/stubs",
                "intel_detail": f"/api/intel/ops-pack/needs-you/items/{oid}",
                "read_only": True,
                "auto_promote": False,
            }
        )
    return block


def _project_row(item: dict[str, Any]) -> dict[str, Any]:
    oid = str(item.get("object_id") or "")
    href = item.get("open_href") or item.get("href") or "/intel-ops-pack"
    return {
        "object_id": oid,
        "kind": item.get("kind"),
        "title": item.get("title"),
        "who": item.get("who"),
        "audience": item.get("audience"),
        "priority": item.get("priority"),
        "status": item.get("operator_status") or item.get("status"),
        "href": href,
        "owner_person_id": item.get("owner_person_id"),
        "surface": item.get("surface"),
        "invented": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
        "handoff": _handoff_block(item),
    }


def _connective_next(item: dict[str, Any]) -> dict[str, Any]:
    href = item.get("open_href") or item.get("href") or "/intel-ops-pack"
    return {
        "code": "needs_you_connective",
        "label": item.get("title") or "Open in-scope Intel Needs-You item",
        "href": href,
        "object_id": item.get("object_id"),
        "kind": item.get("kind"),
        "invented": False,
        "state": "READ",
        "source": "intel_ops_needs_you_connective",
        "preferred_over_pack": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
    }


def _pack_href_next() -> dict[str, Any]:
    return {
        "code": "pack_href",
        "label": "Open Intel home",
        "href": "/intel-ops-pack",
        "invented": False,
        "state": "READ",
        "preferred_over_pack": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "auto_promote": False,
        "auto_execute": False,
    }


def _empty_connective(*, why: str) -> dict[str, Any]:
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "empty": True,
        "count": 0,
        "by_kind": {k: 0 for k in CONNECTIVE_KINDS},
        "items": [],
        "next_action": None,
        "empty_message": why,
        "invented": False,
        "invented_count": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
        "false_resolve_cr": False,
    }


def _sort_connective(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(it: dict[str, Any]) -> tuple[Any, ...]:
        kind_rank = {k: i for i, k in enumerate(CONNECTIVE_KINDS)}.get(
            str(it.get("kind") or ""), 9
        )
        pri = {"P0": 0, "P1": 1, "P2": 2}.get(str(it.get("priority") or ""), 5)
        return (kind_rank, pri, str(it.get("object_id") or ""))

    items.sort(key=sort_key)
    return items


def _commissioning_rows(*, state_path=None) -> list[dict[str, Any]]:
    nye = _needs_you_module()
    meta = _morning_meta()
    rows = nye.collect_candidates(state_path=state_path, include_parked=False)
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("kind") not in CONNECTIVE_DEPTH_KINDS:
            continue
        merged = dict(row)
        extra = meta.get(str(row.get("object_id") or "")) or {}
        for key in (
            "business",
            "surface",
            "capability",
            "person_to_test",
            "route",
            "audience",
            "domain",
        ):
            if extra.get(key) and not merged.get(key):
                merged[key] = extra[key]
        if not merged.get("who") and extra.get("person_to_test"):
            merged["who"] = extra.get("person_to_test")
        if not _is_intel_scoped(merged):
            continue
        merged["business"] = merged.get("business") or "INTEL"
        out.append(merged)
    return out


def _intel_connective_rows(
    *,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Recorded intel-connective attention only. Empty attention is not a row."""
    try:
        from core import intel_connective as connective

        payload = connective.owner_attention_consequence(
            operator_db=operator_db,
            eval_db=eval_db,
        )
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for row in payload.get("items") or []:
        if not isinstance(row, dict):
            continue
        oid = str(row.get("recommendation_id") or "")
        if not oid:
            continue
        nxt = row.get("next_action") if isinstance(row.get("next_action"), dict) else {}
        out.append(
            {
                "object_id": oid,
                "kind": "intel_connective",
                "title": (nxt or {}).get("label") or oid,
                "who": None,
                "audience": "INTEL_SEAT",
                "priority": "P1",
                "status": row.get("disposition") or "open",
                "business": "INTEL",
                "surface": row.get("surface") or "intel_connective",
                "href": row.get("href") or "/intel-ops-pack#operator-depth",
                "open_href": row.get("href") or "/intel-ops-pack#operator-depth",
                "invented": False,
                "auto_promote": False,
                "auto_execute": False,
            }
        )
    return out


def _learning_policy_rows(
    seat: dict[str, Any],
    *,
    rule_db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Non-empty learning-policy rows only. An empty queue is not invented work."""
    try:
        from core import intel_learning_policy as ilp
    except Exception:  # noqa: BLE001
        return []
    role_allowed = seat.get("person_id") == OWNER or seat.get("gate") == "role"
    try:
        recs = ilp.stub_recommendations(
            seat.get("person_id"),
            role_allowed=role_allowed,
            db_path=rule_db_path,
        )
        nxt = ilp.operator_next_action(
            seat.get("person_id"),
            role_allowed=role_allowed,
            db_path=rule_db_path,
        )
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for rec in recs.get("recommendations") or []:
        if not isinstance(rec, dict):
            continue
        oid = str(rec.get("recommendation_id") or rec.get("stub_id") or "")
        if not oid:
            continue
        out.append(
            {
                "object_id": oid,
                "kind": "learning_policy",
                "title": rec.get("label") or oid,
                "who": None,
                "audience": "INTEL_SEAT",
                "priority": "P1",
                "status": rec.get("state") or "STUB",
                "business": "INTEL",
                "surface": "learning_policy",
                "capability": CAP_05,
                "href": rec.get("href") or "/api/intel/learning-policy",
                "open_href": rec.get("href") or "/intel-ops-pack",
                "invented": False,
                "auto_promote": False,
                "auto_execute": False,
                "live_rule": False,
            }
        )
    if out:
        return out
    if nxt.get("empty") is True:
        return []
    code = str(nxt.get("code") or "LEARNING")
    return [
        {
            "object_id": f"LP-{code}",
            "kind": "learning_policy",
            "title": nxt.get("label") or code,
            "who": None,
            "audience": "INTEL_SEAT",
            "priority": "P1",
            "status": code,
            "business": "INTEL",
            "surface": "learning_policy",
            "capability": CAP_05,
            "href": nxt.get("href") or "/api/intel/learning-policy",
            "open_href": "/intel-ops-pack",
            "invented": False,
            "auto_promote": False,
            "auto_execute": False,
            "live_rule": False,
        }
    ]


def _intel_candidates(
    *,
    seat: dict[str, Any],
    state_path=None,
    rule_db_path: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    items = _commissioning_rows(state_path=state_path)
    items.extend(
        _intel_connective_rows(operator_db=operator_db, eval_db=eval_db)
    )
    items.extend(_learning_policy_rows(seat, rule_db_path=rule_db_path))
    return _sort_connective(items)


def connective_cap_honesty(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = honesty_flags()
    nye = _needs_you_module()
    progress = {
        cr: (_cr_state(cr, catalog_db).get("cr_state") or "OPEN")
        for cr in nye.TARGET_CRS
    }
    return {
        "cap_intel_01": flags.get("cap_intel_01"),
        "cap_intel_05": flags.get("cap_intel_05"),
        "cr_05": flags.get("cr_05_state"),
        "cr_05_resolved": False,
        "cr_au": flags.get("cr_au_state"),
        "cr_au_resolved": False,
        "au_intel_02_wolf": AU_WOLF,
        "au_intel_02_wolf_started": False,
        "progress_core_crs": progress,
        "false_resolve_cr": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "auto_promote": False,
        "auto_execute": False,
    }


def needs_you_connective_strip(
    *,
    verified_person_id: str,
    state_path=None,
    db_path: Path | str | None = None,
    rule_db_path: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Intel-scoped Needs-You / connective / learning-policy projection.

    Owner sees the full Intel-scoped set. A non-Owner intel seat sees
    in-scope rows only. EMPTY honesty when none. Counts are the in-scope length.
    """
    del db_path  # pack asks db is not a Needs-You source
    seat = require_actor(verified_person_id)
    try:
        rows = _intel_candidates(
            seat=seat,
            state_path=state_path,
            rule_db_path=_resolve_rule_db(rule_db_path),
            operator_db=operator_db,
            eval_db=eval_db,
        )
    except Exception as exc:  # noqa: BLE001
        empty = _empty_connective(
            why=(
                "Intel Needs-You connective read failed "
                f"({exc}). Count stays EMPTY. No work invented."
            )
        )
        empty["seat"] = {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        }
        return empty
    visible = [row for row in rows if _in_scope_for_seat(row, seat)]
    projected = [_project_row(it) for it in visible]
    by_kind = {k: 0 for k in CONNECTIVE_KINDS}
    for it in visible:
        kind = str(it.get("kind") or "")
        if kind in by_kind:
            by_kind[kind] += 1
    empty = len(visible) == 0
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "run_id": CONNECTIVE_RUN_ID,
        "claim_id": CONNECTIVE_CLAIM_ID,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
            "sees_full_intel": seat.get("person_id") == OWNER,
        },
        "empty": empty,
        "count": len(visible),
        "by_kind": by_kind,
        "items": projected,
        "next_action": None if empty else _connective_next(visible[0]),
        "empty_message": (
            "No Intel-scoped Needs-You / connective / learning-policy rows "
            "in this seat's scope — EMPTY honesty."
            if empty
            else None
        ),
        "invented": False,
        "invented_count": False,
        "source": "intel_scoped_needs_you_connective_learning_policy",
        "kinds": list(CONNECTIVE_KINDS),
        "caps": connective_cap_honesty(catalog_db=catalog_db),
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "invented_haikal_human": False,
        "invented_devi_done": False,
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
        "duplicate_mutate_surface": False,
        "reuse_needs_you_depth": True,
        "false_resolve_cr": False,
        "why": (
            "Derived Intel-scoped commissioning, intel connective, and "
            "learning-policy rows. Owner sees the full Intel-scoped projection. "
            "A non-Owner intel seat sees only in-scope rows. Counts are the "
            "in-scope length. Empty is not invented work."
        ),
    }


def _find_intel_item(
    object_id: str,
    *,
    seat: dict[str, Any],
    state_path=None,
    rule_db_path: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any] | None:
    oid = (object_id or "").strip()
    for row in _intel_candidates(
        seat=seat,
        state_path=state_path,
        rule_db_path=rule_db_path,
        operator_db=operator_db,
        eval_db=eval_db,
    ):
        if str(row.get("object_id") or "") == oid:
            return row
    return None


def connective_item_detail(
    object_id: str,
    *,
    verified_person_id: str,
    state_path=None,
    rule_db_path: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Thin detail. Out of Intel seat scope is 403. Reuses existing handoffs."""
    seat = require_actor(verified_person_id)
    found = _find_intel_item(
        object_id,
        seat=seat,
        state_path=state_path,
        rule_db_path=_resolve_rule_db(rule_db_path),
        operator_db=operator_db,
        eval_db=eval_db,
    )
    if found is None:
        raise IntelOpsPackError(
            f"Intel Needs-You item '{object_id}' not found.",
            code="not_found",
            http_status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise IntelOpsPackError(
            "Intel Needs-You item is outside this seat's scope.",
            code="forbidden",
            http_status=403,
        )
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "schema": CONNECTIVE_SCHEMA_ID,
        "slice": CONNECTIVE_SLICE,
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        },
        "object": _project_row(found),
        "handoff": _handoff_block(found),
        "reuse_needs_you_depth": str(found.get("kind") or "") in CONNECTIVE_DEPTH_KINDS,
        "duplicate_mutate_surface": False,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
        "caps": connective_cap_honesty(catalog_db=catalog_db),
    }


def acknowledge_handoff(
    object_id: str,
    *,
    verified_person_id: str,
    note: str | None = None,
    state_path=None,
    events_path=None,
    rule_db_path: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Acknowledge via the existing Needs-You operator state.

    Intel connective and learning-policy rows keep their existing surfaces.
    This route does not open a second mutate store. Wrong-scope seats are refused.
    """
    seat = require_actor(verified_person_id)
    found = _find_intel_item(
        object_id,
        seat=seat,
        state_path=state_path,
        rule_db_path=_resolve_rule_db(rule_db_path),
        operator_db=operator_db,
        eval_db=eval_db,
    )
    if found is None:
        raise IntelOpsPackError(
            f"Intel Needs-You item '{object_id}' not found.",
            code="not_found",
            http_status=404,
        )
    if not _in_scope_for_seat(found, seat):
        raise IntelOpsPackError(
            "Intel Needs-You item is outside this seat's scope.",
            code="forbidden",
            http_status=403,
        )
    kind = str(found.get("kind") or "")
    if kind not in CONNECTIVE_DEPTH_KINDS:
        raise IntelOpsPackError(
            "Intel connective and learning-policy rows use their existing "
            "surfaces. This route does not open a second mutate surface "
            "and does not auto-promote or execute.",
            code="handoff_only",
            http_status=405,
        )
    nye = _needs_you_module()
    recorded = nye.record_operator_action(
        str(found.get("object_id") or ""),
        verified_person_id=None,
        kind="acknowledge",
        note=note,
        state_path=state_path,
        events_path=events_path,
        catalog_db=catalog_db,
        connective_actor=seat["person_id"],
    )
    strip = needs_you_connective_strip(
        verified_person_id=seat["person_id"],
        state_path=state_path,
        rule_db_path=rule_db_path,
        operator_db=operator_db,
        eval_db=eval_db,
        catalog_db=catalog_db,
    )
    return {
        "ok": True,
        "bound": CONNECTIVE_BOUND,
        "recorded": True,
        "action": "acknowledge",
        "object_id": found.get("object_id"),
        "seat": {
            "person_id": seat.get("person_id"),
            "seat": seat.get("seat"),
        },
        "handoff": _handoff_block(found),
        "reuse_needs_you_depth": True,
        "duplicate_mutate_surface": False,
        "event": recorded.get("event"),
        "needs_you_connective": strip,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "human_done": False,
        "commissioned": False,
        "cr_resolved": False,
        "auto_promote": False,
        "auto_execute": False,
        "live_rule": False,
        "caps": recorded.get("caps"),
        "message": (
            "Acknowledge recorded on the Needs-You operator state. "
            "No second mutate surface. staff_ready, PROVEN, READY, Haikal done, "
            "and Devi done stay uninvented. No auto-promote."
        ),
    }
