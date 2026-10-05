# Phase 6 shadow routing — truthful relabel (2026-10-06)

**Label:** BUILT / SYNTHETIC TESTED  
**Not:** operational, commissioned, live dual-run  
**Evidence in code:** `wolf_intelligence/shadow_compare.py`
- `_current_system_actual()` defaults `last_worker_hint` to `"cursor"`
- `_factory_history_workers()` appends `"cursor"` when no run dirs / defaults
- `quality_diff` fields set to `"UNKNOWN"` / `"UNKNOWN_until_human_outcomes"`
- `accept()` samples synthetic work items with tags `phase6`, `shadow_compare`

**Action:** Preserve code. Update `wolf_intelligence/STATUS.md` (see patch).  
Do not delete shadow_compare.py.
