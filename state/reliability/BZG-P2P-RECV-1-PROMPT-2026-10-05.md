# BZG-P2P-RECV-1 — goods receiving against a saved purchase order

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

The purchase-order slice already exists (BZG-P2P-PO-1): page `/bzg/uma-blu/purchase-orders`, core `scripts/core/bzg_purchase_order.py`, tables `bzg_ops_purchase_orders` / `bzg_ops_po_lines`, migration `scripts/migrations/migrate_bzg_p2p_po1_20261004.py`, test `scripts/tests/test_bzg_p2p_po1_20261004.py`, permission `bzg.po.create`. Request pages `/bzg/uma-blu/bills` and `dashboards/bzg-uma-blu-pr.html` already exist with submit / approve / order / receive actions.

Build the next step only: a real Beta **goods receiving** record that an authenticated person saves against one already-saved purchase order, then reloads and sees again. Do not build nota/bill capture, three-way match, AP, ready-to-pay, or any payment. Do not rebuild purchase requests, purchase orders, Recipe Builder, Daily Close, or Petty Cash; reuse them.

## Rules

- Source: one saved, non-example purchase order row in `bzg_ops_purchase_orders` with its `bzg_ops_po_lines`. Outlet on the receipt is the outlet stored on that order (and its request). Never ask staff to choose outlet, entity, or supplier; display them locked. The server derives them and rejects a client-supplied outlet, supplier, or order line that does not match the stored order.
- Lines: only lines on that order. Received qty per line is zero or more and never above the ordered qty remaining (ordered minus already received). No new item names. Staff may note a short reason for a shortfall or rejected qty (damaged / short / wrong item) in plain words.
- Partial receipts allowed; the order shows ordered / received / outstanding per line. A second receipt cannot push total received above ordered.
- Receiver is the authenticated person with an active assignment. Do not hardcode a person name. Receiver cannot be the same person who approved the source request (separation of duties) unless the existing segregation helper already defines otherwise — reuse `scripts/core/uma_devi_p0.py` and the existing state helpers in `scripts/core/uma_ops_console.py`; do not invent a second state machine.
- Request/order state: use the existing transition helper. A full receipt may move the request `ORDERED` → `RECEIVED`; a partial receipt must not mark it fully received. If the receipt save fails, leave states unchanged. Never set `BILL_RECEIVED`, any `PAYMENT_*`, `PAID_CLAIMED`, or `CLOSED`.
- Permission: reuse an existing assignment permission if one truly fits for receiving; otherwise add one small permission (e.g. `bzg.receiving.create`) and grant it by role to roles that already handle purchasing/receiving at the outlet, not by person name. No new role for a named human.
- Persist in the Beta catalog in new `bzg_ops_goods_receipts` / `bzg_ops_gr_lines` (or an existing real unused receipt table if you find one — no second system of record). Idempotent migration with a backup of the live catalog before the live write. Audit the create.
- Do not invent orders, receipts, quantities, suppliers, or prices so the page looks full. If no saved order is eligible, the page shows an honest empty state.
- No inventory/stock ledger posting in this slice; record the receipt only and say so plainly.

## Page

- Extend `/bzg/uma-blu/purchase-orders` (or a linked `/bzg/uma-blu/receiving` page) so an order shows a Receive action and its receipts history. Phone-friendly.
- Outlet display name from `org_outlet_registry`.
- No GL, journals, debits, credits, account codes, internal ids, or engineering labels on the page. Say clearly this is a goods receipt, not a bill and not a payment.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`).
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks. Tests use a temp sqlite. Never `shutil.copy2` the live catalog into a test.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787.
- Beta listener at launch is pid 89529, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement.

## Tests

Add `scripts/tests/test_bzg_p2p_recv1_20261005.py` on a temp sqlite. Cover: unauthenticated denied; no permission denied; non-existent / example order denied; line not on the order denied; qty above outstanding denied (including across two receipts); client-supplied outlet mismatch rejected; approver-as-receiver denied (if segregation applies); partial receipt keeps request not fully received; full receipt moves to RECEIVED via the helper; failed save leaves state unchanged; save then reload returns the same receipt; no bill / payment state set; protected close ids untouched in the fixture. Also re-run `scripts/tests/test_bzg_p2p_po1_20261004.py` and report it still passes.

## Result

Write `state/reliability/BZG-P2P-RECV-1-RESULT-2026-10-05.json` with pack_id `BZG-P2P-RECV-1`, status, staff_ready false, human_commissioned false, eng_proved false, routes, tables, permission, migration, backup path, files_changed, tests_pass / tests_fail for the new test and the PO regression, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built.

Stop when that result file is written.
