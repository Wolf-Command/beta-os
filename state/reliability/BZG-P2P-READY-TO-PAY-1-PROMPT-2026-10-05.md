# BZG-P2P-READY-TO-PAY-1 — show matched bills allowed to be paid later (no money sent)

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. One finishable slice. The tree is already dirty. Do not commit, push, merge, or clean the git tree. Do not edit `scripts/build-factory/` (the factory owns it). Do not print process command lines, tokens, or secrets. No messaging anyone.

## The one step

Already built and reused (do not rebuild): purchase requests, purchase orders (BZG-P2P-PO-1), goods receiving (BZG-P2P-RECV-1), supplier nota / bill (BZG-P2P-NOTA-BILL-1), three-way match (BZG-P2P-THREE-WAY-1), and AP-ready (BZG-P2P-AP-1). State helpers live in `scripts/core/uma_ops_console.py` (`ALLOWED_TRANSITIONS`, `transition_pr`). Segregation helpers live in `scripts/core/uma_devi_p0.py`.

Build the next step only: a real Beta **Ready to Pay** list that shows matched bills that are allowed to be paid later. Do not send money. Do not connect a bank payment. Do not execute `PAYMENT_*` / `PAID_CLAIMED` / `CLOSED`. Do not rebuild AP, match, nota, receiving, orders, Recipe Builder, Daily Close, Petty Cash, or Owner Home.

## Rules

- Source: bills that already sit AP-ready from a matched chain. Outlet and supplier stay locked from the upstream documents; reject a client-supplied outlet, supplier, order, receipt, or bill that does not match the chain.
- Ready to Pay means: an authenticated controller can see which matched bills are allowed to be paid later — a list and a clear status only. Persist that flag/list (e.g. `bzg_ops_ready_to_pay` or a clear status field if one already fits). No second system of record. Do not write to any `ggv_*` table.
- Hard ban this slice: no bank API, no transfer, no disbursement, no payment file export that moves money, no `transition_pr` into `PAYMENT_REQUESTED`, `PAYMENT_APPROVED`, `PAID_CLAIMED`, `PAYMENT_VERIFIED`, or `CLOSED`. Showing "allowed later" is not approving or executing payment.
- Actor is the authenticated person with an active assignment. Do not hardcode a person name. Reuse an existing permission if one truly fits; otherwise add one small permission (e.g. `bzg.pay.list_ready`) granted by role, not by person name.
- Idempotent migration with a backup of the live catalog before the live write. Audit the change.
- Do not invent bills or amounts so the page looks full. Honest empty state when none are eligible.
- No GL, journals, debits, credits, account codes, internal ids, or engineering labels on the page. Say plainly these bills may be paid later; this screen does not send money.

## Page

- Extend the AP / purchasing controller view (or a linked `/bzg/uma-blu/ready-to-pay` page) with the Ready to Pay list. Phone-friendly. No "Pay now" that executes.
- Outlet display name from `org_outlet_registry`.
- `staff_ready` stays false. `human_commissioned` stays false. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate these `catalog/content_library.sqlite` rows: `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`, `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`, `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`. Do not touch GGV finance tables (`ggv_bills`, `ggv_invoices`, `ggv_notas`, `ggv_vendors`, `ggv_nota_files`, `ggv_nota_history`) — leave the GGV 605 bills / 46 invoices / 33 notas alone.
- Read the live catalog only with Python `sqlite3` `mode=ro` for checks. Tests use a temp sqlite. Never `shutil.copy2` the live catalog into a test.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it, restart it, or touch port 8787. Production untouched.
- Beta listener at launch is pid 92970, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only needs no reload. After any reload, 8788 must have exactly one listener and 1297 must still be the only listener on 8787.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone. No second writer. No money movement. No bank payment connection.

## Tests

Add `scripts/tests/test_bzg_p2p_ready_to_pay1_20261005.py` on a temp sqlite. Cover: unauthenticated denied; no permission denied; non-AP-ready bill cannot appear; client-supplied outlet / supplier mismatch rejected; AP-ready matched bill can appear on the Ready to Pay list; save then reload returns the same list/status; no payment execution state set; no bank fields required; protected close ids untouched in the fixture. Re-run AP, three-way, nota, recv, and PO regression tests and report they still pass.

## Result

Write `state/reliability/BZG-P2P-READY-TO-PAY-1-RESULT-2026-10-05.json` with pack_id `BZG-P2P-READY-TO-PAY-1`, status, staff_ready false, human_commissioned false, eng_proved false, routes, tables (and whether reused), permission, migration, backup path, files_changed, tests_pass / tests_fail for the new test and regressions, beta_reloaded plus 8788 listener pid, prod pid unchanged, protected_close_untouched, no_prod true, no_commit true, no_money_movement true, what_was_not_built.

Stop when that result file is written.
