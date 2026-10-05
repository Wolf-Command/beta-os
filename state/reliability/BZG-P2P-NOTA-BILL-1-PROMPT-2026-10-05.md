# BZG-P2P-NOTA-BILL-1 — supplier nota / bill captured against a saved goods receipt

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

Already built and reused (do not rebuild): purchase requests (`/bzg/uma-blu/bills`, `dashboards/bzg-uma-blu-pr.html`), purchase orders (BZG-P2P-PO-1: `/bzg/uma-blu/purchase-orders`, `scripts/core/bzg_purchase_order.py`, `bzg_ops_purchase_orders` / `bzg_ops_po_lines`), and goods receiving (BZG-P2P-RECV-1: `scripts/core/bzg_goods_receiving.py`, `bzg_ops_goods_receipts` / `bzg_ops_gr_lines`, permission `venue.receive`, test `scripts/tests/test_bzg_p2p_recv1_20261005.py`). State helpers live in `scripts/core/uma_ops_console.py` (`ALLOWED_TRANSITIONS`, `transition_pr`; `RECEIVED` → `BILL_RECEIVED` is already allowed). Segregation helpers live in `scripts/core/uma_devi_p0.py`.

Build the next step only: a real Beta **supplier nota / bill record** that an authenticated person saves against one already-saved goods receipt (and so its purchase order and request), with a photo of the paper nota, then reloads and sees again. Do not build three-way match, AP, ready-to-pay, or any payment. Do not rebuild requests, orders, receiving, Recipe Builder, Daily Close, or Petty Cash.

Before creating tables, inspect `bzg_ops_receipt_events` / `bzg_ops_receipt_lines` / `bzg_ops_receipt_slots` and the GGV nota code (`scripts/core/ggv_finance_nota.py`, `ggv_nota_files`) read-only. If an existing table or evidence/photo helper is truly the right home for a BZG supplier bill or its photo, reuse it; otherwise create `bzg_ops_supplier_bills` / `bzg_ops_bill_lines`. No second system of record. Do not write to any `ggv_*` table.

## Rules

- Source: one saved, non-example goods receipt in `bzg_ops_goods_receipts` with its lines. Outlet, supplier, order, and request are derived server-side from that receipt; display them locked and reject a client-supplied outlet, supplier, order, or receipt line that does not match.
- Staff record what is on the paper: supplier nota number, nota date, one photo (required; real upload path that persists and re-displays after reload), and per received line the billed qty and billed unit price as written, plus the nota total as written. Billed lines must be lines on that receipt. No new item names. Wolf calculates line amounts and the computed total; if the stated total differs from the computed total, save it and show a plain "difference Rp …" note — it must not block the save.
- Duplicate guard: the same supplier + nota number cannot be saved twice for the same outlet.
- Capturer is the authenticated person with an active assignment. Do not hardcode a person name. Reuse an existing permission if one truly fits (e.g. the receiving or purchasing one); otherwise add one small permission (e.g. `bzg.bill.capture`) granted by role, not by person name.
- State: on a successful save, move the request `RECEIVED` → `BILL_RECEIVED` via `transition_pr` only when the source request is fully received; a bill against a partial receipt is saved but leaves state unchanged. Failed save leaves states unchanged. Never set any `PAYMENT_*`, `PAID_CLAIMED`, or `CLOSED`.
- Idempotent migration with a backup of the live catalog before the live write. Audit the create.
- Do not invent receipts, notas, numbers, suppliers, or prices so the page looks full. The live catalog currently has zero purchase orders and zero goods receipts, so the page must show an honest empty state live.
- No GL, journals, debits, credits, account codes, internal ids, or engineering labels on the page. Finance does the accounting later. Say plainly this records the supplier's nota; it is not a payment and not an approval to pay.

## Page

- Extend the receiving view on `/bzg/uma-blu/purchase-orders` (or a linked `/bzg/uma-blu/supplier-bills` page) with an "Add supplier nota" action per receipt and a nota history. Phone-friendly, photo first.
- Outlet display name from `org_outlet_registry`.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`, `ggv_nota_files`, `ggv_nota_history`).
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks. Tests use a temp sqlite. Never `shutil.copy2` the live catalog into a test.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787.
- Beta listener at launch is pid 92970, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement.

## Tests

Add `scripts/tests/test_bzg_p2p_nota1_20261005.py` on a temp sqlite. Cover: unauthenticated denied; no permission denied; non-existent / example receipt denied; billed line not on the receipt denied; client-supplied outlet / supplier mismatch rejected; missing photo rejected; duplicate supplier+nota number rejected; stated-vs-computed total difference saved with a difference note (not blocked); bill on full receipt moves request to BILL_RECEIVED via the helper; bill on partial receipt leaves state unchanged; failed save leaves state unchanged; save then reload returns the same bill and photo reference; no payment state set; protected close ids untouched in the fixture. Re-run `scripts/tests/test_bzg_p2p_recv1_20261005.py` and `scripts/tests/test_bzg_p2p_po1_20261004.py` and report they still pass.

## Result

Write `state/reliability/BZG-P2P-NOTA-BILL-1-RESULT-2026-10-05.json` with pack_id `BZG-P2P-NOTA-BILL-1`, status, staff_ready false, human_commissioned false, eng_proved false, routes, tables (and whether reused), permission, migration, backup path, files_changed, tests_pass / tests_fail for the new test and both regressions, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built.

Stop when that result file is written.
