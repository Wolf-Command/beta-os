#!/usr/bin/env python3
"""Owner Commissioning / Needs Matt queue — inside Progress (not a new DB).

Decision served: RULE-Wolf-Overnight-Owner-Commissioning-2026-09-22.md
Plan: docs/deliveries/GROK-PLAN-WOLF-OWNER-COMMISSIONING-QUEUE-P0-2026-09-22.md

Bound: beta-owner-commissioning-safe

Derives an ordered MY COMMISSIONING queue from real Beta state and records
immutable submit evidence. PASS closes a human-test card when criterion is
satisfied. PROBLEM* opens an engineering Work Item / CR lane and later emits
a RETEST card for the same person. Never invents PROVEN / READY / staff_ready
/ HUMAN COMMISSIONED without submit evidence. ClickUp + Telegram RETIRED.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_STATE_DIR = BETA_ROOT / "state" / "progress"
EVIDENCE_NAME = "commissioning-evidence.jsonl"
QUEUE_STATE_NAME = "commissioning-queue-state.json"
SEED_DOC = (
    BETA_ROOT
    / "docs"
    / "deliveries"
    / "WOLF-MORNING-COMMISSIONING-SEED-2026-09-22.md"
)

BOUND = "beta-owner-commissioning-safe"
SCHEMA_ID = "wolf.owner-commissioning-queue.v1"
ENTITY_OWNER = "ENT-GGV"
PERS_MATT = "PERS-MATT"

FEEDBACK_PASS = "PASS"
FEEDBACK_PROBLEM_FAMILY = frozenset(
    {
        "PROBLEM",
        "CONFUSING",
        "MISSING",
        "WRONG DATA",
        "PERMISSION PROBLEM",
        "MOBILE PROBLEM",
        "OTHER",
    }
)
ALL_FEEDBACK = frozenset({FEEDBACK_PASS}) | FEEDBACK_PROBLEM_FAMILY

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}
STATUS_OPEN = frozenset(
    {"READY_TO_TEST", "RETEST", "BLOCKED_EXTERNAL", "ENGINEERING"}
)

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "schema_id": SCHEMA_ID,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_human_commissioned": False,
    "human_commissioned_requires_submit_evidence": True,
    "clickup_retired": True,
    "telegram_retired": True,
    "production_mutate": False,
    "money_actions": False,
    "cloudflare_mutate": False,
    "owner_only_progress_surface": True,
    "inside_progress_not_new_db": True,
}


class CommissioningQueueError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def honesty_flags() -> dict[str, Any]:
    return dict(HONESTY)


def refuse_proven(_payload: dict[str, Any] | None = None) -> None:
    raise CommissioningQueueError(
        "Owner commissioning queue refuses inventing PROVEN.",
        code="proven_refused",
        http_status=405,
    )


def refuse_ready(_payload: dict[str, Any] | None = None) -> None:
    raise CommissioningQueueError(
        "Owner commissioning queue refuses inventing READY.",
        code="ready_refused",
        http_status=405,
    )


def refuse_staff_ready(_payload: dict[str, Any] | None = None) -> None:
    raise CommissioningQueueError(
        "Owner commissioning queue refuses inventing staff_ready.",
        code="staff_ready_refused",
        http_status=405,
    )


def refuse_human_commissioned_invent(
    _payload: dict[str, Any] | None = None,
) -> None:
    raise CommissioningQueueError(
        "HUMAN COMMISSIONED requires immutable submit evidence — invent refused.",
        code="human_commissioned_invent_refused",
        http_status=405,
    )


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def state_dir(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    env = (os.environ.get("WOLF_COMMISSIONING_STATE_DIR") or "").strip()
    if env:
        return Path(env)
    return DEFAULT_STATE_DIR


def evidence_path(override: Path | None = None) -> Path:
    return state_dir(override) / EVIDENCE_NAME


def queue_state_path(override: Path | None = None) -> Path:
    return state_dir(override) / QUEUE_STATE_NAME


def _ensure_state_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


def _load_queue_state(path: Path | None = None) -> dict[str, Any]:
    p = path or queue_state_path()
    if not p.is_file():
        return {"cards": {}, "retests": [], "as_of": None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cards": {}, "retests": [], "as_of": None}
    if not isinstance(data, dict):
        return {"cards": {}, "retests": [], "as_of": None}
    data.setdefault("cards", {})
    data.setdefault("retests", [])
    return data


def _save_queue_state(state: dict[str, Any], path: Path | None = None) -> None:
    p = path or queue_state_path()
    _ensure_state_dir(p.parent)
    state = dict(state)
    state["as_of"] = now_utc_iso()
    p.write_text(json.dumps(state, indent=2, default=str) + "\n", encoding="utf-8")


def _read_evidence(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or evidence_path()
    if not p.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = p.read_text(encoding="utf-8")
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
            rows.append(row)
    return rows


def _append_evidence(row: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    p = path or evidence_path()
    _ensure_state_dir(p.parent)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return row


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(name: str) -> str:
    base = Path(name or "evidence.bin").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "evidence.bin"
    return cleaned[:120]


def _nas_honesty() -> dict[str, Any]:
    try:
        from core import nas_library as nas

        flags = dict(getattr(nas, "HONESTY", {}) or {})
        retired = nas.retired_systems() if hasattr(nas, "retired_systems") else []
        return {"honesty": flags, "retired": retired}
    except Exception:  # noqa: BLE001
        return {
            "honesty": {"staff_ready": False, "proven": False, "ready": False},
            "retired": [],
        }


def _integration_retired() -> list[dict[str, Any]]:
    try:
        from core import integration_health as ih

        report = ih.build_report() if hasattr(ih, "build_report") else {}
        rows = report.get("retired") if isinstance(report, dict) else None
        if isinstance(rows, list) and rows:
            return [r for r in rows if isinstance(r, dict)]
    except Exception:  # noqa: BLE001
        pass
    return _nas_honesty().get("retired") or []


def seed_templates() -> list[dict[str, Any]]:
    """Morning seed derived from real surfaces — order is default priority, not hard lock."""
    nas = _nas_honesty()
    staff_ready = bool((nas.get("honesty") or {}).get("staff_ready"))
    cards: list[dict[str, Any]] = [
        {
            "id": "CMQ-GGV-FINANCE-NOTA-MATT",
            "task": "MATT — GGV FINANCE NOTA MOBILE TEST",
            "priority": "P0",
            "business": "GGV",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/ggv/finance",
            "do_this": [
                "On your phone: WOLF → Goss Group → GGV → Finance (or open /ggv/finance).",
                "Upload a real new nota (camera or photo/PDF) when one naturally occurs.",
                "Watch progress: Uploading → Reading → Checking vendor → Ready for review → Saved.",
                "Match an existing vendor OR create a new vendor inline (do not leave the nota).",
                "If duplicate vendor/nota warning appears, choose with reason — do not silent-skip.",
                "Confirm/correct details, submit, then find the same record in History/search.",
                "Submit feedback in MY COMMISSIONING. Do not mark Telegram retired yourself.",
            ],
            "check": "Phone path works end-to-end; payment still impossible; Telegram still operating until BOTH Matt+Amanda accept.",
            "capability": "CAP-GGV-FINANCE-NOTA",
            "criterion": "ggv_finance_nota_mobile_matt",
            "surface": "ggv_finance",
            "route": "/ggv/finance",
            "source": "docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md",
            "honesty_note": "Storage arch ENGINEERING_PASS (Peaches verified). Phone commissioning RESUMED — upload a real nota when one occurs; submit MY COMMISSIONING feedback. Telegram stays until BOTH accept.",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-GGV-FINANCE-NOTA-AMANDA",
            "task": "AMANDA — GGV FINANCE NOTA MOBILE TEST",
            "priority": "P0",
            "business": "GGV",
            "person_to_test": "Amanda",
            "audience": "NEEDS_STAFF",
            "open_href": "/ggv/finance",
            "do_this": [
                "On your phone: WOLF → Goss Group → GGV → Finance (or open /ggv/finance).",
                "Upload a real new nota (camera or photo/PDF) when one naturally occurs.",
                "Watch progress through to Saved. If a later step fails, confirm the file was kept.",
                "Match or create vendor on the same screen. Confirm extracted fields before submit.",
                "Search History and open the record (attachment + details + vendor).",
                "Submit feedback in MY COMMISSIONING. Telegram stays until Matt and Amanda both accept.",
            ],
            "check": "Amanda can run the Wolf nota path on phone without Telegram; no payment buttons work.",
            "capability": "CAP-GGV-FINANCE-NOTA",
            "criterion": "ggv_finance_nota_mobile_amanda",
            "surface": "ggv_finance",
            "route": "/ggv/finance",
            "source": "docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md",
            "honesty_note": "Storage arch ENGINEERING_PASS (Peaches verified). Phone commissioning RESUMED — upload a real nota when one occurs; submit MY COMMISSIONING feedback. Telegram stays until BOTH accept.",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-HUMAN-TEST-MATT-GGV-FINANCE",
            "task": "HUMAN TEST — MATT — GGV FINANCE",
            "priority": "P0",
            "business": "GGV",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/ggv/finance",
            "do_this": [
                "Open /ggv/finance — confirm UPLOAD STATEMENT, UPLOAD NOTA, HISTORICAL STATEMENTS, RECONCILIATION actions.",
                "Upload a real Mandiri statement when one occurs (Jun or Sep gap).",
                "Open Historical Statements library — verify months and OPEN view.",
                "Run reconciliation browse — no auto-post, no payment buttons.",
                "Submit feedback in MY COMMISSIONING when done.",
            ],
            "check": "GGV finance statement library + upload + recon paths work for Matt; Zayen cannot see GGV finance.",
            "capability": "CAP-GGV-FINANCE-STATEMENTS",
            "criterion": "ggv_finance_statements_matt",
            "surface": "ggv_finance",
            "route": "/ggv/finance",
            "source": "FINANCE-CORE-STATEMENTS-1",
            "honesty_note": "READY_TO_TEST — engineering proved; not COMMISSIONED until Matt submits MY COMMISSIONING.",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
            "status": "READY_TO_TEST",
        },
        {
            "id": "CMQ-HUMAN-TEST-ZAYEN-AMG-FINANCE",
            "task": "HUMAN TEST — ZAYEN — AMG FINANCE",
            "priority": "P0",
            "business": "AMG",
            "person_to_test": "Zayen",
            "audience": "NEEDS_STAFF",
            "open_href": "/amg/finance",
            "do_this": [
                "Open /amg/finance/notas and /amg/finance/statements.",
                "Verify CIMB statement library per account; upload if a gap month arrives.",
                "Confirm AMG rows do not appear on GGV finance.",
                "Submit staff commissioning feedback.",
            ],
            "check": "Zayen can browse AMG finance statements; GGV finance returns 403.",
            "capability": "CAP-AMG-FINANCE-STATEMENTS",
            "criterion": "amg_finance_statements_zayen",
            "surface": "amg_finance",
            "route": "/amg/finance",
            "source": "FINANCE-CORE-STATEMENTS-1",
            "honesty_note": "READY_TO_TEST — not in Matt NEEDS_MATT queue.",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
            "status": "READY_TO_TEST",
        },
        {
            "id": "CMQ-HUMAN-TEST-ZAYEN-BZG-FINANCE",
            "task": "HUMAN TEST — ZAYEN — BZG FINANCE",
            "priority": "P0",
            "business": "BZG",
            "person_to_test": "Zayen",
            "audience": "NEEDS_STAFF",
            "open_href": "/bzg/finance",
            "do_this": [
                "Open /bzg/finance/bank and statement library surfaces.",
                "Verify Mandiri/BRI/BNI month completeness strip (missing Sep).",
                "Upload a statement only when a real gap file is available.",
                "Submit staff commissioning feedback.",
            ],
            "check": "Zayen can browse BZG bank statements; no payment execution.",
            "capability": "CAP-BZG-FINANCE-STATEMENTS",
            "criterion": "bzg_finance_statements_zayen",
            "surface": "bzg_finance",
            "route": "/bzg/finance",
            "source": "FINANCE-CORE-STATEMENTS-1",
            "honesty_note": "READY_TO_TEST — not in Matt NEEDS_MATT queue.",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
            "status": "READY_TO_TEST",
        },
        {
            "id": "CMQ-GLOBAL-NAV-OWNER",
            "task": "Wolf Global Navigation Owner review (desktop + phone)",
            "priority": "P0",
            "business": "System",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/wolf",
            "do_this": [
                "Open Wolf on desktop — confirm Empire home + Global Nav.",
                "Open same surface on phone — confirm single phone nav.",
                "Confirm no ClickUp / Telegram commission paths.",
            ],
            "check": "Owner can declare review only; navigation usable; proven stays false.",
            "capability": "CAP-CORE-NAV",
            "criterion": "global_nav_owner_review",
            "surface": "progress",
            "route": "/wolf",
            "source": "docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-NAS-HAIKAL",
            "task": "NAS Library Haikal commissioning (upload · search · preview · download + NAS path confirm)",
            "priority": "P0",
            "business": "GGV",
            "person_to_test": "Haikal",
            "audience": "NEEDS_STAFF",
            "open_href": "/content-2.0",
            "do_this": [
                "Open Content / NAS Library on Beta.",
                "Upload one test asset into the Wolf Library import path.",
                "Search, preview, and download that asset.",
                "Confirm the NAS path under _Imports/Wolf-Library.",
            ],
            "check": "Staff can complete the path; staff_ready stays false until Haikal submit.",
            "capability": "CAP-GGV-01",
            "criterion": "nas_library_haikal_human",
            "surface": "nas_library",
            "route": "/content-2.0",
            "source": "state/completion-register/wolf-connection-commissioning-nas-20260922.json",
            "confidence": "DERIVED",
            "honesty_note": f"staff_ready={staff_ready}",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-SMART-UPLOAD-RETEST",
            "task": "Smart Upload regression retest (detail validation)",
            "priority": "P0",
            "business": "GGV",
            "person_to_test": "Haikal",
            "audience": "NEEDS_STAFF",
            "open_href": "/content-2.0",
            "do_this": [
                "Open Smart Upload on Beta.",
                "Submit a detail-validation case that previously failed.",
                "Confirm error copy is human and the happy path completes.",
            ],
            "check": "Prior detail-validation defect does not recur.",
            "capability": "CAP-GGV-01",
            "criterion": "smart_upload_detail_retest",
            "surface": "smart_upload",
            "route": "/content-2.0",
            "source": "scripts/smart_upload.py",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-DEVI-UMA-MOBILE",
            "task": "Uma / BZG Devi mobile day-loop",
            "priority": "P1",
            "business": "BZG",
            "person_to_test": "Devi",
            "audience": "NEEDS_STAFF",
            "open_href": "/bzg/uma-blu",
            "do_this": [
                "Open Uma Blu Today on phone.",
                "Walk the day-loop cards without dead buttons.",
                "Note any permission or mobile problem.",
            ],
            "check": "Devi can operate the day loop on phone; human commissioning NOT invented.",
            "capability": "CAP-BZG-03",
            "criterion": "devi_uma_mobile_day_loop",
            "surface": "uma_ops",
            "route": "/bzg/uma-blu",
            "source": "docs/deliveries/GROK-PLAN-DEVI-UMA-COMMISSION-AUTH-2026-09-19.md",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-AMANDA-GGV",
            "task": "GGV Amanda navigation / operating loop",
            "priority": "P1",
            "business": "GGV",
            "person_to_test": "Amanda",
            "audience": "NEEDS_STAFF",
            "open_href": "/ggv-ops-pack",
            "do_this": [
                "Open GGV Ops Pack as Amanda.",
                "Follow the lead operating loop to the next action.",
                "Confirm empty states show a next action.",
            ],
            "check": "Amanda can navigate and act without inventing leads.",
            "capability": "CAP-GGV-04",
            "criterion": "amanda_ggv_ops_loop",
            "surface": "ggv_ops",
            "route": "/ggv-ops-pack",
            "source": "scripts/core/ggv_ops_pack.py",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-AMG-DAY",
            "task": "AMG operator navigation day-loop",
            "priority": "P1",
            "business": "AMG",
            "person_to_test": "Coral / authorised",
            "audience": "NEEDS_STAFF",
            "open_href": "/amg-ops-pack",
            "do_this": [
                "Open AMG Ops Pack.",
                "Open one day object and record a note / recovery / handover touch.",
                "Confirm wait-words stay honest when hotel data is empty.",
            ],
            "check": "Operator path works; no invented occupancy / ADR / PMS.",
            "capability": "CAP-AMG-04",
            "criterion": "amg_day_loop_operator",
            "surface": "amg_ops",
            "route": "/amg-ops-pack",
            "source": "scripts/core/amg_ops_pack.py",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-PROGRESS-NEEDS-YOU",
            "task": "Owner Progress Needs You honesty",
            "priority": "P1",
            "business": "System",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/progress#my-commissioning",
            "do_this": [
                "Open Progress → MY COMMISSIONING.",
                "Confirm Needs Matt vs Needs Staff counters match the queue.",
                "Confirm no invented HUMAN COMMISSIONED without evidence.",
            ],
            "check": "Needs You / commissioning counters are honest and Owner-only.",
            "capability": "CAP-CORE-PROGRESS",
            "criterion": "progress_needs_you_honesty",
            "surface": "progress",
            "route": "/progress",
            "source": "scripts/core/progress_read_model.py",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-INTEGRATION-HEALTH",
            "task": "Integration Health readable + honest (ClickUp / Telegram RETIRED)",
            "priority": "P1",
            "business": "System",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/integration-health",
            "do_this": [
                "Open Integration Health.",
                "Confirm ClickUp and Telegram show RETIRED / historical only.",
                "Confirm no commission call-to-action for retired systems.",
            ],
            "check": "Retired systems are visible and not queued for commission.",
            "capability": "CAP-INTG-HEALTH",
            "criterion": "integration_health_retired_visible",
            "surface": "integration_health",
            "route": "/integration-health",
            "source": "scripts/core/integration_health.py",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
    ]
    return cards


def _card_from_template(t: dict[str, Any], *, status: str = "READY_TO_TEST") -> dict[str, Any]:
    return {
        "id": t["id"],
        "task": t["task"],
        "priority": t.get("priority") or "P1",
        "business": t.get("business") or "System",
        "person_to_test": t.get("person_to_test") or "Matt",
        "audience": t.get("audience") or "NEEDS_MATT",
        "status": status,
        "open_href": t.get("open_href") or "/progress",
        "do_this": list(t.get("do_this") or []),
        "check": t.get("check") or "",
        "capability": t.get("capability"),
        "criterion": t.get("criterion"),
        "surface": t.get("surface") or "progress",
        "route": t.get("route") or t.get("open_href") or "/progress",
        "source": t.get("source"),
        "confidence": t.get("confidence") or "DERIVED",
        "honesty_note": t.get("honesty_note"),
        "parent_task_id": t.get("parent_task_id"),
        "work_item_id": t.get("work_item_id"),
        "cr_id": t.get("cr_id"),
        "commissioned": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "feedback_options": sorted(ALL_FEEDBACK),
    }


def counters(cards: list[dict[str, Any]]) -> dict[str, int]:
    out = {
        "NEEDS_MATT": 0,
        "NEEDS_STAFF": 0,
        "READY_TO_TEST": 0,
        "RETEST": 0,
        "BLOCKED_EXTERNAL": 0,
        "ENGINEERING": 0,
        "COMMISSIONED": 0,
    }
    for c in cards:
        status = str(c.get("status") or "").upper()
        audience = str(c.get("audience") or "").upper()
        if status == "COMMISSIONED" or c.get("commissioned"):
            out["COMMISSIONED"] += 1
            continue
        if status == "ENGINEERING":
            out["ENGINEERING"] += 1
        elif status == "RETEST":
            out["RETEST"] += 1
            if audience == "NEEDS_STAFF":
                out["NEEDS_STAFF"] += 1
            else:
                out["NEEDS_MATT"] += 1
        elif status == "BLOCKED_EXTERNAL":
            out["BLOCKED_EXTERNAL"] += 1
            if audience == "NEEDS_STAFF":
                out["NEEDS_STAFF"] += 1
            else:
                out["NEEDS_MATT"] += 1
        elif status == "READY_TO_TEST":
            out["READY_TO_TEST"] += 1
            if audience == "NEEDS_STAFF":
                out["NEEDS_STAFF"] += 1
            else:
                out["NEEDS_MATT"] += 1
        else:
            if audience == "NEEDS_STAFF":
                out["NEEDS_STAFF"] += 1
            else:
                out["NEEDS_MATT"] += 1
    return out


def _sort_key(card: dict[str, Any]) -> tuple[Any, ...]:
    status = str(card.get("status") or "")
    # Active human work first: RETEST then READY_TO_TEST, then blocked, then eng, then done
    status_rank = {
        "RETEST": 0,
        "READY_TO_TEST": 1,
        "BLOCKED_EXTERNAL": 2,
        "ENGINEERING": 3,
        "COMMISSIONED": 9,
    }.get(status, 5)
    pri = PRIORITY_RANK.get(str(card.get("priority") or "P2"), 9)
    # Needs Matt slightly ahead of staff for Owner morning start
    aud = 0 if str(card.get("audience") or "") == "NEEDS_MATT" else 1
    return (status_rank, pri, aud, str(card.get("id") or ""))


def build_queue(
    *,
    state_override: Path | None = None,
    include_commissioned: bool = True,
) -> dict[str, Any]:
    """Derive ordered MY COMMISSIONING queue from seed + mutable queue state + evidence."""
    nas = _nas_honesty()
    retired = _integration_retired() or nas.get("retired") or []
    qstate = _load_queue_state(queue_state_path(state_override))
    evidence = _read_evidence(evidence_path(state_override))
    commissioned_ids = {
        str(r.get("task_id"))
        for r in evidence
        if str(r.get("feedback") or "").upper() == FEEDBACK_PASS
        and r.get("criterion_satisfied")
    }

    cards: list[dict[str, Any]] = []
    seen: set[str] = set()

    for tmpl in seed_templates():
        cid = str(tmpl["id"])
        seen.add(cid)
        override = (qstate.get("cards") or {}).get(cid) or {}
        status = str(override.get("status") or "READY_TO_TEST").upper()
        if cid in commissioned_ids or status == "COMMISSIONED":
            status = "COMMISSIONED"
        card = _card_from_template(tmpl, status=status)
        card.update(
            {
                k: override[k]
                for k in (
                    "work_item_id",
                    "cr_id",
                    "parent_task_id",
                    "last_feedback",
                    "last_evidence_id",
                )
                if k in override
            }
        )
        if status == "COMMISSIONED":
            card["commissioned"] = True
            # Honesty: commissioned only via submit evidence — never invent proven/ready
            card["proven"] = False
            card["ready"] = False
            card["staff_ready"] = False
        cards.append(card)

    for retest in qstate.get("retests") or []:
        if not isinstance(retest, dict):
            continue
        rid = str(retest.get("id") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        parent = str(retest.get("parent_task_id") or "")
        base = next((t for t in seed_templates() if t["id"] == parent), None)
        if base is None:
            base = {
                "id": rid,
                "task": retest.get("task") or "Retest",
                "priority": retest.get("priority") or "P0",
                "business": retest.get("business") or "System",
                "person_to_test": retest.get("person_to_test") or "Matt",
                "audience": retest.get("audience") or "NEEDS_MATT",
                "open_href": retest.get("open_href") or "/progress",
                "do_this": retest.get("do_this") or ["Retest the fix on Beta."],
                "check": retest.get("check") or "Prior PROBLEM no longer reproduces.",
                "capability": retest.get("capability"),
                "criterion": retest.get("criterion") or "retest",
                "surface": retest.get("surface") or "progress",
                "route": retest.get("route") or "/progress",
                "source": retest.get("source") or "owner_commissioning_queue",
            }
        card = _card_from_template(base, status="RETEST")
        card["id"] = rid
        card["parent_task_id"] = parent
        card["task"] = f"RETEST: {card['task']}"
        card["work_item_id"] = retest.get("work_item_id")
        card["cr_id"] = retest.get("cr_id")
        if rid in commissioned_ids or str(retest.get("status") or "") == "COMMISSIONED":
            card["status"] = "COMMISSIONED"
            card["commissioned"] = True
        cards.append(card)

    cards.sort(key=_sort_key)
    if not include_commissioned:
        cards = [c for c in cards if c.get("status") != "COMMISSIONED"]

    active = [c for c in cards if c.get("status") in STATUS_OPEN]
    counts = counters(cards)
    return {
        "ok": True,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "title": "MY COMMISSIONING",
        "subtitle": "Needs Matt · ordered human commission queue inside Progress",
        "as_of": now_utc_iso(),
        "seed_doc": str(SEED_DOC.relative_to(BETA_ROOT)) if SEED_DOC.is_file() else None,
        "cards": cards,
        "active_cards": active,
        "first_task": active[0] if active else None,
        "counters": counts,
        "retired_systems": [
            {
                "source_id": r.get("source_id"),
                "name": r.get("name"),
                "status": r.get("status") or "RETIRED",
                "commission": False,
            }
            for r in retired
            if isinstance(r, dict)
        ],
        "honesty": honesty_flags(),
        "nas_staff_ready": bool((nas.get("honesty") or {}).get("staff_ready")),
        "evidence_count": len(evidence),
        "clickup_retired": True,
        "telegram_retired": True,
    }


def list_history(
    *,
    limit: int = 50,
    state_override: Path | None = None,
) -> dict[str, Any]:
    rows = list(reversed(_read_evidence(evidence_path(state_override))))
    return {
        "ok": True,
        "bound": BOUND,
        "count": len(rows),
        "rows": rows[: max(0, int(limit))],
        "honesty": honesty_flags(),
    }


def _persist_file(
    *,
    task_id: str,
    evidence_id: str,
    filename: str,
    content_type: str,
    data: bytes,
    state_override: Path | None = None,
) -> dict[str, Any]:
    root = state_dir(state_override) / "commissioning-files" / task_id
    _ensure_state_dir(root)
    safe = _safe_filename(filename)
    dest = root / f"{evidence_id[:12]}-{safe}"
    dest.write_bytes(data)
    return {
        "path": str(dest.relative_to(BETA_ROOT))
        if dest.is_relative_to(BETA_ROOT)
        else str(dest),
        "filename": safe,
        "content_type": content_type or "application/octet-stream",
        "sha256": _sha256_bytes(data),
        "bytes": len(data),
    }


def _find_card(task_id: str, state_override: Path | None = None) -> dict[str, Any] | None:
    q = build_queue(state_override=state_override, include_commissioned=True)
    for c in q.get("cards") or []:
        if c.get("id") == task_id:
            return c
    return None


def _under_test() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    import sys

    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _create_engineering_lane(
    *,
    card: dict[str, Any],
    feedback: str,
    comment: str,
    evidence_id: str,
    verified_person_id: str,
    state_override: Path | None = None,
) -> dict[str, Any]:
    """PROBLEM* → Work Item + CR NEEDS_ENGINEERING. Matt does not manage eng tickets."""
    out: dict[str, Any] = {
        "work_item_id": None,
        "cr_id": None,
        "engineering_lane": True,
        "owner_manages_engineering": False,
    }
    title = f"Commissioning PROBLEM: {card.get('task')}"
    desc = (
        f"Feedback={feedback}\n"
        f"Person to test={card.get('person_to_test')}\n"
        f"Criterion={card.get('criterion')}\n"
        f"Evidence={evidence_id}\n"
        f"Comment={comment or ''}\n"
        "Factory: Beta fix then auto RETEST for same person."
    )
    # Tests / isolated state dirs never mutate live catalog.
    if _under_test() or state_override is not None:
        out["work_item_id"] = f"WI-TEST-{uuid.uuid4().hex[:10]}"
        out["cr_id"] = f"CR-TEST-{uuid.uuid4().hex[:10]}"
        out["synthetic"] = True
        out["title"] = title
        out["description"] = desc
        return out
    try:
        from core import work_items as wi

        wi_row = wi.create_work_item(
            title=title[:200],
            owning_entity_id=ENTITY_OWNER,
            work_type="EXCEPTION",
            source_type="HUMAN",
            created_by_actor_type="PERSON",
            verified_person_id=verified_person_id,
            description=desc,
            priority=1 if card.get("priority") == "P0" else 2,
            source_id=str(card.get("id")),
            owner_person_id=None,
        )
        out["work_item_id"] = wi_row.get("work_item_id")
    except Exception as exc:  # noqa: BLE001
        out["work_item_error"] = str(exc)[:240]

    try:
        from core import completion_register as cr

        conn = cr.db_connect()
        try:
            row = cr.upsert(
                conn,
                item_type="COMMISSIONING_PROBLEM",
                title=title[:180],
                entity=ENTITY_OWNER,
                domain=str(card.get("business") or "System"),
                view_key="Empire",
                capability=card.get("capability"),
                why_it_matters="Human commissioning PROBLEM — factory engineering lane + RETEST.",
                state="OPEN",
                blocker_class="NEEDS_ENGINEERING",
                evidence=f"evidence_id={evidence_id}; feedback={feedback}",
                source="owner_commissioning_queue",
                next_action="Beta fix then emit RETEST for same person_to_test",
                work_item_id=out.get("work_item_id"),
            )
            conn.commit()
            out["cr_id"] = row.get("id")
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        out["cr_error"] = str(exc)[:240]
    return out


def emit_retest(
    *,
    parent_task_id: str,
    work_item_id: str | None = None,
    cr_id: str | None = None,
    state_override: Path | None = None,
) -> dict[str, Any]:
    """After engineering fix, emit RETEST card for same person (not Matt eng ticket)."""
    parent = _find_card(parent_task_id, state_override=state_override)
    if parent is None:
        # Fall back to seed template
        parent = next(
            (t for t in seed_templates() if t["id"] == parent_task_id),
            None,
        )
    if parent is None:
        raise CommissioningQueueError(
            f"unknown parent task: {parent_task_id}",
            code="unknown_task",
        )
    rid = f"CMQ-RETEST-{parent_task_id.replace('CMQ-', '')}-{uuid.uuid4().hex[:8]}"
    qpath = queue_state_path(state_override)
    state = _load_queue_state(qpath)
    # Mark parent ENGINEERING→done-ish (still not COMMISSIONED)
    cards = state.setdefault("cards", {})
    prev = dict(cards.get(parent_task_id) or {})
    # Parent stays ENGINEERING until RETEST PASSes (Matt does not manage eng tickets).
    prev["status"] = "ENGINEERING"
    prev["work_item_id"] = work_item_id or prev.get("work_item_id")
    prev["cr_id"] = cr_id or prev.get("cr_id")
    prev["retest_emitted"] = True
    cards[parent_task_id] = prev
    retests = state.setdefault("retests", [])
    entry = {
        "id": rid,
        "parent_task_id": parent_task_id,
        "task": parent.get("task"),
        "priority": parent.get("priority") or "P0",
        "business": parent.get("business"),
        "person_to_test": parent.get("person_to_test"),
        "audience": parent.get("audience"),
        "open_href": parent.get("open_href"),
        "do_this": parent.get("do_this"),
        "check": parent.get("check"),
        "capability": parent.get("capability"),
        "criterion": parent.get("criterion"),
        "surface": parent.get("surface"),
        "route": parent.get("route"),
        "source": parent.get("source"),
        "work_item_id": work_item_id,
        "cr_id": cr_id,
        "status": "RETEST",
        "emitted_at": now_utc_iso(),
    }
    retests.append(entry)
    _save_queue_state(state, qpath)
    return {"ok": True, "retest": entry, "honesty": honesty_flags()}


def submit_feedback(
    *,
    task_id: str,
    feedback: str,
    comment: str = "",
    identity: dict[str, Any] | None = None,
    files: list[dict[str, Any]] | None = None,
    state_override: Path | None = None,
    emit_retest_on_problem: bool = False,
) -> dict[str, Any]:
    """Immutable evidence + PASS/PROBLEM factory effects. Never invents PROVEN/READY."""
    fb = (feedback or "").strip().upper()
    if fb not in ALL_FEEDBACK:
        raise CommissioningQueueError(
            f"invalid feedback: {feedback!r}",
            code="invalid_feedback",
        )
    card = _find_card(task_id, state_override=state_override)
    if card is None:
        raise CommissioningQueueError(
            f"unknown task_id: {task_id}",
            code="unknown_task",
        )
    if card.get("status") == "COMMISSIONED" and fb == FEEDBACK_PASS:
        raise CommissioningQueueError(
            "task already commissioned via prior PASS evidence",
            code="already_commissioned",
        )

    identity = identity or {}
    person_id = (
        identity.get("person_id")
        or identity.get("verified_person_id")
        or PERS_MATT
    )
    email = identity.get("email") or identity.get("subject") or ""
    evidence_id = f"EVD-CMQ-{uuid.uuid4().hex[:12]}"
    stamp = now_utc_iso()

    file_rows: list[dict[str, Any]] = []
    for f in files or []:
        if not isinstance(f, dict):
            continue
        data = f.get("data") or b""
        if not isinstance(data, (bytes, bytearray)):
            continue
        file_rows.append(
            _persist_file(
                task_id=task_id,
                evidence_id=evidence_id,
                filename=str(f.get("filename") or "upload.bin"),
                content_type=str(f.get("content_type") or "application/octet-stream"),
                data=bytes(data),
                state_override=state_override,
            )
        )

    criterion_satisfied = False
    effects: dict[str, Any] = {}

    if fb == FEEDBACK_PASS:
        # Human-test criterion satisfied only with explicit PASS submit evidence.
        criterion_satisfied = True
        qpath = queue_state_path(state_override)
        state = _load_queue_state(qpath)
        entry = dict((state.get("cards") or {}).get(task_id) or {})
        entry.update(
            {
                "status": "COMMISSIONED",
                "last_feedback": FEEDBACK_PASS,
                "last_evidence_id": evidence_id,
                "commissioned_at": stamp,
            }
        )
        state.setdefault("cards", {})[task_id] = entry
        # If this is a retest id, mark it commissioned in retests list
        for r in state.get("retests") or []:
            if isinstance(r, dict) and r.get("id") == task_id:
                r["status"] = "COMMISSIONED"
                r["last_evidence_id"] = evidence_id
        _save_queue_state(state, qpath)
        effects = {
            "path": "PASS",
            "criterion_satisfied": True,
            "human_commissioned": True,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "note": "HUMAN COMMISSIONED for this queue card only — not CAP PROVEN/READY.",
        }
    else:
        # PROBLEM* → engineering lane; optionally emit RETEST immediately for prove tests
        eng = _create_engineering_lane(
            card=card,
            feedback=fb,
            comment=comment or "",
            evidence_id=evidence_id,
            verified_person_id=str(person_id),
            state_override=state_override,
        )
        qpath = queue_state_path(state_override)
        state = _load_queue_state(qpath)
        entry = dict((state.get("cards") or {}).get(task_id) or {})
        entry.update(
            {
                "status": "ENGINEERING",
                "last_feedback": fb,
                "last_evidence_id": evidence_id,
                "work_item_id": eng.get("work_item_id"),
                "cr_id": eng.get("cr_id"),
            }
        )
        state.setdefault("cards", {})[task_id] = entry
        _save_queue_state(state, qpath)
        effects = {
            "path": "PROBLEM",
            "criterion_satisfied": False,
            "human_commissioned": False,
            "engineering": eng,
            "owner_manages_engineering": False,
            "proven": False,
            "ready": False,
        }
        if emit_retest_on_problem:
            effects["retest"] = emit_retest(
                parent_task_id=task_id,
                work_item_id=eng.get("work_item_id"),
                cr_id=eng.get("cr_id"),
                state_override=state_override,
            )

    row = {
        "evidence_id": evidence_id,
        "task_id": task_id,
        "task": card.get("task"),
        "person_id": person_id,
        "email": email,
        "person_to_test": card.get("person_to_test"),
        "timestamp": stamp,
        "surface": card.get("surface"),
        "route": card.get("route"),
        "business": card.get("business"),
        "capability": card.get("capability"),
        "criterion": card.get("criterion"),
        "feedback": fb,
        "comment": comment or "",
        "files": file_rows,
        "criterion_satisfied": criterion_satisfied,
        "human_commissioned": bool(criterion_satisfied),
        "proven": False,
        "ready": False,
        "staff_ready": False,
        "effects": effects,
        "provenance": {
            "schema_id": SCHEMA_ID,
            "bound": BOUND,
            "source": "owner_commissioning_queue.submit_feedback",
            "immutable": True,
        },
    }
    _append_evidence(row, evidence_path(state_override))

    queue = build_queue(state_override=state_override)
    return {
        "ok": True,
        "evidence": row,
        "effects": effects,
        "queue": {
            "counters": queue.get("counters"),
            "first_task": (queue.get("first_task") or {}).get("id"),
            "active_count": len(queue.get("active_cards") or []),
        },
        "honesty": honesty_flags(),
    }


def build_for_progress(
    *,
    state_override: Path | None = None,
) -> dict[str, Any]:
    """Payload composed into Progress Empire view."""
    q = build_queue(state_override=state_override)
    return {
        "ok": True,
        "title": q["title"],
        "subtitle": q["subtitle"],
        "as_of": q["as_of"],
        "counters": q["counters"],
        "cards": q["cards"],
        "active_cards": q["active_cards"],
        "first_task": q["first_task"],
        "retired_systems": q["retired_systems"],
        "evidence_count": q["evidence_count"],
        "seed_doc": q.get("seed_doc"),
        "deep_link": "/progress#my-commissioning",
        "honesty": honesty_flags(),
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "clickup_retired": True,
        "telegram_retired": True,
        "nas_staff_ready": q.get("nas_staff_ready"),
    }
