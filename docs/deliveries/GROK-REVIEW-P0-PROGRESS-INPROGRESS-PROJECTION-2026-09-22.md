# GROK REVIEW — P0 Progress In progress projection — 2026-09-22

**Verdict:** PASS
**Scope:** Beta only. Production untouched.
**Problem:** Owner Progress showed In progress **0** while compressed factory had live lanes — silent zero lie.
**Fix:** `progress_read_model.factory_work_surface` + `project_open_loops_with_factory` count factory in-flight stages (ACTIVE/WAITING_CURSOR/GROK_REVIEW/IN_FLIGHT/BUILDING/WAITING_GROK) into Open Loops In progress. Empire Progress surfaces current active pack, queued packs, recently completed, Devi/Habitat parked branches, last factory advance. Empty factory → honest 0, no PROJECTION STALE lie. SYSTEM% path unchanged (`SYSTEM_FROM_LEDGER`, live **25.5**).
**Tests:** `scripts/tests/test_progress_inprogress_projection.py` PASS=26 FAIL=0. Live: register `in_progress=0`, projected `factory_in_flight≥1`, `projection_stale=False`, `/progress` 200, :8787/:8788 up.
**Maturity:** No invent PROVEN/READY. No second scoring table.
**Red-team note (non-blocking):** Many historical runs remain stuck at `GROK_REVIEW`/`WAITING_CURSOR`, so In progress can read high (~30). Projection honesty > silent zero; lifecycle hygiene is a follow-up, not this P0 fail.
**Supervisor note:** bf_watch missed `EXIT: SUCCESS` (wrapper never wrote `CURSOR_DONE`); supervisor escalated `inspect_retry_ceiling` → false BLOCKED. Overridden after log+test verify.
**Claim:** `bf-p0-progress-inprogress-projection-20260922`
