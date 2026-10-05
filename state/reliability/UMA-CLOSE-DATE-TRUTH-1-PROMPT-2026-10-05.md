# UMA-CLOSE-DATE-TRUTH-1

Surgical Daily Close truth + mobile UX. Beta only: /Users/wolfterminal/beta-os.
staff_ready=false. Do not mark human commissioned. Do not redesign Finance or P2P.
Do not commit, push, merge, or clean the dirty tree.
Do not restart production. Production listener pid 1297 on 127.0.0.1:8787 must still be 1297 when you finish.
Do not touch prod files. Do not kill factory, petty-cash, finance, P2P, ready-to-pay, GGV, or recipe workers.
Leave /Users/wolfterminal/.openclaw/workspace/wolf-system processes alone.
Do not call a live ESB API. Do not upload a dummy photo. Do not create a second close.
sqlite3 CLI often fails. Use Python sqlite3 mode=ro for any live read. Do not copy catalog/content_library.sqlite. Do not fake operational rows into the live catalog.

## Proved figures — do not change the numbers

Proof: state/reliability/UMA-29SEP-ESB-PROOF-2026-10-05.md
Verdict: CORRECT. Uma Blu (branch BLZ / outlet BZG-UMA) business date 2026-09-29.

The query already returns only that date. Warehouse `sales.biz_date` is ESB `salesDate`. snapshot_day filters `WHERE biz_date=?` and `branchCode==BLZ` and status Finished. All 51 rows are BLZ / UMA BLU. salesDate, salesDateIn, and salesDateOut are all 2026-09-29. No 28 Sep or 30 Sep leakage. pulled_at is 2026-10-05T05:47:40+08:00 (WITA pull time) and is not the business date.

Stored close VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad state DATA_CAPTURED fingerprint af1310a02e5ffe5c9a5e9ce29bbab6dc6dada93b4691a4843c4b2ac61543c724 matches a fresh snapshot_day('2026-09-29').

Use these figures in the result file. Do not invent replacements:

- cash_from_payments: 4135000.00 (15 cash payment lines; screen Rp4,135,000 is this)
- finished bills: 51
- grand_total rounded: 13513512.40 (raw grandTotal sum 13513512.397)
- payment_total rounded: 13858512.40
- card_from_payments: 8435000.00 of which bank EDC is EDC BNI 2545000 + EDC BRI 4465000 = 7010000, plus house method SCOTT & ETIK 1425000
- qris_from_payments: 1210000.00 (QRIS BNI 145000 + QRIS BRI 1065000)
- other_from_payments: 78512.40 (Executife Chef)
- cash_change_overpay: 345000 (change on 9 cash bills, not a settlement figure)
- discounts 0, cancelled bills 0
- no net field and no serviceCharge field; subtotal raw sum 11181818.1790; vatTotal 1110330.5781; otherTaxTotal 1221363.6364
- printed shift report: NOT AVAILABLE
- settlement API: UNAVAILABLE

Do NOT correct the query for 29 Sep. Do NOT recapture or replace the unfinished 29 Sep draft. The figures are not wrong.

Adjacent dates already have distinct cash (do not write these into the live catalog; they are the proof, for tests use fixtures):

- 2026-09-28 cash 2460000 finished 58
- 2026-09-29 cash 4135000 finished 51
- 2026-09-30 cash 2610000 finished 50
- 2026-10-01 cash 2435000 finished 45
- 2026-10-02 cash 2855000 finished 61
- 2026-10-03 cash 3465000 finished 52
- 2026-10-04 cash 360000 finished 61

## Protected closes — do not alter

- VDC-470e741f-d889-437a-9a40-1ec9c083fb95 (3 Oct EXCEPTION, declared cash 3225000, variance -125000, updated_at 2026-10-03T13:47:39Z)
- VDC-87202768-55af-4c8e-abc3-382a5496b8c6 CANCELLED updated_at 2026-10-03T12:32:22Z
- VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5 4 Oct DATA_CAPTURED, declared_cash_amount stays NULL, do not edit esb_totals_json
- Do not alter any COMPLETED historical close, 3 Oct evidence, 4 Oct draft, Iza attribution, Owner takeover audit, receipt evidence, petty integration, idempotent submit, or entity permissions.

## UX repair (this is the work)

Phone-first normal close flow in dashboards/uma-blu-close.html (and the smallest server/template change if the strings are not in that file). Progressive disclosure. Date and the primary action near the top. Do not redesign Finance or P2P.

1. DATE — huge obvious date plus "Historical Close" when it is not today.
2. ESB SALES — Wolf loads the date; staff-facing values only.
3. SHIFT REPORT — Take Photo / Upload Photo; staff confirms or edits uncertain values.
4. CARD TERMINALS — Mandiri, BNI, BRI; EDC and QRIS separate.
5. CASH — expected, counted, difference.
6. REVIEW — Wolf compares.
7. SUBMIT — one result: CLOSE COMPLETE / CLOSE SAVED WITH EXCEPTION / CANNOT SUBMIT.

Owner controls (unlock abandoned, override lock, return for correction, cancel workflow, correct assignment, force re-capture) go behind one collapsed control labelled OWNER TOOLS or MANAGE CLOSE. Not in the middle of the flow.

Remove engineering language from the main UI. Known strings today include "payment lines, not settlement" and "Owner force re-capture complete — audited. Snapshot replaced." Also remove from the main flow: person ids, "force re-capture", "audited", "correct assignment", "live vs dated snapshot". Normal language: Sales loaded for 29 September; Shift report uploaded; Cash expected; Cash counted; Difference found; Needs review; Close complete.

Owner historical path: Closing history → Missing closes → choose 29 Sep → Start/Continue. Once selected, business BZG, outlet Uma Blu, date 29 Sep 2026 are fixed. Do not ask again. Freeze one dated snapshot. Live ESB must not mutate it. Recapture stays the existing explicit Owner-only audited path, rare, behind OWNER TOOLS, not a new mechanism.

When a historical close begins, the existing path already selects outlet, business date, retrieves that date's ESB dataset, and freezes one snapshot. Do not add a second close product. Do not change the 29 Sep numbers.

Captain still must not see GL, journals, debits, credits, account codes, or a Reconcile button. Petty OUT reduces expected cash exactly once. Petty IN increases it exactly once where the model consumes it. Do not break those rules.

## Tests

Add a fixture or temp DB test. Distinct known totals per date for 28 Sep, 29 Sep, 30 Sep, 1 Oct, 2 Oct, 3 Oct, 4 Oct so accidental date reuse cannot pass. Do not copy the full library. Do not write those rows into the live catalog. Do not mutate protected closes or existing real close history.

## Reload

Reload Beta only if you changed Python and exactly one listener is on 127.0.0.1:8788. At start of this task the Beta listener was pid 11882. If you do not change Python, do not reload. Never reload or signal pid 1297.

## Result

Write state/reliability/UMA-CLOSE-DATE-TRUTH-1-RESULT-2026-10-05.json and a short markdown twin beside it.
Include: proved 29 Sep figures above (not invented), query_corrected false, test counts, beta pid, prod pid still 1297, protected closes unchanged (re-read updated_at / declared_cash / state in mode=ro), staff_ready false, human_commissioned false.
