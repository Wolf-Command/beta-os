#!/usr/bin/env python3
"""HR-DEFERRED-HOLD-STAMP-1 — HR deferred hold stamp (do not build HR).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave10 pack
HR-DEFERRED-HOLD-STAMP-1 (armed 2026-09-30 after ATRIUM-FC-TRUTH-DEEPEN-1
PASS_VERIFIED 163/0).

Stamps HR_DEFERRED as EXTERNAL_BLOCKER_OR_DEFERRED with charter +
requirements-class evidence. Does NOT build HR. Does NOT invent payroll /
headcount / onboarding go-live. Ceiling HOLD only — not COMPLETE.
staff_ready=false · human_commissioned=false.
Does not auto-chain RELIABILITY-PIPE-EPISODE-ROLLUP-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()

PACK_ID = "HR-DEFERRED-HOLD-STAMP-1"
SCHEMA_ID = "wolf.hr-deferred-hold-stamp-1.v1"
BOUND = "beta-hr-deferred-hold"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "HOLD"
CLASSIFICATION = "EXTERNAL_BLOCKER_OR_DEFERRED"
CLOSES_TOWARD = ("HR", "HR_DEFERRED")
CHARTER_HR = "DEFERRED_NEXT_WEEK"
EXPECTED_HR_DEFERRED_COUNT = 33
NEXT_PACK = "RELIABILITY-PIPE-EPISODE-ROLLUP-1"

CHARTER_PATH = BETA_ROOT / "state" / "final-completion" / "MISSION-CHARTER-20260929.json"
PHASE1_PATH = BETA_ROOT / "state" / "final-completion" / "PHASE1-COMPLETE.json"
SYNTHESIS_PATH = BETA_ROOT / "state" / "final-completion" / "MISSING-SYNTHESIS-20260930.json"
PHASE0_PATH = BETA_ROOT / "state" / "final-completion" / "PHASE0-CHECKPOINT-20260929.json"

# Existing CAP-HR skeletons — surface as DEFERRED shells only; never deepen live.
HR_SHELL_MODULES: tuple[dict[str, str], ...] = (
    {
        "id": "hr_hiring_onboarding",
        "module": "scripts/core/hr_hiring_onboarding.py",
        "cap": "CAP-HR-02",
        "label": "Hiring & Onboarding skeleton",
    },
    {
        "id": "hr_training_competency",
        "module": "scripts/core/hr_training_competency.py",
        "cap": "CAP-HR-03",
        "label": "Training & Competency skeleton",
    },
    {
        "id": "hr_payroll_inputs",
        "module": "scripts/core/hr_payroll_inputs.py",
        "cap": "CAP-HR-04",
        "label": "Payroll Inputs skeleton",
    },
    {
        "id": "hr_retention_signals",
        "module": "scripts/core/hr_retention_signals.py",
        "cap": "CAP-HR-05",
        "label": "Retention & Succession skeleton",
    },
)

PAGE_PATHS = frozenset(
    {
        "/ops/hr-deferred-hold-stamp-1",
        "/ops/hr-deferred-hold-stamp-1/",
        "/ops/hr-deferred-hold-stamp",
        "/ops/hr-deferred-hold-stamp/",
        "/ops/hr-deferred-hold",
        "/ops/hr-deferred-hold/",
        "/hr-deferred-hold-stamp-1",
        "/hr-deferred-hold-stamp-1/",
        "/hr-deferred-hold-stamp-1.html",
        "/dashboards/hr-deferred-hold-stamp-1.html",
    }
)
API_PATH = "/api/ops/hr-deferred-hold-stamp-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/hr-deferred-hold-stamp",
        "/api/ops/hr-deferred-hold",
        "/api/hr/deferred-hold-stamp-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "EXTERNAL_BLOCKER_OR_DEFERRED",
        "DEFERRED",
        "DEFERRED_NEXT_WEEK",
        "HOLD",
        "PRESERVED",
        "REFUSED",
        "ABSENT",
        "UNKNOWN",
    }
)

DEFER_EVIDENCE: dict[str, Any] = {
    "source": "MISSION-CHARTER + PHASE1-COMPLETE + MISSING-SYNTHESIS",
    "charter_key": "hr",
    "charter_value": CHARTER_HR,
    "charter_path": str(CHARTER_PATH.relative_to(BETA_ROOT)),
    "phase1_path": str(PHASE1_PATH.relative_to(BETA_ROOT)),
    "synthesis_path": str(SYNTHESIS_PATH.relative_to(BETA_ROOT)),
    "finding": (
        "Mission charter pins hr=DEFERRED_NEXT_WEEK. "
        f"~{EXPECTED_HR_DEFERRED_COUNT} requirements classed HR_DEFERRED. "
        "Matt deferred next week — stamp HOLD only; do not build HR."
    ),
    "owner_note": (
        "Do not invent payroll, headcount, or onboarding go-live. "
        "Existing CAP-HR-* modules stay empty DEFERRED shells."
    ),
}


class HrDeferredHoldStamp1Error(ValueError):
    """Fail closed. Does not invent payroll, headcount, or build HR."""

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


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_charter_hr() -> dict[str, Any]:
    charter = _read_json(CHARTER_PATH) or {}
    phase0 = _read_json(PHASE0_PATH) or {}
    value = charter.get("hr") or phase0.get("hr") or CHARTER_HR
    return {
        "value": value,
        "matches_deferred_next_week": value == CHARTER_HR,
        "charter_path": DEFER_EVIDENCE["charter_path"],
        "phase0_path": str(PHASE0_PATH.relative_to(BETA_ROOT)),
        "active_pack": charter.get("active_pack"),
        "wave10_active": charter.get("wave10_active"),
    }


def load_hr_deferred_requirements() -> dict[str, Any]:
    phase1 = _read_json(PHASE1_PATH) or {}
    synthesis = _read_json(SYNTHESIS_PATH) or {}
    rows = phase1.get("hr_deferred") or []
    if not isinstance(rows, list):
        rows = []
    count_phase1 = len(rows)
    counts = phase1.get("counts_by_class") or {}
    class_count = counts.get("HR_DEFERRED")
    synth_classes = synthesis.get("classes") or synthesis.get("counts_by_class") or {}
    if not isinstance(synth_classes, dict):
        synth_classes = {}
    synth_count = synth_classes.get("HR_DEFERRED")
    # Prefer explicit list length; fall back to class counters.
    count = count_phase1 or class_count or synth_count or 0
    samples = [
        {
            "id": r.get("id"),
            "text": r.get("text"),
            "domain": r.get("domain"),
        }
        for r in rows[:8]
        if isinstance(r, dict)
    ]
    return {
        "count": int(count) if count is not None else 0,
        "phase1_list_count": count_phase1,
        "phase1_class_count": class_count,
        "synthesis_class_count": synth_count,
        "expected": EXPECTED_HR_DEFERRED_COUNT,
        "matches_expected": int(count or 0) == EXPECTED_HR_DEFERRED_COUNT,
        "samples": samples,
        "phase1_path": DEFER_EVIDENCE["phase1_path"],
        "synthesis_path": DEFER_EVIDENCE["synthesis_path"],
    }


def probe_charter_deferral() -> dict[str, Any]:
    pin = load_charter_hr()
    ok = pin.get("matches_deferred_next_week") is True
    return {
        "id": "charter_hr_deferral",
        "label": "Mission charter hr pin",
        "status": "DEFERRED_NEXT_WEEK" if ok else "EXTERNAL_BLOCKER_OR_DEFERRED",
        "value": pin.get("value"),
        "payroll": None,
        "headcount": None,
        "why": (
            f"Charter hr={pin.get('value')}. Matt deferred next week — "
            "EXTERNAL_BLOCKER_OR_DEFERRED hold; do not build HR."
            if ok
            else "Charter hr pin missing or unexpected — still hold; never invent HR."
        ),
        "evidence": DEFER_EVIDENCE["charter_path"],
    }


def probe_hr_deferred_class() -> dict[str, Any]:
    req = load_hr_deferred_requirements()
    return {
        "id": "hr_deferred_requirements",
        "label": "HR_DEFERRED requirements class",
        "status": "EXTERNAL_BLOCKER_OR_DEFERRED",
        "value": req.get("count"),
        "count": req.get("count"),
        "expected": EXPECTED_HR_DEFERRED_COUNT,
        "matches_expected": req.get("matches_expected"),
        "payroll": None,
        "headcount": None,
        "why": (
            f"{req.get('count')} requirements classed HR_DEFERRED "
            f"(expected ~{EXPECTED_HR_DEFERRED_COUNT}). Hold stamp only — "
            "no invent payroll/headcount; no HR product build."
        ),
        "evidence": DEFER_EVIDENCE["phase1_path"],
        "samples": req.get("samples") or [],
    }


def probe_hr_shells() -> dict[str, Any]:
    shells: list[dict[str, Any]] = []
    for spec in HR_SHELL_MODULES:
        path = BETA_ROOT / spec["module"]
        shells.append(
            {
                "id": spec["id"],
                "cap": spec["cap"],
                "label": spec["label"],
                "module": spec["module"],
                "present": path.is_file(),
                "status": "DEFERRED",
                "live": False,
                "invented": False,
                "why": (
                    f"{spec['cap']} skeleton present as DEFERRED shell only. "
                    "Empty framework ≠ live HR. Do not deepen into go-live."
                    if path.is_file()
                    else f"{spec['cap']} module path absent — still DEFERRED; never invent."
                ),
            }
        )
    present = sum(1 for s in shells if s.get("present"))
    return {
        "id": "hr_shell_modules",
        "label": "CAP-HR-* deferred shells",
        "status": "DEFERRED",
        "value": f"{present}/{len(shells)} present as DEFERRED shells",
        "payroll": None,
        "headcount": None,
        "live_hr": False,
        "shells": shells,
        "why": (
            "Existing CAP-HR-02..05 modules are empty DEFERRED shells. "
            "This pack stamps hold — does not build or invent HR data."
        ),
        "evidence": "scripts/core/hr_*.py — skeletons only",
    }


def probe_payroll_amounts() -> dict[str, Any]:
    return {
        "id": "payroll_amounts",
        "label": "Payroll / payslip amounts",
        "status": "HOLD",
        "value": None,
        "payroll": None,
        "payslip": None,
        "headcount": None,
        "why": (
            "Payroll stays null while HR is DEFERRED_NEXT_WEEK. "
            "Never invent payroll or payslips."
        ),
        "evidence": "pack forbids invent payroll",
    }


def probe_headcount() -> dict[str, Any]:
    return {
        "id": "headcount",
        "label": "Headcount / roster",
        "status": "HOLD",
        "value": None,
        "payroll": None,
        "headcount": None,
        "roster": None,
        "why": (
            "Headcount stays null while HR is DEFERRED_NEXT_WEEK. "
            "Never invent headcount or roster."
        ),
        "evidence": "pack forbids invent headcount",
    }


def probe_build_hr() -> dict[str, Any]:
    return {
        "id": "build_hr",
        "label": "Build HR product",
        "status": "REFUSED",
        "value": False,
        "hr_built": False,
        "payroll": None,
        "headcount": None,
        "why": (
            "Build HR refused. Charter DEFERRED_NEXT_WEEK — stamp hold only. "
            "No payroll / onboarding / headcount go-live."
        ),
        "evidence": "ARM forbids: build HR, invent payroll",
    }


def probe_ceiling() -> dict[str, Any]:
    return {
        "id": "ceiling_hold",
        "label": "Ceiling",
        "status": "HOLD",
        "value": CEILING,
        "complete": False,
        "why": (
            "Ceiling HOLD only. Classification EXTERNAL_BLOCKER_OR_DEFERRED "
            "is not COMPLETE. SHELL≠COMPLETE · TESTS≠STAFF READY."
        ),
        "evidence": "pack classification EXTERNAL_BLOCKER_OR_DEFERRED",
    }


def surface_stamps() -> list[dict[str, Any]]:
    return [
        probe_charter_deferral(),
        probe_hr_deferred_class(),
        probe_hr_shells(),
        probe_payroll_amounts(),
        probe_headcount(),
        probe_build_hr(),
        probe_ceiling(),
    ]


def honesty_flags() -> dict[str, Any]:
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "invented_payroll": False,
        "invented_headcount": False,
        "invented_onboarding": False,
        "hr_built": False,
        "fake_hr": False,
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
        "complete_claimed": False,
        "charter_hr": CHARTER_HR,
        "hr_deferred_count_expected": EXPECTED_HR_DEFERRED_COUNT,
        "status_vocab": (
            "EXTERNAL_BLOCKER_OR_DEFERRED|DEFERRED|DEFERRED_NEXT_WEEK|"
            "HOLD|PRESERVED|REFUSED|ABSENT|UNKNOWN"
        ),
        "next_pack_for_parent_only": NEXT_PACK,
        "cursor_did_not_auto_start_next": True,
        "exit_report_forbidden": True,
        "headchef_forbidden": True,
    }


def refuse_invent_payroll(_body: dict | None = None) -> None:
    raise HrDeferredHoldStamp1Error(
        "Payroll invent refused. HR is DEFERRED_NEXT_WEEK — amounts stay null.",
        code="invent_payroll_refused",
    )


def refuse_invent_headcount(_body: dict | None = None) -> None:
    raise HrDeferredHoldStamp1Error(
        "Headcount invent refused. HR is DEFERRED_NEXT_WEEK — roster stays null.",
        code="invent_headcount_refused",
    )


def refuse_build_hr(_body: dict | None = None) -> None:
    raise HrDeferredHoldStamp1Error(
        "Build HR refused. Stamp hold only — Matt deferred next week.",
        code="build_hr_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise HrDeferredHoldStamp1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "payroll",
            "payslip",
            "pay-input",
            "invent-payroll",
            "fake-payroll",
            "salary",
            "wages",
        } or norm in {
            "payroll",
            "payslip",
            "pay_input",
            "invent_payroll",
            "fake_payroll",
            "salary",
            "wages",
        }:
            refuse_invent_payroll(payload)
        if token in {
            "headcount",
            "roster",
            "fte",
            "invent-headcount",
            "fake-headcount",
            "staff-count",
        } or norm in {
            "headcount",
            "roster",
            "fte",
            "invent_headcount",
            "fake_headcount",
            "staff_count",
        }:
            refuse_invent_headcount(payload)
        if token in {
            "build-hr",
            "build_hr",
            "hr-go-live",
            "onboarding-go-live",
            "hire",
            "hiring-live",
            "complete-hr",
        } or norm in {
            "build_hr",
            "hr_go_live",
            "onboarding_go_live",
            "hire",
            "hiring_live",
            "complete_hr",
        }:
            refuse_build_hr(payload)
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "8787",
            "15975",
        }:
            raise HrDeferredHoldStamp1Error(
                "Prod mutate refused. Pid 15975 is READ-ONLY on this pack.",
                code="prod_mutate_refused",
            )
        if token in {
            "staff-ready",
            "human-commissioned",
            "proven",
            "ready",
            "complete",
        }:
            raise HrDeferredHoldStamp1Error(
                "Commissioning flags / PROVEN / READY / COMPLETE are refused.",
                code="ready_refused",
            )
    raise HrDeferredHoldStamp1Error(
        "HR-DEFERRED-HOLD-STAMP-1 is a read-only deferred hold board. Writes refused.",
        code="write_refused",
    )


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    """True when hold surfaces use allowed vocab and payroll/headcount stay null."""
    pack = payload if payload is not None else build_board()
    if pack.get("invented_payroll") is True or pack.get("invented_headcount") is True:
        return False
    if pack.get("hr_built") is True or pack.get("fake_hr") is True:
        return False
    if pack.get("payroll") is not None or pack.get("headcount") is not None:
        return False
    if pack.get("classification") != CLASSIFICATION:
        return False
    if pack.get("ceiling") != CEILING:
        return False
    if pack.get("charter_hr") != CHARTER_HR:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 6:
        return False
    required = {
        "charter_hr_deferral",
        "hr_deferred_requirements",
        "hr_shell_modules",
        "payroll_amounts",
        "headcount",
        "build_hr",
        "ceiling_hold",
    }
    seen: set[str] = set()
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        st = s.get("status")
        if st not in STATUS_VOCAB:
            return False
        sid = str(s.get("id") or "")
        seen.add(sid)
        if sid in ("payroll_amounts", "headcount"):
            if s.get("payroll") is not None or s.get("headcount") is not None:
                return False
            if st != "HOLD":
                return False
        if sid == "build_hr" and st != "REFUSED":
            return False
        if sid == "ceiling_hold" and st != "HOLD":
            return False
        if sid == "hr_deferred_requirements" and st != CLASSIFICATION:
            return False
    return required.issubset(seen)


def no_invented_hr(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    return (
        pack.get("payroll") is None
        and pack.get("headcount") is None
        and pack.get("payslip") is None
        and pack.get("invented_payroll") is False
        and pack.get("invented_headcount") is False
        and pack.get("invented_onboarding") is False
        and pack.get("hr_built") is False
        and pack.get("fake_hr") is False
    )


def build_board() -> dict[str, Any]:
    """Public HR deferred hold board. Auth gating is caller's job."""
    probed_at = _now_wita()
    surfaces = surface_stamps()
    flags = honesty_flags()
    charter = load_charter_hr()
    req = load_hr_deferred_requirements()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1
    shells = next((s for s in surfaces if s.get("id") == "hr_shell_modules"), {})

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
        "invented_payroll": False,
        "invented_headcount": False,
        "invented_onboarding": False,
        "hr_built": False,
        "fake_hr": False,
        "payroll": None,
        "payslip": None,
        "headcount": None,
        "roster": None,
        "secrets_exposed": False,
        "ceiling": CEILING,
        "classification": CLASSIFICATION,
        "closes_toward": list(CLOSES_TOWARD),
        "charter_hr": charter.get("value") or CHARTER_HR,
        "charter_hr_matches": charter.get("matches_deferred_next_week") is True,
        "hr_deferred_count": req.get("count"),
        "hr_deferred_count_expected": EXPECTED_HR_DEFERRED_COUNT,
        "hr_deferred_matches_expected": req.get("matches_expected") is True,
        "complete": False,
        "surfaces": surfaces,
        "surface_counts": by_status,
        "defer_evidence": dict(DEFER_EVIDENCE),
        "charter_probe": charter,
        "requirements_probe": {
            "count": req.get("count"),
            "expected": EXPECTED_HR_DEFERRED_COUNT,
            "matches_expected": req.get("matches_expected"),
            "phase1_list_count": req.get("phase1_list_count"),
            "synthesis_class_count": req.get("synthesis_class_count"),
            "samples": req.get("samples") or [],
        },
        "hr_shells": shells.get("shells") or [],
        "honesty": {
            "policy": "stamp_HR_DEFERRED_hold_do_not_build_HR",
            "charter_hr": CHARTER_HR,
            "hr_deferred_class": CLASSIFICATION,
            "payroll": "null_never_invent",
            "headcount": "null_never_invent",
            "build_hr": "REFUSED",
            "ceiling": CEILING,
            "complete": False,
        },
        "next_pack_for_parent_only": NEXT_PACK,
        "cursor_did_not_auto_start_next": True,
        "exit_report_forbidden": True,
        "headchef_forbidden": True,
        **{
            k: flags[k]
            for k in (
                "operating_adoption",
                "proven_claimed",
                "ready_claimed",
                "complete_claimed",
                "no_push",
                "status_vocab",
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
        "ceiling": CEILING,
        "payroll_property": False,
        "headcount_property": False,
        "writes_accepted": False,
        "hr_built": False,
        "charter_hr": CHARTER_HR,
        "hr_deferred_count_expected": EXPECTED_HR_DEFERRED_COUNT,
        "why": (
            "EXTERNAL_BLOCKER_OR_DEFERRED hold stamp for HR_DEFERRED. "
            "No invent payroll/headcount. No HR product build. Ceiling HOLD."
        ),
    }
