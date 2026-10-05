# FCR-GGV-42 — GGV receipt confirm form, optional tax field

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## Summary

Added optional `Tax` input to the GGV receipt human-confirm form on `dashboards/ggv-finance.html`. Blank tax omits the `tax` key from the confirm POST (stores `null`, never `0`). A trimmed non-empty value is sent on the existing `POST /api/ggv/finance/accounting/receipts/{key}/confirm` route. Detail view pre-fills from `human_confirmed.tax` or extraction `tax` when present.

## Files changed

| File | Change |
|------|--------|
| `dashboards/ggv-finance.html` | `rx-tax` label/input; populate on open; include `tax` in confirm body only when non-blank |
| `scripts/tests/test_fcr_ggv_42_receipt_form_tax_20261004.py` | HTML contract + schema-only temp-DB test for form-shaped confirm bodies |

## Test command

```bash
python3 -m py_compile scripts/tests/test_fcr_ggv_42_receipt_form_tax_20261004.py
python3 scripts/tests/test_fcr_ggv_42_receipt_form_tax_20261004.py
```

## Test results

- **Pass:** 8
- **Fail:** 0
- **Exit code:** 0

## Beta reloaded

**No**

## What was not changed

- `serve_beta.py`
- `catalog/content_library.sqlite` (live catalog not read or written)
- Protected close `VDC-470e741f`
- Beta listeners (no reload, no signals)
- Currency, invoices, notas, or other receipt fields
