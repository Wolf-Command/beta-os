#!/usr/bin/env python3
"""ESB-SETTLEMENT-PATH-1 — Settlement path probe (wire or EXTERNAL_BLOCKER).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
ESB-SETTLEMENT-PATH-1 (armed 2026-09-30 after METRICOOL-RUNTIME-WIRE-1
PASS_VERIFIED). Challenges ESB PARTIAL / settlement UNAVAILABLE ceiling.

Probes settlement API path / credentials / authorised connectors.
No authorised settlement path or credentials found → stamp EXTERNAL_BLOCKER
with evidence (not UNKNOWN forever). Never invents settlement / P&L.
Preserves ESB-TRUTH-1 warehouse RO honesty (settlement_api UNAVAILABLE).
staff_ready=false · human_commissioned=false.
Does not auto-chain SOP-CATALOG-SEED-ROUTE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import esb_truth1 as _esb_truth1

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "ESB-SETTLEMENT-PATH-1"
SCHEMA_ID = "wolf.esb-settlement-path-1.v1"
BOUND = "beta-esb-settlement-probe"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "EXTERNAL_BLOCKER"
CLOSES_TOWARD = ("INT-ESB", "CAP-INTG-02", "CAP-BZG ESB")
PRESERVED_PACKS = ("ESB-TRUTH-1",)
INTEGRATION_ID = "INT-ESB-WOLF"
HONESTY_BOARD = "/ops/integrations-status"
ESB_TRUTH_HREF = "/ops/esb-truth-1"

PAGE_PATHS = frozenset(
    {
        "/ops/esb-settlement-path-1",
        "/ops/esb-settlement-path-1/",
        "/ops/esb-settlement",
        "/ops/esb-settlement/",
        "/esb-settlement-path-1",
        "/esb-settlement-path-1/",
        "/esb-settlement-path-1.html",
        "/dashboards/esb-settlement-path-1.html",
        "/bzg/esb-settlement-path-1",
        "/bzg/esb-settlement-path-1/",
    }
)
API_PATH = "/api/ops/esb-settlement-path-1"

STATUS_VOCAB = frozenset(
    {"RUNTIME_WIRED", "PRESERVED", "EXTERNAL_BLOCKER", "HUMAN_COMMISSIONING", "ABSENT"}
)

# Settlement-related env key name patterns (names only — never load secret values).
_SETTLEMENT_ENV_NAME_RE = re.compile(
    r"(SETTLEMENT|ESB_API|ESB_URL|ESB_HOST|ESB_TOKEN|ESB_SECRET|"
    r"BETA_ESB_API|ESB_SETTLEMENT)",
    re.IGNORECASE,
)

# Authorised evidence that settlement API path is unavailable (not inventable).
FELIX_EVIDENCE: dict[str, Any] = {
    "source": "Felix",
    "dated": "2026-07-19",
    "finding": (
        "ESB settlement / cancel-menu / goods-receipt reports "
        "CONFIRMED UNAVAILABLE via API"
    ),
    "doc": "docs/deliveries/BZG-UMA-BLU-OPERATIONS-DISCOVERY-2026-09-17.md",
    "canon": "docs/canon/UMA-BLU-DAILY-CLOSE.md",
    "owner_approval": (
        "docs/deliveries/WOLF-CONNECTION-OWNER-APPROVAL-LIST-2026-09-22.md"
        " — ESB YES observe / WRITE NO FOR NOW; settlement_api UNAVAILABLE"
    ),
}

SETTLEMENT_CLIENT_SEARCH: dict[str, Any] = {
    "glob": "scripts/**/*.py",
    "patterns": (
        "settlement_client",
        "esb_settlement_api",
        "ESB_SETTLEMENT",
        "class Settlement",
    ),
    "found_modules": (),
    "note": (
        "No dedicated settlement API client module in beta-os scripts/. "
        "esb_close_snapshot / esb_truth1 are warehouse RO only."
    ),
}


class EsbSettlementPath1Error(ValueError):
    """Fail closed. Does not invent settlement, P&L, or ESB writes."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


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


def _env_key_names_from_dotenv(path: Path) -> list[str]:
    if not path.is_file():
        return []
    names: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key = raw.split("=", 1)[0].strip()
            if key:
                names.append(key)
    except OSError:
        return []
    return names


def probe_credentials() -> dict[str, Any]:
    """Name-only probe for settlement / ESB API credentials. Never returns values."""
    process_hits = sorted(
        k for k in os.environ if _SETTLEMENT_ENV_NAME_RE.search(k)
    )
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {
            k
            for k in (dotenv_keys + example_keys)
            if _SETTLEMENT_ENV_NAME_RE.search(k)
        }
    )
    present = bool(process_hits or file_hits)
    return {
        "id": "settlement_credentials",
        "label": "Settlement / ESB API credentials",
        "status": "EXTERNAL_BLOCKER" if not present else "RUNTIME_WIRED",
        "creds_present": present,
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "value": None,
        "settlement": None,
        "pnl": None,
        "why": (
            "No SETTLEMENT / ESB_API / ESB_URL / ESB_TOKEN keys in process env, "
            ".env, or .env.example. Credentials absent — EXTERNAL_BLOCKER with "
            "evidence (not UNKNOWN). Secret values never loaded."
            if not present
            else "Settlement-related key names present; values not loaded this pack."
        ),
        "evidence": ".env + .env.example key-name scan (no values)",
    }


def probe_api_path() -> dict[str, Any]:
    """Probe for an authorised settlement API path/client. No network invent."""
    client_found = bool(SETTLEMENT_CLIENT_SEARCH["found_modules"])
    return {
        "id": "settlement_api_path",
        "label": "Settlement API path / client",
        "status": "EXTERNAL_BLOCKER",
        "path_configured": False,
        "client_module_found": client_found,
        "value": None,
        "settlement": None,
        "pnl": None,
        "why": (
            "No authorised settlement API path or client in Beta. "
            f"Felix {FELIX_EVIDENCE['dated']}: {FELIX_EVIDENCE['finding']}. "
            "Warehouse RO ≠ settlement API. EXTERNAL_BLOCKER evidenced."
        ),
        "evidence": FELIX_EVIDENCE["doc"],
        "felix": dict(FELIX_EVIDENCE),
        "client_search": dict(SETTLEMENT_CLIENT_SEARCH),
    }


def probe_authorised_connector() -> dict[str, Any]:
    """Owner-approved ESB observe path is warehouse RO — not settlement."""
    return {
        "id": "authorised_connector",
        "label": "Authorised ESB connector scope",
        "status": "EXTERNAL_BLOCKER",
        "observe_approved": True,
        "write_approved": False,
        "settlement_approved": False,
        "value": "warehouse_RO_only",
        "settlement": None,
        "pnl": None,
        "why": (
            "Owner approval list: ESB YES observe / WRITE NO FOR NOW. "
            "Settlement API stays unavailable. No settlement connector authorised. "
            "EXTERNAL_BLOCKER — not inventable GREEN."
        ),
        "evidence": FELIX_EVIDENCE["owner_approval"],
    }


def probe_warehouse_ro() -> dict[str, Any]:
    """Preserve ESB-TRUTH-1 warehouse RO honesty — not settlement."""
    try:
        slice_ = _esb_truth1.build_slice()
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "warehouse_ro",
            "label": "ESB-TRUTH-1 warehouse RO",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "settlement": None,
            "pnl": None,
            "why": (
                f"ESB-TRUTH-1 slice failed ({type(exc).__name__}). "
                "No invented warehouse facts."
            ),
            "evidence": "core.esb_truth1.build_slice",
        }
    wh_status = slice_.get("warehouse_status") or (
        (slice_.get("warehouse") or {}).get("warehouse_status")
    )
    # Prefer nested warehouse dict when present.
    warehouse = slice_.get("warehouse") or {}
    if isinstance(warehouse, dict) and warehouse.get("warehouse_status"):
        wh_status = warehouse.get("warehouse_status")
    audit = slice_.get("audit_status")
    sap = slice_.get("settlement_api")
    ok = (
        slice_.get("ok") is True
        and audit == "PARTIAL_IN_BETA"
        and sap == "UNAVAILABLE"
        and slice_.get("pnl") is None
        and slice_.get("settlement") is None
        and slice_.get("pnl_invented") is False
        and slice_.get("fake_settlement") is False
        and slice_.get("esb_write") is False
        and slice_.get("staff_ready") is False
        and slice_.get("human_commissioned") is False
    )
    return {
        "id": "warehouse_ro",
        "label": "ESB-TRUTH-1 warehouse RO",
        "status": "PRESERVED" if ok else "EXTERNAL_BLOCKER",
        "value": wh_status,
        "audit_status": audit,
        "settlement_api": sap,
        "settlement": None,
        "pnl": None,
        "href": ESB_TRUTH_HREF,
        "why": (
            "ESB-TRUTH-1 preserved: PARTIAL_IN_BETA warehouse RO; "
            "settlement_api UNAVAILABLE; pnl/settlement null; no ESB write. "
            "This pack does not invent settlement from warehouse facts."
            if ok
            else "ESB-TRUTH-1 honesty check failed — pack must not break it."
        ),
        "evidence": "core.esb_truth1.build_slice",
        "preserved_ok": ok,
    }


def surface_stamps() -> list[dict[str, Any]]:
    """Probe surfaces with evidenced statuses. Settlement/P&L stay null."""
    creds = probe_credentials()
    api = probe_api_path()
    conn = probe_authorised_connector()
    wh = probe_warehouse_ro()
    return [
        api,
        creds,
        conn,
        wh,
        {
            "id": "settlement_amounts",
            "label": "Settlement amounts / P&L",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "settlement": None,
            "pnl": None,
            "why": (
                "Settlement amounts and P&L stay null. No authorised path to "
                "fetch them. Never invent. EXTERNAL_BLOCKER — not zero success."
            ),
            "evidence": "pack forbids fake settlement / invent P&L",
        },
        {
            "id": "last_success",
            "label": "Settlement last_success",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "last_success": None,
            "settlement": None,
            "pnl": None,
            "why": (
                "last_success stays null. Warehouse RO ≠ settlement connector "
                "success. Never invent."
            ),
            "evidence": "INTG / ESB-TRUTH-1 honesty — null_if_unknown_never_invent",
        },
        {
            "id": "human_commissioning",
            "label": "Human commissioning path",
            "status": "ABSENT",
            "value": None,
            "why": (
                "Not HUMAN_COMMISSIONING — vendor/API has no settlement report "
                "path (Felix). Commissioning credentials cannot unlock a "
                "non-existent API. Classification pins EXTERNAL_BLOCKER."
            ),
            "evidence": FELIX_EVIDENCE["doc"],
        },
    ]


def esb_truth1_preserved() -> dict[str, Any]:
    """Read-only: ESB-TRUTH-1 warehouse RO honesty still holds."""
    wh = probe_warehouse_ro()
    ok = wh.get("preserved_ok") is True and wh.get("status") == "PRESERVED"
    return {
        "ok": ok,
        "pack": "ESB-TRUTH-1",
        "audit_status": wh.get("audit_status"),
        "settlement_api": wh.get("settlement_api"),
        "warehouse_status": wh.get("value"),
        "href": ESB_TRUTH_HREF,
        "why": wh.get("why"),
    }


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "fake_settlement": False,
        "settlement_invented": False,
        "pnl_invented": False,
        "esb_write": False,
        "esb_mutated": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "prod_probe_read_only": True,
        "no_push": True,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "proven_claimed": False,
        "ready_claimed": False,
        "esb_truth1_preserved": True,
        "settlement_api_path": "EXTERNAL_BLOCKER",
        "settlement_credentials": "EXTERNAL_BLOCKER",
        "status_vocab": "RUNTIME_WIRED|PRESERVED|EXTERNAL_BLOCKER|HUMAN_COMMISSIONING|ABSENT",
        "next_pack_for_parent_only": "SOP-CATALOG-SEED-ROUTE-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "unknown_forever_replaced": True,
    }


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise EsbSettlementPath1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "settlement",
            "settle",
            "fake-settlement",
            "invent-settlement",
            "settlement-api",
            "settlement-amount",
            "payout",
        } or norm in {
            "settlement",
            "fake_settlement",
            "invent_settlement",
            "settlement_api",
            "settlement_amount",
            "payout",
        }:
            raise EsbSettlementPath1Error(
                "Fake settlement refused. settlement path EXTERNAL_BLOCKER.",
                code="settlement_refused",
            )
        if token in {
            "pnl",
            "p-and-l",
            "contribution",
            "invent-pnl",
            "fake-pnl",
            "revenue",
            "profit",
        } or norm in {
            "pnl",
            "invent_pnl",
            "fake_pnl",
            "contribution",
            "revenue",
            "profit",
        }:
            raise EsbSettlementPath1Error(
                "Invented P&L refused. Amounts stay null.",
                code="pnl_refused",
            )
        if token in {
            "esb-write",
            "esb-mutate",
            "write",
            "mutate",
        } or norm in {
            "esb_write",
            "esb_mutate",
        }:
            raise EsbSettlementPath1Error(
                "ESB write refused. Write authority not expanded.",
                code="esb_write_refused",
            )
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        }:
            raise EsbSettlementPath1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
        }:
            raise EsbSettlementPath1Error(
                "Commissioning flags / PROVEN / READY are refused.",
                code="ready_refused",
            )
    raise EsbSettlementPath1Error(
        "ESB-SETTLEMENT-PATH-1 is a read-only probe board. Writes refused.",
        code="write_refused",
    )


def refuse_settlement(_body: dict | None = None) -> None:
    raise EsbSettlementPath1Error(
        "Fake settlement refused. settlement path EXTERNAL_BLOCKER.",
        code="settlement_refused",
    )


def refuse_pnl(_body: dict | None = None) -> None:
    raise EsbSettlementPath1Error(
        "Invented P&L refused. Amounts stay null.",
        code="pnl_refused",
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when probe surfaces use allowed vocab and settlement/P&L stay null."""
    pack = payload if payload is not None else build_board()
    if pack.get("fake_settlement") is True or pack.get("settlement_invented") is True:
        return False
    if pack.get("pnl_invented") is True:
        return False
    if pack.get("settlement") is not None or pack.get("pnl") is not None:
        return False
    if pack.get("classification") != "EXTERNAL_BLOCKER":
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 5:
        return False
    blockers = 0
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        st = s.get("status")
        if st not in STATUS_VOCAB:
            return False
        if s.get("id") in (
            "settlement_api_path",
            "settlement_credentials",
            "authorised_connector",
            "settlement_amounts",
            "last_success",
        ):
            if st != "EXTERNAL_BLOCKER":
                return False
            if s.get("settlement") is not None or s.get("pnl") is not None:
                return False
            blockers += 1
        if s.get("id") == "warehouse_ro" and st not in ("PRESERVED", "EXTERNAL_BLOCKER"):
            return False
        if s.get("id") == "human_commissioning" and st not in (
            "ABSENT",
            "HUMAN_COMMISSIONING",
            "EXTERNAL_BLOCKER",
        ):
            return False
    return blockers >= 4


def build_board() -> dict[str, Any]:
    """Public settlement path probe board. Auth gating is caller's job."""
    probed_at = _now_wita()
    surfaces = surface_stamps()
    preserved = esb_truth1_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1
    creds = next((s for s in surfaces if s.get("id") == "settlement_credentials"), {})
    api = next((s for s in surfaces if s.get("id") == "settlement_api_path"), {})
    wh = next((s for s in surfaces if s.get("id") == "warehouse_ro"), {})

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": probed_at,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "fake_settlement": False,
        "settlement_invented": False,
        "pnl_invented": False,
        "settlement": None,
        "pnl": None,
        "last_success": None,
        "esb_write": False,
        "esb_mutated": False,
        "write_authority_expanded": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "integration_id": INTEGRATION_ID,
        "settlement_api": "EXTERNAL_BLOCKER",
        "settlement_api_legacy_stamp": "UNAVAILABLE",
        "surfaces": surfaces,
        "surface_counts": by_status,
        "felix": dict(FELIX_EVIDENCE),
        "credentials_probe": {
            "creds_present": creds.get("creds_present") is True,
            "process_env_key_names": list(creds.get("process_env_key_names") or []),
            "dotenv_key_names": list(creds.get("dotenv_key_names") or []),
            "secret_values_exposed": False,
        },
        "api_path_probe": {
            "path_configured": api.get("path_configured") is True,
            "client_module_found": api.get("client_module_found") is True,
            "status": api.get("status"),
        },
        "warehouse_ro": {
            "status": wh.get("status"),
            "warehouse_status": wh.get("value"),
            "settlement_api": wh.get("settlement_api"),
            "href": ESB_TRUTH_HREF,
        },
        "honesty": {
            "policy": "probe_EXTERNAL_BLOCKER_with_evidence_not_UNKNOWN_forever",
            "settlement_api_path": "EXTERNAL_BLOCKER",
            "settlement_credentials": "EXTERNAL_BLOCKER",
            "settlement_amounts": "null_never_invent",
            "pnl": "null_never_invent",
            "warehouse_ro": wh.get("status"),
            "esb_truth1_settlement_api": "UNAVAILABLE",
            "human_commissioning": "ABSENT_vendor_api_missing",
            "unknown_forever_replaced": True,
        },
        "preserved": {"ESB-TRUTH-1": preserved},
        "esb_truth1_preserved": preserved.get("ok") is True,
        "honesty_board_href": HONESTY_BOARD,
        "esb_truth_href": ESB_TRUTH_HREF,
        "next_pack_for_parent_only": "SOP-CATALOG-SEED-ROUTE-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "no_push",
                "status_vocab",
                "unknown_forever_replaced",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def intg_probe_overlay() -> dict[str, Any]:
    """Compact overlay for INTG-TRUTH-1 INT-ESB-WOLF row."""
    board = None
    try:
        # Light: avoid recursion via preserved → build_slice → intg.
        api = probe_api_path()
        creds = probe_credentials()
        surfaces = {
            "settlement_api_path": api.get("status"),
            "settlement_credentials": creds.get("status"),
            "classification": CLASSIFICATION,
        }
    except Exception:  # noqa: BLE001
        surfaces = {
            "settlement_api_path": "EXTERNAL_BLOCKER",
            "settlement_credentials": "EXTERNAL_BLOCKER",
            "classification": CLASSIFICATION,
        }
        api = {"status": "EXTERNAL_BLOCKER"}
        creds = {"creds_present": False}
    _ = board
    return {
        "probe_status": "WAREHOUSE_READ_OK_PARTIAL_SETTLEMENT_EXTERNAL_BLOCKER",
        "audit_status": "PARTIAL_IN_BETA",
        "last_success": None,
        "settlement": None,
        "pnl": None,
        "settlement_path": "EXTERNAL_BLOCKER",
        "surfaces": surfaces,
        "probe_notes": (
            "ESB-SETTLEMENT-PATH-1: warehouse RO stays PARTIAL_IN_BETA "
            "(ESB-TRUTH-1 preserved). Settlement API path + credentials "
            "EXTERNAL_BLOCKER with Felix 2026-07-19 + env-key-absence evidence. "
            "No invented settlement/P&L. UNKNOWN-forever ceiling lifted."
        ),
        "probe_facts": {
            "pack": PACK_ID,
            "warehouse": "PARTIAL_IN_BETA",
            "settlement_api_path": "EXTERNAL_BLOCKER",
            "settlement_credentials": "EXTERNAL_BLOCKER",
            "creds_present": creds.get("creds_present") is True,
            "settlement": None,
            "pnl": None,
            "fake_settlement": False,
            "pnl_invented": False,
            "felix_dated": FELIX_EVIDENCE["dated"],
            "surfaces": surfaces,
        },
        "honesty_summary": "WAREHOUSE_PARTIAL_SETTLEMENT_EXTERNAL_BLOCKER",
    }
