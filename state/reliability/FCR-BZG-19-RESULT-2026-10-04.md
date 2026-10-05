# FCR-BZG-19 — Original evidence preservation

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## Files changed

- `scripts/core/bzg_daily_close.py` — preservation snapshot/verify helpers, `read_preserved_close_evidence`, supersede guard in `confirm_edc_receipt`
- `scripts/tests/test_fcr_bzg_19_original_evidence_preservation_20261004.py` — new temp-DB test

## Test command

```bash
python3 -m py_compile scripts/core/bzg_daily_close.py scripts/tests/test_fcr_bzg_19_original_evidence_preservation_20261004.py
python3 scripts/tests/test_fcr_bzg_19_original_evidence_preservation_20261004.py
```

## Pass / fail

- **pass=18 fail=0**

## What was done

On the existing venue-close EDC evidence path (`save_close_receipt_bytes` → `submit_evidence` → `confirm_edc_receipt`):

- Added `read_preserved_close_evidence` to read an evidence spine row plus stored receipt bytes and hash match (no second evidence store).
- Before bank supersede, snapshot prior evidence row + bytes; after attach, assert the original row and bytes were not deleted or overwritten.
- Superseded receipt rows stay in `venue_close_edc_receipts` with `evidence_role=SUPERSEDED`; the new receipt is `CURRENT`.

Test on a throwaway close: store original EDC evidence, attach a later item for the same bank, assert original row/bytes still readable and unchanged, later item is CURRENT.

## What was not changed

- FCR-BZG-12 reopen chain
- FCR-BZG-16 idempotency
- FCR-BZG-17 wrong-date protection
- FCR-BZG-18 audit trail
- ESB cash vs printed receipt reconciliation (FCR-BZG-20)
- `catalog/content_library.sqlite` (live catalog)
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- `state/bzg-daily-close/receipts/`
- Beta pid 93525 / production port 8787
- No new staff page
