# ATRIUM FC AUTHORITY MATRIX

Decision served: ATRIUM-SOD-1 / Matt APPROVED 29 Sep 2026 13:32 WITA;  
**ATRIUM-SOD-1B UPDATE 29 Sep 14:10** — real AP/AR staffing (supersedes Matt-as-preparer).

Surfaces: live `/amg/finance` (sidecar `:8790` via Wolf proxy) and lite `/amg/finance/lite`.

## Seats (ENT-AMG)

| Seat | Role / Position | Person | Notes |
| --- | --- | --- | --- |
| Financial Controller | `ROLE-AMG-FINANCIAL-CONTROLLER` / `POS-AMG-FINANCIAL-CONTROLLER-1` / `ASG-ZAYEN-FC-1` | Zayen | Approve + post others (SoD) |
| Accounts Payable | `ROLE-AMG-ACCOUNTS-PAYABLE` / `POS-AMG-ACCOUNTS-PAYABLE-1` / `ASG-ZENITALFATHAN-AP-1` | `PERS-ZENITALFATHAN` · `zenitalfathan@gmail.com` | Prep/submit; CF allow pending |
| Accounts Receivable | `ROLE-AMG-ACCOUNTS-RECEIVABLE` / `POS-AMG-ACCOUNTS-RECEIVABLE-1` / `ASG-ZAYEN-AR-1` | Zayen **temporary** | Separate assignment; end later = data only |
| Finance Officer | `ROLE-AMG-FINANCE-OFFICER` / `POS-AMG-FINANCE-OFFICER-1` | **VACANT** | Keep; do not invent person |

CF email to add: `zenitalfathan@gmail.com` (Peaches verifies before AP commissioning activate).

## Journal lifecycle

| Step | Who | Wolf permission | Product behaviour |
| --- | --- | --- | --- |
| Prepare (draft) | AP / AR / Officer / FC with draft | `atrium.journal.draft` | Allowed |
| Validate | Preparer seat | `atrium.journal.draft` | DRAFT\|RETURNED → VALIDATED |
| Submit | Preparer seat | `atrium.journal.draft` | VALIDATED → SUBMITTED |
| Approve | Financial Controller, **not** the preparer | `atrium.journal.approve` | SUBMITTED → APPROVED |
| Return | Financial Controller, **not** the preparer | `atrium.journal.reject` | SUBMITTED\|APPROVED → RETURNED (reason required) |
| Post | Financial Controller, **not** the preparer | `atrium.journal.post` | APPROVED → POSTED (SoD; no skips) |

## Segregation of duties

- Compare `journal.preparer_person_id` to `actor.person_id` — **never** the set of roles held.
- If equal → 403 on approve and on post, even when the actor also holds Controller.
- If Zayen prepares as AR, Approve/Post requires a different authorised approver (Owner Matt interim).
- UI titles are plain language only (Accounts Payable / Accounts Receivable / Atrium Financial Controller).

## Still denied on preparer seats (AP / AR / Officer)

| Action | Gate |
| --- | --- |
| Approve / post | role grant absent + mount sensitive |
| Payments | `payment.execute` / `payment.approve` |
| Bank-detail change | `vendor.bank.change` + `/bank` path block |
| Owner / admin | `finance.policy.admin`, `/api/admin/*` |
| Other companies | non–ENT-AMG routes 403 |

## Historical data

No authoritative AMG ledger found (see `state/atrium-sod/discovery.md`). Import model present; import nothing. GL empty copy states sources searched + Wolf cutover date. Wolf-created commissioning lines are flagged `wolf_created=1`.
