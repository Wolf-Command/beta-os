# BZG-P2P-AP-1 — matched bill sits ready for the controller (AP view only)

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

Already built and reused (do not rebuild): purchase requests, purchase orders (BZG-P2P-PO-1), goods receiving (BZG-P2P-RECV-1), supplier nota / bill (BZG-P2P-NOTA-BILL-1: `scripts/core/bzg_supplier_bill.py`), and three-way match (BZG-P2P-THREE-WAY-1). State helpers live in `scripts/core/uma_ops_console.py` (`ALLOWED_TRANSITIONS`, `transition_pr`). Segregation helpers live in `scripts/core/uma_devi_p0.py`.

Build the next step only: a real Beta **AP surface** where a bill that already matched can sit as ready for the controller to see. No payment execution. Do not build ready-to-pay lists that send money, bank payment, or any money movement. Do not rebuild requests, orders, receiving, nota, three-way match, Recipe Builder, Daily Close, Petty Cash, or Owner Home.

## Rules

- Source: one saved supplier nota / bill that already has a three-way match result of match (or an explicitly accepted difference if the match slice records that). Outlet and supplier stay locked from the upstream documents; reject a client-supplied outlet, supplier, order, receipt, or bill that does not match the chain.
- AP means: the matched bill is visible to an authenticated controller as sitting ready to review — not paid, not bank-connected, not executed. Persist that AP-ready status beside the bill (e.g. small table `bzg_ops_ap_ready` or a clear status field on the bill row if one already exists and fits). No second system of record. Do not write to any `ggv_*` table.
- Do not call `transition_pr` into any `PAYMENT_*`, `PAID_CLAIMED`, or `CLOSED` state. Do not invent payment approval. If you must note controller visibility, keep the request at `BILL_RECEIVED` (or the honest post-match state) and record AP-ready beside it.
- Actor is the authenticated person with an active assignment. Do not hardcode a person name. Reuse an existing permission if one truly fits; otherwise add one small permission (e.g. `bzg.ap.view` / `bzg.ap.mark_ready`) granted by role, not by person name.
- Idempotent migration with a backup of the live catalog before the live write. Audit the change.
- Do not invent matched bills, suppliers, or amounts so the page looks full. Honest empty state when none are eligible.
- No GL, journals, debits, credits, account codes, internal ids, or engineering labels on the page. Say plainly this is AP-ready for the controller to see; it is not a payment and not an approval to pay.

## Page

- Extend the purchasing / finance controller view on `/bzg/uma-blu/purchase-orders` (or a linked `/bzg/uma-blu/ap` page) with a list of matched bills sitting ready for the controller. Phone-friendly.
- Outlet display name from `org_outlet_registry`.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`, `ggv_nota_files`, `ggv_nota_history`) — leave the GGV 605 bills / 46 invoices / 33 notas alone.
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks. Tests use a temp sqlite. Never `shutil.copy2` the live catalog into a test.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787. Production untouched.
- Beta listener at launch is pid 92970, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement. No bank payment connection.

## Tests

Add `scripts/tests/test_bzg_p2p_ap1_20261005.py` on a temp sqlite. Cover: unauthenticated denied; no permission denied; unmatched bill cannot sit AP-ready; client-supplied outlet / supplier mismatch rejected; matched bill can sit ready for the controller; save then reload returns the same AP-ready row; no payment state set; protected close ids untouched in the fixture. Re-run the three-way, nota, recv, and PO regression tests and report they still pass.

## Result

Write `state/reliability/BZG-P2P-AP-1-RESULT-2026-10-05.json` with pack_id `BZG-P2P-AP-1`, status, staff_ready false, human_commissioned false, eng_proved false, routes, tables (and whether reused), permission, migration, backup path, files_changed, tests_pass / tests_fail for the new test and regressions, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built.

Stop when that result file is written.
