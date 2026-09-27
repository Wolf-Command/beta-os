# PROPOSED finance control matrix

Status: **PROPOSED. Not loaded. Not active.** Owner brief 28 Sep 2026 06:46 WITA, item 3. This uses Wolf Core roles, assignments, scopes, permissions, authority limits, approvals, delegation, segregation of duties, evidence, and exceptions. It does not create a second system. No person is an authority. No amount was invented. No row was inserted into the live catalog.

Live counts after this document, read-only: `org_authority_limits` 0, `core_sod_constraints` 0, `core_governance_policies` 1 (`GPO-HABITAT-CONTENT-PUBLISH`, already there, not this matrix), `venue_close_variance_policies` 0.

## Why it is not in the catalog

`core_governance_policies` and `core_sod_constraints` have status `INACTIVE`, and evaluate reads `ACTIVE` only. `org_authority_limits.limit_type = AMOUNT` cannot be stored without `currency` and `threshold_value`. `venue_close_variance_policies.abs_threshold_amount` is `NOT NULL`. An unresolved threshold cannot be stored. `scripts/tests/test_cap_core_08_self_close.py` requires the live SoD count to stay 0, and `scripts/tests/test_authority_limits.py` requires the live authority-limit count to stay 0. A proposed row in those tables would be a counted pack. Nothing here was inserted. Nothing was activated.

## Roles that already exist

Entities: `ENT-GGV`, `ENT-BZG`, `ENT-AMG`.

| role | holds today that this matrix uses | does not hold |
| --- | --- | --- |
| `ROLE-BZG-FB-OPS-LEAD` | `bzg.pr.operator`, `venue.receive`, `venue.close.submit`, `venue.close.read`, `venue.close.resolve_exception` | `bzg.pr.payment_approve`, `venue.close.verify`, `payment.approve`, `payment.execute` |
| `ROLE-BZG-CLOSER` | `venue.close.submit`, `venue.close.read` | `venue.close.verify`. The position `POS-BZG-CLOSER-UMA-1` has no active assignment |
| `ROLE-BZG-HFB` | `venue.close.verify`, `venue.close.resolve_exception`, `venue.close.read` | `bzg.pr.operator`, `venue.receive`, `venue.close.submit`, `bzg.pr.payment_approve` |
| `ROLE-CONTENT-MGMT` | `finance.nota.create`, `finance.nota.edit`, `finance.nota.read`, `vendor.create`, `vendor.edit`, `vendor.read` | `finance.nota.review`, `vendor.bank.change`, `payment.approve`, `payment.execute` |
| `ROLE-GGV-EXTERNAL-ACCOUNTANT` | `finance.nota.read`, `finance.nota.review`, `vendor.read`, `finance.evidence.export` | `finance.nota.create`, `vendor.bank.change`, `payment.approve`. Position `POS-GGV-EXT-ACCT` may stay empty |
| `ROLE-MATT` | owner/executive grants including `venue.close.submit`, `venue.close.verify`, `finance.nota.create`, `vendor.create`, `approval.decide`, `delegation.create` | `payment.approve`, `payment.execute`, `vendor.bank.change`, `bzg.pr.payment_approve`, `finance.nota.review` |
| `ROLE-AMG-GM` | `amg.day.operator` | no finance, journal, payment, or bank permission |

Permissions that exist and are granted to nobody: `payment.approve`, `payment.execute`, `vendor.bank.change`, `bzg.pr.payment_approve`, `finance.policy.admin`, `governance.policy.manage`, `sod.constraint.manage`. This proposal does not grant them.

Permissions that do not exist: journal prepare, journal approve, petty cash, refund, void, payroll prepare, payroll approve, invoice as a code distinct from `finance.nota.review`. Those duties stay unmapped until a permission exists. This proposal does not create permissions.

Authority limits: none. Every monetary threshold below is **UNRESOLVED**. Empty is not a zero tolerance.

## Duties

| duty | proposed acting role | existing permission | proposed control | threshold |
| --- | --- | --- | --- | --- |
| Purchasing / requesting | `ROLE-BZG-FB-OPS-LEAD` | `bzg.pr.operator` | request only. Evidence on the request when the amount is above the unresolved line | UNRESOLVED |
| Approval of that request | a role that is not the requester. `ROLE-BZG-HFB` is the proposed approver role. It does not hold `bzg.pr.payment_approve` today | `bzg.pr.payment_approve` (ungranted) | approval required. Same person forbidden | UNRESOLVED |
| Receiving | `ROLE-BZG-FB-OPS-LEAD` holds `venue.receive` today, which is the same role as requesting | `venue.receive` | same person forbidden to receive a request they raised, when the amount is above the unresolved line. Below that line: UNRESOLVED | UNRESOLVED |
| Invoice verification | `ROLE-GGV-EXTERNAL-ACCOUNTANT` | `finance.nota.review` | reviewer is not the creator. Seat may stay empty. Empty is not a verified invoice | UNRESOLVED for what counts as material |
| Payment preparation | UNRESOLVED role | `payment.execute` (ungranted) | prepare is not approve. No grant in this proposal | UNRESOLVED |
| Payment approval | UNRESOLVED role, not the preparer | `payment.approve` (ungranted) | two approval decisions proposed. Same person forbidden. No grant | UNRESOLVED |
| Bank-detail change | UNRESOLVED approver role. Not the same person who holds `vendor.create` on that vendor | `vendor.bank.change` (ungranted) | any change, not an amount band. Two approval decisions proposed. Evidence required. No grant | not an amount. The band is UNRESOLVED only if Matt later wants a floor; default proposal is every change |
| Petty cash | recorder: `ROLE-BZG-FB-OPS-LEAD`. Verifier: `ROLE-BZG-HFB` | no petty permission. The ops console records petty. It is not a payment | same person forbidden to record and verify. Variance policy is the Uma document, not a number here | UNRESOLVED |
| Journal preparation | UNRESOLVED. No Wolf permission. `ENT-AMG` is not given a journal grant to close a checkbox | none | do not open Atrium books for this matrix | UNRESOLVED for material |
| Journal approval where material | a different role from the preparer. UNRESOLVED which role | none | approval and evidence only when material. Material amount UNRESOLVED. Fail closed until that amount exists | UNRESOLVED |
| Daily close submission | `ROLE-BZG-CLOSER` or `ROLE-BZG-FB-OPS-LEAD` | `venue.close.submit` | submit is not verify. Closer seat stays empty until a person is assigned. This matrix does not assign one | cash declaration uses the variance policy. Threshold UNRESOLVED |
| Daily close verification | `ROLE-BZG-HFB` | `venue.close.verify` | same person forbidden. The engine already denies `sod_self_close` without a constraint row. `ROLE-MATT` holds both submit and verify; self-verify stays denied by that check | UNRESOLVED |
| Refunds / voids | UNRESOLVED pair of roles | none | same person forbidden to prepare and approve, once permissions exist. No permission created | UNRESOLVED |
| Payroll preparation | UNRESOLVED | none. Catalog payroll is `CAP-HR-04`, not a permission in this catalog | no payroll row, no amount | UNRESOLVED |
| Payroll approval | a different role from preparation. UNRESOLVED | none | same person forbidden once permissions exist | UNRESOLVED |

## SoD pairs

Relationship the engine already knows: `SAME_PERSON_FORBIDDEN`. These pairs are proposed. They are not rows.

| prior action | later action | process family |
| --- | --- | --- |
| `bzg.pr.operator` | `bzg.pr.payment_approve` | purchasing |
| `bzg.pr.operator` | `venue.receive` | purchasing, only above the unresolved amount |
| `finance.nota.create` or `finance.nota.edit` | `finance.nota.review` | invoice |
| `payment.execute` | `payment.approve` | payment |
| `vendor.create` or `vendor.edit` | `vendor.bank.change` | vendor bank |
| petty record | petty verify | petty |
| journal prepare | journal approve | journal, only where material. Both actions lack permissions |
| `venue.close.submit` | `venue.close.verify` | daily close. Code already denies self-verify |
| refund prepare | refund approve | refund. Both actions lack permissions |
| payroll prepare | payroll approve | payroll. Both actions lack permissions |

Delegation (`delegation.create` on `ROLE-MATT`) must not put both sides of a pair on one person. No delegation row was written.

Evidence: `evidence.record.submit` already exists. Proposed as required for payment approval, bank-detail change, material journal approval, and close verification. The only live evidence requirement remains `EVR-HABITAT-CONTENT-PUBLISH`. No requirement was inserted.

Exceptions: `governance.exception.request` already exists. A variance or a material override uses an exception. It does not skip the pair. No exception was inserted.

`GPO-HABITAT-CONTENT-PUBLISH` stays the one active governance policy. It is not a finance pack.

## APPROVE / CHANGE — Matt

This page is the decision. Writing on it does not activate the matrix. Activation is a later pack after you mark APPROVE.

Mark one:

- [ ] APPROVE the matrix as proposed, with every threshold still UNRESOLVED, and no live row until a later pack loads it inactive or active under your mark.
- [ ] CHANGE. Write the change beside the duty. Do not write an amount in chat if you would rather set it in the existing store later. An amount left blank stays UNRESOLVED.
- [ ] REJECT. No finance pack. Core stays as it is: no SoD rows, no authority limits, self-close already denied in code.

Changes (leave blank if APPROVE or REJECT):

| duty | change |
| --- | --- |
| Purchasing / requesting | |
| Approval | |
| Receiving | |
| Invoice verification | |
| Payment preparation | |
| Payment approval | |
| Bank-detail change | |
| Petty cash | |
| Journal preparation | |
| Journal approval | |
| Daily close submission | |
| Daily close verification | |
| Refunds / voids | |
| Payroll preparation | |
| Payroll approval | |
| Thresholds (each stays UNRESOLVED unless you set it) | |

Owner / Executive role: keep self-approval denied. Do not seat the closer here. Do not seat the external accountant here. Do not open Atrium books here.
