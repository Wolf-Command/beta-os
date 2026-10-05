# BZG-P2P-THREE-WAY-1 — three-way match of PO, goods receipt, and supplier nota

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

Already built and reused (do not rebuild): purchase requests (`/bzg/uma-blu/bills`, `dashboards/bzg-uma-blu-pr.html`), purchase orders (BZG-P2P-PO-1: `/bzg/uma-blu/purchase-orders`, `scripts/core/bzg_purchase_order.py`, `bzg_ops_purchase_orders` / `bzg_ops_po_lines`), goods receiving (BZG-P2P-RECV-1: `scripts/core/bzg_goods_receiving.py`, `bzg_ops_goods_receipts` / `bzg_ops_gr_lines`), and supplier nota / bill capture (BZG-P2P-NOTA-BILL-1: `scripts/core/bzg_supplier_bill.py` and its tables when present). State helpers live in `scripts/core/uma_ops_console.py` (`ALLOWED_TRANSITIONS`, `transition_pr`). Segregation helpers live in `scripts/core/uma_devi_p0.py`.

Build the next step only: a real Beta **three-way match** that compares one existing purchase order, one existing goods receipt on that order, and one existing supplier nota on that receipt, then shows a clear match or a plain difference. Do not create AP, ready-to-pay, payment execution, bank connection, or any money movement. Do not rebuild requests, orders, receiving, nota capture, Recipe Builder, Daily Close, Petty Cash, or Owner Home.

## Rules

- Source: one saved, non-example purchase order, one saved goods receipt tied to that order, and one saved supplier nota / bill tied to that receipt (and so its order and request). Outlet and supplier are derived server-side from the upstream documents; display them locked and reject a client-supplied outlet, supplier, order, receipt, or bill that does not match the chain.
- Compare, line by line where lines exist: ordered qty/price, received qty, and billed qty/price / nota total. Show either a plain "match" or a plain difference (qty short/over, price difference, total difference). Differences must not invent new item names.
- Persist the match result (match or difference summary) so an authenticated controller can reload and see the same result. Prefer one small table (e.g. `bzg_ops_three_way_matches`) or an existing unused home if one truly fits — no second system of record. Do not write to any `ggv_*` table.
- Matching is read-and-record only relative to AP and pay: do not create an AP posting, do not move into any `PAYMENT_*`, `PAID_CLAIMED`, or `CLOSED` state. If a tiny state note is required for a matched bill, leave the request at `BILL_RECEIVED` (or the nota slice's honest state) and record the match beside it — never execute payment.
- Matcher is the authenticated person with an active assignment. Do not hardcode a person name. Reuse an existing permission if one truly fits; otherwise add one small permission (e.g. `bzg.match.run`) granted by role, not by person name.
- Idempotent migration with a backup of the live catalog before the live write. Audit the create.
- Do not invent purchase orders, receipts, notas, suppliers, quantities, or prices so the page looks full. If the live catalog has no complete PO+receipt+nota chain, show an honest empty state.
- No GL, journals, debits, credits, account codes, internal ids, or engineering labels on the page. Finance does the accounting later. Say plainly this is a three-way comparison; it is not AP and not a payment.

## Page

- Extend the purchasing views on `/bzg/uma-blu/purchase-orders` (or a linked `/bzg/uma-blu/three-way-match` page) with a Match action for an eligible nota/receipt/order trio and a match history. Phone-friendly.
- Outlet display name from `org_outlet_registry`.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`, `ggv_nota_files`, `ggv_nota_history`) — leave the GGV 605 bills / 46 invoices / 33 notas alone.
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks. Tests use a temp sqlite. Never `shutil.copy2` the live catalog into a test.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787. Production untouched.
- Beta listener at launch is pid 92970, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement.

## Tests

Add `scripts/tests/test_bzg_p2p_three_way1_20261005.py` on a temp sqlite. Cover: unauthenticated denied; no permission denied; missing / example / mismatched chain denied; client-supplied outlet / supplier mismatch rejected; match on equal lines records match; qty or price difference records a plain difference (not blocked); no AP / payment state set; save then reload returns the same match result; protected close ids untouched in the fixture. Re-run `scripts/tests/test_bzg_p2p_nota1_20261005.py`, `scripts/tests/test_bzg_p2p_recv1_20261005.py`, and `scripts/tests/test_bzg_p2p_po1_20261004.py` and report they still pass.

## Result

Write `state/reliability/BZG-P2P-THREE-WAY-1-RESULT-2026-10-05.json` with pack_id `BZG-P2P-THREE-WAY-1`, status, staff_ready false, human_commissioned false, eng_proved false, routes, tables (and whether reused), permission, migration, backup path, files_changed, tests_pass / tests_fail for the new test and regressions, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built.

Stop when that result file is written.
