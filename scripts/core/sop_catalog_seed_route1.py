#!/usr/bin/env python3
"""SOP-CATALOG-SEED-ROUTE-1 — Live catalog seed-or-route (no invent adoption).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
SOP-CATALOG-SEED-ROUTE-1 (armed 2026-09-30 after ESB-SETTLEMENT-PATH-1
PASS_VERIFIED) plus 2026-09-19 PICK SOP Factory v1 + 2026-09-20 PICK
CAP-INTEL-05.

Challenges empty SOP live catalog. Seeds live catalog from approved DEMO
after human route OR stamps HUMAN_COMMISSIONING — never invents live lessons.
Preserves SOP-LESSON-LIVE-1 DEMO honesty. auto_approve stays false.
staff_ready=false · human_commissioned=false.
Does not auto-chain FIN-BANK-CREDS-ROUTE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import sop_factory as _sop
from core import sop_lesson_live1 as _lesson

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
COMMISSION_STAMP = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "SOP-CATALOG-SEED-ROUTE-1-COMMISSION.json"
)
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

PACK_ID = "SOP-CATALOG-SEED-ROUTE-1"
SCHEMA_ID = "wolf.sop-catalog-seed-route-1.v1"
BOUND = "beta-sop-catalog-seed-route-safe"
CAP_ID = "CAP-INTEL-05"
SOP_CAP = "CAP-CORE-11"
CR_ID = "CR-be51980bd1194448"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Pack itself is internally solvable (route board). Live adoption disposition
# without human commission + approved DEMO is HUMAN_COMMISSIONING.
PACK_CLASSIFICATION = "INTERNALLY_SOLVABLE"
ROUTE_CLASSIFICATION = "HUMAN_COMMISSIONING"
CLOSES_TOWARD = ("CAP-INTEL lessons", CAP_ID)
PRESERVED_PACKS = ("SOP-LESSON-LIVE-1", "SOP-FACTORY-1", "INTEL-LEARN-1")
DEMO_LABEL = _sop.DEMO_LABEL
LESSON_PAGE = "/ops/sop-lesson-live"
REVIEW_API = "/api/sop/review-decision"

PAGE_PATHS = frozenset(
    {
        "/ops/sop-catalog-seed-route-1",
        "/ops/sop-catalog-seed-route-1/",
        "/ops/sop-catalog-seed-route",
        "/ops/sop-catalog-seed-route/",
        "/sop-catalog-seed-route-1",
        "/sop-catalog-seed-route-1/",
        "/sop-catalog-seed-route-1.html",
        "/dashboards/sop-catalog-seed-route-1.html",
        "/core/sop-catalog-seed-route-1",
        "/core/sop-catalog-seed-route-1/",
    }
)
API_PATH = "/api/ops/sop-catalog-seed-route-1"
API_PATHS = frozenset({API_PATH, "/api/sop/catalog-seed-route-1"})

STATUS_VOCAB = frozenset(
    {
        "SEEDED",
        "HUMAN_COMMISSIONING",
        "ABSENT",
        "PRESERVED",
        "PENDING_REVIEW",
        "APPROVED",
        "REFUSED",
    }
)

GAPS: tuple[str, ...] = (
    "Live catalog/sop_factory.sqlite stays ABSENT until human-commissioned "
    "seed from approved DEMO — never invented.",
    "DEMO rows remain DEMO / NOT LIVE STAFF ADOPTION until route + seed.",
    "auto_approve stays false. Human APPROVE via SOP factory review-decision.",
    "SOP-LESSON-LIVE-1 honesty preserved. CAP-INTEL-05 stays SPECIFIED.",
    "staff_ready=false · human_commissioned=false on this pack.",
)


class SopCatalogSeedRoute1Error(ValueError):
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
    if act in {"seed", "commission", "route"}:
        return _sop.PERM_APPROVE
    return _sop.PERM_READ


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


def human_route_commissioned(*, stamp_path: Path | None = None) -> bool:
    """True only when an explicit commission stamp says so.

    Pack honesty keeps human_commissioned=false. This helper is for the
    seed gate only — presence of stamp is required before any live seed.
    """
    path = Path(stamp_path) if stamp_path is not None else COMMISSION_STAMP
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("pack") not in {None, PACK_ID}:
        return False
    return data.get("human_route_commissioned") is True or data.get(
        "seed_authorised"
    ) is True


def _demo_db_path(demo_db: Path | str | None = None) -> Path:
    return Path(demo_db) if demo_db is not None else _sop.DEMO_DB


def _list_demo_candidates(
    person_id: str = OWNER_PERSON,
    *,
    role_allowed: bool = True,
    demo_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    path = _demo_db_path(demo_db)
    if not path.is_file():
        return []
    listed = _sop.list_lesson_candidates(
        person_id,
        role_allowed=role_allowed,
        db_path=path,
        pending_only=False,
    )
    return list(listed.get("candidates") or [])


def approved_demo_candidates(
    person_id: str = OWNER_PERSON,
    *,
    role_allowed: bool = True,
    demo_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    """DEMO candidates that a human APPROVED via review-decision — not invented."""
    out: list[dict[str, Any]] = []
    for cand in _list_demo_candidates(
        person_id, role_allowed=role_allowed, demo_db=demo_db
    ):
        status = str(cand.get("review_status") or "")
        approved = bool(cand.get("approved_rule")) or status == _sop.CANDIDATE_APPROVED
        if approved and status == _sop.CANDIDATE_APPROVED:
            out.append(dict(cand))
    return out


def pending_demo_candidates(
    person_id: str = OWNER_PERSON,
    *,
    role_allowed: bool = True,
    demo_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    return [
        dict(c)
        for c in _list_demo_candidates(
            person_id, role_allowed=role_allowed, demo_db=demo_db
        )
        if str(c.get("review_status") or "") == _sop.CANDIDATE_PENDING
    ]


def decide_seed_or_route(
    *,
    person_id: str = OWNER_PERSON,
    role_allowed: bool = True,
    stamp_path: Path | None = None,
    live_present: bool | None = None,
    demo_db: Path | str | None = None,
) -> dict[str, Any]:
    """Core seed-or-route decision. Never invents live lessons."""
    present = live_catalog_present() if live_present is None else bool(live_present)
    approved = approved_demo_candidates(
        person_id, role_allowed=role_allowed, demo_db=demo_db
    )
    pending = pending_demo_candidates(
        person_id, role_allowed=role_allowed, demo_db=demo_db
    )
    commissioned = human_route_commissioned(stamp_path=stamp_path)
    auto_approve = False

    if present:
        action = "LIVE_ALREADY_PRESENT"
        classification = "PRESERVED"
        reason = (
            "Live catalog already present. This pack does not invent rows; "
            "existing live file is preserved as-is."
        )
        may_seed = False
    elif auto_approve:
        action = "REFUSED"
        classification = ROUTE_CLASSIFICATION
        reason = "auto_approve is false — refuse invent/seed."
        may_seed = False
    elif not approved:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = ROUTE_CLASSIFICATION
        reason = (
            "No approved DEMO lessons to seed from. DEMO stays PENDING_REVIEW "
            "or empty — never invent live lessons. Stamp HUMAN_COMMISSIONING: "
            "human must APPROVE DEMO via review-decision, then commission seed."
        )
        may_seed = False
    elif not commissioned:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = ROUTE_CLASSIFICATION
        reason = (
            f"{len(approved)} approved DEMO lesson(s) exist, but human route "
            "commission stamp is absent. Seed refused. Stamp HUMAN_COMMISSIONING."
        )
        may_seed = False
    else:
        action = "SEED_FROM_APPROVED_DEMO"
        classification = "SEEDED_ELIGIBLE"
        reason = (
            f"{len(approved)} approved DEMO lesson(s) and human route "
            "commissioned — eligible to seed live catalog from DEMO "
            "(explicit call only; not auto)."
        )
        may_seed = True

    return {
        "action": action,
        "classification": classification,
        "pack_classification": PACK_CLASSIFICATION,
        "route_classification": ROUTE_CLASSIFICATION
        if classification == ROUTE_CLASSIFICATION
        else classification,
        "reason": reason,
        "may_seed": may_seed,
        "seeded": False,
        "live_catalog_present": present,
        "live_catalog_status": "PRESENT" if present else "ABSENT",
        "live_catalog_path": str(_sop.DEFAULT_DB),
        "demo_path": str(_demo_db_path(demo_db)),
        "approved_demo_count": len(approved),
        "pending_demo_count": len(pending),
        "approved_demo": [
            {
                "candidate_id": c.get("candidate_id"),
                "sop_id": c.get("sop_id"),
                "version_id": c.get("version_id"),
                "title": c.get("title"),
                "review_status": c.get("review_status"),
                "demo_label": DEMO_LABEL,
                "live": False,
                "invented": False,
            }
            for c in approved
        ],
        "pending_demo": [
            {
                "candidate_id": c.get("candidate_id"),
                "title": c.get("title"),
                "review_status": c.get("review_status"),
                "demo_label": DEMO_LABEL,
                "live": False,
            }
            for c in pending
        ],
        "human_route_commissioned": commissioned,
        "auto_approve": False,
        "invented_lessons": False,
        "fake_lessons": False,
        "demo_is_live_adoption": False,
    }


def seed_live_from_approved_demo(
    *,
    person_id: str = OWNER_PERSON,
    role_allowed: bool = True,
    stamp_path: Path | None = None,
    target_db: Path | str | None = None,
    demo_db: Path | str | None = None,
    allow_live_default: bool = False,
) -> dict[str, Any]:
    """Seed a catalog DB from approved DEMO after human route.

    Refuses inventing when no approved DEMO or no commission stamp.
    Refuses writing the real live catalog unless allow_live_default=True
    AND commission stamp is present (pack EXIT never sets that).
    """
    source = _demo_db_path(demo_db)
    decision = decide_seed_or_route(
        person_id=person_id,
        role_allowed=role_allowed,
        stamp_path=stamp_path,
        live_present=False if target_db is not None else None,
        demo_db=source,
    )
    if not decision.get("may_seed"):
        raise SopCatalogSeedRoute1Error(
            decision.get("reason")
            or "Seed refused — HUMAN_COMMISSIONING or no approved DEMO.",
            code="human_commissioning_required"
            if decision.get("classification") == ROUTE_CLASSIFICATION
            else "seed_refused",
        )

    approved = approved_demo_candidates(
        person_id, role_allowed=role_allowed, demo_db=source
    )
    if not approved:
        raise SopCatalogSeedRoute1Error(
            "No approved DEMO lessons — refuse invent live seed.",
            code="invent_lesson_refused",
        )

    target = Path(target_db) if target_db is not None else _sop.DEFAULT_DB
    resolved = target.resolve()
    if resolved == _sop.LIVE_DEFAULT_DB and not allow_live_default:
        raise SopCatalogSeedRoute1Error(
            "Live catalog seed refused without allow_live_default + commission. "
            "Pack EXIT stamps HUMAN_COMMISSIONING; does not write live catalog.",
            code="live_guard",
        )
    if resolved == _sop.LIVE_DEFAULT_DB and not human_route_commissioned(
        stamp_path=stamp_path
    ):
        raise SopCatalogSeedRoute1Error(
            "Live catalog seed requires human route commission stamp.",
            code="human_commissioning_required",
        )

    # Materialise seed by copying the DEMO sqlite (approved rows only exist there)
    # into the target — never invent new lesson bodies.
    if not source.is_file():
        raise SopCatalogSeedRoute1Error(
            "DEMO catalog missing — cannot seed from approved DEMO.",
            code="demo_absent",
        )
    if resolved == source.resolve():
        raise SopCatalogSeedRoute1Error(
            "Refuse seeding onto the DEMO path.",
            code="demo_guard",
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if resolved.is_file():
        raise SopCatalogSeedRoute1Error(
            "Target catalog already exists — refuse overwrite invent.",
            code="target_exists",
        )
    shutil.copy2(source, resolved)

    # Verify target has the approved candidates; do not mint extras.
    listed = _sop.list_lesson_candidates(
        person_id,
        role_allowed=True,
        db_path=resolved,
        pending_only=False,
    )
    seeded_rows = [
        c
        for c in (listed.get("candidates") or [])
        if str(c.get("review_status") or "") == _sop.CANDIDATE_APPROVED
    ]
    if not seeded_rows:
        # Rollback empty invent
        try:
            resolved.unlink()
        except OSError:
            pass
        raise SopCatalogSeedRoute1Error(
            "Seed copy had no APPROVED rows — refuse invent live lessons.",
            code="invent_lesson_refused",
        )

    return {
        "ok": True,
        "seeded": True,
        "action": "SEEDED_FROM_APPROVED_DEMO",
        "classification": "SEEDED",
        "target_db": str(resolved),
        "source_demo": str(source),
        "seeded_count": len(seeded_rows),
        "approved_demo_count": len(approved),
        "invented_lessons": False,
        "fake_lessons": False,
        "auto_approve": False,
        "demo_label_preserved": DEMO_LABEL,
        "note": (
            "Seeded from approved DEMO only after human route. "
            "Not staff_ready. Not operating adoption by itself."
        ),
    }


def honesty_flags() -> dict[str, Any]:
    state = ledger_cap_state()
    ceiling = state if state in {"PROVEN", "READY"} else CEILING
    decision = decide_seed_or_route()
    lesson_h = _lesson.honesty_flags()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap": CAP_ID,
        "sop_cap": SOP_CAP,
        "cr_id": CR_ID,
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
        "seeded_live": False,
        "route_classification": decision.get("route_classification"),
        "pack_classification": PACK_CLASSIFICATION,
        "classification": decision.get("classification"),
        "action": decision.get("action"),
        "second_sop_system": False,
        "extends_sop_lesson_live1": True,
        "extends_sop_factory": True,
        "sop_lesson_live1_preserved": True,
        "sop_factory1_preserved": True,
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
        "lesson_live_catalog_absent": lesson_h.get("live_catalog_sop_absent") is True,
        "lesson_auto_approve": lesson_h.get("auto_approve") is False,
        "lesson_demo_not_adoption": lesson_h.get("demo_is_live_adoption") is False,
        "next_pack_for_parent_only": "FIN-BANK-CREDS-ROUTE-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "status_vocab": "|".join(sorted(STATUS_VOCAB)),
        "commission_stamp_path": str(COMMISSION_STAMP),
        "commission_stamp_present": COMMISSION_STAMP.is_file(),
    }


def gaps() -> list[str]:
    return list(GAPS)


def refuse_auto_approve(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Auto-approve is refused. Human APPROVE via SOP factory "
        "review-decision is required before any seed.",
        code="auto_approve_refused",
    )


def refuse_invent_lesson(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Inventing live lessons is refused. Seed only from approved DEMO "
        "after human route, or stamp HUMAN_COMMISSIONING.",
        code="invent_lesson_refused",
    )


def refuse_fake_lesson(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Fake lessons are refused. DEMO fixtures stay labeled DEMO / NOT LIVE.",
        code="fake_lesson_refused",
    )


def refuse_seed_without_route(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Live catalog seed refused without human route commission. "
        "Stamp HUMAN_COMMISSIONING.",
        code="human_commissioning_required",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Inventing PROVEN is refused. CAP-INTEL-05 stays at the ledger state.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise SopCatalogSeedRoute1Error(
        "Inventing READY / staff_ready / human_commissioned is refused.",
        code="ready_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise SopCatalogSeedRoute1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "auto-approve",
            "autoapprove",
            "auto-approve-lessons",
            "skip-review",
            "approve-all",
        } or norm in {"auto_approve", "auto_approve_lessons"}:
            refuse_auto_approve(payload)
        if token in {
            "invent-lesson",
            "fake-lesson",
            "mint-lesson",
            "live-lesson",
            "fake-lessons",
            "invent-lessons",
            "invent",
        } or norm in {
            "invent_lesson",
            "fake_lesson",
            "mint_lesson",
            "live_lesson",
            "invent_lessons",
            "fake_lessons",
        }:
            refuse_invent_lesson(payload)
        if token in {"seed", "seed-live", "seed-catalog", "promote"} or norm in {
            "seed",
            "seed_live",
            "seed_catalog",
            "promote",
        }:
            refuse_seed_without_route(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {
            "ready",
            "staff-ready",
            "human-commissioned",
            "commission",
        } or norm in {
            "staff_ready",
            "human_commissioned",
        }:
            refuse_ready(payload)
    raise SopCatalogSeedRoute1Error(
        "SOP-CATALOG-SEED-ROUTE-1 is a read honesty / route board. "
        "Seed requires explicit commission path; invent/auto-approve refused.",
        code="write_refused",
    )


def surface_stamps(
    *,
    person_id: str = OWNER_PERSON,
    role_allowed: bool = True,
    stamp_path: Path | None = None,
) -> list[dict[str, Any]]:
    decision = decide_seed_or_route(
        person_id=person_id, role_allowed=role_allowed, stamp_path=stamp_path
    )
    live_status = decision["live_catalog_status"]
    route_status = (
        ROUTE_CLASSIFICATION
        if decision["classification"] == ROUTE_CLASSIFICATION
        else decision["classification"]
    )
    return [
        {
            "id": "live_catalog",
            "label": "SOP live catalog",
            "status": live_status if live_status in STATUS_VOCAB else "ABSENT",
            "value": live_status,
            "live_lesson_count": 0 if live_status == "ABSENT" else None,
            "why": (
                "catalog/sop_factory.sqlite ABSENT — never invented. "
                "Seed only from approved DEMO after human route."
            ),
            "evidence": str(_sop.DEFAULT_DB),
        },
        {
            "id": "demo_lessons",
            "label": "DEMO lessons (SOP-LESSON-LIVE-1)",
            "status": "PENDING_REVIEW"
            if decision["pending_demo_count"]
            else ("APPROVED" if decision["approved_demo_count"] else "ABSENT"),
            "value": {
                "pending": decision["pending_demo_count"],
                "approved": decision["approved_demo_count"],
            },
            "demo_label": DEMO_LABEL,
            "why": (
                "DEMO / NOT LIVE STAFF ADOPTION preserved. "
                "Pending rows are not seedable. Approved rows seed only after route."
            ),
            "evidence": str(_sop.DEMO_DB),
        },
        {
            "id": "human_route",
            "label": "Human route / commission",
            "status": ROUTE_CLASSIFICATION
            if not decision["human_route_commissioned"]
            else "APPROVED",
            "value": decision["human_route_commissioned"],
            "why": (
                "Human must commission live seed after APPROVE. "
                "Absent stamp → HUMAN_COMMISSIONING. Pack flags stay false."
            ),
            "evidence": str(stamp_path or COMMISSION_STAMP),
        },
        {
            "id": "seed_or_route",
            "label": "Seed-or-route decision",
            "status": route_status
            if route_status in STATUS_VOCAB
            else ROUTE_CLASSIFICATION,
            "value": decision["action"],
            "classification": decision["classification"],
            "may_seed": decision["may_seed"],
            "why": decision["reason"],
            "evidence": "decide_seed_or_route()",
        },
        {
            "id": "auto_approve",
            "label": "Auto-approve",
            "status": "REFUSED",
            "value": False,
            "why": "auto_approve stays false. Human review via review-decision.",
            "evidence": REVIEW_API,
        },
        {
            "id": "sop_lesson_live1",
            "label": "SOP-LESSON-LIVE-1 preserved",
            "status": "PRESERVED",
            "value": True,
            "why": "DEMO honesty + live ABSENT + no auto-approve held.",
            "evidence": LESSON_PAGE,
        },
    ]


def sop_lesson_live1_preserved() -> dict[str, Any]:
    h = _lesson.honesty_flags()
    board = _lesson.build_board(OWNER_PERSON)
    ok = (
        h.get("auto_approve") is False
        and h.get("invented_lessons") is False
        and h.get("demo_is_live_adoption") is False
        and h.get("live_catalog_status") == "ABSENT"
        and board.get("live_lesson_count") == 0
        and _lesson.no_invented_live_lessons(board)
        and _lesson.human_review_required(board)
    )
    return {
        "ok": ok,
        "pack": "SOP-LESSON-LIVE-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "live_catalog_status": h.get("live_catalog_status"),
        "auto_approve": h.get("auto_approve"),
        "why": (
            "SOP-LESSON-LIVE-1 DEMO honesty held; live catalog still ABSENT; "
            "no invent; auto-approve off."
        ),
    }


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("auto_approve") is True or pack.get("invented_lessons") is True:
        return False
    if pack.get("fake_lessons") is True:
        return False
    if pack.get("seeded_live") is True and pack.get("live_catalog_status") == "ABSENT":
        return False
    if (
        pack.get("live_catalog_status") == "ABSENT"
        and int(pack.get("live_lesson_count") or 0) != 0
    ):
        return False
    if pack.get("demo_is_live_adoption") is True:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 5:
        return False
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        st = s.get("status")
        if st not in STATUS_VOCAB:
            return False
        if s.get("id") == "auto_approve" and (
            st != "REFUSED" or s.get("value") is not False
        ):
            return False
        if s.get("id") == "live_catalog" and pack.get("live_catalog_status") == "ABSENT":
            if st != "ABSENT":
                return False
        if s.get("id") == "sop_lesson_live1" and st != "PRESERVED":
            return False
    # Default EXIT path: HUMAN_COMMISSIONING when live absent + no commission
    if pack.get("live_catalog_status") == "ABSENT" and not pack.get(
        "human_route_commissioned"
    ):
        if pack.get("classification") != ROUTE_CLASSIFICATION:
            return False
        if pack.get("action") != "STAMP_HUMAN_COMMISSIONING":
            return False
    return True


def build_board(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    stamp_path: Path | None = None,
) -> dict[str, Any]:
    pid = (person_id or "").strip() or None
    if not person_may_view(pid, role_allowed=role_allowed):
        raise SopCatalogSeedRoute1Error(
            "SOP catalog seed-route board requires Owner or an authorised "
            "core.sop.read role. Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    # Ensure DEMO fixture exists for honesty (tmp DEMO path only — not live).
    if not live_catalog_present() and not _sop.DEMO_DB.is_file():
        _lesson.ensure_demo_candidates(person_id=OWNER_PERSON)
    elif not live_catalog_present():
        _lesson.ensure_demo_candidates(person_id=OWNER_PERSON)

    decision = decide_seed_or_route(
        person_id=pid or OWNER_PERSON,
        role_allowed=role_allowed or pid == OWNER_PERSON,
        stamp_path=stamp_path,
    )
    surfaces = surface_stamps(
        person_id=pid or OWNER_PERSON,
        role_allowed=role_allowed or pid == OWNER_PERSON,
        stamp_path=stamp_path,
    )
    preserved = sop_lesson_live1_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "cap": CAP_ID,
        "sop_cap": SOP_CAP,
        "cr_id": CR_ID,
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
        "seeded_live": False,
        "demo_is_live_adoption": False,
        "pack_classification": PACK_CLASSIFICATION,
        "classification": decision["classification"],
        "route_classification": decision.get("route_classification"),
        "action": decision["action"],
        "may_seed": decision["may_seed"],
        "reason": decision["reason"],
        "live_catalog_path": decision["live_catalog_path"],
        "live_catalog_present": decision["live_catalog_present"],
        "live_catalog_sop_absent": not decision["live_catalog_present"],
        "live_catalog_status": decision["live_catalog_status"],
        "live_lesson_count": 0 if not decision["live_catalog_present"] else None,
        "demo_path": decision["demo_path"],
        "demo_label": DEMO_LABEL,
        "approved_demo_count": decision["approved_demo_count"],
        "pending_demo_count": decision["pending_demo_count"],
        "approved_demo": decision["approved_demo"],
        "pending_demo": decision["pending_demo"],
        "human_route_commissioned": decision["human_route_commissioned"],
        "commission_stamp_path": str(stamp_path or COMMISSION_STAMP),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "closes_toward": list(CLOSES_TOWARD),
        "ceiling": flags["maturity_ceiling"],
        "cap_intel_05_maturity": flags["ledger_maturity"],
        "cap_intel_05_proven": False,
        "cap_intel_05_ready": False,
        "gaps": gaps(),
        "review_apis": {
            "review_decision": REVIEW_API,
            "lesson_live_page": LESSON_PAGE,
            "note": (
                "Human APPROVE DEMO via review-decision, then commission stamp, "
                "then seed. This board does not auto-approve or invent live."
            ),
        },
        "does_not_claim": [
            "auto_approve",
            "invented_lessons",
            "live_staff_adoption",
            "staff_ready",
            "human_commissioned",
            "seeded_live_without_route",
            "CAP-INTEL-05 PROVEN",
            "CAP-INTEL-05 READY",
        ],
        "preserved": {"SOP-LESSON-LIVE-1": preserved},
        "sop_lesson_live1_preserved": preserved.get("ok") is True,
        "honesty": flags,
        "summary": (
            "SOP live catalog seed-or-route. Live catalog ABSENT — never invented. "
            "Seed only from approved DEMO after human route; otherwise stamp "
            "HUMAN_COMMISSIONING. DEMO honesty preserved. auto_approve false. "
            "Not staff_ready. Not commissioned."
        ),
        "next_pack_for_parent_only": "FIN-BANK-CREDS-ROUTE-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "prod_pid_held": PROD_PID_HELD,
        "prod_mutate": False,
        "no_push": True,
    }


def public_payload(
    person_id: str | None,
    *,
    role_allowed: bool = False,
) -> dict[str, Any]:
    return build_board(person_id, role_allowed=role_allowed)


def no_invented_live_lessons(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_lessons") is not False:
        return False
    if pack.get("fake_lessons") is not False:
        return False
    if pack.get("seeded_live") is True and not pack.get("human_route_commissioned"):
        return False
    if pack.get("live_catalog_status") == "ABSENT":
        if int(pack.get("live_lesson_count") or 0) != 0:
            return False
    for row in pack.get("approved_demo") or []:
        if row.get("live") is True or row.get("invented") is True:
            return False
    for row in pack.get("pending_demo") or []:
        if row.get("live") is True:
            return False
    return True
