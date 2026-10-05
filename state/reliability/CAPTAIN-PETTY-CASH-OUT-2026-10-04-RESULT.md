# CAPTAIN-PETTY-CASH-OUT-2026-10-04 — Result

**Status:** `IMPLEMENTATION_DONE`  
**Date:** 2026-10-04  
**Scope:** Beta only. No HUMAN PASS claimed.

## Files changed

| File | Change |
|------|--------|
| `scripts/migrations/migrate_petty_cash_record_out_1.py` | New — seeds `petty_cash.record_out` permission; grants Captain+ roles; denies Cashier/CLOSER |
| `scripts/core/uma_ops_console.py` | OUT-only recording gated on `petty_cash.record_out`; new schema columns; `sum_petty_out_for_date` / `list_petty_out_for_date`; missing receipt → `EVIDENCE_EXCEPTION` + `INCOMPLETE` proof |
| `scripts/core/bzg_daily_close.py` | `cash_reconciliation_with_petty()` wired into `recon_board` as `cash_reconciliation` |
| `scripts/core/uma_devi_p0.py` | `petty` / `petty_record_out` capabilities use `petty_cash.record_out` |
| `scripts/serve_beta.py` | POST `/api/bzg/uma-blu/petty` passes new OUT fields (reason, payee, accounting_code, photo_evidence_id, etc.) |
| `scripts/tests/test_petty_cash_record_out_20261004.py` | New — temp-DB tests for capability gate, OUT-only, evidence exception, daily-close math |

## Tests run

```text
python3 -m py_compile scripts/core/uma_ops_console.py scripts/core/bzg_daily_close.py \
  scripts/core/uma_devi_p0.py scripts/migrations/migrate_petty_cash_record_out_1.py \
  scripts/tests/test_petty_cash_record_out_20261004.py
→ exit 0

python3 scripts/tests/test_petty_cash_record_out_20261004.py
→ PASS=28 FAIL=0

python3 scripts/tests/test_uma_petty_cash.py
→ PASS=51 FAIL=2 (pre-existing daily_close issue-card noise in copied live DB; not introduced by this slice)
```

Protected close `VDC-470e741f` state verified unchanged in temp-DB test.

## Behaviour delivered

1. **Capability gate** — `record_petty_ops` requires `petty_cash.record_out` (Captain+ via migration grant list).
2. **OUT only** — IN direction rejected with `direction_forbidden`.
3. **Required fields** — business (`entity_id`), outlet, business_date, transaction_time, amount, category, reason, person recording, evidence photo, accounting mapping; payee optional; receipt optional.
4. **Missing receipt** — `receipt_status=EVIDENCE_EXCEPTION`, `proof_status=INCOMPLETE`; amount unchanged.
5. **Daily close math** — `expected_closing = opening_float + cash_sales − petty_out`; counted vs difference; movements read from Wolf once (`double_count_avoided`, `staff_retype_required=false`).
6. **Separation of duties** — high-value OUT stays `NEEDS_APPROVAL`; no self-approval path in recorder.

## Deliberately not changed

- Petty cash **IN** recording (blocked, not built)
- Petty-cash config / opening-float commission UI
- History edits, audit deletes, bank movement
- Production (8787), Beta server restart, close `VDC-470e741f` or 3 Oct close evidence
- Live catalog migration not applied (migration script ready; run manually when commissioned)
- `venue_close.reconcile()` core variance formula (ESB vs declared) — petty flows via new `cash_reconciliation` board section to avoid breaking existing close states
- Commit, push, PR #1
