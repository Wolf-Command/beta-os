# GGV FINANCE — READY FOR AMANDA TEST

Decision served: owner directive 28 Sep 2026 11:52 WITA. Extends the GGV nota desk and the 28 Sep staff seats. Beta `:8788` only. Production `:8787` stayed pid 15975 (`serve.py`). Beta was restarted from pid 58853 to pid 61134 (`state/build-factory/detach.py` then `scripts/serve_beta.py`). Health on `:8788` is HTTP 200. Unsigned `/ggv/finance` and `/ggv/finance/invoices` are 403. No money movement, no bank write, no payment execution, no Xero write, no customer email send. No Cloudflare edit. No push. Grok was not called. Atrium books were not opened. Authority limits stay 0. SoD constraints stay 0. STAFF READY is false. HUMAN COMMISSIONED is false. No git commit was made. HEAD stays `d97ea20` on `build/wolf-command-rebuild`.

Live catalog after the seat: invoices 0, customers 0. Nothing was invented for cash, profit, ageing, margin, or tax.

## Amanda assignment

Person `PERS-AMANDA` was already bound to `amanda@wolfcommand.net`. No second person was created.

Role `ROLE-GGV-FINANCE-OPERATOR`, label GGV Finance Operator. The role is not named for her. Position `POS-GGV-FINANCE-OPERATOR-1` on `ENT-GGV`. Assignment `ASG-AMANDA-GGV-FIN-1` is ACTIVE and not primary, so her content seat stays the primary seat. Scope `SCOPE-GGV-FINANCE` targets `ENT-GGV` only.

Her content assignment still chooses the existing GGV specialist pages. Those pages already include GGV Finance and do not include Owner, system admin, Atrium, or Blu Zone. Invoice actions are allowed by the finance role, not by her name or email.

## Permission proof

Allowed on that role, through the existing RBAC check: read, create, and edit draft invoices; mark ready; issue; void a document; record paid-claimed; read and create customers; read, create, and edit notas; read and create vendors; create evidence; export finance evidence; read work.

Not granted: `payment.approve`, `payment.execute`, `vendor.bank.change`, `finance.policy.admin`, `finance.invoice.verify`, `atrium.board.read`, `organisation.role.read`.

Checked on a catalog copy: Amanda can create a GGV invoice. She cannot execute a payment. She cannot read the Atrium board. Zayen cannot create a GGV invoice.

## Navigation

WOLF › Goss Group › GGV › Finance, then only these pages: Overview, Invoices, Notas / Bills, Vendors, Customers, History, Reports. Reports is the existing accountant evidence desk. It does not show a profit figure.

The finance switcher lists entities from an active finance assignment. Amanda’s list is GGV. Zayen’s list is AMG. BZG is absent because there is no BZG finance assignment.

## Mobile and desktop

The invoice form is the same page at both widths. At 430px the lines are stacked cards, not a table. The page has no `<table>`. Controls present: + New invoice, customer select, create customer, four line slots, edit a line, delete a line, preview, save draft, issue, PDF link, history, and customer search.

Proof is the Beta handler on a catalog copy: `GET /ggv/finance/invoices` returned 200 and the HTML contained `+ New invoice`, `Add line`, and `max-width: 430px`. A signed browser click-through on the live Beta session was not done.

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

Stored GGV notas are 0 and stored GGV invoices are 0. No consecutive series such as 064A, 065A, 066A is on record, so the next number is not automatic. Saving requires a person to confirm the number. The same number on a second invoice was refused. The unique index is `(entity_id, invoice_number)`.

## PDF and email

Issue writes a PDF from the stored invoice. The same record rendered the same SHA-256. The PDF starts with `%PDF`. Amanda has no PDF editor. There is no sanctioned Gmail draft call on this desk, so issue returns a ready-to-copy draft with `gmail_called` false and `email_sent` false. The draft was not sent.

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

New rows are entity-scoped on the same catalog: `fin_counterparties`, `ggv_invoices`, `ggv_invoice_history`, `ggv_invoice_documents`.

## BZG

Plan only: [BZG-FINANCE-REUSE-PLAN.md](BZG-FINANCE-REUSE-PLAN.md). BZG was not built.

Human test, all PENDING: [GGV-INVOICE-HUMAN-TEST.md](GGV-INVOICE-HUMAN-TEST.md).

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_ggv_finance_invoice_20260928.py` | PASS=66 FAIL=0 |
| `scripts/tests/test_staff_access_20260928.py` | PASS=274 FAIL=0 |
| `scripts/tests/test_ggv_finance_mobile_nota.py` | PASS=138 FAIL=0 |

## Commits

No commit. HEAD `d97ea20`.

RESULT: PASS
