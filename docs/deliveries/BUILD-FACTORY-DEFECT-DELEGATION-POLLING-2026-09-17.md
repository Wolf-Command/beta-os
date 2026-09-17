# BUILD FACTORY DEFECT — Founder-dependent polling (Delegation)

**Date:** 2026-09-17
**Class:** BUILD FACTORY defect (orchestration).

## Evidence

1. Cursor launched for Delegation → no automatic stage advance
2. Matt asked `status` → Cursor complete discovered
3. Grok FAIL DLG-RT-001 → Cursor fix launched → no auto advance
4. Matt asked `status` → fix complete → re-review/report

## Root cause

Peaches ended turns after background Cursor launch without binding completion detection + stage advancement to persisted ACTIVE run state / tracked Shell completion. Matt became the poller.

## Remediation

RULE-Build-Factory-Self-Driving-2026-09-17 + `state/build-factory/` + `bf_watch.py` + Build factory watch routine + Shell-tracked child launches.
