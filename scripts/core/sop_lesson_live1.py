#!/usr/bin/env python3
"""SOP-LESSON-LIVE-1 — SOP lesson board live honesty (human review required).

Decision served: 2026-09-19 PICK SOP Factory v1 + 2026-09-20 PICK CAP-INTEL-05
approve-to-rule learning loop, extended by FINAL_WOLF_COMPLETION_MISSION
Phase 2 pack SOP-LESSON-LIVE-1 (armed 2026-09-30 after AMG-OCC-TRUTH-1
PASS_VERIFIED).

Surfaces SOP factory lesson candidates without inventing a live catalog and
without auto-approve. DEMO rows stay DEMO / NOT LIVE STAFF ADOPTION.
Human review reuses POST /api/sop/review-decision (SOP-FACTORY-1).
Composes sop_factory.py + intel_learn1.py — no second SOP / learning system.
CAP-INTEL-05 stays SPECIFIED. staff_ready=false · human_commissioned=false.
Does not auto-chain FIN-TAX-SHELL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import intel_learn1 as _intel
from core import sop_factory as _sop

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

PACK_ID = "SOP-LESSON-LIVE-1"
SCHEMA_ID = "wolf.sop-lesson-live-1.v1"
BOUND = "beta-sop-lesson-live-safe"
CAP_ID = "CAP-INTEL-05"
SOP_CAP = "CAP-CORE-11"
CR_ID = "CR-be51980bd1194448"
SOP_CR = "CR-c4ed4e3fa9f15a40"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))

PERM_READ = _sop.PERM_READ
PERM_APPROVE = _sop.PERM_APPROVE
DEMO_LABEL = _sop.DEMO_LABEL
REVIEW_API = "/api/sop/review-decision"
CANDIDATES_API = "/api/sop/candidates"
QUEUE_API = "/api/sop/review-queue"
SOP_PAGE = "/core/sop-factory"
INTEL_PAGE = "/intel/learning"

PAGE_PATHS = frozenset(
    {
        "/ops/sop-lesson-live",
        "/ops/sop-lesson-live/",
        "/core/sop-lesson-live",
        "/core/sop-lesson-live/",
        "/sop-lesson-live",
        "/sop-lesson-live/",
        "/sop-lesson-live.html",
        "/sop-lesson-live-1",
        "/sop-lesson-live-1/",
        "/sop-lesson-live-1.html",
        "/dashboards/sop-lesson-live.html",
        "/dashboards/sop-lesson-live-1.html",
    }
)
API_PATH = "/api/ops/sop-lesson-live"
API_PATHS = frozenset({API_PATH, "/api/sop/lesson-live"})

CLOSES_TOWARD = ("CAP-INTEL lessons", CAP_ID)
CEILING = "BUILT"
PRESERVED_PACKS = ("SOP-FACTORY-1", "INTEL-LEARN-1")

GAPS: tuple[str, ...] = (
    "SOP-LESSON-LIVE-1 is a live-honesty board over SOP factory lessons.",
    "Live catalog/sop_factory.sqlite is not invented when absent.",
    "DEMO rows are not live staff adoption. Auto-approve is refused.",
    "Human APPROVE/DENY goes through SOP factory review-decision.",
    "CAP-INTEL-05 stays SPECIFIED. staff_ready=false always.",
)


class SopLessonLive1Error(ValueError):
    """Fail closed. Does not invent live lessons or auto-approve."""

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


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"approve", "review", "review-decision"}:
        return PERM_APPROVE
    return PERM_READ


def person_may_view(person_id: str | None, *, role_allowed: bool = False) -> bool:
    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
        return True
    return bool(role_allowed)


def ledger_cap_state() -> str:
    if not LEDGER_JSON.is_file():
        return "SPECIFIED"
    try:
        data = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "SPECIFIED"
    row = data.get(CAP_ID)
    if isinstance(row, list) and row:
        return str(row[0] or "SPECIFIED")
    if isinstance(row, str) and row.strip():
        return row.strip()
    return "SPECIFIED"


def live_catalog_present() -> bool:
    return _sop.DEFAULT_DB.is_file()


def live_catalog_status() -> str:
    return "PRESENT" if live_catalog_present() else "ABSENT"


def honesty_flags() -> dict[str, Any]:
    state = ledger_cap_state()
    ceiling = state if state in {"PROVEN", "READY"} else CEILING
    sop_h = _sop.honesty_flags()
    intel_h = _intel.honesty_flags()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap": CAP_ID,
        "sop_cap": SOP_CAP,
        "cr_id": CR_ID,
        "sop_cr": SOP_CR,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "auto_approve": False,
        "auto_approve_lessons": False,
        "invented_lessons": False,
        "fake_lessons": False,
        "live_catalog_sop_absent": not live_catalog_present(),
        "live_catalog_status": live_catalog_status(),
        "demo_is_live_adoption": False,
        "second_sop_system": False,
        "second_learning_system": False,
        "extends_sop_factory": True,
        "extends_intel_learn1": True,
        "sop_factory1_preserved": True,
        "intel_learn1_preserved": True,
        "proven": False,
        "ready": False,
        "cap_intel_05_proven": False,
        "cap_intel_05_ready": False,
        "ledger_maturity": state,
        "maturity": state,
        "maturity_ceiling": ceiling,
        "ceiling": ceiling,
        "closes_toward": list(CLOSES_TOWARD),
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "anon_fail_closed": True,
        "sop_human_review_gate": sop_h.get("human_review_gate") is True,
        "sop_auto_approve": sop_h.get("auto_approve") is False,
        "intel_auto_approve": intel_h.get("auto_approve") is False,
        "intel_human_review_gate": intel_h.get("human_review_gate") is True,
        "next_pack_for_parent_only": "FIN-TAX-SHELL-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "demo_db_path": str(_sop.DEMO_DB),
    }


def gaps() -> list[str]:
    return list(GAPS)


def refuse_auto_approve(_body: dict | None = None) -> None:
    raise SopLessonLive1Error(
        "Auto-approve is refused. Human APPROVE via SOP factory "
        "review-decision is required.",
        code="auto_approve_refused",
    )


def refuse_invent_lesson(_body: dict | None = None) -> None:
    raise SopLessonLive1Error(
        "Inventing live lessons is refused. Absent catalog is ABSENT, not fake.",
        code="invent_lesson_refused",
    )


def refuse_fake_lesson(_body: dict | None = None) -> None:
    raise SopLessonLive1Error(
        "Fake lessons are refused. DEMO fixtures stay labeled DEMO / NOT LIVE.",
        code="fake_lesson_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise SopLessonLive1Error(
        "Inventing PROVEN is refused. CAP-INTEL-05 stays at the ledger state.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise SopLessonLive1Error(
        "Inventing READY is refused. A lesson honesty board is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise SopLessonLive1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "auto-approve",
            "autoapprove",
            "auto-approve-lessons",
            "skip-review",
            "approve-all",
        }:
            refuse_auto_approve(payload)
        if token in {
            "invent-lesson",
            "fake-lesson",
            "mint-lesson",
            "live-lesson",
            "fake-lessons",
            "invent-lessons",
        }:
            refuse_invent_lesson(payload)
        if token in {"lesson", "lessons", "seed-fake"}:
            refuse_fake_lesson(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
    raise SopLessonLive1Error(
        "SOP-LESSON-LIVE-1 is a read honesty board. Use POST "
        "/api/sop/review-decision for human APPROVE/DENY. "
        "Do not auto-approve or invent lessons.",
        code="write_refused",
    )


def ensure_demo_candidates(
    *,
    person_id: str | None = OWNER_PERSON,
) -> dict[str, Any]:
    """Ensure SOP-FACTORY-1 DEMO fixture (tmp path only). Not live catalog."""
    if live_catalog_present():
        return {
            "seeded": False,
            "live_catalog_present": True,
            "demo_label": DEMO_LABEL,
            "db_path": str(_sop.DEFAULT_DB),
        }
    return _sop.seed_demo_vertical_slice(
        person_id=person_id or OWNER_PERSON, db_path=_sop.DEMO_DB
    )


def _row(cand: dict[str, Any], *, live: bool) -> dict[str, Any]:
    demo = bool(cand.get("demo") or cand.get("demo_label")) and not live
    status = cand.get("review_status") or "PENDING_REVIEW"
    return {
        "candidate_id": cand.get("candidate_id"),
        "sop_id": cand.get("sop_id"),
        "version_id": cand.get("version_id"),
        "learning_id": cand.get("learning_id"),
        "title": cand.get("title"),
        "lesson_note": cand.get("lesson_note"),
        "evidence_note": cand.get("evidence_note"),
        "review_status": status,
        "approved_rule": bool(cand.get("approved_rule")),
        "live": False if demo else bool(live),
        "demo": demo,
        "demo_label": DEMO_LABEL if demo else None,
        "source": "sop_factory",
        "source_pack": "SOP-FACTORY-1",
        "human_review_required": status == "PENDING_REVIEW",
        "auto_approve": False,
        "invented": False,
        "fake_lesson": False,
        "performance_metric": None,
        "fake_metric": False,
    }


def _list_from(db_path: Path, person_id: str, *, role_allowed: bool) -> list[dict[str, Any]]:
    if not Path(db_path).is_file():
        return []
    listed = _sop.list_lesson_candidates(
        person_id,
        role_allowed=role_allowed,
        db_path=db_path,
        pending_only=False,
    )
    return list(listed.get("candidates") or [])


def build_board(
    person_id: str | None,
    *,
    role_allowed: bool = False,
) -> dict[str, Any]:
    pid = (person_id or "").strip() or None
    if not person_may_view(pid, role_allowed=role_allowed):
        raise SopLessonLive1Error(
            "SOP lesson live board requires Owner or an authorised "
            "core.sop.read role. Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    seed = ensure_demo_candidates(person_id=OWNER_PERSON)
    live_present = live_catalog_present()
    live_status = live_catalog_status()

    live_raw = (
        _list_from(_sop.DEFAULT_DB, pid or OWNER_PERSON, role_allowed=role_allowed)
        if live_present
        else []
    )
    demo_raw = _list_from(
        _sop.DEMO_DB, pid or OWNER_PERSON, role_allowed=role_allowed
    )
    live_rows = [_row(c, live=True) for c in live_raw]
    # Live catalog absent ⇒ never paint invented live rows.
    if not live_present:
        live_rows = []
    demo_rows = [_row(c, live=False) for c in demo_raw]
    pending = [
        r
        for r in (demo_rows + live_rows)
        if r.get("review_status") == "PENDING_REVIEW"
    ]
    flags = honesty_flags()

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "cap": CAP_ID,
        "sop_cap": SOP_CAP,
        "cr_id": CR_ID,
        "closes_toward": list(CLOSES_TOWARD),
        "person_id": pid,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "auto_approve": False,
        "auto_approve_lessons": False,
        "invented_lessons": False,
        "fake_lessons": False,
        "second_sop_system": False,
        "second_learning_system": False,
        "extends_sop_factory": True,
        "extends_intel_learn1": True,
        "sop_factory1_preserved": True,
        "intel_learn1_preserved": True,
        "cap_intel_05_proven": False,
        "cap_intel_05_ready": False,
        "cap_intel_05_maturity": flags["ledger_maturity"],
        "cap_intel_05_ceiling": flags["maturity_ceiling"],
        "demo_label": DEMO_LABEL,
        "demo_seed": {
            "seeded": seed.get("seeded"),
            "already_present": seed.get("already_present"),
            "db_path": seed.get("db_path") or str(_sop.DEMO_DB),
            "live_catalog_present": live_present,
        },
        "live_catalog_path": str(_sop.DEFAULT_DB),
        "live_catalog_present": live_present,
        "live_catalog_sop_absent": not live_present,
        "live_catalog_status": live_status,
        "demo_path": str(_sop.DEMO_DB),
        "live_lesson_count": len(live_rows),
        "demo_lesson_count": len(demo_rows),
        "pending_count": len(pending),
        "candidate_count": len(demo_rows) + len(live_rows),
        "live_lessons": live_rows,
        "demo_lessons": demo_rows,
        "lesson_candidates": demo_rows + live_rows,
        "review_queue": pending,
        "review_apis": {
            "queue": QUEUE_API,
            "candidates": CANDIDATES_API,
            "review_decision": REVIEW_API,
            "sop_factory_page": SOP_PAGE,
            "intel_learning_page": INTEL_PAGE,
            "note": (
                "Human APPROVE/DENY goes through SOP factory review-decision. "
                "This board does not auto-approve or invent live lessons."
            ),
        },
        "gaps": gaps(),
        "does_not_claim": [
            "auto_approve",
            "invented_lessons",
            "live_staff_adoption",
            "staff_ready",
            "human_commissioned",
            "CAP-INTEL-05 PROVEN",
            "CAP-INTEL-05 READY",
        ],
        "honesty": flags,
        "summary": (
            "SOP lesson board live honesty. Factory DEMO lessons are labeled "
            "DEMO / NOT LIVE STAFF ADOPTION. Live catalog is ABSENT unless "
            "the file exists — never invented. Human review required. "
            "Auto-approve off. Not staff_ready. Not commissioned."
        ),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "FIN-TAX-SHELL-1",
    }


def public_payload(
    person_id: str | None,
    *,
    role_allowed: bool = False,
) -> dict[str, Any]:
    return build_board(person_id, role_allowed=role_allowed)


def no_invented_live_lessons(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else None
    if pack is None:
        return True
    if pack.get("invented_lessons") is not False:
        return False
    if pack.get("fake_lessons") is not False:
        return False
    if pack.get("live_catalog_sop_absent") is True:
        if int(pack.get("live_lesson_count") or 0) != 0:
            return False
        if pack.get("live_lessons"):
            return False
        if pack.get("live_catalog_status") != "ABSENT":
            return False
    for row in pack.get("live_lessons") or []:
        if row.get("invented") is True:
            return False
    for row in pack.get("demo_lessons") or []:
        if row.get("live") is True:
            return False
        if row.get("invented") is True:
            return False
    return True


def human_review_required(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else None
    if pack is None:
        return True
    return (
        pack.get("human_review_gate") is True
        and pack.get("auto_approve") is False
        and pack.get("auto_approve_lessons") is False
    )


def all_candidates_human_gated(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if not human_review_required(pack):
        return False
    for row in pack.get("lesson_candidates") or []:
        if row.get("auto_approve") is True:
            return False
        if row.get("invented") is True or row.get("fake_lesson") is True:
            return False
        if row.get("review_status") == "PENDING_REVIEW" and not row.get(
            "human_review_required"
        ):
            return False
    return True


def no_invented_lessons(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    return no_invented_live_lessons(pack)


def sop_factory1_preserved() -> dict[str, Any]:
    h = _sop.honesty_flags()
    ok = (
        h.get("human_review_gate") is True
        and h.get("auto_approve") is False
        and h.get("staff_ready") is False
        and h.get("human_commissioned") is False
    )
    return {
        "ok": ok,
        "pack": "SOP-FACTORY-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "why": "SOP factory human review gate + no auto-approve held.",
    }


def intel_learn1_preserved() -> dict[str, Any]:
    h = _intel.honesty_flags()
    ok = (
        h.get("auto_approve") is False
        and h.get("human_review_gate") is True
        and h.get("second_sop_system") is False
        and h.get("staff_ready") is False
        and h.get("fake_performance") is False
    )
    return {
        "ok": ok,
        "pack": "INTEL-LEARN-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "why": "Intel learning board still requires human review; no second SOP system.",
    }
