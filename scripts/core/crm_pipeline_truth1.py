#!/usr/bin/env python3
"""CRM-PIPELINE-TRUTH-1 — CRM pipeline truth (no invent).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
CRM-PIPELINE-TRUTH-1 (armed 2026-09-30 after FIN-TAX-DEEPEN-1 PASS_VERIFIED).

Probes authorised CRM. Wires Habitat lead stage counts via
ggv_ops_pack.pipeline_consequence when present; UNKNOWN when a stage is empty.
Never invents pipeline counts. External SaaS CRM clients (HubSpot / Salesforce /
Pipedrive / ActiveCampaign reader) stamped ABSENT — not invented.

Preserves GGV-PIPELINE-TRUTH-1 and CRM-IDENTITY-1.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain CONTENT-PUBLISH-PATH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import crm_identity_memory as _crm
from core import ggv_ops_pack as _ops
from core import ggv_pipeline_truth1 as _ggv_pipe

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "CRM-PIPELINE-TRUTH-1"
SCHEMA_ID = "wolf.crm-pipeline-truth-1.v1"
BOUND = "beta-crm-pipeline-safe"
CAP_PIPELINE = "CAP-CRM pipeline"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "WIRED"
ACTION = "WIRE_HABITAT_FACTS"

PAGE_PATHS = frozenset(
    {
        "/crm/pipeline-truth-1",
        "/crm/pipeline-truth-1/",
        "/crm/pipeline",
        "/crm/pipeline/",
        "/crm-pipeline-truth-1",
        "/crm-pipeline-truth-1/",
        "/crm-pipeline",
        "/crm-pipeline/",
        "/crm-pipeline-truth-1.html",
        "/dashboards/crm-pipeline-truth-1.html",
    }
)
API_PATH = "/api/crm/pipeline-truth-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/crm-pipeline-truth-1",
        "/api/ops/crm-pipeline",
    }
)

PRESERVED_PACKS = ("GGV-PIPELINE-TRUTH-1", "CRM-IDENTITY-1")

_STAGE_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "OPEN",
        "Open",
        "Habitat CRM leads in OPEN. Count from authorised CRM facts only. UNKNOWN when empty.",
    ),
    (
        "ACTIVE",
        "Active",
        "Habitat CRM leads in ACTIVE. Count from authorised CRM facts only. UNKNOWN when empty.",
    ),
    (
        "PARKED",
        "Parked",
        "Habitat CRM leads in PARKED. Count from authorised CRM facts only. UNKNOWN when empty.",
    ),
    (
        "CLOSED",
        "Closed",
        "Habitat CRM leads in CLOSED. Closed is not a sale. UNKNOWN when empty.",
    ),
)

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
        "Fake-deal / invent-pipeline writes are refused.",
    ),
)

_FAKE_PIPELINE_TOKENS = frozenset(
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
        "invent-pipeline",
        "invent_pipeline",
        "pipeline-count",
        "pipeline_count",
        "pipeline-counts",
        "pipeline_counts",
        "fake-pipeline",
        "fake_pipeline",
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
        "count",
        "counts",
    }
)

# Name-only external CRM client markers — never load secrets.
EXTERNAL_CRM_CLIENT_SEARCH: dict[str, Any] = {
    "modules_checked": (
        "hubspot_client",
        "salesforce_client",
        "pipedrive_client",
        "activecampaign_reader",
        "zoho_crm_client",
    ),
    "found_modules": (),
    "note": (
        "No HubSpot / Salesforce / Pipedrive / ActiveCampaign reader in-repo. "
        "Authorised pipeline facts are Habitat core_leads via "
        "ggv_ops_pack.pipeline_consequence only. Never invent SaaS counts."
    ),
}


class CrmPipelineTruth1Error(ValueError):
    """Fail closed. Does not invent pipeline counts."""

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
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


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
        raise CrmPipelineTruth1Error(
            "CRM pipeline truth board is not on this assignment.",
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
        "entity": "CRM",
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
        "invented_pipeline": False,
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
        "entity": "CRM",
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
        "invented_pipeline": False,
        "fake_conversion": False,
        "why": why,
    }


def probe_habitat_crm(
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
    empty = bool(pc.get("empty")) or fact_count == 0
    return {
        "ok": bool(pc.get("ok")),
        "authorised": True,
        "status": "HONEST_EMPTY" if empty else "WIRED",
        "empty": empty,
        "crm_lead_count": int(pc.get("count") or 0),
        "fact_count": fact_count,
        "by_stage": {s["id"]: s.get("count") for s in stages},
        "stages": stages,
        "invented_leads": False,
        "invented_pipeline": False,
        "empty_pipeline_is_not_live": True,
        "live_pipeline": False,
        "closed_is_not_a_sale": True,
        "source": "ggv_ops_pack.pipeline_consequence",
        "why": pc.get("why")
        or "Pipeline stages from Habitat CRM lead facts. Empty is not live.",
    }


def probe_external_crm_clients() -> dict[str, Any]:
    """Name-only probe. External SaaS CRM clients are ABSENT — never invent."""
    return {
        "ok": True,
        "status": "ABSENT",
        "authorised": False,
        "modules_checked": list(EXTERNAL_CRM_CLIENT_SEARCH["modules_checked"]),
        "found_modules": list(EXTERNAL_CRM_CLIENT_SEARCH["found_modules"]),
        "invented_pipeline": False,
        "why": EXTERNAL_CRM_CLIENT_SEARCH["note"],
    }


def decide_route(
    *, habitat: dict[str, Any] | None = None, external: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Wire Habitat facts when present; honest empty otherwise. Never invent."""
    hab = habitat if habitat is not None else probe_habitat_crm()
    ext = external if external is not None else probe_external_crm_clients()
    if hab.get("ok") and not hab.get("empty") and int(hab.get("fact_count") or 0) > 0:
        classification = "WIRED"
        action = "WIRE_HABITAT_FACTS"
        why = (
            "Authorised Habitat CRM facts present — wire stage counts. "
            "External SaaS CRM ABSENT (not invented)."
        )
    elif hab.get("ok"):
        classification = "HONEST_EMPTY"
        action = "HOLD_UNKNOWN_STAGES"
        why = (
            "Authorised Habitat CRM empty — stages UNKNOWN. "
            "Never invent pipeline counts."
        )
    else:
        classification = "HUMAN_COMMISSIONING"
        action = "STAMP_HUMAN_COMMISSIONING"
        why = "Authorised CRM probe failed — refuse invent; hold for Owner."
    return {
        "classification": classification,
        "action": action,
        "external_crm": ext.get("status") or "ABSENT",
        "habitat_status": hab.get("status"),
        "invented_pipeline": False,
        "why": why,
    }


def crm_identity1_preserved() -> dict[str, Any]:
    """Read-only: CRM-IDENTITY-1 still honest."""
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
                "This pack adds CRM pipeline truth — does not replace identity."
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


def ggv_pipeline_truth1_preserved() -> dict[str, Any]:
    """Read-only: GGV-PIPELINE-TRUTH-1 still honest / no fake deals."""
    try:
        flags = _ggv_pipe.honesty_flags()
        payload = _ggv_pipe.build_slice()
        ok = (
            payload.get("ok") is True
            and payload.get("staff_ready") is False
            and payload.get("human_commissioned") is False
            and payload.get("fake_deals") is False
            and payload.get("fake_conversion") is False
            and payload.get("live_pipeline") is False
            and flags.get("fake_deals") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and _ggv_pipe.stages_crm_or_unknown(payload) is True
            and _ggv_pipe.all_conversion_slots_unknown(payload) is True
        )
        return {
            "ok": ok,
            "staff_ready": payload.get("staff_ready"),
            "human_commissioned": payload.get("human_commissioned"),
            "fake_deals": payload.get("fake_deals"),
            "fake_conversion": payload.get("fake_conversion"),
            "live_pipeline": payload.get("live_pipeline"),
            "why": (
                "GGV-PIPELINE-TRUTH-1 preserved: fake_deals=false, "
                "fake_conversion=false, live_pipeline=false, "
                "stages CRM-or-UNKNOWN. Empire CRM board does not replace GGV."
                if ok
                else "GGV-PIPELINE-TRUTH-1 check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "GGV-PIPELINE-TRUTH-1 check failed — pack must not break it.",
        }


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "ggv_pipeline_truth_1",
            "label": "GGV Pipeline Truth-1",
            "href": "/ggv/pipeline-truth-1",
            "kind": "existing",
            "note": "GGV sales board. Preserved — not replaced by empire CRM shell.",
        },
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
    ]


def _honesty_tiles(
    pipeline: dict[str, Any],
    route: dict[str, Any],
    external: dict[str, Any],
    ggv: dict[str, Any],
    crm: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "classification",
            "label": "Classification",
            "status": route.get("classification") or CLASSIFICATION,
            "value": route.get("action"),
            "why": route.get("why"),
        },
        {
            "id": "habitat_crm",
            "label": "Habitat CRM",
            "status": pipeline.get("status") or "UNKNOWN",
            "value": pipeline.get("fact_count"),
            "why": (
                "No Habitat CRM leads → stages UNKNOWN (not invent)."
                if pipeline.get("empty")
                else "Stage counts from authorised Habitat CRM lead facts only."
            ),
        },
        {
            "id": "external_crm",
            "label": "External SaaS CRM",
            "status": external.get("status") or "ABSENT",
            "value": None,
            "why": external.get("why"),
        },
        {
            "id": "invent_pipeline",
            "label": "Invent pipeline",
            "status": "REFUSED",
            "value": False,
            "why": "Invented pipeline counts / fake deals are refused.",
        },
        {
            "id": "fake_conversion",
            "label": "Fake conversion",
            "status": "REFUSED",
            "value": False,
            "why": "Conversion rate / deal value stay UNKNOWN until real facts.",
        },
        {
            "id": "ggv_pipeline_truth_1",
            "label": "GGV-PIPELINE-TRUTH-1",
            "status": "PRESERVED" if ggv.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": ggv.get("why"),
        },
        {
            "id": "crm_identity_1",
            "label": "CRM-IDENTITY-1",
            "status": "PRESERVED" if crm.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": crm.get("why"),
        },
        {
            "id": "cap_crm_pipeline",
            "label": "CAP-CRM pipeline",
            "status": "SPECIFIED",
            "value": None,
            "why": "CRM pipeline truth shell only. Ceiling BUILT. Not PROVEN/READY.",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    crm = crm_identity1_preserved()
    ggv = ggv_pipeline_truth1_preserved()
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "cap_crm_pipeline": CAP_PIPELINE,
        "classification": CLASSIFICATION,
        "action": ACTION,
        "staff_ready": False,
        "human_commissioned": False,
        "fake_deals": False,
        "fake_deal": False,
        "invented_deals": False,
        "invented_deal": False,
        "invented_pipeline": False,
        "fake_pipeline": False,
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
        "ggv_pipeline_truth1_preserved": ggv.get("ok") is True,
        "replaces_crm_identity_page": False,
        "replaces_ggv_pipeline_page": False,
        "second_crm_system": False,
        "second_pipeline_system": False,
        "cap_crm_pipeline_proven": False,
        "cap_crm_pipeline_ready": False,
        "cap_crm_pipeline_maturity": "SPECIFIED",
        "cap_crm_pipeline_ceiling": CEILING,
        "preserved_packs": list(PRESERVED_PACKS),
        "production": False,
        "anon_fail_closed": True,
        "owner_read": True,
        "ggv_habitat_seats": True,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": "CONTENT-PUBLISH-PATH-1",
    }


def refuse_fake_deal(_body: dict | None = None) -> None:
    raise CrmPipelineTruth1Error(
        "Fake deals are refused. Pipeline stages stay CRM-fact-only or UNKNOWN.",
        code="fake_deal_refused",
        http_status=403,
    )


def refuse_invent_pipeline(_body: dict | None = None) -> None:
    raise CrmPipelineTruth1Error(
        "Invented pipeline counts / deals are refused.",
        code="invent_pipeline_refused",
        http_status=403,
    )


def refuse_invent_deal(_body: dict | None = None) -> None:
    refuse_invent_pipeline(_body)


def refuse_fake_conversion(_body: dict | None = None) -> None:
    raise CrmPipelineTruth1Error(
        "Fake conversion / deal-value writes are refused. Conversion stays UNKNOWN.",
        code="fake_conversion_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise CrmPipelineTruth1Error(
        "PROVEN is refused. CAP-CRM pipeline stays SPECIFIED. Empty pipeline is not proven.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise CrmPipelineTruth1Error(
        "READY is refused. A pipeline truth board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise CrmPipelineTruth1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {
            "ready",
            "staff-ready",
            "staff_ready",
            "human-commissioned",
            "human_commissioned",
        }:
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
        if token in _FAKE_PIPELINE_TOKENS or norm in {
            t.replace("-", "_") for t in _FAKE_PIPELINE_TOKENS
        }:
            if "conversion" in token or "conversion" in norm or "value" in token:
                refuse_fake_conversion(payload)
            if "fake" in token or "fake" in norm:
                refuse_fake_deal(payload)
            refuse_invent_pipeline(payload)
    raise CrmPipelineTruth1Error(
        "CRM-PIPELINE-TRUTH-1 is a read honesty shell. Writes refused.",
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
        and s.get("invented_pipeline") is False
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
        if (
            s.get("fake_deal") is not False
            or s.get("invented_deal") is not False
            or s.get("invented_pipeline") is not False
        ):
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


def no_invented_pipeline_counts(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_slice()
    if pack.get("invented_pipeline") is not False:
        return False
    if pack.get("fake_pipeline") is not False:
        return False
    if pack.get("fake_deals") is not False:
        return False
    return stages_crm_or_unknown(pack) and all_conversion_slots_unknown(pack)


def build_slice(person_id: str | None = None) -> dict[str, Any]:
    """Public vertical-slice payload."""
    if person_id is not None:
        require_view(person_id)
    flags = honesty_flags()
    habitat = probe_habitat_crm()
    external = probe_external_crm_clients()
    route = decide_route(habitat=habitat, external=external)
    stages = list(habitat.get("stages") or [])
    conversion = [_conversion_slot(*spec) for spec in _CONVERSION_SLOT_SPECS]
    crm = crm_identity1_preserved()
    ggv = ggv_pipeline_truth1_preserved()
    fact_count = int(habitat.get("fact_count") or 0)
    classification = route.get("classification") or CLASSIFICATION
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": [CAP_PIPELINE, "CRM", "IL-R6"],
        "title": "CRM Pipeline Truth Board",
        "person_id": (person_id or "").strip() or None,
        "brand_id": "habitat",
        "classification": classification,
        "action": route.get("action") or ACTION,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "fake_deals": False,
        "fake_deal": False,
        "invented_deals": False,
        "invented_deal": False,
        "invented_pipeline": False,
        "fake_pipeline": False,
        "fake_conversion": False,
        "invented_conversion": False,
        "live_pipeline": False,
        "empty_pipeline_is_not_live": True,
        "closed_is_not_a_sale": True,
        "fact_count": fact_count,
        "crm_lead_count": int(habitat.get("crm_lead_count") or 0),
        "pipeline_empty": bool(habitat.get("empty")),
        "pipeline_unknown": bool(habitat.get("empty")),
        "conversion_unknown": True,
        "last_success": None,
        "crm_identity1_preserved": crm.get("ok") is True,
        "ggv_pipeline_truth1_preserved": ggv.get("ok") is True,
        "cap_crm_pipeline_proven": False,
        "cap_crm_pipeline_ready": False,
        "cap_crm_pipeline_maturity": flags["cap_crm_pipeline_maturity"],
        "cap_crm_pipeline_ceiling": flags["cap_crm_pipeline_ceiling"],
        "pipeline_stages": stages,
        "conversion_slots": conversion,
        "by_stage": habitat.get("by_stage") or {},
        "honesty_tiles": _honesty_tiles(habitat, route, external, ggv, crm),
        "desk_links": _desk_links(),
        "crm_identity1": crm,
        "ggv_pipeline_truth1": ggv,
        "habitat_probe": {
            "ok": habitat.get("ok"),
            "status": habitat.get("status"),
            "authorised": True,
            "why": habitat.get("why"),
            "invented_leads": False,
            "source": habitat.get("source"),
        },
        "external_crm_probe": external,
        "route": route,
        "pipeline_source": {
            "ok": habitat.get("ok"),
            "why": habitat.get("why"),
            "invented_leads": False,
            "source": "ggv_ops_pack.pipeline_consequence",
        },
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "live_pipeline",
            "fake_deals",
            "invented_pipeline",
            "conversion_rate",
            "deal_value",
            "won_value",
            "CLOSED_is_sale",
            "CAP-CRM pipeline PROVEN",
            "staff_ready",
            "human_commissioned",
            "hubspot_counts",
            "salesforce_counts",
        ],
        "honesty": flags,
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "CONTENT-PUBLISH-PATH-1",
        "summary": (
            "CRM pipeline truth board. Probe authorised Habitat CRM; "
            "wire stage counts or honest UNKNOWN. Never invent pipeline counts. "
            "External SaaS CRM ABSENT. GGV-PIPELINE-TRUTH-1 + CRM-IDENTITY-1 preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def build_board(person_id: str | None = None) -> dict[str, Any]:
    return build_slice(person_id)


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
            "WIRED",
            "HONEST_EMPTY",
            "ABSENT",
            "REFUSED",
            "PRESERVED",
        ],
        "classification": CLASSIFICATION,
        "deal_value_property": False,
        "conversion_property": False,
        "writes_accepted": False,
        "fake_deals": False,
        "invented_pipeline": False,
        "fake_conversion": False,
        "unknown_when_facts_missing": True,
        "preserves": list(PRESERVED_PACKS),
        "why": (
            "CRM pipeline truth board. Stages from authorised Habitat CRM facts only. "
            "UNKNOWN when empty. Never invent pipeline counts."
        ),
    }
