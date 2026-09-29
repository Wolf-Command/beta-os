# Human commissioning — 28 Sep 2026

These are login cards. They do not mark anyone ready. They do not mark anyone commissioned. Each person writes PASS or FAIL. A failure is a targeted repair. It is not a redesign.

Sign in at https://beta.wolfcommand.net with your own Gmail. Wolf sends an email code. Do not use someone else's mailbox.

My Work is empty for Content Creator and Creative Director. Nine content plans are stored. None of them is assigned to these seats. Nothing was copied in to fill the page.

## Content Creator

Who: Yudi, Gery, Alam, TJ, Nata, Rapp. One card. Each person uses their own Gmail.

1. Open https://beta.wolfcommand.net.
2. Sign in with your own Gmail and the email code.
3. You should land on Content.
4. Open My Work. It should say Content Creator. Today is empty. Leave it empty.
5. Open Library.
6. Search for a shoot you know is already in the library.
7. Open one file and look at the preview.
8. Upload one real file from a shoot. Do not upload a sample.
9. Submit that work, or the evidence for it, the way the page asks.
10. Write PASS or FAIL, your name, and the exact words on the screen if it fails.

## Creative Director

Who: Haikal, Misa, Zarah, and Frail. Each person uses their own Gmail. Zarah is zarah.lestrange@gmail.com. Frail is frail.bongat@icloud.com. This is the same card.

1. Do every Content Creator step above, on your own sign-in.
2. My Work should say Creative Director. Today is empty. Leave it empty.
3. If a real submission is on your seat, review it.
4. If a real item is on your seat, assign or coordinate that one item.
5. If nothing is on the seat, do not invent one.
6. Publishing stays on the Publish Gate. If the gate refuses you, write the words and stop.
7. Write PASS or FAIL, your name, and the exact words on the screen if it fails.

## Zayen — Atrium Finance — RETEST #2 PENDING

Who: Zayen. Gmail laluzayen@gmail.com.

FAIL #1 (13:18, raw JSON on `/`) and ZAYENFIX-1 stay on record. FAIL #2 (14:16, engineering placeholder on `/amg/finance`) stays on record. ATRIUMFIN-UX-2 is the desk for this retest. It does not mark her ready and it does not mark her commissioned.

1. Open https://beta.wolfcommand.net.
2. Sign in with that Gmail and the email code.
3. You should land on Atrium Finance. The header is Atrium Finance. The entity is Atrium. The desk tabs are Board, Ledger, Chart of Accounts, Journals, Reports, and Approvals.
4. Open Board. There is no balance yet. The chart can be open beside it. A draft does not change the balance.
5. Open Ledger. There are no posted lines until the Finance Controller posts a journal.
6. Open Chart of Accounts. The Atrium account names are listed. There is no balance on the chart.
7. Open Journals. You can save a balanced draft. You cannot approve it or post it.
8. Open Reports. The statement names are listed. There are no figures until a period is posted.
9. Open Approvals. You can describe a decision and send it. Approvals are handled by the Finance Controller.
10. Open one GGV page or one Blu Zone page. You should be refused.
11. Write PASS or FAIL, and the exact words on the screen if it fails.

## PASS / FAIL record

Every row stays PENDING until that person writes the result. Do not fill these in from a test run.

Zayen Atrium Finance Officer — RETEST #2 PENDING. FAIL #1 13:18 raw JSON on / (ZAYENFIX-1). FAIL #2 14:16 engineering placeholder on /amg/finance (ATRIUMFIN-UX-1). ATRIUMFIN-UX-2 is on the desk and is not a pass.

| Person | Role | Result |
| --- | --- | --- |
| Haikal | Creative Director | PENDING |
| Misa | Creative Director | PENDING |
| Zarah | Creative Director | PENDING |
| Frail | Creative Director | PENDING |
| Yudi | Content Creator | PENDING |
| Gery | Content Creator | PENDING |
| Alam | Content Creator | PENDING |
| TJ | Content Creator | PENDING |
| Nata | Content Creator | PENDING |
| Rapp | Content Creator | PENDING |
| Zayen | Atrium Finance Officer | RETEST #2 PENDING |

### Zayen — HUMAN FAIL #2 — 28 Sep 2026 ~14:16 WITA
- FAIL #1 (13:18, raw JSON on `/`) and its repair ZAYENFIX-1 (`ff60204`) stay on record. Routing repair worked: Zayen reached `/amg/finance`.
- FAIL #2: `/amg/finance` renders an engineering placeholder, not a staff finance workspace. Evidence is Zayen's screenshot, supplied by Matt in chat on 28 Sep 14:16 (image not stored on disk). The visible text includes "Hotel books are not open on this desk.", "No report figure is on this page.", "Do not type an amount." and "You cannot approve a payment…".
- Repair ATRIUMFIN-UX-1 is on the desk. ATRIUMFIN-UX-2 adds the ledger, the chart, draft journals, and the statement list. Status: staff_ready=false, human_commissioned=false. Retest #2 is PENDING.

## Haikal — Library human test (reported by Matt 28 Sep 2026 16:17 WITA)
Original feedback, preserved verbatim-in-substance:
- Library search is working.
- He found the Atrium footage he needed.
- He successfully downloaded footage for an Atrium video.
RESULT: PASS for those three tested Library functions ONLY (search, find Atrium footage, download). Untested Library functions are NOT commissioned.
Improvement request (Haikal): search results rely on Prev/Next only. Wants numbered pagination (e.g. "15,561 indexed files match · Showing 48 on this page" / PREV · 1 · 2 · 3 · … · NEXT). Tracked as LIBPAGE-1. This record is evidence and must not be overwritten by the fix.

## Zayen — HUMAN RETEST #2 (reported by Matt 28 Sep 2026 16:18 WITA)
- Routing: PASS. laluzayen@gmail.com signs in and reaches /amg/finance. FAIL #1 raw-JSON defect is fixed.
- Atrium Finance human commissioning: FAIL. Zayen says the board is not the Atrium Finance system he expected: a very small surface with basic tabs and an approval area (UX-1/2/3, head d9029f6). He supplied a reference screenshot of the fuller operating dashboard and says his GitHub repo holds that implementation.
- staff_ready=false, human_commissioned=false. FAIL #1, FAIL #2 and this retest stay in history.
- Next: ATRIUMFIN-RECON-1 (reconciliation only, no build).
