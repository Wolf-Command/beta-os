#!/usr/bin/env python3
"""Core harden / commissioning honesty pack v1 — Beta :8788 only.

Decision served: 2026-09-21 compressed sprint Track F
(docs/deliveries/GROK-PLAN-SPRINT-TRACK-F-CORE-HARDEN-PACK-2026-09-21.md),
under the 2026-09-19 owner release keep_building_without_matt.

One Owner desk. It reads commissioning claims, the Model E adoption file,
and factory mission files. It does not mark COMMISSIONED or ADOPTED, does
not write Cloudflare Access, and does not start a parked lane.

Bound beta-core-safe. Owner only. No money, bank, payment, Zayen, HR,
payroll, tax, or trading.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
ADOPTION_JSON = BETA_ROOT / "state" / "model-e-au-discovery.json"
DEVI_CLAIM_JSON = (
    BETA_ROOT / "state" / "build-claims" / "devi-uma-today-commissioning-2026-09-19.json"
)
RELEASE_JSON = BETA_ROOT / "state" / "build-claims" / "owner-autonomous-release-2026-09-19.json"
CLAIMS_JSON = BETA_ROOT / "state" / "build-claims" / "2026-09-21.json"
OVERLAY_JSON = BETA_ROOT / "state" / "progress" / "v1_overlay.json"
GRAPH_MD = (
    BETA_ROOT / "docs" / "deliveries" / "COMPRESSED-SPRINT-DEPENDENCY-GRAPH-2026-09-21.md"
)
CF_REVIEW = "docs/deliveries/GROK-REVIEW-DEVI-UMA-COMMISSION-AUTH-275d1c7-2026-09-19.md"
BF = BETA_ROOT / "state" / "build-factory"

BOUND = "beta-core-safe"
SCHEMA_ID = "wolf.core-harden-pack.v1"
OWNER = "PERS-MATT"
SLICE = "core_harden_pack_v1"
AU_UMA = "AU-BZG-03-UMA"
MISSION_EXPECTED = "compressed-sprint-20260921"

HABITAT_AUS = (
    "AU-GGV-02-HABITAT",
    "AU-GGV-01-HABITAT",
    "AU-GGV-05-HABITAT",
    "AU-CRM-01-HABITAT",
    "AU-INTG-05-HABITAT",
    "AU-CORE-07-HABITAT-PUBLISH",
    "AU-CORE-06-HABITAT-PUBLISH",
    "AU-CORE-09-HABITAT-PUBLISH",
)

SPRINT_CLAIM_IDS = (
    "bf-bzg-ops-pack-20260921",
    "bf-ggv-ops-pack-20260921",
    "bf-amg-ops-pack-20260921",
    "bf-intel-ops-pack-20260921",
    "bf-owner-empire-pack-20260921",
    "bf-core-harden-pack-20260921",
)

HIDDEN = (
    "finance",
    "zayen",
    "hr",
    "trading",
    "bank",
    "payment",
    "payroll",
    "tax",
)

DONE_WORDS = frozenset(
    {"DONE", "COMMISSIONED", "HUMAN_COMMISSIONED", "ADOPTED", "COMPLETE", "COMPLETED"}
)

REFUSE_VIEWS = {
    "payment": "payment",
    "money": "payment",
    "pay": "payment",
    "bank": "bank",
    "transfer": "bank",
    "finance": "finance",
    "zayen": "finance",
    "payroll": "finance",
    "tax": "finance",
    "folio": "finance",
    "hr": "hr",
    "hris": "hr",
    "trading": "trading",
    "cloudflare": "cloudflare",
    "cf": "cloudflare",
    "cf-include": "cloudflare",
    "access": "cloudflare",
    "include": "cloudflare",
    "commission": "commission",
    "commissioned": "commission",
    "adopt": "adopt",
    "adopted": "adopt",
    "au": "adopt",
    "proven": "proven",
    "ready": "ready",
    "resolve": "resolve",
    "production": "production",
}


class HardenPackError(ValueError):
    """Fail closed. Does not commission, adopt, or move money."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_payment(_body: dict | None = None) -> None:
    raise HardenPackError("Core Harden does not move money.", code="payment_refused")


def refuse_bank(_body: dict | None = None) -> None:
    raise HardenPackError("Core Harden does not touch a bank.", code="bank_refused")


def refuse_finance(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Finance, Zayen, payroll, and tax stay off this desk.",
        code="finance_refused",
    )


def refuse_hr(_body: dict | None = None) -> None:
    raise HardenPackError("HR stays off this desk.", code="hr_refused")


def refuse_trading(_body: dict | None = None) -> None:
    raise HardenPackError("Trading stays off this desk.", code="trading_refused")


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Core Harden does not write Cloudflare Access.",
        code="cloudflare_refused",
    )


def refuse_commission(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Core Harden does not mark COMMISSIONED.",
        code="commission_refused",
    )


def refuse_adopt(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Core Harden does not mark ADOPTED.",
        code="adopt_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise HardenPackError("Core Harden does not mark PROVEN.", code="proven_refused")


def refuse_ready(_body: dict | None = None) -> None:
    raise HardenPackError("Core Harden does not mark READY.", code="ready_refused")


def refuse_resolve(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Core Harden does not resolve a completion row.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise HardenPackError(
        "Core Harden refuses a production write.",
        code="production_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    keys = {str(key).strip().lower() for key in payload.keys()}
    state = str(payload.get("state") or payload.get("status") or "").strip().upper()
    if keys & {"bank", "transfer"}:
        refuse_bank(payload)
    if keys & {"hr", "hris"}:
        refuse_hr(payload)
    if keys & {"trading"}:
        refuse_trading(payload)
    if keys & {"zayen", "payroll", "tax", "finance", "folio"}:
        refuse_finance(payload)
    if keys & {"money", "amount", "payment", "pay"} or payload.get("pay"):
        refuse_payment(payload)
    if keys & {"cloudflare", "cf", "access", "include"} or payload.get("cf_include"):
        refuse_cloudflare(payload)
    if state in {"COMMISSIONED", "HUMAN_COMMISSIONED", "COMMISSIONING"} or payload.get(
        "commission"
    ):
        refuse_commission(payload)
    if state in {"ADOPTED"} or "au_id" in keys or payload.get("adopt"):
        refuse_adopt(payload)
    if payload.get("proven") or "proven" in keys:
        refuse_proven(payload)
    if payload.get("ready") or "ready" in keys:
        refuse_ready(payload)
    if payload.get("resolve") or payload.get("cr_resolve"):
        refuse_resolve(payload)
    if payload.get("production"):
        refuse_production(payload)
    raise HardenPackError(
        "Core Harden is a read desk. Writes are refused.",
        code="writes_refused",
    )


def refuse_code(path: str) -> str | None:
    prefix = "/api/core/harden-pack"
    if path != prefix and not path.startswith(prefix + "/"):
        return None
    view = path[len(prefix) :].strip("/")
    if not view:
        return None
    head = view.split("/", 1)[0]
    return REFUSE_VIEWS.get(head)


def seat_for(person_id: str | None) -> dict[str, Any] | None:
    if (person_id or "").strip() != OWNER:
        return None
    return {
        "person_id": OWNER,
        "seat": "owner",
        "can_read": True,
        "money": False,
        "finance": False,
        "hr": False,
        "trading": False,
        "cloudflare_write": False,
        "can_commission": False,
        "can_adopt": False,
    }


def require_owner(person_id: str | None) -> dict[str, Any]:
    seat = seat_for(person_id)
    if seat is None:
        raise HardenPackError(
            "Core Harden is Owner (PERS-MATT) only.",
            code="forbidden",
        )
    return seat


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _ledger_state(cap_id: str) -> str:
    data = _read_json(LEDGER_JSON)
    row = data.get(cap_id) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return str(row[0]).strip().upper() or "UNKNOWN"


def _au_row(au_id: str) -> dict[str, Any]:
    data = _read_json(ADOPTION_JSON)
    rows = data if isinstance(data, list) else []
    for row in rows:
        if isinstance(row, dict) and row.get("au_id") == au_id:
            state = str(row.get("state") or "").strip() or "EMPTY"
            return {
                "au_id": au_id,
                "present": True,
                "state": state,
                "cap": row.get("cap"),
                "missing": row.get("missing") or "",
                "evidence": row.get("evidence") or "",
                "flipped": False,
                "adopted": state.upper() == "ADOPTED",
                "commissioning": state.upper() == "COMMISSIONING",
            }
    return {
        "au_id": au_id,
        "present": False,
        "state": "ABSENT",
        "cap": None,
        "missing": "",
        "evidence": "",
        "flipped": False,
        "adopted": False,
        "commissioning": False,
        "why": "Absence in the adoption file is not ADOPTED.",
    }


def _sha_kind(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "ABSENT"
    text = str(value).strip()
    if text.startswith("synthetic-"):
        return "SYNTHETIC"
    if len(text) >= 7 and all(c in "0123456789abcdef" for c in text.lower()):
        return "GIT"
    return "OTHER"


def honesty_flags() -> dict[str, Any]:
    core_11 = _ledger_state("CAP-CORE-11")
    core_12 = _ledger_state("CAP-CORE-12")
    uma = _au_row(AU_UMA)
    return {
        "bound": BOUND,
        "slice": SLICE,
        "schema": SCHEMA_ID,
        "owner_only": True,
        "person_gate": OWNER,
        "cap_core_11": core_11,
        "cap_core_12": core_12,
        "caps_raised": False,
        "invented_proven": False,
        "invented_ready": False,
        "invented_commissioned": False,
        "invented_adopted": False,
        "au_bzg_03_uma": uma["state"],
        "au_flipped": False,
        "not_done_is_done": False,
        "empty_is_done": False,
        "cr_mutated": False,
        "ledger_write": False,
        "adoption_write": False,
        "model_c_write": False,
        "money": None,
        "payment_executed": False,
        "bank_write": False,
        "zayen_write": False,
        "finance_controls": False,
        "hr_broadened": False,
        "trading": False,
        "payroll": False,
        "tax": False,
        "production_write": False,
        "production": False,
        "cloudflare_mutated": False,
        "track_d_restarted": False,
        "fin_lanes_restarted": False,
        "anon_fail_closed": True,
        "proven": core_11 == "PROVEN" or core_12 == "PROVEN",
        "ready": core_11 == "READY" or core_12 == "READY",
        "hidden": list(HIDDEN),
    }


def devi_gate() -> dict[str, Any]:
    claim = _read_json(DEVI_CLAIM_JSON)
    claim = claim if isinstance(claim, dict) else {}
    release = _read_json(RELEASE_JSON)
    release = release if isinstance(release, dict) else {}
    retest_row = release.get("devi_fb_ops_lead")
    retest_row = retest_row if isinstance(retest_row, dict) else {}
    operational = str(claim.get("UMA_FULL_OPERATIONAL_COMMISSIONING") or "").strip().upper()
    detail = str(claim.get("HUMAN_COMMISSIONING_STATUS") or "").strip()
    if operational in DONE_WORDS:
        human = operational
    else:
        human = "NOT_DONE" if operational or detail else "NOT_READ"
    if human in DONE_WORDS and operational not in DONE_WORDS:
        human = "NOT_DONE"
    if detail.upper() in DONE_WORDS and operational not in DONE_WORDS:
        human = "NOT_DONE"
    retest = str(retest_row.get("human_retest") or "").strip().upper() or "NOT_READ"
    cf_claim = str(claim.get("CF_ACCESS") or "").strip() or "NOT_READ"
    au = _au_row(AU_UMA)
    blockers: list[dict[str, Any]] = []
    if retest == "PARKED":
        blockers.append(
            {
                "id": "phone-retest",
                "status": "PARKED",
                "why": (
                    "Owner release parks the Devi human retest. "
                    "A parked retest is not a finished commission."
                ),
                "source": "state/build-claims/owner-autonomous-release-2026-09-19.json",
            }
        )
    elif retest != "DONE":
        blockers.append(
            {
                "id": "phone-retest",
                "status": retest,
                "why": "Phone retest was not read as done.",
                "source": "state/build-claims/owner-autonomous-release-2026-09-19.json",
            }
        )
    blockers.append(
        {
            "id": "cf-include",
            "claim_value": cf_claim,
            "review_value": "NEEDS_MATT",
            "resolved_by_pack": False,
            "why": (
                "The commissioning claim records CF_ACCESS as "
                f"{cf_claim}. The 19 Sep commission review records NEEDS_MATT. "
                "This pack does not write Cloudflare Access and does not close that gap."
            ),
            "claim_source": "state/build-claims/devi-uma-today-commissioning-2026-09-19.json",
            "review_source": CF_REVIEW,
        }
    )
    blockers.append(
        {
            "id": AU_UMA,
            "status": au["state"],
            "flipped": False,
            "why": "The Model E unit is shown as read. This pack does not move it to COMMISSIONING or ADOPTED.",
            "source": "state/model-e-au-discovery.json",
        }
    )
    commissioned = human in DONE_WORDS
    return {
        "ok": True,
        "gate": "devi-uma",
        "loud": not commissioned,
        "human_commissioning": human if not commissioned else human,
        "status_detail": detail or "NOT_READ",
        "operational": operational or "NOT_READ",
        "commissioned": False if not commissioned else True,
        "partial_is_done": False,
        "not_done_is_done": False,
        "phone_retest": retest,
        "cf_access_claim": cf_claim,
        "cf_access_review": "NEEDS_MATT",
        "cloudflare_write": False,
        "au": au,
        "cutover_at": claim.get("CUTOVER_AT"),
        "notes": claim.get("NOTES") or "",
        "blockers": blockers,
        "payment_approve": claim.get("PAYMENT_APPROVE") or "DENIED",
        "closer_submit": claim.get("CLOSER_SUBMIT") or "DENIED",
    }


def habitat_gate() -> dict[str, Any]:
    overlay = _read_json(OVERLAY_JSON)
    overlay = overlay if isinstance(overlay, dict) else {}
    missions = overlay.get("commissioning_missions")
    missions = missions if isinstance(missions, list) else []
    staff = next(
        (
            row
            for row in missions
            if isinstance(row, dict) and row.get("id") == "CM-HABITAT-STAFF"
        ),
        None,
    )
    rows = overlay.get("rows")
    rows = rows if isinstance(rows, list) else []
    ui = next(
        (row for row in rows if isinstance(row, dict) and row.get("id") == "OV-HABITAT-UI"),
        None,
    )
    verticals = overlay.get("verticals") if isinstance(overlay.get("verticals"), dict) else {}
    habitat = verticals.get("habitat") if isinstance(verticals.get("habitat"), dict) else {}
    distinctions = habitat.get("distinctions") if isinstance(habitat.get("distinctions"), dict) else {}
    graph = _read_text(GRAPH_MD) or ""
    phrase = "Prove-week ended; soft-hold Stage C"
    planning_hit = phrase in graph
    units = [_au_row(au_id) for au_id in HABITAT_AUS]
    any_adopted = any(unit["adopted"] for unit in units)
    human = "NOT_READ"
    if isinstance(ui, dict):
        human = str(ui.get("human_commissioning") or "NOT_READ").strip().upper() or "NOT_READ"
    commissioned = human in DONE_WORDS
    return {
        "ok": True,
        "gate": "habitat",
        "loud": not commissioned,
        "human_commissioning": "NOT_DONE" if human not in DONE_WORDS else human,
        "overlay_human_commissioning": human,
        "commissioned": commissioned and human in DONE_WORDS,
        "adopted": any_adopted,
        "invented_commissioned": False,
        "staff_mission": {
            "id": "CM-HABITAT-STAFF",
            "present": staff is not None,
            "status": (staff or {}).get("status") or "NOT_READ",
            "who": (staff or {}).get("who") or "",
            "note": (staff or {}).get("note") or "",
            "source": "state/progress/v1_overlay.json",
        },
        "metricool_write": distinctions.get("METRICOL_WRITE") or "NOT_READ",
        "real_external_publish": distinctions.get("REAL_EXTERNAL_PUBLISH"),
        "prove_week": {
            "proved": False,
            "status": "NOT_PROVED",
            "live_marker": None,
            "planning_phrase_present": planning_hit,
            "planning_phrase": phrase if planning_hit else None,
            "evidence_class": "PLANNING_DOC" if planning_hit else "NOT_READ",
            "source": "docs/deliveries/COMPRESSED-SPRINT-DEPENDENCY-GRAPH-2026-09-21.md",
            "why": (
                "The dependency graph mentions a prove-week and a soft-hold. "
                "This pack found no separate prove-week file, so that sentence is not a live commission."
                if planning_hit
                else "No prove-week sentence was read. That absence is not commissioned."
            ),
        },
        "adoption_units": units,
        "not_done_is_done": False,
    }


def _event_commit(events: list, lane_id: str) -> Any:
    found = None
    for event in events:
        if isinstance(event, dict) and event.get("lane_id") == lane_id and "completion_commit" in event:
            found = event.get("completion_commit")
    return found


def claim_rows() -> list[dict[str, Any]]:
    data = _read_json(CLAIMS_JSON)
    claims = data.get("claims") if isinstance(data, dict) else None
    by_id: dict[str, dict] = {}
    if isinstance(claims, list):
        for row in claims:
            if isinstance(row, dict) and row.get("id"):
                by_id[str(row["id"])] = row
    out: list[dict[str, Any]] = []
    for cid in SPRINT_CLAIM_IDS:
        row = by_id.get(cid)
        if row is None:
            out.append(
                {
                    "id": cid,
                    "present": False,
                    "verify": "ABSENT",
                    "checked": False,
                    "why": "The claim id is not in state/build-claims/2026-09-21.json. Absence is not PASS.",
                }
            )
            continue
        verify = row.get("verify")
        status = str(verify).strip() if verify else "UNCHECKED"
        out.append(
            {
                "id": cid,
                "present": True,
                "verify": status,
                "checked": bool(row.get("checked")),
                "by": row.get("by"),
                "why": "Verify is the value stored on the claim. This pack does not mark PASS.",
            }
        )
    return out


def factory_strip() -> dict[str, Any]:
    active_text = _read_text(BF / "ACTIVE")
    active_id = active_text.strip() if active_text else ""
    active_json = _read_json(BF / "ACTIVE.json")
    active_json = active_json if isinstance(active_json, dict) else {}
    mission_text = _read_text(BF / "ACTIVE_MISSION")
    mission_id = mission_text.strip() if mission_text else ""
    mission = _read_json(BF / "missions" / f"{mission_id}.json") if mission_id else None
    mission = mission if isinstance(mission, dict) else {}
    parked = _read_json(BF / "PARKED-sprint-track-d-intel-ops-pack-20260921.json")
    parked = parked if isinstance(parked, dict) else {}
    release = _read_json(RELEASE_JSON)
    release = release if isinstance(release, dict) else {}
    wave12 = release.get("wave12") if isinstance(release.get("wave12"), dict) else {}
    events = mission.get("event_log") if isinstance(mission.get("event_log"), list) else []
    lanes_out: list[dict[str, Any]] = []
    track_d: dict[str, Any] | None = None
    for lane in mission.get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("id") or "")
        commit = lane.get("completion_commit")
        event_commit = _event_commit(events, lane_id)
        kind = _sha_kind(commit)
        event_kind = _sha_kind(event_commit)
        card = {
            "id": lane_id,
            "track": lane.get("track"),
            "status": lane.get("status") or "NOT_READ",
            "stage": lane.get("stage"),
            "completion_commit": commit,
            "completion_commit_kind": kind,
            "event_completion_commit": event_commit,
            "event_completion_commit_kind": event_kind,
            "real_git_sha": kind == "GIT",
            "commit_deferred": bool(lane.get("commit_deferred_reason")) or kind != "GIT",
            "commit_deferred_reason": lane.get("commit_deferred_reason"),
            "peaches_verify": lane.get("peaches_verify"),
            "block_reason": lane.get("block_reason"),
        }
        if lane.get("track") == "D" or "intel" in lane_id:
            reason = lane.get("block_reason") or parked.get("reason") or "NOT_READ"
            track_d = {
                "track": "D",
                "state": "PARKED",
                "lane_status": lane.get("status") or "NOT_READ",
                "reason": reason,
                "parked_file_reason": parked.get("reason"),
                "ops_pack_built": False,
                "restarted": False,
                "why": "Track D stays parked. This pack does not start it.",
            }
            card["restarted"] = False
        lanes_out.append(card)
    if track_d is None:
        track_d = {
            "track": "D",
            "state": "PARKED",
            "lane_status": "NOT_READ",
            "reason": parked.get("reason") or "NOT_READ",
            "parked_file_reason": parked.get("reason"),
            "ops_pack_built": False,
            "restarted": False,
            "why": "Track D was not found on the mission. That is not a start.",
        }
    run_id = active_id or str(active_json.get("run_id") or "")
    return {
        "ok": True,
        "active_run_id": run_id or "EMPTY",
        "active_run_read": bool(run_id),
        "active_stage": active_json.get("stage") or "NOT_READ",
        "mission_id": mission_id or "EMPTY",
        "mission_expected": MISSION_EXPECTED,
        "mission_matches_expected": mission_id == MISSION_EXPECTED,
        "mission_status": mission.get("status") or "NOT_READ",
        "active_lane_id": mission.get("active_lane_id") or "EMPTY",
        "lanes": lanes_out,
        "claims": claim_rows(),
        "track_d": track_d,
        "wave12": {
            "status": wave12.get("status") or "NOT_READ",
            "parked_pending": list(wave12.get("parked_pending") or []),
            "restarted": False,
            "why": "Parked Finance lanes stay parked. This pack does not start them.",
        },
        "empty_is_done": False,
        "writes": False,
    }


def _action(action_id: str, label: str, who: str, why: str, href: str | None) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "who": who,
        "kind": "human",
        "href": href,
        "done": False,
        "why": why,
    }


def next_actions(devi: dict[str, Any], habitat: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    if devi.get("phone_retest") == "PARKED" or devi.get("human_commissioning") == "NOT_DONE":
        actions.append(
            _action(
                "devi-phone-retest",
                "Devi phone retest",
                "Devi",
                (
                    "Full Uma operational commissioning is NOT_DONE and the human retest is parked. "
                    "Opening Today does not mark the loop commissioned."
                ),
                "/bzg/uma-blu",
            )
        )
    if devi.get("cf_access_claim") != devi.get("cf_access_review"):
        actions.append(
            _action(
                "confirm-devi-cf-seat",
                "Confirm the Devi Cloudflare Access seat",
                "Matt",
                (
                    f"Claim CF_ACCESS is {devi.get('cf_access_claim')}. "
                    "The 19 Sep review says NEEDS_MATT. This desk does not widen Access."
                ),
                None,
            )
        )
    staff = habitat.get("staff_mission") or {}
    if staff.get("status") == "WAITING" or habitat.get("human_commissioning") == "NOT_DONE":
        actions.append(
            _action(
                "habitat-staff-commission",
                "Habitat staff commissioning stays waiting",
                str(staff.get("who") or "Haikal / Amanda"),
                (
                    "Habitat human commissioning is NOT_DONE. "
                    "A prove-week sentence is not a commissioned mark."
                ),
                "/habitat-operator.html",
            )
        )
    nxt = actions[0] if actions else None
    return {
        "ok": True,
        "next": nxt,
        "items": actions,
        "fake_green": False,
        "why": "Actions come from claim, release, overlay, and review files. NOT_DONE is not done.",
    }


def build_desk(verified_person_id: str | None = None) -> dict[str, Any]:
    require_owner(verified_person_id)
    devi = devi_gate()
    habitat = habitat_gate()
    factory = factory_strip()
    actions = next_actions(devi, habitat)
    flags = honesty_flags()
    return {
        "ok": True,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "title": "Core Harden",
        "devi": devi,
        "habitat": habitat,
        "factory": factory,
        "actions": actions,
        "honesty": flags,
        "money": None,
        "payment_executed": False,
        "cloudflare_mutated": False,
        "invented_commissioned": False,
        "invented_adopted": False,
        "hidden": list(HIDDEN),
    }


def schema_document() -> dict[str, Any]:
    return {
        "id": SCHEMA_ID,
        "bound": BOUND,
        "owner": OWNER,
        "writes": False,
        "views": ["desk", "devi", "habitat", "factory", "actions", "honesty", "schema"],
        "refused": sorted(set(REFUSE_VIEWS)),
    }
