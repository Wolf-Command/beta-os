# Petty balance provenance — Uma Blu — 2026-10-05

Read-only proof. No ledger row was inserted, edited, or deleted. Rp2,300 was NOT inserted. The ledger was NOT forced to Rp55,000.

- Proven at: 2026-10-05 about 07:25 WITA (Asia/Makassar, UTC+8)
- Catalog: `/Users/wolfterminal/beta-os/catalog/content_library.sqlite` opened `file:...?mode=ro` (Python sqlite3). This is the file `scripts/core/uma_ops_console.py` and `scripts/serve_beta.py` read (`CATALOG_DB`).
- Tables: `bzg_ops_petty_movements`, `bzg_ops_petty_days`. Column names taken from `PRAGMA table_info`.
- Page: `dashboards/bzg-uma-blu-petty.html` displays `data.current_balance` from `list_petty()` → `reconcile_petty_balance()`.
- Venue filter: `venue='BZG-UMA'`, `example=0`.
- Business date for the page: `today_biz_date()` = 2026-10-05 (WITA).

## Display rule (code, not a guess)

`reconcile_petty_balance` takes the latest `bzg_ops_petty_days.opening_float` with `business_date <= as_of`, then adds IN and subtracts OUT for movements with `business_date >= that anchor date`.

Anchor used for 2026-10-05:

- Day `2026-10-02`, `opening_float` = **56000**
- `opening_float_source` = `human_supplied`
- `opening_float_set_by` = Matt Goss
- `opening_float_set_at` = 2026-10-01T23:52:23Z (2026-10-02 07:52 WITA)
- `opening_float_kind` = `human_supplied_opening_balance`
- `note` = Human-supplied opening balance by Matt Goss

`state/reliability/PETTY-CHAIN-VERIFICATION-ANCHORS.json` has anchors only for 2026-10-03 (opening 560000) and 2026-10-04 (opening 505000, stated 55000). None match `as_of` 2026-10-05, so they do **not** replace today's displayed balance. Today has no day row and no proven opening_float.

## Arithmetic that equals the displayed balance

Start **56000** (2 Oct opening). Every later non-example Uma movement:

| movement_id | type | amount | actor (`logged_by`) | business_date | created_at (Z) | outlet | running |
|---|---|---:|---|---|---|---|---:|
| PETTY-UMA-36743CB1E2 | IN | 500000 | Owner | 2026-10-02 | 2026-10-02T04:28:48Z | Uma Blu | 556000 |
| PETTY-UMA-898F771D08 | OUT | 26000 | Owner | 2026-10-02 | 2026-10-02T04:30:14Z | Uma Blu | 530000 |
| PETTY-UMA-535A0CBDE0 | OUT | 45300 | Owner | 2026-10-02 | 2026-10-02T13:47:51Z | Uma Blu | 484700 |
| PETTY-UMA-3E3916F24A | OUT | 42000 | Owner | 2026-10-02 | 2026-10-02T13:48:34Z | Uma Blu | 442700 |
| PETTY-UMA-E53F9B191A | OUT | 20000 | Owner | 2026-10-02 | 2026-10-02T13:49:18Z | Uma Blu | 422700 |
| PETTY-UMA-3B76ACAAB3 | OUT | 14000 | Owner | 2026-10-02 | 2026-10-02T13:49:56Z | Uma Blu | 408700 |
| PETTY-UMA-588D5C787F | OUT | 350000 | Owner | 2026-10-02 | 2026-10-02T13:50:44Z | Uma Blu | 58700 |
| PETTY-UMA-266BD262E4 | IN | 500000 | Owner | 2026-10-02 | 2026-10-02T14:12:40Z | Uma Blu | 558700 |
| PETTY-UMA-0153380282 | OUT | 500000 | Owner | 2026-10-02 | 2026-10-02T14:13:12Z | Uma Blu | 58700 |
| PETTY-UMA-9EE4DF7AFB | IN | 500000 | Owner | 2026-10-02 | 2026-10-02T14:13:37Z | Uma Blu | 558700 |
| PETTY-UMA-A172457171 | OUT | 490000 | Owner | 2026-10-03 | 2026-10-03T13:50:05Z | Uma Blu | 68700 |
| PETTY-UMA-74588A9330 | OUT | 50000 | Owner | 2026-10-03 | 2026-10-03T13:51:06Z | Uma Blu | 18700 |
| PETTY-UMA-7883C01A50 | OUT | 15000 | Owner | 2026-10-03 | 2026-10-03T13:51:45Z | Uma Blu | 3700 |
| PETTY-UMA-060F581083 | IN | 500000 | Owner | 2026-10-03 | 2026-10-03T13:52:40Z | Uma Blu | 503700 |
| PETTY-UMA-6E512800FE | OUT | 430000 | Iza Zainatulloh Hulhidayati | 2026-10-04 | 2026-10-04T12:43:04Z | Uma Blu | 73700 |
| PETTY-UMA-80867C2504 | OUT | 21000 | Iza Zainatulloh Hulhidayati | 2026-10-04 | 2026-10-04T12:44:12Z | Uma Blu | **52700** |

**Displayed ledger balance = Rp52,700.** This is the true sum under the page's reconcile rule. It is not a rounded or invented figure.

Check: IN after anchor 2,000,000 − OUT after anchor 2,003,300 + opening 56,000 = 52,700.

## Movement excluded from the displayed sum (not missing)

- `PETTY-UMA-2321496C6D` OUT Rp50,000, `logged_by` NULL, business_date 2026-10-01, created_at 2026-10-01T11:37:10Z, outlet NULL, venue BZG-UMA, example 0, purpose transport / Alchemist petty_cash id 451.
- Excluded because its business date is before the 2026-10-02 opening anchor. It is still in the table, unchanged. No other Uma petty movement exists (17 rows total, all example=0).

All-time IN 2,000,000 − all-time OUT 2,053,300 = net −53,300. That is not the displayed balance, because the 2 Oct opening replaces the pre-anchor chain.

## Earlier model vs this proof (do not force either number)

- Earlier model: 4 Oct reference opening Rp505,000 − Iza OUT Rp451,000 (430,000 + 21,000, each id once) = derived Rp54,000.
- Chain position immediately before those two OUTs is **Rp503,700**, not Rp505,000. Unrecorded gap vs that model: Rp1,300. After the two OUTs the chain is Rp52,700, which is Rp1,300 below the old derived Rp54,000.
- Owner previously said physical Rp55,000 vs derived Rp54,000 (Rp1,000). Owner now says the page shows Rp52,700 and physical should be Rp55,000 (gap Rp2,300). 1,300 + 1,000 = 2,300. That arithmetic explains the new gap. It is not a stored movement.

## Coins / Rp2,300 — not proved

- `bzg_ops_petty_days.counted_amount` is NULL on every Uma day (0 counted rows).
- No coin, cash-count, or reconciliation movement of Rp2,300 exists.
- Therefore coins are **not proved**. The repair must show an unproved difference. Do not manufacture Rp2,300. Do not post an adjustment. Do not edit any existing row.

## Protected history that must stay unchanged

- `PETTY-UMA-6E512800FE` OUT 430000, Iza, once.
- `PETTY-UMA-80867C2504` OUT 21000, Iza, once.

Protected closes read at proof time (not mutated):

- `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` business_date 2026-10-03, state EXCEPTION, outlet BZG-UMA, declared_cash_amount 3225000, variance_cash_amount -125000, updated_at 2026-10-03T13:47:39Z
- `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` business_date 2026-10-02, state CANCELLED, declared_cash_amount NULL, updated_at 2026-10-03T12:32:22Z
- `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5` business_date 2026-10-04, state DATA_CAPTURED, outlet Uma, declared_cash_amount NULL, updated_at 2026-10-04T13:56:05Z. Do not write 360000. Do not edit esb_totals_json.

## Rp2,300 inserted?

**NO.**
