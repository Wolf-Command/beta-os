# GGV-EMPTY-CHAIN-REPAIR

Beta only. One pack. Do not restart Production. Do not edit Prod. Do not commit. Do not push. Do not change Cloudflare or Wolf permissions. Do not mutate closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not load the AMG template into BZG. Do not copy catalog/content_library.sqlite for tests. Do not invent invoices, bills, notas, amounts, or vendors.

## Proved source (read-only)

`/Users/wolfterminal/.openclaw/workspace/wolf-system/ggv-finance/money.sqlite`

Counted 2026-10-04 19:14 WITA, mode=ro:

- sales_invoice 46
- bill 605
- ggv_nota 33
- bank_txn 339
- contact 296

An older note said 41 sales invoices. The file now has 46. Import the file. Do not delete rows to force 41. In the result, split the 46 by whatever status column exists so the extra five are explained, not hidden.

Live Beta `catalog/content_library.sqlite` at the same time: ggv_invoices 0, ggv_notas 0. That empty is the defect.

## Do

Import those source rows into the existing Beta GGV tables for invoices, bills if a real table already exists, and notas. Preserve source ids and amounts. Idempotent: a second run must not duplicate. Tests run on a schema-only temporary database, then the migration may apply to the live Beta catalog. Unsigned API stays fail-closed. staff_ready stays false. human_commissioned stays false.

Write:

- state/reliability/GGV-EMPTY-CHAIN-REPAIR-RESULT-2026-10-04.json
- state/reliability/GGV-EMPTY-CHAIN-REPAIR-RESULT-2026-10-04.md

Include source counts, imported counts, skipped counts with reasons, and the test command with pass/fail.

## Do not

Do not open a public port. Do not print secrets. Do not restart the Beta or Prod listeners. Do not write opening balances. Do not touch petty cash or the purchase-request pages except by leaving them alone.
