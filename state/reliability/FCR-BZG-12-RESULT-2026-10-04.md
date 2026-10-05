# FCR-BZG-12 — Reopen completed close four-stage chain

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04  
**Id:** FCR-BZG-12

## Summary

Built the missing ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL chain on the existing `venue_close` reopen path. No second close system.

| Stage | Implementation |
|-------|----------------|
| 1. ORIGINAL | Existing `venue_close_final_history` freeze (unchanged semantics) |
| 2. REOPEN EVENT | New `venue_close_reopen_events` row on `owner_control` reopen of `VERIFIED_CLOSED`, pointing at `final_history_id`, with reason, assignment-derived actor, timestamp |
| 3. CHANGES | New `venue_close_reopen_changes` rows when working close mutates after an open reopen (`esb_capture`, `declared_cash`, `reconcile`) |
| 4. NEW APPROVAL | New `venue_close_reopen_approvals` row on `verify_close` or zero-variance reconcile re-close — distinct from the reopen event |

## Files changed

- `scripts/core/venue_close.py` — reopen chain tables, helpers (`reopen_chain`, `record_reopen_working_change`), hooks on reopen / capture / declare / reconcile / verify
- `scripts/tests/test_fcr_bzg_12_reopen_chain_20261004.py` — throwaway close prove on temp DB copy

## Test

```bash
python3 -m py_compile scripts/core/venue_close.py scripts/tests/test_fcr_bzg_12_reopen_chain_20261004.py
python3 scripts/tests/test_fcr_bzg_12_reopen_chain_20261004.py
```

**Result:** 23 passed, 0 failed

## Deliberately not changed

- `catalog/content_library.sqlite` (live catalog — test uses temp copy under `catalog/backups/`)
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- Cancel unfinished, petty cash, bank import, history views, other FCR rows
- `serve_beta.py` HTTP surface (chain available via `reopen_chain()` and reopen response `reopen_chain` payload)
- Production / Beta processes (no restart, no signal)
