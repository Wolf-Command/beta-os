#!/usr/bin/env python3
"""CRM Package Intelligence operator depth — Beta :8788 only.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + CAP-CRM-03
package product register. Plan:
docs/deliveries/GROK-PLAN-CRM-PACKAGE-INTEL-OPERATOR-DEPTH-2026-09-23.md.

Authorised Owner and existing CRM seats (Amanda, Haikal, Misa) open a
package, channel, margin-note, evidence, owner, or due slot, or the EMPTY
placeholder when the register has no rows, and record note /
next-action-touch / handoff-touch / dismiss-noise / review-decision.
Recording refreshes the CRM management desk and the CRM Needs-You
projection. It does not write the package register.

CAP-CRM-03 stays SPECIFIED. A margin note is not a market price. An empty
register is not a live census and not a booking. No Habitat cutover. No
Klaviyo write. No BZG compose. No Cloudflare Access Include mutate. No
secret mint. No money. No guest blast. No public post.
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

from core import crm_mgmt_cluster as cluster
from core import crm_ops_needs_you_connective as nye
from core import crm_package_intel as pkg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
DEFAULT_EVENTS = BETA_ROOT / "state" / "crm-package-intel" / "operator-events.jsonl"

BOUND = "beta-crm-loop-safe"
SCHEMA_ID = "wolf.crm-package-intel-operator-depth.v1"
SLICE = "crm_package_intel_operator_depth"
RUN_ID = "BF-crm-package-intel-operator-depth-20260923"
CLAIM_ID = "bf-crm-package-intel-operator-depth-20260923"
DESK_HREF = "/crm-package-intel"
DESK_ANCHOR = "/crm-package-intel#package-intel-depth"
CRM_DESK_HREF = "/crm-mgmt-cluster"
EMPTY_ID = "EMPTY-CRM-PKG"
DESK_OBJECT_ID = "CRM-DESK-PKG"
OWNER = cluster.OWNER
AMANDA = cluster.AMANDA
HAIKAL = cluster.HAIKAL
MISA = cluster.MISA
CRM_SEATS = frozenset({OWNER, AMANDA, HAIKAL, MISA})
PERM_LEAD_OPERATOR = cluster.PERM_CRM_OPERATOR
CAP_ID = pkg.CAP_ID
CR_ID = pkg.CR_ID

OPERATOR_SLOTS: tuple[dict[str, str], ...] = (
    {
        "kind": "package",
        "label": "Package",
        "why": "Named package slot. Empty is not a market census and not a price.",
    },
    {
        "kind": "channel",
        "label": "Channel",
        "why": "Named channel slot. Empty is not a live channel and not a booking.",
    },
    {
        "kind": "margin_note",
        "label": "Margin note",
        "why": "Named margin-note slot. Empty is not a market price and not a margin amount.",
    },
    {
        "kind": "evidence",
        "label": "Evidence",
        "why": "Named evidence slot. Empty is not invented evidence and not a price.",
    },
    {
        "kind": "owner",
        "label": "Owner",
        "why": "Named owner slot. Empty is not proof the package is live.",
    },
    {
        "kind": "due",
        "label": "Due",
        "why": "Named due slot. Empty is not a payment due and not an amount.",
    },
)

SLOT_OBJECT_IDS: dict[str, str] = {
    "package": "PKG-SLOT",
    "channel": "PKG-CHANNEL",
    "margin_note": "PKG-MARGIN-NOTE",
    "evidence": "PKG-EVIDENCE",
    "owner": "PKG-OWNER",
    "due": "PKG-DUE",
}
OBJECT_TO_SLOT = {value: key for key, value in SLOT_OBJECT_IDS.items()}
CHAIN: tuple[str, ...] = (
    "package",
    "channel",
    "margin_note",
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
CRM_CRS: tuple[str, ...] = nye.CRM_TARGET_CRS

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_specified", "not_market_truth", "keep_as_note"})
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
    "price": "price_as_market_refused",
    "price-as-market": "price_as_market_refused",
    "price_as_market": "price_as_market_refused",
    "margin": "price_as_market_refused",
    "census": "live_census_refused",
    "live-census": "live_census_refused",
    "live_census": "live_census_refused",
    "invent-live-census": "live_census_refused",
    "invent_live_census": "live_census_refused",
    "booking": "live_booking_refused",
    "live-booking": "live_booking_refused",
    "live_booking": "live_booking_refused",
    "invent-booking": "live_booking_refused",
    "invent_booking": "live_booking_refused",
    "habitat": "habitat_refused",
    "habitat-cutover": "habitat_refused",
    "habitat_cutover": "habitat_refused",
    "cutover": "habitat_refused",
    "klaviyo": "klaviyo_refused",
    "klaviyo-write": "klaviyo_refused",
    "klaviyo_write": "klaviyo_refused",
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
        "price",
        "price_as_market",
        "price-as-market",
        "margin",
        "census",
        "live_census",
        "live-census",
        "invent_live_census",
        "invent-live-census",
        "booking",
        "live_booking",
        "live-booking",
        "invent_booking",
        "invent-booking",
        "habitat",
        "habitat_cutover",
        "habitat-cutover",
        "cutover",
        "klaviyo",
        "klaviyo_write",
        "klaviyo-write",
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
    r"staff[_\s-]?ready|\bproven\b|\bready\b|live[_\s-]?census|live[_\s-]?booking|"
    r"price[_\s-]?as[_\s-]?market|habitat|klaviyo|guest[_\s-]?blast|public[_\s-]?post|"
    r"\b(payment|idr|usd|invoice|transfer|booking)\b|\$\s*\d",
    re.IGNORECASE,
)
_REFUSE_TAILS = dict(_BANNED_KINDS)
_PKG_RE = pkg._PKG_RE

_NULL_METRICS: dict[str, Any] = {
    "price": None,
    "margin": None,
    "pricing_is_truth": False,
    "price_as_market": False,
    "market_package_count": None,
    "channel": None,
    "due": None,
    "money": None,
    "live_census": False,
    "invented_live_census": False,
    "live_booking_write": False,
    "booking_mutated": False,
    "habitat_commissioned": False,
    "habitat_cutover": False,
    "klaviyo_write": False,
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
    "invented_channel": False,
    "invented_margin": False,
    "invented_due": False,
    "invented_live_census": False,
    "live_census": False,
    "live_booking_write": False,
    "booking_mutated": False,
    "price": None,
    "margin": None,
    "pricing_is_truth": False,
    "price_as_market": False,
    "market_package_count": None,
    "empty_is_census": False,
    "empty_is_price": False,
    "empty_is_ready": False,
    "habitat_commissioned": False,
    "habitat_cutover": False,
    "klaviyo_write": False,
    "guest_blast": False,
    "public_post": False,
    "bzg_compose": False,
    "money": None,
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
    "crm_package_intel_operator_depth": True,
    "inside_package_intel_desk_not_orphan_dashboard": True,
}


class PackageDepthError(ValueError):
    """Fail closed. Does not invent a census, a price, or a booking."""

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
        raise PackageDepthError(
            "CRM package-intel operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if name == "money.sqlite" or "payment" in name:
        raise PackageDepthError(
            "CRM package-intel operator depth refuses money",
            code="money_refused",
            http_status=403,
        )
    if name == pkg.DEFAULT_DB.name or "booking" in name:
        raise PackageDepthError(
            "Operator depth does not write the package register.",
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
        raise PackageDepthError(
            "CRM package-intel operator depth refuses a path outside Beta",
            code="production_refused",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env = (os.environ.get("WOLF_CRM_PKG_OPS_EVENTS") or "").strip()
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


def honesty_flags(*, catalog_db: Path | str | None = None) -> dict[str, Any]:
    flags = dict(HONESTY)
    try:
        snap = nye.connective_cap_honesty(catalog_db=catalog_db)
    except Exception:  # noqa: BLE001
        snap = {
            "caps": {},
            "crm_crs": {},
            "progress_core_crs": {},
            "au_crm_01_habitat": "NOT STARTED",
        }
    flags["caps"] = snap.get("caps") or {}
    flags["crm_crs"] = snap.get("crm_crs") or {
        cr: _cr_state(cr, catalog=catalog_db) for cr in CRM_CRS
    }
    flags["progress_core_crs"] = {
        cr: _cr_state(cr, catalog=catalog_db) for cr in PROGRESS_CRS
    }
    flags["global_nav_crs"] = {cr: _cr_state(cr, catalog=catalog_db) for cr in NAV_CRS}
    caps = flags["caps"] or {}
    flags["cap_crm_01"] = caps.get("CAP-CRM-01") or _ledger_cap("CAP-CRM-01")
    flags["cap_crm_02"] = caps.get("CAP-CRM-02") or _ledger_cap("CAP-CRM-02")
    flags["cap_crm_03"] = _ledger_cap(CAP_ID)
    flags["cap_crm_04"] = caps.get("CAP-CRM-04") or _ledger_cap("CAP-CRM-04")
    flags["au_crm_01_habitat"] = snap.get("au_crm_01_habitat") or "NOT STARTED"
    flags["cr_id"] = CR_ID
    flags["cr_state"] = _cr_state(CR_ID, catalog=catalog_db)
    flags["ledger_maturity"] = flags["cap_crm_03"]
    flags["maturity_ceiling"] = "SPECIFIED"
    flags["skeleton_ceiling"] = "BUILT"
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["price"] = None
    flags["margin"] = None
    flags["pricing_is_truth"] = False
    flags["price_as_market"] = False
    flags["market_package_count"] = None
    flags["live_census"] = False
    flags["live_booking_write"] = False
    flags["booking_mutated"] = False
    flags["habitat_commissioned"] = False
    flags["habitat_cutover"] = False
    flags["klaviyo_write"] = False
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
        "crm_desk": CRM_DESK_HREF,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "empty_object_id": EMPTY_ID,
        "slot_object_ids": dict(SLOT_OBJECT_IDS),
        "chain": list(CHAIN),
        "cap": CAP_ID,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "price_accepted": False,
        "price_as_market_accepted": False,
        "live_census_accepted": False,
        "live_booking_accepted": False,
        "habitat_cutover_accepted": False,
        "klaviyo_write_accepted": False,
        "guest_blast_accepted": False,
        "public_post_accepted": False,
        "payment_accepted": False,
        "additionalProperties": False,
    }


def _package_id(token: str) -> str | None:
    raw = (token or "").strip()
    if not raw.upper().startswith("PKG-"):
        return None
    candidate = "PKG-" + raw[4:].lower()
    if _PKG_RE.fullmatch(candidate):
        return candidate
    return None


def _object_tail(tail: str) -> bool:
    token = (tail or "").strip()
    upper = token.upper()
    if upper in {EMPTY_ID, DESK_OBJECT_ID}:
        return True
    if upper in OBJECT_TO_SLOT:
        return True
    return _package_id(token) is not None


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    if "/api/crm/package-intel/operator-depth" not in p:
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
        "message": f"CRM package-intel operator depth refuses: {code}",
        **_NULL_METRICS,
        "bzg_compose": False,
        "register_mutated": False,
        **honesty_flags(),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_refused",
        "message": (
            "CRM package-intel operator depth records only the allowed POST actions. "
            "This method does not store a price, a census, or a booking."
        ),
        "register_mutated": False,
        "live_census": False,
        "live_booking_write": False,
        "price": None,
        "margin": None,
        "pricing_is_truth": False,
        "habitat_cutover": False,
        "klaviyo_write": False,
        "guest_blast": False,
        "public_post": False,
        "bzg_compose": False,
        **honesty_flags(),
    }


def not_found_read(path: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "not_found",
        "message": "CRM package-intel operator depth has no such read.",
        "path": path,
        **_NULL_METRICS,
        "register_mutated": False,
        "bzg_compose": False,
        **honesty_flags(),
    }


def _existing_crm_permission(person_id: str) -> bool:
    """Read an existing grant. This slice does not insert a permission."""
    from core import rbac as _rbac

    try:
        if _rbac.can(person_id, PERM_LEAD_OPERATOR):
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


def require_seat(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner or an existing CRM seat. Does not grant a seat.

    catalog_db is accepted so callers can pass a fixture. Seats are the
    existing CRM operator fixtures and are not loaded from a new grant table.
    A non-owner seat still needs the existing crm.lead.operator grant.
    """
    del catalog_db
    pid = (person_id or "").strip()
    if not pid:
        raise PackageDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    if pid not in CRM_SEATS:
        raise PackageDepthError(
            "CRM package-intel operator depth is Owner or an existing CRM seat "
            "(Amanda, Haikal, Misa). This slice does not grant a seat.",
            code="outsider",
            http_status=403,
        )
    if pid != OWNER and not _existing_crm_permission(pid):
        raise PackageDepthError(
            "existing CRM seat permission is not present; this slice does not grant it",
            code="denied",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": "owner" if pid == OWNER else "crm",
        "authorised": True,
        "invented_permission_grant": False,
        "live_census": False,
        "price": None,
        "margin": None,
        "pricing_is_truth": False,
        "live_booking_write": False,
        "habitat_cutover": False,
        "klaviyo_write": False,
    }


def prove_rbac(
    *,
    person_id: str,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(person_id, catalog_db=catalog_db)
    return {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "person_id": seat["person_id"],
        "seat": seat["seat"],
        "can_package_operator": True,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "price_as_market": False,
            "live_census": False,
            "live_booking": False,
            "habitat_cutover": False,
            "klaviyo_write": False,
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
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _normalise_kind(kind: str) -> str:
    raw = (kind or "").strip().lower()
    if raw in _BANNED_KINDS:
        code = _BANNED_KINDS[raw]
        raise PackageDepthError(
            f"CRM package-intel operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise PackageDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise PackageDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key) or _BANNED_KINDS.get(key.replace("_", "-"), "refused_field")
        raise PackageDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise PackageDepthError(
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


def _products(db_path: Path | str | None) -> list[dict[str, Any]]:
    return list(pkg.list_products(db_path))


def _register_stamp(db_path: Path | str | None) -> int | None:
    if db_path is None and not (os.environ.get("WOLF_CRM_PACKAGE_DB") or "").strip():
        path = pkg.DEFAULT_DB
    else:
        path = pkg._resolve_db(db_path)
    if not path.is_file():
        return None
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _slot_row(kind: str) -> dict[str, str]:
    return next(item for item in OPERATOR_SLOTS if item["kind"] == kind)


def _evidence_refs(products: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for row in products:
        for ref in row.get("evidence_refs") or []:
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    return refs


def _owners(products: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for row in products:
        owner = row.get("recorded_by")
        if isinstance(owner, str) and owner and owner not in found:
            found.append(owner)
    return found


def _slot_filled(kind: str, products: list[dict[str, Any]]) -> bool:
    """Only fields the register already stores. Channel, margin, and due stay empty."""
    if kind == "package":
        return bool(products)
    if kind == "evidence":
        return bool(_evidence_refs(products))
    if kind == "owner":
        return bool(_owners(products))
    return False


def _public_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "brand": row.get("brand"),
        "status": row.get("status"),
        "evidence_refs": list(row.get("evidence_refs") or []),
        "recorded_at": row.get("recorded_at"),
        "recorded_by": row.get("recorded_by"),
        "price": None,
        "margin": None,
        "pricing_is_truth": False,
        "channel": None,
        "due": None,
    }


def _slot_card(
    kind: str,
    events: list[dict[str, Any]],
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    oid = SLOT_OBJECT_IDS[kind]
    row = _slot_row(kind)
    filled = _slot_filled(kind, products)
    card: dict[str, Any] = {
        "object_id": oid,
        "object_kind": "package_slot",
        "slot": kind,
        "label": row.get("label"),
        "slot_state": "named" if filled else "empty",
        "href": f"{DESK_ANCHOR}-{oid}",
        "empty": not filled,
        **_NULL_METRICS,
        "why": row.get("why"),
        **_action_view(oid, events),
    }
    if kind == "package":
        card["product_count"] = len(products)
        card["products"] = [_public_product(item) for item in products]
    elif kind == "evidence":
        card["evidence_refs"] = _evidence_refs(products)
    elif kind == "owner":
        card["recorded_by"] = _owners(products)
    return card


def _package_row_card(row: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    oid = str(row.get("id") or "")
    return {
        **_public_product(row),
        "object_id": oid,
        "object_kind": "package_row",
        "slot": "package",
        "href": f"{DESK_ANCHOR}-{oid}",
        "empty": False,
        "chain": [
            {"slot": kind, "object_id": SLOT_OBJECT_IDS[kind]} for kind in CHAIN
        ],
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
            "No package rows. Empty is not a market census, not a price, "
            "not a booking, and not CAP-CRM-03 PROVEN."
        ),
        **_action_view(EMPTY_ID, events),
    }


def _desk_card(events: list[dict[str, Any]], *, empty: bool) -> dict[str, Any]:
    return {
        "object_id": DESK_OBJECT_ID,
        "object_kind": "crm_package_desk",
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
            "staff_ready": False,
            "proven": False,
            "ready": False,
            "live_census": False,
            "price": None,
            "margin": None,
            "why": (
                "This seat is outside the CRM Needs-You strip. "
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
        "in_scope": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "live_census": False,
        "live_booking_write": False,
        "price": None,
        "margin": None,
        "pricing_is_truth": False,
        "habitat_cutover": False,
        "klaviyo_write": False,
        "guest_blast": False,
        "public_post": False,
        "href": "/lead-spine",
    }


def _crm_desk_projection(
    person_id: str,
    *,
    catalog_db: Path | str | None,
    package_db: Path | str | None,
) -> dict[str, Any]:
    try:
        desk = cluster.build_desk(
            verified_person_id=person_id,
            catalog_db=catalog_db,
            package_db=package_db,
        )
    except cluster.MgmtClusterError as exc:
        raise PackageDepthError(str(exc), code="outsider", http_status=403) from exc
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
            }
        )
    return {
        "ok": True,
        "bound": desk.get("bound"),
        "schema_id": desk.get("schema_id"),
        "module_count": desk.get("module_count"),
        "empty_count": desk.get("empty_count"),
        "modules": modules,
        "href": CRM_DESK_HREF,
        "package_href": DESK_ANCHOR,
        "caps_raised": False,
        "cr_resolved": False,
        "register_mutated": False,
        "duplicate_mutate_surface": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "live_census": False,
        "price": None,
        "margin": None,
        "pricing_is_truth": False,
        "live_booking_write": False,
        "habitat_cutover": False,
        "klaviyo_write": False,
        "guest_blast": False,
        "public_post": False,
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    products = _products(db_path)
    events = _load_events(events_path(events_file))
    recorded = len(products)
    empty = recorded == 0
    slots = [_slot_card(kind, events, products) for kind in SLOT_OBJECT_IDS]
    rows = [_package_row_card(row, events) for row in products]
    placeholder = [_empty_placeholder(events)] if empty else []
    desk_card = _desk_card(events, empty=empty)
    objects = placeholder + slots + rows + [desk_card]
    open_objects = [obj for obj in objects if not obj.get("dismissed_noise")]
    if empty:
        empty_message = (
            "No package rows. Empty is not a market census, not a price, "
            "not a booking, and not a Habitat or Klaviyo write. CAP-CRM-03 stays SPECIFIED."
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
        "package_href": DESK_HREF,
        "chain": list(CHAIN),
        "slots": slots,
        "slot_count": len(slots),
        "packages": rows,
        "empty_placeholder": placeholder[0] if placeholder else None,
        "package_desk_card": desk_card,
        "objects": objects,
        "open_count": len(open_objects),
        "empty": empty,
        "empty_message": empty_message,
        "recorded_count": recorded,
        **_NULL_METRICS,
        "register": {
            "empty": empty,
            "recorded_count": recorded,
            "cap": CAP_ID,
            "price": None,
            "margin": None,
            "pricing_is_truth": False,
            "market_package_count": None,
            "live_census": False,
            "live_booking_write": False,
        },
        "crm_desk": _crm_desk_projection(
            seat["person_id"],
            catalog_db=catalog_db,
            package_db=db_path,
        ),
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db),
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
) -> dict[str, Any]:
    token = (object_id or "").strip()
    upper = token.upper()
    products = _products(db_path)
    recorded = len(products)
    if upper == EMPTY_ID:
        if recorded != 0:
            raise PackageDepthError(
                "The register has package rows. The empty placeholder is not a second catalog.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "empty_placeholder",
            "object_id": EMPTY_ID,
            "slot": None,
            "product": None,
        }
    if upper == DESK_OBJECT_ID:
        return {
            "object_kind": "crm_package_desk",
            "object_id": DESK_OBJECT_ID,
            "slot": None,
            "product": None,
        }
    kind = OBJECT_TO_SLOT.get(upper)
    if kind is not None:
        return {
            "object_kind": "package_slot",
            "object_id": upper,
            "slot": kind,
            "product": None,
        }
    package_id = _package_id(token)
    if package_id:
        row = next((item for item in products if item.get("id") == package_id), None)
        if row is None:
            raise PackageDepthError(
                "Package was not found. A missing row was not invented as a price or a booking.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "package_row",
            "object_id": row.get("id"),
            "slot": "package",
            "product": row,
        }
    raise PackageDepthError(
        "Package card was not found. A missing card was not invented as a census or a price.",
        code="not_found",
        http_status=404,
    )


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    events = _load_events(events_path(events_file))
    products = _products(db_path)
    found = _find_object(object_id, db_path=db_path)
    oid = str(found["object_id"])
    slot = dict(_slot_row(found["slot"])) if found["slot"] else None
    filled = bool(found["slot"] and _slot_filled(found["slot"], products))
    if found["object_kind"] == "package_row":
        filled = True
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
        "empty": not filled if found["object_kind"] != "crm_package_desk" else len(products) == 0,
        "chain": [
            {"slot": kind, "object_id": SLOT_OBJECT_IDS[kind]} for kind in CHAIN
        ],
        **_NULL_METRICS,
        "register_mutated": False,
        "cap": CAP_ID,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
    detail["cap_state"] = (detail["honesty"] or {}).get("cap_crm_03")
    if found["object_kind"] == "empty_placeholder":
        detail["empty"] = True
        detail["empty_message"] = (
            "No package rows. Empty is not a market census and not a price."
        )
    if found["slot"] == "package":
        detail["products"] = [_public_product(item) for item in products]
        detail["product_count"] = len(products)
    if found["slot"] == "evidence":
        detail["evidence_refs"] = _evidence_refs(products)
    if found["slot"] == "owner":
        detail["recorded_by"] = _owners(products)
    if found["object_kind"] == "package_row" and found["product"]:
        detail["product"] = _public_product(found["product"])
        detail["empty"] = False
    if found["object_kind"] == "crm_package_desk":
        detail["crm_desk"] = _crm_desk_projection(
            seat["person_id"],
            catalog_db=catalog_db,
            package_db=db_path,
        )
        detail["cap_ceiling"] = "SPECIFIED"
        detail["needs_you"] = _needs_you_projection(seat["person_id"], catalog_db)
    return detail


def _clean_note(text: str) -> str:
    note = (text or "").strip()
    if len(note) < 2 or len(note) > 4000:
        raise PackageDepthError(
            "An operator note is required. A blank note is not a price and not a census.",
            code="missing_note",
            http_status=400,
        )
    if _NOTE_BANNED.search(note):
        raise PackageDepthError(
            "An operator note cannot invent a market price, a live census, a booking, "
            "a Habitat cutover, a Klaviyo write, a guest blast, a public post, or maturity.",
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
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record an allowed operator action. Does not write the package register."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    canon = _normalise_kind(kind)
    before_stamp = _register_stamp(db_path)
    before_count = len(_products(db_path))
    found = _find_object(object_id, db_path=db_path)
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise PackageDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        decision_token = (decision or "").strip().lower().replace("-", "_")
        banned_decision = _BANNED_KINDS.get(decision_token) or _BANNED_KINDS.get(
            decision_token.replace("_", "-")
        )
        if banned_decision:
            raise PackageDepthError(
                "A review decision does not prove a price, a census, or a booking.",
                code=banned_decision,
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise PackageDepthError(
                "decision must be still_specified, not_market_truth, or keep_as_note",
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
        "bzg_compose": False,
    }
    _append_event(path, event)
    after_count = len(_products(db_path))
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        events_file=path,
        catalog_db=catalog_db,
        db_path=db_path,
    )
    return {
        "ok": True,
        "action": "crm_package_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": found["object_id"],
        "register_unchanged": (
            before_count == after_count and _register_stamp(db_path) == before_stamp
        ),
        "register_mutated": False,
        "crm_desk": {
            "module_count": (desk.get("crm_desk") or {}).get("module_count"),
            "empty_count": (desk.get("crm_desk") or {}).get("empty_count"),
            "href": CRM_DESK_HREF,
            "caps_raised": False,
            "cr_resolved": False,
            "register_mutated": False,
        },
        "package_desk": {
            "slot_count": desk.get("slot_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "open_count": desk.get("open_count"),
            "recorded_count": desk.get("recorded_count"),
            "price": None,
            "margin": None,
            "market_package_count": None,
            "live_census": False,
            "live_booking_write": False,
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
