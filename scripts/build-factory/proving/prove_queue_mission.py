#!/usr/bin/env python3
"""Harmless Beta proving mission for the lane queue. Not business commissioning.

Lane A: first Grok FAIL, second attempt PASS (synthetic in-process).
Lane B: BLOCKED by synthetic proving condition.
Lane C: authorised harmless lane runs automatically despite B.
Then restart/resume and prove completed lanes are not re-run.

No maturity credit. No Production. No external writes.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bf_queue as bq


def run_proof(persist_dir: Path) -> dict:
    bq.BF = persist_dir
    bq.MISSIONS = persist_dir / "missions"
    bq.ACTIVE_MISSION = persist_dir / "ACTIVE_MISSION"

    mid = "BF-PROVE-QUEUE-2026-09-18"
    mission = bq.new_mission(
        mid,
        [
            {"id": "A", "bound": "beta-harmless-prove"},
            {"id": "B", "bound": "beta-harmless-prove"},
            {"id": "C", "bound": "beta-harmless-prove"},
        ],
        title="factory-queue-proving",
    )
    results = {"steps": []}

    # Start A
    r = bq.close_slice(mission)
    results["steps"].append({"close_start_A": r})
    assert r.get("lane_id") == "A" and r.get("started")

    # Cursor done → Grok FAIL (first)
    bq.advance_cursor_done(mission, "A", event_id="prove-cd-1")
    r = bq.apply_grok_result(mission, "A", "FAIL", event_id="prove-fail-1")
    results["steps"].append({"A_first_fail": r})
    assert r.get("status") == bq.LANE_WAITING_CURSOR_FIX and r.get("retry_count") == 1

    # Fix attempt → PASS
    bq.advance_cursor_done(mission, "A", event_id="prove-cd-2")
    r = bq.apply_grok_result(
        mission, "A", "PASS", event_id="prove-pass-A", completion_commit="prove-A-ok"
    )
    results["steps"].append({"A_pass": r})
    assert r.get("status") == bq.LANE_COMPLETED

    # Block B synthetically, then close_slice should start C
    bq.mark_blocked(mission, "B", "synthetic_proving_condition")
    results["steps"].append({"B_blocked": mission["lanes"][1]["block_reason"]})

    r = bq.close_slice(mission)
    results["steps"].append({"close_start_C": r})
    assert r.get("lane_id") == "C" and r.get("started"), r

    bq.advance_cursor_done(mission, "C", event_id="prove-cd-C")
    r = bq.apply_grok_result(
        mission, "C", "PASS", event_id="prove-pass-C", completion_commit="prove-C-ok"
    )
    results["steps"].append({"C_pass": r})

    bq.save_mission(mission, bq.MISSIONS)
    bq.set_active_mission(mid, persist_dir)

    # Restart mid-mission (all A/C done, B blocked) — must not re-run A or C
    rr = bq.restart_mission(mid, bq.MISSIONS)
    mission2 = rr["mission"]
    start_a = bq.start_lane(mission2, "A")
    start_c = bq.start_lane(mission2, "C")
    results["steps"].append({"restart": rr["lanes"], "start_A": start_a, "start_C": start_c})

    assert start_a.get("reason") == "already_completed"
    assert start_c.get("reason") == "already_completed"
    assert mission2["lanes"][0]["completion_commit"] == "prove-A-ok"
    assert mission2["lanes"][2]["completion_commit"] == "prove-C-ok"
    assert mission2["lanes"][1]["status"] == bq.LANE_BLOCKED

    # Idle after close
    idle = bq.close_slice(mission2)
    results["steps"].append({"final_close": idle})
    results["ok"] = True
    results["mission_id"] = mid
    results["final_lanes"] = [
        {
            "id": ln["id"],
            "status": ln["status"],
            "completion_commit": ln.get("completion_commit"),
            "block_reason": ln.get("block_reason"),
            "retry_count": ln.get("retry_count"),
        }
        for ln in mission2["lanes"]
    ]
    return results


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = run_proof(Path(tmp))
    print(json.dumps(out, indent=2))
    print("PROVING_MISSION: PASS" if out.get("ok") else "PROVING_MISSION: FAIL")
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
