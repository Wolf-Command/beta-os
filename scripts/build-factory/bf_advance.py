#!/usr/bin/env python3
"""Deterministic build-factory stage advance. Beta tooling only.

Invariant: authorised WAITING_CURSOR → GROK_REVIEW must not require Matt "status".

Does NOT run Grok/Cursor itself — only persists the next stage so Peaches/watch
can continue without Owner prompt. Idempotent.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
RUNS = BF / "runs"
ACTIVE = BF / "ACTIVE"
WAKE = BF / "WAKE.json"

# Import advise helpers from bf_watch
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))
import bf_watch as bw  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_wake(payload: dict) -> None:
    WAKE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def save_run(run: dict) -> Path:
    path = RUNS / f"{run['run_id']}.json"
    run["updated_at"] = now_iso()
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return path


def advance_once(run_id: str | None = None, dry_run: bool = False) -> dict:
    run = bw.load_run(run_id)
    if not run:
        return {"ok": True, "advanced": False, "reason": "no_active_run"}
    advice = bw.advise(run)
    stage = advice["stage"]
    action = advice["next_action"]
    out = {
        "ok": True,
        "run_id": run["run_id"],
        "stage_before": stage,
        "next_action": action,
        "advanced": False,
        "dry_run": dry_run,
    }

    if action == "ADVANCE" and stage in (
        "WAITING_CURSOR",
        "WAITING_CURSOR_FIX",
        "WAITING_HARMLESS_JOB",
    ):
        # Do not re-advance if already past
        new_stage = "GROK_REVIEW"
        out["stage_after"] = new_stage
        out["advanced"] = True
        if not dry_run:
            run["stage"] = new_stage
            if advice.get("exit_code") is not None:
                run["child_exit_code"] = advice["exit_code"]
            run["advance_reason"] = "cursor_child_done_auto"
            save_run(run)
            write_wake(
                {
                    "kind": "FACTORY_ADVANCE",
                    "run_id": run["run_id"],
                    "from_stage": stage,
                    "to_stage": new_stage,
                    "at": now_iso(),
                    "require_matt": False,
                    "instruction": "Continue Grok actual-diff review then Peaches verify; do not wait for Matt status.",
                }
            )
        return out

    out["stage_after"] = stage
    out["reason"] = f"no_auto_advance_for_action={action}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    print(json.dumps(advance_once(args.run_id, dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
