# Pack 2 — Uma Blu buy → receive → petty → close

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No staff clicked the page.

Verified 2026-10-01 from the Beta catalog `~/beta-os/catalog/content_library.sqlite` and a read-only open of `~/.openclaw/workspace/alchemist/data/alchemist.db`. Prod `:8787` was not written. Alchemist was opened `mode=ro`.

## What a named path can do

Buyer `PERS-DEVI` (Ni Putu Devi Parwati). Approver `PERS-MATT` (Matthew Goss), a different person. Devi holds `venue.receive` and `venue.close.submit`. Matt holds `work.complete` and `approval.decide` on the Uma target. Devi cannot approve her own request.

| Step | Result |
|---|---|
| Source shape | Alchemist `pr_orders.id` 557, `PR-1557`, vendor BU SEPTI, Kitchen, order_date 2026-09-30, status Received. 15 `pr_order_lines` rows. |
| Wolf PR | `PR-UMA-0E65E353A422`, `example=0`, state `RECEIVED`, 15 lines. Item, qty, and unit match the Alchemist lines. |
| Segregation | `approve_purchase_segregated` as Devi returns `self_approval_denied`. Matt decided `APR-292cc664-f235-4bef-93eb-78a6abbf43bd` (`GENERAL`, requester Devi, decision APPROVED). One request. Not the pack 10 approvals product. |
| Receipt | `RCP-d8d0d12a-903f-4f50-aa5e-216ed31394fe`, status `COMPLETE`, 15 `bzg_ops_receipt_lines`. Evidence `EVD-372162c1-d0ac-42a6-b5f3-5959c11f4621` (`receiving_document`). Alchemist not rewritten. |
| Petty | `PETTY-UMA-2321496C6D`, `example=0`, OUT, amount 50000, currency NULL, business_date 2026-10-01. Source Alchemist `petty_cash.id` 451 (Transport, Uma Blu outlet phone, Drive photo). The other 442 petty rows were not copied. No opening float. |
| Close, today | `VDC-3353351f-3234-4f7d-acf0-a63e0e176114`, 2026-10-01, state `OPEN`. ESB capture failed `esb_empty_day` (finished 0). Issue `ISS-UMA-12FD811939` OPEN. |
| Close, finished night | `VDC-25a3123a-3e26-43db-8085-10c6f208bbcd`, 2026-09-30, state `DATA_CAPTURED`. ESB totals on the row: finished 50, grand 15140000, cash_from_payments 2610000. That cash figure is ESB payment mix, not a till count. |
| Declared cash | Not attached. Alchemist `cash_count` has 0 rows. No till amount was invented. `declared_cash_evidence_id` is null on both closes. |

## Read-back

A second connection after commit read the same ids: PR state RECEIVED example 0, 15 PR lines, 1 receipt event, 15 receipt lines, petty example 0 amount 50000 currency null, approval APPROVED requested by PERS-DEVI decided by PERS-MATT.

`today_cards()` for 2026-10-01 returns the daily-close card with `attention=true`, `blocked=true`, `explain_kind=close_evidence_missing`, why: "Daily close has no declared-cash evidence. No till count was invented."

Unauthenticated `GET http://127.0.0.1:8788/api/bzg/uma-blu/today` after `launchctl kickstart` of `net.wolfcommand.serve-beta` returned **403** `missing_auth` (Cloudflare JWT fail-closed). `GET /api/health` on `:8788` returned 200 `{"ok": true, "root": "beta-os"}`. `GET /api/health` on `:8787` returned 200. Auth mode was not changed. The page was not human-clicked.

Temp-catalog test `scripts/tests/test_uma_buy_close_pack2.py`: 6 passed, 0 failed (self-approval denied, Matt decides one request, open close is blocked on the card). Existing BZG service-layer approve steps passed with the approver moved to PERS-MATT. Two HTML string checks in `test_bzg_ops_pack.py` and several HTTP identity checks in the operator-depth and loop tests still fail with `not authorized` / missing dashboard strings. Those failures are outside this pack's service chain. They were not treated as a pass.

A second run of `scripts/packs/pack02_uma_buy_close.py` left the counts at petty 1, issues 1, receipts 1, closes 2, approval requests 1.

## Left undone on purpose

Recipe costing and variance. Bills and three-way match. Payment. Xero. HR. Metricool write. Pre-open outlet sales. Historical backfill of 543 PRs or 443 petty rows. A human till count. `staff_ready`.

## NEXT — Pack 3, not started

Atrium sales desk. The 14 views, on the 88 units / 570 leads / 399 payments, as tabs under AMG. Occupancy card stays vacant-versus-rooms until in-house is known. Kuta tonight sits on the same hub. No housekeeping. Do not start it from this pack.
