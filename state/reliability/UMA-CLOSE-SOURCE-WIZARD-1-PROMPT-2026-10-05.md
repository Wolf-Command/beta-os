# UMA-CLOSE-SOURCE-WIZARD-1

Workspace: /Users/wolfterminal/beta-os
Today: Monday 5 Oct 2026, Asia/Makassar.
PHOTO_PATH:

You are the single Beta writer. Workspace /Users/wolfterminal/beta-os. Matt's 29 Sep 2026 Uma Blu close human test FAILED. Do not submit or finalise that close. Do not touch production pid on 127.0.0.1:8787. Do not alter 3 Oct close VDC-470e741f or 4 Oct close VDC-64f5f529. Do not commit or push.

DATA TRUTH FAIL: the page showed warehouse figures (cash Rp4,135,000, 51 finished bills). Matt supplied the printed FINAL Shift Summary for 29 Sep 2026. Those are a second source, not a correction of the first. Preserve both. Never silently overwrite one with the other.

Printed report, Owner-typed, 5 Oct 2026, during this human test. Treat these as the printed-report source, not as a replacement of the warehouse:
- Sales total Rp11,103,306
- Net sales total Rp11,103,306
- Service charge Rp1,221,364
- Tax Rp1,110,331
- Gross sales total Rp13,435,000
- Pax 79
- Bills 50
- Cancel 0
- Void 0
- Cash Rp3,790,000
- EDC BNI Rp2,545,000
- EDC BRI Rp4,465,000
- QRIS BNI Rp145,000
- QRIS BRI Rp1,065,000
- SCOTT & ETIK Rp1,425,000
- Payment total Rp13,435,000
- Non sales Executive Chef Rp78,512
- Total non sales Rp78,512
Warehouse that must remain: cash Rp4,135,000, finished bills 51.
Discrepancy to show, not auto-resolve: cash Rp345,000 and 1 bill.

If a real photo file of that printed report is found (search the close evidence store and any path named in the prompt header PHOTO_PATH), attach the original bytes to the 29 Sep evidence record. Provenance: provided by Owner, 5 Oct 2026, during historical Daily Close human test. If PHOTO_PATH is empty, do not invent a file. Store the typed figures as the printed source and leave the image slot honest (missing file, values supplied by Owner in the test). Do not fabricate an image.

UX FAIL: the current page is an engineering screen. Rebuild Uma Blu close as a phone-first step wizard, one primary action at a time. Not one enormous scrolling page.

Screens, in order:
1. CLOSE UMA BLU, the business date, short summary using the PRINTED report when it exists (for 29 Sep: Sales Rp13,435,000, Bills 50, Cash Rp3,790,000) and a single next action: Add the printed shift report, with Take photo and Upload photo. If the photo already exists, show it.
2. After reading, show WE READ with Gross sales, Cash, BNI card, BNI QRIS, BRI card, BRI QRIS, Scott & Etik, Bills, Pax, and two actions: CORRECT and EDIT. No "AI is not truth" copy on the staff screen.
3. If warehouse and printed report disagree, one warning SOURCE DIFFERENCE FOUND with both figures and the difference, then CONTINUE WITH SHIFT REPORT or SEND FOR REVIEW. The closer does not fix the database.
4. Card terminals: only banks on the confirmed shift report. For 29 Sep show BNI and BRI with expected card and QRIS. Mandiri says NOT USED. Do not show CHECK THIS AMOUNT, Sales EDC, Shift report EDC, Terminal EDC, delta, or blank technical values until there is a receipt to compare. After ADD BANK RECEIPT, show Actual and Difference.
5. Cash: SHIFT REPORT CASH, PETTY CASH PAID for THAT business date only, EXPECTED CASH IN TILL, one amount field, optional cash photo. Then Expected, Counted, Difference. Never say "Cannot calculate yet" six times. If something is missing, name the one next step, e.g. Confirm the shift report first.
6. Petty: historical petty for the selected business date only, from the canonical petty ledger. 29 Sep must not include today's balance or the 5 Oct Owner Cash In PETTY-UMA-6D853EEAE0 Rp500,000. If that date's petty cannot be proved, say PETTY CASH FOR THIS DATE NEEDS REVIEW. Do not change the live petty balance (must stay Rp552,700) and do not touch PETTY-UMA-6D853EEAE0.
7. One review screen: sales, cash expected/counted/difference, BNI, BRI, Scott & Etik, petty, issues (source discrepancy, missing evidence, other exceptions). Then SUBMIT CLOSE, or SUBMIT WITH EXCEPTION if there is an exception, routed to the existing exception role. Do not submit the 29 Sep test close as part of this build.
8. Submit stays disabled until the minimum steps are done. The screen states the ONE next thing. A large green Submit must not appear while the shift report, cash, and terminals are incomplete.

Date range: remove the 7-day limit. Owner and authorised Finance can select any historical date, search a date, and see missing, completed, and exception closes. 3 Sep 2026 must be selectable in the product, not via a hand-built URL. 3 Sep is the next evidence-rich test (1 shift report photo + 4 card slips already on file) but do not build that close.

Protected: do not recapture or rewrite 3 Oct or 4 Oct. Opening 29 Sep must keep warehouse snapshot and add the printed source beside it. Fingerprint behaviour that freezes a snapshot must not be broken.

Staff UX: no GL, journals, debits, credits, account codes, or a Reconcile button. Operational staff record what happened. Wolf calculates.

Tests must prove the acceptance list:
- 29 Sep warehouse cash 4135000 and 51 bills still stored
- 29 Sep printed cash 3790000, bills 50, gross 13435000, pax 79, executive chef non-sales 78512, payment lines as above, payment total 13435000
- source discrepancy visible (345000 and 1 bill)
- photo attached only if a real file was supplied, otherwise honest missing-file
- Mandiri NOT USED on 29 Sep
- BNI and BRI expected values correct
- Scott & Etik 1425000 preserved
- petty for 29 Sep does not include PETTY-UMA-6D853EEAE0 or the 5 Oct balance
- submit disabled until prerequisites complete
- 3 Sep is selectable
- 3 Oct and 4 Oct rows unchanged (compare updated_at and declared cash before and after)
- production pid 1297 not restarted

Reload Beta only at the end, only if Python changed, only if exactly one listener remains on 8788, using the existing beta restart path. If Matt's close page would be required to prove, prove with tests plus a read of the served HTML, not by submitting.

staff_ready false. human_commissioned false. Do not describe it as staff ready.

Write state/reliability/UMA-CLOSE-SOURCE-WIZARD-1-RESULT-2026-10-05.json and end the log with a single line EXIT 0 or EXIT 1. The supervisor misreads a table of test counts with no exit line as a crash.
