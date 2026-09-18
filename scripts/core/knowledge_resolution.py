#!/usr/bin/env python3
"""Owner knowledge resolution path (Beta) — compose Decision Memory + AKR.

One function: resolve_question. No agent, no persona, no HTTP route, no UI.
No model call. No invented rationale. Does not decide; does not replace audit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core import authorised_knowledge as akr
from core import decision_memory as dm

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
AKR_HABITAT_LIVE_REGISTRY = (
    BETA_ROOT / "scripts" / "core" / "data" / "akr_habitat_live_registry.json"
)
CREDITS_DOC = "docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md"

STATUS_CANONICAL = "CANONICAL"
STATUS_OWNER_DECISION = "OWNER_DECISION"
STATUS_NOT_CANONICAL = "NOT_CANONICAL"
STATUS_CONFLICTED = "CONFLICTED"
STATUS_INACCESSIBLE = "INACCESSIBLE"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_UNKNOWN = "UNKNOWN"

STATUSES = frozenset(
    {
        STATUS_CANONICAL,
        STATUS_OWNER_DECISION,
        STATUS_NOT_CANONICAL,
        STATUS_CONFLICTED,
        STATUS_INACCESSIBLE,
        STATUS_NOT_FOUND,
        STATUS_UNKNOWN,
    }
)

AUTHORITY_CANONICAL = "CANONICAL"
AUTHORITY_OWNER_DECISION = "OWNER_DECISION"
AUTHORITY_AUTHORISED_SOURCE = "AUTHORISED_SOURCE"

HONESTY = {
    "knowledge_resolution": "BUILT",
    "decides": False,
    "replaces_audit": False,
    "llm": False,
    "agent": False,
    "compose_only": True,
}

# Exact question → keys. Do not infer new keys from wording.
QUESTION_MAP: dict[str, dict[str, Any]] = {
    "What is Wolf's ClickUp policy?": {
        "decision_key": "What is Wolf's ClickUp policy?",
        "akr_key": None,
        "scope": "Wolf system",
    },
    "What are the current SYSTEM maturity credits?": {
        "decision_key": "What are the current SYSTEM maturity credits?",
        "akr_key": None,
        "scope": "Wolf system",
    },
    "What font does Habitat use?": {
        "decision_key": None,
        "akr_key": "brand_font",  # never ui_font
        "scope": "Habitat",
    },
    "Is Habitat CRM cut over?": {
        "decision_key": "Is Habitat CRM cut over?",
        "akr_key": None,
        "scope": "Habitat",
    },
    "What does Klaviyo created mean for Habitat lead receipt?": {
        "decision_key": "What does Klaviyo created mean for Habitat lead receipt?",
        "akr_key": None,
        "scope": "Habitat",
    },
    "Is the Habitat headline rule lowercase or uppercase?": {
        "decision_key": None,
        "akr_key": "headline_case",
        "scope": "Habitat",
    },
}

_FAMILY_TOKENS: dict[str, frozenset[str]] = {
    "wolf": frozenset({"wolf-system", "wolf"}),
    "habitat": frozenset({"habitat", "ggv-habitat"}),
    "uma": frozenset({"uma", "uma-blu"}),
}

_FAMILY_RECALL_SCOPES: dict[str, tuple[str, ...]] = {
    "wolf": ("Wolf system",),
    "habitat": ("Habitat", "brand:habitat", "GGV / Habitat"),
    "uma": ("Uma Blu", "brand:uma"),
}


class KnowledgeResolutionError(ValueError):
    """Fail-closed input error for the resolution path."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def _attempt(
    step: str, detail: str, *, ok: bool = True, **extra: Any
) -> dict[str, Any]:
    row: dict[str, Any] = {"step": step, "detail": detail, "ok": ok}
    row.update(extra)
    return row


def _norm_scope(scope: str | dict[str, Any] | None) -> dict[str, Any]:
    return dm.normalize_scope(scope)


def _scope_family(scope: str | dict[str, Any] | None) -> str | None:
    sc = _norm_scope(scope)
    tokens = {
        t for t in (sc.get("brand"), sc.get("object"), sc.get("entity")) if t
    }
    raw = str(sc.get("raw") or "").casefold()
    for family, members in _FAMILY_TOKENS.items():
        if tokens & members:
            return family
        if family == "habitat" and "habitat" in raw:
            return family
        if family == "wolf" and ("wolf" in raw and "system" in raw):
            return family
        if family == "uma" and "uma" in raw:
            return family
    return None


def _lookup_question(question: str) -> dict[str, Any] | None:
    q = (question or "").strip()
    if not q:
        return None
    if q in QUESTION_MAP:
        return dict(QUESTION_MAP[q])
    q_cf = q.casefold()
    for key, meta in QUESTION_MAP.items():
        if key.casefold() == q_cf:
            return dict(meta)
    return None


def _permission_context(actor_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(actor_context, dict):
        return None
    nested = actor_context.get("permission_context")
    if isinstance(nested, dict):
        return nested
    if actor_context.get("person_id"):
        return actor_context
    return None


def _is_empty_field(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


def _canonical_fields(actor_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(actor_context, dict):
        return {}
    canonical = actor_context.get("canonical")
    if not isinstance(canonical, dict):
        return {}
    fields = canonical.get("fields")
    if isinstance(fields, dict):
        return fields
    return canonical


def _decision_answer_text(decision: dict[str, Any]) -> str:
    chosen = decision.get("chosen_option")
    if chosen is not None and str(chosen).strip():
        return str(chosen).strip()
    title = decision.get("title")
    return str(title).strip() if title else ""


def _akr_status_to_allowed(akr_status: str | None) -> str | None:
    if not akr_status:
        return None
    s = str(akr_status).strip().upper().replace(" ", "_")
    if s in STATUSES:
        return s
    return None


def _values_contradict(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    sa = str(a).strip().casefold()
    sb = str(b).strip().casefold()
    if not sa or not sb:
        return False
    if sa == sb:
        return False
    if sa in sb or sb in sa:
        return False
    return True


def _compare_credits_decision(
    decision: dict[str, Any], attempts: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    """Compare Owner credits decision to canon file. Return conflict, prov, matched."""
    prov: list[dict[str, Any]] = []
    try:
        file_table = dm._credits_chosen_option_from_canon()
    except Exception as exc:  # noqa: BLE001
        attempts.append(
            _attempt(
                "CREDITS_FILE",
                f"unreadable or lock mismatch: {exc}",
                ok=False,
            )
        )
        return (
            {"side": "credits_file", "detail": str(exc), "path": CREDITS_DOC},
            prov,
            False,
        )

    chosen = str(decision.get("chosen_option") or "").strip()
    file_norm = file_table.strip()
    if chosen != file_norm:
        attempts.append(
            _attempt(
                "CREDITS_FILE",
                "decision chosen_option differs from canon file table",
                ok=False,
            )
        )
        return (
            {
                "side": "credits_mismatch",
                "decision": chosen,
                "file": file_norm,
                "path": CREDITS_DOC,
            },
            [{"path": CREDITS_DOC, "role": "canon_file", "agrees": False}],
            False,
        )

    attempts.append(_attempt("CREDITS_FILE", f"matches {CREDITS_DOC}", ok=True))
    prov.append(
        {
            "path": CREDITS_DOC,
            "role": "canon_file",
            "agrees": True,
            "authority": "CANONICAL_DOC",
        }
    )
    return None, prov, True


def _validate_scope(
    question: str,
    scope: str | dict[str, Any] | None,
    meta: dict[str, Any] | None,
    attempts: list[dict[str, Any]],
) -> tuple[bool, str | None]:
    if scope is None or (isinstance(scope, str) and not scope.strip()):
        attempts.append(_attempt("SCOPE", "missing scope — refused", ok=False))
        return False, "missing_scope"

    caller_family = _scope_family(scope)
    attempts.append(
        _attempt(
            "SCOPE",
            f"normalized={_norm_scope(scope)} family={caller_family}",
            ok=True,
        )
    )

    if meta is not None:
        expected_family = _scope_family(meta.get("scope"))
        if expected_family and caller_family and expected_family != caller_family:
            attempts.append(
                _attempt(
                    "SCOPE",
                    f"refused: caller family={caller_family} "
                    f"question family={expected_family} — no cross-brand bleed",
                    ok=False,
                )
            )
            return False, "brand_mismatch"
        if expected_family and caller_family is None:
            attempts.append(
                _attempt(
                    "SCOPE",
                    f"refused: cannot classify caller scope against {expected_family}",
                    ok=False,
                )
            )
            return False, "brand_mismatch"

    q_cf = (question or "").casefold()
    if caller_family == "uma" and "habitat" in q_cf:
        attempts.append(
            _attempt("SCOPE", "refused: Habitat question under Uma scope", ok=False)
        )
        return False, "brand_mismatch"

    return True, None


def _result(
    *,
    answer: Any,
    status: str,
    authority: str | None,
    provenance: list[dict[str, Any]],
    confidence_basis: str,
    conflict: Any,
    attempts: list[dict[str, Any]],
    escalate: bool | None = None,
) -> dict[str, Any]:
    if status not in STATUSES:
        status = STATUS_UNKNOWN
    if escalate is None:
        escalate = status in (
            STATUS_CONFLICTED,
            STATUS_INACCESSIBLE,
            STATUS_UNKNOWN,
        )
    # Explicit false for resolved / empty-canonical / miss statuses.
    if status in (
        STATUS_NOT_FOUND,
        STATUS_NOT_CANONICAL,
        STATUS_OWNER_DECISION,
        STATUS_CANONICAL,
    ):
        escalate = False
    return {
        "answer": answer,
        "status": status,
        "authority": authority,
        "provenance": list(provenance),
        "confidence_basis": confidence_basis,
        "conflict": conflict,
        "attempts": list(attempts),
        "escalate": bool(escalate),
        "honesty": honesty_flags(),
    }


def _status_for_authorised_fact(mapped_akr_status: str | None) -> str:
    """Status for a retrieved authorised fact.

    Authority is always AUTHORISED_SOURCE (caller sets it). Answer stays the
    fact — never emptied into an empty-canonical finding. AKR's success word
    "NOT CANONICAL" maps to the allowed NOT_CANONICAL (found, not promoted).
    That is not OWNER_DECISION, not UNKNOWN, and not NOT_FOUND.
    """
    if mapped_akr_status in (
        STATUS_CONFLICTED,
        STATUS_INACCESSIBLE,
        STATUS_UNKNOWN,
        STATUS_CANONICAL,
        STATUS_NOT_CANONICAL,
    ):
        return mapped_akr_status
    return STATUS_NOT_CANONICAL


def resolve_question(
    question: str,
    scope: str | dict[str, Any] | None,
    *,
    actor_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve an Owner/brand question via canonical → Decision Memory → AKR.

    Steps run in order and are recorded in attempts. No LLM. No writes.
    """
    attempts: list[dict[str, Any]] = []
    q = (question or "").strip()
    if not q:
        raise KnowledgeResolutionError("question required", code="bad_question")

    # Security: Habitat live registry only. No injected roots / crawl / writes.
    if isinstance(actor_context, dict):
        injected = actor_context.get("sources_registry") or actor_context.get(
            "akr_registry"
        )
        if injected is not None:
            attempts.append(
                _attempt(
                    "AKR",
                    "refused: custom sources_registry not allowed "
                    "(Habitat live registry only)",
                    ok=False,
                )
            )
            return _result(
                answer=None,
                status=STATUS_INACCESSIBLE,
                authority=None,
                provenance=[],
                confidence_basis="registry_override_refused",
                conflict=None,
                attempts=attempts,
                escalate=True,
            )
        outside = actor_context.get("path") or actor_context.get("source_path")
        if outside is not None:
            attempts.append(
                _attempt(
                    "AKR",
                    f"refused: path outside AKR allowlist not accepted ({outside})",
                    ok=False,
                )
            )
            return _result(
                answer=None,
                status=STATUS_INACCESSIBLE,
                authority=None,
                provenance=[],
                confidence_basis="path_outside_allowlist",
                conflict=None,
                attempts=attempts,
                escalate=True,
            )

    meta = _lookup_question(q)
    attempts.append(
        _attempt(
            "MAP",
            "mapped"
            if meta
            else "no registered key — search still runs; no human escalate",
            ok=True,
            decision_key=(meta or {}).get("decision_key"),
            akr_key=(meta or {}).get("akr_key"),
        )
    )

    ok_scope, refuse = _validate_scope(q, scope, meta, attempts)
    if not ok_scope:
        return _result(
            answer=None,
            status=STATUS_NOT_FOUND,
            authority=None,
            provenance=[],
            confidence_basis=f"scope_refused:{refuse}",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    caller_family = _scope_family(scope)
    decision_key = (meta or {}).get("decision_key")
    akr_key = (meta or {}).get("akr_key")

    # --- 2. Canonical structured truth (only if field already exists) --------
    fields = _canonical_fields(actor_context)
    canonical_answer: Any = None
    canonical_empty = False
    canon_field = akr_key
    if canon_field and isinstance(fields, dict) and canon_field in fields:
        val = fields.get(canon_field)
        if _is_empty_field(val):
            canonical_empty = True
            attempts.append(
                _attempt(
                    "CANONICAL",
                    f"field {canon_field} empty — NOT_CANONICAL (not UNKNOWN)",
                    ok=True,
                )
            )
        else:
            canonical_answer = val
            attempts.append(
                _attempt("CANONICAL", f"field {canon_field} present", ok=True)
            )
    else:
        attempts.append(
            _attempt(
                "CANONICAL",
                "no existing canonical field for this question — skipped",
                ok=True,
            )
        )

    # --- 3. Decision Memory --------------------------------------------------
    decision: dict[str, Any] | None = None
    decision_inaccessible = False
    perm = _permission_context(actor_context)
    db_path = None
    if isinstance(actor_context, dict):
        db_path = actor_context.get("db_path")

    recall_query = decision_key if decision_key else q
    recall_scopes: list[str] = []
    if isinstance(scope, str) and scope.strip():
        recall_scopes.append(scope.strip())
    if caller_family and caller_family in _FAMILY_RECALL_SCOPES:
        recall_scopes.extend(_FAMILY_RECALL_SCOPES[caller_family])
    seen_scopes: set[str] = set()
    ordered_scopes: list[str] = []
    for s in recall_scopes:
        key = str(_norm_scope(s))
        if key not in seen_scopes:
            seen_scopes.add(key)
            ordered_scopes.append(s)

    if perm is None:
        decision_inaccessible = True
        attempts.append(
            _attempt(
                "DECISION_MEMORY",
                "INACCESSIBLE — no permission context (fail closed)",
                ok=False,
            )
        )
    else:
        for rs in ordered_scopes:
            try:
                hit = dm.recall(
                    rs,
                    recall_query,
                    permission_context=perm,
                    db_path=db_path,
                    limit=5,
                )
            except dm.DecisionMemoryError as exc:
                decision_inaccessible = True
                attempts.append(
                    _attempt(
                        "DECISION_MEMORY",
                        f"INACCESSIBLE — {exc}",
                        ok=False,
                        scope=rs,
                    )
                )
                break
            count = int(hit.get("count") or 0)
            attempts.append(
                _attempt(
                    "DECISION_MEMORY",
                    f"recall scope={rs!r} query={recall_query!r} count={count}",
                    ok=count > 0,
                    scope=rs,
                )
            )
            if count > 0:
                decision = (hit.get("decisions") or [None])[0]
                break

    # --- 4. AKR (Habitat live registry only) ---------------------------------
    akr_result: dict[str, Any]
    if caller_family == "habitat":
        akr_scope: str | dict[str, Any] = "brand:habitat"
    elif caller_family == "uma":
        akr_scope = "brand:uma"
    elif isinstance(scope, str):
        akr_scope = scope
    else:
        akr_scope = scope or {}

    # Always call AKR (do not skip). Decision-only keys use a non-matching probe.
    if akr_key:
        akr_question_key = akr_key
    elif decision_key:
        akr_question_key = f"__no_akr_key__:{decision_key}"
    else:
        akr_question_key = q

    if not AKR_HABITAT_LIVE_REGISTRY.is_file():
        attempts.append(
            _attempt(
                "AKR",
                f"INACCESSIBLE — registry missing: {AKR_HABITAT_LIVE_REGISTRY}",
                ok=False,
            )
        )
        akr_result = {
            "status": akr.STATUS_INACCESSIBLE,
            "answer": None,
            "provenance": [],
            "conflicts": [],
        }
    else:
        try:
            akr_result = akr.resolve(
                akr_scope,
                str(akr_question_key),
                AKR_HABITAT_LIVE_REGISTRY,
                canonical={"fields": fields} if fields else {"fields": {}},
            )
            attempts.append(
                _attempt(
                    "AKR",
                    f"resolve key={akr_question_key!r} status={akr_result.get('status')}",
                    ok=akr_result.get("answer") is not None
                    or akr_result.get("status") == akr.STATUS_CONFLICTED,
                )
            )
        except akr.AuthorisedKnowledgeError as exc:
            attempts.append(_attempt("AKR", f"refused: {exc}", ok=False))
            akr_result = {
                "status": akr.STATUS_INACCESSIBLE,
                "answer": None,
                "provenance": [],
                "conflicts": [],
            }

    # --- 5. Compare / 6. Single result ---------------------------------------
    akr_status_raw = akr_result.get("status")
    akr_answer_obj = akr_result.get("answer") or {}
    if not isinstance(akr_answer_obj, dict):
        akr_answer_obj = {}
    akr_value = akr_answer_obj.get("value")
    if akr_key == "brand_font":
        if akr_answer_obj.get("brand_font") is not None:
            akr_value = akr_answer_obj.get("brand_font")
        # Never surface UI lane as the brand answer.
        akr_answer_obj = {k: v for k, v in akr_answer_obj.items() if k != "ui_font"}
        if akr_value is not None:
            akr_answer_obj = dict(akr_answer_obj)
            akr_answer_obj["value"] = akr_value

    akr_prov = list(akr_result.get("provenance") or [])
    akr_conflicts = list(akr_result.get("conflicts") or [])
    mapped_akr_status = _akr_status_to_allowed(
        str(akr_status_raw) if akr_status_raw else None
    )

    # Credits: Owner decision vs canon file (required cite on agree).
    if (
        decision is not None
        and decision_key == "What are the current SYSTEM maturity credits?"
    ):
        conflict_side, credits_prov, matched = _compare_credits_decision(
            decision, attempts
        )
        if not matched:
            return _result(
                answer={
                    "decision": _decision_answer_text(decision),
                    "file": (conflict_side or {}).get("file"),
                },
                status=STATUS_CONFLICTED,
                authority=None,
                provenance=[
                    {
                        "decision_id": decision.get("decision_id"),
                        "authority": AUTHORITY_OWNER_DECISION,
                    },
                    *credits_prov,
                ],
                confidence_basis="credits_decision_vs_file",
                conflict={
                    "sides": [
                        {
                            "authority": AUTHORITY_OWNER_DECISION,
                            "decision_id": decision.get("decision_id"),
                            "value": _decision_answer_text(decision),
                        },
                        {
                            "authority": "CANONICAL_DOC",
                            "path": CREDITS_DOC,
                            "value": (conflict_side or {}).get("file")
                            or (conflict_side or {}).get("detail"),
                        },
                    ]
                },
                attempts=attempts,
                escalate=True,
            )
        return _result(
            answer=_decision_answer_text(decision),
            status=STATUS_OWNER_DECISION,
            authority=AUTHORITY_OWNER_DECISION,
            provenance=[
                {
                    "decision_id": decision.get("decision_id"),
                    "authority": AUTHORITY_OWNER_DECISION,
                    "scope_raw": decision.get("scope_raw"),
                    "query_keys": decision.get("query_keys"),
                },
                *credits_prov,
            ],
            confidence_basis="owner_decision_agrees_credits_file",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    if decision_inaccessible and decision_key and decision is None:
        if (
            canonical_answer is None
            and akr_value is None
            and not (
                mapped_akr_status == STATUS_CONFLICTED and akr_conflicts
            )
        ):
            return _result(
                answer=None,
                status=STATUS_INACCESSIBLE,
                authority=None,
                provenance=[],
                confidence_basis="decision_memory_inaccessible",
                conflict=None,
                attempts=attempts,
                escalate=True,
            )

    if mapped_akr_status == STATUS_CONFLICTED and akr_conflicts:
        prov = list(akr_prov)
        conflict_payload: dict[str, Any] = {"sides": akr_conflicts}
        if decision is not None:
            prov = [
                {
                    "decision_id": decision.get("decision_id"),
                    "value": _decision_answer_text(decision),
                    "authority": AUTHORITY_OWNER_DECISION,
                },
                *prov,
            ]
            conflict_payload["decision"] = decision.get("decision_id")
        return _result(
            answer=None,
            status=STATUS_CONFLICTED,
            authority=None,
            provenance=prov,
            confidence_basis="akr_conflicted",
            conflict=conflict_payload,
            attempts=attempts,
            escalate=True,
        )

    if decision is not None:
        d_text = _decision_answer_text(decision)
        prov = [
            {
                "decision_id": decision.get("decision_id"),
                "authority": AUTHORITY_OWNER_DECISION,
                "value": d_text,
                "scope_raw": decision.get("scope_raw"),
                "query_keys": decision.get("query_keys"),
                "provenance": decision.get("provenance"),
            }
        ]
        if akr_value is not None and _values_contradict(d_text, akr_value):
            attempts.append(
                _attempt(
                    "COMPARE",
                    "Owner decision contradicts AKR evidence",
                    ok=False,
                )
            )
            return _result(
                answer=None,
                status=STATUS_CONFLICTED,
                authority=None,
                provenance=prov + akr_prov,
                confidence_basis="decision_vs_akr",
                conflict={
                    "sides": [
                        {
                            "authority": AUTHORITY_OWNER_DECISION,
                            "value": d_text,
                            "decision_id": decision.get("decision_id"),
                        },
                        {
                            "authority": AUTHORITY_AUTHORISED_SOURCE,
                            "value": akr_value,
                            "provenance": akr_prov,
                        },
                    ]
                },
                attempts=attempts,
                escalate=True,
            )
        if akr_value is not None:
            attempts.append(
                _attempt(
                    "COMPARE", "Owner decision agrees with AKR evidence", ok=True
                )
            )
            prov.extend(akr_prov)
        return _result(
            answer=d_text,
            status=STATUS_OWNER_DECISION,
            authority=AUTHORITY_OWNER_DECISION,
            provenance=prov,
            confidence_basis="owner_decision",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    if canonical_answer is not None:
        if akr_value is not None and _values_contradict(canonical_answer, akr_value):
            return _result(
                answer=None,
                status=STATUS_CONFLICTED,
                authority=None,
                provenance=[
                    {
                        "authority": AUTHORITY_CANONICAL,
                        "value": canonical_answer,
                        "field": canon_field,
                    },
                    *akr_prov,
                ],
                confidence_basis="canonical_vs_akr",
                conflict={
                    "sides": [
                        {
                            "authority": AUTHORITY_CANONICAL,
                            "value": canonical_answer,
                        },
                        {
                            "authority": AUTHORITY_AUTHORISED_SOURCE,
                            "value": akr_value,
                        },
                    ]
                },
                attempts=attempts,
                escalate=True,
            )
        return _result(
            answer=canonical_answer,
            status=STATUS_CANONICAL,
            authority=AUTHORITY_CANONICAL,
            provenance=[
                {
                    "authority": AUTHORITY_CANONICAL,
                    "value": canonical_answer,
                    "field": canon_field,
                }
            ],
            confidence_basis="canonical_field",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    if mapped_akr_status == STATUS_INACCESSIBLE and akr_key:
        return _result(
            answer=None,
            status=STATUS_INACCESSIBLE,
            authority=None,
            provenance=akr_prov,
            confidence_basis="akr_inaccessible",
            conflict=None,
            attempts=attempts,
            escalate=True,
        )

    if akr_value is not None:
        # Keep the retrieved fact. Authority AUTHORISED_SOURCE — never
        # OWNER_DECISION unless a decision answered it (handled above).
        status = _status_for_authorised_fact(mapped_akr_status)
        answer_out: Any = akr_value
        if akr_key == "brand_font":
            answer_out = akr_value
        elif akr_answer_obj:
            answer_out = akr_answer_obj
        return _result(
            answer=answer_out,
            status=status,
            authority=AUTHORITY_AUTHORISED_SOURCE,
            provenance=akr_prov,
            confidence_basis="authorised_source",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    if canonical_empty:
        return _result(
            answer=None,
            status=STATUS_NOT_CANONICAL,
            authority=None,
            provenance=[{"field": canon_field, "empty": True}],
            confidence_basis="empty_canonical_field",
            conflict=None,
            attempts=attempts,
            escalate=False,
        )

    if mapped_akr_status == STATUS_UNKNOWN:
        return _result(
            answer=None,
            status=STATUS_UNKNOWN,
            authority=None,
            provenance=akr_prov,
            confidence_basis="unclassified",
            conflict=None,
            attempts=attempts,
            escalate=True,
        )

    return _result(
        answer=None,
        status=STATUS_NOT_FOUND,
        authority=None,
        provenance=[],
        confidence_basis="searched_decision_and_allowlist",
        conflict=None,
        attempts=attempts,
        escalate=False,
    )
