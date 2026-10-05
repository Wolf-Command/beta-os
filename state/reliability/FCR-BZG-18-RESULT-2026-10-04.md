# FCR-BZG-18 — Full audit trail

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## What changed

- `scripts/core/venue_close.py`
  - Added `audit_trail(close_id, conn=…)` — reads ordered rows from `core_audit_events` for `resource_type='venue_daily_close'` / `resource_id=close_id`. Each entry returns `action`, `actor_person_id`, `occurred_at`, `result`, and `before`/`after` extracted from recorded metadata (`before_state`/`after_state`, or `note` JSON for owner-control rows).
  - Added `_trail_before_after()` helper for metadata extraction.
  - Enriched `venue_close.open` and `venue_close.esb_captured` `safe_record` metadata with `before_state` / `after_state` so mutations record state transitions on the existing audit spine.
  - Trail ordering: `occurred_at ASC, recorded_at ASC, rowid ASC` (stable when timestamps share second precision).

- `scripts/tests/test_fcr_bzg_18_audit_trail_20261004.py` — new prove test.

## Test command

```bash
python3 -m py_compile scripts/core/venue_close.py scripts/tests/test_fcr_bzg_18_audit_trail_20261004.py
python3 scripts/tests/test_fcr_bzg_18_audit_trail_20261004.py
```

## Pass / fail

**18 passed, 0 failed**

## What was not changed

- Live `catalog/content_library.sqlite` — not written.
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` — not updated.
- Beta pid 93525 — not restarted/reloaded.
- Production port 8787 pid 15975 — not touched.
- FCR-BZG-12 (reopen chain), FCR-BZG-16 (idempotency), FCR-BZG-17 (wrong-date) — not redone.
- GGV, petty cash, bank import — not covered.
- No new staff page, no second audit system, no deletion/rewrite of existing audit rows.
- `serve_beta.py` — no API route added (engine function only).
