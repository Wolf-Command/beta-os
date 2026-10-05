# BZG history register — 5 Oct 2026

Read-only recount at 2026-10-05T07:34:54+08:00. No import started. staff_ready=false.

Writer was busy: `UMA-CLOSE-DATE-TRUTH-1` run `BF-5031a6f54de6` cursor pid 15569 cwd `/Users/wolfterminal/beta-os`. Import slice queued, not launched. Prod pid 1297 untouched.

## Cut lines

- V1 authoritative through: **UNKNOWN**. 29 Sep register says Uma ops `cutover_at` null and Alchemist remains the purchasing SoR.
- Alchemist observed maxima (not an authority end): PO order_date **2026-09-30**, ledger invoice **2026-09-30**, petty entry_date **2026-10-01** (created_at max 2026-10-01T15:37:01+08:00).
- ESB: Uma Blu POS only, branch BLZ, sales **2026-04-05 → 2026-10-04**, 183 days, 0 gaps inside that span. No `biz_date` 2026-10-05. goods_receipts **0**.
- Wolf/Beta daily closes begin business date **2026-09-28**. Finance SoR start for historical P2P: **UNKNOWN**.
- Bank files on disk: **Mar–Aug 2026** (Mandiri from Mar; BNI/BRI from Apr). **Sep and Oct 2026 statements are not on disk.** README says pre-start months are not a gap.
- Days with zero Alchemist orders inside the PO span are absence, not proved missing records. No `order_date` after 2026-09-30.

## Counts

| Dataset | Source | Beta | Linked | Unresolved | Status |
|---|---:|---:|---:|---:|---|
| Sales (ESB bills) | 9167 | 0 | 0 | 9167 | GAP |
| Daily closes | 8 | 8 | UNKNOWN | pre-28 Sep not in Beta | GAP |
| Tender lines | 8655 | 0 | 0 | 8655 | GAP |
| Bank statement files | 15 | 0 | 0 | 15 | GAP |
| Bank transactions | UNKNOWN | 0 | 0 | UNKNOWN | GAP |
| Bank reconciliations | 0 | 0 | 0 | UNKNOWN | GAP |
| Suppliers | 103 | 0 | 0 | 103 | GAP |
| PO / PR documents (pr_orders) | 543 | 0 PO / 4 PR text | 0 | 543 | GAP |
| PO lines | 2017 | 0 | 0 | 2017 | GAP |
| Receipt lines | 477 (104 PRs) | 0 historical | 0 | 477 | GAP |
| Deliveries table | 0 | 0 | 0 | 0 | GAP |
| Ledger / notas book | 473 | 0 | 0 | 473 | GAP |
| Nota-prefix images | 2 | 0 | 0 | 2 | GAP |
| Petty cash | 443 | 17 live | 0 | 443 | GAP |
| AP unpaid | 106 | 0 | 0 | 106 | GAP |
| Paid ledger | 362 | 0 in Beta | 464 Alchemist L-id links | 362 | NEEDS RECONCILIATION |
| ESB GL journal | 6062 | 0 | 0 | 6062 | GAP |
| Recipes | 127 / 756 lines | not in content_library | 0 | 127 | GAP |
| Evidence jpg | 1379 | 16 live petty | 16 | 1363 | EVIDENCE UNLINKED |

PO status: Paid 304, Received 166, Awaiting Devi 39, Cancelled 27, Ordered 6, Rejected 1. pr_num duplicates 0. Supplier name collision: Bake House ids 5 and 90.

Petty fingerprint collisions: 33 groups, 36 extra rows. Not merged. One entry_date 2026-01-09 (id 317) was created 2026-09-01 — bad date, not January history.

Live Uma petty balance was not changed. Opening float 2026-10-02 Rp56,000 plus movements from that date = **Rp52,700**. Sum of all 17 movements from zero is -53,300 and is not the live balance. Do not duplicate PETTY-UMA-6E512800FE or PETTY-UMA-80867C2504. Do not insert 2,300 or force 55,000.

Protected closes read, not written: VDC-470e741f EXCEPTION cash 3225000 variance -125000 updated_at 2026-10-03T13:47:39Z; VDC-87202768 CANCELLED; VDC-64f5f529 DATA_CAPTURED declared cash null.

Zayen active scopes: AMG finance and BZG finance. No GGV finance scope on Zayen. Amanda finance scope is GGV only. Matt has GGV, AMG, and BZG. Switcher not proved. Zayen NOT READY.

Old ~514 / 1883 / 435 / 433 figures are the 29 Sep UMAREAL snapshot, not this recount.

