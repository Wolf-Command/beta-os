#!/usr/bin/env python3
"""CRM Identity operator depth — confidence match + human review (Beta).

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + CAP-CRM-02
customer identity memory v1 (2026-09-19). Plan:
docs/deliveries/GROK-PLAN-CRM-IDENTITY-OPERATOR-DEPTH-2026-09-23.md.

Authorised CRM seats open a customer or link-candidate and record note /
next-action-touch / handoff-touch / dismiss-noise / review-decision.
Uncertain matches stay review candidates. A review decision does not merge.
EMPTY honesty when there are no candidates. Refreshes the identity desk and
the CRM Needs-You projection without a second lead-spine or Habitat write.

CAP-CRM-02 stays SPECIFIED. No invent staff_ready / PROVEN / READY /
graph_complete / Habitat commissioned / Haikal done / Devi done.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import crm_identity_memory as ident

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
DEFAULT_EVENTS = BETA_ROOT / "state" / "crm-identity" / "operator-events.jsonl"

BOUND = "beta-crm-loop-safe"
SCHEMA_ID = "wolf.crm-identity-operator-depth.v1"
SLICE = "crm_identity_operator_depth"
RUN_ID = "BF-crm-identity-operator-depth-20260923"
CLAIM_ID = "bf-crm-identity-operator-depth-20260923"
DESK_HREF = "/crm-identity"
DESK_ANCHOR = "/crm-identity#identity-depth"

OWNER = ident.OWNER_PERSON
AMANDA = "PERS-AMANDA"
HAIKAL = "PERS-HAIKAL"
MISA = "PERS-MISA"
# Existing CRM operator fixtures (lead-operator seats). Devi is not a CRM seat.
CRM_SEATS = frozenset({OWNER, AMANDA, HAIKAL, MISA})
PERM_LEAD_OPERATOR = "crm.lead.operator"
PERM_IDENTITY_READ = ident.PERM_READ

CAP_02 = ident.CAP_ID
CR_02 = ident.CR_ID
NOTE_PROVENANCE = "Operator depth memory note on the Beta identity desk."

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_uncertain", "not_a_match", "keep_separate"})
_ACTION_ALIASES = {
    "note": "note",
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "next_action": "next_action",
    "handoff": "handoff_touch",
    "handoff-touch": "handoff_touch",
    "handoff_touch": "handoff_touch",
    "dismiss": "dismiss_noise",
    "dismiss-noise": "dismiss_noise",
    "dismiss_noise": "dismiss_noise",
    "review": "review_decision",
    "review-decision": "review_decision",
    "review_decision": "review_decision",
}
_BANNED_KINDS = {
    "merge": "silent_merge_refused",
    "silent-merge": "silent_merge_refused",
    "silent_merge": "silent_merge_refused",
    "verified": "invented_match",
    "certain": "invented_match",
    "graph_complete": "graph_complete_refused",
    "graph-complete": "graph_complete_refused",
    "proven": "proven_refused",
    "ready": "ready_refused",
    "staff_ready": "staff_ready_refused",
    "staff-ready": "staff_ready_refused",
    "habitat": "habitat_refused",
    "habitat-done": "habitat_refused",
    "cutover": "cutover_refused",
    "klaviyo": "klaviyo_refused",
    "klaviyo-send": "klaviyo_refused",
    "metricool": "metricool_refused",
    "money": "money_refused",
    "secret": "secret_refused",
    "secret-mint": "secret_refused",
    "access": "access_refused",
    "access-include": "access_refused",
    "compose": "bzg_compose_refused",
    "bzg-compose": "bzg_compose_refused",
    "production": "production_refused",
}
_BANNED_BODY = frozenset(
    {
        "graph_complete",
        "identity_graph_complete",
        "merged",
        "merge",
        "silent_merge",
        "proven",
        "ready",
        "staff_ready",
        "maturity",
        "klaviyo",
        "metricool",
        "money",
        "secret",
        "token",
        "habitat",
        "habitat_commissioned",
        "cutover",
        "crm_cutover",
        "compose",
        "bzg_compose",
        "production",
        "access",
        "access_include",
        "email",
        "blast",
    }
)
_ALLOWED_BODY = frozenset({"kind", "note", "body", "decision", "provenance"})
_LINK_RE = re.compile(
    r"^LINK-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_REFUSE_TAILS = {
    "merge": "silent_merge_refused",
    "silent-merge": "silent_merge_refused",
    "graph-complete": "graph_complete_refused",
    "graph_complete": "graph_complete_refused",
    "proven": "proven_refused",
    "ready": "ready_refused",
    "staff-ready": "staff_ready_refused",
    "staff_ready": "staff_ready_refused",
    "habitat": "habitat_refused",
    "habitat-done": "habitat_refused",
    "cutover": "cutover_refused",
    "klaviyo": "klaviyo_refused",
    "klaviyo-send": "klaviyo_refused",
    "metricool": "metricool_refused",
    "money": "money_refused",
    "secret": "secret_refused",
    "secret-mint": "secret_refused",
    "access": "access_refused",
    "access-include": "access_refused",
    "compose": "bzg_compose_refused",
    "bzg-compose": "bzg_compose_refused",
    "production": "production_refused",
    "email-send": "klaviyo_refused",
}

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema_id": SCHEMA_ID,
    "run_id": RUN_ID,
    "claim_id": CLAIM_ID,
    "cap": CAP_02,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "identity_graph_complete": False,
    "graph_invented": False,
    "graph_complete": False,
    "merged": False,
    "merge_executed": False,
    "silent_merge": False,
    "verified_match": False,
    "distinct_from_lead": True,
    "lead_rows_written": False,
    "org_persons_written": False,
    "lead_spine_mutated": False,
    "habitat_mutated": False,
    "duplicate_mutate_surface": False,
    "live_habitat_commission": False,
    "habitat_commissioned": False,
    "crm_cutover": False,
    "klaviyo_write": False,
    "metricool_write": False,
    "marketing_blast": False,
    "bzg_compose": False,
    "money": None,
    "secret_mint": False,
    "cf_access_include_mutated": False,
    "production": False,
    "production_mutate": False,
    "cr_mutated": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "anon_fail_closed": True,
    "invented_permission_grant": False,
    "crm_identity_operator_depth": True,
    "empty_candidates_are_not_a_graph": True,
}


class IdentityDepthError(ValueError):
    """Fail closed. Does not merge, invent a graph, or raise maturity."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.http = http_status


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _assert_events_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low or "wolf-system" in low or "/production" in low:
        raise IdentityDepthError(
            "identity operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if resolved.name == "money.sqlite":
        raise IdentityDepthError(
            "identity operator depth refuses money",
            code="money_refused",
            http_status=403,
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
        raise IdentityDepthError(
            "identity operator events refuse a path outside Beta or a test fixture",
            code="not_beta",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        path = Path(explicit)
    else:
        override = (os.environ.get("WOLF_CRM_IDENTITY_OPS_EVENTS") or "").strip()
        path = Path(override) if override else DEFAULT_EVENTS
    resolved = path.resolve()
    _assert_events_path(resolved)
    return resolved


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    snap = _cap_snapshot(catalog_db)
    flags["caps"] = snap.get("caps") or {}
    flags["cap_crm_02"] = (flags["caps"] or {}).get(CAP_02)
    flags["crm_crs"] = snap.get("crm_crs") or {}
    flags["progress_core_crs"] = snap.get("progress_core_crs") or {}
    flags["au_crm_01_habitat"] = snap.get("au_crm_01_habitat") or "NOT STARTED"
    flags["ledger_maturity"] = flags["cap_crm_02"]
    flags["maturity_ceiling"] = "BUILT"
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["cr_resolved"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "surface": DESK_HREF,
        "desk_anchor": DESK_ANCHOR,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "match_confidence_band": "uncertain",
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "merge_accepted": False,
        "graph_complete_accepted": False,
        "additionalProperties": False,
    }


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    if "/api/crm/identity" not in p:
        return None
    # Legacy register/note/link/merge stays on the identity module.
    if p in {
        "/api/crm/identity",
        "/api/crm/identity/note",
        "/api/crm/identity/link",
        "/api/crm/identity/merge",
    }:
        return None
    if "/operator-depth" not in p:
        return None
    tail = p.rsplit("/", 1)[-1]
    if tail in {"operator-depth", "rbac", "operator-action", "note"}:
        return None
    if tail in {"next-action-touch", "handoff-touch", "dismiss-noise", "review-decision"}:
        return None
    if _LINK_RE.match(tail.upper()) or tail.upper().startswith("CUST-") or tail.upper().startswith("LINK-"):
        return None
    return _REFUSE_TAILS.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"CRM identity operator depth refuses: {code}",
        "merged": False,
        "identity_graph_complete": False,
        "silent_merge": False,
        **honesty_flags(),
    }


def _cap_snapshot(catalog_db: Path | str | None) -> dict[str, Any]:
    from core import crm_ops_needs_you_connective as nye

    try:
        return nye.connective_cap_honesty(catalog_db=catalog_db)
    except Exception:  # noqa: BLE001
        return {
            "caps": {},
            "crm_crs": {},
            "progress_core_crs": {},
            "au_crm_01_habitat": "NOT STARTED",
        }


def _existing_crm_permission(person_id: str) -> bool:
    """Read existing grants. This slice does not insert a permission."""
    from core import rbac as _rbac

    try:
        if _rbac.can(person_id, PERM_LEAD_OPERATOR):
            return True
        if _rbac.can(person_id, PERM_IDENTITY_READ):
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


def require_seat(person_id: str | None) -> dict[str, Any]:
    pid = (person_id or "").strip()
    if not pid:
        raise IdentityDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    if pid not in CRM_SEATS:
        raise IdentityDepthError(
            "CRM identity operator depth is Owner or an existing CRM seat only",
            code="outsider",
            http_status=403,
        )
    if pid != OWNER and not _existing_crm_permission(pid):
        raise IdentityDepthError(
            "existing CRM seat permission is not present; this slice does not grant it",
            code="denied",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": "owner" if pid == OWNER else "crm",
        "authorised": True,
        "invented_permission_grant": False,
        "live_habitat_commission": False,
    }


def prove_rbac(*, person_id: str) -> dict[str, Any]:
    seat = require_seat(person_id)
    allowed = True
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "can_identity_operator": allowed,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "merge": False,
            "silent_merge": False,
            "graph_complete": False,
            "klaviyo_send": False,
            "habitat_done": False,
            "cutover": False,
            "proven": False,
            "ready": False,
            "staff_ready": False,
        },
        "invented_permission_grant": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(),
    }


def _normalise_kind(kind: str) -> str:
    raw = (kind or "").strip().lower()
    if raw in _BANNED_KINDS:
        code = _BANNED_KINDS[raw]
        raise IdentityDepthError(
            f"CRM identity operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise IdentityDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise IdentityDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key, "refused_field")
        if key in {"merged", "merge", "silent_merge"}:
            code = "silent_merge_refused"
        elif key in {"graph_complete", "identity_graph_complete"}:
            code = "graph_complete_refused"
        elif key in {"proven"}:
            code = "proven_refused"
        elif key in {"ready"}:
            code = "ready_refused"
        elif key in {"staff_ready"}:
            code = "staff_ready_refused"
        raise IdentityDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise IdentityDepthError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


def _read_rows(db_path: Path | str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    conn, _resolved = ident._open_read(db_path)
    if conn is None:
        return [], []
    try:
        customers = [
            ident._public_customer(r)
            for r in conn.execute(
                """
                SELECT customer_id, display_name, entity_id, status,
                       created_by, created_at, provenance
                FROM crm_customers
                ORDER BY created_at, customer_id
                """
            ).fetchall()
        ]
        candidates = []
        for r in conn.execute(
            """
            SELECT candidate_id, customer_id, other_id, other_kind, evidence_ref,
                   status, recorded_by, recorded_at, provenance
            FROM crm_link_candidates
            ORDER BY recorded_at, candidate_id
            """
        ).fetchall():
            item = dict(r)
            item["verified"] = False
            item["merged"] = False
            item["lead_is_customer"] = False
            candidates.append(item)
    finally:
        conn.close()
    return customers, candidates


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _events_for(events: list[dict[str, Any]], object_id: str) -> list[dict[str, Any]]:
    return [e for e in events if str(e.get("object_id") or "") == object_id]


def _latest(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    found = [e for e in events if e.get("kind") == kind]
    return found[-1] if found else None


def confidence_view(candidate: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Uncertain until a human records a decision. A decision is not a merge."""
    related = _events_for(events, str(candidate.get("candidate_id") or ""))
    review = _latest(related, "review_decision")
    dismissed = _latest(related, "dismiss_noise") is not None
    decision = str((review or {}).get("decision") or "") or None
    if decision == "still_uncertain":
        human_review_required = True
    elif review is None and not dismissed:
        human_review_required = True
    else:
        human_review_required = False
    return {
        "match_confidence": "uncertain",
        "confidence_band": "uncertain",
        "human_review_required": human_review_required,
        "review_recorded": review is not None,
        "review_decision": decision,
        "dismissed_noise": dismissed,
        "verified": False,
        "merged": False,
        "graph_complete": False,
        "silent_merge": False,
        "status": candidate.get("status") or "REVIEW_REQUIRED",
    }


def _project_candidate(candidate: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    view = confidence_view(candidate, events)
    return {
        "object_id": candidate.get("candidate_id"),
        "object_kind": "link_candidate",
        "candidate_id": candidate.get("candidate_id"),
        "customer_id": candidate.get("customer_id"),
        "other_id": candidate.get("other_id"),
        "other_kind": candidate.get("other_kind"),
        "evidence_ref": candidate.get("evidence_ref"),
        "href": f"/crm-identity#identity-depth-{candidate.get('candidate_id')}",
        **view,
    }


def _needs_you_projection(person_id: str, catalog_db: Path | str | None) -> dict[str, Any]:
    from core import crm_ops_needs_you_connective as nye

    try:
        strip = nye.needs_you_connective_strip(
            verified_person_id=person_id,
            catalog_db=catalog_db,
        )
    except nye.ConnectiveError:
        return {
            "ok": True,
            "empty": True,
            "in_scope": False,
            "count": 0,
            "duplicate_mutate_surface": False,
            "lead_spine_mutated": False,
            "habitat_mutated": False,
            "why": (
                "This seat is outside the CRM Needs-You strip. "
                "No second mutate surface was opened."
            ),
        }
    out = dict(strip)
    out["duplicate_mutate_surface"] = False
    out["lead_spine_mutated"] = False
    out["habitat_mutated"] = False
    out["in_scope"] = True
    return out


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    customers, candidates = _read_rows(db_path)
    events = _load_events(events_path(events_file))
    projected = [_project_candidate(c, events) for c in candidates]
    open_review = [
        c
        for c in projected
        if not c.get("dismissed_noise") and c.get("human_review_required") is True
    ]
    reviewed = [c for c in projected if c.get("review_recorded") and not c.get("dismissed_noise")]
    empty = len(projected) == 0
    empty_open = len(open_review) == 0
    if empty:
        empty_message = (
            "No link candidates. Empty is not a complete identity graph, "
            "not a merge, and not a verified match."
        )
    elif empty_open:
        empty_message = (
            "No open uncertain matches. Recorded candidates were not merged "
            "and the graph is not complete."
        )
    else:
        empty_message = None
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "seat": seat,
        "href": DESK_ANCHOR,
        "customers": customers,
        "customer_count": len(customers),
        "link_candidates": projected,
        "candidate_count": len(projected),
        "open_review": open_review,
        "open_review_count": len(open_review),
        "reviewed_count": len(reviewed),
        "empty": empty,
        "empty_open": empty_open,
        "empty_message": empty_message,
        "match_confidence_band": "uncertain",
        "human_review_required_when_uncertain": True,
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db),
        "distinct_from_lead": True,
        "identity_graph_complete": False,
        "merged": False,
        "silent_merge": False,
        "graph_note": ident.GRAPH_NOTE,
        "lead_spine_mutated": False,
        "habitat_mutated": False,
        "duplicate_mutate_surface": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _find_object(
    object_id: str,
    *,
    db_path: Path | str | None,
    person_id: str,
) -> dict[str, Any]:
    token = (object_id or "").strip()
    customers, candidates = _read_rows(db_path)
    if token.upper().startswith("CUST-"):
        try:
            cust = ident._customer_id(token)
        except ident.CrmIdentityError as exc:
            raise IdentityDepthError(str(exc), code="not_found", http_status=404) from exc
        row = next((c for c in customers if c.get("customer_id") == cust), None)
        if row is None:
            raise IdentityDepthError(
                "Customer was not found. It was not invented.",
                code="not_found",
                http_status=404,
            )
        return {"object_kind": "customer", "customer": row, "candidate": None}
    if token.upper().startswith("LINK-"):
        if not _LINK_RE.match(token):
            raise IdentityDepthError(
                "Link candidate was not found. It was not invented.",
                code="not_found",
                http_status=404,
            )
        row = next((c for c in candidates if c.get("candidate_id") == token), None)
        if row is None:
            raise IdentityDepthError(
                "Link candidate was not found. It was not invented.",
                code="not_found",
                http_status=404,
            )
        parent = next(
            (c for c in customers if c.get("customer_id") == row.get("customer_id")),
            None,
        )
        return {"object_kind": "link_candidate", "customer": parent, "candidate": row}
    raise IdentityDepthError(
        "Object was not found. A lead was not turned into a customer.",
        code="not_found",
        http_status=404,
    )


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    found = _find_object(object_id, db_path=db_path, person_id=seat["person_id"])
    events = _load_events(events_path(events_file))
    _customers, candidates = _read_rows(db_path)
    if found["object_kind"] == "customer":
        cust = found["customer"]
        cid = str(cust.get("customer_id") or "")
        related = [
            _project_candidate(c, events)
            for c in candidates
            if c.get("customer_id") == cid
        ]
        actions_on = _events_for(events, cid)
        uncertain = [c for c in related if c.get("human_review_required")]
        confidence = {
            "match_confidence": "uncertain" if related else None,
            "confidence_band": "uncertain" if related else None,
            "human_review_required": bool(uncertain),
            "verified": False,
            "merged": False,
            "graph_complete": False,
            "empty_candidates": len(related) == 0,
        }
        try:
            notes = ident.read_customer(
                cid,
                seat["person_id"],
                role_allowed=True,
                db_path=db_path,
            ).get("notes") or []
        except ident.CrmIdentityError:
            notes = []
        obj = {
            "object_id": cid,
            "object_kind": "customer",
            "customer": cust,
            "notes": notes,
            "link_candidates": related,
            "is_lead": False,
            "is_customer": True,
        }
    else:
        cand = found["candidate"]
        projected = _project_candidate(cand, events)
        actions_on = _events_for(events, str(cand.get("candidate_id") or ""))
        confidence = {
            "match_confidence": projected.get("match_confidence"),
            "confidence_band": projected.get("confidence_band"),
            "human_review_required": projected.get("human_review_required"),
            "review_recorded": projected.get("review_recorded"),
            "review_decision": projected.get("review_decision"),
            "dismissed_noise": projected.get("dismissed_noise"),
            "verified": False,
            "merged": False,
            "graph_complete": False,
            "empty_candidates": False,
        }
        obj = {
            "object_id": cand.get("candidate_id"),
            "object_kind": "link_candidate",
            "candidate": projected,
            "customer": found["customer"],
            "is_lead": False,
        }
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "seat": seat,
        "object": obj,
        "confidence": confidence,
        "operator_actions": actions_on[-40:],
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": found["object_kind"] == "link_candidate",
            "merge": False,
            "silent_merge": False,
            "graph_complete": False,
            "klaviyo_send": False,
        },
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db),
        "identity_graph_complete": False,
        "merged": False,
        "silent_merge": False,
        "lead_spine_mutated": False,
        "habitat_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _clean_note(text: str) -> str:
    try:
        return ident._clean_text(text, field="note", min_len=2, max_len=4000)
    except ident.CrmIdentityError as exc:
        raise IdentityDepthError(str(exc), code=exc.code, http_status=400) from exc


def record_operator_action(
    object_id: str,
    *,
    verified_person_id: str | None,
    kind: str,
    note: str | None = None,
    decision: str | None = None,
    body: dict | None = None,
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Record an allowed operator action. Does not merge and does not write leads."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id)
    canon = _normalise_kind(kind)
    found = _find_object(object_id, db_path=db_path, person_id=seat["person_id"])
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise IdentityDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        if found["object_kind"] != "link_candidate":
            raise IdentityDepthError(
                "review-decision is for a link candidate. People were not merged.",
                code="review_target",
                http_status=400,
            )
        decision_token = (decision or "").strip().lower().replace("-", "_")
        if decision_token in {"merge", "silent_merge", "verified", "graph_complete"}:
            raise IdentityDepthError(
                "A review decision does not merge and does not complete the graph.",
                code="silent_merge_refused",
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise IdentityDepthError(
                "decision must be still_uncertain, not_a_match, or keep_separate",
                code="invalid_decision",
                http_status=400,
            )
    before_customers, before_links = _read_rows(db_path)
    note_id = None
    if canon == "note":
        customer = found["customer"] or (
            found["candidate"] and {"customer_id": found["candidate"].get("customer_id")}
        )
        cid = (customer or {}).get("customer_id")
        if not cid:
            raise IdentityDepthError("Customer was not found.", code="not_found", http_status=404)
        recorded = ident.append_note(
            {
                "customer_id": cid,
                "body": text,
                "provenance": NOTE_PROVENANCE,
            },
            person_id=seat["person_id"],
            role_allowed=True,
            db_path=db_path,
        )
        note_id = recorded.get("note_id")
    path = events_path(events_file)
    oid = (
        found["candidate"].get("candidate_id")
        if found["object_kind"] == "link_candidate"
        else found["customer"].get("customer_id")
    )
    event = {
        "event_id": f"EVT-{uuid.uuid4()}",
        "object_id": oid,
        "object_kind": found["object_kind"],
        "customer_id": (found["customer"] or found["candidate"] or {}).get("customer_id")
        if found["object_kind"] == "link_candidate"
        else (found["customer"] or {}).get("customer_id"),
        "candidate_id": (found["candidate"] or {}).get("candidate_id"),
        "kind": canon,
        "note": text or None,
        "decision": decision_token,
        "note_id": note_id,
        "person_id": seat["person_id"],
        "recorded_at": now_utc_iso(),
        "merged": False,
        "silent_merge": False,
        "graph_complete": False,
        "verified": False,
        "lead_spine_mutated": False,
        "habitat_mutated": False,
    }
    if found["object_kind"] == "link_candidate":
        event["customer_id"] = (found["candidate"] or {}).get("customer_id")
    _append_event(path, event)
    after_customers, after_links = _read_rows(db_path)
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        db_path=db_path,
        events_file=path,
        catalog_db=catalog_db,
    )
    return {
        "ok": True,
        "action": "crm_identity_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": oid,
        "note_id": note_id,
        "customers_unchanged": len(before_customers) == len(after_customers),
        "link_rows_unchanged": len(before_links) == len(after_links),
        "identity_desk": {
            "customer_count": desk.get("customer_count"),
            "candidate_count": desk.get("candidate_count"),
            "open_review_count": desk.get("open_review_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "href": DESK_ANCHOR,
        },
        "needs_you": desk.get("needs_you"),
        "identity_graph_complete": False,
        "merged": False,
        "merge_executed": False,
        "silent_merge": False,
        "verified_match": False,
        "lead_spine_mutated": False,
        "habitat_mutated": False,
        "duplicate_mutate_surface": False,
        "klaviyo_write": False,
        "metricool_write": False,
        "bzg_compose": False,
        "money": None,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
