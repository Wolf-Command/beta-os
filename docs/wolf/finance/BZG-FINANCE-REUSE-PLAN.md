# BZG finance — reuse plan

Decision served: owner directive 28 Sep 2026 11:52 WITA. Plan only. BZG finance is not built in this pack.

## Outlets

Use these when a BZG finance assignment exists. Do not invent figures for them.

- Uma Blu
- Blu Zone Rainforest Restaurant & Bar
- Pool bar
- Merah
- Rooftop
- Catering, where a bill is for catering
- Room service, where a bill is for a room

## What BZG needs

Accounts payable, vendors, purchasing, outlet allocation, inventory and cost context, bills and notas, daily close and reconciliation, intercompany, and reporting.

ESB stays the POS sales truth. Wolf does not replace ESB and does not invent a second sales total.

## What to reuse

| Need | Reuse | Do not start |
| --- | --- | --- |
| Database, audit, evidence | Beta catalog, `core.audit`, `core.evidence` | A second finance database |
| Access | Person → Role → Assignment → Scope → Permission → Audience | A BZG login list |
| Approvals | Authority limits, approval policy, separation of duties | A payment button |
| Vendors and notas | `scripts/core/ggv_finance_nota.py` with an entity id | A copy of the nota module |
| Customers | `fin_counterparties` in `scripts/core/ggv_finance_invoice.py`, entity id on the row | A BZG-only customer list |
| Invoices | Same invoice record, maths, PDF, and states, with BZG branding from `org_entities` | A second PDF writer |
| Purchasing | Existing Uma purchase-request rows | A new purchasing app |
| Daily close | Existing Uma close | A second close ledger |
| Intercompany | `scripts/core/fin_intercompany_billing.py` | A new intercompany ledger |
| Reporting | Evidence export and `scripts/core/fin_mgmt_reporting.py` reads | A typed profit, cash, margin, or tax figure |
| Entity switch | `finance_entities()` — BZG appears only after a BZG finance assignment | A switcher entry with no assignment |

## Entity config still to name

Legal entity, bank accounts, tax profile, chart of accounts, authority limits, branding, workflows, scope, and reporting packs. None of these are filled in here. Unknown stays unknown.

## Not in this pack

No BZG pages, no BZG role, no BZG invoices, no ESB write, no stock movement, and no money movement.
