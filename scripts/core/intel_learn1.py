#!/usr/bin/env python3
"""INTEL-LEARN-1 — Wolf Intelligence learning board (ties SOP factory).

Decision served: 2026-09-20 PICK CAP-INTEL-05 approve-to-rule learning loop
skeleton, deepened by FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INTEL-LEARN-1
(armed 2026-09-30 after FIN-INTERCO-1 PASS_VERIFIED). Ties to 2026-09-19 PICK
SOP Factory v1 / SOP-FACTORY-1 review gate.

Composes scripts/core/sop_factory.py lesson candidates (demo path) into an
Owner-readable Intel learning board. Does NOT invent a second SOP factory or
a second approve-to-rule ledger. Human review gate required before any
approved rule — reuse POST /api/sop/review-decision. Auto-approve refused.
No fake performance / experiment success metrics.
CAP-INTEL-05 stays SPECIFIED. CR-be51980bd1194448 stays OPEN.
staff_ready=false · human_commissioned=false. Ceiling BUILT only.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import intel_approve_to_rule as _rules
from core import sop_factory as _sop

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

PACK_ID = "INTEL-LEARN-1"
SCHEMA_ID = "wolf.intel-learn-1.v1"
BOUND = "beta-intel-learn-safe"
CAP_ID = "CAP-INTEL-05"
CR_ID = "CR-be51980bd1194448"
SOP_CAP = "CAP-CORE-11"
OWNER_PERSON = "PERS-MATT"
WITA = timezone(timedelta(hours=8))

PERM_READ = _rules.PERM_READ  # intel.rule.read
PERM_SOP_READ = _sop.PERM_READ  # core.sop.read
PERM_SOP_APPROVE = _sop.PERM_APPROVE

DEMO_LABEL = _sop.DEMO_LABEL
REVIEW_API = "/api/sop/review-decision"
CANDIDATES_API = "/api/sop/candidates"
QUEUE_API = "/api/sop/review-queue"
SOP_PAGE = "/core/sop-factory"

PAGE_PATHS = frozenset(
    {
        "/intel/learning",
        "/intel/learning/",
        "/ops/intel-learning",
        "/ops/intel-learning/",
        "/intel-learning",
        "/intel-learning/",
        "/intel-learning.html",
        "/dashboards/intel-learning.html",
    }
)
API_PATH = "/api/intel/learning"

GAPS: tuple[str, ...] = (
    "INTEL-LEARN-1 is a read board over SOP factory lesson candidates.",
    "Human APPROVE via SOP factory review-decision is required before a rule.",
    "Auto-approve is refused. DEMO rows are not live staff adoption.",
    "No fake experiment success or performance metrics are invented.",
    "CAP-INTEL-05 stays SPECIFIED. CR-be51980bd1194448 stays OPEN.",
    "staff_ready=false · human_commissioned=false always on this pack.",
)


class IntelLearn1Error(ValueError):
    """Fail closed. Does not invent an approved rule or fake metrics."""

    def __init__(self, message: str, *, code: str = "invalid"):
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


def permission_for(action: str) -> str:
    act = (action or "").strip().lower()
    if act in {"approve", "review", "review-decision"}:
        return PERM_SOP_APPROVE
    return PERM_READ


def person_may_view(person_id: str | None, *, role_allowed: bool = False) -> bool:
    """Owner always. Staff only when role_allowed already granted (no invent)."""
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


def honesty_flags() -> dict[str, Any]:
    state = ledger_cap_state()
    ceiling = state if state in {"PROVEN", "READY"} else "BUILT"
    sop_h = _sop.honesty_flags()
    rule_h = _rules.honesty_flags()
    return {
        "cap": CAP_ID,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cr_id": CR_ID,
        "sop_cap": SOP_CAP,
        "sop_pack": "SOP-FACTORY-1",
        "append_only": True,
        "human_review_gate": True,
        "auto_approve": False,
        "auto_promote": False,
        "auto_apply": False,
        "rule_execution": False,
        "production_rules": False,
        "fake_performance": False,
        "fake_experiment_success": False,
        "invented_metrics": False,
        "demo_is_live_adoption": False,
        "second_sop_system": False,
        "second_learning_system": False,
        "extends_sop_factory": True,
        "extends_approve_to_rule": True,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "score_changed": False,
        "production": False,
        "alchemist_write": False,
        "anon_fail_closed": True,
        "owner_or_role": True,
        "cr_mutated": False,
        "model_c_write": False,
        "model_c_maturity_raised": False,
        "ledger_maturity": state,
        "maturity": state,
        "maturity_ceiling": ceiling,
        "proven": False,
        "ready": False,
        "cap_intel_05_proven": False,
        "cap_intel_05_ready": False,
        "sop_human_review_gate": sop_h.get("human_review_gate") is True,
        "sop_auto_approve": sop_h.get("auto_approve") is False,
        "sop_staff_ready": sop_h.get("staff_ready") is False,
        "sop_human_commissioned": sop_h.get("human_commissioned") is False,
        "sop_operating_adoption": sop_h.get("operating_adoption") is False,
        "approve_to_rule_auto_promote": rule_h.get("auto_promote") is False,
        "live_catalog_sop_absent": not _sop.DEFAULT_DB.is_file(),
        "demo_db_path": str(_sop.DEMO_DB),
    }


def gaps() -> list[str]:
    return list(GAPS)


def refuse_auto_approve(_body: dict | None = None) -> None:
    raise IntelLearn1Error(
        "Auto-approve is refused. Human APPROVE via SOP factory review-decision "
        "is required before any approved rule.",
        code="auto_approve_refused",
    )


def refuse_promote(_body: dict | None = None) -> None:
    raise IntelLearn1Error(
        "Auto-promote to production rules is refused on INTEL-LEARN-1.",
        code="promote_refused",
    )


def refuse_fake_performance(_body: dict | None = None) -> None:
    raise IntelLearn1Error(
        "Fake performance / experiment success metrics are refused.",
        code="fake_metrics_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise IntelLearn1Error(
        "Inventing PROVEN is refused. CAP-INTEL-05 stays at the ledger state.",
        code="score_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise IntelLearn1Error(
        "Inventing READY is refused. A learning board is not READY.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise IntelLearn1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "auto-approve",
            "autoapprove",
            "auto-approve-rule",
            "skip-review",
        }:
            refuse_auto_approve(payload)
        if token in {"promote", "auto-promote", "production-rule"}:
            refuse_promote(payload)
        if token in {
            "performance",
            "experiment-success",
            "success-rate",
            "accuracy",
            "lift",
            "roi",
            "fake-metric",
        }:
            refuse_fake_performance(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token == "ready":
            refuse_ready(payload)
    raise IntelLearn1Error(
        "INTEL-LEARN-1 board does not accept auto-approve or metric writes. "
        "Use POST /api/sop/review-decision for human APPROVE/DENY.",
        code="write_refused",
    )


def ensure_demo_candidates(
    *,
    person_id: str | None = OWNER_PERSON,
) -> dict[str, Any]:
    """Ensure SOP-FACTORY-1 DEMO fixture exists (tmp path only). Not adoption."""
    if _sop.DEFAULT_DB.is_file():
        return {
            "seeded": False,
            "live_catalog_present": True,
            "demo_label": DEMO_LABEL,
            "db_path": str(_sop.DEFAULT_DB),
        }
    return _sop.seed_demo_vertical_slice(
        person_id=person_id or OWNER_PERSON, db_path=_sop.DEMO_DB
    )


def _candidate_board_row(cand: dict[str, Any]) -> dict[str, Any]:
    demo = bool(cand.get("demo") or cand.get("demo_label"))
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
        "live": False,
        "demo": demo,
        "demo_label": DEMO_LABEL if demo else None,
        "source": "sop_factory",
        "source_pack": "SOP-FACTORY-1",
        "human_review_required": status == "PENDING_REVIEW",
        "auto_approve": False,
        "performance_metric": None,
        "experiment_success": None,
        "fake_metric": False,
    }


def build_board(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Compose Intel learning board from SOP factory lesson candidates."""
    pid = (person_id or "").strip() or None
    if not person_may_view(pid, role_allowed=role_allowed):
        raise IntelLearn1Error(
            "Intel learning board requires Owner or an authorised read role. "
            "Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    seed = ensure_demo_candidates(person_id=OWNER_PERSON)
    path = Path(db_path) if db_path is not None else _sop.runtime_db_path()

    queue = _sop.list_review_queue(pid, role_allowed=role_allowed, db_path=path)
    all_cands = _sop.list_lesson_candidates(
        pid, role_allowed=role_allowed, db_path=path, pending_only=False
    )
    rows = [_candidate_board_row(c) for c in (all_cands.get("candidates") or [])]
    pending = [r for r in rows if r["review_status"] == "PENDING_REVIEW"]
    flags = honesty_flags()

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "cap": CAP_ID,
        "cr_id": CR_ID,
        "closes_toward": [CAP_ID],
        "person_id": pid,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "human_review_gate": True,
        "auto_approve": False,
        "auto_promote": False,
        "fake_performance": False,
        "fake_experiment_success": False,
        "invented_metrics": False,
        "second_sop_system": False,
        "second_learning_system": False,
        "extends_sop_factory": True,
        "cap_intel_05_proven": False,
        "cap_intel_05_ready": False,
        "cap_intel_05_maturity": flags["ledger_maturity"],
        "cap_intel_05_ceiling": flags["maturity_ceiling"],
        "demo_label": DEMO_LABEL,
        "demo_seed": {
            "seeded": seed.get("seeded"),
            "already_present": seed.get("already_present"),
            "db_path": seed.get("db_path") or str(path),
            "live_catalog_present": _sop.DEFAULT_DB.is_file(),
        },
        "db_path": str(path),
        "demo_path": str(_sop.DEMO_DB),
        "live_catalog_sop_absent": not _sop.DEFAULT_DB.is_file(),
        "pending_count": int(queue.get("pending_count") or len(pending)),
        "candidate_count": len(rows),
        "lesson_candidates": rows,
        "review_queue": pending,
        "review_apis": {
            "queue": QUEUE_API,
            "candidates": CANDIDATES_API,
            "review_decision": REVIEW_API,
            "sop_factory_page": SOP_PAGE,
            "note": (
                "Human APPROVE/DENY goes through SOP factory review-decision. "
                "This board does not auto-approve."
            ),
        },
        "approve_to_rule": {
            "policy_api": "/api/intel/learning-policy",
            "skeleton_api": "/api/intel/approve-to-rule",
            "auto_promote": False,
            "rule_execution": False,
        },
        "gaps": gaps(),
        "does_not_claim": [
            "auto_approve",
            "staff_ready",
            "human_commissioned",
            "operating_adoption",
            "CAP-INTEL-05 PROVEN",
            "CAP-INTEL-05 READY",
            "fake_experiment_success",
            "live_staff_adoption",
        ],
        "honesty": flags,
        "sop_honesty": {
            "human_review_gate": True,
            "auto_approve": False,
            "staff_ready": False,
            "human_commissioned": False,
            "operating_adoption": False,
            "demo_is_live_adoption": False,
            "pack": "SOP-FACTORY-1",
            "cap": SOP_CAP,
        },
        "summary": (
            "Wolf Intelligence learning board. Lesson candidates come from the "
            "SOP factory DEMO path. Human review gate required before any "
            "approved rule. Auto-approve off. Not staff_ready. Not commissioned."
        ),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": "BZG-OPS-DESK-1",
    }


def public_payload(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    return build_board(person_id, role_allowed=role_allowed, db_path=db_path)


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "cap": CAP_ID,
        "writes_accepted": False,
        "auto_approve": False,
        "human_review_gate": True,
        "review_decision_api": REVIEW_API,
        "extends": [
            "scripts/core/sop_factory.py",
            "scripts/core/intel_approve_to_rule.py",
            "scripts/core/intel_learning_policy.py",
        ],
        "second_sop_system": False,
        "second_learning_system": False,
        "fake_performance": False,
        "why": (
            "Intel learning board listing SOP factory lesson candidates. "
            "Human APPROVE required. DEMO is not live adoption."
        ),
    }
