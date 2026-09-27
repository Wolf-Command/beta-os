#!/usr/bin/env python3
"""GGV intercompany client operator depth — Beta :8788 only.

Decision served: keep_building_without_matt
(state/build-claims/owner-autonomous-release-2026-09-19.json) + CAP-GGV-06
intercompany client mode. Plan:
docs/deliveries/GROK-PLAN-GGV-INTERCOMPANY-CLIENT-OPERATOR-DEPTH-2026-09-23.md.

Authorised Owner and existing GGV seats (Amanda, Haikal, Misa) open a
service-record, invoice, allocation, arms-length, AR/AP, or notes slot, or
the EMPTY placeholder when the framework has no intercompany evidence, and
record note / next-action-touch / handoff-touch / dismiss-noise /
review-decision. Recording refreshes the GGV management desk and the
GGV Needs-You projection. It does not store an invoice, an allocation, an
AR/AP balance, a tax treatment, or a payment, and it does not raise CAP-GGV-06.

CAP-GGV-06 stays SPECIFIED. The intercompany skeleton stays empty.
No invent staff_ready / PROVEN / READY / live billing / invoice / AR-AP /
tax / bank / books / Alchemist. No BZG compose. No Cloudflare Access Include
mutate. No secret mint. No money. No guest blast. No public post.
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

from core import ggv_intercompany_client as ic
from core import ggv_ops_pack as pack

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
DEFAULT_EVENTS = BETA_ROOT / "state" / "ggv-intercompany-client" / "operator-events.jsonl"

BOUND = "beta-ggv-ops-safe"
SCHEMA_ID = "wolf.ggv-intercompany-client-operator-depth.v1"
SLICE = "ggv_intercompany_client_operator_depth"
RUN_ID = "BF-ggv-intercompany-client-operator-depth-20260923"
CLAIM_ID = "bf-ggv-intercompany-client-operator-depth-20260923"
DESK_HREF = "/ggv-intercompany-client"
DESK_ANCHOR = "/ggv-intercompany-client#interco-depth"
GGV_DESK_HREF = "/ggv-mgmt-cluster"
EMPTY_ID = "EMPTY-GGV-IC"
DESK_OBJECT_ID = "GGV-DESK-IC"
OWNER = pack.OWNER
CAP_ID = ic.CAP_ID
CR_ID = ic.CR_ID

OPERATOR_SLOTS: tuple[dict[str, str], ...] = (
    {
        "kind": "service_record",
        "label": "Service record",
        "why": "Named service-record slot. Empty is not a service record and not live intercompany billing.",
    },
    {
        "kind": "invoice",
        "label": "Invoice",
        "why": "Named invoice slot. Empty is not an invoice and not live intercompany billing.",
    },
    {
        "kind": "allocation",
        "label": "Allocation",
        "why": "Named allocation slot. Empty is not an allocation and not live intercompany billing.",
    },
    {
        "kind": "arms_length",
        "label": "Arms length",
        "why": "Named arms-length slot. Empty is not arms-length evidence and not proof of client machinery.",
    },
    {
        "kind": "ar_ap",
        "label": "AR/AP",
        "why": "Named AR/AP slot. Empty is not an AR or AP balance and not live intercompany billing.",
    },
    {
        "kind": "notes",
        "label": "Notes",
        "why": "Named notes slot. Empty is not a billing note and not live intercompany billing.",
    },
)

SLOT_OBJECT_IDS: dict[str, str] = {
    "service_record": "IC-SERVICE-RECORD",
    "invoice": "IC-INVOICE",
    "allocation": "IC-ALLOCATION",
    "arms_length": "IC-ARMS-LENGTH",
    "ar_ap": "IC-AR-AP",
    "notes": "IC-NOTES",
}
OBJECT_TO_SLOT = {value: key for key, value in SLOT_OBJECT_IDS.items()}

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

ACTION_KINDS = frozenset(
    {"note", "next_action", "handoff_touch", "dismiss_noise", "review_decision"}
)
REVIEW_DECISIONS = frozenset({"still_specified", "not_live_billing", "keep_as_note"})
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
    "zayen": "books_refused",
    "money": "money_refused",
    "alchemist": "alchemist_refused",
    "alchemist-write": "alchemist_refused",
    "alchemist_write": "alchemist_refused",
    "live-billing": "live_billing_refused",
    "live_billing": "live_billing_refused",
    "invent-live-billing": "live_billing_refused",
    "invent_live_billing": "live_billing_refused",
    "current": "live_billing_refused",
    "invoice": "invent_invoice_refused",
    "invent-invoice": "invent_invoice_refused",
    "invent_invoice": "invent_invoice_refused",
    "allocation": "invent_allocation_refused",
    "invent-allocation": "invent_allocation_refused",
    "invent_allocation": "invent_allocation_refused",
    "ar-ap": "invent_ar_ap_refused",
    "ar_ap": "invent_ar_ap_refused",
    "invent-ar-ap": "invent_ar_ap_refused",
    "invent_ar_ap": "invent_ar_ap_refused",
    "service-record": "live_billing_refused",
    "service_record": "live_billing_refused",
    "arms-length": "live_billing_refused",
    "arms_length": "live_billing_refused",
    "notes": "live_billing_refused",
    "tax": "tax_refused",
    "tax-write": "tax_refused",
    "tax_write": "tax_refused",
    "tax-treatment": "tax_refused",
    "tax_treatment": "tax_refused",
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
        "zayen",
        "money",
        "alchemist",
        "alchemist_write",
        "alchemist-write",
        "live_billing",
        "live-billing",
        "invent_live_billing",
        "invent-live-billing",
        "invoice",
        "invent_invoice",
        "invent-invoice",
        "allocation",
        "invent_allocation",
        "invent-allocation",
        "ar_ap",
        "ar-ap",
        "invent_ar_ap",
        "invent-ar-ap",
        "service_record",
        "service-record",
        "arms_length",
        "arms-length",
        "tax",
        "tax_write",
        "tax-write",
        "tax_treatment",
        "tax-treatment",
        "current",
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
    r"staff[_\s-]?ready|\bproven\b|\bready\b|live[_\s-]?billing|"
    r"invent[_\s-]?(live[_\s-]?billing|invoice)|alchemist|"
    r"guest[_\s-]?blast|public[_\s-]?post|"
    r"\b(payment|idr|usd|invoice|allocation|transfer|tax)\b|"
    r"ar[/\s_-]?ap|\$\s*\d",
    re.IGNORECASE,
)
_REFUSE_TAILS = dict(_BANNED_KINDS)

_NULL_METRICS: dict[str, Any] = {
    "service_record": None,
    "invoice": None,
    "allocation": None,
    "arms_length": None,
    "ar_ap": None,
    "tax_treatment": None,
    "tax_claimed": False,
    "payment": None,
    "money": None,
    "live_billing": False,
    "client_machinery": False,
    "invented_invoice": False,
    "invented_allocation": False,
    "invented_ar_ap": False,
    "invented_tax": False,
    "alchemist_write": False,
    "books_write": False,
    "bank_write": False,
    "zayen_write": False,
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
    "invented_invoice": False,
    "invented_allocation": False,
    "invented_ar_ap": False,
    "invented_tax": False,
    "live_billing": False,
    "client_machinery": False,
    "service_record": None,
    "invoice": None,
    "allocation": None,
    "arms_length": None,
    "ar_ap": None,
    "tax_treatment": None,
    "tax_claimed": False,
    "payment": None,
    "empty_is_billing": False,
    "empty_is_client_machinery": False,
    "empty_is_ready": False,
    "alchemist_write": False,
    "books_write": False,
    "bank_write": False,
    "zayen_write": False,
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
    "ggv_intercompany_client_operator_depth": True,
    "inside_intercompany_desk_not_orphan_dashboard": True,
    "skeleton_ceiling": "BUILT",
}


class IntercoDepthError(ValueError):
    """Fail closed. Does not invent live billing, an invoice, or a payment."""

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
        raise IntercoDepthError(
            "GGV intercompany operator depth refuses a production path",
            code="production_refused",
            http_status=403,
        )
    if name == "money.sqlite" or "payment" in name:
        raise IntercoDepthError(
            "GGV intercompany operator depth refuses money",
            code="money_refused",
            http_status=403,
        )
    if "tax" in name:
        raise IntercoDepthError(
            "GGV intercompany operator depth refuses a tax write",
            code="tax_refused",
            http_status=403,
        )
    if (
        "invoice" in name
        or "allocation" in name
        or "ar_ap" in name
        or "arap" in name
        or "arms_length" in name
        or "service_record" in name
    ):
        raise IntercoDepthError(
            "Operator depth does not store an invoice, an allocation, or an AR/AP balance.",
            code="invent_invoice_refused",
            http_status=403,
        )
    if name == ic.DEFAULT_DB.name:
        raise IntercoDepthError(
            "Operator depth does not write the intercompany framework store.",
            code="framework_refused",
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
        raise IntercoDepthError(
            "GGV intercompany operator depth refuses a path outside Beta",
            code="production_refused",
            http_status=403,
        ) from exc


def events_path(explicit: Path | str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env = (os.environ.get("WOLF_GGV_IC_OPS_EVENTS") or "").strip()
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
        snap = pack.connective_cap_honesty(catalog_db=catalog_db)
    except Exception:  # noqa: BLE001
        snap = {"caps": {}, "ggv_crs": {}, "progress_core_crs": {}}
    flags["caps"] = snap.get("caps") or {}
    flags["ggv_crs"] = snap.get("ggv_crs") or {
        cr: _cr_state(cr, catalog=catalog_db) for cr in pack.GGV_TARGET_CRS
    }
    flags["progress_core_crs"] = {
        cr: _cr_state(cr, catalog=catalog_db) for cr in PROGRESS_CRS
    }
    flags["global_nav_crs"] = {cr: _cr_state(cr, catalog=catalog_db) for cr in NAV_CRS}
    flags["cap_ggv_06"] = _ledger_cap(CAP_ID)
    flags["cr_id"] = CR_ID
    flags["cr_state"] = _cr_state(CR_ID, catalog=catalog_db)
    flags["ledger_maturity"] = flags["cap_ggv_06"]
    flags["maturity_ceiling"] = "SPECIFIED"
    flags["proven"] = False
    flags["ready"] = False
    flags["staff_ready"] = False
    flags["service_record"] = None
    flags["invoice"] = None
    flags["allocation"] = None
    flags["arms_length"] = None
    flags["ar_ap"] = None
    flags["tax_treatment"] = None
    flags["tax_claimed"] = False
    flags["payment"] = None
    flags["live_billing"] = False
    flags["client_machinery"] = False
    flags["invented_invoice"] = False
    flags["invented_allocation"] = False
    flags["invented_ar_ap"] = False
    flags["invented_tax"] = False
    flags["alchemist_write"] = False
    flags["books_write"] = False
    flags["bank_write"] = False
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
        "ggv_desk": GGV_DESK_HREF,
        "action_kinds": sorted(ACTION_KINDS),
        "review_decisions": sorted(REVIEW_DECISIONS),
        "empty_object_id": EMPTY_ID,
        "slot_object_ids": dict(SLOT_OBJECT_IDS),
        "cap": CAP_ID,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "payment_accepted": False,
        "bank_accepted": False,
        "books_accepted": False,
        "alchemist_write_accepted": False,
        "live_billing_accepted": False,
        "invoice_accepted": False,
        "allocation_accepted": False,
        "ar_ap_accepted": False,
        "tax_accepted": False,
        "guest_blast_accepted": False,
        "public_post_accepted": False,
        "additionalProperties": False,
    }


def _object_tail(tail: str) -> bool:
    token = (tail or "").strip()
    upper = token.upper()
    if upper == EMPTY_ID or upper == DESK_OBJECT_ID:
        return True
    return upper in OBJECT_TO_SLOT


def refuse_code(path: str) -> str | None:
    p = (path or "").rstrip("/").lower()
    if "/api/ggv/intercompany-client/operator-depth" not in p:
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
        "message": f"GGV intercompany operator depth refuses: {code}",
        **_NULL_METRICS,
        "bzg_compose": False,
        "framework_mutated": False,
        **honesty_flags(),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_refused",
        "message": (
            "GGV intercompany operator depth records only the allowed POST actions. "
            "This method does not store an invoice, an allocation, an AR/AP balance, or a payment."
        ),
        "framework_mutated": False,
        "live_billing": False,
        "invoice": None,
        "allocation": None,
        "ar_ap": None,
        "payment": None,
        "alchemist_write": False,
        "guest_blast": False,
        "public_post": False,
        "bzg_compose": False,
        **honesty_flags(),
    }


def not_found_read(path: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "not_found",
        "message": "GGV intercompany operator depth has no such read.",
        "path": path,
        **_NULL_METRICS,
        "framework_mutated": False,
        "bzg_compose": False,
        **honesty_flags(),
    }


def require_seat(
    person_id: str | None,
    *,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner or an existing GGV seat. Does not grant a seat.

    This slice does not insert a permission, a Cloudflare Access Include, or a secret.
    catalog_db is accepted so callers can pass a fixture; seats are the existing
    GGV read seats and are not loaded from a new grant table.
    """
    del catalog_db
    pid = (person_id or "").strip()
    if not pid:
        raise IntercoDepthError(
            "anonymous callers are refused",
            code="denied",
            http_status=403,
        )
    seat = pack.seat_for(pid)
    if seat is None:
        raise IntercoDepthError(
            "GGV intercompany operator depth is Owner or an existing GGV seat "
            "(Amanda, Haikal, Misa). This slice does not grant a seat.",
            code="outsider",
            http_status=403,
        )
    return {
        "person_id": seat["person_id"],
        "seat": seat.get("seat") or "ggv",
        "authorised": True,
        "invented_permission_grant": False,
        "live_billing": False,
        "invoice": None,
        "allocation": None,
        "ar_ap": None,
        "payment": None,
        "alchemist_write": False,
        "guest_blast": False,
        "public_post": False,
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
        "can_interco_operator": True,
        "actions": {
            "note": True,
            "next_action_touch": True,
            "handoff_touch": True,
            "dismiss_noise": True,
            "review_decision": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "payment": False,
            "bank": False,
            "books": False,
            "alchemist_write": False,
            "live_billing": False,
            "invoice": False,
            "allocation": False,
            "ar_ap": False,
            "tax_write": False,
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
        raise IntercoDepthError(
            f"GGV intercompany operator depth refuses {raw}",
            code=code,
            http_status=403,
        )
    canon = _ACTION_ALIASES.get(raw)
    if canon not in ACTION_KINDS:
        raise IntercoDepthError(
            "kind must be note, next-action-touch, handoff-touch, dismiss-noise, or review-decision",
            code="invalid_kind",
            http_status=400,
        )
    return canon


def _reject_body(body: dict) -> None:
    if not isinstance(body, dict):
        raise IntercoDepthError("payload must be an object", code="invalid")
    low = {str(k).lower() for k in body}
    banned = sorted(low & _BANNED_BODY)
    if banned:
        key = banned[0]
        code = _BANNED_KINDS.get(key) or _BANNED_KINDS.get(key.replace("_", "-"), "refused_field")
        raise IntercoDepthError(
            "refused field " + ",".join(banned),
            code=code,
            http_status=403,
        )
    extra = sorted(set(body) - _ALLOWED_BODY)
    if extra:
        raise IntercoDepthError(
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


def _framework_stamp() -> int | None:
    path = ic.DEFAULT_DB
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
        "object_kind": "interco_slot",
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
            "No intercompany evidence. Empty is not live intercompany billing, "
            "not an invoice, not an AR/AP balance, and not CAP-GGV-06 PROVEN."
        ),
        **_action_view(EMPTY_ID, events),
    }


def _desk_card(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_id": DESK_OBJECT_ID,
        "object_kind": "ggv_interco_desk",
        "cap": CAP_ID,
        "cr": CR_ID,
        "href": DESK_ANCHOR,
        "empty": True,
        **_NULL_METRICS,
        **_action_view(DESK_OBJECT_ID, events),
    }


def _needs_you_projection(
    person_id: str,
    catalog_db: Path | str | None,
) -> dict[str, Any]:
    try:
        strip = pack.needs_you_connective_strip(
            verified_person_id=person_id,
            db_path=catalog_db,
        )
    except pack.OpsPackError:
        return {
            "ok": True,
            "empty": True,
            "in_scope": False,
            "count": 0,
            "duplicate_mutate_surface": False,
            "framework_mutated": False,
            "staff_ready": False,
            "proven": False,
            "ready": False,
            "live_billing": False,
            "invoice": None,
            "allocation": None,
            "ar_ap": None,
            "payment": None,
            "why": (
                "This seat is outside the GGV Needs-You strip. "
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
        "framework_mutated": False,
        "in_scope": True,
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "live_billing": False,
        "invoice": None,
        "allocation": None,
        "ar_ap": None,
        "payment": None,
        "tax_treatment": None,
        "alchemist_write": False,
        "books_write": False,
        "bank_write": False,
        "guest_blast": False,
        "public_post": False,
        "href": "/ggv-ops-pack",
    }


def _ggv_desk_projection(
    person_id: str,
    *,
    catalog_db: Path | str | None,
) -> dict[str, Any]:
    from core import ggv_mgmt_cluster as cluster

    try:
        desk = cluster.build_desk(
            verified_person_id=person_id,
            catalog_db=catalog_db,
        )
    except cluster.MgmtClusterError as exc:
        raise IntercoDepthError(str(exc), code="outsider", http_status=403) from exc
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
            }
        )
    return {
        "ok": True,
        "bound": desk.get("bound"),
        "schema_id": desk.get("schema_id"),
        "module_count": desk.get("module_count"),
        "empty_count": desk.get("empty_count"),
        "modules": modules,
        "href": GGV_DESK_HREF,
        "interco_href": DESK_ANCHOR,
        "caps_raised": False,
        "cr_resolved": False,
        "framework_mutated": False,
        "duplicate_mutate_surface": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "live_billing": False,
        "invoice": None,
        "allocation": None,
        "ar_ap": None,
        "payment": None,
        "alchemist_write": False,
        "books_write": False,
        "bank_write": False,
        "guest_blast": False,
        "public_post": False,
    }


def operator_depth_desk(
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    framework = ic.build_framework(catalog_db=catalog_db)
    events = _load_events(events_path(events_file))
    recorded = int(framework.get("recorded_count") or 0)
    empty = recorded == 0
    slots = [_slot_card(kind, events) for kind in SLOT_OBJECT_IDS]
    placeholder = [_empty_placeholder(events)] if empty else []
    desk_card = _desk_card(events)
    objects = placeholder + slots + [desk_card]
    open_objects = [obj for obj in objects if not obj.get("dismissed_noise")]
    if empty:
        empty_message = (
            "No intercompany evidence. Empty is not live intercompany billing, "
            "not an invoice, not an allocation, and not an AR/AP balance. "
            "CAP-GGV-06 stays SPECIFIED."
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
        "interco_href": DESK_HREF,
        "slots": slots,
        "slot_count": len(slots),
        "empty_placeholder": placeholder[0] if placeholder else None,
        "interco_desk_card": desk_card,
        "objects": objects,
        "open_count": len(open_objects),
        "empty": empty,
        "empty_message": empty_message,
        "recorded_count": recorded,
        **_NULL_METRICS,
        "framework": {
            "empty": empty,
            "recorded_count": recorded,
            "cap": CAP_ID,
            "on_disk": False,
            "live_billing": False,
            "client_machinery": False,
        },
        "ggv_desk": _ggv_desk_projection(seat["person_id"], catalog_db=catalog_db),
        "needs_you": _needs_you_projection(seat["person_id"], catalog_db),
        "framework_mutated": False,
        "duplicate_mutate_surface": False,
        "bzg_compose": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "haikal_human": "not_started",
        "devi_retest": "parked",
        "honesty": honesty_flags(catalog_db=catalog_db),
    }


def _find_object(object_id: str) -> dict[str, Any]:
    token = (object_id or "").strip()
    upper = token.upper()
    framework = ic.build_framework()
    recorded = int(framework.get("recorded_count") or 0)
    if upper == EMPTY_ID:
        if recorded != 0:
            raise IntercoDepthError(
                "The framework has intercompany evidence. The empty placeholder is not a second catalog.",
                code="not_found",
                http_status=404,
            )
        return {
            "object_kind": "empty_placeholder",
            "object_id": EMPTY_ID,
            "slot": None,
        }
    if upper == DESK_OBJECT_ID:
        return {
            "object_kind": "ggv_interco_desk",
            "object_id": DESK_OBJECT_ID,
            "slot": None,
        }
    kind = OBJECT_TO_SLOT.get(upper)
    if kind is None:
        raise IntercoDepthError(
            "Intercompany card was not found. A missing card was not invented as live billing.",
            code="not_found",
            http_status=404,
        )
    return {
        "object_kind": "interco_slot",
        "object_id": upper,
        "slot": kind,
    }


def object_detail(
    object_id: str,
    *,
    verified_person_id: str | None,
    events_file: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    events = _load_events(events_path(events_file))
    found = _find_object(object_id)
    oid = found["object_id"]
    slot = None
    if found["slot"]:
        slot = dict(_slot_row(found["slot"]))
    detail = {
        "ok": True,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "seat": seat,
        "object_id": oid,
        "object_kind": found["object_kind"],
        "slot": slot,
        "actions": _action_view(oid, events),
        "events": _events_for(events, oid),
        "empty": True,
        **_NULL_METRICS,
        "framework_mutated": False,
        "cap": CAP_ID,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "honesty": honesty_flags(catalog_db=catalog_db),
    }
    detail["cap_state"] = (detail["honesty"] or {}).get("cap_ggv_06")
    if found["object_kind"] == "empty_placeholder":
        detail["empty_message"] = (
            "No intercompany evidence. Empty is not live billing and not an invoice."
        )
    if found["object_kind"] == "ggv_interco_desk":
        detail["ggv_desk"] = _ggv_desk_projection(
            seat["person_id"],
            catalog_db=catalog_db,
        )
        detail["cap_ceiling"] = "SPECIFIED"
    return detail


def _clean_note(text: str) -> str:
    note = (text or "").strip()
    if len(note) < 2 or len(note) > 4000:
        raise IntercoDepthError(
            "An operator note is required. A blank note is not an invoice and not live billing.",
            code="missing_note",
            http_status=400,
        )
    if _NOTE_BANNED.search(note):
        raise IntercoDepthError(
            "An operator note cannot invent live billing, an invoice, an allocation, "
            "an AR/AP balance, a tax treatment, a payment, an Alchemist write, "
            "a guest blast, a public post, or maturity.",
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
) -> dict[str, Any]:
    """Record an allowed operator action. Does not write the intercompany framework."""
    if body is not None:
        _reject_body(body)
    seat = require_seat(verified_person_id, catalog_db=catalog_db)
    canon = _normalise_kind(kind)
    before_stamp = _framework_stamp()
    before_framework = ic.build_framework(catalog_db=catalog_db)
    found = _find_object(object_id)
    text = (note or "").strip()
    if canon in {"note", "next_action", "handoff_touch"} and not text:
        raise IntercoDepthError(f"{canon} note required", code="missing_note", http_status=400)
    if text:
        text = _clean_note(text)
    decision_token = None
    if canon == "review_decision":
        decision_token = (decision or "").strip().lower().replace("-", "_")
        banned_decision = _BANNED_KINDS.get(decision_token) or _BANNED_KINDS.get(
            decision_token.replace("_", "-")
        )
        if banned_decision:
            raise IntercoDepthError(
                "A review decision does not prove live billing, an invoice, or a payment.",
                code=banned_decision,
                http_status=403,
            )
        if decision_token not in REVIEW_DECISIONS:
            raise IntercoDepthError(
                "decision must be still_specified, not_live_billing, or keep_as_note",
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
        "framework_mutated": False,
        "bzg_compose": False,
    }
    _append_event(path, event)
    after_framework = ic.build_framework(catalog_db=catalog_db)
    desk = operator_depth_desk(
        verified_person_id=seat["person_id"],
        events_file=path,
        catalog_db=catalog_db,
    )
    return {
        "ok": True,
        "action": "ggv_interco_operator",
        "kind": canon,
        "decision": decision_token,
        "recorded": True,
        "event": event,
        "seat": seat,
        "object_id": found["object_id"],
        "framework_unchanged": (
            before_framework.get("recorded_count") == after_framework.get("recorded_count")
            and _framework_stamp() == before_stamp
        ),
        "framework_mutated": False,
        "ggv_desk": {
            "module_count": (desk.get("ggv_desk") or {}).get("module_count"),
            "empty_count": (desk.get("ggv_desk") or {}).get("empty_count"),
            "href": GGV_DESK_HREF,
            "caps_raised": False,
            "cr_resolved": False,
            "framework_mutated": False,
        },
        "interco_desk": {
            "slot_count": desk.get("slot_count"),
            "empty": desk.get("empty"),
            "empty_message": desk.get("empty_message"),
            "open_count": desk.get("open_count"),
            "recorded_count": desk.get("recorded_count"),
            "invoice": None,
            "allocation": None,
            "ar_ap": None,
            "payment": None,
            "live_billing": False,
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
