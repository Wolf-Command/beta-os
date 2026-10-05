# FCR-GGV-38 — Receipt field: upload date

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## Summary

Added `upload_date` column on `ggv_receipt_accounting`. Upload date is set once when a row is first inserted (from vault meta `filed_at` when present, otherwise the date portion of `created_at`). Human confirm continues to store transaction date in `human_confirmed_json.date` and does not touch `upload_date`. Sync updates do not overwrite `upload_date`.

## Files changed

| File | Change |
|------|--------|
| `scripts/core/ggv_receipt_accounting1.py` | `upload_date` column + migration backfill; helpers `_date_only`, `_upload_date_at_store`; set on INSERT only |
| `scripts/tests/test_fcr_ggv_38_upload_date_20261004.py` | New temp-DB test for distinct upload vs transaction date and confirm non-overwrite |

## Test command

```bash
python3 -m py_compile scripts/core/ggv_receipt_accounting1.py scripts/tests/test_fcr_ggv_38_upload_date_20261004.py
python3 scripts/tests/test_fcr_ggv_38_upload_date_20261004.py
```

## Test results

- **Pass:** 13  
- **Fail:** 0  
- **Exit code:** 0

## What was not changed

- `catalog/content_library.sqlite` (live catalog not written)
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- `state/bzg-daily-close/receipts/`
- Beta pid 93525 / production port 8787 pid 15975 / pid 63443
- No new staff page, tax, currency, or second pipeline
- No ESB/receipt/till reconciliation work (FCR-BZG slices untouched)
- No `BETA_AUTH_MODE` changes
- No commits, pushes, or Beta reload
