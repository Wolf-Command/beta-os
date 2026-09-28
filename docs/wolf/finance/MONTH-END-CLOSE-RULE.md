# PERMANENT RULE — Month-End Close + Shareholder Reporting (Wolf Finance Core)

Owner: Matthew Goss. Locked: 28 Sep 2026. Applies to GGV, AMG, BZG (inherited by all entities). Lane: P0 Finance / Shareholder Reporting.

## Principle
The shareholder report on the 5th is the OUTPUT of the previous month's close. It is not a standalone report job.

## 1. Bank statements (required inputs)
- Canonical register of every active bank account per legal entity.
- On day 1 of each month, create a work item per registered account for the previous month's statement.
- The responsible finance person uploads the actual statement into Wolf.
- Store the original as evidence with: company, bank, account, statement period, opening balance, closing balance, upload date, uploader, source/provenance, file hash, reconciliation status.
- Preserve the original. Never silently replace it (new versions are appended, not overwritten).
- Missing statement: show `MONTH END BLOCKED — BANK STATEMENT MISSING` with the exact account and period.

## 2. Reconciliation
- Import/extract statement lines into that company's ledger/reconciliation workspace only (no cross-company leakage).
- Match against: invoices, customer receipts, supplier bills, payments, notas/receipts, payroll, transfers, journals, intercompany, other legitimate entries.
- AI may suggest matches. Status and accounting consequences are deterministic and auditable.
- Statuses: MATCHED, PARTIALLY MATCHED, UNMATCHED, DUPLICATE, NEEDS EVIDENCE, NEEDS HUMAN REVIEW.
- Never invent a counterparty, invoice, account code or explanation to force a match.

## 3. Month-end audit (deterministic checks, where applicable)
Bank opening/closing balance tie-out; unreconciled items; missing evidence; duplicates; AR/AP reconciliation; unusual journals; revenue vs authoritative operating systems; intercompany balances; tax/service charge; inventory/cost variances; payroll; outstanding approvals; stale/missing source data; entity-specific controls.
- AMG: reconciles to authorised hotel-system data.
- BZG: ESB is POS/transaction truth and reconciles INTO Wolf Finance. Wolf is never a competing POS.
- GGV: invoices, receipts, notas/bills and bank activity reconcile through the same Finance Core.

## 4. Close gate (per company, visible)
WAITING FOR STATEMENTS -> RECONCILING -> EXCEPTIONS OPEN -> READY FOR REVIEW -> MONTH CLOSED.
- Show exactly what blocks close.
- Never report an incomplete month as complete. Never hide differences to meet the 5th.
- Material exceptions follow Wolf approvals/evidence/authority rules.

## 5. Director's Report
- In the same workflow, early in the month (not on the 5th), ask Matt separately for GGV, AMG, BZG commentary.
- He types or dictates rough thoughts. Wolf structures and polishes without changing meaning, then presents for approval.
- Missing: `WAITING FOR DIRECTOR'S REPORT`.

## 6. Shareholder report gate
- Built only from the closed/reconciled month, never preliminary dashboard figures.
- Target distribution: the 5th.
- If close is blocked near the deadline, surface the exception to Matt. Never silently publish unreliable numbers.
- First live cycle: Matt approves the three reports and recipient lists before any send. No auto-send until he commissions.

## 7. UX
One MONTH END workspace per company: previous month; statements received/missing; reconciliation progress; open exceptions; audit checks; Director's Report status; finance review status; shareholder report status; delivery status.
Owner dashboard shows only exceptions needing Matt. He never manages the reconciliation process.

## Hard constraints
No ClickUp dependency. No fake data. No invented reconciliation. Preserve evidence and audit history. Beta first. Production untouched.
