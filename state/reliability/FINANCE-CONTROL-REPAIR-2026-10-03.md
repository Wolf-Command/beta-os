# FINANCE CONTROL REPAIR PACK — 2026-10-03
Owner: Matt. Governor: Peaches. Worker: Cursor on Beta only (`/Users/wolfterminal/beta-os`, branch `build/wolf-command-rebuild`).
Status: ARMED_BLOCKED_MAC_PIPE. Incident INCIDENT-20261003-0712 FAIL_CEILING. Do not start until PIPE_OK.
Do NOT build this in wolf-system, atrium-finance-live, or any other remote repo. Beta source is Mac-local. No prod writes. No PR #1 merge. staff_ready stays false until human PASS.

## Outcome
One controlled Beta repair. Reuse existing close, ESB, evidence, permissions, receipt ingest, and GGV finance. Do not redesign unrelated Wolf. Inspect live Beta before editing.

## Non-negotiable
- ESB is a source, not the historical closing record.
- Separate LIVE ESB, CLOSING DRAFT SNAPSHOT (frozen at start for the selected business date), and FINAL CLOSED RECORD.
- Live ESB sync must not mutate an open draft or a finalised close.
- Backdated close uses that business date's ESB, never today's live sales.
- Verify business date before save. Never fabricate missing figures as zero. Unavailable stays unavailable.
- Never silently overwrite. Corrections append history: ORIGINAL → REOPEN → CHANGES → NEW APPROVAL.
- Audit on every important action: who, what, when, business date, before, after, reason.
- Original receipt image and original bank statement stay retrievable evidence.
- Preserve RAW and NORMALISED bank values.
- No weak auto-match. High confidence may be proposed. Ambiguous goes to human review.
- Respect company boundaries. Accountant must not need the Peaches chat to see evidence.
- Telegram is retired. Receipt intake is this Peaches chat ("receipt ggv" + image), into the existing GGV receipt path, visible at GGV → Accounting → Receipts. Do not build a second pipeline. Inspect receipt-from-telegram.py, receipt-ingest.py, and any Beta successor and reuse.

## Part A — BZG closing
History UI: filter single day, range, outlet, company, status. Each close shows business date, outlet, gross, net if available, tax, service, discounts, cash, card, QRIS, other tenders, expected cash, actual cash, variance, adjustments, notes, who completed, who approved, started, completed, evidence, source of each important figure, later corrections, full audit. Range view shows each day plus consolidated totals. History reads saved close data, never recompute from today's ESB.

ADD MISSING CLOSING: company, outlet, business date → snapshot ESB for THAT date.

CANCEL CLOSING visible through unfinished flow. Before final submit: stop, abandon draft, no accounting entry, no historical adjustment, no fake completed close, record who/when/business date, optional reason, allow clean restart.

After FINAL SUBMIT, staff cannot cancel. REOPEN requires manager/finance. Preserve original.

Safety: block double close of same outlet/date (tell what exists and what is allowed), block today's ESB against an old date, duplicate submit, refresh duplicates, two staff on same outlet/date, live ESB mutating an open close, staff overwriting a completed close.

Staff UX: SELECT DAY → CHECK SALES → COUNT/CONFIRM MONEY → UPLOAD/CONFIRM EVIDENCE → REVIEW VARIANCE → SUBMIT. Unfinished: SAVE, BACK, CANCEL CLOSING. Business date obvious, especially backdated. No engineering language.

Permissions: staff close / add permitted missing / cancel own unfinished / upload evidence / correct unfinished draft. Cannot rewrite completed history, reopen without permission, or delete audit. Manager: reopen, review discrepancies, approve corrections, review history. Finance: GGV accounting as below. Owner: full visibility inside company boundaries.

## Part B — GGV receipts and accounting
Peaches chat image + "receipt ggv" → existing pipeline → GGV Accounting → Receipts.

Receipt record where available: original image, merchant, receipt date, upload time, amount, tax, currency, payment method, category/account, description, uploaded by, reimbursement flag, processing status, accountant status, bank recon status, linked bank txn, extracted data, original AI extraction, human corrections, notes, full audit. Image opens from the transaction.

Queues: All, Needs coding, Needs review, Needs receipt/evidence, Matched to bank, Unmatched, Possible duplicate, Reimbursable, Completed. Exceptions first.

GGV Accounting operational sections: Dashboard, Banking, Transactions, Receipts, Reconciliation, Income/Invoices, Expenses, Suppliers, Missing evidence, Reports, Audit history. No fake placeholder numbers. Unavailable says unavailable and why.

Banking → Upload statement: keep original file, parse normalised txns (date, value date, description, reference, debit, credit, running balance, bank account, original statement, import batch, recon status, matched record, notes, audit). RAW + NORMALISED kept.

Reconciliation matches bank txns to Peaches receipts, supplier expenses, bills, invoices, client payments, payroll, reimbursements, transfers, existing records, prior reconciled txns. Signals: amount, date, merchant, description, reference, invoice number, receipt. States: MATCHED, PARTIALLY MATCHED, NEEDS RECEIPT, NEEDS CODING, TRANSFER, POSSIBLE DUPLICATE, UNIDENTIFIED, RECONCILED.

Accountant sees txns, receipts, every image, original statements, recon status, missing evidence, coding, documents, corrections, audit. No Peaches-chat dependency.

## Tests (PASS only on Beta UI + persisted data + permissions)
1. Close today normally.
2. Start today, cancel halfway.
3. Restart successfully.
4. Start backdated close.
5. It retrieves that historical ESB business date.
6. Live ESB sync while backdated draft is open.
7. Draft does not change.
8. Complete backdated close.
9. Retrieve it in Closing History.
10. Multi-day range shows days plus totals.
11. Duplicate close blocked/handled, history intact.
12. Manager reopen.
13. Original values remain in audit.
14. Upload GGV receipt via Peaches.
15. It appears in GGV Accounting.
16. Open original image from Accounting.
17. Correct extracted fields.
18. Original extraction and correction history remain.
19. Upload a representative GGV bank statement.
20. Parse without losing raw.
21. Match a receipt to a bank txn.
22. Flag unmatched.
23. Flag missing evidence.
24. Accountant can open txn and original evidence.
25. Unauthorised staff cannot access GGV accounting.

## Handoff
WHAT CHANGED, WHAT WAS REUSED, WHAT WAS FIXED, WHAT WAS TESTED, TEST RESULTS, REMAINING LIMITATIONS, EXACT URLS. Then READY FOR MATT TEST checklist. Do not call finished because code compiled or unit tests passed in isolation.

## Preserve
Tonight's Uma close VDC-87202768-55af-4c8e-abc3-382a5496b8c6 (2026-10-02, BZG-UMA, DATA_CAPTURED, holder PERS-MATT) and its receipt photos. Do not wipe. EDC bank-card work was mid-visual-verify when the pipe died; do not treat it as Matt-ready and do not clobber it. Prod :8787 read-only.

---

# MANDATORY COMMISSIONING AMENDMENT (3 Oct 2026 ~10:03 WITA)
Supersedes any conflicting assumption above. Do not restart completed work. Inspect current Beta and continue from the last proved checkpoint. Pack stays in the production line if the control path drops. Outage may delay deploy. It must not erase or park this work.

## Host language (required)
Never say "Mac Studio offline" unless the host is proved down.
States: HOST ONLINE / CONTROL PATH ONLINE · HOST ONLINE / CONTROL PATH DOWN · HOST OFFLINE · HOST STATE UNKNOWN.
Current incident INCIDENT-20261003-0712 is CONTROL PATH DOWN until a host-down prove exists. legitimate_needs_matt false. No Matt restart nag.

## A. Owner authority (constitutional)
Matt has direct Owner UI authority to take over, reassign, cancel, restart, reopen, unlock, supersede incorrect evidence, correct configuration, stop/start workflows, and override operational locks where appropriate. No Peaches prompt and no engineering step for routine Owner control. Audit: who, what, when, before, after, reason. Destructive actions and actual money movement stay separately controlled. Wolf controls staff. Matt controls Wolf.

## B. Three data states
LIVE ESB OPERATIONAL DATA, DATED CLOSING SNAPSHOT, FINAL HISTORICAL CLOSE are different objects. Close for business date X creates an immutable working snapshot for X. Live ESB sync continues independently and must not mutate the open close. Final confirmed close is historical evidence. Backdated close pulls the selected business date, never today's live state.

## C. Live ESB vs printed closing receipt
Separate sources. Never overwrite one with the other. 2 Oct 2026 example (do not force them to agree): live previously Bills 61 / Cash Rp2,855,000; printed Shift Summary Bills 58 / Cash Rp2,735,000. Expose the evidenced cause if found (cutoff, late/reopened bills, status, voids, ingest timing, payment semantics). Do not invent a cause.

## D. Full receipt extraction
Do not reduce the receipt to Cash/EDC/QRIS. Model RECEIPT → SECTION → LINE with raw label, qty/value, amount, normalized type where known, confidence, human confirmed value. Unknown lines = NEEDS CLASSIFICATION, never dropped. Payment methods are an extensible collection (CASH, EDC BNI, EDC MANDIRI, QRIS BNI, QRIS MANDIRI, ROB & FAMILY, ROOM CHARGE 112, SCOTT & ETIK, plus future lines). Also capture Non Sales, Compliment, Executive Chef, Cancelled Menu, Void Payment Detail, Promotion Summary, and unknown future sections.

## E–G. Uma Blu bank cards
Three cards from outlet config: MANDIRI, BNI, BRI. Not a generic Add EDC Receipt. Confirmed Shift Summary prepopulates expected EDC and QRIS per bank, terminal actuals, difference, evidence, status. ESB EDC=0 and QRIS=0 → NOT USED TODAY, no receipt, override if evidence says the terminal was used. EDC and QRIS stay separate lines; totals may be calculated but originals remain. One bank/day = one CURRENT reconciliation state. Prior attempt stays in audit as SUPERSEDED and is excluded from totals. A warning is not enough if both still sum.

## H. Vision is a Wolf capability
RECEIPT_IMAGE_EXTRACTION backed by an authorised provider. Do not hardcode staff UX to Gemini. Staff never see provider/key errors. On failure: keep photo, Retry Reading, Enter Manually, close continues. AI is draft. Human confirmed data is authoritative.

## I. ENG_PROVED
Unit/mock tests are not enough for an external integration. Required: code test, Beta deployed, actual credential resolution, actual provider call, representative real input, expected output, failure/fallback test, persisted evidence. Else CODE COMPLETE / INTEGRATION UNPROVED. Applies to ESB, vision, bank import, GGV receipt processing, Gmail/Peaches ingestion, and every other external dependency. Cursor EXIT is not PASS.

## J–K. Cancel, restart, reopen, takeover
Cancel unfinished: abandon draft, no history/accounting effect. Restart: clean dated snapshot. Reopen final: never edit the original in place (original close, reopen event, changes, new approval, new final). Owner can do these in UI. Authorised closer may claim. Manager/Owner can view holder, reassign, take over, and must preserve entered work and evidence. Takeover records original closer, new closer, reason, timestamp, before/after. Ordinary staff cannot steal an active close.

## L. History detail
Also show source snapshot, ESB receipt, API vs receipt differences, bank-by-bank EDC, QRIS, cash, non-sales, outstanding/house classifications, evidence, superseded evidence, corrections, reopen/takeover/cancel history. Date-range totals use finalized/current states only, not superseded attempts.

## M–O. GGV
No second receipt pipeline. Image permanent. Extraction separate from human confirmation. Raw extraction and corrections retained. Duplicate protection. One canonical receipt. Accountant opens evidence from the transaction, not from Matt's Peaches chat. Bank: RAW statement + NORMALISED txns. Proposed ≠ human confirmed ≠ reconciled. Weak matches never auto-reconcile. Owner override audited. Entity isolation: PERSON → ASSIGNMENT → ROLE → ENTITY SCOPE → PERMISSION → RESOURCE ENTITY. Shared finance permission must not leak GGV into AMG/BZG. Zayen stays GGV DENY. Amanda/Matt follow canonical GGV assignments. Accountant scope is per business.

## P. Continue, don't park
Last proved close checkpoint stays. Tonight's close VDC-87202768 and photos stay. EDC bank-card work that was awaiting Peaches visual verify is in-scope continuation, not a new pack and not Matt-ready.

## Q. Staff flow
1 select/confirm business date 2 ESB snapshot for that date 3 photo Shift Summary 4 read all lines 5 human confirm/edit 6 Mandiri/BNI/BRI checklist from the report 7 photo receipts for banks actually used 8 read EDC and QRIS separately 9 human confirm/edit 10 count cash 11 reconcile each source 12 resolve visible exceptions 13 submit. Unfinished: SAVE, BACK, CANCEL CLOSING. Authorised: TAKE OVER, REASSIGN, REOPEN, SUPERSEDE EVIDENCE.

## R. Tests 26–40 (plus original 1–25)
26 full Shift Summary extract 27 unknown payment kept 28 BNI and Mandiri EDC separate 29 BNI and Mandiri QRIS separate 30 BRI unused when ESB zero 31 misread then correct → SUPERSEDED, not double-counted 32 vision down → photo kept, manual entry, close continues 33 Owner takeover via UI 34 takeover keeps prior work 35 API vs receipt both retained and difference shown 36 backdated draft stable while live ESB changes 37 cancel backdated and restart clean 38 reopen historical, original unchanged 39 Owner operational override in UI without Peaches 40 real external calls on deployed Beta, not mocks.

## Done
READY FOR MATT TEST only after Peaches independently verifies deployed Beta screens and real integration paths. Code complete, unit tests, mock integration, and Cursor EXIT are not PASS.
