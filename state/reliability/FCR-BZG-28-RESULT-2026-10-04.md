# FCR-BZG-28 — Manual fallback if image extraction fails

**Date:** 2026-10-04  
**Status:** IMPLEMENTATION_DONE  
**Parent requirement:** Manual fallback if image extraction fails (FCR-BZG-28)

## Files changed

| File | Change |
|------|--------|
| `scripts/core/bzg_daily_close.py` | EDC extract soft-fail parity with ESB; `_entry_source_from_vision`; manual vs vision-confirmed entry tracking on confirm |
| `scripts/tests/test_fcr_bzg_28_manual_fallback_20261004.py` | New temp-DB test (forced dry-run extract failure + manual follow-up) |

## Test command

```bash
python3 -m py_compile scripts/core/bzg_daily_close.py
python3 scripts/tests/test_fcr_bzg_28_manual_fallback_20261004.py
```

## Pass / fail counts

| Run | Passed | Failed |
|-----|--------|--------|
| `test_fcr_bzg_28_manual_fallback_20261004.py` | 26 | 0 |

## What was implemented

1. **`extract_edc_receipt_draft`** — When vision returns `extraction_unavailable`, the close continues (`ok: true`), staff get `STAFF_VISION_UNAVAILABLE` copy, `manual_entry_ok: true`, and extracted JSON is tagged `extraction_status: UNAVAILABLE` with **null amounts** (not zero). No `venue_close_edc_receipts` row is written on extract alone.

2. **`extract_esb_closing_receipt_draft`** — Vision-event JSON now records unavailable flags **before** insert (so downstream manual confirm can detect failed extract). Added `manual_entry_ok` on failure.

3. **`confirm_edc_receipt` / `confirm_esb_closing_receipt`** — New `manual_entry` flag and `_entry_source_from_vision()` set `entry_source` to `MANUAL` or `VISION_CONFIRMED` in `confirmed_json`. Failed-extract follow-up is stored as manual entry (`vision_extract_succeeded: false`), not as a successful vision confirm.

4. **Missing bank lines** — Unconfirmed banks (e.g. BNI with no receipt) stay absent (`actual_edc` / `actual_qris` null on bank card), not stored as zero.

## What was not changed

- No live vision provider calls; test uses `WOLF_CLOSE_VISION_DRY=1` only.
- No second extractor, no new staff page, no `serve_beta.py` edits.
- No changes to FCR-BZG-12, 16, 17, 18, 19, 22, or 23 logic.
- No ESB cash reconciliation against printed receipt; no invented cash-difference causes.
- `catalog/content_library.sqlite` not written.
- Protected closes `VDC-470e741f…` and `VDC-87202768…` not updated.
- `state/bzg-daily-close/receipts/` not read or written.
- Beta pid 93525, production port 8787, pid 63443 untouched.
- No commit, push, merge, reset, stash, or clean performed.

## Evidence notes

Implementation verified by temp-DB test only. Not PROVEN_COMPLETE, not staff_ready, not human commissioned.
