# Uma Blu 29 September 2026 ESB date truth

Read-only proof. Written 2026-10-05 morning WITA (UTC+8). No close row was updated by this proof. No ESB API call was made. Warehouse read: `file:/Users/wolfterminal/.openclaw/data/esb.sqlite?mode=ro`. Close read: `file:/Users/wolfterminal/beta-os/catalog/content_library.sqlite?mode=ro`.

## Verdict

**29 SEP cash Rp4,135,000 and finished bills 51 are CORRECT.**

They are the payment-line cash sum and the Finished-bill count for outlet Uma Blu (branch BLZ) on business date 2026-09-29 only. They are not copied from 28 Sep, 30 Sep, or today. Settlement / end-of-day report is not available, so there is no second official cash figure to prefer.

## Path traced

1. Screen / API asks for a business date. `serve_beta.py` `_venue_close_get` reads `business_date` and calls `venue_close.get_close(business_date=date)` for `by-date`. Open uses `bzg_daily_close.open_human_close(business_date, outlet_id)` default outlet `BZG-UMA`. Capture calls `venue_close.capture_esb_snapshot(..., business_date=body.business_date)`.
2. `get_close` loads `venue_daily_closes` where `entity_id=ENT-BZG`, `venue_brand_id=BZG-UMA`, `business_date` equals the requested date, `state != CANCELLED`, newest `created_at`.
3. Capture calls `esb_close_snapshot.snapshot_day(close.business_date)` with default branch `BLZ`. `_assert_esb_snapshot_matches_close` refuses if the snapshot date is not the close date (`wrong_business_date`).
4. `snapshot_day` runs `SELECT nk, biz_date, raw, pulled_at FROM sales WHERE biz_date=?` then keeps only `branchCode == BLZ` and `statusName == Finished`. Cancelled bills are counted and excluded from money. Blank branch code is excluded.
5. `sales.biz_date` is not computed in Beta. `esb_ingest.py` `pull_sales` stores `biz_date = salesDate` from `GET /corev1/sales/sales-information?salesDateFrom=&salesDateTo=`. `--date YYYY-MM-DD` pulls that same day for both bounds. Ingest `pulled_at` is stamped `Asia/Makassar` (WITA, UTC+8). The snapshot query does not filter on `pulled_at`.
6. Cash is the sum of `salesPayments.paymentAmount` whose method classifies as CASH. QRIS is split out of TypeName CARD when `paymentMethodName` contains QRIS. Card bucket is everything else classified CARD, including house methods. There is no settlement table in `esb.sqlite`. `esb_settlement_path1.py` records `settlement_api: UNAVAILABLE`.

## 29 SEP ESB SOURCE

Warehouse table `sales`, path `/Users/wolfterminal/.openclaw/data/esb.sqlite`. 51 rows with `biz_date='2026-09-29'`. Each raw bill: `branchCode=BLZ`, `branchName=UMA BLU`, `statusName=Finished`, `salesDate=2026-09-29` (date only). `sales_menu_summary` for the same date is one row, branch BLZ / UMA BLU, menus only, no payment totals.

Natural keys in the whole `sales` table (9167 rows) are prefixed `BLZ` only.

## OUTLET FILTER

Code: `esb_close_snapshot.BRANCH_CODE = "BLZ"`, then `branchCode` must equal that. Close row outlet is `BZG-UMA` / brand `BZG-UMA`. Payload branch name on every 29 Sep row is `UMA BLU`. No other branch is in the 28 Sep–4 Oct window. Skipped other-outlet finished bills on 29 Sep: 0.

## BUSINESS DATE FILTER

SQL equality `biz_date = '2026-09-29'`. `biz_date` is the ESB `salesDate` field. Independent check of all 51 rows: `salesDate`, `salesDateIn` date, and `salesDateOut` date are all `2026-09-29`. Bills whose `salesDateOut` falls on 29 Sep but whose `biz_date` is another day in 27 Sep–5 Oct: none. Bills on `biz_date` 29 Sep with `salesDateOut` on another day: none.

## TIMEZONE / CUTOFF

No timezone conversion inside `snapshot_day`. Cutoff is ESB `salesDate` (calendar date) plus the wall-clock `salesDateIn` / `salesDateOut` strings, which have no offset. On 29 Sep those out-times run from `2026-09-29 07:13:32` through `2026-09-29 20:51:01`. Ingest labels its own pull clock `WITA = UTC+8` (`Asia/Makassar`). `pulled_at` on these rows is `2026-10-05T05:47:40.362801+08:00`. That is when the warehouse row was written, not the business date. Today is 2026-10-05. The 29 Sep query does not include 5 Oct sales. Not live/today contamination.

## CASH

**4,135,000.00** stored and recomputed (`cash_from_payments`).

Fifteen CASH `paymentAmount` lines, `fullPaymentAmount` equal to `paymentAmount` on every line, sum **4135000**:

| salesNum | cash tendered | bill grandTotal | salesDateOut |
|---|---:|---:|---|
| SBLZ179064026604 | 700000 | 660000 | 2026-09-29 10:35:09 |
| SBLZ179064150326 | 100000 | 75000 | 2026-09-29 08:46:56 |
| SBLZ179064315429 | 345000 | 345000 | 2026-09-29 09:57:55 |
| SBLZ179064324242 | 100000 | 65000 | 2026-09-29 08:54:10 |
| SBLZ179064340464 | 250000 | 230000 | 2026-09-29 09:25:55 |
| SBLZ179064458928 | 35000 | 115000 | 2026-09-29 14:44:31 |
| SBLZ179064553543 | 400000 | 400000 | 2026-09-29 10:19:08 |
| SBLZ179065311763 | 200000 | 190000 | 2026-09-29 12:03:22 |
| SBLZ179065406080 | 200000 | 145000 | 2026-09-29 13:06:29 |
| SBLZ179065414868 | 600000 | 545000 | 2026-09-29 13:13:12 |
| SBLZ179066422309 | 500000 | 425000 | 2026-09-29 15:25:37 |
| SBLZ179066495396 | 105000 | 105000 | 2026-09-29 15:28:27 |
| SBLZ179067198657 | 90000 | 90000 | 2026-09-29 17:12:19 |
| SBLZ179067631010 | 160000 | 160000 | 2026-09-29 18:50:55 |
| SBLZ179067920992 | 350000 | 320000 | 2026-09-29 19:38:08 |

Nine of those bills have cash tender above the bill grand total. Overpay = tender − grand: 40000+25000+35000+20000+10000+55000+55000+75000+30000 = **345000**. Stored `cash_change_overpay` is 345000. Stored `cash_sales_grand` (grand total of bills that have any cash, not net cash) is 3870000. This 345000 is change on those bills. It is not a settlement cash figure. The screen number is tendered cash, which is what the close stores.

## FINISHED BILLS

**51**. All 51 warehouse rows for the date are Finished. Cancelled 0. Other status 0. One finished bill is other-cost only (`other_cost_bill_count` 1), so `sales_bill_count_excl_other_cost` is 50. The screen count 51 is the finished count, including that one other-cost bill.

## GROSS

Unrounded sum of raw `grandTotal` on the 51 finished bills: **13513512.397**. Snapshot / stored `grand_total` (rounded to 2 dp by `snapshot_day`): **13513512.40**.

## NET

No field named net, and no `serviceCharge` field, on the bill. Unrounded sums of the raw fields that exist:

- subtotal **11181818.1790**
- vatTotal **1110330.5781**
- otherTaxTotal **1221363.6364**
- otherVatTotal 0, roundingTotal 0, deliveryCost 0, orderFee 0
- discountTotal 0, menuDiscountTotal 0, promotionDiscount 0, voucherDiscountTotal 0
- subtotal + vatTotal + otherTaxTotal = **13513512.3935** (0.0035 below the grandTotal sum; per-bill ESB rounding, not another day)

Canonical money the close stores is `grand_total` 13513512.40, not a separate net. Pre-tax subtotal rounded to 2 dp is 11181818.18. `otherTaxTotal` is the non-VAT tax component. It was not renamed to service.

## EDC

Code bucket `card_from_payments` (what the close compares as the card/EDC side): **8435000.00**.

That bucket is not all bank EDC. Method names on 29 Sep:

- EDC BNI **2545000**
- EDC BRI **4465000**
- bank EDC subtotal **7010000**
- SCOTT & ETIK **1425000** (TypeName CARD, house method, not a terminal)
- no EDC Mandiri on this date

TypeName mix still says CARD **9645000** because QRIS lines are TypeName CARD. The snapshot splits them by method name. 8435000 + 1210000 = 9645000.

## QRIS

**1210000.00** (`qris_from_payments`). QRIS BNI 145000 + QRIS BRI 1065000. No QRIS Mandiri on this date.

## OTHER

**78512.40** (`other_from_payments`). Method name `Executife Chef`, bank-split key `EXECUTIVE_CHEF`, TypeName OTHER COST.

Payment lines sum: 4135000 + 8435000 + 1210000 + 78512.40 = **13858512.40**, matching stored `payment_total`. Unrounded raw `paymentTotal` sum is 13858512.3967.

## VOIDS / DISCOUNTS

Cancelled bills: 0. Menu lines: 175, all `statusID=13` / `statusName=Preparing`. `cancelNotes` empty on every line. Menu discount sum 0. Bill discount fields 0. No void amount was found to add back.

## PRINTED SHIFT REPORT COMPARISON

**NOT AVAILABLE.**

- `venue_close_esb_closing_receipts` for close `VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad`: 0 rows
- `venue_close_till_evidence`: 0 rows
- `venue_close_edc_receipts`: 0 rows
- `venue_close_final_history`: 0 rows
- close `work_item_id` is null
- `evidence_items`: no row whose ref or content matches 2026-09-29, shift, or this close id
- NAS `/Volumes/01-Media-Library/BZG/Uma-Blu-Cafe/2026` is empty. A depth-2 name search under `One-Touch` and `_dropbox` found no shift / esb / close / 2026-09-29 filename.

`sales_menu_summary` is a menu list, not a shift settlement. Settlement API remains UNAVAILABLE in code and there is no settlement table in the warehouse. Canonical close source is therefore these payment lines.

## Wolf snapshot (source C)

One close for 2026-09-29: `VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad`.

- entity ENT-BZG, brand BZG-UMA, outlet BZG-UMA
- state DATA_CAPTURED (unfinished draft, not COMPLETED)
- created_at 2026-10-04T23:19:46Z
- updated_at 2026-10-04T23:21:20Z
- esb_pulled_at 2026-10-05T05:47:40.362801+08:00
- fingerprint `af1310a02e5ffe5c9a5e9ce29bbab6dc6dada93b4691a4843c4b2ac61543c724`
- query meta branch BLZ, business_date 2026-09-29, finished_count 51, bill_count 51, cancelled 0
- stored totals: cash 4135000.0, card 8435000.0, qris 1210000.0, other 78512.4, grand 13513512.4, payment 13858512.4, finished 51

Recomputing `snapshot_day('2026-09-29')` in this proof produced the same fingerprint and the same rounded totals. The stored snapshot is this date's warehouse, not another close. `fingerprint_stale` is 0.

## Adjacent dates (same filter, own rows)

Warehouse recomputed with the same BLZ + Finished + payment-line rules. Cash figures are all different. No two dates share both cash and finished-bill count. 2 Oct and 4 Oct both have 61 finished bills but cash 2855000 vs 360000.

| business date | warehouse rows | finished | cancelled | cash | card bucket | qris | other | grand (rounded by snapshot_day) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-28 | 61 | 58 | 3 | 2460000.00 | 12540000.00 | 905000.00 | 107438.02 | 15862438.02 |
| 2026-09-29 | 51 | 51 | 0 | 4135000.00 | 8435000.00 | 1210000.00 | 78512.40 | 13513512.40 |
| 2026-09-30 | 54 | 50 | 4 | 2610000.00 | 11620000.00 | 1080000.00 | 0.00 | 15140000.00 |
| 2026-10-01 | 50 | 45 | 5 | 2435000.00 | 8865000.00 | 1855000.00 | 119834.71 | 13114834.71 |
| 2026-10-02 | 66 | 61 | 5 | 2855000.00 | 13490000.00 | 2170000.00 | 219008.26 | 18614008.26 |
| 2026-10-03 | 56 | 52 | 4 | 3465000.00 | 9590000.00 | 2215000.00 | 0.00 | 15030000.00 |
| 2026-10-04 | 67 | 61 | 6 | 360000.00 | 15155000.00 | 3570000.00 | 103305.79 | 19158305.79 |

`salesDate` / `salesDateIn` / `salesDateOut` calendar dates matched `biz_date` on every row in this window. Every row was BLZ / UMA BLU.

## Why the screen is not wrong

Rp4,135,000 is the 15-line cash tender sum. 51 is the finished bill count. Both match source A (warehouse) and source C (this close's `esb_totals_json`). Source B does not exist. Do not replace the 29 Sep draft. Do not change the query's date or outlet results for this date; the rows already are Uma Blu on 29 Sep only.

## Protected closes (read only, not edited)

- VDC-470e741f-d889-437a-9a40-1ec9c083fb95 state EXCEPTION, declared_cash_amount 3225000.0, variance_cash_amount -125000.0, updated_at 2026-10-03T13:47:39Z
- VDC-87202768-55af-4c8e-abc3-382a5496b8c6 state CANCELLED, updated_at 2026-10-03T12:32:22Z
- VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5 state DATA_CAPTURED, declared_cash_amount NULL, updated_at 2026-10-04T13:56:05Z

## Live mutation

None. This proof only read SQLite mode=ro and source files.
