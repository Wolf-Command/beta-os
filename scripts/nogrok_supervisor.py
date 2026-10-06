#!/usr/bin/env python3
"""Restart-safe supervisor for the non-Grok control plane.

Pid plus lease. A dead pid is replaced and stale RUNNING rows are reaped.
This process does not shell out to a model, a metered API, or a blocked worker.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from core import nogrok_control as control


def _pid_path(root: Path | None) -> Path:
    return control.state_dir(root) / "supervisor.pid"


def _lease_path(root: Path | None) -> Path:
    return control.state_dir(root) / "supervisor.json"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_pid(root: Path | None) -> int:
    path = _pid_path(root)
    if not path.is_file():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def supervisor_alive(root: Path | None) -> bool:
    return pid_alive(read_pid(root))


def acquire(root: Path | None = None) -> bool:
    """Take the pid if nobody live holds it. Reap first so a crash cannot leave RUNNING."""
    control.tick(root)
    if supervisor_alive(root):
        return False
    directory = control.state_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    _pid_path(root).write_text(str(os.getpid()) + "\n", encoding="utf-8")
    _lease_path(root).write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "held_at": control._iso(),
                "worker": control.LOCAL_WORKER,
                "invokes_models": False,
                "production_mutation": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    control.hold_local(root)
    return True


def release(root: Path | None = None) -> None:
    path = _pid_path(root)
    if path.is_file() and read_pid(root) == os.getpid():
        path.unlink()
    lease = _lease_path(root)
    if lease.is_file():
        try:
            data = json.loads(lease.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if data.get("pid") == os.getpid():
            lease.unlink()


def tick_once(root: Path | None = None) -> dict:
    if not supervisor_alive(root) or read_pid(root) == os.getpid():
        acquire(root)
    return control.hold_local(root)


def serve(root: Path | None = None, *, interval: float = 30.0) -> None:
    if not acquire(root):
        return
    try:
        while True:
            if read_pid(root) != os.getpid():
                return
            control.hold_local(root)
            time.sleep(interval)
    finally:
        release(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local non-Grok supervisor")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--state", default="")
    args = parser.parse_args(argv)
    root = Path(args.state) if args.state else None
    if args.once:
        if supervisor_alive(root) and read_pid(root) != os.getpid():
            print(json.dumps({"ok": True, "started": False, "reason": "already_running"}))
            return 0
        state = tick_once(root)
        print(
            json.dumps(
                {
                    "ok": True,
                    "started": True,
                    "pid": os.getpid(),
                    "human_commissioned": False,
                    "running": [item.get("id") for item in control.running_items(state)],
                }
            )
        )
        return 0
    if supervisor_alive(root):
        print(json.dumps({"ok": True, "started": False, "reason": "already_running", "pid": read_pid(root)}))
        return 0
    serve(root, interval=args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
