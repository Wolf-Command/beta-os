#!/usr/bin/env python3
"""CAP-INTEL-01 orchestration surface (Beta) — BUILT, not PROVEN.

One function: orchestrate_institutional_question.
Composes knowledge_resolution and, when a blocker kind is present,
blocker_explain. Optional work-item load is fail-closed.

Deterministic. No LLM-as-evidence. No chain-of-thought. Does not decide.
Does not claim Cloudflare JWT authenticated the answer.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core import blocker_explain as bx
from core import decision_memory as dm
from core import knowledge_resolution as kr
from core import work_items as wi

DEMO_QUESTION = "What is Wolf's ClickUp policy?"
DEMO_SCOPE = "Wolf system"

OUTCOME_AUTHORISED = "AUTHORISED"
OUTCOME_OWNER_DECISION = "OWNER_DECISION"
OUTCOME_CONFLICTED = "CONFLICTED"
OUTCOME_NOT_FOUND = "NOT_FOUND"
OUTCOME_UNKNOWN = "UNKNOWN"
OUTCOME_NEEDS_HUMAN = "NEEDS_HUMAN"

OUTCOMES = frozenset(
    {
        OUTCOME_AUTHORISED,
        OUTCOME_OWNER_DECISION,
        OUTCOME_CONFLICTED,
        OUTCOME_NOT_FOUND,
        OUTCOME_UNKNOWN,
        OUTCOME_NEEDS_HUMAN,
    }
)

ACTION_NONE = "NONE"
ACTION_NEEDS_MATT = "NEEDS_MATT"
ACTION_NEEDS_STAFF = "NEEDS_STAFF"
ACTION_NEEDS_POLICY = "NEEDS_POLICY"
ACTION_NEEDS_EXTERNAL = "NEEDS_EXTERNAL_ACCESS"
ACTION_REVIEW_CONFLICT = "REVIEW_CONFLICT"

ACTIONS = frozenset(
    {
        ACTION_NONE,
        ACTION_NEEDS_MATT,
        ACTION_NEEDS_STAFF,
        ACTION_NEEDS_POLICY,
        ACTION_NEEDS_EXTERNAL,
        ACTION_REVIEW_CONFLICT,
    }
)

# Resolution status → fixed outcome. No free-text rationale.
_STATUS_OUTCOME = {
    kr.STATUS_CANONICAL: OUTCOME_AUTHORISED,
    kr.STATUS_NOT_CANONICAL: OUTCOME_AUTHORISED,
    kr.STATUS_OWNER_DECISION: OUTCOME_OWNER_DECISION,
    kr.STATUS_CONFLICTED: OUTCOME_CONFLICTED,
    kr.STATUS_NOT_FOUND: OUTCOME_NOT_FOUND,
    kr.STATUS_UNKNOWN: OUTCOME_UNKNOWN,
    kr.STATUS_INACCESSIBLE: OUTCOME_NEEDS_HUMAN,
}

_SUMMARY = {
    OUTCOME_AUTHORISED: (
        "An authorised source answered this question. No new authority was invented."
    ),
    OUTCOME_OWNER_DECISION: (
        "An owner decision already records the answer. This surface does not decide."
    ),
    OUTCOME_CONFLICTED: (
        "Authorised sources conflict, so a human must review before any answer is used."
    ),
    OUTCOME_NOT_FOUND: (
        "No authorised answer was found, and nothing was invented to fill the gap."
    ),
    OUTCOME_UNKNOWN: "The outcome is unknown. No model rationale was produced.",
    OUTCOME_NEEDS_HUMAN: (
        "A human must supply access or a decision before this question can be answered."
    ),
}

HONESTY = {
    "cap": "CAP-INTEL-01",
    "maturity": "BUILT",
    "proven": False,
    "llm_as_evidence": False,
    "chain_of_thought": False,
    "cloudflare_jwt_auth": False,
    "invented_authority": False,
    "decides": False,
    "agent": False,
    "compose_only": True,
}

_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)


class IntelOrchestrationError(ValueError):
    """Fail-closed input error. Does not invent an answer."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def _kind(actor_context: dict[str, Any] | None) -> str:
    if not isinstance(actor_context, dict):
        return ""
    return str(
        actor_context.get("kind") or actor_context.get("blocker_kind") or ""
    ).strip()


def _provenance_labels(provenance: Any) -> list[str]:
    """Short source labels only. No values, secrets, or attempt text."""
    labels: list[str] = []
    if not isinstance(provenance, list):
        return labels
    for item in provenance:
        label = ""
        if isinstance(item, str):
            label = item.strip()
        elif isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str) and path.strip():
                label = Path(path).name
            elif item.get("source_id"):
                label = str(item["source_id"])
            elif item.get("authority"):
                label = str(item["authority"])
            elif item.get("field"):
                label = str(item["field"])
            elif item.get("decision_id"):
                label = str(item["decision_id"])
        label = label.strip()
        if not label or _SECRET_RE.search(label):
            continue
        if label not in labels:
            labels.append(label)
        if len(labels) >= 8:
            break
    return labels


def _map_outcome(resolution_status: str | None, answer: Any) -> str:
    status = str(resolution_status or "").strip().upper().replace(" ", "_")
    outcome = _STATUS_OUTCOME.get(status, OUTCOME_UNKNOWN)
    if outcome == OUTCOME_AUTHORISED and answer is None and status == kr.STATUS_NOT_CANONICAL:
        return OUTCOME_NOT_FOUND
    if outcome not in OUTCOMES:
        return OUTCOME_UNKNOWN
    return outcome


def _next_action(outcome: str, blocker_class: str | None) -> str:
    if outcome == OUTCOME_CONFLICTED:
        return ACTION_REVIEW_CONFLICT
    if blocker_class in (
        ACTION_NEEDS_MATT,
        ACTION_NEEDS_STAFF,
        ACTION_NEEDS_POLICY,
        ACTION_NEEDS_EXTERNAL,
    ):
        return blocker_class
    if outcome == OUTCOME_NEEDS_HUMAN:
        return ACTION_NEEDS_EXTERNAL
    return ACTION_NONE


def _load_work_item(
    work_item_id: str, actor_context: dict[str, Any] | None
) -> dict[str, Any]:
    wid = (work_item_id or "").strip()
    if not wid:
        raise IntelOrchestrationError("work_item_id required", code="bad_work_item")
    db_path = None
    if isinstance(actor_context, dict) and actor_context.get("work_db_path"):
        db_path = Path(str(actor_context["work_db_path"]))
    conn = wi.db_connect(db_path) if db_path is not None else None
    try:
        item = wi.get_work_item(wid, conn=conn) if conn is not None else wi.get_work_item(wid)
    finally:
        if conn is not None:
            conn.close()
    if not item:
        raise IntelOrchestrationError(
            f"work item not found: {wid}",
            code="work_item_missing",
        )
    return {
        "work_item_id": str(item.get("work_item_id") or wid),
        "status": str(item.get("status") or ""),
    }


def orchestrate_institutional_question(
    question: str,
    scope: str | dict[str, Any] | None,
    actor_context: dict[str, Any] | None = None,
    work_item_id: str | None = None,
) -> dict[str, Any]:
    """DATA → TOOLS → REASONING → SYNTHESIS → HUMAN. Read-only. No model call."""
    q = (question or "").strip()
    if not q:
        raise IntelOrchestrationError("question required", code="bad_question")

    normalised = dm.normalize_scope(scope)
    steps: list[dict[str, Any]] = [
        {"phase": "DATA", "tool": "scope", "ran": True},
    ]

    work_ref: dict[str, Any] | None = None
    if work_item_id and str(work_item_id).strip():
        work_ref = _load_work_item(str(work_item_id), actor_context)
        steps.append({"phase": "DATA", "tool": "work_items", "ran": True})
    else:
        steps.append({"phase": "DATA", "tool": "work_items", "ran": False})

    try:
        resolved = kr.resolve_question(q, scope, actor_context=actor_context)
    except kr.KnowledgeResolutionError as exc:
        raise IntelOrchestrationError(str(exc), code=exc.code) from exc
    if not isinstance(resolved, dict):
        resolved = {}
    steps.append({"phase": "TOOLS", "tool": "knowledge_resolution", "ran": True})

    kind = _kind(actor_context)
    blocker_class: str | None = None
    blocker_labels: list[str] = []
    if kind:
        explained = bx.explain_operating_blocker(
            kind,
            {
                "question": q,
                "scope": scope,
                "actor_context": actor_context,
                "surface": "owner",
            },
        )
        if isinstance(explained, dict):
            raw_class = explained.get("classification")
            if isinstance(raw_class, str) and raw_class.strip():
                blocker_class = raw_class.strip()
            blocker_labels = _provenance_labels(explained.get("provenance"))
        steps.append({"phase": "TOOLS", "tool": "blocker_explain", "ran": True})
    else:
        steps.append({"phase": "TOOLS", "tool": "blocker_explain", "ran": False})

    outcome = _map_outcome(resolved.get("status"), resolved.get("answer"))
    steps.append({"phase": "REASONING", "tool": "status_map", "ran": True})

    labels = _provenance_labels(resolved.get("provenance"))
    for label in blocker_labels:
        if label not in labels and len(labels) < 8:
            labels.append(label)
    summary = _SUMMARY.get(outcome, _SUMMARY[OUTCOME_UNKNOWN])
    steps.append({"phase": "SYNTHESIS", "tool": "summary", "ran": True})

    action = _next_action(outcome, blocker_class)
    if action not in ACTIONS:
        action = ACTION_NONE
    steps.append({"phase": "HUMAN", "tool": "next_human_action", "ran": True})

    tools = ["knowledge_resolution"]
    if kind:
        tools.append("blocker_explain")
    if work_ref:
        tools.append("work_items")

    return {
        "question": q,
        "scope": normalised,
        "status": outcome,
        "summary": summary,
        "provenance": labels,
        "next_human_action": action,
        "steps": steps,
        "tools": tools,
        "work_item": work_ref,
        "honesty": honesty_flags(),
    }
