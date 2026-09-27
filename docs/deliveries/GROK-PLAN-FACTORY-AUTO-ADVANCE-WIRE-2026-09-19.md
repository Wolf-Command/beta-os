# GROK PLAN — Factory auto-advance wire — 2026-09-19

## Class
FIX — wire existing `bf_queue.close_slice` into supervisor when ACTIVE is empty.
Not a new capability surface. Owner correction 19 Sep: IDLE with eligible queue is a defect.

## Defect
After slice DONE, `ACTIVE` cleared → supervisor `IDLE`. `ACTIVE_MISSION` was unset.
Calendar watcher fixed wakes; multi-lane select still required Peaches to pick the next slice.

## Repair (in flight)
1. Arm mission `owner-autonomous-20260919` with ordered safe lanes; bind Devi P0 as current.
2. `bf_supervisor.mission_continue_if_idle`: empty ACTIVE → RESUME_LANE or `close_slice` → `FACTORY_LAUNCH_NEXT` wake.
3. On LAUNCH_NEXT wake: Peaches/watch starts Cursor for that lane (plan → WAITING_CURSOR). No Matt pick.
4. Completion Register item `CR-a0e1f0f8adc02de3` tracks until multi-lane prove without human pick.
5. After Devi P0 FINISHED: park human retest branch; auto-start `factory-auto-advance-wire` then remaining queue.

## Out of scope
Production, finance/trading (Zayen), HR (Tisa), score gaming, inventing maturity credits.

## Prove bar
- Empty ACTIVE + PENDING lane → LAUNCH_NEXT (not silent IDLE)
- Blocked lane skipped; next safe starts
- Human-blocked Devi retest does not stop mission
- Existing queue tests stay green
