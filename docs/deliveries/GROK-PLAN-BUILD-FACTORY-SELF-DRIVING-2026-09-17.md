# GROK PLAN — Build Factory Self-Driving (orchestration only)

**Date:** 2026-09-17 WITA  
**Scope:** Governance + Mac build tooling. No Wolf application/domain code. No Production. No Dual Approval. No Authority seed.

## Verified defect (Delegation evidence)

1. Cursor launched for Delegation → no automatic stage advance  
2. Matt typed `status` → Cursor discovered complete  
3. Grok FAIL DLG-RT-001 → Cursor fix launched → again no auto-advance  
4. Matt typed `status` again → fix discovered → only then re-review/report  

**Root cause (verified):** Peaches ended conversational turns after launching background `cursor-agent` and treated completion as something Matt must surface via chat. Background Shell completion wakes and/or a standing watch were not wired to **mandatory stage advancement**. Chat memory was the de-facto state store. Matt became the poller.

## Smallest solution (no platform)

1. **Persisted run state** under `state/build-factory/runs/<run_id>.json` + `state/build-factory/ACTIVE` pointer.  
2. **Watch script** `scripts/build-factory/bf_watch.py` — read-only inspect of pid/log/exit marker; print machine-readable stage advice.  
3. **Peaches procedure (RULE)** — on any Cursor/Grok child launch: write run state; prefer Await/completion handling in-session; if turn must end, ACTIVE run + watch routine MUST be armed; completion wake for an ACTIVE run is NEVER silent.  
4. **Standing routine** `build-factory-watch` — weekday every 5 minutes; quiet if no ACTIVE run; if ACTIVE and child done, Peaches advances next stage automatically.  
5. **Heartbeat policy** — STARTED / BLOCKED / FINISHED only to Matt.

## Not inventing

Does not claim a new OS daemon. Uses: Mac files, pid/log, existing Shell background completion, existing Grok Bot routines.
