#!/usr/bin/env python3
"""MSC asset / maintenance operator depth — Beta :8788 only.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + CAP-MSC-01
asset register. Plan:
docs/deliveries/GROK-PLAN-MSC-ASSET-OPERATOR-DEPTH-2026-09-23.md.

Authorised Owner opens an asset, its maintenance note, an MSC desk module,
or the EMPTY placeholder when the register has no rows, and records note /
next-action-touch / handoff-touch / dismiss-noise / review-decision.
Recording refreshes the MSC desk and the MSC Needs-You projection.
It does not write the asset register, invent an inventory count, or raise
a CAP.

CAP-MSC-01/03/04/05 stay SPECIFIED. CAP-MSC-02 stays BUILT.
AU-MSC-02-CF-DOORS stays NOT STARTED. No invent staff_ready / PROVEN /
READY / inventory_complete / MFA live / compliance-done / legal-hold.
No BZG compose. No Cloudflare Access Include mutate. No secret mint.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import msc_asset_register as assets
from core import msc_mgmt_cluster as msc

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
AU_DISCOVERY = BETA_ROOT / "state" / "model-e-au-discovery.json"
DEFAULT_EVENTS = BETA_ROOT / "state" / "msc-asset" / "operator-events.jsonl"

BOUND = "beta-core-safe"
SCHEMA_ID = "wolf.msc-asset-operator-depth.v1"
SLICE = "msc_asset_operator_depth"
RUN_ID = "BF-msc-asset-operator-depth-20260923"
CLAIM_ID = "bf-msc-asset-operator-depth-20260923"
DESK_HREF = "/msc-mgmt-cluster"
DESK_ANCHOR = "/msc-mgmt-cluster#asset-depth"
ASSET_HREF = "/msc-assets"
AU_ID = "AU-MSC-02-CF-DOORS"
EMPTY_ID = "EMPTY-MSC-ASSET"
OWNER = msc.OWNER

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_specified", "not_complete", "keep_as_note"})
DESK_MODULE_IDS = tuple(spec["id"] for spec in msc.MODULE_SPECS)
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
    "inventory_complete": "inventory_refused",
    "inventory-complete": "inventory_refused",
    "inventory": "inventory_refused",
    "compliance_done": "compliance_refused",
    "compliance-done": "compliance_refused",
    "mfa_live": "mfa_refused",
    "mfa-live": "mfa_refused",
    "mfa": "mfa_refused",
    "legal_hold": "legal_hold_refused",
    "legal-hold": "legal_hold_refused",
    "legal_hold_active": "legal_hold_refused",
    "legal-hold-active": "legal_hold_refused",
    "proven": "proven_refused",
    "ready": "ready_refused",
    "staff_ready": "staff_ready_refused",
    "staff-ready": "staff_ready_refused",
    "money": "money_refused",
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
        "inventory",
        "inventory_count",
        "inventory_complete",
        "compliance_done",
        "mfa",
        "mfa_live",
        "legal_hold",
        "legal_hold_active",
        "proven",
        "ready",
        "staff_ready",
        "maturity",
        "money",
        "secret",
        "token",
        "access",
        "access_include",
        "compose",
        "bzg_compose",
        "production",
        "resolve",
        "cr_resolved",
    }
)
_ALLOWED_BODY = frozenset({"kind", "note", "body", "decision", "provenance"})
_ASSET_RE = assets._ASSET_RE
_NOTE_BANNED = re.compile(
    r"inventory[_\s-]?complete|compliance[_\s-]?done|mfa[_\s-]?live|"
    r"legal[_\s-]?hold|staff[_\s-]?ready|\bproven\b|\bready\b",
    re.IGNORECASE,
)
_REFUSE_TAILS = dict(_BANNED_KINDS)

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
    "inventory_complete": False,
    "inventory_count": None,
    "empty_is_inventory": False,
    "recorded_is_inventory": False,
    "compliance_done": False,
    "mfa_live": False,
    "legal_hold_active": False,
    "service_proved": False,
    "bzg_compose": False,
    "money": None,
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
    "duplicate_mutate_surface": False,
    "haikal_human": "not_started",
    "devi_retest": "parked",
    "anon_fail_closed": True,
    "invented_permission_grant": False,
    "intg_reopened": False,
    "w12_fin_reopened": False,
    "msc_asset_operator_depth": True,
    "empty_register_is_not_inventory": True,
}


class AssetDepthError(ValueError):
    """Fail closed. Does not invent inventory, compliance, MFA, or maturity."""

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
        raise AssetDepthError(
            "MSC asset operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if resolved.name == "money.sqlite":
        raise AssetDepthError(
            "MSC asset operator depth refuses money",
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
        raise AssetDepthError(
            "MSC asset operator depth refuses a path outside Beta",
            code="production_refused",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env = (os.environ.get("WOLF_MSC_ASSET_OPS_EVENTS") or "").strip()
        path = Path(env) if env else DEFAULT_EVENTS
    _assert_events_path(path)
    return path


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
    snap = _cap_snapshot(catalog_db)
    flags["caps"] = snap.get("caps") or {}
    flags["expected"] = snap.get("expected") or {}
    flags["msc_crs"] = snap.get("msc_crs") or {}
    flags["progress_core_crs"] = snap.get("progress_core_crs") or {}
    flags["cap_msc_01"] = (flags["caps"] or {}).get("CAP-MSC-01")
    flags["cap_msc_02"] = (flags["caps"] or {}).get("CAP-MSC-02")
    flags["au_msc_02_cf_doors"] = _au_state()
    flags["ledger_maturity"] = flags["cap_msc_01"]
    flags["maturity_ceiling"] = "SPECIFIED"
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["inventory_count"] = None
    flags["inventory_complete"] = False
    flags["compliance_done"] = False
    flags["mfa_live"] = False
    flags["legal_hold_active"] = False
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
        "asset_surface": ASSET_HREF,
        "desk_anchor": DESK_ANCHOR,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "empty_object_id": EMPTY_ID,
        "au_id": AU_ID,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "inventory_complete_accepted": False,
        "compliance_done_accepted": False,
        "mfa_live_accepted": False,
        "legal_hold_accepted": False,
        "additionalProperties": False,
    }


def _object_tail(tail: str) -> bool:
    token = (tail or "").strip()
    upper = token.upper()
    if upper == EMPTY_ID:
        return True
    low = token.lower()
    if low.startswith("msc-desk-"):
        return low[len("msc-desk-") :] in DESK_MODULE_IDS
    if low.startswith("maint-"):
        asset_id = "AST-" + low[len("maint-ast-") :] if low.startswith("maint-ast-") else low[6:]
        return bool(_ASSET_RE.fullmatch(asset_id))
    if low.startswith("ast-"):
        return bool(_ASSET_RE.fullmatch("AST-" + low[4:]))
    return bool(_ASSET_RE.fullmatch(token))


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    if "/operator-depth" not in p:
        return None
    if "/api/msc/assets/" not in p and "/api/msc/mgmt-cluster/" not in p:
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
        "message": f"MSC asset operator depth refuses: {code}",
        "inventory_complete": False,
        "inventory_count": None,
        "compliance_done": False,
        "mfa_live": False,
        "legal_hold_active": False,
        "bzg_compose": False,
        "register_mutated": False,
        **honesty_flags(),
    }


def _cap_snapshot(catalog_db: Path | str | None) -> dict[str, Any]:
    from core import msc_ops_needs_you_connective as nye

    try:
        return nye.connective_cap_honesty(catalog_db=catalog_db)
    except Exception:  # noqa: BLE001
        return {
            "caps": {},
            "expected": {},
            "msc_crs": {},
            "progress_core_crs": {},
        }


def require_seat(person_id: str | None) -> dict[str, Any]:
    """Owner only. Existing MSC desks do not grant another seat.

    This slice does not insert a permission, a Cloudflare Access Include,
    or a secret.
    """
    pid = (person_id or "").strip()
    if not pid:
        raise AssetDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    if pid != OWNER:
        raise AssetDepthError(
            "MSC asset operator depth is Owner only. "
            "No other MSC seat is granted, and this slice does not grant one.",
            code="outsider",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": "owner",
        "authorised": True,
        "invented_permission_grant": False,
        "live_mfa": False,
        "compliance_done": False,
        "legal_hold_active": False,
    }


def prove_rbac(*, person_id: str) -> dict[str, Any]:
    seat = require_seat(person_id)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "can_asset_operator": True,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "inventory_complete": False,
            "compliance_done": False,
            "mfa_live": False,
            "legal_hold_active": False,
            "proven": False,
            "ready": False,
            "staff_ready": False,
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
        raise AssetDepthError(
            f"MSC asset operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise AssetDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise AssetDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key) or _BANNED_KINDS.get(key.replace("_", "-"), "refused_field")
        raise AssetDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise AssetDepthError(
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


def _asset_rows(db_path: Path | str | None) -> list[dict[str, Any]]:
    return list(assets.list_assets(db_path))


def _maintenance_block(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {
            "present": False,
            "last_service": None,
            "last_service_is_note": True,
            "service_proved": False,
            "inventory_count": None,
        }
    return {
        "present": True,
        "last_service": row.get("last_service"),
        "last_service_is_note": True,
        "service_proved": False,
        "inventory_count": None,
        "status": row.get("status"),
    }


def _action_view(object_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    related = _events_for(events, object_id)
    review = _latest(related, "review_decision")
    dismissed = _latest(related, "dismiss_noise") is not None
    return {
        "operator_event_count": len(related),
        "review_recorded": review is not None,
        "review_decision": (review or {}).get("decision"),
        "dismissed_noise": dismissed,
        "latest_note": (_latest(related, "note") or {}).get("note"),
        "latest_next_action": (_latest(related, "next_action") or {}).get("note"),
        "inventory_complete": False,
        "service_proved": False,
        "compliance_done": False,
        "mfa_live": False,
        "legal_hold_active": False,
    }


def _project_asset(row: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    oid = str(row.get("id") or "")
    return {
        "object_id": oid,
        "object_kind": "asset",
        "asset_id": oid,
        "venue": row.get("venue"),
        "venue_name": row.get("venue_name"),
        "type": row.get("type"),
        "status": row.get("status"),
        "href": f"{ASSET_HREF}#asset-depth-{oid}",
        "maintenance": _maintenance_block(row),
        "inventory_count": None,
        "empty": False,
        **_action_view(oid, events),
    }


def _project_maintenance(row: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    asset_id = str(row.get("id") or "")
    oid = f"MAINT-{asset_id}"
    return {
        "object_id": oid,
        "object_kind": "maintenance",
        "asset_id": asset_id,
        "venue": row.get("venue"),
        "type": row.get("type"),
        "href": f"{ASSET_HREF}#asset-depth-{oid}",
        "maintenance": _maintenance_block(row),
        "inventory_count": None,
        "service_proved": False,
        "empty": False,
        **_action_view(oid, events),
    }


def _empty_placeholder(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_id": EMPTY_ID,
        "object_kind": "empty_placeholder",
        "asset_id": None,
        "href": f"{DESK_ANCHOR}-{EMPTY_ID}",
        "maintenance": _maintenance_block(None),
        "inventory_count": None,
        "empty": True,
        "empty_message": (
            "Asset register has no noted rows. Empty is not an inventory count, "
            "not a completed service, and not CAP-MSC-01 PROVEN."
        ),
        **_action_view(EMPTY_ID, events),
    }


def _desk_objects(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for spec in msc.MODULE_SPECS:
        oid = f"MSC-DESK-{spec['id']}"
        out.append(
            {
                "object_id": oid,
                "object_kind": "msc_desk",
                "module_id": spec["id"],
                "cap": spec["cap"],
                "cr": spec["cr"],
                "title": spec["title"],
                "href": f"{DESK_ANCHOR}-{oid}",
                "inventory_count": None,
                "compliance_done": False,
                "mfa_live": False,
                "legal_hold_active": False,
                **_action_view(oid, events),
            }
        )
    return out


def _needs_you_projection(
    person_id: str,
    catalog_db: Path | str | None,
    assets_db: Path | str | None,
) -> dict[str, Any]:
    from core import msc_ops_needs_you_connective as nye

    try:
        strip = nye.needs_you_connective_strip(
            verified_person_id=person_id,
            catalog_db=catalog_db,
            assets_db=assets_db,
        )
    except nye.ConnectiveError:
        return {
            "ok": True,
            "empty": True,
            "in_scope": False,
            "count": 0,
            "duplicate_mutate_surface": False,
            "register_mutated": False,
            "why": (
                "This seat is outside the MSC Needs-You strip. "
                "No second mutate surface was opened."
            ),
        }
    out = dict(strip)
    out["duplicate_mutate_surface"] = False
    out["register_mutated"] = False
    out["bzg_compose"] = False
    out["in_scope"] = True
    return out


def _msc_desk_projection(
    person_id: str,
    *,
    catalog_db: Path | str | None,
    assets_db: Path | str | None,
) -> dict[str, Any]:
    try:
        desk = msc.build_desk(
            verified_person_id=person_id,
            catalog_db=catalog_db,
            assets_db=assets_db,
        )
    except msc.MgmtClusterError as exc:
        raise AssetDepthError(str(exc), code="forbidden", http_status=403) from exc
    modules = []
    for card in desk.get("modules") or []:
        strip = card.get("honesty_strip") or {}
        modules.append(
            {
                "id": card.get("id"),
                "cap": card.get("cap"),
                "cr": card.get("cr"),
                "ledger_maturity": card.get("ledger_maturity"),
                "cr_state": card.get("cr_state"),
                "cr_resolved": False,
                "status": strip.get("status"),
                "empty": strip.get("empty"),
                "inventory_count": None,
                "compliance_done": False,
                "mfa_live": False,
                "legal_hold_active": False,
            }
        )
    return {
        "ok": True,
        "bound": desk.get("bound"),
        "schema_id": desk.get("schema_id"),
        "module_count": desk.get("module_count"),
        "empty_count": desk.get("empty_count"),
        "modules": modules,
        "href": DESK_ANCHOR,
        "register_mutated": False,
        "duplicate_mutate_surface": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    rows = _asset_rows(db_path)
    events = _load_events(events_path(events_file))
    projected = [_project_asset(row, events) for row in rows]
    maintenance = [_project_maintenance(row, events) for row in rows]
    empty = len(rows) == 0
    placeholder = [_empty_placeholder(events)] if empty else []
    desk_objects = _desk_objects(events)
    objects = placeholder + projected + maintenance + desk_objects
    open_objects = [obj for obj in objects if not obj.get("dismissed_noise")]
    if empty:
        empty_message = (
            "No asset rows. Empty is not an inventory count, not compliance-done, "
            "not live MFA, and not a legal hold. CAP-MSC-01 stays SPECIFIED."
        )
    else:
        empty_message = None
    register = assets.build_register(db_path, catalog_db=catalog_db)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "seat": seat,
        "href": DESK_ANCHOR,
        "asset_href": ASSET_HREF,
        "assets": projected,
        "asset_count": len(projected),
        "maintenance": maintenance,
        "maintenance_count": len(maintenance),
        "empty_placeholder": placeholder[0] if placeholder else None,
        "msc_objects": desk_objects,
        "objects": objects,
        "open_count": len(open_objects),
        "empty": empty,
        "empty_message": empty_message,
        "recorded_count": register.get("recorded_count"),
        "recorded_is_inventory": False,
        "inventory_count": None,
        "inventory_complete": False,
        "service_proved": False,
        "register": {
            "empty": register.get("empty"),
            "recorded_count": register.get("recorded_count"),
            "inventory_count": None,
            "recorded_is_inventory": False,
            "cap": assets.CAP_ID,
        },
        "msc_desk": _msc_desk_projection(
            seat["person_id"],
            catalog_db=catalog_db,
            assets_db=db_path,
        ),
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db, db_path),
        "register_mutated": False,
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
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
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    token = (object_id or "").strip()
    rows = _asset_rows(db_path)
    by_id = {str(row.get("id")): row for row in rows}
    if token == EMPTY_ID:
        if rows:
            raise AssetDepthError(
                "The register has noted rows. The empty placeholder is not a second inventory.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "empty_placeholder",
            "object_id": EMPTY_ID,
            "asset": None,
            "module_id": None,
        }
    if token.startswith("MSC-DESK-"):
        module_id = token[len("MSC-DESK-") :]
        if module_id not in DESK_MODULE_IDS:
            raise AssetDepthError(
                "Unknown MSC desk object. It was not invented.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "msc_desk",
            "object_id": token,
            "asset": None,
            "module_id": module_id,
        }
    if token.startswith("MAINT-"):
        asset_id = token[6:]
        row = by_id.get(asset_id)
        if row is None:
            raise AssetDepthError(
                "Maintenance note was not found. A missing note is not a completed service.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "maintenance",
            "object_id": token,
            "asset": row,
            "module_id": None,
        }
    row = by_id.get(token)
    if row is None:
        raise AssetDepthError(
            "Asset was not found. It was not invented.",
            code="not_found",
            http_status=404,
        )
    return {
        "object_kind": "asset",
        "object_id": token,
        "asset": row,
        "module_id": None,
    }


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id)
    events = _load_events(events_path(events_file))
    found = _find_object(object_id, db_path=db_path, events=events)
    oid = found["object_id"]
    asset = found["asset"]
    detail = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "seat": seat,
        "object_id": oid,
        "object_kind": found["object_kind"],
        "module_id": found["module_id"],
        "asset": asset,
        "maintenance": _maintenance_block(asset),
        "actions": _action_view(oid, events),
        "events": _events_for(events, oid),
        "empty": found["object_kind"] == "empty_placeholder",
        "inventory_count": None,
        "inventory_complete": False,
        "compliance_done": False,
        "mfa_live": False,
        "legal_hold_active": False,
        "service_proved": False,
        "register_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
    if found["object_kind"] == "empty_placeholder":
        detail["empty_message"] = (
            "No asset rows. Empty is not an inventory count and not a proved service."
        )
    if found["object_kind"] == "msc_desk":
        desk = _msc_desk_projection(
            seat["person_id"],
            catalog_db=catalog_db,
            assets_db=db_path,
        )
        module = next(
            (m for m in desk.get("modules") or [] if m.get("id") == found["module_id"]),
            None,
        )
        detail["msc_module"] = module
        detail["cap_ceiling"] = "SPECIFIED" if (module or {}).get("cap") != "CAP-MSC-02" else "BUILT"
    return detail


def _clean_note(text: str) -> str:
    note = (text or "").strip()
    if len(note) < 2 or len(note) > 4000:
        raise AssetDepthError(
            "An operator note is required. A blank note is not a service and not an inventory count.",
            code="missing_note",
            http_status=400,
        )
    if assets._looks_like_count(note) or assets._looks_like_payment(note):
        raise AssetDepthError(
            "An operator note is not an inventory count and not a payment.",
            code="inventory_refused" if assets._looks_like_count(note) else "money_refused",
            http_status=403,
        )
    if _NOTE_BANNED.search(note):
        raise AssetDepthError(
            "An operator note cannot invent inventory, compliance, MFA, legal hold, or maturity.",
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
    db_path: Path | str | None = None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Record an allowed operator action. Does not write the asset register."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id)
    canon = _normalise_kind(kind)
    before_rows = _asset_rows(db_path)
    events_before = events_path(events_file)
    found = _find_object(
        object_id,
        db_path=db_path,
        events=_load_events(events_before),
    )
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise AssetDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        decision_token = (decision or "").strip().lower().replace("-", "_")
        banned_decision = _BANNED_KINDS.get(decision_token) or _BANNED_KINDS.get(
            decision_token.replace("_", "-")
        )
        if banned_decision:
            raise AssetDepthError(
                "A review decision does not complete inventory, compliance, MFA, or a legal hold.",
                code=banned_decision,
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise AssetDepthError(
                "decision must be still_specified, not_complete, or keep_as_note",
                code="invalid_decision",
                http_status=400,
            )
    path = events_path(events_file)
    event = {
        "event_id": f"EVT-{uuid.uuid4()}",
        "object_id": found["object_id"],
        "object_kind": found["object_kind"],
        "asset_id": (found["asset"] or {}).get("id"),
        "module_id": found["module_id"],
        "kind": canon,
        "note": text or None,
        "decision": decision_token,
        "person_id": seat["person_id"],
        "recorded_at": now_utc_iso(),
        "inventory_complete": False,
        "inventory_count": None,
        "compliance_done": False,
        "mfa_live": False,
        "legal_hold_active": False,
        "service_proved": False,
        "register_mutated": False,
        "bzg_compose": False,
    }
    _append_event(path, event)
    after_rows = _asset_rows(db_path)
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        db_path=db_path,
        events_file=path,
        catalog_db=catalog_db,
    )
    return {
        "ok": True,
        "action": "msc_asset_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": found["object_id"],
        "register_rows_unchanged": len(before_rows) == len(after_rows),
        "register_mutated": False,
        "msc_desk": {
            "module_count": (desk.get("msc_desk") or {}).get("module_count"),
            "empty_count": (desk.get("msc_desk") or {}).get("empty_count"),
            "href": DESK_ANCHOR,
            "register_mutated": False,
        },
        "asset_desk": {
            "asset_count": desk.get("asset_count"),
            "maintenance_count": desk.get("maintenance_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "open_count": desk.get("open_count"),
            "inventory_count": None,
            "href": DESK_ANCHOR,
        },
        "needs_you": desk.get("needs_you"),
        "inventory_complete": False,
        "inventory_count": None,
        "compliance_done": False,
        "mfa_live": False,
        "legal_hold_active": False,
        "service_proved": False,
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
        "money": None,
        "secret_mint": False,
        "cf_access_include_mutated": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
