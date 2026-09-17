#!/usr/bin/env python3
"""Build-factory advance state machine — overnight stall regression. CLAIMED ≠ VERIFIED."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))

import bf_watch as bw
import bf_advance as ba

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def write_run(td: Path, run: dict) -> Path:
    runs = td / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    p = runs / f"{run['run_id']}.json"
    p.write_text(json.dumps(run, indent=2))
    (td / "ACTIVE").write_text(run["run_id"])
    return p


def main() -> int:
    global PASS, FAIL
    # Monkeypatch paths into temp
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        bw.BF = td
        bw.ACTIVE = td / "ACTIVE"
        bw.RUNS = td / "runs"
        ba.BF = td
        ba.RUNS = td / "runs"
        ba.ACTIVE = td / "ACTIVE"
        ba.WAKE = td / "WAKE.json"
        ba.bw = bw

        log = td / "cursor.log"
        log.write_text("working...\nCURSOR_DONE\n`abc123` fix\n**Tests:** 1 passed\n")

        run = {
            "run_id": "BF-test-stall",
            "slice": "harmless",
            "stage": "WAITING_CURSOR",
            "cursor_pid": 999999999,  # not alive
            "cursor_log": str(log),
            "updated_at": "2026-09-17T13:55:00Z",
        }
        write_run(td, run)

        # 1) CURSOR_DONE without EXIT advances (regression for overnight stall)
        advice = bw.advise(json.loads((td / "runs/BF-test-stall.json").read_text()))
        # pid 999999999 not alive
        check("CURSOR_DONE without EXIT → child_done", advice["child_done"] is True, str(advice))
        check("CURSOR_DONE without EXIT → ADVANCE", advice["next_action"] == "ADVANCE", str(advice))

        # 2) dry-run advance
        out = ba.advance_once("BF-test-stall", dry_run=True)
        check("dry-run would advance", out["advanced"] is True and out["stage_after"] == "GROK_REVIEW")

        # 3) real advance persists GROK_REVIEW + WAKE
        out = ba.advance_once("BF-test-stall", dry_run=False)
        check("advance applied", out["advanced"] is True)
        saved = json.loads((td / "runs/BF-test-stall.json").read_text())
        check("stage GROK_REVIEW persisted", saved["stage"] == "GROK_REVIEW", saved.get("stage"))
        wake = json.loads((td / "WAKE.json").read_text())
        check("WAKE require_matt false", wake.get("require_matt") is False)
        check("WAKE to GROK_REVIEW", wake.get("to_stage") == "GROK_REVIEW")

        # 4) idempotent — already GROK_REVIEW does not re-advance from WAITING
        out2 = ba.advance_once("BF-test-stall", dry_run=False)
        check("no duplicate advance from GROK_REVIEW", out2["advanced"] is False)

        # 5) EXIT:1 still child_done (failed child still advances to review/inspect path)
        log2 = td / "cursor-fail.log"
        log2.write_text("boom\nEXIT:1\n")
        run2 = {
            "run_id": "BF-test-fail",
            "stage": "WAITING_CURSOR",
            "cursor_pid": 999999998,
            "cursor_log": str(log2),
        }
        write_run(td, run2)
        adv2 = bw.advise(run2)
        check("EXIT:1 → child_done", adv2["child_done"] and adv2["exit_code"] == 1)
        check("EXIT:1 → ADVANCE", adv2["next_action"] == "ADVANCE")

        # 6) alive process → WAIT
        run3 = {
            "run_id": "BF-test-live",
            "stage": "WAITING_CURSOR",
            "cursor_pid": os.getpid(),  # self = alive
            "cursor_log": str(log),
        }
        write_run(td, run3)
        adv3 = bw.advise(run3)
        check("alive → WAIT", adv3["next_action"] == "WAIT" and adv3["child_alive"] is True)

        # 7) human-blocked / DONE idle
        run4 = {"run_id": "BF-done", "stage": "REPORT", "final_state": "DONE"}
        write_run(td, run4)
        adv4 = bw.advise(run4)
        check("DONE → IDLE", adv4["next_action"] == "IDLE")

        # 8) process gone, no EXIT, no CURSOR_DONE → INSPECT
        empty = td / "empty.log"
        empty.write_text("still starting...\n")
        run5 = {
            "run_id": "BF-inspect",
            "stage": "WAITING_CURSOR",
            "cursor_pid": 999999997,
            "cursor_log": str(empty),
        }
        write_run(td, run5)
        adv5 = bw.advise(run5)
        check("no marker → INSPECT", adv5["next_action"] == "INSPECT", str(adv5))

    print(f"\nFACTORY ADVANCE RESULT: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
