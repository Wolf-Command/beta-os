# FINANCE CONTROL REPAIR PACK — 3 OCT 2026

Canonical register. Maintained. Do not delete rows. Do not shrink the denominator.

As of 2026-10-03T20:18:23+08:00 WITA. `staff_ready=false`. `eng_proved=false`. Pack is not finished. No human pass.

Machine-readable: `state/reliability/FINANCE-CONTROL-REPAIR-PARENT-2026-10-03.json`

## Counts

- TOTAL 132
- PROVEN COMPLETE 2
- IN PROGRESS 88
- HUMAN COMMISSIONING 1
- EXTERNAL BLOCKED 0
- OWNER BLOCKED 0
- NOT STARTED 41

Sum of the six status counts equals TOTAL.

## Branch

current_branch = IZA_3OCT_CLOSE
next_unfinished = FCR-BZG-01 Real 3 Oct Iza commissioning (HUMAN_COMMISSIONING)
next_after_branch = FCR-BZG-30 Real deployed external integration proof (real Cloudflare staff session, not dev assertion) (NOT_STARTED)
next_vertical_queued = P2P, implementation not started, outside this denominator.

current branch is Iza's real 3 Oct close; next item is Real deployed external integration proof (real Cloudflare staff session, not dev assertion)

## Rows

| id | status | requirement |
| --- | --- | --- |
| FCR-BZG-01 | HUMAN_COMMISSIONING | Real 3 Oct Iza commissioning |
| FCR-BZG-02 | IN_PROGRESS | Closing history |
| FCR-BZG-03 | IN_PROGRESS | Single-day history |
| FCR-BZG-04 | IN_PROGRESS | Date-range history |
| FCR-BZG-05 | IN_PROGRESS | Range totals |
| FCR-BZG-06 | IN_PROGRESS | Backdated / missing closing |
| FCR-BZG-07 | IN_PROGRESS | Business-date ESB retrieval |
| FCR-BZG-08 | IN_PROGRESS | LIVE ESB DATA kept separate from DATED CLOSING SNAPSHOT kept separate from FINAL HISTORICAL CLOSE |
| FCR-BZG-09 | IN_PROGRESS | Live ESB cannot mutate a historical close |
| FCR-BZG-10 | IN_PROGRESS | Cancel unfinished close |
| FCR-BZG-11 | IN_PROGRESS | Restart cancelled close |
| FCR-BZG-12 | IN_PROGRESS | Reopen completed close with ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL |
| FCR-BZG-13 | IN_PROGRESS | Owner takeover/reassignment preserving previous closer work |
| FCR-BZG-14 | IN_PROGRESS | Duplicate close protection |
| FCR-BZG-15 | IN_PROGRESS | Concurrent closer protection |
| FCR-BZG-16 | NOT_STARTED | Refresh/idempotency protection |
| FCR-BZG-17 | IN_PROGRESS | Wrong-date protection |
| FCR-BZG-18 | IN_PROGRESS | Full audit trail |
| FCR-BZG-19 | IN_PROGRESS | Original evidence preservation |
| FCR-BZG-20 | IN_PROGRESS | ESB live data vs printed end-of-day receipt reconciliation |
| FCR-BZG-21 | IN_PROGRESS | Full extensible shift-receipt extraction |
| FCR-BZG-22 | NOT_STARTED | Unknown receipt lines preserved (not discarded) |
| FCR-BZG-23 | IN_PROGRESS | Mandiri / BNI / BRI outlet configuration |
| FCR-BZG-24 | IN_PROGRESS | EDC and QRIS separate per bank |
| FCR-BZG-25 | IN_PROGRESS | NOT USED TODAY from confirmed final ESB data |
| FCR-BZG-26 | IN_PROGRESS | One CURRENT bank reconciliation state per bank + business date |
| FCR-BZG-27 | IN_PROGRESS | Incorrect previous bank evidence SUPERSEDED, never double counted |
| FCR-BZG-28 | NOT_STARTED | Manual fallback if image extraction fails |
| FCR-BZG-29 | IN_PROGRESS | Provider-agnostic receipt extraction (no provider names in staff UI) |
| FCR-BZG-30 | NOT_STARTED | Real deployed external integration proof (real Cloudflare staff session, not dev assertion) |
| FCR-BZG-31 | IN_PROGRESS | Staff-language UX on the phone workflow |
| FCR-BZG-32 | IN_PROGRESS | Owner direct controls through Wolf UI (take over, reassign, cancel unfinished, restart, reopen, supersede evidence, correct config) |
| FCR-GGV-33 | IN_PROGRESS | Reuse existing authorised Peaches/receipt ingestion (not a second pipeline) |
| FCR-GGV-34 | IN_PROGRESS | Receipt sent/captured for GGV |
| FCR-GGV-35 | IN_PROGRESS | Original image preserved |
| FCR-GGV-36 | IN_PROGRESS | Receipt field: merchant |
| FCR-GGV-37 | IN_PROGRESS | Receipt field: transaction date |
| FCR-GGV-38 | IN_PROGRESS | Receipt field: upload date |
| FCR-GGV-39 | IN_PROGRESS | Receipt field: amount |
| FCR-GGV-40 | NOT_STARTED | Receipt field: tax |
| FCR-GGV-41 | NOT_STARTED | Receipt field: currency |
| FCR-GGV-42 | NOT_STARTED | Receipt field: payment method |
| FCR-GGV-43 | IN_PROGRESS | Receipt field: category/account |
| FCR-GGV-44 | NOT_STARTED | Receipt field: description |
| FCR-GGV-45 | NOT_STARTED | Receipt field: uploader |
| FCR-GGV-46 | NOT_STARTED | Receipt field: reimbursement state |
| FCR-GGV-47 | IN_PROGRESS | Receipt field: accounting state |
| FCR-GGV-48 | IN_PROGRESS | Bank reconciliation state on the receipt |
| FCR-GGV-49 | IN_PROGRESS | Linked transaction |
| FCR-GGV-50 | IN_PROGRESS | Original extraction retained |
| FCR-GGV-51 | IN_PROGRESS | Human corrections |
| FCR-GGV-52 | IN_PROGRESS | Notes |
| FCR-GGV-53 | IN_PROGRESS | Audit history |
| FCR-GGV-54 | IN_PROGRESS | Accountant can retrieve every original image without asking Peaches |
| FCR-ACCT-55 | NOT_STARTED | Dashboard workflow (operational, not a nav shell) |
| FCR-ACCT-56 | IN_PROGRESS | Banking workflow (operational, not a nav shell) |
| FCR-ACCT-57 | IN_PROGRESS | Transactions workflow (operational, not a nav shell) |
| FCR-ACCT-58 | IN_PROGRESS | Receipts workflow (operational, not a nav shell) |
| FCR-ACCT-59 | IN_PROGRESS | Reconciliation workflow (operational, not a nav shell) |
| FCR-ACCT-60 | IN_PROGRESS | Income/Invoices workflow (operational, not a nav shell) |
| FCR-ACCT-61 | NOT_STARTED | Expenses workflow (operational, not a nav shell) |
| FCR-ACCT-62 | IN_PROGRESS | Suppliers workflow (operational, not a nav shell) |
| FCR-ACCT-63 | IN_PROGRESS | Missing Evidence workflow (operational, not a nav shell) |
| FCR-ACCT-64 | NOT_STARTED | Reports workflow (operational, not a nav shell) |
| FCR-ACCT-65 | NOT_STARTED | Audit workflow (operational, not a nav shell) |
| FCR-BANK-66 | IN_PROGRESS | Upload real bank statement |
| FCR-BANK-67 | IN_PROGRESS | Preserve original statement |
| FCR-BANK-68 | IN_PROGRESS | Normalize while retaining raw source |
| FCR-BANK-69 | IN_PROGRESS | Bank field: transaction date |
| FCR-BANK-70 | IN_PROGRESS | Bank field: value date |
| FCR-BANK-71 | IN_PROGRESS | Bank field: description |
| FCR-BANK-72 | IN_PROGRESS | Bank field: reference |
| FCR-BANK-73 | IN_PROGRESS | Bank field: debit |
| FCR-BANK-74 | IN_PROGRESS | Bank field: credit |
| FCR-BANK-75 | IN_PROGRESS | Bank field: balance |
| FCR-BANK-76 | IN_PROGRESS | Bank field: bank account |
| FCR-BANK-77 | IN_PROGRESS | Bank field: import batch |
| FCR-BANK-78 | IN_PROGRESS | Bank field: reconciliation state |
| FCR-BANK-79 | IN_PROGRESS | Bank field: linked accounting record |
| FCR-BANK-80 | IN_PROGRESS | Bank field: evidence |
| FCR-BANK-81 | NOT_STARTED | Bank field: notes |
| FCR-BANK-82 | NOT_STARTED | Bank field: audit |
| FCR-REC-83 | IN_PROGRESS | Match target: receipts |
| FCR-REC-84 | NOT_STARTED | Match target: supplier expenses |
| FCR-REC-85 | NOT_STARTED | Match target: bills |
| FCR-REC-86 | NOT_STARTED | Match target: invoices |
| FCR-REC-87 | NOT_STARTED | Match target: client payments |
| FCR-REC-88 | NOT_STARTED | Match target: payroll where applicable |
| FCR-REC-89 | NOT_STARTED | Match target: reimbursements |
| FCR-REC-90 | NOT_STARTED | Match target: transfers |
| FCR-REC-91 | NOT_STARTED | Match target: existing accounting records |
| FCR-REC-92 | IN_PROGRESS | Match key: amount |
| FCR-REC-93 | IN_PROGRESS | Match key: date |
| FCR-REC-94 | NOT_STARTED | Match key: merchant |
| FCR-REC-95 | NOT_STARTED | Match key: description |
| FCR-REC-96 | NOT_STARTED | Match key: reference |
| FCR-REC-97 | NOT_STARTED | Match key: invoice |
| FCR-REC-98 | NOT_STARTED | Match key: receipt |
| FCR-REC-99 | NOT_STARTED | Match key: other deterministic evidence |
| FCR-REC-100 | IN_PROGRESS | Weak matches are proposals not truth |
| FCR-REC-101 | NOT_STARTED | Reconciliation state: MATCHED |
| FCR-REC-102 | NOT_STARTED | Reconciliation state: PARTIALLY MATCHED |
| FCR-REC-103 | IN_PROGRESS | Reconciliation state: NEEDS RECEIPT |
| FCR-REC-104 | IN_PROGRESS | Reconciliation state: NEEDS CODING |
| FCR-REC-105 | NOT_STARTED | Reconciliation state: TRANSFER |
| FCR-REC-106 | IN_PROGRESS | Reconciliation state: POSSIBLE DUPLICATE |
| FCR-REC-107 | IN_PROGRESS | Reconciliation state: UNIDENTIFIED |
| FCR-REC-108 | NOT_STARTED | Reconciliation state: RECONCILED |
| FCR-REC-109 | IN_PROGRESS | Reconciliation state: NEEDS REVIEW (present in code, not in the original list) |
| FCR-AUTH-110 | IN_PROGRESS | PERSON → ASSIGNMENT → ROLE → ENTITY SCOPE → PERMISSION → RESOURCE ENTITY chain preserved |
| FCR-AUTH-111 | NOT_STARTED | Zayen AMG/BZG finance per assignment |
| FCR-AUTH-112 | IN_PROGRESS | Zayen ZERO GGV |
| FCR-AUTH-113 | IN_PROGRESS | Amanda GGV finance per assignment |
| FCR-AUTH-114 | IN_PROGRESS | Matt Owner |
| FCR-AUTH-115 | IN_PROGRESS | Matt approved GGV financial-control |
| FCR-AUTH-116 | IN_PROGRESS | Shared Finance Core is not merged entities |
| FCR-HIST-117 | IN_PROGRESS | Historical reconciliation: ESB |
| FCR-HIST-118 | IN_PROGRESS | Historical reconciliation: Alchemist |
| FCR-HIST-119 | NOT_STARTED | Historical reconciliation: V1 |
| FCR-HIST-120 | NOT_STARTED | Historical reconciliation: notas |
| FCR-HIST-121 | NOT_STARTED | Historical reconciliation: receipts |
| FCR-HIST-122 | IN_PROGRESS | Historical reconciliation: POs |
| FCR-HIST-123 | IN_PROGRESS | Historical reconciliation: receiving |
| FCR-HIST-124 | IN_PROGRESS | Historical reconciliation: petty cash |
| FCR-HIST-125 | IN_PROGRESS | Historical reconciliation: supplier history |
| FCR-HIST-126 | IN_PROGRESS | Historical reconciliation: Telegram evidence |
| FCR-HIST-127 | NOT_STARTED | Historical reconciliation: NAS |
| FCR-HIST-128 | NOT_STARTED | Historical reconciliation: Drive |
| FCR-HIST-129 | NOT_STARTED | Historical reconciliation: other discovered authorised sources |
| FCR-REL-130 | PROVEN_COMPLETE | Primary watchdog recovery evidence preserved |
| FCR-REL-131 | IN_PROGRESS | Root cause of repeated Grok/control-path failure |
| FCR-REL-132 | PROVEN_COMPLETE | Wolf Recovery Key private Tailscale secondary recovery |

## Why familiar results are not PROVEN_COMPLETE

- Iza's 3 Oct close is READY FOR HUMAN TEST, not a human pass.
- Continuation prove scripts and the development_assertion HTTP window are IN_PROGRESS.
- Cursor continuation logs exiting are not proof.
- A page render or HTML inspection is not proof.
- The 30 Sep authority file and the 2 Oct historical recon are partial records, not completion.
- GGV bank import used a fixture CSV, not a real statement.
- Root cause of the Grok/control-path failure is still UNKNOWN.
- PROVEN_COMPLETE is only the preserved 13:42 watchdog drill evidence and the Recovery Key Tailscale result already on disk. Neither was rerun.

Preserved close VDC-87202768-55af-4c8e-abc3-382a5496b8c6 (2026-10-02, DATA_CAPTURED, PERS-MATT) was not mutated and was not read in a way that writes.

