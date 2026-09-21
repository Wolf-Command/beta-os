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
"""
from __future__ import annotations

import json
import os
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

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


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
    flags = honesty_flags()
    return {
        "ok": True,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "person_id": seat["person_id"],
        "seat": seat,
        "today": today,
        "recall": recall,
        "queue": queue,
        "loop": {
            "ask": "/api/intel/ops-pack/ask",
            "recall": "/api/intel/ops-pack/recall",
            "queue": "/api/intel/ops-pack/queue",
            "note": "/api/intel/ops-pack/note",
            "approve_to_rule": "/api/intel/approve-to-rule",
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
        ],
        "refused": sorted(REFUSE_VIEWS.keys()),
        "auto_promote": False,
        "rule_execution": False,
        "money": False,
    }
