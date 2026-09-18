#!/usr/bin/env python3
"""Calendar-free factory supervisor proofs. Beta only."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))
sys.path.insert(0, str(ROOT / "scripts"))

import bf_supervisor as sup  # noqa: E402
import bf_watch as bw  # noqa: E402
import bf_advance as ba  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name} :: {detail}")


def with_temp_bf(fn):
    """Point BF paths at a temp dir for isolated proofs."""
    tmp = Path(tempfile.mkdtemp(prefix="bf-sup-"))
    runs = tmp / "runs"
    runs.mkdir(parents=True)
    old = {
        "BF": (sup, "BF"),
        "ACTIVE": (sup, "ACTIVE"),
        "WAKE": (sup, "WAKE"),
        "TICKS": (sup, "TICKS"),
        "bw_BF": (bw, "BF"),
        "bw_ACTIVE": (bw, "ACTIVE"),
        "bw_RUNS": (bw, "RUNS"),
        "ba_BF": (ba, "BF"),
        "ba_ACTIVE": (ba, "ACTIVE"),
        "ba_RUNS": (ba, "RUNS"),
        "ba_WAKE": (ba, "WAKE"),
    }
    try:
        for _, (mod, attr) in old.items():
            pass
        # rebind
        for mod, mapping in (
            (sup, {"BF": tmp, "ACTIVE": tmp / "ACTIVE", "WAKE": tmp / "WAKE.json", "TICKS": tmp / "supervisor-ticks.jsonl"}),
            (bw, {"BF": tmp, "ACTIVE": tmp / "ACTIVE", "RUNS": runs}),
            (ba, {"BF": tmp, "ACTIVE": tmp / "ACTIVE", "RUNS": runs, "WAKE": tmp / "WAKE.json"}),
        ):
            for k, v in mapping.items():
                setattr(mod, k, v)
        return fn(tmp, runs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def seed_run(runs: Path, active: Path, *, stage: str, log_text: str, pid: int | None, run_id="BF-test") -> Path:
    log = runs / f"{run_id}.log"
    log.write_text(log_text, encoding="utf-8")
    run = {
        "run_id": run_id,
        "slice": "supervisor-prove",
        "stage": stage,
        "cursor_log": str(log),
        "cursor_pid": pid,
        "child_log": str(log),
        "child_pid": pid,
        "approved_scope": "harmless",
    }
    path = runs / f"{run_id}.json"
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    active.write_text(run_id + "\n", encoding="utf-8")
    return path


def main() -> int:
    check("supervisor source has no runtime calendar gate", sup.calendar_independent())

    # inactive → IDLE
    def inactive(tmp, runs):
        out = sup.tick(dry_run=False)
        check("inactive mission does NOT spuriously advance", out["action"] == "IDLE" and out["active"] is False, str(out))
        check("inactive require_matt false", out.get("require_matt") is False)
        check("inactive calendar_gate false", out.get("calendar_gate") is False)
    with_temp_bf(inactive)

    # EXIT 0 advances
    def exit0(tmp, runs):
        seed_run(runs, tmp / "ACTIVE", stage="WAITING_CURSOR", log_text="CURSOR_DONE\nEXIT:0\n", pid=None)
        out = sup.tick(dry_run=False)
        check("EXIT 0 advances", out.get("action") == "ADVANCE" and out.get("advanced") is True, str(out))
        run = json.loads((runs / "BF-test.json").read_text())
        check("stage becomes GROK_REVIEW", run.get("stage") == "GROK_REVIEW", str(run.get("stage")))
        wake = json.loads((tmp / "WAKE.json").read_text())
        check("WAKE require_matt false after EXIT0", wake.get("require_matt") is False)
        # idempotent
        out2 = sup.tick(dry_run=False)
        check("restart/idempotent — no second ADVANCE from GROK_REVIEW", out2.get("action") in ("CONTINUE_PEACHES", "WAIT", "UNKNOWN") or out2.get("advanced") is not True, str(out2))
    with_temp_bf(exit0)

    # CURSOR_DONE without EXIT
    def cursor_done(tmp, runs):
        seed_run(runs, tmp / "ACTIVE", stage="WAITING_CURSOR", log_text="work\nCURSOR_DONE\n", pid=None)
        out = sup.tick(dry_run=False)
        check("CURSOR_DONE dead advances", out.get("action") == "ADVANCE" and out.get("advanced") is True, str(out))
    with_temp_bf(cursor_done)

    # dead / no-exit → RECOVER_INSPECT
    def inspect(tmp, runs):
        seed_run(runs, tmp / "ACTIVE", stage="WAITING_CURSOR", log_text="CURSOR_START only\n", pid=None)
        out = sup.tick(dry_run=False)
        check("dead/no-exit detected as RECOVER_INSPECT", out.get("action") == "RECOVER_INSPECT", str(out))
        wake = json.loads((tmp / "WAKE.json").read_text())
        check("inspect WAKE require_matt false", wake.get("require_matt") is False)
        check("inspect WAKE kind", wake.get("kind") == "FACTORY_INSPECT_RECOVER", str(wake))
        last = out
        for _ in range(sup.INSPECT_RETRY_CEILING + 3):
            run = json.loads((runs / "BF-test.json").read_text())
            if run.get("final_state") == "BLOCKED":
                break
            run["stage"] = "WAITING_CURSOR"
            run.pop("final_state", None)
            (runs / "BF-test.json").write_text(json.dumps(run, indent=2) + "\n")
            (tmp / "ACTIVE").write_text("BF-test\n")
            last = sup.tick(dry_run=False)
            if last.get("action") == "ESCALATE":
                break
        check("retry ceiling stops repeated inspect", last.get("action") == "ESCALATE", str(last))
        run = json.loads((runs / "BF-test.json").read_text())
        check("ceiling marks BLOCKED", run.get("final_state") == "BLOCKED", str(run))
    with_temp_bf(inspect)

    # Saturday / Sunday / weekday — same code path (no calendar input)
    def weekend_paths(tmp, runs):
        seed_run(runs, tmp / "ACTIVE", stage="WAITING_CURSOR", log_text="EXIT:0\n", pid=None)
        # Simulate three "days" by repeating ticks; calendar never consulted.
        results = []
        for label in ("saturday", "sunday", "weekday"):
            # reset
            seed_run(runs, tmp / "ACTIVE", stage="WAITING_CURSOR", log_text="EXIT:0\nCURSOR_DONE\n", pid=None)
            out = sup.tick(dry_run=False)
            results.append((label, out.get("action"), out.get("advanced"), out.get("calendar_gate")))
        check("Saturday active mission advances", results[0][1] == "ADVANCE" and results[0][2] is True, str(results[0]))
        check("Sunday active mission advances", results[1][1] == "ADVANCE" and results[1][2] is True, str(results[1]))
        check("weekday still advances", results[2][1] == "ADVANCE" and results[2][2] is True, str(results[2]))
        check("no calendar_gate on any day", all(r[3] is False for r in results), str(results))
    with_temp_bf(weekend_paths)

    # Matt prompt is not an input — tick signature has no owner_prompt
    import inspect as ins
    sig = str(ins.signature(sup.tick))
    check("Matt prompt is not an input to tick()", "matt" not in sig.lower() and "status" not in sig.lower() and "owner" not in sig.lower(), sig)

    # LaunchAgent plist has no Weekday / calendar keys
    plist = (ROOT / "scripts/build-factory/launchd/net.wolfcommand.build-factory-supervisor.plist").read_text()
    check("LaunchAgent has StartInterval", "StartInterval" in plist)
    check("LaunchAgent has no Weekday calendar", "Weekday" not in plist and "Month" not in plist and "Day" not in plist.split("StartInterval")[0])

    # blocked lane alternate — use bf_queue
    import bf_queue as bq
    mid = "MIS-sup-prove"
    mission = bq.new_mission(
        mid,
        [
            {"id": "L1", "bound": "beta-docs"},
            {"id": "L2", "bound": "beta-docs"},
        ],
    )
    # start L1 then block, close_slice should start L2
    bq.start_lane(mission, "L1")
    bq.mark_blocked(mission, "L1", "policy")
    out = bq.close_slice(mission)
    check("blocked lane allows alternate safe lane", out.get("started") == "L2" or (mission.get("active_lane_id") == "L2"), str(out) + str(mission.get("active_lane_id")))

    print(f"\nSUPERVISOR RESULT: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
