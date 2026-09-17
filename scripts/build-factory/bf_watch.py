#!/usr/bin/env python3
"""Read-only build-factory run inspector. Beta tooling only. No Wolf app writes."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
ACTIVE = BF / "ACTIVE"
RUNS = BF / "runs"


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


def advise(run: dict) -> dict:
    stage = run.get("stage") or "UNKNOWN"
    pid = run.get("cursor_pid") or run.get("child_pid")
    log_path = run.get("cursor_log") or run.get("child_log")
    alive = pid_alive(int(pid)) if pid else False
    exit_code = log_exit_code(log_path)
    child_done = (not alive) and (exit_code is not None)

    next_action = "WAIT"
    if run.get("final_state") in ("DONE", "BLOCKED", "FAILED"):
        next_action = "IDLE"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and child_done:
        next_action = "ADVANCE"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and alive:
        next_action = "WAIT"
    elif stage in ("WAITING_CURSOR", "WAITING_CURSOR_FIX", "WAITING_HARMLESS_JOB") and (not alive) and exit_code is None:
        next_action = "INSPECT"  # process gone but no EXIT line yet
    elif stage in ("GROK_REVIEW", "GROK_REREVIEW", "PEACHES_VERIFY", "GROK_PLAN"):
        next_action = "CONTINUE_PEACHES"
    elif stage == "REPORT":
        next_action = "FINISH"

    return {
        "run_id": run.get("run_id"),
        "slice": run.get("slice"),
        "stage": stage,
        "child_alive": alive,
        "exit_code": exit_code,
        "child_done": child_done,
        "next_action": next_action,
        "blocker": run.get("blocker"),
        "head_commit": run.get("head_commit"),
        "updated_at": run.get("updated_at"),
    }


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    run = load_run(run_id)
    if not run:
        print(json.dumps({"ok": True, "active": False, "next_action": "IDLE"}))
        return 0
    out = {"ok": True, "active": True, **advise(run)}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
