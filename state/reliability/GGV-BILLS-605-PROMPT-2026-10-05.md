# GGV-BILLS-605

Beta only. One finishable slice. Workspace `/Users/wolfterminal/beta-os`. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (another worker owns factory orchestration). Do not touch production (pid 1297 on 127.0.0.1:8787). Do not open a public port. Do not print process command lines, tokens, or secrets. Do not execute money movement: no payments, no Xero writes, no bank posting.

Do not mutate these closes:
- VDC-470e741f-d889-437a-9a40-1ec9c083fb95
- VDC-87202768-55af-4c8e-abc3-382a5496b8c6
- VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5

`staff_ready` stays false. `human_commissioned` stays false. Zayen stays GGV NO. Amanda and Matt are the only GGV operators. Do not grant anyone else. No general-ledger jargon on operator pages (no journal, debit, credit, chart of accounts, or GL). Staff language only: invoices, bills, notas.

## Proved gap

Live Beta `catalog/content_library.sqlite` already has ggv_invoices 46, ggv_notas 33, ggv_vendors 13, and no bills table. The prior repair in `scripts/core/ggv_empty_chain_repair1.py` and `scripts/migrations/migrate_ggv_empty_chain_repair_20261004.py` skipped 605 source bills with reason `no_target_table`. Do not trim, rewrite, or delete those 46 invoices or 33 notas. Do not invent invoices, bills, amounts, vendors, or tax.

## Authorised source (read-only)

`/Users/wolfterminal/.openclaw/workspace/wolf-system/ggv-finance/money.sqlite`, opened mode=ro. Confirmed on this machine: table `bill` has 605 rows. Columns, and only these — do not invent fields:

id, entity, contact_id, number, issued_on, due_on, status, amount, currency, notes, created_at, created_by, amount_due, amount_paid, contact_name, reference, source

`sales_invoice` is 46 and `ggv_nota` is 33 in that same file. They are already on Beta. Leave them.

Build the Beta bills structure from that source schema. Map only columns that exist. Leave a missing target field blank (null), never 0 and never a guessed vendor, tax, or amount. Preserve provenance: source id, source table, source file path, source status, and the source `source` column. Idempotent: a second run must not duplicate rows and must not delete the existing invoices or notas.

You may edit finance and import files: `dashboards/ggv-finance.html`, the GGV finance core/API that feeds the finance page, and a new migration plus temp-db test beside the existing empty-chain repair. Take a backup of the live catalog before the live write. Tests use a schema-only or tiny temp sqlite. Do not copy `catalog/content_library.sqlite` into the test.

## Page

https://beta.wolfcommand.net/ggv/finance must show the real imported invoices, these 605 bills, and the real notas. Not an empty chain and not sample rows. The existing Notas / Bills area is the right place if it can list them. Do not show an empty state when the rows exist.

## Reload

Reload Beta only if Python changed, and only after you confirm exactly one listener remains on 127.0.0.1:8788. HTML-only needs no reload. Never signal pid 1297. Never touch port 8787.

## Result

Write `state/reliability/GGV-BILLS-605-RESULT-2026-10-05.json` with pack_id `GGV-BILLS-605`, status, staff_ready false, human_commissioned false, source counts, target counts before and after for ggv_invoices, bills, ggv_notas, and ggv_vendors, skipped reasons, provenance fields stored, confirmation the three closes were not written, test command with pass/fail/exit_code, beta_reloaded true or false plus the 8788 listener pid, no_prod true, no_commit true, no_money_movement true.

Stop when that result file is written.
