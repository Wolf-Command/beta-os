# UMA close staff workflow repair — 2026-10-03

Status: **IMPLEMENTATION_DONE** (not HUMAN PASS)

Commissioning note read: `state/reliability/UMA-CLOSE-2026-10-03-COMMISSIONING.md`

Protected close **not modified**: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`

## Files changed

| File | Change |
|------|--------|
| `scripts/core/bzg_close_vision.py` | Added `_edc_prompt_with_bank_context`; soft-fail on unexpected provider errors |
| `scripts/core/venue_close.py` | Idempotent `attach_declared_cash` when same amount already declared |
| `scripts/core/bzg_daily_close.py` | Idempotent till declare; `cash_three_sources`; `staff_submit_close`; bank card staff labels + live/shift/terminal fields; `enrich_close` includes `cash_sources` |
| `scripts/serve_beta.py` | `POST /api/venue-close/staff-submit` |
| `dashboards/uma-blu-close.html` | Cash photo controls; three-source display; staff submit UX; removed Reconcile button; staff language; bank card three-source rows |
| `scripts/tests/test_uma_close_repair_20261003.py` | New repair proof suite (temp DB only) |

## Tests run

```text
python3 -m py_compile scripts/core/bzg_close_vision.py scripts/core/bzg_daily_close.py scripts/core/venue_close.py scripts/serve_beta.py
python3 scripts/tests/test_uma_close_repair_20261003.py
```

**Result:** pass=23 fail=0

Proofs:

- `_edc_prompt_with_bank_context` defined; `extract_edc_receipt` no NameError; provider failure returns soft `extraction_unavailable`
- Duplicate `attach_declared_cash` same amount → `idempotent: true`, no second cash evidence row
- Staff HTML: no `btnReconcile`; `btnCashTakePhoto` / `btnCashUploadPhoto` present; Live ESB / Printed shift receipt / Physical till labels present
- Protected close id reference count unchanged in temp DB after test writes

## What was deliberately not changed

- Protected 3 Oct close row `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` and its evidence, photos, audit, exception `WI-109e1683-4e57-4fc0-860f-24bfbaf42975`
- Receipt files under `state/bzg-daily-close/receipts/` including unattached `EVD-CLOSE-EDC-95A47735CCB3.jpg` (no bank guessed)
- Closes `VDC-da1b6621-b657-4444-bc7c-7161a0bf5b94` (2 Oct) and `VDC-4046a805-8c76-4439-8019-f879f3b49513` (28 Sep)
- Production Beta (port 8787) — no restart, no reload
- No git commit, push, or PR merge

## Behaviour summary

1. **EDC reader** — prompt helper defined; EDC and QRIS stay separate; failures are staff-safe messages.
2. **Cash evidence** — optional Take/Upload photo on cash section; submit not blocked without photo.
3. **Staff language** — Reconcile removed from staff UI; canonical phrases (MATCH, DIFFERENCE FOUND, RECEIPT MISSING, etc.).
4. **Submit UX** — single staff-submit flow with SUBMITTING → CLOSE COMPLETE / CLOSE SAVED WITH EXCEPTION / CANNOT SUBMIT / PLEASE RECOUNT CASH; idempotent declare for same close + amount.
5. **Three cash sources** — live ESB, printed shift receipt, physical till shown separately with differences.
6. **Bank cards** — Mandiri/BNI/BRI from config; live ESB, shift report, terminal, and Δ per EDC/QRIS; NOT USED TODAY when zero confirmed.
7. **Variance** — recount → confirm recount → submit with exception; exception routes via `find_hfb_assignee`.
8. **Phone layout** — raw codes humanized in staff-facing bank/dual-source rows; date masthead kept.

Python changes are on disk only until a later controlled Beta reload.
