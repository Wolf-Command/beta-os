# PETTY-OWNER-CASH-IN-1 — Result — 2026-10-05

**Status:** PASS · **staff_ready:** false · **human_commissioned:** false

## Summary

Owner and authorised Finance can now record **Cash IN / top-up** and submit **physical cash counts** on the Uma Blu petty page. Captains remain **Cash OUT only**. No ledger rows were inserted, edited, or deleted on the live catalog. Live displayed balance remains **Rp52,700**.

## Live balance

| | IDR |
|---|---:|
| Before repair | 52,700 |
| After repair | 52,700 |
| Rp2,300 inserted | **NO** |
| Coins counted | **NO** |

Provenance: [PETTY-BALANCE-PROVENANCE-2026-10-05.md](PETTY-BALANCE-PROVENANCE-2026-10-05.md)

## Permissions (assignment-derived)

| Permission | Captain | Owner (ROLE-MATT) | BZG FC |
|---|---|---|---|
| `petty_cash.record_out` | ALLOW | ALLOW | ALLOW |
| `petty_cash.record_in` | denied | ALLOW | ALLOW |
| `petty_cash.reconcile` | denied | ALLOW | ALLOW |

## Tests — 118 pass, 0 fail

- `test_petty_owner_cash_in_20261005.py` — 31/0 (all 12 required scenarios)
- `test_petty_cash_record_out_20261004.py` — 31/0
- `test_petty_surface_20261004.py` — 26/0
- `test_petty_iza_fail_repair_20261004.py` — 30/0

## Deploy

- Beta restarted via `scripts/beta_restart.py` — pid **11882** on `127.0.0.1:8788`
- Production pid **1297** on `:8787` — untouched
- Public URL: https://beta.wolfcommand.net/bzg/uma-blu/petty

## JSON

Full machine-readable result: [PETTY-OWNER-CASH-IN-1-RESULT-2026-10-05.json](PETTY-OWNER-CASH-IN-1-RESULT-2026-10-05.json)
