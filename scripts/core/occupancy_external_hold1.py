#!/usr/bin/env python3
"""OCCUPANCY-EXTERNAL-HOLD-1 — Occupancy EXTERNAL hold (Yanolja/Mews).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
OCCUPANCY-EXTERNAL-HOLD-1 (armed 2026-09-30 after CONTENT-PUBLISH-PATH-1
PASS_VERIFIED). Challenges AMG occupancy UNKNOWN / Yanolja BLOCKED ceiling.

Stamps EXTERNAL_BLOCKER with Yanolja evidence (not UNKNOWN forever).
Never invents occupancy / ADR / RevPAR. Google NPWP remains MATT_ACTION
non-blocking. Preserves AMG-OCC-TRUTH-1 honesty.
staff_ready=false · human_commissioned=false.
Does not auto-chain WAVE9-SYNTH-CONTINUE / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import amg_occ_truth1 as _amg_occ
from core import amg_os_shell as _shell
from core import intg_truth_board as _intg

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "OCCUPANCY-EXTERNAL-HOLD-1"
SCHEMA_ID = "wolf.occupancy-external-hold-1.v1"
BOUND = "beta-amg-occupancy-external-hold"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
CLASSIFICATION = "EXTERNAL_BLOCKER"
CLOSES_TOWARD = ("CAP-AMG occupancy", "CAP-AMG-01", "INT-YAN-WOLF")
PRESERVED_PACKS = ("AMG-OCC-TRUTH-1", "AMG-OCC")
YANOLJA_ID = "INT-YAN-WOLF"
HONESTY_BOARD = "/ops/integrations-status"
AMG_OCC_HREF = "/amg/occ-truth-1"
AMG_SHELL_HREF = "/amg/os-shell"
NPWP_STATUS = "MATT_ACTION"
NPWP_BLOCKING = False
OWNER_PERSON = "PERS-MATT"

PAGE_PATHS = frozenset(
    {
        "/amg/occupancy-external-hold-1",
        "/amg/occupancy-external-hold-1/",
        "/amg/occupancy-external-hold",
        "/amg/occupancy-external-hold/",
        "/amg/occupancy-hold-1",
        "/amg/occupancy-hold-1/",
        "/ops/occupancy-external-hold-1",
        "/ops/occupancy-external-hold-1/",
        "/ops/occupancy-external-hold",
        "/ops/occupancy-external-hold/",
        "/occupancy-external-hold-1",
        "/occupancy-external-hold-1/",
        "/occupancy-external-hold-1.html",
        "/dashboards/occupancy-external-hold-1.html",
    }
)
API_PATH = "/api/amg/occupancy-external-hold-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/occupancy-external-hold-1",
        "/api/amg/occupancy-hold-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "EXTERNAL_BLOCKER",
        "BLOCKED_EXTERNAL",
        "PRESERVED",
        "MATT_ACTION",
        "ABSENT",
        "UNKNOWN",
        "REFUSED",
    }
)

# Name-only PMS / Yanolja / Mews env patterns — never load secret values.
_PMS_ENV_NAME_RE = re.compile(
    r"(YANOLJA|MEWS|PMS_|OCCUPANCY_|HOTEL_PMS|CLOUD_BEDS|CLOUDBEDS|"
    r"BETA_YANOLJA|YANOLJA_API|MEWS_API|MEWS_TOKEN)",
    re.IGNORECASE,
)

YANOLJA_EVIDENCE: dict[str, Any] = {
    "source": "INTG-TRUTH-1 + AMG-OCC-TRUTH-1 + credential discovery",
    "integration_id": YANOLJA_ID,
    "audit_status": "BLOCKED_EXTERNAL",
    "finding": (
        "INT-YAN-WOLF remains BLOCKED_EXTERNAL; CAP-AMG-01 not unblocked; "
        "no authorised live Yanolja/Mews PMS feed; occupancy/ADR stay UNKNOWN"
    ),
    "credential_doc": "docs/wolf/five/CREDENTIAL-DISCOVERY.md",
    "p1_queue": "docs/wolf/p0/P1-QUEUE.json — CAP-INTG-01 Yanolja; api_key empty; no Wolf reader",
    "mews_register": (
        "docs/deliveries/WOLF-CONNECTION-COMMISSIONING-REGISTER-BOX-ENRICHMENT-2026-09-22.md "
        "— Mews/Origin not found in available evidence"
    ),
    "amg_occ_result": "docs/wolf/ops/AMG-OCC-TRUTH-1-RESULT.md",
    "intg_result": "docs/wolf/ops/INTG-TRUTH-1-RESULT.md",
    "owner_note": (
        "Do not paste Yanolja/Mews keys in chat. Empty api_key / absent Mews "
        "is EXTERNAL_BLOCKER evidence — not inventable occupancy."
    ),
}

PMS_CLIENT_SEARCH: dict[str, Any] = {
    "glob": "scripts/core/**/*.py",
    "patterns": (
        "yanolja_client",
        "mews_client",
        "YanoljaClient",
        "MewsClient",
        "live_occupancy_feed",
        "pms_live_reader",
    ),
    "found_modules": (),
    "note": (
        "No dedicated live Yanolja/Mews occupancy client in beta-os scripts/core. "
        "amg_occ_truth1 / amg_os_shell are honesty shells only — UNKNOWN when blocked."
    ),
}


class OccupancyExternalHold1Error(ValueError):
    """Fail closed. Does not invent occupancy, ADR, or unblock PMS."""

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
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


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


def probe_yanolja_credentials() -> dict[str, Any]:
    """Name-only probe for Yanolja/Mews/PMS credentials. Never returns values."""
    process_hits = sorted(k for k in os.environ if _PMS_ENV_NAME_RE.search(k))
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {
            k
            for k in (dotenv_keys + example_keys)
            if _PMS_ENV_NAME_RE.search(k)
        }
    )
    # Presence of key *names* does not mean a live feed — still EXTERNAL without
    # authorised Wolf reader. Secret values never loaded.
    return {
        "id": "yanolja_credentials",
        "label": "Yanolja / Mews / PMS credentials",
        "status": "EXTERNAL_BLOCKER",
        "creds_present": bool(process_hits or file_hits),
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "value": None,
        "occupancy": None,
        "adr": None,
        "why": (
            "No authorised live Yanolja/Mews Wolf reader. Credential discovery: "
            "yanolja.json api_key empty (names-only evidence); Mews/Origin not found. "
            "Key-name presence ≠ live occupancy. EXTERNAL_BLOCKER — never invent."
        ),
        "evidence": YANOLJA_EVIDENCE["credential_doc"],
    }


def probe_yanolja_path() -> dict[str, Any]:
    """Probe INT-YAN-WOLF — BLOCKED_EXTERNAL with evidence."""
    board = _intg.build_board(persist_audit=False)
    yan = next(
        (
            c
            for c in (board.get("connectors") or [])
            if c.get("integration_id") == YANOLJA_ID
        ),
        None,
    )
    audit = (yan or {}).get("audit_status") or "BLOCKED_EXTERNAL"
    return {
        "id": "yanolja_path",
        "label": "Yanolja PMS path (INT-YAN-WOLF)",
        "status": "EXTERNAL_BLOCKER",
        "audit_status": audit,
        "blocked_external": True,
        "path_configured": False,
        "client_module_found": bool(PMS_CLIENT_SEARCH["found_modules"]),
        "value": None,
        "occupancy": None,
        "adr": None,
        "last_success": None,
        "yanolja_live": False,
        "pms_connected": False,
        "why": (
            f"{YANOLJA_ID} audit_status={audit}. CAP-AMG-01 not unblocked. "
            f"{YANOLJA_EVIDENCE['finding']}. EXTERNAL_BLOCKER evidenced."
        ),
        "evidence": YANOLJA_EVIDENCE["intg_result"],
        "yanolja": dict(YANOLJA_EVIDENCE),
        "client_search": dict(PMS_CLIENT_SEARCH),
    }


def probe_mews_path() -> dict[str, Any]:
    """Mews / Origin not found — EXTERNAL_BLOCKER."""
    return {
        "id": "mews_path",
        "label": "Mews / Origin PMS path",
        "status": "EXTERNAL_BLOCKER",
        "path_configured": False,
        "client_module_found": False,
        "value": None,
        "occupancy": None,
        "adr": None,
        "why": (
            "Mews/Origin not found in available evidence "
            "(commissioning register 2026-09-22). No invent occupancy from "
            "absent connector. EXTERNAL_BLOCKER."
        ),
        "evidence": YANOLJA_EVIDENCE["mews_register"],
    }


def probe_occupancy_amounts() -> dict[str, Any]:
    return {
        "id": "occupancy_amounts",
        "label": "Occupancy % / rooms / ADR / RevPAR",
        "status": "EXTERNAL_BLOCKER",
        "value": None,
        "occupancy": None,
        "occupancy_pct": None,
        "adr": None,
        "revpar": None,
        "rooms_sold": None,
        "rooms_available": None,
        "why": (
            "Occupancy amounts stay null while PMS is EXTERNAL_BLOCKER. "
            "Never invent percent, rooms, ADR, or RevPAR."
        ),
        "evidence": "pack forbids invent occupancy / invent ADR",
    }


def probe_npwp_matt_action() -> dict[str, Any]:
    """Google NPWP stays MATT_ACTION Owner-only — non-blocking."""
    return {
        "id": "npwp_matt_action",
        "label": "Google NPWP (MATT_ACTION)",
        "status": "MATT_ACTION",
        "blocking": False,
        "npwp": None,
        "npwp_number": None,
        "invented_npwp": False,
        "value": "MATT_ACTION_NON_BLOCKING",
        "why": (
            "Google NPWP remains Matt Owner exception ONLY (MATT_ACTION). "
            "Non-blocking for this pack — do not invent NPWP; do not fail "
            "EXIT waiting on NPWP."
        ),
        "evidence": "MISSION / ARM npwp=MATT_ACTION_NON_BLOCKING",
    }


def amg_occ_preserved() -> dict[str, Any]:
    """Read-only: AMG-OCC-TRUTH-1 honesty still holds."""
    try:
        slice_ = _amg_occ.build_slice()
        ok = (
            slice_.get("ok") is True
            and slice_.get("staff_ready") is False
            and slice_.get("human_commissioned") is False
            and slice_.get("invented_occupancy") is False
            and slice_.get("cap_amg_01_unblocked") is False
            and slice_.get("occupancy_unknown") is True
            and _amg_occ.all_occ_slots_unknown(slice_)
            and _amg_occ.yanolja_stays_blocked(slice_)
        )
        return {
            "ok": ok,
            "pack": "AMG-OCC-TRUTH-1",
            "href": AMG_OCC_HREF,
            "invented_occupancy": slice_.get("invented_occupancy"),
            "cap_amg_01_unblocked": slice_.get("cap_amg_01_unblocked"),
            "occupancy_unknown": slice_.get("occupancy_unknown"),
            "yanolja_status": (slice_.get("yanolja") or {}).get("audit_status"),
            "why": (
                "AMG-OCC-TRUTH-1 preserved: occupancy slots UNKNOWN/"
                "BLOCKED_EXTERNAL; invented_occupancy=false; "
                "cap_amg_01_unblocked=false; Yanolja BLOCKED_EXTERNAL. "
                "This pack stamps EXTERNAL_BLOCKER hold — does not replace OCC honesty."
                if ok
                else "AMG-OCC-TRUTH-1 honesty check failed — pack must not break it."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "AMG-OCC-TRUTH-1",
            "error": type(exc).__name__,
            "href": AMG_OCC_HREF,
            "why": "AMG-OCC-TRUTH-1 check failed — pack must not break OCC honesty.",
        }


def probe_amg_occ_preserved() -> dict[str, Any]:
    pin = amg_occ_preserved()
    return {
        "id": "amg_occ_preserved",
        "label": "AMG-OCC-TRUTH-1 honesty",
        "status": "PRESERVED" if pin.get("ok") else "EXTERNAL_BLOCKER",
        "value": "PRESERVED" if pin.get("ok") else None,
        "occupancy": None,
        "adr": None,
        "href": AMG_OCC_HREF,
        "why": pin.get("why"),
        "evidence": YANOLJA_EVIDENCE["amg_occ_result"],
        "preserved_ok": pin.get("ok") is True,
    }


def surface_stamps() -> list[dict[str, Any]]:
    """Hold surfaces with evidenced statuses. Occupancy/ADR stay null."""
    return [
        probe_yanolja_path(),
        probe_mews_path(),
        probe_yanolja_credentials(),
        probe_occupancy_amounts(),
        {
            "id": "last_success",
            "label": "Yanolja / occupancy last_success",
            "status": "EXTERNAL_BLOCKER",
            "value": None,
            "last_success": None,
            "occupancy": None,
            "adr": None,
            "why": (
                "last_success stays null. BLOCKED_EXTERNAL ≠ live connector "
                "success. Never invent."
            ),
            "evidence": "INTG / AMG-OCC honesty — null_if_unknown_never_invent",
        },
        probe_amg_occ_preserved(),
        probe_npwp_matt_action(),
        {
            "id": "cap_amg_01",
            "label": "CAP-AMG-01 unblock",
            "status": "EXTERNAL_BLOCKER",
            "value": False,
            "cap_amg_01_unblocked": False,
            "why": (
                "Does not unblock CAP-AMG-01. Needs external Yanolja/Mews "
                "authorisation. EXTERNAL_BLOCKER held."
            ),
            "evidence": YANOLJA_EVIDENCE["p1_queue"],
        },
    ]


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "invented_occupancy": False,
        "invented_adr": False,
        "invented_revpar": False,
        "fake_occupancy": False,
        "yanolja_live": False,
        "pms_connected": False,
        "cap_amg_01_unblocked": False,
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
        "amg_occ_preserved": True,
        "npwp": NPWP_STATUS,
        "npwp_blocking": NPWP_BLOCKING,
        "yanolja": "EXTERNAL_HOLD",
        "status_vocab": "EXTERNAL_BLOCKER|BLOCKED_EXTERNAL|PRESERVED|MATT_ACTION|ABSENT|UNKNOWN|REFUSED",
        "next_pack_for_parent_only": "WAVE9-SYNTH-CONTINUE",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "unknown_forever_replaced": True,
    }


def refuse_invent_occupancy(_body: dict | None = None) -> None:
    raise OccupancyExternalHold1Error(
        "Occupancy invent refused. EXTERNAL_BLOCKER — amounts stay null.",
        code="invent_occupancy_refused",
    )


def refuse_invent_adr(_body: dict | None = None) -> None:
    raise OccupancyExternalHold1Error(
        "ADR invent refused. EXTERNAL_BLOCKER — ADR stays null.",
        code="invent_adr_refused",
    )


def refuse_unblock_pms(_body: dict | None = None) -> None:
    raise OccupancyExternalHold1Error(
        "CAP-AMG-01 / Yanolja unblock refused. External seating required.",
        code="unblock_pms_refused",
    )


def refuse_invent_npwp(_body: dict | None = None) -> None:
    raise OccupancyExternalHold1Error(
        "NPWP invent refused. Google NPWP is MATT_ACTION Owner-only "
        "non-blocking — never invent NPWP numbers.",
        code="invent_npwp_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise OccupancyExternalHold1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "occupancy",
            "occupancy-pct",
            "occ",
            "occ-pct",
            "rooms-sold",
            "rooms-available",
            "invent-occupancy",
            "fake-occupancy",
            "fake-occ",
        } or norm in {
            "occupancy",
            "occupancy_pct",
            "rooms_sold",
            "rooms_available",
            "invent_occupancy",
            "fake_occupancy",
            "fake_occ",
        }:
            refuse_invent_occupancy(payload)
        if token in {
            "adr",
            "revpar",
            "invent-adr",
            "fake-adr",
            "invent-revpar",
        } or norm in {
            "adr",
            "revpar",
            "invent_adr",
            "fake_adr",
            "invent_revpar",
        }:
            refuse_invent_adr(payload)
        if token in {
            "unblock",
            "unblock-pms",
            "yanolja-live",
            "pms-live",
            "cap-amg-01",
            "mews-live",
        } or norm in {
            "unblock_pms",
            "yanolja_live",
            "pms_live",
            "cap_amg_01",
            "mews_live",
        }:
            refuse_unblock_pms(payload)
        if token in {"npwp", "npwp-number", "invent-npwp"} or norm in {
            "npwp",
            "npwp_number",
            "invent_npwp",
        }:
            refuse_invent_npwp(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        }:
            raise OccupancyExternalHold1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
        }:
            raise OccupancyExternalHold1Error(
                "Commissioning flags / PROVEN / READY are refused.",
                code="ready_refused",
            )
    raise OccupancyExternalHold1Error(
        "OCCUPANCY-EXTERNAL-HOLD-1 is a read-only EXTERNAL hold board. Writes refused.",
        code="write_refused",
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when hold surfaces use allowed vocab and occupancy/ADR stay null."""
    pack = payload if payload is not None else build_board()
    if pack.get("invented_occupancy") is True or pack.get("fake_occupancy") is True:
        return False
    if pack.get("invented_adr") is True or pack.get("invented_revpar") is True:
        return False
    if pack.get("occupancy") is not None or pack.get("adr") is not None:
        return False
    if pack.get("occupancy_pct") is not None:
        return False
    if pack.get("classification") != "EXTERNAL_BLOCKER":
        return False
    if pack.get("npwp") != "MATT_ACTION" or pack.get("npwp_blocking") is not False:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 6:
        return False
    blockers = 0
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        st = s.get("status")
        if st not in STATUS_VOCAB:
            return False
        if s.get("id") in (
            "yanolja_path",
            "mews_path",
            "yanolja_credentials",
            "occupancy_amounts",
            "last_success",
            "cap_amg_01",
        ):
            if st != "EXTERNAL_BLOCKER":
                return False
            if s.get("occupancy") is not None or s.get("adr") is not None:
                return False
            blockers += 1
        if s.get("id") == "amg_occ_preserved" and st not in (
            "PRESERVED",
            "EXTERNAL_BLOCKER",
        ):
            return False
        if s.get("id") == "npwp_matt_action" and st != "MATT_ACTION":
            return False
    return blockers >= 5


def no_invented_occupancy(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    return (
        pack.get("occupancy") is None
        and pack.get("occupancy_pct") is None
        and pack.get("adr") is None
        and pack.get("revpar") is None
        and pack.get("rooms_sold") is None
        and pack.get("invented_occupancy") is False
        and pack.get("invented_adr") is False
        and pack.get("fake_occupancy") is False
    )


def build_board() -> dict[str, Any]:
    """Public occupancy EXTERNAL hold board. Auth gating is caller's job."""
    probed_at = _now_wita()
    surfaces = surface_stamps()
    preserved = amg_occ_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1
    yan = next((s for s in surfaces if s.get("id") == "yanolja_path"), {})
    creds = next((s for s in surfaces if s.get("id") == "yanolja_credentials"), {})
    shell = _shell.build_shell()

    # WIRE-YANOLJA-READ-HOUSE-1 overlay — clear EXTERNAL when last-read usable
    try:
        from core.yanolja_last_read_ro import connection_stamp as _yan_stamp

        ys = _yan_stamp()
    except Exception:  # noqa: BLE001
        ys = {}
    occ = (ys or {}).get("occupancy") or {}
    live = bool(occ.get("usable"))
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
        "invented_occupancy": False,
        "invented_adr": False,
        "invented_revpar": False,
        "fake_occupancy": False,
        "occupancy": occ.get("pct") if live else None,
        "occupancy_pct": occ.get("pct") if live else None,
        "occupancy_display": occ.get("display") if live else None,
        "adr": None,
        "revpar": None,
        "rooms_sold": occ.get("occupied_rooms") if live else None,
        "rooms_available": occ.get("vacant") if live else None,
        "rooms_total": occ.get("rooms_total") if live else None,
        "guests": None,
        "last_success": ys.get("last_success") if live else None,
        "yanolja_live": live,
        "pms_connected": live,
        "cap_amg_01_unblocked": False,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": "LIVE_READ_PARTIAL" if live else CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "integration_id": YANOLJA_ID,
        "yanolja_status": "LIVE_READ_OK" if live else "EXTERNAL_BLOCKER",
        "yanolja_audit_status": (ys.get("audit_status") if ys else None)
        or yan.get("audit_status")
        or "BLOCKED_EXTERNAL",
        "source": "yanolja_last_read" if live else None,
        "freshness": occ.get("written_at") if live else None,
        "hold_note": (
            "Inventory+RoomInfo LIVE — occupancy hold cleared for that scope. "
            "Arrivals/ADR/RevPAR/guest depth still UNKNOWN/held."
            if live
            else "External hold remains — no usable last-read."
        ),
        "npwp": NPWP_STATUS,
        "npwp_blocking": NPWP_BLOCKING,
        "npwp_number": None,
        "invented_npwp": False,
        "surfaces": surfaces,
        "surface_counts": by_status,
        "yanolja_evidence": dict(YANOLJA_EVIDENCE),
        "credentials_probe": {
            "creds_present": creds.get("creds_present") is True,
            "process_env_key_names": list(creds.get("process_env_key_names") or []),
            "dotenv_key_names": list(creds.get("dotenv_key_names") or []),
            "secret_values_exposed": False,
        },
        "yanolja_path_probe": {
            "path_configured": yan.get("path_configured") is True,
            "client_module_found": yan.get("client_module_found") is True,
            "status": yan.get("status"),
            "audit_status": yan.get("audit_status"),
        },
        "honesty": {
            "policy": "stamp_EXTERNAL_BLOCKER_with_Yanolja_evidence_not_UNKNOWN_forever",
            "yanolja_path": "EXTERNAL_BLOCKER",
            "mews_path": "EXTERNAL_BLOCKER",
            "occupancy_amounts": "null_never_invent",
            "adr": "null_never_invent",
            "amg_occ": preserved.get("ok") and "PRESERVED" or "CHECK_FAILED",
            "npwp": "MATT_ACTION_NON_BLOCKING",
            "cap_amg_01": "EXTERNAL_BLOCKER",
            "unknown_forever_replaced": True,
        },
        "preserved": {"AMG-OCC-TRUTH-1": preserved},
        "amg_occ_preserved": preserved.get("ok") is True,
        "amg_os_shell_yanolja": (shell.get("yanolja") or {}).get("audit_status"),
        "honesty_board_href": HONESTY_BOARD,
        "amg_occ_href": AMG_OCC_HREF,
        "amg_shell_href": AMG_SHELL_HREF,
        "next_pack_for_parent_only": "WAVE9-SYNTH-CONTINUE",
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
                "yanolja",
            )
        },
    }


def public_payload() -> dict[str, Any]:
    return build_board()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "classification": CLASSIFICATION,
        "occupancy_property": False,
        "adr_property": False,
        "writes_accepted": False,
        "pms_unblocked": False,
        "npwp": NPWP_STATUS,
        "npwp_blocking": False,
        "preserved": list(PRESERVED_PACKS),
        "why": (
            "EXTERNAL_BLOCKER hold stamp with Yanolja/Mews evidence. "
            "No invented occupancy/ADR. AMG-OCC preserved. NPWP non-blocking."
        ),
    }
