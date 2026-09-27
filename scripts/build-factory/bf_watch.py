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


def breadth_arm_blocked(pack_hint: str | None = None) -> dict:
    """True when conservation enabled and hint is breadth without allow_finish."""
    cc = credit_conservation_status()
    if not cc["enabled"]:
        return {"blocked": False, "enabled": False}
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
        "next_breadth_arm": "BLOCKED_PEACHES_VETO_CREDIT_CONSERVATION"
        if cc.get("enabled")
        and not (
            (run.get("run_id") or "") == (cc.get("allow_finish_run_id") or "")
            and next_action in ("CONTINUE_PEACHES", "ADVANCE", "FINISH", "WAIT")
        )
        and next_action in ("IDLE", "FINISH")
        else ("ALLOW_FINISH_ONLY" if cc.get("enabled") else "N/A"),
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
        print(json.dumps({"ok": True, "active": False, "next_action": "IDLE", "credit_conservation": credit_conservation_status(), "next_breadth_arm": "BLOCKED_PEACHES_VETO_CREDIT_CONSERVATION" if credit_conservation_status().get("enabled") else "N/A"}))
        return 0
    out = {"ok": True, "active": True, **advise(run)}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
