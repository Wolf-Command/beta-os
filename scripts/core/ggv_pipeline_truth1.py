#!/usr/bin/env python3
"""GGV-PIPELINE-TRUTH-1 — GGV sales pipeline truth board (no fake deals).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack GGV-PIPELINE-TRUTH-1
(armed 2026-09-30 after BZG-LABOR-COST-1 PASS_VERIFIED).

Pipeline stages from real Habitat CRM lead facts only (via existing
ggv_ops_pack.pipeline_consequence). UNKNOWN when a stage is empty.
Never invent deals or conversion. Preserves CRM-IDENTITY-1.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain CONN-HEALTH-BOARD-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import crm_identity_memory as _crm
from core import ggv_ops_pack as _ops

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "GGV-PIPELINE-TRUTH-1"
SCHEMA_ID = "wolf.ggv-pipeline-truth-1.v1"
BOUND = "beta-ggv-pipeline-safe"
CAP_PIPELINE = "CAP-GGV pipeline"
LEGAL_ENTITY = "ENT-GGV"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"

PAGE_PATHS = frozenset(
    {
        "/ggv/pipeline-truth-1",
        "/ggv/pipeline-truth-1/",
        "/ggv/pipeline",
        "/ggv/pipeline/",
        "/ggv-pipeline-truth-1",
        "/ggv-pipeline-truth-1/",
        "/ggv-pipeline",
        "/ggv-pipeline/",
        "/ggv-pipeline-truth-1.html",
        "/dashboards/ggv-pipeline-truth-1.html",
    }
)
API_PATH = "/api/ggv/pipeline-truth-1"

PRESERVED_PACKS = ("CRM-IDENTITY-1",)

# Wolf lifecycle stages — counts come from real Habitat CRM leads only.
_STAGE_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "OPEN",
        "Open",
        "Habitat leads in OPEN. Count from CRM facts only. UNKNOWN when empty.",
    ),
    (
        "ACTIVE",
        "Active",
        "Habitat leads in ACTIVE. Count from CRM facts only. UNKNOWN when empty.",
    ),
    (
        "PARKED",
        "Parked",
        "Habitat leads in PARKED. Count from CRM facts only. UNKNOWN when empty.",
    ),
    (
        "CLOSED",
        "Closed",
        "Habitat leads in CLOSED. Closed is not a sale. UNKNOWN when empty.",
    ),
)

# Conversion / deal-value stubs — always UNKNOWN. Never invent conversion.
_CONVERSION_SLOT_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "conversion_rate",
        "Conversion rate",
        "No commissioned conversion facts. UNKNOWN — never invent conversion.",
    ),
    (
        "deal_value",
        "Deal value",
        "No deal-value facts. UNKNOWN — never invent deals or amounts.",
    ),
    (
        "won_value",
        "Won value",
        "CLOSED ≠ won sale. No won-value facts. UNKNOWN — never invent.",
    ),
    (
        "fake_deal",
        "Fake deal write",
        "Fake-deal / invent-deal writes are refused.",
    ),
)

_FAKE_DEAL_TOKENS = frozenset(
    {
        "deal",
        "deals",
        "fake-deal",
        "fake_deal",
        "fake-deals",
        "fake_deals",
        "invent-deal",
        "invent_deal",
        "invent-deals",
        "invent_deals",
        "conversion",
        "conversion-rate",
        "conversion_rate",
        "fake-conversion",
        "fake_conversion",
        "invent-conversion",
        "invent_conversion",
        "deal-value",
        "deal_value",
        "won-value",
        "won_value",
        "won",
        "pipeline-fill",
        "pipeline_fill",
        "fill",
        "seed-deal",
        "seed_deal",
        "create-deal",
        "create_deal",
        "sale",
        "sales",
        "revenue",
        "amount",
        "amounts",
    }
)


class GgvPipelineTruth1Error(ValueError):
    """Fail closed. Does not invent deals or conversion."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 403,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == API_PATH


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner progress.read or GGV Habitat read seats (Amanda/Haikal/Misa)."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid in _ops.READ_SEATS:
        return True
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        return bool(_rbac.can(pid, "progress.read", {}, conn=c))
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise GgvPipelineTruth1Error(
            "GGV pipeline truth board is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _stage_slot(stage_id: str, label: str, why: str, count: int) -> dict[str, Any]:
    n = int(count or 0)
    empty = n <= 0
    return {
        "id": stage_id,
        "label": label,
        "kind": "pipeline_stage",
        "entity": "GGV",
        "brand_id": "habitat",
        "status": "UNKNOWN" if empty else "FROM_CRM",
        "display": "UNKNOWN" if empty else str(n),
        "value": None if empty else n,
        "count": None if empty else n,
        "fact_count": 0 if empty else n,
        "last_fact_at": None,
        "last_success": None,
        "fake_deal": False,
        "invented_deal": False,
        "fake_conversion": False,
        "why": (
            why
            if not empty
            else f"{label}: no CRM leads in this stage — UNKNOWN (not invent)."
        ),
    }


def _conversion_slot(stub_id: str, label: str, why: str) -> dict[str, Any]:
    return {
        "id": stub_id,
        "label": label,
        "kind": "conversion_stub",
        "entity": "GGV",
        "status": "UNKNOWN" if stub_id != "fake_deal" else "REFUSED",
        "display": "UNKNOWN" if stub_id != "fake_deal" else "REFUSED",
        "value": None,
        "amount": None,
        "currency": None,
        "fact_count": 0,
        "last_fact_at": None,
        "last_success": None,
        "fake_deal": False,
        "invented_deal": False,
        "fake_conversion": False,
        "why": why,
    }


def _pipeline_from_crm(
    *, conn: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Read Habitat CRM stage counts. Never invent leads."""
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        pc = _ops.pipeline_consequence(c)
    finally:
        if own and c is not None:
            c.close()
    by_stage = dict(pc.get("by_stage") or {})
    stages = [
        _stage_slot(sid, label, why, int(by_stage.get(sid) or 0))
        for sid, label, why in _STAGE_SPECS
    ]
    fact_count = sum(int(s.get("fact_count") or 0) for s in stages)
    return {
        "ok": bool(pc.get("ok")),
        "empty": bool(pc.get("empty")) or fact_count == 0,
        "crm_lead_count": int(pc.get("count") or 0),
        "fact_count": fact_count,
        "by_stage": {s["id"]: s.get("count") for s in stages},
        "stages": stages,
        "invented_leads": False,
        "empty_pipeline_is_not_live": True,
        "live_pipeline": False,
        "closed_is_not_a_sale": True,
        "why": pc.get("why")
        or "Pipeline stages from Habitat CRM lead facts. Empty is not live.",
    }


def _conversion_slots() -> list[dict[str, Any]]:
    return [_conversion_slot(*spec) for spec in _CONVERSION_SLOT_SPECS]


def crm_identity1_preserved() -> dict[str, Any]:
    """Read-only: CRM-IDENTITY-1 still honest / no fake pipeline / no cross-client leak."""
    try:
        flags = _crm.honesty_flags()
        payload = _crm.public_payload(_crm.OWNER_PERSON, role_allowed=True)
        ok = (
            payload.get("ok") is True
            and payload.get("staff_ready") is False
            and payload.get("human_commissioned") is False
            and payload.get("fake_pipeline") is False
            and payload.get("cross_client_leak") is False
            and payload.get("auto_merge") is False
            and flags.get("fake_pipeline") is False
            and flags.get("cross_client_leak") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
        )
        return {
            "ok": ok,
            "staff_ready": payload.get("staff_ready"),
            "human_commissioned": payload.get("human_commissioned"),
            "fake_pipeline": payload.get("fake_pipeline"),
            "cross_client_leak": payload.get("cross_client_leak"),
            "auto_merge": payload.get("auto_merge"),
            "yanolja_graph_merge": payload.get("yanolja_graph_merge"),
            "why": (
                "CRM-IDENTITY-1 preserved: fake_pipeline=false, "
                "cross_client_leak=false, auto_merge=false, "
                "staff_ready/human_commissioned false. "
                "This pack adds pipeline truth — does not replace identity."
                if ok
                else "CRM-IDENTITY-1 check failed — pack must not break identity."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "CRM-IDENTITY-1 check failed — pack must not break identity.",
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "crm_identity_1",
            "label": "CRM Identity-1",
            "href": "/crm/identity-1",
            "kind": "existing",
            "note": "Upstream identity slice. Preserved — not replaced.",
        },
        {
            "id": "crm_identity",
            "label": "Customer identity desk",
            "href": "/crm-identity",
            "kind": "existing",
            "note": "Existing CAP-CRM-02 desk. Not a second CRM.",
        },
        {
            "id": "ggv_ops",
            "label": "GGV Ops Pack",
            "href": "/ggv-ops-pack",
            "kind": "existing",
            "note": "Habitat lead operator loop. Pipeline consequence lives here.",
        },
        {
            "id": "ggv_content_prove",
            "label": "GGV Content Prove",
            "href": "/ggv/content-prove",
            "kind": "existing",
            "note": "Content Machine prove/harden. Separate from sales pipeline.",
        },
    ]


def _honesty_tiles(pipeline: dict[str, Any], crm: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "pipeline_stages",
            "label": "Pipeline stages",
            "status": "UNKNOWN" if pipeline.get("empty") else "FROM_CRM",
            "value": pipeline.get("fact_count"),
            "why": (
                "No Habitat CRM leads → stages UNKNOWN (not invent)."
                if pipeline.get("empty")
                else "Stage counts from Habitat CRM lead facts only."
            ),
        },
        {
            "id": "fake_deals",
            "label": "Fake deals",
            "status": "REFUSED",
            "value": False,
            "why": "Fake-deal / invent-deal writes are refused.",
        },
        {
            "id": "fake_conversion",
            "label": "Fake conversion",
            "status": "REFUSED",
            "value": False,
            "why": "Conversion rate / deal value stay UNKNOWN until real facts.",
        },
        {
            "id": "crm_identity_1",
            "label": "CRM-IDENTITY-1",
            "status": "PRESERVED" if crm.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": crm.get("why"),
        },
        {
            "id": "cap_ggv_pipeline",
            "label": "CAP-GGV pipeline",
            "status": "SPECIFIED",
            "value": None,
            "why": "Sales pipeline truth board only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    crm = crm_identity1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_ggv_pipeline": CAP_PIPELINE,
        "legal_entity_id": LEGAL_ENTITY,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_deals": False,
        "fake_deal": False,
        "invented_deals": False,
        "invented_deal": False,
        "fake_conversion": False,
        "invented_conversion": False,
        "live_pipeline": False,
        "empty_pipeline_is_not_live": True,
        "closed_is_not_a_sale": True,
        "zero_as_success": False,
        "unknown_when_facts_missing": True,
        "empty_slots_honest": True,
        "conversion_unknown": True,
        "crm_identity1_preserved": crm.get("ok") is True,
        "replaces_crm_identity_page": False,
        "second_crm_system": False,
        "second_pipeline_system": False,
        "cap_ggv_pipeline_proven": False,
        "cap_ggv_pipeline_ready": False,
        "cap_ggv_pipeline_maturity": "SPECIFIED",
        "cap_ggv_pipeline_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "ggv_habitat_seats": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "CONN-HEALTH-BOARD-1",
    }


def refuse_fake_deal(_body: dict | None = None) -> None:
    raise GgvPipelineTruth1Error(
        "Fake deals are refused. Pipeline stages stay CRM-fact-only or UNKNOWN.",
        code="fake_deal_refused",
        http_status=403,
    )


def refuse_invent_deal(_body: dict | None = None) -> None:
    raise GgvPipelineTruth1Error(
        "Invented deals / pipeline fills are refused.",
        code="invent_deal_refused",
        http_status=403,
    )


def refuse_fake_conversion(_body: dict | None = None) -> None:
    raise GgvPipelineTruth1Error(
        "Fake conversion / deal-value writes are refused. Conversion stays UNKNOWN.",
        code="fake_conversion_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise GgvPipelineTruth1Error(
        "PROVEN is refused. CAP-GGV pipeline stays SPECIFIED. Empty pipeline is not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise GgvPipelineTruth1Error(
        "READY is refused. A pipeline truth board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise GgvPipelineTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if token in {
            "conversion",
            "conversion-rate",
            "fake-conversion",
            "won-value",
            "deal-value",
        } or norm in {
            "conversion",
            "conversion_rate",
            "fake_conversion",
            "won_value",
            "deal_value",
        }:
            refuse_fake_conversion(payload)
        if token in _FAKE_DEAL_TOKENS or norm in {
            t.replace("-", "_") for t in _FAKE_DEAL_TOKENS
        }:
            if "conversion" in token or "conversion" in norm or "value" in token:
                refuse_fake_conversion(payload)
            if "fake" in token or "fake" in norm:
                refuse_fake_deal(payload)
            refuse_invent_deal(payload)
    raise GgvPipelineTruth1Error(
        "GGV-PIPELINE-TRUTH-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def all_conversion_slots_unknown(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    slots = pack.get("conversion_slots") or []
    if not slots:
        return False
    return all(
        s.get("value") is None
        and s.get("amount") is None
        and s.get("fact_count") == 0
        and s.get("last_success") is None
        and s.get("fake_deal") is False
        and s.get("invented_deal") is False
        and s.get("fake_conversion") is False
        and s.get("status") in ("EMPTY", "UNKNOWN", "REFUSED")
        for s in slots
    )


def stages_crm_or_unknown(payload: dict[str, Any] | None = None) -> bool:
    """Every stage is FROM_CRM with a real count, or UNKNOWN with null value."""
    pack = payload if payload is not None else build_slice()
    stages = pack.get("pipeline_stages") or []
    if not stages:
        return False
    for s in stages:
        if s.get("fake_deal") is not False or s.get("invented_deal") is not False:
            return False
        status = s.get("status")
        if status == "FROM_CRM":
            if s.get("value") is None or int(s.get("fact_count") or 0) <= 0:
                return False
        elif status in ("EMPTY", "UNKNOWN"):
            if s.get("value") is not None or s.get("count") is not None:
                return False
            if int(s.get("fact_count") or 0) != 0:
                return False
        else:
            return False
    return True


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility
    when person_id is None (tests); require_view when person_id provided."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    pipeline = _pipeline_from_crm()
    stages = list(pipeline.get("stages") or [])
    conversion = _conversion_slots()
    crm = crm_identity1_preserved()
    fact_count = int(pipeline.get("fact_count") or 0)
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_PIPELINE],
        "title": "GGV Sales Pipeline Truth Board",
        "person_id": (person_id or "").strip() or None,
        "legal_entity_id": LEGAL_ENTITY,
        "brand_id": "habitat",
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "fake_deals": False,
        "fake_deal": False,
        "invented_deals": False,
        "invented_deal": False,
        "fake_conversion": False,
        "invented_conversion": False,
        "live_pipeline": False,
        "empty_pipeline_is_not_live": True,
        "closed_is_not_a_sale": True,
        "fact_count": fact_count,
        "crm_lead_count": int(pipeline.get("crm_lead_count") or 0),
        "pipeline_empty": bool(pipeline.get("empty")),
        "pipeline_unknown": bool(pipeline.get("empty")),
        "conversion_unknown": True,
        "last_success": None,
        "crm_identity1_preserved": crm.get("ok") is True,
        "cap_ggv_pipeline_proven": False,
        "cap_ggv_pipeline_ready": False,
        "cap_ggv_pipeline_maturity": flags["cap_ggv_pipeline_maturity"],
        "cap_ggv_pipeline_ceiling": flags["cap_ggv_pipeline_ceiling"],
        "pipeline_stages": stages,
        "conversion_slots": conversion,
        "by_stage": pipeline.get("by_stage") or {},
        "honesty_tiles": _honesty_tiles(pipeline, crm),
        "desk_links": _desk_links(),
        "crm_identity1": crm,
        "pipeline_source": {
            "ok": pipeline.get("ok"),
            "why": pipeline.get("why"),
            "invented_leads": False,
            "source": "ggv_ops_pack.pipeline_consequence",
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_pipeline",
            "fake_deals",
            "conversion_rate",
            "deal_value",
            "won_value",
            "CLOSED_is_sale",
            "CAP-GGV pipeline PROVEN",
            "staff_ready",
            "human_commissioned",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "CONN-HEALTH-BOARD-1",
        "summary": (
            "GGV sales pipeline truth board. Stages from Habitat CRM facts only. "
            "UNKNOWN when empty. No fake deals / conversion. "
            "CRM-IDENTITY-1 preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "pipeline_stages": [s[0] for s in _STAGE_SPECS],
        "conversion_slots": [s[0] for s in _CONVERSION_SLOT_SPECS],
        "status_enum": [
            "EMPTY",
            "UNKNOWN",
            "FROM_CRM",
            "REFUSED",
            "PRESERVED",
        ],
        "deal_value_property": False,
        "conversion_property": False,
        "writes_accepted": False,
        "fake_deals": False,
        "fake_conversion": False,
        "unknown_when_facts_missing": True,
        "preserves": list(PRESERVED_PACKS),
        "why": (
            "GGV sales pipeline truth board. Stages from CRM facts only. "
            "UNKNOWN when empty. No fake deals / conversion."
        ),
    }
