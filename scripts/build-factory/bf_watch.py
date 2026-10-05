#!/usr/bin/env python3
"""Read-only build-factory run inspector. Beta tooling only. No Wolf app writes.

Also surfaces ACTIVE_MISSION lane status from bf_queue when present.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
ACTIVE = BF / "ACTIVE"
RUNS = BF / "runs"

sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))
import bf_queue as bq  # noqa: E402


def load_run(run_id: str | None = None) -> dict | None:
    if run_id is None:
        if not ACTIVE.exists():
            return None
        run_id = ACTIVE.read_text(encoding="utf-8").strip()
    if not run_id:
        return None
    path = RUNS / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def log_exit_code(log_path: str | None) -> int | None:
    """Prefer explicit EXIT:N. CURSOR_DONE with process gone counts as EXIT:0."""
    if not log_path:
        return None
    p = Path(log_path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("EXIT:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def log_cursor_done(log_path: str | None) -> bool:
    if not log_path:
        return False
    p = Path(log_path)
    if not p.exists():
        return False
    return "CURSOR_DONE" in p.read_text(encoding="utf-8", errors="replace")




def credit_conservation_status() -> dict:
    """CREDIT_CONSERVATION_GATE_V1 — surface conservation for IDLE / arm decisions."""
    mode_path = BF / "CREDIT-CONSERVATION.json"
    gate_path = BF / "GATE-credit-conservation-20260923.json"
    mode = {}
    gate = {}
    if mode_path.exists():
        try:
            mode = json.loads(mode_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            mode = {}
    if gate_path.exists():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            gate = {}
    enabled = bool(mode.get("enabled")) or bool(gate.get("enabled"))
    return {
        "enabled": enabled,
        "mode": mode.get("mode") or ("CREDIT_CONSERVATION" if enabled else None),
        "veto_code": mode.get("veto_code")
        or gate.get("veto_code")
        or "PEACHES_VETO_CREDIT_CONSERVATION",
        "allow_finish_run_id": mode.get("allow_finish_run_id"),
        "auto_chain_operator_depth": bool(mode.get("auto_chain_operator_depth")),
        "auto_chain_management_depth": bool(mode.get("auto_chain_management_depth")),
        "auto_chain_connective": bool(mode.get("auto_chain_connective")),
        "idle_acceptable_when_only_breadth": bool(
            mode.get("idle_acceptable_when_only_breadth", True)
        ),
        "after_msc_policy": "RECOMPUTE_HIGHEST_VALUE_NO_AUTO_BREADTH",
        "veto_if_pack_class_in": gate.get("veto_if_pack_class_in")
        or ["operator-depth", "management-depth", "connective"],
    }


def _dispatch_queue() -> dict:
    path = BF / "GOD-MODE-DISPATCH.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def named_queue_exempt(pack_hint: str | None = None) -> bool:
    """Owner 5 Oct 2026 06:24 WITA God Mode queue is not a credit-conservation veto."""
    hint = (pack_hint or "").lower().replace("_", "-")
    if not hint:
        queue = _dispatch_queue()
        return any(
            (it.get("state") == "READY" and it.get("auto_arm") is not False and it.get("exempt_from_credit_veto"))
            for it in (queue.get("items") or [])
        )
    breadth = ("tour", "event", "operator-depth", "management-depth", "connective")
    rebuild = ("recipe-builder", "recipe builder", "daily-close", "daily close", "petty-cash", "petty cash", "bzg-p2p-po-1")
    if any(tok in hint for tok in breadth) or any(tok in hint for tok in rebuild):
        return False
    ids = [
        "ggv-bills-605",
        "bzg-p2p-recv-1",
        "bzg-p2p-nota-bill-1",
        "bzg-p2p-three-way-1",
        "bzg-p2p-ap-1",
        "bzg-p2p-ready-to-pay-1",
        "owner-home-factory-indicator",
        "finance-testable-slice",
    ]
    for it in (_dispatch_queue().get("items") or []):
        if it.get("exempt_from_credit_veto") and it.get("id"):
            ids.append(str(it["id"]).lower())
    return any(item_id in hint or hint in item_id for item_id in ids)


def breadth_arm_blocked(pack_hint: str | None = None) -> dict:
    """True when conservation enabled and hint is breadth without allow_finish.

    Named God Mode queue items are exempt. Tours/Events and other breadth stay blocked.
    """
    cc = credit_conservation_status()
    if not cc["enabled"]:
        return {"blocked": False, "enabled": False}
    if named_queue_exempt(pack_hint):
        return {"blocked": False, "enabled": True, "reason": "named_god_mode_queue_exempt"}
    hint = (pack_hint or "").lower()
    classes = [c.lower().replace("_", "-") for c in (cc.get("veto_if_pack_class_in") or [])]
    is_breadth = any(c in hint for c in classes) or any(
        tok in hint for tok in ("operator-depth", "management-depth", "connective")
    )
    allow = cc.get("allow_finish_run_id") or ""
    if allow and allow.lower() in hint:
        return {"blocked": False, "enabled": True, "reason": "allow_finish_exception"}
    if not is_breadth:
        return {"blocked": False, "enabled": True, "reason": "not_breadth"}
    if cc.get("auto_chain_operator_depth") or cc.get("auto_chain_management_depth") or cc.get(
        "auto_chain_connective"
    ):
        return {"blocked": False, "enabled": True, "reason": "auto_chain_flag_true"}
    return {
        "blocked": True,
        "enabled": True,
        "veto_code": cc["veto_code"],
        "reason": "PEACHES_VETO_CREDIT_CONSERVATION",
    }

def advise(run: dict) -> dict:
    stage = run.get("stage") or "UNKNOWN"
    pid = run.get("cursor_pid") or run.get("child_pid")
    log_path = run.get("cursor_log") or run.get("child_log")
    alive = pid_alive(int(pid)) if pid else False
    exit_code = log_exit_code(log_path)
    cursor_done = log_cursor_done(log_path)
    # CLAIMED≠VERIFIED: process gone + (EXIT line OR CURSOR_DONE) = child_done
    # Historical defect 2026-09-17: CURSOR_DONE without EXIT forced INSPECT forever.
    if exit_code is None and cursor_done and (not alive):
        exit_code = 0
    child_done = (not alive) and (exit_code is not None)

    next_action = "WAIT"
    if run.get("final_state") in ("DONE", "BLOCKED", "FAILED"):
        next_action = "IDLE"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and child_done:
        next_action = "ADVANCE"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and alive:
        next_action = "WAIT"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and (not alive) and exit_code is None:
        next_action = "INSPECT"  # process gone, no EXIT and no CURSOR_DONE
    elif stage in ("GROK_REVIEW", "GROK_REREVIEW", "PEACHES_VERIFY", "GROK_PLAN"):
        next_action = "CONTINUE_PEACHES"
    elif stage == "REPORT":
        next_action = "FINISH"

    cc = credit_conservation_status()
    slice_hint = run.get("slice") or ""
    # Slice-local exemption only. A ready named item must not exempt an unrelated breadth run.
    exempt = named_queue_exempt(slice_hint)
    if not cc.get("enabled"):
        breadth_arm = "N/A"
    elif exempt:
        breadth_arm = "NAMED_QUEUE_EXEMPT"
    elif next_action in ("IDLE", "FINISH") and not named_queue_exempt(None):
        breadth_arm = "BLOCKED_PEACHES_VETO_CREDIT_CONSERVATION"
    elif named_queue_exempt(None):
        breadth_arm = "NAMED_QUEUE_EXEMPT"
    else:
        breadth_arm = "ALLOW_FINISH_ONLY"
    # Supervisor launches. wake_parent stays false so a second watcher does not also start a cursor.
    # stopped is false whenever named READY work exists, which is the old IDLE defect.
    return {
        "run_id": run.get("run_id"),
        "slice": run.get("slice"),
        "stage": stage,
        "child_alive": alive,
        "exit_code": exit_code,
        "cursor_done": cursor_done,
        "child_done": child_done,
        "next_action": next_action,
        "blocker": run.get("blocker"),
        "head_commit": run.get("head_commit"),
        "updated_at": run.get("updated_at"),
        "credit_conservation": cc,
        "next_breadth_arm": breadth_arm,
        "wake_parent": False,
        "stopped": not (exempt or named_queue_exempt(None)),
        "require_matt": False,
    }


def advise_mission(mission_id: str | None = None) -> dict:
    """Read-only mission/lane advise from persisted file."""
    mid = mission_id or bq.read_active_mission_id(BF)
    if not mid:
        return {"ok": True, "active_mission": False, "next_action": "IDLE"}
    mission = bq.load_mission(mid, BF / "missions")
    if not mission:
        return {"ok": True, "active_mission": False, "stale_pointer": True, "mission_id": mid}
    nxt = bq.next_runnable_lane(mission)
    aid = mission.get("active_lane_id")
    active = bq.get_lane(mission, aid) if aid else None
    return {
        "ok": True,
        "active_mission": True,
        "mission_id": mid,
        "mission_status": mission.get("status"),
        "active_lane_id": aid,
        "active_lane_status": active["status"] if active else None,
        "next_lane_id": nxt["id"] if nxt else None,
        "next_action": "RESUME" if active and active["status"] not in bq.TERMINAL_LANE else (
            "CLOSE_SLICE" if nxt else "IDLE"
        ),
        "retry_ceiling": bq.RETRY_CEILING,
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--mission":
        mid = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(advise_mission(mid), indent=2))
        return 0
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    run = load_run(run_id)
    if not run:
        miss = advise_mission()
        if miss.get("active_mission"):
            print(json.dumps(miss, indent=2))
            return 0
        cc = credit_conservation_status()
        exempt = named_queue_exempt(None)
        print(json.dumps({
            "ok": True,
            "active": False,
            "next_action": "IDLE",
            "credit_conservation": cc,
            "next_breadth_arm": "NAMED_QUEUE_EXEMPT" if exempt else (
                "BLOCKED_PEACHES_VETO_CREDIT_CONSERVATION" if cc.get("enabled") else "N/A"
            ),
            "wake_parent": False,
            "stopped": not exempt,
            "dispatch_owner": "bf_supervisor",
            "require_matt": False,
        }))
        return 0
    out = {"ok": True, "active": True, **advise(run)}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
