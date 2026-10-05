# FCR-GGV-41 — Receipt field: currency

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## Summary

Added `currency` to GGV receipt human confirm on the existing `ggv_receipt_accounting` row (`human_confirmed_json`). Currency is stored only when explicitly provided in the confirm body; omitted currency stays `null`, not a default code and not zero. `confirm_receipt` asserts readback of `currency` after update. Extraction meta may surface `currency` when present in vault meta.

## Files changed

| File | Change |
|------|--------|
| `scripts/core/ggv_receipt_accounting1.py` | `_confirmed_currency` helper; `currency` in human confirm + `confirmed_fields`; extraction meta `currency`; post-update readback assert |
| `scripts/tests/test_fcr_ggv_41_currency_20261004.py` | New schema-only temp-DB test for blank vs provided currency readback |

## Test command

```bash
python3 -m py_compile scripts/core/ggv_receipt_accounting1.py scripts/tests/test_fcr_ggv_41_currency_20261004.py
python3 scripts/tests/test_fcr_ggv_41_currency_20261004.py
```

## Test results

- **Pass:** 10  
- **Fail:** 0  
- **Exit code:** 0

## What was not changed

- `catalog/content_library.sqlite` (live catalog not read or written)
- `catalog/backups/` (no copy made)
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- `state/bzg-daily-close/receipts/`
- Beta pid 93525 / production pid 15975 / pid 63443
- `serve_beta.py` (no new route)
- Staff pages / dashboards
- Amount field behavior (FCR-GGV-39 untouched)
- Tax field behavior (FCR-GGV-40 untouched)
- No `BETA_AUTH_MODE` changes
- No commits, pushes, or Beta reload
