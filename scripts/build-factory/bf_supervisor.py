#!/usr/bin/env python3
"""Active-mission factory supervisor. Beta tooling only.

Invariant: ACTIVE MISSION → advancement available regardless of calendar.
Matt status is not an input. Quiet when inactive.

Does NOT touch Production. Matt status is not an input.
On worker exit or idle, bf_dispatch starts the next safe named-queue slice.
Does not kill a live cursor. Credit conservation does not block that queue.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
ACTIVE = BF / "ACTIVE"
WAKE = BF / "WAKE.json"
SUPERVISOR_LOG = BF / "supervisor.log"
TICKS = BF / "supervisor-ticks.jsonl"

sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))
import bf_advance as ba  # noqa: E402
import bf_watch as bw  # noqa: E402
import bf_queue as bq  # noqa: E402
try:
    import bf_disk_guard as bdg  # noqa: E402
except ImportError:  # pragma: no cover
    bdg = None  # type: ignore

# Hard ceiling for consecutive INSPECT recoveries on the same run without EXIT.
INSPECT_RETRY_CEILING = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_tick(payload: dict) -> None:
    BF.mkdir(parents=True, exist_ok=True)
    with TICKS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_wake(payload: dict) -> None:
    WAKE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _load_run_mut() -> dict | None:
    run = bw.load_run()
    return run


def _save_run(run: dict) -> None:
    path = BF / "runs" / f"{run['run_id']}.json"
    run["updated_at"] = now_iso()
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def calendar_independent() -> bool:
    """True when this module has no runtime calendar gate."""
    text = Path(__file__).read_text(encoding="utf-8")
    # Build needles without storing forbidden tokens as contiguous literals in this file.
    needles = [
        "datetime.now()." + "weekday",
        "iso" + "weekday(",
        "." + "weekday()",
        "day_" + "of_week",
        "strftime(" + '"%w"',
        "strftime(" + "'%w'",
    ]
    body_lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    # Exclude this function body from the scan so the needles themselves do not self-fail.
    keep = []
    skipping = False
    for ln in body_lines:
        if ln.startswith("def calendar_independent"):
            skipping = True
            continue
        if skipping:
            if ln.startswith("def "):
                skipping = False
                keep.append(ln)
            continue
        keep.append(ln)
    body = "\n".join(keep)
    return not any(n in body for n in needles)




_IN_FLIGHT = (
    bq.LANE_WAITING_CURSOR,
    bq.LANE_WAITING_CURSOR_FIX,
    bq.LANE_ACTIVE,
    bq.LANE_GROK_REVIEW,
)


def _human_parked_lane(lane: dict | None) -> bool:
    """Human retest / park is a side branch. It must not stall later safe lanes."""
    if not lane:
        return False
    if lane.get("human_parked") is True:
        return True
    status = str(lane.get("status") or "")
    if status in ("PARKED", "WAITING_HUMAN"):
        return True
    reason = str(lane.get("block_reason") or "").lower()
    return "human_retest" in reason or reason.startswith("human_park")


def _release_human_parks(mission: dict) -> None:
    """Drop a human-parked pointer so close_slice can select the next safe lane."""
    for lane in mission.get("lanes") or []:
        if not _human_parked_lane(lane):
            continue
        if lane.get("status") not in bq.TERMINAL_LANE and lane.get("status") != "PARKED":
            lane["status"] = "PARKED"
            lane["stage"] = "PARKED"
            if not lane.get("block_reason"):
                lane["block_reason"] = "human_retest_parked"
        if mission.get("active_lane_id") == lane.get("id"):
            mission["active_lane_id"] = None


def _resume_wake(mid: str, lane_id: str, status: str | None) -> dict:
    return {
        "kind": "FACTORY_RESUME_LANE",
        "mission_id": mid,
        "lane_id": lane_id,
        "at": now_iso(),
        "require_matt": False,
        "instruction": (
            "ACTIVE run pointer empty but mission lane still in flight. "
            "Relaunch or finish that lane, then close_slice. Do not wait for Matt."
        ),
        "lane_status": status,
    }


def mission_continue_if_idle(*, dry_run: bool = False) -> dict:
    """When no ACTIVE run, CLOSE→SELECT NEXT on ACTIVE_MISSION if eligible.

    Owner 19 Sep invariant: IDLE with eligible safe queue is a factory defect.
    Queue software already proved; this wires run-empty ticks to close_slice.
    Does not launch cursor-agent itself — writes FACTORY_LAUNCH_NEXT wake.
    Human-parked retest (Devi) is not a mission stop.
    """
    mid = bq.read_active_mission_id(BF)
    if not mid:
        return {"action": "IDLE", "reason": "no_active_run_and_no_mission", "wake_parent": False, "stopped": True}
    mission = bq.load_mission(mid, BF / "missions")
    if not mission:
        return {"action": "IDLE", "reason": "active_mission_missing", "mission_id": mid}

    if not dry_run:
        _release_human_parks(mission)

    # If current lane still non-terminal and has no completion, do not skip it.
    # A human-parked retest is not in-flight work.
    aid = mission.get("active_lane_id")
    if aid:
        cur = bq.get_lane(mission, aid)
        if (
            cur
            and not _human_parked_lane(cur)
            and cur.get("status") not in bq.TERMINAL_LANE
            and not cur.get("completion_commit")
            and cur.get("status") in _IN_FLIGHT
        ):
            out = {
                "action": "RESUME_LANE",
                "reason": "active_run_missing_lane_in_flight",
                "mission_id": mid,
                "lane_id": aid,
                "lane_status": cur.get("status"),
                "require_matt": False,
            }
            if not dry_run:
                _write_wake(_resume_wake(mid, aid, cur.get("status")))
                bq.save_mission(mission, BF / "missions")
            return out

    if dry_run:
        nxt = None
        for lane in mission["lanes"]:
            if lane["status"] == bq.LANE_PENDING and not lane.get("completion_commit"):
                g = bq.guard_lane_bound(lane.get("bound"))
                if g["allowed"]:
                    nxt = lane
                    break
        return {
            "action": "CLOSE_SLICE" if nxt else "IDLE",
            "reason": "dry_run_mission_scan",
            "mission_id": mid,
            "next_lane_id": nxt["id"] if nxt else None,
        }

    result = bq.close_slice(mission)
    bq.save_mission(mission, BF / "missions")
    if result.get("resumed") and not result.get("started"):
        lane_id = result.get("lane_id") or mission.get("active_lane_id")
        lane = bq.get_lane(mission, lane_id) if lane_id else None
        if lane_id and not _human_parked_lane(lane):
            _write_wake(_resume_wake(mid, lane_id, (lane or {}).get("status")))
            return {
                "action": "RESUME_LANE",
                "reason": "close_slice_resumed_in_flight",
                "mission_id": mid,
                "lane_id": lane_id,
                "close_slice": result,
                "require_matt": False,
            }
    if result.get("started"):
        lane_id = result.get("lane_id") or mission.get("active_lane_id")
        lane = bq.get_lane(mission, lane_id) if lane_id else None
        wake = {
            "kind": "FACTORY_LAUNCH_NEXT",
            "mission_id": mid,
            "lane_id": lane_id,
            "bound": (lane or {}).get("bound"),
            "at": now_iso(),
            "require_matt": False,
            "instruction": (
                "close_slice selected next eligible safe lane. Peaches must START Cursor "
                "for this lane (plan→WAITING_CURSOR), update Completion Register, no Matt pick."
            ),
        }
        _write_wake(wake)
        return {
            "action": "LAUNCH_NEXT",
            "reason": "mission_close_slice_started",
            "mission_id": mid,
            "lane_id": lane_id,
            "close_slice": result,
            "require_matt": False,
        }
    return {
        "action": "IDLE",
        "reason": result.get("reason") or "no_runnable_lane",
        "mission_id": mid,
        "close_slice": result,
        "require_matt": False,
    }



def hold_flags_blocking(bf_dir: Path | None = None) -> dict | None:
    """Refuse dispatch while any factory hold flag is active.

    Owner grill 2026-10-06 item 2: on-exit calls bf_supervisor directly and
    previously skipped DISK-SAFETY-HOLD / SINGLE_TRACK-HOLD flag files (launchd
    unload alone is not enough). Every dispatch path must read these flags.
    Returns a dict describing the active hold, or None when clear.
    """
    base = bf_dir if bf_dir is not None else BF
    active: list[dict] = []

    disk = base / "DISK-SAFETY-HOLD.json"
    if disk.is_file():
        try:
            payload = json.loads(disk.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payload = {"status": "UNREADABLE", "error": exc.__class__.__name__}
        status = str(payload.get("status") or "").upper()
        # RESUMED = hold lifted; anything else (missing status, HOLD, PAUSED) blocks.
        if status != "RESUMED":
            active.append({
                "flag": "DISK-SAFETY-HOLD.json",
                "status": payload.get("status") or "ACTIVE",
                "kind": payload.get("kind") or "DISK_SAFETY_HOLD",
                "reason": payload.get("reason"),
            })

    single = base / "SINGLE_TRACK-HOLD.json"
    if single.is_file():
        try:
            payload = json.loads(single.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payload = {"status": "UNREADABLE", "error": exc.__class__.__name__}
        status = str(payload.get("status") or "").upper()
        if status not in ("RESUMED", "CLEAR", "CLEARED", "OFF"):
            active.append({
                "flag": "SINGLE_TRACK-HOLD.json",
                "status": payload.get("status") or "HOLD",
                "kind": payload.get("kind") or "SINGLE_TRACK_HOLD",
                "reason": payload.get("reason"),
                "allowed_track": payload.get("allowed_track"),
            })

    hold_marker = base / "HOLD"
    if hold_marker.exists():
        try:
            body = hold_marker.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            body = ""
        # Empty marker still counts as a hold presence signal.
        active.append({
            "flag": "HOLD",
            "status": "HOLD",
            "kind": body or "HOLD_MARKER",
            "reason": "HOLD marker file present",
        })

    # Any other *-HOLD.json that is not RESUMED/CLEAR (exclude archived-*).
    for path in sorted(base.glob("*-HOLD.json")):
        name = path.name
        if name in ("DISK-SAFETY-HOLD.json", "SINGLE_TRACK-HOLD.json"):
            continue
        if name.startswith("archived-"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payload = {"status": "UNREADABLE", "error": exc.__class__.__name__}
        status = str(payload.get("status") or "").upper()
        if status not in ("RESUMED", "CLEAR", "CLEARED", "OFF"):
            active.append({
                "flag": name,
                "status": payload.get("status") or "HOLD",
                "kind": payload.get("kind") or name,
                "reason": payload.get("reason"),
            })

    if not active:
        return None
    return {
        "action": "HOLD_REFUSED",
        "holds": active,
        "allow_dispatch": False,
        "message": "dispatch refused: factory hold flag(s) set",
    }


def tick(*, dry_run: bool = False) -> dict:
    """One supervisor tick. Idempotent. Calendar-blind."""
    out: dict = {
        "ok": True,
        "at": now_iso(),
        "active": False,
        "action": "IDLE",
        "require_matt": False,
        "dry_run": dry_run,
        "calendar_gate": False,  # always false — invariant
        "wake_parent": False,
        "stopped": False,
    }

    # Owner grill 2026-10-06: honour DISK-SAFETY / SINGLE_TRACK / HOLD flags on
    # every path, including the launcher on-exit tick (launchd unload alone is
    # not enough). Runs even on dry_run so refuse is testable.
    blocked = hold_flags_blocking()
    if blocked:
        out["action"] = "HOLD_REFUSED"
        out["ok"] = True
        out["stopped"] = False
        out["hold_flags"] = blocked
        out["allow_dispatch"] = False
        refuse_line = {
            "at": now_iso(),
            "event": "DISPATCH_REFUSED_HOLD",
            "action": "HOLD_REFUSED",
            "holds": blocked.get("holds"),
            "dry_run": dry_run,
            "require_matt": False,
        }
        try:
            with (BF / "DISPATCH-AUDIT.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(refuse_line, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001
            pass
        try:
            with (BF / "hold-refusals.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(refuse_line, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001
            pass
        if not dry_run:
            _append_tick(out)
            _write_wake({
                "kind": "FACTORY_HOLD_REFUSED",
                "at": now_iso(),
                "require_matt": False,
                "wake_parent": False,
                "stopped": False,
                "action": "HOLD_REFUSED",
                "hold_flags": blocked,
                "instruction": (
                    "Factory hold flag(s) set. No dispatch (including on-exit). "
                    "Do not message Matt."
                ),
            })
        return out

    # Owner P0 5 Oct 2026 21:01 WITA — hard free-space guards.
    # <100GB WARN, <50GB pause new dispatches + auto-clean tmp-f1, <25GB P0 protection.
    if bdg is not None and not dry_run:
        try:
            dg = bdg.check(auto_clean=True)
            out["disk_guard"] = dg
            if not dg.get("allow_dispatch", True):
                out["action"] = "DISK_HOLD"
                out["ok"] = True
                out["stopped"] = False
                _append_tick(out)
                _write_wake({
                    "kind": "FACTORY_DISK_HOLD",
                    "at": now_iso(),
                    "require_matt": False,
                    "wake_parent": False,
                    "stopped": False,
                    "action": "DISK_HOLD",
                    "disk_guard": dg,
                    "instruction": (
                        "Studio free space below guard. No new factory dispatches. "
                        "Do not message Matt. Archive catalog/backups to NAS or free disk."
                    ),
                })
                return out
        except Exception as exc:  # noqa: BLE001
            out["disk_guard_error"] = exc.__class__.__name__

    import bf_dispatch as bd

    dispatched = bd.supervisor_dispatch(dry_run=dry_run)
    if dispatched.get("handled"):
        out.update(dispatched)
        out["require_matt"] = False
        out["calendar_gate"] = False
        # Self-dispatch is not a parent wake and is not an idle stop.
        if dispatched.get("started") or dispatched.get("action") in ("WAIT", "DISPATCH"):
            out["stopped"] = False
            out["wake_parent"] = False
        if not dry_run:
            _append_tick(out)
            _write_wake(
                {
                    "kind": "FACTORY_SUPERVISOR_OWNS_DISPATCH",
                    "at": now_iso(),
                    "require_matt": False,
                    "wake_parent": False,
                    "stopped": False,
                    "action": out.get("action"),
                    "run_id": out.get("run_id"),
                    "slice": out.get("slice"),
                    "instruction": (
                        "The build-factory supervisor owns dispatch. Do not message Matt. "
                        "Do not start a second cursor while this writer is alive."
                    ),
                }
            )
        return out

    if not ACTIVE.exists() or not ACTIVE.read_text(encoding="utf-8").strip():
        # Owner 19 Sep: empty ACTIVE must still consume ACTIVE_MISSION queue.
        cont = mission_continue_if_idle(dry_run=dry_run)
        out.update(cont)
        out["reason"] = cont.get("reason", "no_active_run")
        if not dry_run:
            _append_tick(out)
        return out

    run = _load_run_mut()
    if not run:
        out["reason"] = "active_pointer_stale"
        out["action"] = "IDLE"
        if not dry_run:
            _append_tick(out)
        return out

    out["active"] = True
    out["run_id"] = run.get("run_id")
    out["stage"] = run.get("stage")
    advice = bw.advise(run)
    out["next_action"] = advice["next_action"]
    action = advice["next_action"]

    if action == "IDLE":
        # Terminal run: attempt mission close_slice so DONE cannot stall the queue.
        cont = mission_continue_if_idle(dry_run=dry_run)
        if cont.get("action") in ("LAUNCH_NEXT", "CLOSE_SLICE", "RESUME_LANE"):
            out.update(cont)
        else:
            out["action"] = "IDLE"
            out["reason"] = "terminal_or_done"
            if cont.get("reason"):
                out["mission_idle_reason"] = cont.get("reason")
    elif action == "WAIT":
        out["action"] = "WAIT"
        out["reason"] = "child_alive"
    elif action == "ADVANCE":
        adv = ba.advance_once(run.get("run_id"), dry_run=dry_run)
        out["action"] = "ADVANCE"
        out["advanced"] = adv.get("advanced")
        out["stage_after"] = adv.get("stage_after")
        out["advance"] = adv
    elif action == "INSPECT":
        # Dead child, no EXIT / CURSOR_DONE. Recovery WAKE — not Matt.
        inspect_count = int(run.get("inspect_count") or 0)
        if inspect_count >= INSPECT_RETRY_CEILING:
            out["action"] = "ESCALATE"
            out["reason"] = "inspect_retry_ceiling"
            if not dry_run:
                run["stage"] = "BLOCKED"
                run["blocker"] = "FACTORY_FAILURE:inspect_retry_ceiling"
                run["final_state"] = "BLOCKED"
                _save_run(run)
                _write_wake(
                    {
                        "kind": "FACTORY_BLOCKED",
                        "run_id": run["run_id"],
                        "at": now_iso(),
                        "require_matt": False,
                        "instruction": (
                            "Inspect retry ceiling hit. Peaches must diagnose or park "
                            "and continue next safe lane. Do not wait for Matt status."
                        ),
                    }
                )
        else:
            out["action"] = "RECOVER_INSPECT"
            out["inspect_count"] = inspect_count + 1
            if not dry_run:
                run["inspect_count"] = inspect_count + 1
                run["last_inspect_at"] = now_iso()
                _save_run(run)
                _write_wake(
                    {
                        "kind": "FACTORY_INSPECT_RECOVER",
                        "run_id": run["run_id"],
                        "at": now_iso(),
                        "require_matt": False,
                        "inspect_count": run["inspect_count"],
                        "instruction": (
                            "Child dead without EXIT/CURSOR_DONE. Relaunch or mark "
                            "failed per recovery rules, then continue. Do not wait for Matt status."
                        ),
                    }
                )
    elif action in ("CONTINUE_PEACHES", "FINISH"):
        out["action"] = action
        if not dry_run:
            _write_wake(
                {
                    "kind": "FACTORY_CONTINUE",
                    "run_id": run["run_id"],
                    "stage": advice["stage"],
                    "at": now_iso(),
                    "require_matt": False,
                    "instruction": (
                        "Continue Grok review / Peaches verify / finish. "
                        "Do not wait for Matt status."
                    ),
                }
            )
    else:
        out["action"] = "UNKNOWN"
        out["reason"] = f"unhandled_next_action={action}"

    if not dry_run:
        _append_tick(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Calendar-free ACTIVE factory supervisor")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prove-calendar-free", action="store_true")
    args = ap.parse_args()
    if args.prove_calendar_free:
        print(json.dumps({"ok": True, "calendar_independent": calendar_independent()}))
        return 0 if calendar_independent() else 1
    # One tick at a time: launchd's 5-minute tick and the launcher's on-exit tick must not race.
    import fcntl
    lock_path = BF / "supervisor-tick.flock"
    with lock_path.open("w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(json.dumps({"ok": True, "action": "SKIP", "reason": "tick_in_progress"}))
            return 0
        print(json.dumps(tick(dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
