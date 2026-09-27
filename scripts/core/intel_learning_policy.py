#!/usr/bin/env python3
"""CAP-INTEL-05 learning policy v2 — operator read surface (Beta only).

Decision served: 2026-09-20 PICK approve-to-rule learning loop skeleton
(docs/deliveries/GROK-PLAN-INTEL-APPROVE-TO-RULE-V1-2026-09-19.md), deepened by
docs/deliveries/GROK-PLAN-INTEL-LEARNING-POLICY-V2-2026-09-23.md.

Beyond the note → approve → stub skeleton: list/filter approved stubs and
project them into an Intel operator next-action read model and as read-only
recommendations visible to Decision Memory / connective callers.

Fail closed. Append-only stubs only. No auto-promote. No live rule execution.
Does not write Model C. Does not resolve CR-be51980bd1194448. CAP-INTEL-05
stays at the ledger state (SPECIFIED). proven=false ready=false staff_ready=false.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core import intel_approve_to_rule as rules

BOUND = "beta-intel-connect-safe"
SLICE = "intel_learning_policy_v2"
SCHEMA_ID = "wolf.intel-learning-policy.v2"
RUN_ID = "BF-intel-learning-policy-v2-20260923"
CAP_ID = rules.CAP_ID
CR_ID = rules.CR_ID
OWNER_PERSON = rules.OWNER_PERSON

PERM_READ = rules.PERM_READ

OWNER_PROVE_PATH = "GET /api/intel/learning-policy"

NEXT_EMPTY = "EMPTY"
NEXT_WAITING_APPROVAL = "WAITING_APPROVAL"
NEXT_WAITING_STUB = "WAITING_STUB"
NEXT_REVIEW_STUBS = "REVIEW_STUBS"

GAPS: tuple[str, ...] = (
    "Learning policy v2 is a read surface over append-only stubs.",
    "Approved stubs are recommendations only — not applied, not promoted.",
    "Decision Memory / connective may see stubs; they do not auto-apply.",
    "Auto-promote to live operating rules is refused.",
    "CAP-INTEL-05 stays at the ledger state. This slice does not write it.",
    "CR-be51980bd1194448 stays OPEN.",
    "Noise suppression and performance learning are not this slice.",
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
        "case": "put_shortcut",
        "result": "REFUSED",
        "code": "writes_refused",
    },
    {
        "case": "auto_apply_stub",
        "result": "REFUSED",
        "code": "apply_refused",
    },
)

HONESTY = {
    "cap": CAP_ID,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "bound": BOUND,
    "run_id": RUN_ID,
    "append_only": True,
    "full_loop": False,
    "auto_promote": False,
    "auto_apply": False,
    "rule_execution": False,
    "production_rules": False,
    "live_without_approve": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_or_role": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "staff_ready": False,
    "learning_policy_v1_relaunched": False,
}


class LearningPolicyError(ValueError):
    """Fail closed. Does not invent a live rule or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"approve", "note", "rule"}:
        return rules.permission_for(act)
    return PERM_READ


def honesty_flags() -> dict[str, Any]:
    base = rules.honesty_flags()
    flags = dict(HONESTY)
    flags.update(
        {
            "cr_id": base.get("cr_id"),
            "cr_bound": base.get("cr_bound"),
            "cr_present": base.get("cr_present"),
            "cr_state": base.get("cr_state"),
            "cr_blocker": base.get("cr_blocker"),
            "cr_capability": base.get("cr_capability"),
            "cr_title": base.get("cr_title"),
            "cr_next_action": base.get("cr_next_action"),
            "cr_resolved": base.get("cr_resolved"),
            "ledger_maturity": base.get("ledger_maturity"),
            "maturity": base.get("maturity"),
            "maturity_ceiling": base.get("maturity_ceiling"),
            "framework_skeleton": base.get("framework_skeleton"),
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "auto_promote": False,
            "auto_apply": False,
            "rule_execution": False,
            "production_rules": False,
            "model_c_write": False,
            "model_c_maturity_raised": False,
            "cr_mutated": False,
        }
    )
    return flags


def gaps() -> list[str]:
    return list(GAPS)


def red_team_table() -> list[dict[str, str]]:
    return [dict(row) for row in RED_TEAM]


def refuse_promote(_body: dict | None = None) -> None:
    rules.refuse_promote(_body)


def refuse_execute(_body: dict | None = None) -> None:
    rules.refuse_execute(_body)


def refuse_proven(_body: dict | None = None) -> None:
    rules.refuse_proven(_body)


def refuse_production(_body: dict | None = None) -> None:
    rules.refuse_production(_body)


def refuse_method(_body: dict | None = None) -> None:
    raise LearningPolicyError(
        "This method cannot write a learning-policy rule. "
        "Use approve-to-rule note, approve, then rule steps.",
        code="writes_refused",
    )


def refuse_apply(_body: dict | None = None) -> None:
    raise LearningPolicyError(
        "Auto-apply is refused. Approved stubs are recommendations only.",
        code="apply_refused",
    )


def list_stubs(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    experiment_id: str | None = None,
    note_id: str | None = None,
    limit: int = 50,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """List/filter approved rule stubs. Fail closed for anonymous."""
    try:
        out = rules.list_stubs(
            person_id,
            role_allowed=role_allowed,
            experiment_id=experiment_id,
            note_id=note_id,
            limit=limit,
            db_path=db_path,
        )
    except rules.IntelRuleError as exc:
        raise LearningPolicyError(str(exc), code=exc.code) from exc
    return {
        **out,
        "ok": True,
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "owner_prove_path": OWNER_PROVE_PATH,
        "auto_apply": False,
        "recommendation_only": True,
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
    try:
        out = rules.get_stub(
            stub_id,
            person_id,
            role_allowed=role_allowed,
            db_path=db_path,
        )
    except rules.IntelRuleError as exc:
        raise LearningPolicyError(str(exc), code=exc.code) from exc
    return {
        **out,
        "ok": True,
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "owner_prove_path": OWNER_PROVE_PATH,
        "auto_apply": False,
        "recommendation_only": True,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "honesty": honesty_flags(),
    }


def _recommendation_from_stub(stub: dict[str, Any]) -> dict[str, Any]:
    stub_id = str(stub.get("stub_id") or "")
    text = str(stub.get("rule_text") or "").strip()
    label = text if len(text) <= 120 else text[:117] + "..."
    return {
        "recommendation_id": f"REC-STUB-{stub_id}",
        "kind": "approved_rule_stub",
        "source": "intel_learning_policy",
        "stub_id": stub_id,
        "experiment_id": stub.get("experiment_id"),
        "note_id": stub.get("note_id"),
        "version_n": stub.get("version_n"),
        "label": label,
        "rule_text": text,
        "state": stub.get("state") or rules.STATE_STUB,
        "applied": False,
        "auto_apply": False,
        "auto_promote": False,
        "auto_execute": False,
        "read_only": True,
        "promoted": False,
        "executed": False,
        "live": False,
        "href": f"/api/intel/learning-policy/stubs/{stub_id}",
        "why": (
            "Approved append-only rule stub — recommendation only. "
            "Not applied. Not promoted. Not a live operating rule."
        ),
    }


def stub_recommendations(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    experiment_id: str | None = None,
    note_id: str | None = None,
    limit: int = 50,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Project approved stubs as read-only recommendations for DM / connective.

    Does not write Decision Memory. Does not auto-apply. Honest empty when none.
    """
    listed = list_stubs(
        person_id,
        role_allowed=role_allowed,
        experiment_id=experiment_id,
        note_id=note_id,
        limit=limit,
        db_path=db_path,
    )
    stubs = listed.get("stubs") or []
    recommendations = [_recommendation_from_stub(s) for s in stubs]
    empty = len(recommendations) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "count": len(recommendations),
        "recommendations": recommendations,
        "empty": empty,
        "empty_message": (
            "No approved rule stubs to recommend — EMPTY (not invent)."
            if empty
            else None
        ),
        "decision_memory_visible": True,
        "connective_visible": True,
        "auto_apply": False,
        "auto_promote": False,
        "auto_execute": False,
        "applied_count": 0,
        "owner_prove_path": OWNER_PROVE_PATH,
        "gaps": gaps(),
        "red_team": red_team_table(),
        "honesty": honesty_flags(),
    }


def _queue_counts(
    person_id: str | None,
    *,
    role_allowed: bool,
    db_path: Path | str | None,
) -> dict[str, Any]:
    try:
        listed = rules.list_experiments(
            person_id,
            role_allowed=role_allowed,
            db_path=db_path,
        )
    except rules.IntelRuleError as exc:
        raise LearningPolicyError(str(exc), code=exc.code) from exc
    experiments = listed.get("experiments") or []
    noted = sum(1 for row in experiments if row.get("state") == rules.STATE_NOTED)
    approved = sum(
        1 for row in experiments if row.get("state") == rules.STATE_APPROVED
    )
    stub = sum(1 for row in experiments if row.get("state") == rules.STATE_STUB)
    return {
        "experiment_count": int(listed.get("count") or 0),
        "note_count": int(listed.get("note_count") or 0),
        "approval_count": int(listed.get("approval_count") or 0),
        "stub_count": int(listed.get("stub_count") or 0),
        "state_counts": {
            "NOTED": noted,
            "APPROVED": approved,
            "STUB": stub,
        },
        "promoted_count": int(listed.get("promoted_count") or 0),
        "executed_count": int(listed.get("executed_count") or 0),
        "experiments": experiments[:20],
    }


def operator_next_action(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Intel operator next-action read model over the approve-to-rule queue.

    Honest empty states. Never invents work. Never auto-promotes.
    """
    queue = _queue_counts(person_id, role_allowed=role_allowed, db_path=db_path)
    stub_count = int(queue.get("stub_count") or 0)
    approval_count = int(queue.get("approval_count") or 0)
    note_count = int(queue.get("note_count") or 0)
    state_counts = queue.get("state_counts") or {}
    noted = int(state_counts.get("NOTED") or 0)
    approved_waiting = int(state_counts.get("APPROVED") or 0)

    if stub_count > 0:
        code = NEXT_REVIEW_STUBS
        label = "Review approved rule stubs (read-only recommendations)"
        why = (
            "Versioned stubs exist. They are recommendations only — "
            "not applied, not promoted, not live operating rules."
        )
        empty = False
    elif approved_waiting > 0:
        code = NEXT_WAITING_STUB
        label = "Append a versioned rule stub for an approved note"
        why = (
            "Notes are approved but no stub exists yet. "
            "Stub requires Owner/role path; approve does not invent a rule."
        )
        empty = False
    elif note_count > 0 or noted > 0:
        code = NEXT_WAITING_APPROVAL
        label = "Owner or role must approve an experiment note"
        why = (
            "Experiment notes await approval. "
            "A note is not a stub and is not a live rule. No auto-promote."
        )
        empty = False
    else:
        code = NEXT_EMPTY
        label = "No learning-policy next action — EMPTY (not invent)"
        why = (
            "Approve-to-rule queue is empty. "
            "Empty is not live learning, an adopted rule, or performance proof."
        )
        empty = True

    return {
        "ok": True,
        "code": code,
        "label": label,
        "why": why,
        "empty": empty,
        "href": "/api/intel/learning-policy",
        "approve_to_rule_href": "/api/intel/approve-to-rule",
        "auto_promote": False,
        "auto_apply": False,
        "auto_execute": False,
        "queue": queue,
        "approval_count": approval_count,
        "note_count": note_count,
        "stub_count": stub_count,
        "honesty": honesty_flags(),
    }


def build_desk(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    experiment_id: str | None = None,
    note_id: str | None = None,
    limit: int = 50,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose learning-policy operator desk: next-action + stubs + recommendations."""
    next_action = operator_next_action(
        person_id, role_allowed=role_allowed, db_path=db_path
    )
    stubs = list_stubs(
        person_id,
        role_allowed=role_allowed,
        experiment_id=experiment_id,
        note_id=note_id,
        limit=limit,
        db_path=db_path,
    )
    recommendations = stub_recommendations(
        person_id,
        role_allowed=role_allowed,
        experiment_id=experiment_id,
        note_id=note_id,
        limit=limit,
        db_path=db_path,
    )
    flags = honesty_flags()
    return {
        "ok": True,
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "run_id": RUN_ID,
        "person_id": person_id,
        "next_action": next_action,
        "stubs": stubs.get("stubs") or [],
        "stub_count": stubs.get("count") or 0,
        "recommendations": recommendations.get("recommendations") or [],
        "recommendation_count": recommendations.get("count") or 0,
        "recommendations_empty": recommendations.get("empty"),
        "empty_message": recommendations.get("empty_message"),
        "decision_memory_visible": True,
        "connective_visible": True,
        "auto_promote": False,
        "auto_apply": False,
        "auto_execute": False,
        "live": False,
        "owner_prove_path": OWNER_PROVE_PATH,
        "loop": {
            "desk": "/api/intel/learning-policy",
            "stubs": "/api/intel/learning-policy/stubs",
            "recommendations": "/api/intel/learning-policy/recommendations",
            "approve_to_rule": "/api/intel/approve-to-rule",
            "note": "/api/intel/approve-to-rule/note",
            "approve": "/api/intel/approve-to-rule/approve",
            "rule": "/api/intel/approve-to-rule/rule",
        },
        "caps": {
            CAP_ID: {
                "maturity": flags.get("ledger_maturity"),
                "ceiling": flags.get("maturity_ceiling"),
                "proven": False,
                "ready": False,
                "staff_ready": False,
            }
        },
        "crs": {
            CR_ID: {
                "state": flags.get("cr_state"),
                "resolved": False,
            }
        },
        "gaps": gaps(),
        "red_team": red_team_table(),
        "honesty": flags,
        "why": (
            "Learning policy v2: list/filter approved stubs + operator next-action "
            "read surface. Stubs are Decision Memory / connective visible "
            "recommendations only. No auto-promote. No auto-apply. "
            "CAP-INTEL-05 stays SPECIFIED. CR stays OPEN."
        ),
    }


def refuse_code(path: str) -> str | None:
    """Return refuse kind for promote/execute/proven/apply shortcuts."""
    low = (path or "").rstrip("/")
    if low in {
        "/api/intel/learning-policy/promote",
        "/api/intel/learning-policy/auto-promote",
    }:
        return "promote"
    if low in {
        "/api/intel/learning-policy/proven",
        "/api/intel/learning-policy/ready",
    }:
        return "proven"
    if low in {
        "/api/intel/learning-policy/execute",
        "/api/intel/learning-policy/run",
    }:
        return "execute"
    if low == "/api/intel/learning-policy/production":
        return "production"
    if low in {
        "/api/intel/learning-policy/apply",
        "/api/intel/learning-policy/auto-apply",
    }:
        return "apply"
    return None
