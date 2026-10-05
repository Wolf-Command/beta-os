# FCR-BZG-22 — Unknown receipt lines preserved (not discarded)

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## What changed

| File | Change |
|------|--------|
| `scripts/core/bzg_close_vision.py` | Added `_unclassified_lines_from_sections`, `parse_shift_receipt` (fixture-text entry point into existing `normalize_esb_document`), and `derived.unclassified_lines` |
| `scripts/core/bzg_daily_close.py` | `_receipt_document_recon` now exposes `unclassified_lines` for NEEDS_CLASSIFICATION rows |
| `scripts/tests/test_fcr_bzg_22_unknown_receipt_lines_20261004.py` | New prove test — one known + one unknown shift-summary line |

## Test

```bash
python3 -m py_compile scripts/core/bzg_close_vision.py scripts/core/bzg_daily_close.py scripts/tests/test_fcr_bzg_22_unknown_receipt_lines_20261004.py
PYTHONPATH=scripts python3 scripts/tests/test_fcr_bzg_22_unknown_receipt_lines_20261004.py
```

**Result:** 14 passed, 0 failed

Fixture: Shift Summary with `Sales Total` (known) and `Mystery Promo Surcharge` (unknown). Asserts unknown line keeps raw label/amount and `NEEDS_CLASSIFICATION`; known line stays `SALES_TOTAL` / `KNOWN`; derived shift total is not replaced by the unknown amount.

## What was not changed

- No commit, push, merge, reset, stash, or clean
- Beta pid 93525 not restarted/reloaded; production port 8787 pid 15975 untouched
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` not touched
- `state/bzg-daily-close/receipts/` not read or written
- `catalog/content_library.sqlite` not written
- No live vision provider calls; no second parser pipeline; no new staff page
- FCR-BZG-12, 16, 17, 18, 19 not redone; no ESB/receipt/till collapse or cash-difference invention
- `BETA_AUTH_MODE` not set; no hardcoded email or person id; pid 63443 untouched
