# UMA-CLOSE-4OCT-FAIL — surgical repair

Human fail. Iza is on the real 4 October Uma Blu close on her phone. Do not commission. Do not redesign Daily Close.

## Locked close
- Repair under existing close `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5` (business_date 2026-10-04, outlet BZG-UMA, state DATA_CAPTURED, submitted_by PERS-IZA).
- `declared_cash_amount` is NULL in the row. Do NOT write 360000 into it. The screenshot label "Declared cash Rp360,000" is suspected to be the ESB cash figure mis-labeled.
- Do NOT mutate `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` (3 Oct EXCEPTION, declared 3225000, variance -125000, updated_at 2026-10-03T13:47:39Z) or `VDC-87202768-55af-4c8e-abc3-382a5496b8c6`.

## Already proved in the frozen snapshot (do not invent numbers)
`esb_totals_json` pulled 2026-10-04T21:24:19+08:00 already contains:
- cash_from_payments 360000
- cash_sales_grand 330000
- cash_change_overpay 30000
- finished_count 61
- bill_count 67
The screen shows ESB cash as blank and shows 61 under Variance. That is a UI binding bug, not missing ESB data. Use the close engine's existing ESB-cash field. Do not invent a third number. Do not borrow 3 Oct. Do not call live ESB if the frozen 4 Oct snapshot already has payment lines.

## Display (staff language only)
Separate lines, never nested:
- ESB cash
- Petty cash paid today (automatic, from the petty ledger, once)
- Expected cash
- Cash counted
- Difference (MATCHES or DIFFERENCE Rp)
- Finished bills (61 stays its own line, never under Difference)
If a figure cannot be calculated, say "Cannot calculate yet". Never show a fake variance.

No GL, journals, debits, credits, cost centres, account codes, outlet dropdown, Reconcile button, or accounting mapping. Do not ask her to re-pick person, outlet, business, or date.

## Photo
Printed ESB shift report Take Photo / Upload Photo must work on a phone: picker opens, file uploads, original stored, bound to BZG / Uma Blu / 2026-10-04 / Iza / this close. If the image reader fails, the photo still stays and she can type the numbers. Do not block the close on reader failure. Trace the real route, not only a DOM test.

## Petty
Same-day authorised OUT already persisted, count once, do not re-enter:
- PETTY-UMA-6E512800FE 430000 Nasi bungkus
- PETTY-UMA-80867C2504 21000 Laundry
Total OUT 451000. Opening reference 505000. Derived petty balance 54000. Owner stated 55000. Gap 1000 is Finance. Do not show her an accounting investigation. Do not force 55000. Do not block the close for that gap.
If the existing cash model subtracts same-day petty OUT from expected cash, do it exactly once. Do not add a new accounting model.

## Submit
One button. One result: CLOSE COMPLETE, or CLOSE SAVED WITH EXCEPTION, or CANNOT SUBMIT plus a plain reason. Repeat taps do not write twice.

## Limits
Beta only. Do not restart prod (pid 1297 on 127.0.0.1:8787). Do not commit. Do not push. Do not copy the live catalog for tests. Reload Beta only if Python changed and only one listener is on 8788.
Write `state/reliability/UMA-CLOSE-4OCT-PHOTO-ESB-RESULT-2026-10-04.json` with: photo proved or the exact failed hop, which ESB field is shown, expected-cash formula with the real numbers, whether declared stayed null, whether 61 is off the variance line, protected close unchanged, beta pid, prod pid.
