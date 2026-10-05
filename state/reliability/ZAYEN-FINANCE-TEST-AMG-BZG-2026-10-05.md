# Zayen — Finance human tests (AMG + BZG)

Status: NOT COMMISSIONED. Draft for Peaches to send to Zayen once engineering is proved:
- AMG after FINANCE-CORE-STATEMENTS-1
- BZG after FINANCE-CORE-STATEMENTS-1 and FINANCE-CORE-BZG-PROVE-1

Do not send before then. Matt does not run these tests; they are not in Matt's queue.

Login: open the link, sign in with Cloudflare Access as laluzayen@gmail.com.
Expected access: AMG yes, BZG yes, GGV no (GGV Finance should say you do not have access).
For each step, mark PASS or FAIL. On a FAIL, add a screenshot and one line saying what you expected.

---

## HUMAN TEST — ZAYEN — AMG FINANCE

| # | Step | Link | PASS/FAIL |
|---|------|------|-----------|
| 1 | Finance opens with AMG data (no GGV/BZG rows) | https://beta.wolfcommand.net/amg/finance | |
| 2 | Banking → BANK STATEMENTS opens | https://beta.wolfcommand.net/amg/finance/banking | |
| 3 | Historical list shows the real CIMB statements for the 5 accounts (Dec 2025–Aug 2026 where they exist); missing months say MISSING STATEMENT, not zero | https://beta.wolfcommand.net/amg/finance/banking | |
| 4 | UPLOAD STATEMENT works with a real CIMB e-statement you have. Upload the same file again: it must say ALREADY IMPORTED | https://beta.wolfcommand.net/amg/finance/banking | |
| 5 | Open a statement: original file downloads, opening/closing balance shown | (OPEN from the list) | |
| 6 | Transactions listed for that statement, with no duplicates | https://beta.wolfcommand.net/amg/finance/transactions | |
| 7 | Nota / evidence: upload a receipt photo; it is kept even if the reading fails; open it again | https://beta.wolfcommand.net/amg/finance/notas | |
| 8 | AP (bills) list opens; there is no pay button | https://beta.wolfcommand.net/amg/finance/bills | |
| 9 | AR (invoices / customers) opens | https://beta.wolfcommand.net/amg/finance/invoices | |
| 10 | Reconciliation shows only PROPOSE MATCH / HUMAN REVIEW / UNMATCHED; nothing is auto-posted | https://beta.wolfcommand.net/amg/finance/reconciliation | |
| 11 | Journals open | https://beta.wolfcommand.net/amg/finance/journals | |
| 12 | Reports open | https://beta.wolfcommand.net/amg/finance/reports | |
| 13 | Refresh the browser: everything you uploaded is still there | — | |
| 14 | GGV is denied: you see "do not have access" | https://beta.wolfcommand.net/ggv/finance | |

Also available: missing evidence https://beta.wolfcommand.net/amg/finance/missing-evidence · audit https://beta.wolfcommand.net/amg/finance/audit

---

## HUMAN TEST — ZAYEN — BZG FINANCE

| # | Step | Link | PASS/FAIL |
|---|------|------|-----------|
| 1 | Finance opens with BZG data only | https://beta.wolfcommand.net/bzg/finance | |
| 2 | Banking → BANK STATEMENTS opens | https://beta.wolfcommand.net/bzg/finance/bank | |
| 3 | Historical list shows Mandiri ••5558 Mar–Aug, BRI ••9305 Apr–Aug and BNI ••7110 Apr–Aug; Sep shows MISSING STATEMENT | https://beta.wolfcommand.net/bzg/finance/bank | |
| 4 | UPLOAD STATEMENT works with a real BZG statement. Uploading the same file again says ALREADY IMPORTED | https://beta.wolfcommand.net/bzg/finance/bank | |
| 5 | Open a statement: original file downloads, balances shown | (OPEN from the list) | |
| 6 | Transactions shown with MATCHED / POSSIBLE MATCH / UNMATCHED / EXCEPTION | https://beta.wolfcommand.net/bzg/finance/bank | |
| 7 | Suppliers: search for one (e.g. "Banneton") and open it | https://beta.wolfcommand.net/bzg/finance/suppliers | |
| 8 | POs: open a historical PO from the supplier and check its lines | (from the supplier page, e.g. /bzg/finance/po/PO-HIST-15) | |
| 9 | Receipts (GR): open the linked receipt | (from the PO page) | |
| 10 | Notas: open the linked nota or bill | (from the PO page) | |
| 11 | Evidence images: open one where it is linked. Where none is linked, it must honestly say missing | (from the nota page) | |
| 12 | Outlet filter: switch Uma Blu / Rainforest / Pool Bar; the lists change | https://beta.wolfcommand.net/bzg/finance | |
| 13 | AP list opens; there is no pay button | https://beta.wolfcommand.net/bzg/finance/ap | |
| 14 | AR / invoices (if shown) open | https://beta.wolfcommand.net/bzg/finance | |
| 15 | Reconciliation and exceptions open | https://beta.wolfcommand.net/bzg/finance/exceptions | |
| 16 | Journals and reports open, if shown for BZG | https://beta.wolfcommand.net/bzg/finance | |
| 17 | Petty cash history opens | https://beta.wolfcommand.net/bzg/finance/petty | |
| 18 | Refresh the browser: everything persists | — | |

Note for Peaches: BZG bank and statement routes may move to a shared BANK STATEMENTS route after FINANCE-CORE-STATEMENTS-1. Re-check the links in its RESULT JSON before sending.
