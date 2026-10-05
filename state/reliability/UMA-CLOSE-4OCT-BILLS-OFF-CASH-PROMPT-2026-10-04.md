# UMA close 4 Oct — move finished bills out of the cash block

Peaches verified the previous takeover run failed the Owner's display rule.
Do not treat the previous 17/0 as a pass.

## Confirmed live truth (do not change these facts)
- Close id: VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5
- business_date 2026-10-04, outlet BZG-UMA, state DATA_CAPTURED
- submitted_by_person_id PERS-IZA, created_at 2026-10-04T13:24:15Z
- taken_by_person_id already PERS-MATT, taken_at 2026-10-04T13:56:05Z
- declared_cash_amount is NULL. Leave it NULL.
- esb_totals_json already has cash_from_payments 360000 and finished_count 61. Do not edit that JSON. Do not call live ESB.
- Only one 4 Oct Uma close. Do not create another.
- Protected, do not touch:
  - VDC-470e741f-d889-437a-9a40-1ec9c083fb95 EXCEPTION declared 3225000 variance -125000 updated_at 2026-10-03T13:47:39Z
  - VDC-87202768-55af-4c8e-abc3-382a5496b8c6 CANCELLED updated_at 2026-10-03T12:32:22Z
- Do not take over again. Do not change taken_by. Do not erase Iza.

## The defect, still in dashboards/uma-blu-close.html
renderStaffCashBox builds:
staffCashLine("Difference", diffLabel) + staffCashLine("Finished bills", ...)
Finished bills is inside the cash box, on the line under Difference.
That is forbidden. Counts must not sit in the cash, variance, or difference area.

## Required
1. Remove Finished bills from renderStaffCashBox and from every cash, variance, and difference renderer.
2. Render "Finished bills" and the number 61 in its own operational section, not inside the cash box.
3. Difference stays a money line. With no cash count it stays "Cannot calculate yet". It must never show 61.
4. ESB cash stays its own money line from cash_from_payments (360000), formatted as Rp360,000. Do not bind finished_count into it.
5. Rewrite scripts/tests/test_uma_close_4oct_takeover_20261004.py.
   The current test is wrong: it passes when Finished bills is a staffCashLine next to Difference.
   The test must FAIL if the renderStaffCashBox function body contains "Finished bills".
   The test must FAIL if the difference label contains the finished-bill count.
   Add a check that the served page has a separate finished-bills section.
6. Shift report photo: keep Take Photo (capture=environment) and Upload Photo (library) on the real mobile inputs.
   Prove with a local authenticated request to the Beta upload path that the original bytes are stored and bound to this close, BZG, Uma Blu, 2026-10-04, and the actor.
   If extraction fails, the photo stays and manual confirmation still works. No provider or model error text on the page.
   If you cannot prove a real stored upload, set photo_phone_proved to false. Do not set it true because the input tags exist.
7. Write state/reliability/UMA-CLOSE-4OCT-BILLS-OFF-CASH-RESULT-2026-10-04.json with the proof.
8. Beta reload only if Python changed, and only if one listener remains on 127.0.0.1:8788.
   Do not restart prod pid 1297 on 127.0.0.1:8787.
9. No commit. No push. No live catalog copy. No new close. No fake operational rows.
