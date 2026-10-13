# Wolf Finance — canonical architecture

Decision: one accounting core, three legal entities, one Finance experience.

This checkout is the GitHub Beta repository. It is not the Mac Studio process at `/Users/wolfterminal/beta-os`, and it does not contain `catalog/content_library.sqlite` or the Atrium books files. The map below is from the code and routes that Beta actually serves. Sharing a database is not treated as sharing an accounting core.

Production `:8787` is out of scope. Nothing in this sequence opens it, restarts it, or writes `money.sqlite`.

## 1. Current architecture

Beta Finance is three desks, two ledger stores, and a set of older shells that name accounting slots and leave them empty.

```text
Person → Assignment → Position → Role → Permission → entity scope
        │
        ├─ /ggv/finance          operational desk (GGV HTML)
        ├─ /amg/finance          Atrium hotel ledger desk (different HTML)
        ├─ /amg-finance-ops      operational desk (AMG copy of the GGV HTML)
        ├─ /bzg/finance          BZG browse / AP / bank desk (third HTML)
        └─ /finance              switcher, then a redirect to one of the three

Catalog SQLite (content_library.sqlite)
  GGV + AMG operational rows in ggv_* tables, filtered by entity_id
  BZG operational rows in bzg_* and Uma Blu P2P tables
  ILA review, proposals, document requests, filing notes
  Identity, RBAC, audit

Atrium books (one file per entity, under atrium-finance/data/beta/)
  ENT-AMG → atrium.sqlite          live chart and journals
  ENT-BZG → atrium-bzg.sqlite      chart shell, no claim of live journals
  ENT-GGV → atrium-ggv.sqlite      chart shell, no claim of live journals
```

`scripts/core/finance_core_entity.py` already names the product rule: one finance product, entity config, isolated rows. The screens do not follow it. GGV, AMG operations, AMG ledger, and BZG each have their own navigation, labels, and page structure.

## 2. Engines

| Engine | Code | What it actually does | Status |
| --- | --- | --- | --- |
| Entity books | `scripts/core/entity_books.py` | Opens the per-entity Atrium SQLite file. Adds `legal_entity_id`. Does not copy journals across entities. | Authoritative book files |
| Atrium ledger desk | `scripts/core/atrium_finance_desk.py`, `atrium_fc_authority.py` | AMG chart, draft journals, ledger, approvals, reports. Posting stays with the Finance Controller. | Authoritative AMG general ledger |
| GGV operational finance | `scripts/core/ggv_finance_nota.py`, `ggv_finance_invoice.py`, `ggv_finance_desk.py` | Notas, vendors, invoices, bills, evidence files, accountant page routes. | Authoritative GGV subledger |
| AMG operational reuse | `scripts/core/amg_finance_core.py` | Calls the GGV nota and bank modules inside `ENT-AMG` scope. | Authoritative AMG subledger service, duplicate screen |
| BZG finance desk | `scripts/core/bzg_finance_desk.py`, `bzg_finance_usability_ro.py` | Browse, suppliers, petty, bank, statements, AP, exceptions, completeness. | Authoritative BZG operational desk |
| Uma Blu purchasing | BZG Uma Blu purchase, receipt, bill, and ready-to-pay routes | Purchase orders, notas, goods receipts, three-way match. | Authoritative BZG purchasing records |
| Statement library | `scripts/core/finance_core_statements.py` | File import only. GGV and AMG use `ggv_bank_*`. BZG uses `bzg_bank_*`. | Authoritative statement intake |
| Bank reconciliation | `ggv_bank_statement1.py`, `amg_bank_recon1.py`, `bzg_bank_recon1.py`, `fc_recon_queues1.py` | Propose-only match. No auto-reconcile. Two transaction tables. | Authoritative match state, split implementation |
| ILA accountant workspace | `scripts/core/ggv_ila_accountant.py` | GGV external accountant: September exceptions, proposals, tax preparation, exports. Does not post. | Authoritative GGV review queue, not a second ledger |
| Management reporting shell | `scripts/core/fin_mgmt_reporting.py` | Names P&L, balance sheet, and cash flow slots and leaves them empty. | Incomplete. Not a report of record |
| Reconciliation shell | `scripts/core/fin_recon_shell1.py`, `dashboards/fin-recon-shell-1.html` | Older file-import shell. | Obsolete as a user-facing desk |
| AP/AR shell | `dashboards/fin-ap-ar-shell-1.html` | Honesty shell. Not the live invoice or bill register. | Obsolete as a user-facing desk |
| Tax shells | `dashboards/fin-tax-shell-1.html`, `fin-tax-deepen-1.html` | Named slots. ILA's tax workspace is the GGV preparation surface. | Incomplete. Do not invent liabilities |

## 3. Databases

| Store | Path the code expects | Financial contents | Rule |
| --- | --- | --- | --- |
| Beta catalog | `/Users/wolfterminal/beta-os/catalog/content_library.sqlite` | Identity, permissions, audit, GGV/AMG `ggv_*` finance rows, BZG `bzg_*` and Uma Blu rows, ILA tables | Operational system of record. Not the general ledger |
| AMG books | `atrium-finance/data/beta/atrium.sqlite` | AMG chart of accounts and journals | Do not copy into GGV or BZG |
| BZG books | `atrium-finance/data/beta/atrium-bzg.sqlite` | Chart shell | Empty is empty. Do not manufacture journals |
| GGV books | `atrium-finance/data/beta/atrium-ggv.sqlite` | Chart shell | GGV posted-journal count stays unread until this file is opened read-only |
| Production money | `money.sqlite` on `:8787` | Out of bounds | Migrations already refuse this path |
| Bank originals | `state/{ggv,amg,bzg}-bank-statements/originals` | Source files | Link. Do not recreate |

Same catalog file for GGV and AMG operational rows does not make one ledger. `entity_id` is the isolation key. BZG bank rows are a different table family on purpose until a later gate puts one service in front of both.

## 4. General ledger and journals

The only posted-journal implementation is the Atrium books file: `journal_headers`, `journal_lines`, `journal_workflow_audit`, `journal_evidence`.

AMG is the live book. GGV and BZG book files are structure shells. `ggv_accountant_journal_proposals` stores ILA proposals with `posted = 0`. A proposal is not a journal. Approving a September exception does not approve the month and does not post.

No gate in this sequence backfills a GGV or BZG journal to make a trial balance appear.

## 5. Bank reconciliation

| Entity | Transactions | Behaviour |
| --- | --- | --- |
| GGV | `ggv_bank_transactions` where `entity_id = ENT-GGV` | September 2026 stays `READY_FOR_REVIEW`. The five Finance exceptions are Alfamart Rp64,000, Blu Zone Rp15,000,000, Keen Eye Rp24,875,000, Canva Rp390,000, ATM Rp2,500,000 |
| AMG | `ggv_bank_transactions` where `entity_id = ENT-AMG` | Same table, other entity. `amg_bank_recon1.py` |
| BZG | `bzg_bank_transactions` | `bzg_bank_recon1.py` |

Match fields on the bank row are the allocation history. There is no second allocation ledger. Auto-reconcile stays off.

The 98 September dispositions live in the Beta catalog, which is not in this checkout. This sequence does not rewrite them. An open, undecided review title may be corrected. A decided row is left alone.

## 6. Invoices, bills, notas, reimbursements

| Record | Authoritative store | Screen today |
| --- | --- | --- |
| GGV customer invoices and original PDFs | `ggv_invoices`, `ggv_invoice_documents` | GGV Finance → Invoices |
| GGV notas and receipt photographs | `ggv_notas`, `ggv_nota_files`, `ggv_receipt_accounting` | GGV Finance → Receipts/Notas and Peaches receipts |
| GGV bills | `ggv_bills` | GGV Finance → Bills |
| AMG invoices, notas, bills | Same tables, `entity_id = ENT-AMG` | AMG operational desk |
| BZG purchase orders, notas, receipts, AP | Uma Blu P2P tables and `bzg_finance_*` | BZG Finance and `/bzg/uma-blu/*` |
| Matt and Amanda reimbursements | Derived from GGV notas and GGV bank text. No reimbursement ledger | ILA accountant desk |

Missing originals stay missing. Fulfilled document requests do not create files.

## 7. Dashboards and duplicate workflows

| Surface | File | Problem |
| --- | --- | --- |
| GGV Finance | `dashboards/ggv-finance.html` | Long tab row: Overview, Accountant, Banking, Transactions, Receipts/Notas, Bills, Invoices, Reconciliation, Suppliers, Missing Evidence, Reports, Audit |
| AMG operations | `dashboards/amg-finance-ops.html` | Same tab row, separate file, AMG APIs |
| AMG ledger | `dashboards/amg-finance.html` | Different nav: Board, Ledger, Chart of Accounts, Journals, Reports, Approvals |
| BZG Finance | `dashboards/bzg-finance.html` | Different nav: Browse, Suppliers, Petty, Bank, Statements, AP, Ready to pay, Exceptions, Completeness, Photos |
| Finance entry | `dashboards/finance-entry.html` | Redirects to whichever company the switcher stored |
| Older shells | `dashboards/fin-*.html` | Parallel vocabulary and empty slots |

Company-specific work that must remain:

- BZG outlet reporting and Uma Blu nightly close (`/uma-blu-close`, `/bzg/venue-pnl`, `/bzg/outlets`).
- AMG hotel board, chart, journals, and approvals (`/amg/finance`, `/amg/finance/ledger`, `/amg/finance/accounts`, `/amg/finance/journals`, `/amg/finance/approvals`).
- GGV Peaches receipts (`/ggv/finance/receipts`), reimbursements, and the September exception desk (`/ggv/finance/accountant`).

The finance-only wall still denies `/uma-blu-close` to a finance-only seat. Gate 1 does not widen that wall. The close stays listed as the existing Uma Blu workflow.

## 8. Permissions and accountant roles

Authority is Person → Assignment → Position → Role → Permission, with a scope `WHERE` on the legal entity. Cloudflare Access identifies a person. It does not grant a finance permission.

| Role | Lands on | Scope |
| --- | --- | --- |
| `ROLE-GGV-FINANCE-OPERATOR`, `ROLE-GGV-FINANCIAL-CONTROLLER` | `/ggv/finance` | GGV |
| `ROLE-GGV-EXTERNAL-ACCOUNTANT` | `/ggv/finance/accountant` | GGV only. ILA (`tax.accounting@ilaglobalconsulting.com`) sits here |
| `ROLE-AMG-FINANCE-OFFICER`, `ROLE-AMG-FINANCIAL-CONTROLLER`, `ROLE-AMG-ACCOUNTS-PAYABLE`, `ROLE-AMG-ACCOUNTS-RECEIVABLE`, `ROLE-AMG-EXTERNAL-ACCOUNTANT` | `/amg/finance` | AMG |
| `ROLE-BZG-FINANCIAL-CONTROLLER`, `ROLE-BZG-EXTERNAL-ACCOUNTANT` | `/bzg/finance` | BZG |

ILA grants on `ENT-GGV`: read records, evidence, history, invoices, and notas; review reconciliation; propose journals; export; request documents; record filing evidence.

ILA does not receive journal post, payment approval, payment execution, bank-detail changes, user administration, AMG, or BZG. `finance.journal.post`, `payment.approve`, and `payment.execute` exist so they can be refused. They are not allowed.

An accountant-only session is walled to GGV Finance plus shell chrome. The shared nav API and its script are chrome. They do not open another company.

## 9. Intercompany

| Module | State |
| --- | --- |
| `scripts/core/fin_intercompany_billing.py` | Named slots. No live GGV↔AMG/BZG invoice, allocation, or balance |
| `scripts/core/fin_interco1.py` and `dashboards/fin-interco-1.html` | Earlier shell |
| `scripts/core/ggv_intercompany_client_operator_depth.py` | Operator notes. Explicitly not an invoice, allocation, or AR/AP balance |

Intercompany is a dependency that is not implemented. The canonical core will have one intercompany service later. This sequence does not invent a balance to put there.

## 10. Canonical map

Authoritative, and kept:

- Catalog for identity, permissions, audit, and operational finance rows.
- Atrium `atrium.sqlite` for the AMG general ledger.
- Atrium `atrium-bzg.sqlite` and `atrium-ggv.sqlite` as separate empty-or-shell books.
- GGV nota / invoice / bill / bank services.
- AMG calling those services with `ENT-AMG`.
- BZG desk, Uma Blu purchasing, and `bzg_bank_*`.
- Statement library.
- ILA review tables inside the GGV scope.
- Existing audit spine.

Duplicated, and to be collapsed into one experience:

- `ggv-finance.html` and `amg-finance-ops.html` tab rows.
- AMG ledger nav and BZG browse nav, as the front door. The underlying routes stay.
- Accountant tab treated as a side application. It becomes Accounting, Tax, and Reconciliation inside the same nav.

Incomplete, and left incomplete:

- GGV and BZG posted ledgers.
- Management P&L, balance sheet, and cash flow.
- Tax liabilities, NPWP, PKP, regime selection, DJP/Coretax compatibility.
- Intercompany balances.
- Reimbursement ledgers beyond stored GGV rows.

Obsolete as the Finance front door:

- `fin-ap-ar-shell-1`, `fin-recon-shell-1`, `fin-tax-shell-1`, and the other `fin-*-shell` pages. They stay on disk until a later gate so old bookmarks do not 404 in this change. They are not linked from the new primary nav.

## 11. Consolidation decisions

1. One navigation vocabulary for every company: Overview, Banking, Transactions, Sales, Purchases, Expenses, Reconciliation, Accounting, Tax, Reports.
2. Secondary items inside an area. The primary row is the same ten labels on GGV, AMG, and BZG.
3. Each secondary item points at the route that already owns the data. Gate 1 does not move rows and does not rewrite a desk's API.
4. Switching company changes `entity_id` and the book file name. It does not change the ten labels.
5. The signed-in permission set hides secondary items. An empty area still shows the label so the layout does not change shape.
6. ILA uses this nav on GGV. AMG and BZG items are not returned for that assignment.
7. No payment, post, or government-filing action is added to the nav.
8. Books stay in three files. Operational tables keep their entity filter. BZG bank rows stay in `bzg_bank_*` until a later service wraps both table families.
9. September dispositions, Uma Blu purchase orders, and AMG journals are not migrated by the nav.
10. Missing evidence stays missing.

## 12. Risks

| Risk | Control |
| --- | --- |
| A shared screen leaks another company's rows | Nav hrefs stay on the entity's existing routes. Those routes already apply scope. The nav API returns 403 for an entity the person cannot read |
| ILA is walled off the new script | `/api/finance/nav` and `/shared/finance-nav.*` are shell chrome. The payload is still permission-filtered |
| Hiding the old tab row hides a workflow | The old row remains in the page. It is hidden only after the shared nav renders. A failed nav request leaves the old row in place |
| Nightly close 403 for a finance-only seat | Known current wall. Gate 1 does not grant close access |
| Empty GGV books presented as a finished ledger | Nav names the book file and does not open it or invent totals |
| This host is not the running Beta | No catalog backup, no `beta_restart.py`, no live browser acceptance here |

## 13. Implementation sequence

Gate 0. This document. No schema change.

Gate 1. Shared navigation contract in `scripts/core/finance_nav.py`, `GET /api/finance/nav`, and `dashboards/shared/finance-nav.js`. Mounted on the GGV, AMG operational, AMG ledger, and BZG finance pages. Old routes and old buttons remain. No database write.

Gate 2. One operational page template for GGV and AMG, selected by entity. Delete the duplicated markup only after the shared page passes the current GGV and AMG finance tests.

Gate 3. BZG outlet reporting and nightly close as panels inside Reconciliation and Reports, calling the existing Uma Blu APIs. Do not copy close rows. Do not loosen the finance-only wall until the panel is read-only for seats that cannot close.

Gate 4. Accounting area reads the entity book file that already exists. AMG shows the live chart and journals. GGV and BZG show the shell status already returned by `entity_books`. ILA proposals stay unposted.

Gate 5. One reconciliation service in front of `ggv_bank_transactions` and `bzg_bank_transactions`. Tables stay separate. September's five exceptions and 98 dispositions are read, not rewritten.

Gate 6. On the Mac Studio Beta: back up the catalog and the three book files, run only the gates that passed in review, restart Beta with `scripts/beta_restart.py`, and accept in the browser. Production stays on `:8787`.

Gates 2 through 6 are not part of the Gate 1 change.

## 14. Acceptance for Gate 1

- GGV, AMG operations, AMG ledger, and BZG render the same ten primary labels.
- Secondary links for a company point at that company's existing routes.
- ILA's nav payload contains the September exception desk and no AMG or BZG href.
- No nav item posts, pays, or files.
- Existing desk tests that require the old routes still pass.
- No catalog or book file is written.
