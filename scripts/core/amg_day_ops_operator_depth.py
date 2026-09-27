#!/usr/bin/env python3
"""AMG day-ops operator depth — HK/maint/incident/recovery/handover loop (Beta).

Decision served: keep_building_without_matt (owner-autonomous-release-2026-09-19)
+ CAP-AMG-04 daily ops PICK 2026-09-20 + overnight soft pack after NAS index
operator depth ENGINEERING_PASS. Plan:
docs/deliveries/GROK-PLAN-AMG-DAY-OPS-OPERATOR-DEPTH-2026-09-23.md.

Authorised AMG/hotel seats see today's day-ops objects filtered by kind
(HK / maint / incident / recovery / handover), open fixture-honest detail,
and record next-action-touch (plus recovery/handover aliases) that refreshes
Needs-You / day-ops readiness strips. EMPTY honesty when no rows. No invent
live Yanolja occupancy/ADR. No invent PROVEN/READY/staff_ready. Do not
false-resolve AMG CRs. No money / folio / payment.

Bound: beta-amg-day-safe (:8788 only).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import amg_ops_pack as pack

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OPERATOR_EVENTS = BETA_ROOT / "state" / "amg-day-ops" / "operator-events.jsonl"

BOUND = "beta-amg-day-safe"
SCHEMA_ID = "wolf.amg-day-ops-operator-depth.v1"
SLICE = "amg_day_ops_operator_depth"
RUN_ID = "BF-amg-day-ops-operator-depth-20260923"
CLAIM_ID = "bf-amg-day-ops-operator-depth-20260923"
DESK_HREF = "/amg-ops-pack"
DESK_ANCHOR = "/amg-ops-pack#day-ops-depth"

OWNER = pack.OWNER
MISA = pack.MISA
OPERATOR_FIXTURES: tuple[str, ...] = (MISA, OWNER)

CAP_IDS = tuple(f"CAP-AMG-0{i}" for i in range(1, 8))
TARGET_CRS: tuple[str, ...] = (
    "CR-d212cdefaef81166",  # CAP-AMG-01
    "CR-ce127471ba41692b",  # CAP-AMG-02
    "CR-f346ff7449a0bd5f",  # CAP-AMG-03
    "CR-bc5785d66c981fd4",  # CAP-AMG-04
    "CR-49f6461020b693fc",  # CAP-AMG-05
    "CR-e9b3d23e63c1c8a7",  # CAP-AMG-06
    "CR-29c6ac36a9ca03f1",  # CAP-AMG-07
)

# Operator-facing kind aliases → pack day_object kinds
KIND_ALIASES: dict[str, str] = {
    "hk": "housekeeping",
    "housekeeping": "housekeeping",
    "housekeep": "housekeeping",
    "maint": "maintenance",
    "maintenance": "maintenance",
    "incident": "incident",
    "recovery": "service_recovery",
    "service_recovery": "service_recovery",
    "service-recovery": "service_recovery",
    "handover": "handover",
    "hand-over": "handover",
    "shift_handover": "handover",
}
KIND_FILTERS: tuple[str, ...] = ("hk", "maint", "incident", "recovery", "handover")
KIND_FILTER_TO_PACK = {
    "hk": "housekeeping",
    "maint": "maintenance",
    "incident": "incident",
    "recovery": "service_recovery",
    "handover": "handover",
}
PACK_TO_FILTER = {v: k for k, v in KIND_FILTER_TO_PACK.items()}

NEXT_ACTION_KINDS = frozenset(
    {
        "next_action",
        "next_action_touch",
        "recovery",
        "recovery_touch",
        "handover_touch",
        "handover",
        "note",
    }
)
_ACTION_ALIASES = {
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "next_action": "next_action",
    "recovery": "recovery",
    "recovery-touch": "recovery",
    "recovery_touch": "recovery",
    "handover": "handover_touch",
    "handover-touch": "handover_touch",
    "handover_touch": "handover_touch",
    "note": "note",
}

WITA = timezone(timedelta(hours=8))

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema_id": SCHEMA_ID,
    "run_id": RUN_ID,
    "claim_id": CLAIM_ID,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_occupancy": False,
    "invented_adr": False,
    "invented_revpar": False,
    "invented_yanolja": False,
    "yanolja_write": False,
    "yanolja_called": False,
    "folio_executed": False,
    "payment_executed": False,
    "money": None,
    "cr_resolved": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "live_hotel_commission": False,
    "empty_day_ops_is_not_live": True,
    "empty_day_loop_is_not_live": True,
    "production": False,
    "production_mutate": False,
    "cf_seat_mint": False,
    "clickup_retired": True,
    "telegram_retired": True,
    "anon_fail_closed": True,
    "amg_day_ops_operator_depth": True,
}


class DayOpsDepthError(ValueError):
    """Fail closed. Does not invent hotel facts, maturity, or money."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.http = http_status


def now_iso() -> str:
    return datetime.now(WITA).isoformat(timespec="seconds")


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    flags["caps"] = cap_honesty(catalog_db=catalog_db)
    flags["ledger_maturity"] = "SPECIFIED"
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "kind_filters": list(KIND_FILTERS),
        "kind_aliases": dict(KIND_ALIASES),
        "next_action_kinds": sorted(NEXT_ACTION_KINDS),
        "caps": list(CAP_IDS),
        "target_crs": list(TARGET_CRS),
        "surface": DESK_HREF,
        "desk_anchor": DESK_ANCHOR,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "yanolja_write": False,
        "folio_accepted": False,
        "payment_accepted": False,
        "additionalProperties": False,
    }


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/")
    # Allowed operator routes are not refused by tail alone.
    if any(
        x in p
        for x in (
            "/operator-depth",
            "/objects/",
            "/kinds",
            "/rbac",
            "/next-action",
        )
    ):
        pass
    tail = p.rsplit("/", 1)[-1].lower()
    mapping = {
        "proven": "proven_refused",
        "ready": "ready_refused",
        "staff-ready": "staff_ready_refused",
        "staff_ready": "staff_ready_refused",
        "occupancy": "occupancy_refused",
        "adr": "adr_refused",
        "revpar": "revpar_refused",
        "yanolja": "yanolja_refused",
        "yanolja-write": "yanolja_refused",
        "folio": "folio_refused",
        "payment": "payment_refused",
        "money": "payment_refused",
        "bank": "bank_refused",
        "resolve": "resolve_refused",
        "production": "production_refused",
        "cloudflare": "cloudflare_refused",
        "cf": "cloudflare_refused",
    }
    return mapping.get(tail)


def refuse(path: str) -> dict[str, Any]:
    code = refuse_code(path) or "refused"
    return {
        "ok": False,
        "error": code,
        "message": f"AMG day-ops operator depth refuses: {code}",
        **honesty_flags(),
    }


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


def _cr_state(item_id: str, *, catalog: Path | str | None = None) -> str:
    path = Path(catalog) if catalog else CATALOG_DB
    try:
        conn = sqlite3.connect(str(path))
        try:
            row = conn.execute(
                "SELECT state FROM wolf_completion_items WHERE id=?",
                (item_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return "OPEN"
    return str(row[0]) if row and row[0] else "OPEN"


def cap_honesty(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    """CAP / CR honesty — CAP-AMG stay SPECIFIED; CRs stay OPEN; never false-resolve."""
    caps = {cid: _ledger_cap(cid) for cid in CAP_IDS}
    crs = {cr: _cr_state(cr, catalog=catalog_db) for cr in TARGET_CRS}
    return {
        **caps,
        "crs": crs,
        "all_caps_specified": all(v == "SPECIFIED" for v in caps.values()),
        "all_crs_open": all(v == "OPEN" for v in crs.values()),
        "false_resolve_refused": True,
        "denominator": 77,
    }


def normalize_kind_filter(raw: str | None) -> str | None:
    """Map operator kind filter (hk/maint/…) to pack kind. None = all kinds."""
    if raw is None or str(raw).strip() == "":
        return None
    key = str(raw).strip().lower().replace(" ", "_")
    if key in ("all", "*", "any"):
        return None
    if key in KIND_FILTER_TO_PACK:
        return KIND_FILTER_TO_PACK[key]
    if key in KIND_ALIASES:
        return KIND_ALIASES[key]
    raise DayOpsDepthError(
        f"Unknown day-ops kind filter '{raw}'. Use: {', '.join(KIND_FILTERS)}",
        code="invalid_kind",
        http_status=400,
    )


def filter_label(pack_kind: str | None) -> str | None:
    if not pack_kind:
        return None
    return PACK_TO_FILTER.get(pack_kind) or pack_kind


def require_day_ops_operator(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """RBAC: AMG day operator (Misa fixture) or Owner. Outsider → 403."""
    pid = (person_id or "").strip()
    if not pid:
        raise DayOpsDepthError(
            "verified_person_id required",
            code="missing_verified_person",
            http_status=403,
        )
    catalog = pack._catalog_connect(catalog_db)  # noqa: SLF001 — shared catalog helper
    try:
        try:
            pack.ensure_operator_depth_rbac(conn=catalog, commit=True)
            seat = pack._require_day_operator(  # noqa: SLF001
                catalog,
                verified_person_id=pid,
                catalog_db=catalog_db,
            )
        except pack.OpsPackError as exc:
            code = getattr(exc, "code", "forbidden") or "forbidden"
            status = int(getattr(exc, "http_status", 403) or 403)
            if code in {"forbidden", "missing_verified_person"} or status < 400:
                status = 403
            raise DayOpsDepthError(
                str(exc),
                code=code,
                http_status=status,
            ) from exc
        return {
            "person_id": seat["person_id"],
            "seat": seat.get("seat") or "day_operator",
            "label": seat.get("label") or seat["person_id"],
            "live_hotel_commission": False,
        }
    finally:
        catalog.close()


def day_ops_readiness_strip(
    *,
    db_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Day-ops readiness strip from recorded objects. Not staff_ready invent."""
    day = pack.service_day(service_day_value)
    conn = pack._connect(db_path)  # noqa: SLF001
    try:
        objects = pack._day_objects(conn, day)  # noqa: SLF001
        open_objs = [o for o in objects if o.get("status") != "DONE"]
        by_kind = {f: 0 for f in KIND_FILTERS}
        for o in open_objs:
            filt = filter_label(str(o.get("kind") or ""))
            if filt in by_kind:
                by_kind[filt] += 1
        empty = len(open_objs) == 0
        return {
            "ok": True,
            "bound": BOUND,
            "service_day": day,
            "open_count": len(open_objs),
            "by_kind": by_kind,
            "empty": empty,
            "staff_ready": False,
            "ready": False,
            "proven": False,
            "empty_message": (
                "No open day-ops objects today — EMPTY honesty (not invent live hotel state)."
                if empty
                else None
            ),
            "why": (
                "Day-ops readiness from recorded HK/maint/incident/recovery/handover "
                "objects only. Not occupancy/ADR. Not staff_ready=true invent."
            ),
            "yanolja_called": False,
            "occupancy": None,
            "adr": None,
        }
    finally:
        conn.close()


def day_ops_needs_you_consequence(
    *,
    db_path: Path | str | None = None,
    service_day_value: str | None = None,
) -> dict[str, Any]:
    """Needs-You strip for AMG day-ops — mgmt exceptions + open escalations."""
    day = pack.service_day(service_day_value)
    conn = pack._connect(db_path)  # noqa: SLF001
    try:
        mgmt = pack.mgmt_consequence(conn, service_day_value=day)
        owner = pack.owner_consequence(conn, service_day_value=day)
        objects = pack._day_objects(conn, day)  # noqa: SLF001
        needs: list[dict[str, Any]] = []
        for o in objects:
            if o.get("status") == "DONE":
                continue
            reasons: list[str] = []
            if o.get("status") == "ESCALATED" or o.get("needs_mgmt"):
                reasons.append("mgmt_exception")
            if o.get("kind") == "service_recovery":
                reasons.append("recovery_open")
            if o.get("kind") == "handover":
                reasons.append("handover_open")
            if not reasons and o.get("status") == "OPEN":
                reasons.append("day_ops_open")
            needs.append(
                {
                    "object_id": o.get("object_id"),
                    "kind": o.get("kind"),
                    "filter": filter_label(str(o.get("kind") or "")),
                    "title": o.get("title"),
                    "status": o.get("status"),
                    "reasons": reasons,
                    "href": pack.day_object_href(str(o.get("object_id") or "")),
                    "code": "amg_day_ops_needs_you",
                }
            )
        empty = len(needs) == 0
        return {
            "ok": True,
            "bound": BOUND,
            "service_day": day,
            "empty": empty,
            "count": len(needs),
            "items": needs[:20],
            "mgmt_consequence": mgmt,
            "owner_consequence": owner,
            "empty_message": (
                "Nothing Needs-You on AMG day-ops today — EMPTY honesty."
                if empty
                else None
            ),
            "staff_ready": False,
            "invented_sla": False,
            "occupancy": None,
            "yanolja_called": False,
        }
    finally:
        conn.close()


def _append_event(event: dict[str, Any]) -> None:
    OPERATOR_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with OPERATOR_EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    kind: str | None = None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    service_day_value: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    """Today's day-ops objects filtered by kind + EMPTY honesty + readiness strips."""
    seat = require_day_ops_operator(verified_person_id, catalog_db=catalog_db)
    pack_kind = normalize_kind_filter(kind)
    day = pack.service_day(service_day_value)
    catalog = pack._catalog_connect(catalog_db)  # noqa: SLF001
    pack_db = pack._connect(db_path)  # noqa: SLF001
    try:
        prove = pack.prove_day_operator(
            person_id=seat["person_id"],
            conn=catalog,
            catalog_db=catalog_db,
        )
        rows = pack._day_objects(pack_db, day, kind=pack_kind)  # noqa: SLF001
        candidates: list[dict[str, Any]] = []
        for item in rows:
            if item.get("status") == "DONE":
                continue
            candidates.append(
                {
                    "object_id": item.get("object_id"),
                    "kind": item.get("kind"),
                    "filter": filter_label(str(item.get("kind") or "")),
                    "label": item.get("label"),
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "note": item.get("note"),
                    "needs_mgmt": item.get("needs_mgmt"),
                    "href": pack.day_object_href(str(item.get("object_id") or "")),
                    "hotel_fact": False,
                    "pms_fact": False,
                    "occupancy": None,
                    "adr": None,
                }
            )
        capped = candidates[: max(1, min(int(limit or 40), 100))]
        empty = len(candidates) == 0
        readiness = day_ops_readiness_strip(db_path=db_path, service_day_value=day)
        needs = day_ops_needs_you_consequence(db_path=db_path, service_day_value=day)
        caps = cap_honesty(catalog_db=catalog_db)
        if pack_kind:
            kind_buckets = [
                {
                    "filter": filter_label(pack_kind),
                    "kind": pack_kind,
                    "label": pack.DAY_OBJECT_LABELS.get(pack_kind, pack_kind),
                    "open_count": len(candidates),
                }
            ]
        else:
            kind_buckets = [
                {
                    "filter": filt,
                    "kind": KIND_FILTER_TO_PACK[filt],
                    "label": pack.DAY_OBJECT_LABELS[KIND_FILTER_TO_PACK[filt]],
                    "open_count": readiness["by_kind"].get(filt, 0),
                }
                for filt in KIND_FILTERS
            ]
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": SCHEMA_ID,
            "slice": SLICE,
            "run_id": RUN_ID,
            "desk_anchor": DESK_ANCHOR,
            "desk_href": DESK_HREF,
            "service_day": day,
            "kind_filter": filter_label(pack_kind) if pack_kind else None,
            "kind_pack": pack_kind,
            "kind_buckets": kind_buckets,
            "seat": seat,
            "rbac": prove,
            "day_candidates": capped,
            "day_candidate_count": len(candidates),
            "empty": empty,
            "empty_message": (
                (
                    f"No open {filter_label(pack_kind) or 'day-ops'} objects today — "
                    "EMPTY honesty (not invent live hotel state)."
                )
                if empty
                else None
            ),
            "day_ops_readiness": readiness,
            "day_ops_needs_you": needs,
            "mgmt_consequence": needs.get("mgmt_consequence"),
            "owner_consequence": needs.get("owner_consequence"),
            "caps": caps,
            "target_crs": list(TARGET_CRS),
            "why": (
                "AMG day-ops operator depth: today's HK/maint/incident/recovery/handover "
                "objects filtered by kind; open detail; next-action-touch refreshes "
                "Needs-You / day-ops readiness strips. No invent occupancy/ADR. "
                "CAP-AMG-01…07 stay SPECIFIED. AMG CRs stay OPEN."
            ),
            **honesty_flags(catalog_db=catalog_db),
        }
    finally:
        pack_db.close()
        catalog.close()


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Day-ops object detail — fixture honesty; no invent live PMS numbers."""
    seat = require_day_ops_operator(verified_person_id, catalog_db=catalog_db)
    try:
        detail = pack.operator_day_detail(
            object_id,
            verified_person_id=seat["person_id"],
            db_path=db_path,
            catalog_db=catalog_db,
        )
    except pack.OpsPackError as exc:
        raise DayOpsDepthError(
            str(exc),
            code=getattr(exc, "code", "invalid") or "invalid",
            http_status=int(getattr(exc, "http_status", 400) or 400),
        ) from exc
    obj = detail.get("object") or {}
    day = str(obj.get("service_day") or pack.service_day())
    readiness = day_ops_readiness_strip(db_path=db_path, service_day_value=day)
    needs = day_ops_needs_you_consequence(db_path=db_path, service_day_value=day)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "seat": seat,
        "object": {
            **obj,
            "filter": filter_label(str(obj.get("kind") or "")),
            "hotel_fact": False,
            "pms_fact": False,
            "occupancy": None,
            "adr": None,
            "revpar": None,
            "yanolja_called": False,
        },
        "raw": detail.get("raw"),
        "actions": {
            **(detail.get("actions") or {}),
            "next_action_touch": bool((detail.get("actions") or {}).get("day_operator")),
            "recovery_touch": bool((detail.get("actions") or {}).get("recovery")),
            "handover_touch": bool((detail.get("actions") or {}).get("handover_touch")),
            "folio": False,
            "payment": False,
            "yanolja_write": False,
            "occupancy_invent": False,
        },
        "operator_actions": detail.get("operator_actions") or [],
        "next_actions": [
            {
                "code": "next_action_touch",
                "label": "Touch next action (refresh Needs-You / day-ops readiness)",
            },
            {
                "code": "recovery_touch",
                "label": "Recovery touch",
            },
            {
                "code": "handover_touch",
                "label": "Handover touch",
            },
        ],
        "day_ops_readiness": readiness,
        "day_ops_needs_you": needs,
        "mgmt_consequence": detail.get("mgmt_consequence"),
        "owner_consequence": detail.get("owner_consequence"),
        "caps": cap_honesty(catalog_db=catalog_db),
        "href": detail.get("href"),
        **honesty_flags(catalog_db=catalog_db),
    }


def next_action_touch(
    object_id: str,
    *,
    verified_person_id: str | None,
    note: str | None = None,
    kind: str | None = None,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Record next-action / recovery / handover touch; refresh Needs-You strips.

    No folio/payment. No invent occupancy/ADR. No Yanolja write.
    """
    seat = require_day_ops_operator(verified_person_id, catalog_db=catalog_db)
    raw_kind = (kind or "next_action").strip().lower()
    action = _ACTION_ALIASES.get(raw_kind) or _ACTION_ALIASES.get(
        raw_kind.replace("-", "_")
    )
    if action is None:
        raise DayOpsDepthError(
            f"kind must be one of next-action-touch / recovery / handover-touch / note",
            code="invalid_kind",
            http_status=400,
        )
    # Map to pack action kinds where applicable; next_action is depth-local.
    if action == "next_action":
        # Record via pack note/handover_touch path + sidecar next_action event.
        text = (note or "").strip() or "Next-action touch recorded for day-ops object."
        try:
            result = pack.record_day_operator_action(
                verified_person_id=seat["person_id"],
                object_id=object_id,
                kind="note" if (note or "").strip() else "handover_touch",
                note=text if (note or "").strip() else None,
                db_path=db_path,
                catalog_db=catalog_db,
            )
        except pack.OpsPackError as exc:
            raise DayOpsDepthError(
                str(exc),
                code=getattr(exc, "code", "invalid") or "invalid",
                http_status=int(getattr(exc, "http_status", 400) or 400),
            ) from exc
        # Overlay event kind as next_action in sidecar log
        event = {
            "at": now_iso(),
            "kind": "next_action_touch",
            "object_id": object_id,
            "person_id": seat["person_id"],
            "note": (note or "").strip()[:500] or None,
            "pack_event_id": (result.get("event") or {}).get("event_id"),
            "yanolja_write": False,
            "folio_executed": False,
            "payment_executed": False,
        }
        _append_event(event)
        depth_kind = "next_action"
    else:
        pack_action = action  # recovery | handover_touch | note
        text = (note or "").strip()
        if pack_action == "recovery" and not text:
            raise DayOpsDepthError(
                "recovery note required",
                code="missing_note",
                http_status=400,
            )
        try:
            result = pack.record_day_operator_action(
                verified_person_id=seat["person_id"],
                object_id=object_id,
                kind=pack_action,
                note=text or None,
                db_path=db_path,
                catalog_db=catalog_db,
            )
        except pack.OpsPackError as exc:
            raise DayOpsDepthError(
                str(exc),
                code=getattr(exc, "code", "invalid") or "invalid",
                http_status=int(getattr(exc, "http_status", 400) or 400),
            ) from exc
        event = {
            "at": now_iso(),
            "kind": pack_action,
            "object_id": object_id,
            "person_id": seat["person_id"],
            "note": text[:500] if text else None,
            "pack_event_id": (result.get("event") or {}).get("event_id"),
            "yanolja_write": False,
            "folio_executed": False,
            "payment_executed": False,
        }
        _append_event(event)
        depth_kind = pack_action

    obj = result.get("object") or {}
    day = str(obj.get("service_day") or pack.service_day())
    readiness = day_ops_readiness_strip(db_path=db_path, service_day_value=day)
    needs = day_ops_needs_you_consequence(db_path=db_path, service_day_value=day)
    return {
        "ok": True,
        "recorded": True,
        "action": "day_ops_operator",
        "kind": depth_kind,
        "seat": seat,
        "object": {
            **obj,
            "filter": filter_label(str(obj.get("kind") or "")),
            "occupancy": None,
            "adr": None,
        },
        "event": event,
        "pack_result_kind": result.get("kind"),
        "day_ops_readiness": readiness,
        "day_ops_needs_you": needs,
        "mgmt_consequence": result.get("mgmt_consequence") or needs.get("mgmt_consequence"),
        "owner_consequence": result.get("owner_consequence") or needs.get("owner_consequence"),
        "message": (
            f"{depth_kind} recorded. Needs-You / day-ops readiness strips refreshed. "
            "No invent occupancy/ADR · no folio · no payment · staff_ready=false."
        ),
        "caps": cap_honesty(catalog_db=catalog_db),
        **honesty_flags(catalog_db=catalog_db),
    }


def prove_rbac(
    *,
    person_id: str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    pid = (person_id or "").strip() or MISA
    catalog = pack._catalog_connect(catalog_db)  # noqa: SLF001
    try:
        pack.ensure_operator_depth_rbac(conn=catalog, commit=True)
        prove = pack.prove_day_operator(
            person_id=pid, conn=catalog, catalog_db=catalog_db
        )
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": SCHEMA_ID,
            "slice": SLICE,
            "person_id": pid,
            "can_day_ops_operator": bool(prove.get("can_day_operator")),
            "rbac": prove,
            "fixtures": list(OPERATOR_FIXTURES),
            "live_hotel_commission": False,
            "caps": cap_honesty(catalog_db=catalog_db),
            **honesty_flags(catalog_db=catalog_db),
        }
    finally:
        catalog.close()


def kind_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "filters": [
            {
                "filter": filt,
                "kind": KIND_FILTER_TO_PACK[filt],
                "label": pack.DAY_OBJECT_LABELS[KIND_FILTER_TO_PACK[filt]],
            }
            for filt in KIND_FILTERS
        ],
        **honesty_flags(),
    }
