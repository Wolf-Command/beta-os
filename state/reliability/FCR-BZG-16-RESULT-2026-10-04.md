# FCR-BZG-16 — Refresh/idempotency protection

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## Files changed

| File | Change |
|------|--------|
| `scripts/core/venue_close.py` | `open_or_get` returns `idempotent: True` on existing close; `capture_esb_snapshot` sets `idempotent: True` on frozen re-capture; `reconcile` short-circuits when already `VERIFIED_CLOSED` |
| `scripts/core/bzg_daily_close.py` | `staff_submit_close` returns idempotent `CLOSE COMPLETE` when verified with same amount; rejects refresh with different amount (`amount_mismatch`) |
| `scripts/tests/test_fcr_bzg_16_idempotency_20261004.py` | New temp-DB prove for open / capture / declare / submit idempotency |

## Test command

```bash
python3 -m py_compile scripts/core/venue_close.py scripts/core/bzg_daily_close.py scripts/tests/test_fcr_bzg_16_idempotency_20261004.py
python3 scripts/tests/test_fcr_bzg_16_idempotency_20261004.py
```

## Pass / fail

- **FCR-BZG-16:** 28 passed, 0 failed
- **Regression (FCR-BZG-12 reopen chain):** 23 passed, 0 failed

## What was built

- **Open:** repeating `open_or_get` for the same outlet/date returns the existing close (`idempotent: True`, `created: False`); no second current row.
- **Capture:** repeating `capture_esb_snapshot` on a frozen dated snapshot returns existing fingerprint (`idempotent: True`, `mutated: False`).
- **Cash declare:** same-amount `attach_declared_cash` returns existing declaration (`idempotent: True`); no second cash evidence row. Different amount is not treated as idempotent and writes a new evidence row.
- **Staff submit:** repeating `staff_submit_close` on a verified close with the same amount returns `CLOSE COMPLETE` (`idempotent: True`); no duplicate reopen approval. Different amount on refresh returns `CANNOT SUBMIT` with `amount_mismatch`.
- **Reconcile:** already-`VERIFIED_CLOSED` reconcile returns existing row (`idempotent: True`).
- Actors resolved from org assignment / closer roster in the test — no hardcoded person ids in engine code.

## What was not changed

- FCR-BZG-09 fingerprint freeze semantics
- FCR-BZG-12 reopen chain (ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL)
- History, cancel, takeover, petty cash paths
- `catalog/content_library.sqlite` (temp copy only in test)
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`
- Beta / production processes or ports
- No commit, push, Beta reload, or `BETA_AUTH_MODE` changes
