#!/usr/bin/env python3
"""MSC Compliance Pack operator depth — Beta :8788 only.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + CAP-MSC-03
compliance pack. Plan:
docs/deliveries/GROK-PLAN-MSC-COMPLIANCE-OPERATOR-DEPTH-2026-09-23.md.

Authorised Owner opens a licence, statutory, policy, evidence, owner, or due
slot, or the EMPTY placeholder when the pack has no rows, and records note /
next-action-touch / handoff-touch / dismiss-noise / review-decision.
Recording refreshes the MSC management desk and the MSC Needs-You projection.
It does not write the compliance pack store.

The existing MSC seat is Owner. This slice does not grant another seat.
CAP-MSC-03 stays SPECIFIED. An empty pack is not a current licence and not
proof of compliance. No payment. No BZG compose. No Cloudflare Access Include
mutate. No secret mint. No guest blast. No public post.
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

from core import msc_compliance_pack as pack
from core import msc_mgmt_cluster as cluster
from core import msc_ops_needs_you_connective as nye

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
AU_DISCOVERY = BETA_ROOT / "state" / "model-e-au-discovery.json"
DEFAULT_EVENTS = BETA_ROOT / "state" / "msc-compliance" / "operator-events.jsonl"

BOUND = "beta-msc-loop-safe"
SCHEMA_ID = "wolf.msc-compliance-operator-depth.v1"
SLICE = "msc_compliance_operator_depth"
RUN_ID = "BF-msc-compliance-operator-depth-20260923"
CLAIM_ID = "bf-msc-compliance-operator-depth-20260923"
DESK_HREF = "/msc-compliance"
DESK_ANCHOR = "/msc-compliance#compliance-depth"
MSC_DESK_HREF = "/msc-mgmt-cluster"
EMPTY_ID = "EMPTY-MSC-COMP"
DESK_OBJECT_ID = "MSC-DESK-COMP"
OWNER = cluster.OWNER
AU_ID = "AU-MSC-02-CF-DOORS"
CAP_ID = pack.CAP_ID
CR_ID = pack.CR_ID

OPERATOR_SLOTS: tuple[dict[str, str], ...] = (
    {
        "kind": "licence",
        "label": "Licence",
        "why": "Named licence slot. Empty is not a current licence and not proof of compliance.",
    },
    {
        "kind": "statutory",
        "label": "Statutory",
        "why": "Named statutory slot. Empty is not a filing and not proof of compliance.",
    },
    {
        "kind": "policy",
        "label": "Policy",
        "why": "Named policy slot. Empty is not a policy in force and not proof of compliance.",
    },
    {
        "kind": "evidence",
        "label": "Evidence",
        "why": "Named evidence slot. Empty is not invented evidence and not proof of compliance.",
    },
    {
        "kind": "owner",
        "label": "Owner",
        "why": "Named owner slot. Empty is not proof the pack is current.",
    },
    {
        "kind": "due",
        "label": "Due",
        "why": "Named due slot. Empty is not a payment due and not an amount.",
    },
)

SLOT_OBJECT_IDS: dict[str, str] = {
    "licence": "COMP-LICENCE",
    "statutory": "COMP-STATUTORY",
    "policy": "COMP-POLICY",
    "evidence": "COMP-EVIDENCE",
    "owner": "COMP-OWNER",
    "due": "COMP-DUE",
}
OBJECT_TO_SLOT = {value: key for key, value in SLOT_OBJECT_IDS.items()}
CHAIN: tuple[str, ...] = (
    "licence",
    "statutory",
    "policy",
    "evidence",
    "owner",
    "due",
)

# Read-only as-is. This slice does not write these rows.
NAV_CRS: tuple[str, ...] = (
    "531f29b41f5dfb381503889cacdcfb39",
    "e4bee2462ff81803287fa3562776d8ec",
    "CR-5a5e660e41f782a4",
    "CR-26989486969627cd",
)
PROGRESS_CRS: tuple[str, ...] = (
    "e38d9812128a4535b4a6f59f3a3a0319",
    "CR-c4ed4e3fa9f15a40",
    "CR-6e3fd7b9d7edca0e",
    "CR-7a022a9394592c75",
)
MSC_CRS: tuple[str, ...] = nye.MSC_TARGET_CRS

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_specified", "not_compliance_proof", "keep_as_note"})
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
    "proven": "proven_refused",
    "ready": "ready_refused",
    "staff_ready": "staff_ready_refused",
    "staff-ready": "staff_ready_refused",
    "payment": "payment_refused",
    "bank": "bank_refused",
    "books": "books_refused",
    "alchemist": "alchemist_refused",
    "alchemist-write": "alchemist_refused",
    "alchemist_write": "alchemist_refused",
    "money": "money_refused",
    "licence-current": "licence_current_refused",
    "licence_current": "licence_current_refused",
    "license-current": "licence_current_refused",
    "invent-licence-current": "licence_current_refused",
    "invent_licence_current": "licence_current_refused",
    "current": "licence_current_refused",
    "licence_status": "licence_current_refused",
    "licence-status": "licence_current_refused",
    "compliance-proved": "compliance_proved_refused",
    "compliance_proved": "compliance_proved_refused",
    "invent-compliance-proved": "compliance_proved_refused",
    "invent_compliance_proved": "compliance_proved_refused",
    "compliant": "compliance_proved_refused",
    "guest-blast": "guest_blast_refused",
    "guest_blast": "guest_blast_refused",
    "blast": "guest_blast_refused",
    "public-post": "public_post_refused",
    "public_post": "public_post_refused",
    "public": "public_post_refused",
    "secret": "secret_refused",
    "secret-mint": "secret_refused",
    "access": "access_refused",
    "access-include": "access_refused",
    "compose": "bzg_compose_refused",
    "bzg-compose": "bzg_compose_refused",
    "production": "production_refused",
    "resolve": "resolve_refused",
}
_BANNED_BODY = frozenset(
    {
        "proven",
        "ready",
        "staff_ready",
        "staff-ready",
        "payment",
        "bank",
        "books",
        "alchemist",
        "alchemist_write",
        "alchemist-write",
        "money",
        "licence_status",
        "licence-status",
        "licence_current",
        "licence-current",
        "current",
        "compliance_proved",
        "compliance-proved",
        "compliant",
        "guest_blast",
        "guest-blast",
        "public_post",
        "public-post",
        "maturity",
        "secret",
        "token",
        "access",
        "access_include",
        "access-include",
        "compose",
        "bzg_compose",
        "bzg-compose",
        "production",
        "resolve",
        "cr_resolved",
    }
)
_ALLOWED_BODY = frozenset({"kind", "note", "body", "decision", "provenance"})
_NOTE_BANNED = re.compile(
    r"staff[_\s-]?ready|\bproven\b|\bready\b|licence[_\s-]?current|"
    r"compliance[_\s-]?proved|guest[_\s-]?blast|public[_\s-]?post|"
    r"\b(payment|idr|usd|invoice|transfer)\b|\$\s*\d",
    re.IGNORECASE,
)
_REFUSE_TAILS = dict(_BANNED_KINDS)

_NULL_METRICS: dict[str, Any] = {
    "licence_status": None,
    "current": False,
    "compliance_proved": False,
    "payment": None,
    "money": None,
    "empty_is_compliance": False,
    "guest_blast": False,
    "public_post": False,
}

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema_id": SCHEMA_ID,
    "run_id": RUN_ID,
    "claim_id": CLAIM_ID,
    "cap": CAP_ID,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_licence_current": False,
    "invented_compliance_proved": False,
    "licence_status": None,
    "current": False,
    "compliance_proved": False,
    "payment": None,
    "money": None,
    "empty_is_compliance": False,
    "empty_is_licence_current": False,
    "guest_blast": False,
    "public_post": False,
    "bzg_compose": False,
    "payment_executed": False,
    "secret_mint": False,
    "cf_access_include_mutated": False,
    "access_mutated": False,
    "production": False,
    "production_mutate": False,
    "cr_mutated": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "ledger_write": False,
    "register_mutated": False,
    "pack_mutated": False,
    "framework_mutated": False,
    "duplicate_mutate_surface": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "anon_fail_closed": True,
    "invented_permission_grant": False,
    "intg_reopened": False,
    "w12_fin_reopened": False,
    "clickup_retired": True,
    "telegram_retired": True,
    "msc_compliance_operator_depth": True,
    "inside_compliance_desk_not_orphan_dashboard": True,
}


class ComplianceDepthError(ValueError):
    """Fail closed. Does not invent a current licence or proof of compliance."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.http = http_status


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _assert_events_path(resolved: Path) -> None:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "alchemist" in low or "wolf-system" in low or "/production" in low:
        raise ComplianceDepthError(
            "MSC compliance operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if name == "money.sqlite" or "payment" in name:
        raise ComplianceDepthError(
            "MSC compliance operator depth refuses money",
            code="money_refused",
            http_status=403,
        )
    pack_name = pack.DEFAULT_DB.name.lower()
    if name == pack_name or name == "content_library.sqlite":
        raise ComplianceDepthError(
            "Operator depth does not write the compliance pack store.",
            code="register_refused",
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
        raise ComplianceDepthError(
            "MSC compliance operator depth refuses a path outside Beta",
            code="production_refused",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env = (os.environ.get("WOLF_MSC_COMPLIANCE_OPS_EVENTS") or "").strip()
        path = Path(env) if env else DEFAULT_EVENTS
    _assert_events_path(path)
    return path


def _cr_state(item_id: str, *, catalog: Path | str | None = None) -> str:
    path = Path(catalog) if catalog else CATALOG_DB
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?",
                (item_id,),
            ).fetchone()
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return "OPEN"
    return str(row[0]) if row and row[0] else "OPEN"


def _ledger_cap(cap_id: str) -> str:
    if not LEDGER_JSON.is_file():
        return "UNKNOWN"
    try:
        ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = ledger.get(cap_id)
    if isinstance(row, list) and row:
        return str(row[0])
    if isinstance(row, str):
        return row
    return "UNKNOWN"


def _au_state() -> str:
    """Read AU-MSC-02-CF-DOORS. This slice does not write the discovery file."""
    try:
        data = json.loads(AU_DISCOVERY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "NOT STARTED"
    rows = data if isinstance(data, list) else data.get("units") or data.get("rows") or []
    if not isinstance(rows, list):
        return "NOT STARTED"
    for row in rows:
        if isinstance(row, dict) and row.get("au_id") == AU_ID:
            state = str(row.get("state") or "").strip()
            return state or "NOT STARTED"
    return "NOT STARTED"


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    try:
        snap = nye.connective_cap_honesty(catalog_db=catalog_db)
    except Exception:  # noqa: BLE001
        snap = {"caps": {}, "msc_crs": {}, "progress_core_crs": {}}
    flags["caps"] = snap.get("caps") or {}
    flags["msc_crs"] = snap.get("msc_crs") or {
        cr: _cr_state(cr, catalog=catalog_db) for cr in MSC_CRS
    }
    flags["progress_core_crs"] = {
        cr: _cr_state(cr, catalog=catalog_db) for cr in PROGRESS_CRS
    }
    flags["global_nav_crs"] = {cr: _cr_state(cr, catalog=catalog_db) for cr in NAV_CRS}
    caps = flags["caps"] or {}
    flags["cap_msc_01"] = caps.get("CAP-MSC-01") or _ledger_cap("CAP-MSC-01")
    flags["cap_msc_02"] = caps.get("CAP-MSC-02") or _ledger_cap("CAP-MSC-02")
    flags["cap_msc_03"] = _ledger_cap(CAP_ID)
    flags["cap_msc_04"] = caps.get("CAP-MSC-04") or _ledger_cap("CAP-MSC-04")
    flags["cap_msc_05"] = caps.get("CAP-MSC-05") or _ledger_cap("CAP-MSC-05")
    flags["au_msc_02_cf_doors"] = _au_state()
    flags["cr_id"] = CR_ID
    flags["cr_state"] = _cr_state(CR_ID, catalog=catalog_db)
    flags["ledger_maturity"] = flags["cap_msc_03"]
    flags["maturity_ceiling"] = "SPECIFIED"
    flags["skeleton_ceiling"] = "BUILT"
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["licence_status"] = None
    flags["current"] = False
    flags["compliance_proved"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["guest_blast"] = False
    flags["public_post"] = False
    flags["cr_resolved"] = False
    flags["false_resolve_cr"] = False
    flags["caps_raised"] = False
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
        "msc_desk": MSC_DESK_HREF,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "empty_object_id": EMPTY_ID,
        "slot_object_ids": dict(SLOT_OBJECT_IDS),
        "chain": list(CHAIN),
        "cap": CAP_ID,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "licence_current_accepted": False,
        "compliance_proved_accepted": False,
        "payment_accepted": False,
        "guest_blast_accepted": False,
        "public_post_accepted": False,
        "additionalProperties": False,
    }


def _object_tail(tail: str) -> bool:
    token = (tail or "").strip().upper()
    if token in {EMPTY_ID, DESK_OBJECT_ID}:
        return True
    return token in OBJECT_TO_SLOT


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    if "/api/msc/compliance/operator-depth" not in p:
        return None
    tail = p.rsplit("/", 1)[-1]
    if tail in {
        "operator-depth",
        "desk",
        "rbac",
        "operator-action",
        "note",
        "next-action-touch",
        "handoff-touch",
        "dismiss-noise",
        "review-decision",
    }:
        return None
    if _object_tail(tail):
        return None
    return _REFUSE_TAILS.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"MSC compliance operator depth refuses: {code}",
        **_NULL_METRICS,
        "bzg_compose": False,
        "register_mutated": False,
        "pack_mutated": False,
        **honesty_flags(),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_refused",
        "message": (
            "MSC compliance operator depth records only the allowed POST actions. "
            "This method does not store a current licence, proof of compliance, or a payment."
        ),
        "register_mutated": False,
        "pack_mutated": False,
        **_NULL_METRICS,
        "bzg_compose": False,
        **honesty_flags(),
    }


def not_found_read(path: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "not_found",
        "message": "MSC compliance operator depth has no such read.",
        "path": path,
        **_NULL_METRICS,
        "register_mutated": False,
        "pack_mutated": False,
        "bzg_compose": False,
        **honesty_flags(),
    }


def require_seat(person_id: str | None) -> dict[str, Any]:
    """Owner only. Existing MSC desks do not grant another seat.

    Haikal, Misa, Devi, and Amanda are not this MSC seat. This slice does
    not insert a permission, a Cloudflare Access Include, or a secret.
    """
    pid = (person_id or "").strip()
    if not pid:
        raise ComplianceDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    if pid != OWNER:
        raise ComplianceDepthError(
            "MSC compliance operator depth is Owner only. "
            "No other MSC seat is granted, and this slice does not grant one.",
            code="outsider",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": "owner",
        "authorised": True,
        "invented_permission_grant": False,
        "licence_status": None,
        "current": False,
        "compliance_proved": False,
        "payment": None,
    }


def prove_rbac(*, person_id: str) -> dict[str, Any]:
    seat = require_seat(person_id)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "can_compliance_operator": True,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "licence_current": False,
            "compliance_proved": False,
            "payment": False,
            "guest_blast": False,
            "public_post": False,
            "bzg_compose": False,
            "access_include": False,
            "secret_mint": False,
            "money": False,
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
        raise ComplianceDepthError(
            f"MSC compliance operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise ComplianceDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise ComplianceDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key) or _BANNED_KINDS.get(key.replace("_", "-"), "refused_field")
        raise ComplianceDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise ComplianceDepthError(
            "unknown field " + ",".join(extra),
            code="invalid",
        )


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
    _assert_events_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _events_for(events: list[dict[str, Any]], object_id: str) -> list[dict[str, Any]]:
    return [e for e in events if str(e.get("object_id") or "") == object_id]


def _latest(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    found = [e for e in events if e.get("kind") == kind]
    return found[-1] if found else None


def _action_view(object_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    related = _events_for(events, object_id)
    review = _latest(related, "review_decision")
    return {
        "operator_event_count": len(related),
        "review_recorded": review is not None,
        "review_decision": (review or {}).get("decision"),
        "dismissed_noise": _latest(related, "dismiss_noise") is not None,
        "latest_note": (_latest(related, "note") or {}).get("note"),
        "latest_next_action": (_latest(related, "next_action") or {}).get("note"),
        **_NULL_METRICS,
    }


def _pack_view(
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    built = pack.build_pack(ledger_path, catalog_db)
    recorded = int(built.get("recorded_count") or 0)
    empty = bool(built.get("empty", True)) or recorded == 0
    return {
        "empty": empty,
        "recorded_count": 0 if empty else recorded,
        "on_disk": bool(built.get("on_disk")),
        "cap": CAP_ID,
        **_NULL_METRICS,
    }


def _pack_stamp() -> int | None:
    path = pack.LIVE_DEFAULT_DB
    if not path.is_file():
        return None
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _slot_row(kind: str) -> dict[str, str]:
    return next(item for item in OPERATOR_SLOTS if item["kind"] == kind)


def _slot_card(kind: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    oid = SLOT_OBJECT_IDS[kind]
    row = _slot_row(kind)
    return {
        "object_id": oid,
        "object_kind": "compliance_slot",
        "slot": kind,
        "label": row.get("label"),
        "slot_state": "empty",
        "href": f"{DESK_ANCHOR}-{oid}",
        "empty": True,
        **_NULL_METRICS,
        "why": row.get("why"),
        **_action_view(oid, events),
    }


def _empty_placeholder(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_id": EMPTY_ID,
        "object_kind": "empty_placeholder",
        "slot": None,
        "href": f"{DESK_ANCHOR}-{EMPTY_ID}",
        "empty": True,
        **_NULL_METRICS,
        "empty_message": (
            "No compliance rows. Empty is not a current licence, not proof of "
            "compliance, and not a payment. CAP-MSC-03 stays SPECIFIED."
        ),
        **_action_view(EMPTY_ID, events),
    }


def _desk_card(events: list[dict[str, Any]], *, empty: bool) -> dict[str, Any]:
    return {
        "object_id": DESK_OBJECT_ID,
        "object_kind": "msc_compliance_desk",
        "cap": CAP_ID,
        "cr": CR_ID,
        "href": DESK_ANCHOR,
        "empty": empty,
        **_NULL_METRICS,
        **_action_view(DESK_OBJECT_ID, events),
    }


def _needs_you_projection(
    person_id: str,
    catalog_db: Path | str | None,
) -> dict[str, Any]:
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
            "register_mutated": False,
            "pack_mutated": False,
            "staff_ready": False,
            "proven": False,
            "ready": False,
            **_NULL_METRICS,
            "why": (
                "This seat is outside the MSC Needs-You strip. "
                "No second mutate surface was opened."
            ),
        }
    return {
        "ok": True,
        "empty": strip.get("empty"),
        "count": strip.get("count"),
        "by_kind": strip.get("by_kind"),
        "next_action": strip.get("next_action"),
        "duplicate_mutate_surface": False,
        "register_mutated": False,
        "pack_mutated": False,
        "in_scope": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        **_NULL_METRICS,
        "bzg_compose": False,
        "href": MSC_DESK_HREF,
    }


def _msc_desk_projection(
    person_id: str,
    *,
    catalog_db: Path | str | None,
) -> dict[str, Any]:
    try:
        desk = cluster.build_desk(
            verified_person_id=person_id,
            catalog_db=catalog_db,
        )
    except cluster.MgmtClusterError as exc:
        raise ComplianceDepthError(str(exc), code="outsider", http_status=403) from exc
    modules = []
    for card in desk.get("modules") or []:
        modules.append(
            {
                "id": card.get("id"),
                "cap": card.get("cap"),
                "cr": card.get("cr"),
                "ledger_maturity": card.get("ledger_maturity"),
                "cr_state": card.get("cr_state"),
                "cr_resolved": False,
                "operator_depth_href": card.get("operator_depth_href"),
                "licence_status": None,
                "compliance_proved": False,
                "payment": None,
            }
        )
    return {
        "ok": True,
        "bound": desk.get("bound"),
        "schema_id": desk.get("schema_id"),
        "module_count": desk.get("module_count"),
        "empty_count": desk.get("empty_count"),
        "modules": modules,
        "href": MSC_DESK_HREF,
        "compliance_href": DESK_ANCHOR,
        "caps_raised": False,
        "cr_resolved": False,
        "register_mutated": False,
        "pack_mutated": False,
        "duplicate_mutate_surface": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        **_NULL_METRICS,
        "bzg_compose": False,
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    built = _pack_view(ledger_path=ledger_path, catalog_db=catalog_db)
    events = _load_events(events_path(events_file))
    empty = bool(built.get("empty"))
    slots = [_slot_card(kind, events) for kind in SLOT_OBJECT_IDS]
    placeholder = [_empty_placeholder(events)] if empty else []
    desk_card = _desk_card(events, empty=empty)
    objects = placeholder + slots + [desk_card]
    open_objects = [obj for obj in objects if not obj.get("dismissed_noise")]
    if empty:
        empty_message = (
            "No compliance rows. Empty is not a current licence, not proof of "
            "compliance, and not a payment. CAP-MSC-03 stays SPECIFIED."
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
        "compliance_href": DESK_HREF,
        "chain": list(CHAIN),
        "slots": slots,
        "slot_count": len(slots),
        "empty_placeholder": placeholder[0] if placeholder else None,
        "compliance_desk_card": desk_card,
        "objects": objects,
        "open_count": len(open_objects),
        "empty": empty,
        "empty_message": empty_message,
        "recorded_count": built.get("recorded_count") or 0,
        **_NULL_METRICS,
        "register": {
            "empty": empty,
            "recorded_count": built.get("recorded_count") or 0,
            "cap": CAP_ID,
            "on_disk": built.get("on_disk"),
            **_NULL_METRICS,
        },
        "msc_desk": _msc_desk_projection(seat["person_id"], catalog_db=catalog_db),
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db),
        "register_mutated": False,
        "pack_mutated": False,
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _find_object(object_id: str, *, empty: bool) -> dict[str, Any]:
    token = (object_id or "").strip().upper()
    if token == EMPTY_ID:
        if not empty:
            raise ComplianceDepthError(
                "The pack has rows. The empty placeholder is not a second catalog.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "empty_placeholder",
            "object_id": EMPTY_ID,
            "slot": None,
        }
    if token == DESK_OBJECT_ID:
        return {
            "object_kind": "msc_compliance_desk",
            "object_id": DESK_OBJECT_ID,
            "slot": None,
        }
    kind = OBJECT_TO_SLOT.get(token)
    if kind is not None:
        return {
            "object_kind": "compliance_slot",
            "object_id": token,
            "slot": kind,
        }
    raise ComplianceDepthError(
        "Compliance card was not found. A missing card was not invented as a current licence.",
        code="not_found",
        http_status=404,
    )


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    events = _load_events(events_path(events_file))
    built = _pack_view(ledger_path=ledger_path, catalog_db=catalog_db)
    found = _find_object(object_id, empty=bool(built.get("empty")))
    oid = str(found["object_id"])
    slot = dict(_slot_row(found["slot"])) if found["slot"] else None
    detail: dict[str, Any] = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "seat": seat,
        "object_id": oid,
        "object_kind": found["object_kind"],
        "slot": slot,
        "actions": _action_view(oid, events),
        "events": _events_for(events, oid),
        "empty": True if found["object_kind"] != "msc_compliance_desk" else bool(built.get("empty")),
        "chain": [
            {"slot": kind, "object_id": SLOT_OBJECT_IDS[kind]} for kind in CHAIN
        ],
        **_NULL_METRICS,
        "register_mutated": False,
        "pack_mutated": False,
        "cap": CAP_ID,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
    detail["cap_state"] = (detail["honesty"] or {}).get("cap_msc_03")
    if found["object_kind"] == "empty_placeholder":
        detail["empty"] = True
        detail["empty_message"] = (
            "No compliance rows. Empty is not a current licence and not proof of compliance."
        )
    if found["object_kind"] == "compliance_slot":
        detail["empty"] = True
        detail["slot_state"] = "empty"
    if found["object_kind"] == "msc_compliance_desk":
        detail["msc_desk"] = _msc_desk_projection(seat["person_id"], catalog_db=catalog_db)
        detail["cap_ceiling"] = "SPECIFIED"
        detail["needs_you"] = _needs_you_projection(seat["person_id"], catalog_db)
    return detail


def _clean_note(text: str) -> str:
    note = (text or "").strip()
    if len(note) < 2 or len(note) > 4000:
        raise ComplianceDepthError(
            "An operator note is required. A blank note is not a current licence and not proof.",
            code="missing_note",
            http_status=400,
        )
    if _NOTE_BANNED.search(note):
        raise ComplianceDepthError(
            "An operator note cannot invent a current licence, proof of compliance, "
            "a payment, a guest blast, a public post, or maturity.",
            code="refused_field",
            http_status=403,
        )
    return note


def record_operator_action(
    object_id: str,
    *,
    verified_person_id: str | None,
    kind: str,
    note: str | None = None,
    decision: str | None = None,
    body: dict | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record an allowed operator action. Does not write the compliance pack store."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id)
    canon = _normalise_kind(kind)
    before_stamp = _pack_stamp()
    before_pack = _pack_view(ledger_path=ledger_path, catalog_db=catalog_db)
    found = _find_object(object_id, empty=bool(before_pack.get("empty")))
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise ComplianceDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        decision_token = (decision or "").strip().lower().replace("-", "_")
        banned_decision = _BANNED_KINDS.get(decision_token) or _BANNED_KINDS.get(
            decision_token.replace("_", "-")
        )
        if banned_decision:
            raise ComplianceDepthError(
                "A review decision does not prove a licence, compliance, or a payment.",
                code=banned_decision,
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise ComplianceDepthError(
                "decision must be still_specified, not_compliance_proof, or keep_as_note",
                code="invalid_decision",
                http_status=400,
            )
    path = events_path(events_file)
    event = {
        "event_id": f"EVT-{uuid.uuid4()}",
        "object_id": found["object_id"],
        "object_kind": found["object_kind"],
        "slot": found["slot"],
        "kind": canon,
        "note": text or None,
        "decision": decision_token,
        "person_id": seat["person_id"],
        "recorded_at": now_utc_iso(),
        **_NULL_METRICS,
        "register_mutated": False,
        "pack_mutated": False,
        "bzg_compose": False,
    }
    _append_event(path, event)
    after_pack = _pack_view(ledger_path=ledger_path, catalog_db=catalog_db)
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        events_file=path,
        catalog_db=catalog_db,
        ledger_path=ledger_path,
    )
    unchanged = (
        before_pack.get("recorded_count") == after_pack.get("recorded_count")
        and before_pack.get("empty") == after_pack.get("empty")
        and _pack_stamp() == before_stamp
    )
    return {
        "ok": True,
        "action": "msc_compliance_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": found["object_id"],
        "register_unchanged": unchanged,
        "register_mutated": False,
        "pack_mutated": False,
        "msc_desk": {
            "module_count": (desk.get("msc_desk") or {}).get("module_count"),
            "empty_count": (desk.get("msc_desk") or {}).get("empty_count"),
            "href": MSC_DESK_HREF,
            "caps_raised": False,
            "cr_resolved": False,
            "register_mutated": False,
            "pack_mutated": False,
        },
        "compliance_desk": {
            "slot_count": desk.get("slot_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "open_count": desk.get("open_count"),
            "recorded_count": desk.get("recorded_count"),
            **_NULL_METRICS,
            "href": DESK_ANCHOR,
        },
        "needs_you": desk.get("needs_you"),
        **_NULL_METRICS,
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
        "secret_mint": False,
        "cf_access_include_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
