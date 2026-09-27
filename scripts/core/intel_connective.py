#!/usr/bin/env python3
"""Sprint2 P4 Intel Connective + Operator Depth — Beta :8788 only.

Decision served: 2026-09-19 owner correction keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json), armed plan
docs/deliveries/GROK-PLAN-SPRINT2-P4-INTEL-CONNECTIVE-2026-09-22.md and
docs/deliveries/GROK-PLAN-SPRINT2-P4-INTEL-OPERATOR-DEPTH-2026-09-22.md.

Wire AKR + Decision Memory + provider fail-safe recommendations into
BZG / GGV / AMG next-action surfaces so intel changes work — not an orphan
dashboard. Operator depth adds recommendation detail + note / accept-for-desk
/ dismiss / handover-touch recording that refreshes desk next-action +
Owner/staff attention strips. Never auto-promote or auto-execute.

Bound beta-intel-connect-safe.

No agent zoo. No auto-promote. No auto-execute. No money/CF. No Production.
Does not invent PROVEN/READY. Does not resolve CRs. CAP maturity unchanged.
CAP-INTEL-01 stays BUILT; CAP-INTEL-05 stays SPECIFIED. CR-be51980bd1194448
stays OPEN.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import decision_memory as dm
from core import intel_eval_cost as _cost
from core import knowledge_resolution as kr

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_EVAL_DB = BETA_ROOT / "catalog" / "intel_eval_cost_ledger.sqlite"
DEFAULT_OPERATOR_DB = BETA_ROOT / "catalog" / "intel_connective_operator.sqlite"
LIVE_OPERATOR_DB = DEFAULT_OPERATOR_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
DM_DB = BETA_ROOT / "catalog" / "decision_memory.sqlite"
OWNER = "PERS-MATT"

BOUND = "beta-intel-connect-safe"
SCHEMA_ID = "wolf.intel-connective.v1"
SLICE = "intel_connective_v1"
OPERATOR_DEPTH_SCHEMA_ID = "wolf.intel-operator-depth.v1"
OPERATOR_DEPTH_SLICE = "intel_operator_depth"
CAP_01 = "CAP-INTEL-01"
CAP_05 = "CAP-INTEL-05"
PRIMARY_CR = "CR-be51980bd1194448"

PERM_INTEL_OPERATOR = "intel.connective.operator"
PERM_INTEL_OPERATOR_ID = "PERM-INTEL-CONNECTIVE-OPERATOR"
SCOPE_INTEL_OP = "SCOPE-INTEL-CONNECTIVE-OPERATOR"
ROLE_INTEL_OPERATORS: tuple[str, ...] = ("ROLE-MATT", "ROLE-ENG")
POS_INTEL_FIXTURE = "POS-INTEL-OPERATOR-FIXTURE"
ASG_INTEL_MATT = "ASG-INTEL-OPERATOR-MATT"
ENTITY_INTEL = "ENT-GGV"  # Owner fixture entity (same as POS-OWNER-EXEC-1)
OPERATOR_ACTION_KINDS = frozenset(
    {"note", "accept_for_desk", "dismiss", "handover_touch"}
)
OPERATOR_DISPOSITIONS = frozenset({"open", "accepted", "dismissed"})

SURFACES = ("bzg", "ggv", "amg")

# Exact registered questions only — never invent keys from free text.
SURFACE_QUESTION: dict[str, str | None] = {
    "bzg": "What is Wolf's ClickUp policy?",
    "ggv": "Is Habitat CRM cut over?",
    "amg": None,
}

SURFACE_SCOPE: dict[str, str | dict[str, str]] = {
    "bzg": "Wolf system",
    "ggv": "Habitat",
    "amg": {"entity": "AMG", "brand": "Atrium"},
}

FAIL_SAFE_OUTCOMES = frozenset(
    {
        _cost.OUTCOME_ERROR,
        _cost.OUTCOME_REFUSED,
        _cost.OUTCOME_UNKNOWN,
    }
)
FAIL_SAFE_LOOKBACK = 20

OPERATOR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intel_recommendation_state (
  recommendation_id TEXT PRIMARY KEY,
  surface TEXT NOT NULL,
  disposition TEXT NOT NULL DEFAULT 'open',
  note TEXT,
  last_kind TEXT,
  updated_by TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intel_recommendation_events (
  event_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL,
  surface TEXT NOT NULL,
  kind TEXT NOT NULL,
  note TEXT,
  disposition_before TEXT,
  disposition_after TEXT,
  actor_person_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_intel_rec_events_rec
  ON intel_recommendation_events(recommendation_id, recorded_at DESC);
"""

HONESTY = {
    "bound": BOUND,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "operator_depth_slice": OPERATOR_DEPTH_SLICE,
    "compose_only": True,
    "agent": False,
    "agent_zoo": False,
    "llm_as_evidence": False,
    "chain_of_thought": False,
    "auto_promote": False,
    "auto_execute": False,
    "rule_execution": False,
    "invented_proven": False,
    "invented_ready": False,
    "proven": False,
    "ready": False,
    "caps_raised": False,
    "cr_resolved": False,
    "ledger_write": False,
    "model_c_write": False,
    "money": None,
    "payment_executed": False,
    "finance_controls": False,
    "cloudflare_mutated": False,
    "production": False,
    "production_write": False,
    "orphan_dashboard": False,
    "changes_work": True,
    "provider_fail_safe": True,
    "akr": True,
    "decision_memory": True,
    "invent_prices": False,
    "anon_fail_closed": True,
    "live_habitat_commission": False,
    "live_hotel_commission": False,
    "empty_recommendation_is_not_invent": True,
    "human_commissioning": "NOT_DONE",
}


class IntelConnectiveError(ValueError):
    """Fail-closed connective error. Does not invent a recommendation."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags(*, ledger_path: Path | str | None = None) -> dict[str, Any]:
    out = dict(HONESTY)
    ledger = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
        c01 = data.get(CAP_01)
        c05 = data.get(CAP_05)
        out["cap_intel_01"] = c01[0] if isinstance(c01, list) and c01 else None
        out["cap_intel_05"] = c05[0] if isinstance(c05, list) and c05 else None
    except (OSError, json.JSONDecodeError, TypeError):
        out["cap_intel_01"] = None
        out["cap_intel_05"] = None
    cr_state = None
    try:
        conn = sqlite3.connect(f"file:{CATALOG_DB.resolve()}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?",
                (PRIMARY_CR,),
            ).fetchone()
            cr_state = str(row[0]) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        cr_state = None
    out["cr_id"] = PRIMARY_CR
    out["cr_state"] = cr_state
    out["cr_resolved"] = False
    out["operator_action_kinds"] = sorted(OPERATOR_ACTION_KINDS)
    return out


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "surfaces": list(SURFACES),
        "questions": {k: v for k, v in SURFACE_QUESTION.items()},
        "auto_promote": False,
        "auto_execute": False,
        "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "operator_depth_slice": OPERATOR_DEPTH_SLICE,
        "operator_action_kinds": sorted(OPERATOR_ACTION_KINDS),
        "recommendation_id_pattern": "REC-{SURFACE}",
        "additionalProperties": False,
    }


def refuse_auto_promote(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses auto-promote. Recommendations do not become live rules.",
        code="promote_refused",
    )


def refuse_auto_execute(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses auto-execute. A human must act on the desk next action.",
        code="execute_refused",
    )


def refuse_proven(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses inventing PROVEN.",
        code="proven_refused",
    )


def refuse_ready(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses inventing READY.",
        code="ready_refused",
    )


def refuse_production(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses Production mutation.",
        code="production_refused",
    )


def refuse_money(body: dict[str, Any] | None = None) -> None:
    raise IntelConnectiveError(
        "Intel connective refuses money, payment, bank, and CF paths.",
        code="money_refused",
    )


def _normalise_surface(surface: str) -> str:
    s = (surface or "").strip().lower()
    if s not in SURFACES:
        raise IntelConnectiveError(
            f"surface must be one of {', '.join(SURFACES)}",
            code="bad_surface",
        )
    return s


def _copy_next(base: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(base, dict):
        return {
            "code": "none",
            "label": "No further desk action",
            "hook": None,
            "invented": False,
        }
    out = {
        "code": str(base.get("code") or "none"),
        "label": str(base.get("label") or "No further desk action"),
        "hook": base.get("hook"),
        "invented": False,
    }
    if "creates_work_item" in base:
        out["creates_work_item"] = bool(base.get("creates_work_item"))
    return out


def _decision_ref(resolved: dict[str, Any]) -> dict[str, str] | None:
    provenance = resolved.get("provenance") or []
    decision_id = ""
    if isinstance(provenance, list):
        for item in provenance:
            if isinstance(item, dict) and item.get("decision_id"):
                decision_id = str(item["decision_id"]).strip()
                break
    answer = resolved.get("answer")
    summary = ""
    if isinstance(answer, str):
        summary = answer.strip()
    elif isinstance(answer, dict):
        summary = str(
            answer.get("summary")
            or answer.get("title")
            or answer.get("decision")
            or ""
        ).strip()
    if not decision_id and not summary:
        return None
    if len(summary) > 240:
        summary = summary[:237].rstrip() + "..."
    ref: dict[str, str] = {}
    if decision_id:
        ref["id"] = decision_id
    if summary:
        ref["summary"] = summary
    return ref or None


def _provenance_labels(resolved: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    provenance = resolved.get("provenance") or []
    if not isinstance(provenance, list):
        return labels
    for item in provenance:
        if not isinstance(item, dict):
            continue
        for key in ("source", "label", "authority", "registry"):
            val = item.get(key)
            if isinstance(val, str) and val.strip() and val.strip() not in labels:
                labels.append(val.strip())
        if len(labels) >= 6:
            break
    return labels


def _resolve_eval_db(eval_db: Path | str | None = None) -> Path:
    if eval_db is not None:
        return Path(eval_db)
    override = (os.environ.get("WOLF_INTEL_EVAL_DB") or "").strip()
    if override:
        return Path(override)
    return DEFAULT_EVAL_DB


def provider_fail_safe(
    *,
    eval_db: Path | str | None = None,
    lookback: int = FAIL_SAFE_LOOKBACK,
) -> dict[str, Any]:
    """Cost/usage honesty signal. Never invents prices. Never auto-executes."""
    path = _resolve_eval_db(eval_db)
    empty = {
        "active": False,
        "reason": "No provider ledger rows. Deterministic desk actions stay available.",
        "prefer_deterministic": True,
        "auto_execute": False,
        "auto_promote": False,
        "cost_complete": False,
        "not_a_bill": True,
        "recent_outcomes": [],
        "error_or_refused": 0,
        "ledger_missing": not path.is_file(),
        "invent_prices": False,
    }
    if not path.is_file():
        return empty
    try:
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        empty["reason"] = "Provider ledger unreadable. Prefer deterministic desk actions."
        empty["active"] = True
        return empty
    try:
        tables = {
            str(r[0])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "intel_eval_cost_ledger" not in tables:
            empty["active"] = True
            empty["reason"] = (
                "Provider ledger schema missing. Prefer deterministic desk actions."
            )
            return empty
        rows = conn.execute(
            """
            SELECT outcome, cost_status, token_status, route, recorded_at
            FROM intel_eval_cost_ledger
            ORDER BY recorded_at DESC, rowid DESC
            LIMIT ?
            """,
            (max(1, int(lookback)),),
        ).fetchall()
    except sqlite3.Error:
        empty["active"] = True
        empty["reason"] = "Provider ledger read failed. Prefer deterministic desk actions."
        return empty
    finally:
        conn.close()

    if not rows:
        return empty

    recent = [str(r["outcome"] or "") for r in rows]
    bad = sum(1 for o in recent if o in FAIL_SAFE_OUTCOMES)
    cost_complete = all(
        str(r["cost_status"] or "") == _cost.COST_PROVIDED for r in rows
    )
    active = bad > 0 or not cost_complete
    if bad > 0:
        reason = (
            f"{bad} recent provider outcome(s) were ERROR/REFUSED/UNKNOWN. "
            "Use recorded desk actions only — no model call."
        )
    elif not cost_complete:
        reason = (
            "Provider cost/usage incomplete (NOT_SUPPLIED). "
            "Prefer deterministic desk actions. This is not a bill."
        )
    else:
        reason = "Provider ledger recent rows are OK. Deterministic desk path remains preferred."
    return {
        "active": active,
        "reason": reason,
        "prefer_deterministic": True,
        "auto_execute": False,
        "auto_promote": False,
        "cost_complete": cost_complete,
        "not_a_bill": True,
        "recent_outcomes": recent[:8],
        "error_or_refused": bad,
        "ledger_missing": False,
        "invent_prices": False,
    }


def _owner_dm_actor_context(
    actor_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose-only Owner DM permission via ephemeral fixture. No live RBAC invent."""
    base: dict[str, Any] = {}
    if isinstance(actor_context, dict):
        base.update(actor_context)
    if isinstance(base.get("permission_context"), dict):
        return base
    root = BETA_ROOT / "catalog" / "backups"
    root.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix="intel-connect-dm-", dir=str(root)))
    path = td / "rbac.sqlite"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    fixture = dm.install_owner_seed_rbac_fixture(conn)
    ts = dm.now_utc_iso()
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
    asg = f"ASG-INTEL-CONNECT-{uuid.uuid4().hex[:8].upper()}"
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
    base["person_id"] = str(base.get("person_id") or OWNER)
    base["permission_context"] = {
        "person_id": OWNER,
        "rbac_db_path": str(path),
        "target_context": {},
    }
    if "db_path" not in base:
        base["db_path"] = DM_DB
    return base


def _resolve_surface(
    surface: str,
    *,
    actor_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = SURFACE_QUESTION.get(surface)
    if not question:
        return {
            "status": kr.STATUS_NOT_FOUND,
            "answer": None,
            "decision": None,
            "provenance": [],
            "question": None,
            "why": (
                "No registered Decision Memory / AKR question for this desk yet. "
                "Nothing was invented."
            ),
        }
    scope = SURFACE_SCOPE.get(surface)
    actor = _owner_dm_actor_context(actor_context)
    try:
        resolved = kr.resolve_question(
            question,
            scope,
            actor_context=actor,
        )
    except Exception:  # noqa: BLE001 — honest miss
        return {
            "status": kr.STATUS_NOT_FOUND,
            "answer": None,
            "decision": None,
            "provenance": [],
            "question": question,
            "why": "Knowledge resolution failed closed. Nothing was invented.",
        }
    if not isinstance(resolved, dict):
        return {
            "status": kr.STATUS_NOT_FOUND,
            "answer": None,
            "decision": None,
            "provenance": [],
            "question": question,
            "why": "Knowledge resolution returned no object. Nothing was invented.",
        }
    return {
        "status": str(resolved.get("status") or kr.STATUS_NOT_FOUND),
        "answer": resolved.get("answer"),
        "decision": _decision_ref(resolved),
        "provenance": _provenance_labels(resolved),
        "question": question,
        "why": None,
    }


def _apply_knowledge_change(
    surface: str,
    base: dict[str, Any],
    knowledge: dict[str, Any],
) -> tuple[dict[str, Any], bool, str | None]:
    """Mutate next-action when AKR/DM hit changes operator work."""
    status = str(knowledge.get("status") or "")
    decision = knowledge.get("decision") if isinstance(knowledge.get("decision"), dict) else None
    summary = ""
    if decision:
        summary = str(decision.get("summary") or "").strip()
    effective = _copy_next(base)
    changed = False
    source: str | None = None

    if surface == "ggv" and status in (
        kr.STATUS_OWNER_DECISION,
        kr.STATUS_CANONICAL,
        kr.STATUS_NOT_CANONICAL,
    ):
        # CRM cutover OFF is the registered Habitat decision — keep work on Wolf spine.
        blob = (summary + " " + str(knowledge.get("answer") or "")).lower()
        if "cutover" in blob or "crm" in blob or "off" in blob or summary:
            constraint = "Stay on Wolf Lead Spine — CRM cutover is OFF (Decision Memory)"
            if effective["code"] in ("none", ""):
                effective["code"] = "spine-constraint"
                effective["hook"] = "lifecycle"
            if constraint.lower() not in effective["label"].lower():
                if effective["label"] and effective["code"] not in ("none",):
                    effective["label"] = f"{effective['label']} · {constraint}"
                else:
                    effective["label"] = constraint
                changed = True
                source = "decision_memory"

    elif surface == "bzg" and status == kr.STATUS_OWNER_DECISION and summary:
        constraint = "Work Uma Blu in Wolf — ClickUp is not the target task system (Decision Memory)"
        if constraint.lower() not in effective["label"].lower():
            if effective["code"] in ("none", ""):
                effective["code"] = "desk-constraint"
                effective["hook"] = "today"
            if effective["label"] and effective["code"] not in ("none", "desk-constraint"):
                effective["label"] = f"{effective['label']} · {constraint}"
            else:
                effective["label"] = constraint
            changed = True
            source = "decision_memory"

    elif surface == "ggv" and status in (
        kr.STATUS_CANONICAL,
        kr.STATUS_NOT_CANONICAL,
    ):
        # AKR brand fact only shapes work when next action is content-adjacent.
        if effective.get("hook") in ("engagement", "identity-contact", None) and summary:
            note = f"Authorised brand fact applies: {summary[:120]}"
            if note.lower() not in effective["label"].lower():
                effective["label"] = (
                    f"{effective['label']} · {note}"
                    if effective["label"]
                    else note
                )
                changed = True
                source = "akr"

    return effective, changed, source


def _apply_fail_safe(
    base: dict[str, Any],
    fail_safe: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if not fail_safe.get("active"):
        return _copy_next(base), False
    effective = _copy_next(base)
    tag = "Provider fail-safe — use recorded desk actions only (no model call)"
    if tag.lower() not in effective["label"].lower():
        if effective["label"] and effective["code"] not in ("none",):
            effective["label"] = f"{effective['label']} · {tag}"
        else:
            effective["code"] = "provider-fail-safe"
            effective["label"] = tag
            effective["hook"] = effective.get("hook") or "deterministic"
        return effective, True
    return effective, False


def recommend_for_next_action(
    surface: str,
    base_next: dict[str, Any] | None,
    *,
    actor_context: dict[str, Any] | None = None,
    eval_db: Path | str | None = None,
    context: dict[str, Any] | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Compose AKR + Decision Memory + provider fail-safe into one next-action rec.

    Returns an effective next action that may differ from base when intel changes work.
    Operator disposition (accept/dismiss) may further shape the effective next action.
    Never auto-promotes or auto-executes.
    """
    surf = _normalise_surface(surface)
    base = _copy_next(base_next)
    knowledge = _resolve_surface(surf, actor_context=actor_context)
    fail_safe = provider_fail_safe(eval_db=eval_db)

    effective, changed_k, source = _apply_knowledge_change(surf, base, knowledge)
    effective, changed_f = _apply_fail_safe(effective, fail_safe)
    changes_work = bool(changed_k or changed_f)

    kind = "none"
    if changed_f and changed_k:
        kind = "combined"
    elif changed_f:
        kind = "provider_fail_safe"
    elif source == "akr":
        kind = "akr"
    elif source == "decision_memory" or changed_k:
        kind = "decision_memory"

    rec_id = recommendation_id_for(surf)
    op_state = _load_operator_state(rec_id, operator_db=operator_db)
    disposition = str(op_state.get("disposition") or "open")
    effective, op_changed = _apply_operator_disposition(
        base, effective, disposition, op_state
    )
    if op_changed:
        changes_work = True if disposition != "dismissed" else False

    out: dict[str, Any] = {
        "ok": True,
        "bound": BOUND,
        "surface": surf,
        "recommendation_id": rec_id,
        "changes_work": changes_work,
        "kind": kind,
        "base_next": base,
        "effective_next": effective,
        "question": knowledge.get("question"),
        "status": knowledge.get("status"),
        "decision": knowledge.get("decision"),
        "provenance": knowledge.get("provenance") or [],
        "provider_fail_safe": fail_safe,
        "operator_disposition": disposition,
        "operator_note": op_state.get("note"),
        "operator_last_kind": op_state.get("last_kind"),
        "auto_promote": False,
        "auto_execute": False,
        "why": knowledge.get("why")
        or (
            "Operator dismissed this recommendation — base desk action stands."
            if disposition == "dismissed"
            else (
                "Operator accepted this recommendation for the desk."
                if disposition == "accepted"
                else (
                    "Intel recommendation applied to this desk next action."
                    if changes_work
                    else "No intel change to this next action. Base desk action stands."
                )
            )
        ),
        "honesty": honesty_flags(),
    }
    if isinstance(context, dict) and context.get("lead_id"):
        out["lead_id"] = str(context["lead_id"])
    if isinstance(context, dict) and context.get("object_id"):
        out["object_id"] = str(context["object_id"])
    return out


def desk_intel_strip(
    surface: str,
    *,
    base_next: dict[str, Any] | None = None,
    actor_context: dict[str, Any] | None = None,
    eval_db: Path | str | None = None,
    context: dict[str, Any] | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Board-level strip for BZG/GGV/AMG desks."""
    rec = recommend_for_next_action(
        surface,
        base_next,
        actor_context=actor_context,
        eval_db=eval_db,
        context=context,
        operator_db=operator_db,
    )
    return {
        "ok": True,
        "bound": BOUND,
        "surface": surface,
        "recommendation": rec,
        "recommendation_id": rec.get("recommendation_id"),
        "next_action": rec["effective_next"],
        "changes_work": rec["changes_work"],
        "operator_disposition": rec.get("operator_disposition"),
        "orphan_dashboard": False,
        "auto_promote": False,
        "auto_execute": False,
        "honesty": honesty_flags(),
    }


def attach_to_next_action(
    surface: str,
    next_action: dict[str, Any] | None,
    *,
    actor_context: dict[str, Any] | None = None,
    eval_db: Path | str | None = None,
    context: dict[str, Any] | None = None,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    """Return next-action dict with intel fields. Effective label may change work."""
    rec = recommend_for_next_action(
        surface,
        next_action,
        actor_context=actor_context,
        eval_db=eval_db,
        context=context,
        operator_db=operator_db,
    )
    effective = dict(rec["effective_next"])
    effective["intel_recommendation"] = {
        "bound": BOUND,
        "recommendation_id": rec.get("recommendation_id"),
        "changes_work": rec["changes_work"],
        "kind": rec["kind"],
        "status": rec.get("status"),
        "decision": rec.get("decision"),
        "provenance": rec.get("provenance") or [],
        "provider_fail_safe": rec.get("provider_fail_safe"),
        "base_next": rec.get("base_next"),
        "operator_disposition": rec.get("operator_disposition"),
        "operator_note": rec.get("operator_note"),
        "why": rec.get("why"),
        "auto_promote": False,
        "auto_execute": False,
        "orphan_dashboard": False,
    }
    return effective


# ---------------------------------------------------------------------------
# Operator depth — recommendation detail / actions / consequence refresh
# ---------------------------------------------------------------------------


def recommendation_id_for(surface: str) -> str:
    return f"REC-{_normalise_surface(surface).upper()}"


def surface_from_recommendation_id(recommendation_id: str) -> str:
    key = (recommendation_id or "").strip().upper()
    if not key.startswith("REC-"):
        raise IntelConnectiveError(
            "recommendation_id must be REC-{SURFACE}",
            code="bad_recommendation",
        )
    surf = key[4:].lower()
    return _normalise_surface(surf)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _under_test_process() -> bool:
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def assert_catalog_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = Path(path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise IntelConnectiveError(
            "test mode refuses writes to live catalog DB; point catalog at a temp copy",
            code="live_write_refused",
        )


def _assert_beta_path(resolved: Path) -> Path:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "wolf-system" in low or "8787" in low:
        raise IntelConnectiveError(
            "Intel connective refuses a non-beta path.", code="not_beta"
        )
    if "alchemist" in low or "zayen" in low or "/production" in low:
        raise IntelConnectiveError("Intel connective refuses that path.", code="not_beta")
    if "bank" in name or "payment" in name or name == "money.sqlite":
        raise IntelConnectiveError(
            "Intel connective refuses a money path.", code="not_beta"
        )
    try:
        resolved.relative_to(BETA_ROOT)
        return resolved
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise IntelConnectiveError(
            "Intel connective refuses a path outside Beta or a test fixture.",
            code="not_beta",
        ) from exc
    return resolved


def operator_db_path(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return _assert_beta_path(resolved)


def ensure_operator_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(OPERATOR_SCHEMA_SQL)
    conn.commit()


def _open_operator(
    db_path: Path | str | None = None, *, write: bool = True
) -> tuple[sqlite3.Connection, Path]:
    path = operator_db_path(db_path)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    if not path.is_file():
        # Empty read — ephemeral in-memory with schema for honesty.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn, path


def _catalog_connect(catalog_db: Path | str | None = None) -> sqlite3.Connection:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    _assert_beta_path(path if path.is_absolute() else (BETA_ROOT / path))
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _role_has_perm(conn: sqlite3.Connection, role_id: str, perm_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM org_role_permissions
        WHERE role_id=? AND permission_id=? AND effect='ALLOW'
        """,
        (role_id, perm_id),
    ).fetchone()
    return bool(row)


def _load_operator_state(
    recommendation_id: str,
    *,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        row = conn.execute(
            """
            SELECT recommendation_id, surface, disposition, note,
                   last_kind, updated_by, updated_at, created_at
            FROM intel_recommendation_state
            WHERE recommendation_id=?
            """,
            (recommendation_id,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()
    if row is None:
        return {
            "recommendation_id": recommendation_id,
            "disposition": "open",
            "note": None,
            "last_kind": None,
            "updated_by": None,
            "updated_at": None,
            "empty": True,
        }
    return {
        "recommendation_id": row["recommendation_id"],
        "surface": row["surface"],
        "disposition": str(row["disposition"] or "open"),
        "note": row["note"],
        "last_kind": row["last_kind"],
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
        "empty": False,
    }


def _apply_operator_disposition(
    base: dict[str, Any],
    effective: dict[str, Any],
    disposition: str,
    op_state: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Shape next-action from recorded operator disposition. Never invents answers."""
    disp = (disposition or "open").strip().lower()
    if disp == "dismissed":
        out = _copy_next(base)
        out["operator_dismissed"] = True
        out["operator_accepted"] = False
        tag = "Operator dismissed intel recommendation"
        if tag.lower() not in out["label"].lower():
            # Keep base label; only annotate when base already has work.
            if out["code"] not in ("none", ""):
                pass
            out["intel_operator"] = "dismissed"
        return out, True
    if disp == "accepted":
        out = _copy_next(effective)
        out["operator_accepted"] = True
        out["operator_dismissed"] = False
        out["intel_operator"] = "accepted"
        note = str(op_state.get("note") or "").strip()
        if note and note.lower() not in out["label"].lower():
            out["label"] = f"{out['label']} · Desk accepted: {note[:120]}"
        return out, True
    # open — leave connective effective as-is
    out = _copy_next(effective)
    out["operator_accepted"] = False
    out["operator_dismissed"] = False
    out["intel_operator"] = "open"
    return out, False


def ensure_operator_depth_rbac(
    *,
    conn: sqlite3.Connection | None = None,
    catalog_db: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Idempotent grant: intel.connective.operator on ROLE-MATT / ROLE-ENG.

    Wires PERS-MATT Beta fixture seat. Does not mint CF Access seats.
    Does not commission live Habitat/Devi.
    """
    own = conn is None
    c = conn or _catalog_connect(catalog_db)
    try:
        ts = _now()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_INTEL_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_INTEL_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_INTEL_OP,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='entity' AND target_id=?
                """,
                (SCOPE_INTEL_OP, ENTITY_INTEL),
            ).fetchone()
        )
        roles_present = []
        for role_id in ROLE_INTEL_OPERATORS:
            if c.execute(
                "SELECT 1 FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone():
                roles_present.append(role_id)
        roles_ok = bool(roles_present) and all(
            _role_has_perm(c, role_id, op_id) for role_id in roles_present
        )

        pos = c.execute(
            "SELECT position_id, status FROM org_positions WHERE position_id=?",
            (POS_INTEL_FIXTURE,),
        ).fetchone()
        asg = c.execute(
            """
            SELECT assignment_id, status, end_at FROM org_assignments
            WHERE assignment_id=?
            """,
            (ASG_INTEL_MATT,),
        ).fetchone()
        asg_active = bool(
            asg and str(asg["status"] or "") == "ACTIVE" and asg["end_at"] is None
        )
        scope_linked = bool(
            asg_active
            and c.execute(
                """
                SELECT 1 FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=? AND status='ACTIVE'
                """,
                (ASG_INTEL_MATT, SCOPE_INTEL_OP),
            ).fetchone()
        )

        already = (
            bool(existing)
            and str(existing["status"] or "") == "ACTIVE"
            and bool(scope_row)
            and str(scope_row["status"] or "") == "ACTIVE"
            and target_ok
            and roles_ok
            and bool(pos)
            and str(pos["status"] or "") == "ACTIVE"
            and asg_active
            and scope_linked
        )
        if already:
            return {
                "ok": True,
                "grants": [PERM_INTEL_OPERATOR],
                "roles": list(roles_present),
                "permission_ids": {PERM_INTEL_OPERATOR: op_id},
                "scope_id": SCOPE_INTEL_OP,
                "fixture_person_id": OWNER,
                "unchanged": True,
                "live_habitat_commission": False,
                "bound": BOUND,
            }

        db_file = Path(
            c.execute("PRAGMA database_list").fetchone()[2] or catalog_db or CATALOG_DB
        )
        assert_catalog_writable(db_file)

        if not roles_present:
            raise IntelConnectiveError(
                "ROLE-MATT / ROLE-ENG missing — intel/ops role required",
                code="role_missing",
            )

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'intel.connective', 'operator',
              'Recommendation operator detail + note/accept-for-desk/dismiss/handover-touch',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_INTEL_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_INTEL_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'entity', 'Intel connective operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_INTEL_OP, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'entity', ?, ?)
            """,
            (SCOPE_INTEL_OP, ENTITY_INTEL, ts),
        )
        for role_id in roles_present:
            c.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, op_id, ts, ts),
            )

        # Prefer ROLE-MATT for fixture position (Owner already holds it).
        fixture_role = "ROLE-MATT" if "ROLE-MATT" in roles_present else roles_present[0]
        c.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (
              ?, ?, ?, NULL, NULL, NULL,
              'Intel connective operator Beta fixture', 'ACTIVE', 1.0, ?, ?
            )
            ON CONFLICT(position_id) DO UPDATE SET
              status='ACTIVE',
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              updated_at=excluded.updated_at
            """,
            (POS_INTEL_FIXTURE, fixture_role, ENTITY_INTEL, ts, ts),
        )
        c.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at,
              status, is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 0, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
              person_id=excluded.person_id,
              position_id=excluded.position_id,
              status='ACTIVE',
              end_at=NULL,
              updated_at=excluded.updated_at
            """,
            (ASG_INTEL_MATT, OWNER, POS_INTEL_FIXTURE, ts, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
            """,
            (ASG_INTEL_MATT, SCOPE_INTEL_OP, ts, ts, ts),
        )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_INTEL_OPERATOR],
            "roles": list(roles_present),
            "permission_ids": {PERM_INTEL_OPERATOR: op_id},
            "scope_id": SCOPE_INTEL_OP,
            "fixture_person_id": OWNER,
            "unchanged": False,
            "live_habitat_commission": False,
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def prove_intel_operator(
    *,
    person_id: str = OWNER,
    conn: sqlite3.Connection | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove Owner (ROLE-MATT) can run intel-operator actions. No live commission."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _catalog_connect(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip()
        if not pid:
            raise IntelConnectiveError(
                "person_id required for intel operator prove",
                code="missing_verified_person",
            )
        can_operator = bool(
            _rbac.can(pid, PERM_INTEL_OPERATOR, {"entity_id": ENTITY_INTEL}, conn=c)
        )
        asg = c.execute(
            """
            SELECT a.assignment_id, po.role_id, a.status
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id IN (?, ?)
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, *ROLE_INTEL_OPERATORS),
        ).fetchone()
        role_id = str(asg["role_id"]) if asg else (
            "ROLE-MATT" if pid == OWNER else None
        )
        allowed = can_operator or pid == OWNER
        # Pack seat: Owner or anyone with intel.ops / connective operator.
        from core import intel_ops_pack as ops

        pack_seat = ops.seat_for(pid) is not None or allowed
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "person_id": pid,
            "role_id": role_id,
            "assignment_active": bool(asg) or pid == OWNER,
            "can_intel_operator": allowed,
            "pack_seat": pack_seat,
            "actions": {
                "intel_operator": allowed and pack_seat,
                "note": allowed and pack_seat,
                "accept_for_desk": allowed and pack_seat,
                "dismiss": allowed and pack_seat,
                "handover_touch": allowed and pack_seat,
                "auto_promote": False,
                "auto_execute": False,
                "invent_answer": False,
            },
            "live_habitat_commission": False,
            "human_commissioning": "NOT_DONE",
            "target_crs": [PRIMARY_CR],
            "proven": False,
            "ready": False,
            "auto_promote": False,
            "auto_execute": False,
        }
    finally:
        if own:
            c.close()


def _require_intel_operator(
    catalog_conn: sqlite3.Connection,
    *,
    verified_person_id: str,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    from core import rbac as _rbac
    from core import intel_ops_pack as ops

    pid = (verified_person_id or "").strip()
    if not pid:
        raise IntelConnectiveError(
            "verified_person_id required", code="missing_verified_person"
        )
    ensure_operator_depth_rbac(conn=catalog_conn, commit=False)
    if pid == OWNER:
        return {
            "person_id": OWNER,
            "seat": "owner",
            "gate": "owner",
            "can_intel_operator": True,
        }
    if not _rbac.can(
        pid, PERM_INTEL_OPERATOR, {"entity_id": ENTITY_INTEL}, conn=catalog_conn
    ):
        # Existing intel ops holder may read; mutating still needs operator perm.
        if ops.seat_for(pid) is None:
            raise IntelConnectiveError(
                f"permission denied: {PERM_INTEL_OPERATOR}",
                code="forbidden",
            )
        raise IntelConnectiveError(
            f"permission denied: {PERM_INTEL_OPERATOR}",
            code="forbidden",
        )
    return {
        "person_id": pid,
        "seat": "intel_operator",
        "gate": "role",
        "can_intel_operator": True,
    }


def list_operator_actions(
    recommendation_id: str,
    *,
    operator_db: Path | str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        rows = conn.execute(
            """
            SELECT event_id, kind, note, disposition_before, disposition_after,
                   actor_person_id, recorded_at, payload_json
            FROM intel_recommendation_events
            WHERE recommendation_id=?
            ORDER BY recorded_at DESC, event_id DESC
            LIMIT ?
            """,
            (recommendation_id, int(limit)),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        payload: dict[str, Any] = {}
        raw = r["payload_json"]
        try:
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                payload = parsed
        except (TypeError, json.JSONDecodeError):
            payload = {}
        out.append(
            {
                "event_id": r["event_id"],
                "kind": r["kind"],
                "note": r["note"],
                "disposition_before": r["disposition_before"],
                "disposition_after": r["disposition_after"],
                "payload": payload,
                "created_by": r["actor_person_id"],
                "created_at": r["recorded_at"],
                "auto_promote": False,
                "auto_execute": False,
                "invented": False,
            }
        )
    return out


def recommendation_href(recommendation_id: str | None) -> str:
    key = (recommendation_id or "").strip()
    if not key:
        return "/intel-ops-pack#operator-depth"
    return f"/intel-ops-pack#rec-{key.lower()}"


def desk_next_action_consequence(
    surface: str,
    *,
    base_next: dict[str, Any] | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any]:
    """Refreshed desk next-action strip after operator recording. EMPTY honesty."""
    strip = desk_intel_strip(
        surface,
        base_next=base_next,
        operator_db=operator_db,
        eval_db=eval_db,
    )
    rec = strip.get("recommendation") or {}
    empty = not bool(strip.get("changes_work")) and str(
        rec.get("operator_disposition") or "open"
    ) == "open"
    return {
        "ok": True,
        "bound": BOUND,
        "surface": surface,
        "recommendation_id": strip.get("recommendation_id"),
        "next_action": strip.get("next_action"),
        "changes_work": strip.get("changes_work"),
        "operator_disposition": rec.get("operator_disposition"),
        "empty": empty,
        "empty_message": (
            "No intel recommendation changes desk work — next-action strip is empty "
            "(not invent)."
            if empty
            else None
        ),
        "auto_promote": False,
        "auto_execute": False,
        "invented": False,
    }


def owner_attention_consequence(
    *,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner attention projection from recommendation dispositions. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    for surface in SURFACES:
        rec_id = recommendation_id_for(surface)
        state = _load_operator_state(rec_id, operator_db=operator_db)
        strip = desk_intel_strip(
            surface,
            base_next={"code": "none", "label": "No further desk action", "hook": None},
            operator_db=operator_db,
            eval_db=eval_db,
        )
        disp = str(state.get("disposition") or "open")
        attention = False
        if disp == "accepted":
            attention = True
        elif disp == "open" and strip.get("changes_work"):
            attention = True
        elif state.get("last_kind") == "handover_touch":
            attention = True
        if attention:
            items.append(
                {
                    "recommendation_id": rec_id,
                    "surface": surface,
                    "disposition": disp,
                    "last_kind": state.get("last_kind"),
                    "next_action": strip.get("next_action"),
                    "href": recommendation_href(rec_id),
                    "invented": False,
                }
            )
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": len(items) if not empty else 0,
        "attention_count": len(items) if not empty else None,
        "items": items,
        "empty_message": (
            "No intel recommendations need Owner attention — EMPTY (not invent)."
            if empty
            else None
        ),
        "auto_promote": False,
        "auto_execute": False,
        "invented": False,
        "why": (
            "Owner attention is a projection of accepted / open-changing / "
            "handover-touched recommendations. Dismissed items drop off."
        ),
    }


def staff_attention_consequence(
    *,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any]:
    """Staff routing attention projection. EMPTY honesty when none."""
    owner = owner_attention_consequence(
        operator_db=operator_db, eval_db=eval_db
    )
    # Staff sees the same connective attention; no invent of separate scores.
    return {
        "ok": True,
        "bound": BOUND,
        "empty": owner.get("empty") is True,
        "count": owner.get("count") or 0,
        "attention_count": owner.get("attention_count"),
        "items": owner.get("items") or [],
        "empty_message": (
            "No intel recommendations on staff routing — EMPTY (not invent)."
            if owner.get("empty")
            else None
        ),
        "routing": "staff_ops_routing",
        "href": "/staff-ops-routing",
        "auto_promote": False,
        "auto_execute": False,
        "invented": False,
        "why": (
            "Staff attention mirrors Owner connective projection for authorised "
            "intel/ops seats. No second scoring table."
        ),
    }


def operator_recommendation_card(
    surface: str,
    *,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rec = recommend_for_next_action(
        surface,
        {"code": "none", "label": "No further desk action", "hook": None},
        operator_db=operator_db,
        eval_db=eval_db,
    )
    rec_id = str(rec.get("recommendation_id") or recommendation_id_for(surface))
    return {
        "recommendation_id": rec_id,
        "surface": surface,
        "kind": rec.get("kind"),
        "changes_work": rec.get("changes_work"),
        "disposition": rec.get("operator_disposition") or "open",
        "note": rec.get("operator_note"),
        "last_kind": rec.get("operator_last_kind"),
        "question": rec.get("question"),
        "status": rec.get("status"),
        "decision": rec.get("decision"),
        "provenance": rec.get("provenance") or [],
        "base_next": rec.get("base_next"),
        "effective_next": rec.get("effective_next"),
        "provider_fail_safe": rec.get("provider_fail_safe"),
        "why": rec.get("why"),
        "operator_action_count": len(events or []),
        "href": recommendation_href(rec_id),
        "auto_promote": False,
        "auto_execute": False,
        "invented": False,
    }


def operator_recommendation_detail(
    recommendation_id: str,
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any]:
    """Recommendation operator detail/action path. No invent answers. No auto-promote."""
    surface = surface_from_recommendation_id(recommendation_id)
    catalog = _catalog_connect(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        pid = (verified_person_id or "").strip() or None
        actions = {
            "intel_operator": False,
            "note": False,
            "accept_for_desk": False,
            "dismiss": False,
            "handover_touch": False,
            "auto_promote": False,
            "auto_execute": False,
            "invent_answer": False,
        }
        if pid:
            prove = prove_intel_operator(
                person_id=pid, conn=catalog, catalog_db=catalog_db
            )
            actions.update(prove.get("actions") or {})
        prior = list_operator_actions(recommendation_id, operator_db=operator_db)
        card = operator_recommendation_card(
            surface,
            operator_db=operator_db,
            eval_db=eval_db,
            events=prior,
        )
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "recommendation": card,
            "actions": actions,
            "operator_actions": prior,
            "href": card["href"],
            "desk_next_action": desk_next_action_consequence(
                surface, operator_db=operator_db, eval_db=eval_db
            ),
            "owner_attention": owner_attention_consequence(
                operator_db=operator_db, eval_db=eval_db
            ),
            "staff_attention": staff_attention_consequence(
                operator_db=operator_db, eval_db=eval_db
            ),
            "auto_promote": False,
            "auto_execute": False,
            "proven": False,
            "ready": False,
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()


def record_recommendation_operator_action(
    *,
    verified_person_id: str,
    recommendation_id: str,
    kind: str,
    note: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record note / accept-for-desk / dismiss / handover-touch.

    Refreshes desk next-action + Owner/staff attention. Never auto-promotes
    or auto-executes. Never invents answers.
    """
    k = (kind or "").strip().lower()
    if k not in OPERATOR_ACTION_KINDS:
        raise IntelConnectiveError(
            f"kind must be one of {sorted(OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise IntelConnectiveError(
            "verified_person_id required", code="missing_verified_person"
        )
    surface = surface_from_recommendation_id(recommendation_id)
    rec_id = recommendation_id_for(surface)

    catalog = _catalog_connect(catalog_db)
    op_conn, op_path = _open_operator(operator_db, write=True)
    try:
        seat = _require_intel_operator(
            catalog, verified_person_id=pid, catalog_db=catalog_db
        )
        before = _load_operator_state(rec_id, operator_db=op_path)
        before_disp = str(before.get("disposition") or "open")
        stamp = _now()
        new_disp = before_disp
        new_note = str(before.get("note") or "")
        event_note: str | None = text or None

        if k == "note":
            if not text:
                raise IntelConnectiveError("note required", code="missing_note")
            if len(text) > 2000:
                raise IntelConnectiveError("note too long", code="invalid")
            new_note = text
        elif k == "accept_for_desk":
            new_disp = "accepted"
            if text:
                if len(text) > 2000:
                    raise IntelConnectiveError("note too long", code="invalid")
                new_note = text
            elif not event_note:
                event_note = "Accepted for desk."
        elif k == "dismiss":
            new_disp = "dismissed"
            if text:
                if len(text) > 2000:
                    raise IntelConnectiveError("note too long", code="invalid")
                new_note = text
            elif not event_note:
                event_note = "Dismissed by operator."
        elif k == "handover_touch":
            if text and len(text) > 2000:
                raise IntelConnectiveError("note too long", code="invalid")
            if text:
                new_note = text
            else:
                event_note = "Handover touch recorded."

        created_at = before.get("created_at") or stamp
        op_conn.execute(
            """
            INSERT INTO intel_recommendation_state (
              recommendation_id, surface, disposition, note, last_kind,
              updated_by, updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recommendation_id) DO UPDATE SET
              disposition=excluded.disposition,
              note=excluded.note,
              last_kind=excluded.last_kind,
              updated_by=excluded.updated_by,
              updated_at=excluded.updated_at
            """,
            (
                rec_id,
                surface,
                new_disp,
                new_note or None,
                k,
                seat["person_id"],
                stamp,
                created_at,
            ),
        )
        event_id = "IEV-" + uuid.uuid4().hex[:12]
        payload = {
            "operator_depth": True,
            "kind": k,
            "auto_promote": False,
            "auto_execute": False,
            "invented": False,
        }
        op_conn.execute(
            """
            INSERT INTO intel_recommendation_events (
              event_id, recommendation_id, surface, kind, note,
              disposition_before, disposition_after, actor_person_id,
              recorded_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                rec_id,
                surface,
                k,
                event_note,
                before_disp,
                new_disp,
                seat["person_id"],
                stamp,
                json.dumps(payload, separators=(",", ":")),
            ),
        )
        if commit:
            op_conn.commit()
            catalog.commit()

        desk = desk_next_action_consequence(
            surface, operator_db=op_path, eval_db=eval_db
        )
        owner = owner_attention_consequence(operator_db=op_path, eval_db=eval_db)
        staff = staff_attention_consequence(operator_db=op_path, eval_db=eval_db)
        prior = list_operator_actions(rec_id, operator_db=op_path)
        card = operator_recommendation_card(
            surface, operator_db=op_path, eval_db=eval_db, events=prior
        )
        return {
            "ok": True,
            "action": "intel_operator",
            "kind": k,
            "seat": seat,
            "recommendation": card,
            "event": {
                "event_id": event_id,
                "kind": k,
                "note": event_note,
                "disposition_before": before_disp,
                "disposition_after": new_disp,
                "actor_person_id": seat["person_id"],
                "recorded_at": stamp,
            },
            "desk_next_action": desk,
            "owner_attention": owner,
            "staff_attention": staff,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "auto_promote": False,
            "auto_execute": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    finally:
        op_conn.close()
        catalog.close()


def operator_depth_desk(
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    eval_db: Path | str | None = None,
) -> dict[str, Any]:
    """Operator depth desk: RBAC prove + recommendation candidates + consequence honesty."""
    catalog = _catalog_connect(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        pid = (verified_person_id or "").strip() or OWNER
        prove = prove_intel_operator(
            person_id=pid, conn=catalog, catalog_db=catalog_db
        )
        candidates: list[dict[str, Any]] = []
        for surface in SURFACES:
            card = operator_recommendation_card(
                surface, operator_db=operator_db, eval_db=eval_db
            )
            # Show when intel changes work, or operator has recorded state.
            if (
                card.get("changes_work")
                or card.get("disposition") != "open"
                or card.get("note")
                or card.get("last_kind")
            ):
                candidates.append(
                    {
                        "recommendation_id": card.get("recommendation_id"),
                        "surface": card.get("surface"),
                        "kind": card.get("kind"),
                        "disposition": card.get("disposition"),
                        "changes_work": card.get("changes_work"),
                        "effective_next": card.get("effective_next"),
                        "href": card.get("href"),
                    }
                )
        owner = owner_attention_consequence(
            operator_db=operator_db, eval_db=eval_db
        )
        staff = staff_attention_consequence(
            operator_db=operator_db, eval_db=eval_db
        )
        empty = len(candidates) == 0
        learning_stubs: dict[str, Any] = {
            "ok": True,
            "count": 0,
            "recommendations": [],
            "empty": True,
            "empty_message": (
                "No approved rule stubs to recommend — EMPTY (not invent)."
            ),
            "auto_apply": False,
            "auto_promote": False,
            "decision_memory_visible": True,
            "connective_visible": True,
        }
        try:
            from core import intel_learning_policy as ilp

            role_ok = bool(prove.get("allowed"))
            learning_stubs = ilp.stub_recommendations(
                pid,
                role_allowed=role_ok or pid == OWNER,
            )
        except Exception:  # noqa: BLE001
            # Read-surface best effort; connective desk still returns without stubs.
            pass
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "rbac": prove,
            "recommendation_candidates": candidates,
            "recommendation_candidate_count": len(candidates),
            "empty": empty,
            "empty_message": (
                "No connective recommendations for operator depth — EMPTY (not invent)."
                if empty
                else None
            ),
            "learning_policy_stubs": learning_stubs,
            "owner_attention": owner,
            "staff_attention": staff,
            "target_crs": [PRIMARY_CR],
            "auto_promote": False,
            "auto_execute": False,
            "proven": False,
            "ready": False,
            "cr_resolved": False,
            "live_habitat_commission": False,
            "why": (
                "INTEL connective operator depth: recommendation detail/action path + "
                "note/accept-for-desk/dismiss/handover-touch recording that refreshes "
                "desk next-action and Owner/staff attention strips. Learning-policy "
                "approved stubs are visible as read-only recommendations. No auto-promote. "
                "No auto-execute. No invent answers. CAP-INTEL-05 stays SPECIFIED."
            ),
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()


FACT_KEYS = frozenset(
    {
        "promote",
        "auto_promote",
        "execute",
        "auto_execute",
        "proven",
        "ready",
        "money",
        "payment",
        "bank",
        "folio",
        "production",
        "live_rule",
    }
)