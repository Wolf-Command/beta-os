#!/usr/bin/env python3
"""Deterministic build-factory lane queue. Beta tooling only.

Persisted mission state under state/build-factory/missions/<id>.json.
No network. No cursor-agent process. Queue software — not a new agent.

Invariant: slice close selects the next authorised runnable lane without
human pick. Policy-blocked lanes do not stop later safe lanes. Grok FAIL
returns WAITING_CURSOR_FIX up to RETRY_CEILING, then ESCALATED.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
MISSIONS = BF / "missions"
ACTIVE_MISSION = BF / "ACTIVE_MISSION"

# Retries after the first attempt → 3 attempts total
RETRY_CEILING = 2
MAX_ATTEMPTS = RETRY_CEILING + 1

LANE_PENDING = "PENDING"
LANE_ACTIVE = "ACTIVE"
LANE_WAITING_CURSOR = "WAITING_CURSOR"
LANE_WAITING_CURSOR_FIX = "WAITING_CURSOR_FIX"
LANE_GROK_REVIEW = "GROK_REVIEW"
LANE_COMPLETED = "COMPLETED"
LANE_BLOCKED = "BLOCKED"
LANE_ESCALATED = "ESCALATED"

TERMINAL_LANE = frozenset({LANE_COMPLETED, LANE_BLOCKED, LANE_ESCALATED})
RUNNABLE_LANE = frozenset({LANE_PENDING})

# Bounds that refuse even if a lane asks
FORBIDDEN_BOUND_TOKENS = frozenset(
    {
        "production",
        "external-write",
        "external_write",
        "owner-authority",
        "owner_authority",
        "metricool",
        "esb",
        "yanolja",
        "banking",
        "email-write",
        "dns-write",
        "cloudflare-write",
    }
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def guard_lane_bound(bound: str | None) -> dict[str, Any]:
    """Explicit Production / external-write / owner-authority guard.

    Tests call this directly. Refuse even if a lane asks.
    """
    text = (bound or "").strip().lower()
    tokens = set(text.replace("/", " ").replace(",", " ").split())
    for tok in FORBIDDEN_BOUND_TOKENS:
        if tok in text or tok in tokens:
            return {
                "allowed": False,
                "reason": f"policy_refuse:{tok}",
                "bound": bound,
            }
    return {"allowed": True, "reason": None, "bound": bound}


def _lane(id: str, bound: str, status: str = LANE_PENDING, **extra: Any) -> dict:
    base = {
        "id": id,
        "bound": bound,
        "status": status,
        "retry_count": 0,
        "attempt_count": 0,
        "completion_commit": None,
        "block_reason": None,
        "escalation_reason": None,
        "stage": None,
        "events_applied": [],
    }
    base.update(extra)
    return base


def new_mission(
    mission_id: str,
    lanes: list[dict[str, str]],
    *,
    title: str = "",
) -> dict:
    """Create mission from ordered authorised lane list. No invented lanes."""
    ordered = []
    for spec in lanes:
        lid = spec["id"]
        bound = spec.get("bound", "beta-harmless")
        g = guard_lane_bound(bound)
        lane = _lane(lid, bound)
        if not g["allowed"]:
            lane["status"] = LANE_BLOCKED
            lane["block_reason"] = g["reason"]
        ordered.append(lane)
    return {
        "mission_id": mission_id,
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "OPEN",
        "active_lane_id": None,
        "lanes": ordered,
        "event_log": [],
        "watcher_tokens": [],
    }


def mission_path(mission_id: str, root: Path | None = None) -> Path:
    base = root if root is not None else MISSIONS
    return base / f"{mission_id}.json"


def save_mission(mission: dict, root: Path | None = None) -> Path:
    base = root if root is not None else MISSIONS
    base.mkdir(parents=True, exist_ok=True)
    mission = deepcopy(mission)
    mission["updated_at"] = now_iso()
    path = base / f"{mission['mission_id']}.json"
    path.write_text(json.dumps(mission, indent=2) + "\n", encoding="utf-8")
    return path


def load_mission(mission_id: str, root: Path | None = None) -> dict | None:
    path = mission_path(mission_id, root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_active_mission(mission_id: str | None, bf_root: Path | None = None) -> None:
    bf = bf_root if bf_root is not None else BF
    bf.mkdir(parents=True, exist_ok=True)
    ptr = bf / "ACTIVE_MISSION"
    if mission_id is None:
        if ptr.exists():
            ptr.unlink()
        return
    ptr.write_text(mission_id + "\n", encoding="utf-8")


def read_active_mission_id(bf_root: Path | None = None) -> str | None:
    bf = bf_root if bf_root is not None else BF
    ptr = bf / "ACTIVE_MISSION"
    if not ptr.exists():
        return None
    mid = ptr.read_text(encoding="utf-8").strip()
    return mid or None


def get_lane(mission: dict, lane_id: str) -> dict | None:
    for lane in mission["lanes"]:
        if lane["id"] == lane_id:
            return lane
    return None


def authorised_lane_ids(mission: dict) -> list[str]:
    return [lane["id"] for lane in mission["lanes"]]


def next_runnable_lane(mission: dict) -> dict | None:
    """Select next authorised runnable lane. No human pick. No invention."""
    for lane in mission["lanes"]:
        if lane["status"] in TERMINAL_LANE:
            continue
        if lane.get("completion_commit"):
            # Already completed — never relaunch
            continue
        g = guard_lane_bound(lane.get("bound"))
        if not g["allowed"]:
            if lane["status"] != LANE_BLOCKED:
                lane["status"] = LANE_BLOCKED
                lane["block_reason"] = g["reason"]
            continue
        if lane["status"] in RUNNABLE_LANE:
            return lane
        if lane["status"] in (
            LANE_WAITING_CURSOR,
            LANE_WAITING_CURSOR_FIX,
            LANE_GROK_REVIEW,
            LANE_ACTIVE,
        ):
            # Already in flight — resume that lane, do not start another
            return lane
    return None


def _append_event(mission: dict, event: dict) -> None:
    mission.setdefault("event_log", []).append({**event, "at": now_iso()})


def _idempotent_seen(lane: dict, event_id: str) -> bool:
    seen = lane.setdefault("events_applied", [])
    if event_id in seen:
        return True
    seen.append(event_id)
    return False


def start_lane(mission: dict, lane_id: str | None = None) -> dict:
    """Start next (or named) runnable lane. Refuses unauthorised / forbidden."""
    if lane_id is not None and lane_id not in authorised_lane_ids(mission):
        return {
            "ok": False,
            "error": "unauthorised_lane",
            "lane_id": lane_id,
        }
    lane = get_lane(mission, lane_id) if lane_id else next_runnable_lane(mission)
    if lane is None:
        remaining = [
            ln
            for ln in mission["lanes"]
            if ln["status"] not in TERMINAL_LANE and not ln.get("completion_commit")
        ]
        if not remaining or all(ln["status"] == LANE_BLOCKED for ln in mission["lanes"] if ln["status"] != LANE_COMPLETED):
            mission["status"] = "IDLE"
            mission["active_lane_id"] = None
            return {"ok": True, "started": False, "reason": "no_runnable_lane", "mission_status": "IDLE"}
        mission["status"] = "IDLE"
        mission["active_lane_id"] = None
        return {"ok": True, "started": False, "reason": "no_runnable_lane", "mission_status": "IDLE"}

    if lane.get("completion_commit"):
        return {
            "ok": True,
            "started": False,
            "reason": "already_completed",
            "lane_id": lane["id"],
            "completion_commit": lane["completion_commit"],
        }

    g = guard_lane_bound(lane.get("bound"))
    if not g["allowed"]:
        lane["status"] = LANE_BLOCKED
        lane["block_reason"] = g["reason"]
        _append_event(mission, {"kind": "LANE_BLOCKED", "lane_id": lane["id"], "reason": g["reason"]})
        # Do not stop later lanes — caller should call close_slice / start again
        return {
            "ok": True,
            "started": False,
            "blocked": True,
            "lane_id": lane["id"],
            "reason": g["reason"],
        }

    if lane["status"] in (LANE_WAITING_CURSOR, LANE_WAITING_CURSOR_FIX, LANE_GROK_REVIEW, LANE_ACTIVE):
        mission["active_lane_id"] = lane["id"]
        mission["status"] = "RUNNING"
        return {
            "ok": True,
            "started": False,
            "resumed": True,
            "lane_id": lane["id"],
            "status": lane["status"],
        }

    lane["status"] = LANE_WAITING_CURSOR
    lane["stage"] = LANE_WAITING_CURSOR
    lane["attempt_count"] = max(int(lane.get("attempt_count") or 0), 1)
    mission["active_lane_id"] = lane["id"]
    mission["status"] = "RUNNING"
    _append_event(mission, {"kind": "LANE_STARTED", "lane_id": lane["id"]})
    return {
        "ok": True,
        "started": True,
        "lane_id": lane["id"],
        "status": lane["status"],
        "attempt_count": lane["attempt_count"],
    }


def close_slice(mission: dict) -> dict:
    """Slice close: select next authorised runnable lane and start it."""
    # Clear active if current lane terminal
    aid = mission.get("active_lane_id")
    if aid:
        cur = get_lane(mission, aid)
        if cur and cur["status"] in TERMINAL_LANE:
            mission["active_lane_id"] = None

    # Auto-block any pending forbidden bounds without stopping the scan
    for lane in mission["lanes"]:
        if lane["status"] == LANE_PENDING:
            g = guard_lane_bound(lane.get("bound"))
            if not g["allowed"]:
                lane["status"] = LANE_BLOCKED
                lane["block_reason"] = g["reason"]

    result = start_lane(mission)
    result["action"] = "close_slice"
    if not result.get("started") and result.get("reason") == "no_runnable_lane":
        # Distinguish all-blocked / escalated idle
        non_done = [ln for ln in mission["lanes"] if ln["status"] != LANE_COMPLETED]
        if non_done and all(ln["status"] in (LANE_BLOCKED, LANE_ESCALATED) for ln in non_done):
            mission["status"] = "IDLE"
            result["mission_status"] = "IDLE"
            result["reason"] = "all_remaining_blocked_or_escalated"
    return result


def advance_cursor_done(mission: dict, lane_id: str, *, event_id: str = "cursor_done") -> dict:
    """Cursor finished → GROK_REVIEW. Idempotent on event_id."""
    lane = get_lane(mission, lane_id)
    if not lane:
        return {"ok": False, "error": "unknown_lane"}
    if _idempotent_seen(lane, event_id):
        return {
            "ok": True,
            "advanced": False,
            "idempotent": True,
            "lane_id": lane_id,
            "status": lane["status"],
        }
    if lane["status"] not in (LANE_WAITING_CURSOR, LANE_WAITING_CURSOR_FIX, LANE_ACTIVE):
        return {
            "ok": True,
            "advanced": False,
            "reason": f"wrong_stage:{lane['status']}",
            "lane_id": lane_id,
            "status": lane["status"],
        }
    lane["status"] = LANE_GROK_REVIEW
    lane["stage"] = LANE_GROK_REVIEW
    mission["active_lane_id"] = lane_id
    _append_event(mission, {"kind": "CURSOR_DONE", "lane_id": lane_id, "event_id": event_id})
    return {"ok": True, "advanced": True, "lane_id": lane_id, "status": LANE_GROK_REVIEW}


def apply_grok_result(
    mission: dict,
    lane_id: str,
    result: str,
    *,
    event_id: str | None = None,
    completion_commit: str | None = None,
) -> dict:
    """Grok PASS → complete; Grok FAIL → fix or escalate. Idempotent."""
    lane = get_lane(mission, lane_id)
    if not lane:
        return {"ok": False, "error": "unknown_lane"}
    eid = event_id or f"grok:{result}:{lane.get('retry_count', 0)}:{lane.get('attempt_count', 0)}"
    if _idempotent_seen(lane, eid):
        return {
            "ok": True,
            "applied": False,
            "idempotent": True,
            "lane_id": lane_id,
            "status": lane["status"],
            "retry_count": lane.get("retry_count", 0),
        }

    if lane["status"] != LANE_GROK_REVIEW and result.upper() == "PASS":
        # Allow PASS only from review; duplicate completion handled below
        if lane["status"] == LANE_COMPLETED:
            return {
                "ok": True,
                "applied": False,
                "idempotent": True,
                "lane_id": lane_id,
                "status": LANE_COMPLETED,
            }

    result_u = result.upper()
    if result_u == "PASS":
        if lane["status"] not in (LANE_GROK_REVIEW, LANE_WAITING_CURSOR, LANE_WAITING_CURSOR_FIX):
            if lane["status"] == LANE_COMPLETED:
                return {
                    "ok": True,
                    "applied": False,
                    "idempotent": True,
                    "lane_id": lane_id,
                    "status": LANE_COMPLETED,
                }
        lane["status"] = LANE_COMPLETED
        lane["stage"] = LANE_COMPLETED
        if completion_commit:
            lane["completion_commit"] = completion_commit
        elif not lane.get("completion_commit"):
            lane["completion_commit"] = f"synthetic-{lane_id}-{now_iso()}"
        mission["active_lane_id"] = None
        _append_event(
            mission,
            {
                "kind": "GROK_PASS",
                "lane_id": lane_id,
                "event_id": eid,
                "completion_commit": lane["completion_commit"],
            },
        )
        return {
            "ok": True,
            "applied": True,
            "lane_id": lane_id,
            "status": LANE_COMPLETED,
            "completion_commit": lane["completion_commit"],
        }

    if result_u == "FAIL":
        if lane["status"] not in (LANE_GROK_REVIEW, LANE_WAITING_CURSOR_FIX):
            return {
                "ok": True,
                "applied": False,
                "reason": f"wrong_stage:{lane['status']}",
                "lane_id": lane_id,
            }
        retries = int(lane.get("retry_count") or 0)
        if retries >= RETRY_CEILING:
            lane["status"] = LANE_ESCALATED
            lane["stage"] = LANE_ESCALATED
            lane["escalation_reason"] = (
                f"retry_ceiling_exhausted:{retries}>={RETRY_CEILING}"
            )
            mission["active_lane_id"] = None
            _append_event(
                mission,
                {
                    "kind": "LANE_ESCALATED",
                    "lane_id": lane_id,
                    "event_id": eid,
                    "reason": lane["escalation_reason"],
                },
            )
            return {
                "ok": True,
                "applied": True,
                "lane_id": lane_id,
                "status": LANE_ESCALATED,
                "retry_count": retries,
                "escalation_reason": lane["escalation_reason"],
            }

        lane["retry_count"] = retries + 1
        lane["attempt_count"] = int(lane.get("attempt_count") or 1) + 1
        lane["status"] = LANE_WAITING_CURSOR_FIX
        lane["stage"] = LANE_WAITING_CURSOR_FIX
        mission["active_lane_id"] = lane_id
        _append_event(
            mission,
            {
                "kind": "GROK_FAIL",
                "lane_id": lane_id,
                "event_id": eid,
                "retry_count": lane["retry_count"],
            },
        )
        return {
            "ok": True,
            "applied": True,
            "lane_id": lane_id,
            "status": LANE_WAITING_CURSOR_FIX,
            "retry_count": lane["retry_count"],
            "attempt_count": lane["attempt_count"],
        }

    return {"ok": False, "error": f"unknown_result:{result}"}


def record_completion_commit(mission: dict, lane_id: str, commit: str) -> dict:
    lane = get_lane(mission, lane_id)
    if not lane:
        return {"ok": False, "error": "unknown_lane"}
    if lane.get("completion_commit") == commit:
        return {"ok": True, "recorded": False, "idempotent": True, "lane_id": lane_id}
    lane["completion_commit"] = commit
    if lane["status"] != LANE_COMPLETED:
        lane["status"] = LANE_COMPLETED
        lane["stage"] = LANE_COMPLETED
    mission["active_lane_id"] = None
    _append_event(
        mission,
        {"kind": "COMPLETION_COMMIT", "lane_id": lane_id, "completion_commit": commit},
    )
    return {"ok": True, "recorded": True, "lane_id": lane_id, "completion_commit": commit}


def mark_blocked(mission: dict, lane_id: str, reason: str) -> dict:
    lane = get_lane(mission, lane_id)
    if not lane:
        return {"ok": False, "error": "unknown_lane"}
    if lane["status"] == LANE_BLOCKED and lane.get("block_reason") == reason:
        return {"ok": True, "blocked": False, "idempotent": True, "lane_id": lane_id}
    lane["status"] = LANE_BLOCKED
    lane["block_reason"] = reason
    if mission.get("active_lane_id") == lane_id:
        mission["active_lane_id"] = None
    _append_event(mission, {"kind": "LANE_BLOCKED", "lane_id": lane_id, "reason": reason})
    return {"ok": True, "blocked": True, "lane_id": lane_id, "reason": reason}


def restart_mission(mission_id: str, root: Path | None = None) -> dict:
    """Reconstruct from persisted mission file. Do not trust memory-only flags."""
    mission = load_mission(mission_id, root)
    if not mission:
        return {"ok": False, "error": "mission_not_found", "mission_id": mission_id}

    # Stale ACTIVE pointer: clear if lane already terminal / completed
    aid = mission.get("active_lane_id")
    if aid:
        lane = get_lane(mission, aid)
        if not lane or lane["status"] in TERMINAL_LANE or lane.get("completion_commit"):
            mission["active_lane_id"] = None
            if lane and lane.get("completion_commit") and lane["status"] != LANE_COMPLETED:
                lane["status"] = LANE_COMPLETED

    # Never relaunch completed lanes
    for lane in mission["lanes"]:
        if lane.get("completion_commit") and lane["status"] != LANE_COMPLETED:
            lane["status"] = LANE_COMPLETED

    resumed = None
    if mission.get("active_lane_id"):
        resumed = get_lane(mission, mission["active_lane_id"])
    else:
        # Resume in-flight non-terminal without starting fresh completed work
        for lane in mission["lanes"]:
            if lane["status"] in (
                LANE_WAITING_CURSOR,
                LANE_WAITING_CURSOR_FIX,
                LANE_GROK_REVIEW,
                LANE_ACTIVE,
            ) and not lane.get("completion_commit"):
                mission["active_lane_id"] = lane["id"]
                resumed = lane
                break

    mission["status"] = "RUNNING" if resumed else mission.get("status") or "OPEN"
    save_mission(mission, root)
    return {
        "ok": True,
        "mission_id": mission_id,
        "active_lane_id": mission.get("active_lane_id"),
        "resumed_status": resumed["status"] if resumed else None,
        "lanes": [
            {
                "id": ln["id"],
                "status": ln["status"],
                "completion_commit": ln.get("completion_commit"),
                "retry_count": ln.get("retry_count", 0),
            }
            for ln in mission["lanes"]
        ],
        "mission": mission,
    }


def watcher_execute(mission: dict, token: str) -> dict:
    """Duplicate watcher execution is idempotent via token."""
    tokens = mission.setdefault("watcher_tokens", [])
    if token in tokens:
        return {"ok": True, "executed": False, "idempotent": True, "token": token}
    tokens.append(token)
    # Watcher only advises/advances via close_slice semantics when idle
    if mission.get("active_lane_id"):
        lane = get_lane(mission, mission["active_lane_id"])
        return {
            "ok": True,
            "executed": True,
            "token": token,
            "action": "observe",
            "active_lane_id": mission["active_lane_id"],
            "status": lane["status"] if lane else None,
        }
    out = close_slice(mission)
    out["executed"] = True
    out["token"] = token
    return out


def simulate_process_death(mission: dict, *, after_commit: bool, commit: str | None = None) -> dict:
    """Model process death before/after commit without launching children."""
    aid = mission.get("active_lane_id")
    if not aid:
        return {"ok": False, "error": "no_active_lane"}
    lane = get_lane(mission, aid)
    if not lane:
        return {"ok": False, "error": "unknown_lane"}
    if after_commit:
        c = commit or f"dead-after-{aid}"
        lane["completion_commit"] = c
        lane["status"] = LANE_COMPLETED
        lane["stage"] = LANE_COMPLETED
        mission["active_lane_id"] = None
        _append_event(
            mission,
            {"kind": "PROCESS_DEATH_AFTER_COMMIT", "lane_id": aid, "completion_commit": c},
        )
        return {"ok": True, "after_commit": True, "lane_id": aid, "completion_commit": c}
    # before commit — leave stage as-is for restart reconstruction
    _append_event(mission, {"kind": "PROCESS_DEATH_BEFORE_COMMIT", "lane_id": aid})
    return {
        "ok": True,
        "after_commit": False,
        "lane_id": aid,
        "status": lane["status"],
        "completion_commit": lane.get("completion_commit"),
    }
