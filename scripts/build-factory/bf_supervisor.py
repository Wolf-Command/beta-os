#!/usr/bin/env python3
"""Active-mission factory supervisor. Beta tooling only.

Invariant: ACTIVE MISSION → advancement available regardless of calendar.
Matt status is not an input. Quiet when inactive.

Does NOT invent Cursor work. Does NOT touch Production.
Deterministic stage advance + recovery WAKE only.
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
    }

    if not ACTIVE.exists() or not ACTIVE.read_text(encoding="utf-8").strip():
        out["reason"] = "no_active_run"
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
        out["action"] = "IDLE"
        out["reason"] = "terminal_or_done"
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
    print(json.dumps(tick(dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
