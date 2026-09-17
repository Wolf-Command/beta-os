#!/usr/bin/env python3
"""Build-factory deterministic lane queue — required cases. No network. CLAIMED ≠ VERIFIED."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))

import bf_queue as bq

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


def fresh(td: Path, lanes=None, mid="M-test") -> dict:
    bq.BF = td
    bq.MISSIONS = td / "missions"
    bq.ACTIVE_MISSION = td / "ACTIVE_MISSION"
    lanes = lanes or [
        {"id": "A", "bound": "beta-harmless"},
        {"id": "B", "bound": "beta-harmless"},
        {"id": "C", "bound": "beta-harmless"},
    ]
    m = bq.new_mission(mid, lanes, title="queue-test")
    bq.save_mission(m, bq.MISSIONS)
    bq.set_active_mission(mid, td)
    return m


def main() -> int:
    global PASS, FAIL

    # --- guard function ---
    g_ok = bq.guard_lane_bound("beta-harmless")
    check("guard allows beta-harmless", g_ok["allowed"] is True)
    g_prod = bq.guard_lane_bound("production")
    check("guard refuses production", g_prod["allowed"] is False and "production" in g_prod["reason"])
    g_ext = bq.guard_lane_bound("external-write")
    check("guard refuses external-write", g_ext["allowed"] is False)
    g_own = bq.guard_lane_bound("owner-authority")
    check("guard refuses owner-authority", g_own["allowed"] is False)

    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)

        # 1) normal Cursor PASS lifecycle
        m = fresh(td / "t1", mid="M-cursor-pass")
        r = bq.close_slice(m)
        check("cursor_pass: starts A", r.get("started") and r.get("lane_id") == "A", str(r))
        check("cursor_pass: WAITING_CURSOR", m["lanes"][0]["status"] == bq.LANE_WAITING_CURSOR)
        r = bq.advance_cursor_done(m, "A", event_id="cd1")
        check("cursor_pass: → GROK_REVIEW", r.get("advanced") and m["lanes"][0]["status"] == bq.LANE_GROK_REVIEW)
        r = bq.apply_grok_result(m, "A", "PASS", event_id="gp1", completion_commit="cA1")
        check("cursor_pass: COMPLETED", r.get("applied") and m["lanes"][0]["status"] == bq.LANE_COMPLETED)
        check("cursor_pass: commit recorded", m["lanes"][0]["completion_commit"] == "cA1")

        # 2) Grok PASS lifecycle (alias path already covered; explicit)
        m = fresh(td / "t2", mid="M-grok-pass")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        r = bq.apply_grok_result(m, "A", "PASS", event_id="pass1", completion_commit="gA")
        check("grok_pass lifecycle", r["status"] == bq.LANE_COMPLETED and r["completion_commit"] == "gA")

        # 3) Grok FAIL then Cursor fix
        m = fresh(td / "t3", mid="M-fail-fix")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        r = bq.apply_grok_result(m, "A", "FAIL", event_id="fail1")
        check(
            "grok_fail → WAITING_CURSOR_FIX",
            r.get("status") == bq.LANE_WAITING_CURSOR_FIX and r.get("retry_count") == 1,
            str(r),
        )
        bq.advance_cursor_done(m, "A", event_id="cd-fix")
        r = bq.apply_grok_result(m, "A", "PASS", event_id="pass-after-fix", completion_commit="cFix")
        check("fix then pass", m["lanes"][0]["status"] == bq.LANE_COMPLETED and m["lanes"][0]["retry_count"] == 1)

        # 4) repeated Grok FAIL until retry ceiling
        m = fresh(td / "t4", mid="M-ceiling")
        bq.close_slice(m)
        # attempt 1 fail → retry 1
        bq.advance_cursor_done(m, "A", event_id="cd0")
        r1 = bq.apply_grok_result(m, "A", "FAIL", event_id="f0")
        check("ceiling: retry_count=1", r1.get("retry_count") == 1 and r1.get("status") == bq.LANE_WAITING_CURSOR_FIX)
        # attempt 2 fail → retry 2
        bq.advance_cursor_done(m, "A", event_id="cd1")
        r2 = bq.apply_grok_result(m, "A", "FAIL", event_id="f1")
        check("ceiling: retry_count=2", r2.get("retry_count") == 2 and r2.get("status") == bq.LANE_WAITING_CURSOR_FIX)
        # attempt 3 fail → escalated (retries already at ceiling)
        bq.advance_cursor_done(m, "A", event_id="cd2")
        r3 = bq.apply_grok_result(m, "A", "FAIL", event_id="f2")
        check(
            "ceiling: ESCALATED no loop",
            r3.get("status") == bq.LANE_ESCALATED and "retry_ceiling" in (r3.get("escalation_reason") or ""),
            str(r3),
        )
        # other lanes may continue
        r = bq.close_slice(m)
        check("ceiling: B still starts", r.get("started") and r.get("lane_id") == "B", str(r))

        # idempotency: same FAIL event does not increment past ceiling
        m2 = fresh(td / "t4b", mid="M-ceiling-idemp")
        bq.close_slice(m2)
        bq.advance_cursor_done(m2, "A", event_id="cd")
        bq.apply_grok_result(m2, "A", "FAIL", event_id="same-fail")
        r_dup = bq.apply_grok_result(m2, "A", "FAIL", event_id="same-fail")
        check("idempotent FAIL event", r_dup.get("idempotent") is True and m2["lanes"][0]["retry_count"] == 1)

        # 5) blocked first lane then second safe lane
        m = fresh(
            td / "t5",
            mid="M-block-then-safe",
            lanes=[
                {"id": "A", "bound": "beta-harmless"},
                {"id": "B", "bound": "beta-harmless"},
            ],
        )
        bq.mark_blocked(m, "A", "synthetic_proving_block")
        r = bq.close_slice(m)
        check("blocked A then B starts", r.get("started") and r.get("lane_id") == "B", str(r))
        check("A remains BLOCKED", m["lanes"][0]["status"] == bq.LANE_BLOCKED)
        check("A block reason", m["lanes"][0]["block_reason"] == "synthetic_proving_block")

        # 6) all remaining lanes blocked then clean idle/escalation
        m = fresh(
            td / "t6",
            mid="M-all-blocked",
            lanes=[
                {"id": "A", "bound": "beta-harmless"},
                {"id": "B", "bound": "beta-harmless"},
            ],
        )
        bq.mark_blocked(m, "A", "x")
        bq.mark_blocked(m, "B", "y")
        r = bq.close_slice(m)
        check(
            "all blocked → idle",
            r.get("started") is False and r.get("reason") == "all_remaining_blocked_or_escalated",
            str(r),
        )
        check("mission IDLE", m.get("status") == "IDLE")

        # 7) process dies before commit
        m = fresh(td / "t7", mid="M-die-before")
        bq.close_slice(m)
        r = bq.simulate_process_death(m, after_commit=False)
        check("die before: no commit", r.get("after_commit") is False and m["lanes"][0].get("completion_commit") is None)
        check("die before: still WAITING_CURSOR", m["lanes"][0]["status"] == bq.LANE_WAITING_CURSOR)
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-die-before", bq.MISSIONS)
        check(
            "die before: restart resumes WAITING_CURSOR",
            rr.get("resumed_status") == bq.LANE_WAITING_CURSOR,
            str(rr),
        )

        # 8) process dies after commit
        m = fresh(td / "t8", mid="M-die-after")
        bq.close_slice(m)
        r = bq.simulate_process_death(m, after_commit=True, commit="deadC1")
        check("die after: commit kept", r.get("completion_commit") == "deadC1")
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-die-after", bq.MISSIONS)
        m2 = rr["mission"]
        start = bq.start_lane(m2, "A")
        check(
            "die after: restart does not relaunch A",
            start.get("started") is False and start.get("reason") == "already_completed",
            str(start),
        )

        # 9) restart during WAITING_CURSOR
        m = fresh(td / "t9", mid="M-rs-wc")
        bq.close_slice(m)
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-rs-wc", bq.MISSIONS)
        check("restart WAITING_CURSOR", rr.get("resumed_status") == bq.LANE_WAITING_CURSOR)

        # 10) restart during GROK_REVIEW
        m = fresh(td / "t10", mid="M-rs-gr")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-rs-gr", bq.MISSIONS)
        check("restart GROK_REVIEW", rr.get("resumed_status") == bq.LANE_GROK_REVIEW)

        # 11) restart after slice completion
        m = fresh(td / "t11", mid="M-rs-done")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        bq.apply_grok_result(m, "A", "PASS", event_id="p", completion_commit="doneA")
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-rs-done", bq.MISSIONS)
        m2 = rr["mission"]
        check("restart after complete: A not active", m2.get("active_lane_id") != "A" or m2["lanes"][0]["status"] == bq.LANE_COMPLETED)
        r = bq.close_slice(m2)
        check("restart after complete: next is B", r.get("lane_id") == "B" and r.get("started"), str(r))
        # A not run again
        check("A still single completion", m2["lanes"][0]["completion_commit"] == "doneA")

        # 12) duplicate completion event
        m = fresh(td / "t12", mid="M-dup-comp")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        bq.apply_grok_result(m, "A", "PASS", event_id="same-pass", completion_commit="c1")
        r = bq.apply_grok_result(m, "A", "PASS", event_id="same-pass", completion_commit="c1")
        check("dup completion idempotent", r.get("idempotent") is True)
        check("dup completion no double", m["lanes"][0]["completion_commit"] == "c1")

        # 13) duplicate watcher execution
        m = fresh(td / "t13", mid="M-dup-watch")
        r1 = bq.watcher_execute(m, "tok-1")
        r2 = bq.watcher_execute(m, "tok-1")
        check("watcher first executes", r1.get("executed") is True)
        check("watcher dup idempotent", r2.get("idempotent") is True and r2.get("executed") is False)

        # 14) stale ACTIVE pointer
        m = fresh(td / "t14", mid="M-stale")
        bq.close_slice(m)
        bq.advance_cursor_done(m, "A", event_id="cd")
        bq.apply_grok_result(m, "A", "PASS", event_id="p", completion_commit="staleA")
        m["active_lane_id"] = "A"  # stale pointer
        bq.save_mission(m, bq.MISSIONS)
        rr = bq.restart_mission("M-stale", bq.MISSIONS)
        check("stale ACTIVE cleared", rr["mission"].get("active_lane_id") is None, str(rr))

        # 15) no unauthorised lane selection
        m = fresh(td / "t15", mid="M-unauth")
        r = bq.start_lane(m, "Z-INVENTED")
        check("unauthorised lane refused", r.get("ok") is False and r.get("error") == "unauthorised_lane")

        # 16) no Production / external-write escalation (refuse, block, continue)
        m = fresh(
            td / "t16",
            mid="M-policy",
            lanes=[
                {"id": "P", "bound": "production"},
                {"id": "E", "bound": "external-write"},
                {"id": "S", "bound": "beta-harmless"},
            ],
        )
        check("prod pre-blocked at create", m["lanes"][0]["status"] == bq.LANE_BLOCKED)
        check("ext pre-blocked at create", m["lanes"][1]["status"] == bq.LANE_BLOCKED)
        r = bq.close_slice(m)
        check("policy: safe lane still starts", r.get("started") and r.get("lane_id") == "S", str(r))
        # refuse even if asked
        g = bq.guard_lane_bound("production")
        check("policy: guard called by tests", g["allowed"] is False)

        # Idempotency: same cursor_done twice
        m = fresh(td / "t17", mid="M-idemp-cd")
        bq.close_slice(m)
        a1 = bq.advance_cursor_done(m, "A", event_id="once")
        a2 = bq.advance_cursor_done(m, "A", event_id="once")
        check("cursor_done advanced once", a1.get("advanced") is True)
        check("cursor_done dup idempotent", a2.get("idempotent") is True)

        # Persist + reconstruct (memory-only flag must not matter)
        m = fresh(td / "t18", mid="M-persist")
        bq.close_slice(m)
        bq.save_mission(m, bq.MISSIONS)
        loaded = bq.load_mission("M-persist", bq.MISSIONS)
        check("persist reconstruct", loaded is not None and loaded["lanes"][0]["status"] == bq.LANE_WAITING_CURSOR)

        # Ceiling constant
        check("RETRY_CEILING==2", bq.RETRY_CEILING == 2)
        check("MAX_ATTEMPTS==3", bq.MAX_ATTEMPTS == 3)

    print(f"\nFACTORY QUEUE RESULT: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
