# GGV FINANCE — READY FOR AMANDA TEST

Decision served: owner decision (Matthew, 28 Sep 2026 13:17 WITA). The next GGV invoice number is 067A. Wolf owns issuance. This extends the same GGV invoice desk from the 28 Sep 2026 11:52 WITA directive. Beta `:8788` only. Production `:8787` stayed pid 15975 (`serve.py`). Beta was restarted from pid 66899 to pid 68812 (`state/build-factory/detach.py` then `scripts/serve_beta.py`). Health on `:8788` is HTTP 200. Unsigned `/ggv/finance` and `/ggv/finance/invoices` are 403. No money movement, no bank write, no payment execution, no Xero write, no Gmail call, no customer email send. No Cloudflare edit. No push. Grok was not called. Atrium books were not opened. Authority limits stay 0. SoD constraints stay 0. STAFF READY is false. HUMAN COMMISSIONED is false.

Live catalog: invoices 0, customers 0. The sequence row is `ENT-GGV`, format `{n:03d}A`, next value 67. Nothing was invented for cash, profit, ageing, margin, or tax. Historical invoices 064A, 065A, and 066A were not created.

## Amanda assignment

Person `PERS-AMANDA` was already bound to `amanda@wolfcommand.net`. No second person was created.

Role `ROLE-GGV-FINANCE-OPERATOR`, label GGV Finance Operator. The role is not named for her. Position `POS-GGV-FINANCE-OPERATOR-1` on `ENT-GGV`. Assignment `ASG-AMANDA-GGV-FIN-1` is ACTIVE and not primary, so her content seat stays the primary seat. Scope `SCOPE-GGV-FINANCE` targets `ENT-GGV` only.

Her content assignment still chooses the existing GGV specialist pages. Those pages already include GGV Finance and do not include Owner, system admin, Atrium, or Blu Zone. Invoice actions are allowed by the finance role, not by her name or email.

## Permission proof

Allowed on that role, through the existing RBAC check: read, create, and edit draft invoices; mark ready; issue; void a document; record paid-claimed; read and create customers; read, create, and edit notas; read and create vendors; create evidence; export finance evidence; read work.

Not granted: `payment.approve`, `payment.execute`, `vendor.bank.change`, `finance.policy.admin`, `finance.invoice.verify`, `finance.invoice.import`, `atrium.board.read`, `organisation.role.read`. Historical import is on `ROLE-MATT` only.

Checked on a catalog copy: Amanda can create a GGV invoice. She cannot execute a payment. She cannot read the Atrium board. Zayen cannot create a GGV invoice.

## Navigation

WOLF › Goss Group › GGV › Finance, then only these pages: Overview, Invoices, Notas / Bills, Vendors, Customers, History, Reports. Reports is the existing accountant evidence desk. It does not show a profit figure.

The finance switcher lists entities from an active finance assignment. Amanda’s list is GGV. Zayen’s list is AMG. BZG is absent because there is no BZG finance assignment.

## Mobile and desktop

The path is GGV → Finance → Invoices → + New Invoice. The invoice form is the same page at both widths. At 430px the lines are stacked cards, not a table, and + New Invoice is a full-width control. The page has no `<table>`. The operator form has no invoice-number field. Controls present: + New Invoice, customer select, create customer, line items, edit a line, delete a line, live server preview, save draft, issue, PDF link, and a copy-ready email draft.

Proof is the Beta handler on a catalog copy: `GET /ggv/finance/invoices` returned 200 and the HTML contained `+ New Invoice`, `Number assigned on issue`, `Add line`, and `max-width: 430px`. It did not contain `id="inv-number"`. A signed browser click-through on the live Beta session was not done.

## Invoice maths

The server calculates every total. A typed grand total of `1` was stored as the calculated total, not `1`.

Rounding is half up. IDR uses 0 decimal places. Any other 3-letter currency uses 2. Each line subtotal is rounded, then each line tax is rounded, then the invoice total is the sum of those rounded line totals.

| Case | Result |
| --- | --- |
| IDR, qty 1, unit 10.5, no tax | 11 |
| IDR, qty 1, unit 333, tax 10% | tax 33, total 366 |
| USD, qty 1, unit 10.005, no tax | 10.01 |

## Line items

Four separate lines were saved. Deleting one line changed the total. A description with two quantity marks (`2 x` and `1 x`) was refused. A price typed inside the description was refused.

## Numbering

Wolf assigns the number at issue. A draft stores no number and shows “Number assigned on issue”. The operator does not type a number. The first issue on an empty sequence is 067A. The next issue is 068A.

The sequence lives in `fin_invoice_sequences` (`entity_id`, `format`, `next_value`, `updated_by`, `updated_at`). GGV is seeded at next value 67 and format `{n:03d}A`. Migration `031_ggv_invoice_sequences` is idempotent. Re-running it left next at 67. The owner decision is one row in `fin_invoice_sequence_audit`: actor Matthew, reason text for 28 Sep 2026 13:17 WITA. A second run did not add a second owner row.

Allocation is one `BEGIN IMMEDIATE` transaction. The row update accepts only the current `next_value`, then the invoice update stores that number. Six parallel issues produced six different numbers and no errors. A database trigger aborts any update that would set `next_value` lower. The unique index remains `(entity_id, invoice_number)`.

An issued number cannot be changed. The API returns `number_immutable`. Void keeps the number, writes the void on the invoice history, and leaves the sequence where it is. After 067A was issued and 068A was voided, the next issue was 069A. 068A was not used again.

Historical import is owner-only (`finance.invoice.import` on `ROLE-MATT`). It stores the original number, sets `number_source` to `imported`, and refuses a number that is already stored (`duplicate_number`, `conflict` true). Import of 064A on a sequence already at 70 left next at 70. Import of 090A advanced next to 91. Import does not go backwards. 064A, 065A, and 066A were not created on the live catalog. The 064A and 090A rows exist only on the test copy.

## PDF and email

Issue writes a PDF from the stored invoice, including the number assigned in that same transaction. The same record rendered the same SHA-256. The PDF starts with `%PDF`. Amanda has no PDF editor. Issue still returns a copy-ready draft with `gmail_called` false, `gmail_draft_created` false, and `email_sent` false. The draft was not sent.

Next integration step, not built: Generate Gmail draft with PDF attachment — human review/send, never automatic. The same sentence is on `CR-8f20b066fac63445` and `CR-214e370b5b96cbd1` `next_action`. Both rows stay OPEN. No Gmail API call was made.

## Customers

Customers are `fin_counterparties` rows for one entity, linked to `crm_customers` only when that table already has the same normalised name. The live catalog has no `crm_customers` table and no finance customers. The One and Keen Eye were not created. A second save of the same legal name was refused on the test copy.

From on a GGV invoice is the stored entity name, Goss Group Ventures. The billing address on the entity record is not stored, so the address stays unknown.

## States, audit, history

Draft, ready (approval required), issued, paid claimed, and void can be written by the operator where the transition allows it. Overdue is calculated from an issued invoice whose due date is before today. Part paid and payment verified are refused. Issued is not paid. Claimed is not verified. Claiming does not move money.

Each save writes `ggv_invoice_history` and an audit event with the person id. The invoice stores `created_by`, `finalised_by`, and timestamps.

## Denied routes

| Route | Result |
| --- | --- |
| Unsigned `/ggv/finance` and `/ggv/finance/invoices` on Beta | 403 |
| Unsigned `POST /api/ggv/finance/pay` on Beta | 403 |
| Amanda `POST /api/ggv/finance/pay` on the test handler | 405 |
| Amanda `/amg/finance` | 403 |
| Zayen `/ggv/finance` | 403 |
| Invoice verify and part-paid | 405 |
| Bank change | refused by the existing nota desk |

## Atrium and shared finance reuse

| Piece | Where it already lived |
| --- | --- |
| Nota upload, vendors, history, month export, GGV scope | `scripts/core/ggv_finance_nota.py` |
| RBAC, audit, evidence | `core.rbac`, `core.audit`, `core.evidence` |
| Person, role, assignment, scope | `scripts/core/staff_access.py` |
| My Work link | `scripts/core/staff_home.py` |
| Entity legal name | `org_entities` for `ENT-GGV` |
| Atrium seat and page | Zayen’s existing Atrium Finance assignment and `/amg/finance` |
| Books, cash, profit, bank | Not opened. `fin_accounting_core` was not given a new writer |

New rows are entity-scoped on the same catalog: `fin_counterparties`, `ggv_invoices`, `ggv_invoice_history`, `ggv_invoice_documents`, `fin_invoice_sequences`, `fin_invoice_sequence_audit`.

## BZG

Plan only: [BZG-FINANCE-REUSE-PLAN.md](BZG-FINANCE-REUSE-PLAN.md). BZG was not built.

Human test, all PENDING: [GGV-INVOICE-HUMAN-TEST.md](GGV-INVOICE-HUMAN-TEST.md).

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_ggv_finance_invoice_20260928.py` | PASS=92 FAIL=0 |
| `scripts/tests/test_staff_access_20260928.py` | PASS=274 FAIL=0 |
| `scripts/tests/test_ggv_finance_mobile_nota.py` | PASS=138 FAIL=0 |
| `scripts/tests/test_ggv_finance_nota_storage_accountant.py` | PASS=100 FAIL=0 |

## Commits

Local commit on `build/wolf-command-rebuild`. Not pushed.

RESULT: PASS
