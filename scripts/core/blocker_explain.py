#!/usr/bin/env python3
"""Deterministic operating-blocker explanation (Beta).

No agent. No LLM rationale. No chain-of-thought. Does not invent
monetary authority, an opening float, or a named closer.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CLASS_NEEDS_MATT = "NEEDS_MATT"
CLASS_NEEDS_STAFF = "NEEDS_STAFF"
CLASS_NEEDS_POLICY = "NEEDS_POLICY"
CLASS_NEEDS_EXTERNAL = "NEEDS_EXTERNAL_ACCESS"

CLASSIFICATIONS = frozenset(
    {
        CLASS_NEEDS_MATT,
        CLASS_NEEDS_STAFF,
        CLASS_NEEDS_POLICY,
        CLASS_NEEDS_EXTERNAL,
    }
)

CLASSIFICATION_LABELS = {
    CLASS_NEEDS_MATT: "Needs you",
    CLASS_NEEDS_STAFF: "Needs staff",
    CLASS_NEEDS_POLICY: "Needs policy",
    CLASS_NEEDS_EXTERNAL: "Needs external access",
}

WHY_POLICY_REQUIRED = (
    "No approved monetary authority limit exists for this action."
)
WHY_OPENING_FLOAT = "No authorised opening-float source was found."
WHY_CLOSER = "A named closer has not been assigned."
WHY_PAYMENT_EVIDENCE = (
    "Paid claim is not verified payment — evidence still required."
)
WHY_CLOSE_EXCEPTION = "Daily Close has an unresolved exception."
WHY_PETTY_POLICY = "No authorised petty variance policy exists for this count."
WHY_PETTY_OPEN = "The petty tin is open and has not been counted."
WHY_PETTY_VARIANCE = "The petty tin has a noted variance that is not resolved."
WHY_PETTY_ATTENTION = "The petty tin needs attention."
WHY_EXTERNAL = "Required external access has not been granted for this action."
WHY_PR_WAITING = "A purchase request is waiting for approval."
WHY_ORDERED = "An order has been placed and the goods have not been received."
WHY_BILL_WAITING = "A bill is waiting for payment approval."
WHY_CLOSE_NOT_STARTED = "Daily Close has not been started."
WHY_CLOSE_EVIDENCE_MISSING = (
    "Daily close has no declared-cash evidence. No till count was invented."
)
WHY_CLOSE_POLICY = (
    "Variance policy needs approval. "
    "Daily Close can still be saved. Any unexplained variance becomes an exception until the Owner approves the variance policy. "
    "No threshold was invented."
)
WHY_CLOSE_NOT_LOADED = (
    "Daily Close could not be loaded. No substitute figures were invented."
)
WHY_ISSUES = "Issues are open and need a human."
WHY_PARTIAL = (
    "Part of this order has been received. The rest is still outstanding. "
    "This is not a verified stock count."
)
WHY_DRAFT = "This purchase request is still a draft and has not been submitted."
WHY_UNMATCHED = (
    "No deterministic explanation template matches this blocker, "
    "so it is not treated as an owner task."
)

# kind → (why, classification). Deterministic. Do not invent numbers or names.
_TEMPLATES: dict[str, tuple[str, str]] = {
    "policy_required": (WHY_POLICY_REQUIRED, CLASS_NEEDS_POLICY),
    "opening_balance_required": (WHY_OPENING_FLOAT, CLASS_NEEDS_POLICY),
    "closer_required": (WHY_CLOSER, CLASS_NEEDS_STAFF),
    "missing_payment_evidence": (WHY_PAYMENT_EVIDENCE, CLASS_NEEDS_STAFF),
    "close_exception": (WHY_CLOSE_EXCEPTION, CLASS_NEEDS_STAFF),
    "petty_policy_required": (WHY_PETTY_POLICY, CLASS_NEEDS_POLICY),
    "petty_open_uncounted": (WHY_PETTY_OPEN, CLASS_NEEDS_STAFF),
    "petty_variance_noted": (WHY_PETTY_VARIANCE, CLASS_NEEDS_STAFF),
    "petty_attention": (WHY_PETTY_ATTENTION, CLASS_NEEDS_STAFF),
    "external_access_required": (WHY_EXTERNAL, CLASS_NEEDS_EXTERNAL),
    "pr_waiting_approval": (WHY_PR_WAITING, CLASS_NEEDS_STAFF),
    "ordered_not_received": (WHY_ORDERED, CLASS_NEEDS_STAFF),
    "bill_waiting_payment": (WHY_BILL_WAITING, CLASS_NEEDS_STAFF),
    "close_not_started": (WHY_CLOSE_NOT_STARTED, CLASS_NEEDS_STAFF),
    "close_evidence_missing": (WHY_CLOSE_EVIDENCE_MISSING, CLASS_NEEDS_STAFF),
    "close_policy_required": (WHY_CLOSE_POLICY, CLASS_NEEDS_POLICY),
    "close_not_loaded": (WHY_CLOSE_NOT_LOADED, CLASS_NEEDS_STAFF),
    "issues_open": (WHY_ISSUES, CLASS_NEEDS_STAFF),
    "partial_receive": (WHY_PARTIAL, CLASS_NEEDS_STAFF),
    "draft_not_submitted": (WHY_DRAFT, CLASS_NEEDS_STAFF),
}

_KIND_ALIAS = {
    "float_not_found": "opening_balance_required",
    "float not_found": "opening_balance_required",
    "waiting_for_closer": "closer_required",
    "needs_external_access": "external_access_required",
    "inaccessible_source": "external_access_required",
}

HONESTY = {
    "invented_authority": False,
    "invented_float": False,
    "invented_closer": False,
    "llm_rationale_as_evidence": False,
    "note": "Does not invent monetary authority, opening float, or a named closer.",
}

_SECRET_RE = re.compile(
    r"(secret|password|token|api[_-]?key|bearer|cookie)",
    re.IGNORECASE,
)
_UMA_SCOPE = {"entity": "BZG", "brand": "Uma Blu"}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if value == "" or value == [] or value == {}:
        return False
    return True


def _float_not_found(kind: str, context: dict[str, Any]) -> bool:
    if kind in ("opening_balance_required", "float_not_found", "float not_found"):
        return True
    status = str(
        context.get("opening_float_status") or context.get("float") or ""
    ).strip().upper()
    if status == "NOT_FOUND":
        return True
    label = str(context.get("label") or "")
    upper = label.upper()
    if "FLOAT NOT FOUND" in upper or "FLOAT NOT_FOUND" in upper:
        return True
    if "OPENING BALANCE" in upper and "REQUIRED" in upper:
        return True
    return False


def _canonical_kind(kind: str, context: dict[str, Any]) -> str:
    raw = (kind or "").strip()
    key = raw.lower().replace("-", "_")
    if key == "waiting_for_closer" or raw.upper() == "WAITING_FOR_CLOSER":
        return "closer_required"
    if _float_not_found(key, context) and key in (
        "opening_balance_required",
        "float_not_found",
        "float not_found",
        "petty_policy_required",
        "petty_open_uncounted",
        "petty_variance_noted",
        "petty_attention",
        "petty_attention",
        "",
    ):
        return "opening_balance_required"
    # Explicit float signal on any petty/opening kind wins over payment-policy copy.
    if _float_not_found(key, context) and (
        key.startswith("petty_") or "float" in key or "opening" in key
    ):
        return "opening_balance_required"
    if key in _KIND_ALIAS:
        return _KIND_ALIAS[key]
    if key in _TEMPLATES:
        return key
    return key


def _question_matches(question: str) -> bool:
    from core import knowledge_resolution as kr

    q = (question or "").strip()
    if not q:
        return False
    if q in kr.QUESTION_MAP:
        return True
    folded = q.casefold()
    return any(key.casefold() == folded for key in kr.QUESTION_MAP)


def _provenance_labels(provenance: Any) -> list[str]:
    """Short source labels only. No values, secrets, or attempt text."""
    labels: list[str] = []
    if not isinstance(provenance, list):
        return labels
    for item in provenance:
        if not isinstance(item, dict):
            continue
        label = ""
        path = item.get("path")
        if isinstance(path, str) and path.strip():
            label = Path(path).name
        elif item.get("source_id"):
            label = str(item["source_id"])
        elif item.get("authority"):
            label = str(item["authority"])
        elif item.get("field"):
            label = str(item["field"])
        label = label.strip()
        if not label or _SECRET_RE.search(label):
            continue
        if label not in labels:
            labels.append(label)
        if len(labels) >= 8:
            break
    return labels


def _decision_ref(resolved: dict[str, Any]) -> dict[str, str] | None:
    provenance = resolved.get("provenance") or []
    decision_id = ""
    if isinstance(provenance, list):
        for item in provenance:
            if isinstance(item, dict) and item.get("decision_id"):
                decision_id = str(item["decision_id"]).strip()
                break
    if not decision_id:
        return None
    answer = resolved.get("answer")
    summary = ""
    if isinstance(answer, str):
        summary = answer.strip()
    elif isinstance(answer, dict):
        summary = str(
            answer.get("summary") or answer.get("decision") or ""
        ).strip()
    if len(summary) > 240:
        summary = summary[:237].rstrip() + "..."
    ref: dict[str, str] = {"id": decision_id}
    if summary:
        ref["summary"] = summary
    return ref


def _resolve_scope(context: dict[str, Any]) -> str | dict[str, Any]:
    if context.get("scope") is not None:
        return context["scope"]
    surface = str(context.get("surface") or "").strip().lower()
    if surface in ("cockpit", "owner", "progress"):
        return "OWNER"
    return dict(_UMA_SCOPE)


def _attach_resolution(out: dict[str, Any], context: dict[str, Any]) -> None:
    """Optional Decision Memory / AKR lookup. Never copies attempts or prompts."""
    question = str(context.get("question") or "").strip()
    if not question:
        return
    if not _question_matches(question) and not context.get("resolve"):
        return
    from core import knowledge_resolution as kr

    scope = _resolve_scope(context)
    actor = context.get("actor_context")
    try:
        resolved = kr.resolve_question(question, scope, actor_context=actor)
    except Exception:  # noqa: BLE001 — honest miss, no invented answer
        out["status"] = kr.STATUS_NOT_FOUND
        return
    if not isinstance(resolved, dict):
        out["status"] = kr.STATUS_NOT_FOUND
        return
    status = resolved.get("status")
    if status:
        out["status"] = str(status)
    decision = _decision_ref(resolved)
    if decision:
        out["decision"] = decision
    labels = _provenance_labels(resolved.get("provenance"))
    if labels:
        out["provenance"] = labels


def explain_operating_blocker(
    kind: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain one operating blocker. Omits empty optional fields.

    Optional resolve_question runs only when context carries a question that
    matches a registered decision (ClickUp / CRM / credits) or context['resolve']
    is true. Scope defaults to Uma Blu; cockpit/owner/progress uses OWNER.
    CONFLICTED and NOT_FOUND are surfaced as status. Attempts are never returned.
    """
    ctx = context if isinstance(context, dict) else {}
    canonical = _canonical_kind(kind, ctx)
    why, classification = _TEMPLATES.get(
        canonical, (WHY_UNMATCHED, CLASS_NEEDS_STAFF)
    )
    if classification not in CLASSIFICATIONS:
        classification = CLASS_NEEDS_STAFF
    out: dict[str, Any] = {
        "why": why,
        "classification": classification,
        "honesty": dict(HONESTY),
    }
    _attach_resolution(out, ctx)
    return {k: v for k, v in out.items() if _present(v)}
