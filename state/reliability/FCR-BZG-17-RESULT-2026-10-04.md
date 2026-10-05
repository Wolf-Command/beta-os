# FCR-BZG-17 — Wrong-date protection

**Id:** FCR-BZG-17  
**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## What changed

Server-side wrong-date guards on the venue-close capture and staff-submit paths:

- `_assert_close_business_date` — when the caller pins `business_date`, it must match the close row; otherwise reject with `wrong_business_date` (409) and leave the close unchanged.
- `_assert_esb_snapshot_matches_close` — after ESB warehouse read, snapshot `query_meta.business_date` must match the close row before any totals are written.
- `capture_esb_snapshot` accepts optional `business_date` and runs both checks.
- `staff_submit_close` accepts optional `business_date` and runs the close-date check before declare/reconcile.
- Existing `/api/venue-close/capture` and `/api/venue-close/staff-submit` handlers forward optional `business_date` from the request body (no new HTTP surface).

## Files changed

| File | Change |
|------|--------|
| `scripts/core/venue_close.py` | `_assert_close_business_date`, `_assert_esb_snapshot_matches_close`; wired into `capture_esb_snapshot` |
| `scripts/core/bzg_daily_close.py` | `business_date` param on `staff_submit_close` |
| `scripts/serve_beta.py` | Forward `business_date` on capture and staff-submit |
| `scripts/tests/test_fcr_bzg_17_wrong_date_20261004.py` | New prove test (temp DB) |

## Test

```bash
python3 -m py_compile scripts/core/venue_close.py scripts/core/bzg_daily_close.py scripts/tests/test_fcr_bzg_17_wrong_date_20261004.py
python3 scripts/tests/test_fcr_bzg_17_wrong_date_20261004.py
```

**Result:** 19 passed, 0 failed

Proved:

- Wrong-date capture rejected (`wrong_business_date`); close row unchanged (still OPEN, no fingerprint).
- Same-date capture succeeds; capture without pinned date remains idempotent on an already-captured close.
- Wrong-date submit rejected (`wrong_business_date`); close row unchanged after failed submit.
- Same-date submit proceeds (not rejected as wrong date).

Temp DB only. `catalog/content_library.sqlite` not written. Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` untouched.

## Deliberately not changed

- FCR-BZG-16 refresh/idempotency
- FCR-BZG-12 reopen chain
- Fingerprint freeze (FCR-BZG-09)
- History, cancel, takeover, petty cash, bank import
- Beta reload (pid 93525)
- Production port 8787 (pid 15975)
- Protected close rows
- `BETA_AUTH_MODE`
- Dashboard HTML (client-side date pins remain; server now enforces)
