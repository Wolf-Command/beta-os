# FCR-BZG-23 — Mandiri / BNI / BRI outlet configuration

**Status:** IMPLEMENTATION_DONE  
**Date:** 2026-10-04

## What changed

| File | Change |
|------|--------|
| `scripts/core/bzg_daily_close.py` | Removed auto-seed of `venue_close_outlet_banks` on schema ensure. Added `SETTLEMENT_BANK_LABELS` constant and explicit `configure_outlet_settlement_banks()` workflow. `list_outlet_banks()` now returns `bank_labels` and is read-only for bank rows. |
| `scripts/tests/test_fcr_bzg_23_outlet_bank_configuration_20261004.py` | New temp-DB test for empty → NEEDS CONFIGURATION, configure → three ACTIVE rows, idempotent second read, no cross-outlet writes. |

## Test command

```bash
python3 -m py_compile scripts/core/bzg_daily_close.py scripts/tests/test_fcr_bzg_23_outlet_bank_configuration_20261004.py
python3 scripts/tests/test_fcr_bzg_23_outlet_bank_configuration_20261004.py
```

## Test result

**13 passed, 0 failed**

## What was not changed

- `catalog/content_library.sqlite` — not written
- Protected closes `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` — not touched
- `state/bzg-daily-close/receipts/` — not read or written
- FCR-BZG-12, 16, 17, 18, 19, 22 — not redone
- Beta pid 93525, production port 8787 pid 15975, pid 63443 — not touched
- No new staff page, no Beta reload, no `BETA_AUTH_MODE` change
- EDC terminal auto-seed on schema ensure (separate from outlet-bank config) — left as-is
