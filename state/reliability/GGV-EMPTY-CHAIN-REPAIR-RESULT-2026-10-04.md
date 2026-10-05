# GGV-EMPTY-CHAIN-REPAIR — Result

**Finished:** 2026-10-04 19:16 WITA  
**Status:** MIGRATION_APPLIED_IDEMPOTENT_PROVED  
**Decision:** GGV-EMPTY-CHAIN-REPAIR (2026-10-04)

## Defect

Live Beta `catalog/content_library.sqlite` had `ggv_invoices` 0 and `ggv_notas` 0 while proved read-only source `money.sqlite` held 46 sales invoices and 33 notas.

## Source (read-only, counted 19:14 WITA)

| Table | Count |
|-------|------:|
| sales_invoice | 46 |
| bill | 605 |
| ggv_nota | 33 |
| bank_txn | 339 |
| contact | 296 |

### sales_invoice status split (all 46 imported)

| Source status | Count | Beta status |
|---------------|------:|-------------|
| DRAFT | 17 | DRAFT |
| ISSUED | 4 | ISSUED |
| AUTHORISED | 5 | ISSUED |
| PAID | 13 | PAID_CLAIMED |
| REPORTED_PAID | 1 | PAID_CLAIMED |
| VOIDED | 4 | VOID |
| DELETED | 2 | VOID (`source_status=DELETED` in notes) |

**41 vs 46:** An older note said 41 sales invoices. The source file now has 46. Nothing was deleted to force 41. The five beyond the older issued/paid-style count are the five **AUTHORISED** rows — imported as ISSUED, not hidden.

## Import result (live Beta)

| Target | Imported | Skipped |
|--------|----------:|---------|
| ggv_invoices | 46 | 0 |
| ggv_notas | 33 | 0 |
| bills | 0 | 605 (`no_target_table` — no `ggv_bills` / `fin_bills` table in Beta catalog) |

After import:

| Table | Count |
|-------|------:|
| ggv_invoices | 46 |
| ggv_notas | 33 |
| ggv_vendors | 13 (from nota suppliers) |
| fin_counterparties | 14 (from invoice contacts) |

Source ids and amounts preserved. Invoice sequence advanced to `next_value=72` (past highest imported `071A`).

## Idempotency

Second migration run:

- invoices: imported 0, skipped `already_exists` 46
- notas: imported 0, skipped `already_exists` 33

## Backup

`catalog/backups/pre-ggv-empty-chain-repair-20261004-191618.sqlite`  
SHA256: `9b80fbb22b954598175ec905ca53fa5601ac1f85fa1b7c3dd2115e188bcb6eb3`

## Tests

```bash
python3 -m py_compile scripts/core/ggv_empty_chain_repair1.py \
  scripts/migrations/migrate_ggv_empty_chain_repair_20261004.py \
  scripts/tests/test_ggv_empty_chain_repair_20261004.py
python3 scripts/tests/test_ggv_empty_chain_repair_20261004.py
```

**Pass:** 21 · **Fail:** 0 · **Exit:** 0

Schema-only temp sqlite. No `shutil.copy2` of live catalog into tests.

## Honesty

| Fact | State |
|------|-------|
| staff_ready | false |
| human_commissioned | false |
| Unsigned API | fail-closed (unchanged) |
| Prod / :8787 | not restarted, not edited |
| Beta listener | not restarted this session |
| Protected closes VDC-470e741f / VDC-87202768 | untouched |
| bank_txn / contact bulk | not imported |
| Opening balances | not written |
| Petty cash / PR pages | left alone |
| Commit / push | not done |

## Files

| File | Role |
|------|------|
| `scripts/core/ggv_empty_chain_repair1.py` | Import logic |
| `scripts/migrations/migrate_ggv_empty_chain_repair_20261004.py` | Live Beta migration |
| `scripts/tests/test_ggv_empty_chain_repair_20261004.py` | Schema-only tests |
