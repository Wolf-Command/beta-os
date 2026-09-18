# FACTORY DISAPPEARANCE TEST — 18→19 September 2026

**Result: FAIL**

Do not rewrite this result after later repairs.

## What happened

- History / Issues Cursor for `BF-uma-history-issues-20260919` started ~00:21 WITA Saturday 19 Sep 2026.
- Child pid 37508 died with no `EXIT` line (log had start markers only).
- Build-factory watch last ran ~00:15 WITA Saturday (end of Friday night weekday ticks), then did not fire again because its Grok routine schedule was weekdays only: `*/5 * * * 1-5`.
- Matt typed `status` at ~06:48 WITA → factory inspected and Cursor relaunched.
- Matt typed `status` again at ~07:08 WITA → another factory check.

## Classification

**OWNER PROMPT REQUIRED TO RESUME = FOUNDER DEPENDENCY**

Useful overnight builds (dashboard truth, cockpit, empire, petty, history/issues after relaunch) remain valid as candidate completed work.

The unattended autonomy test for 18→19 Sep is still **FAIL**.

## Root cause (calendar layer)

`bf_watch.py` / `bf_advance.py` themselves have no Saturday filter.

The supervisor wake path was the Grok Bot routine `build-factory-watch` with cron day-of-week `1-5`.

An ACTIVE approved mission therefore depended on weekday calendar + Matt status when the weekday watch was silent.

## Not claimed here

This file does not claim the repair. Repair evidence lives in a separate delivery after the calendar-free supervisor is proven.
