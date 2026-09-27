# PROPOSED wide approval policy (CAP-CORE-07)

Status: **PROPOSED. Not loaded. Not active.** Owner brief 28 Sep 2026 06:46 WITA, item 3. This is the wide pack `CAP-CORE-07` was waiting for. It is not canonical. `CAP-CORE-07` stays BLOCKED_OWNER until you mark this page.

## What the engine already does

`scripts/core/governance_policy.py` matches `core_governance_policies` where `status = 'ACTIVE'`. `INACTIVE` is ignored. No matching policy is `NO_MATCH` and the evaluation is denied. That is not an allow. Amount-governed actions without an amount are `MISSING_AMOUNT` and denied.

The live table has one row: `GPO-HABITAT-CONTENT-PUBLISH`, version 1, status `ACTIVE`, entity `ENT-GGV`, action `HABITAT.CONTENT.PUBLISH`. This proposal does not edit that row. It is not a wide finance pack.

`core_approval_requests` stays 0. This proposal does not insert a request.

Known action types the matcher already uses: `SPEND_APPROVE`, `EXCEPTION`, `GENERAL_MATERIAL`. Request types `SPEND`, `EXCEPTION`, `GENERAL`, `ACCESS`, `HR`, and `CONTRACT` map onto those. Payment, bank-detail change, journal, refund, and payroll are not separate action types today. Until you approve a mapping, they sit under `SPEND_APPROVE` or `GENERAL_MATERIAL` only as a proposal.

## Proposed pack

Status if it were ever stored: `INACTIVE`. It was not stored. Amount bands are null. Null is **UNRESOLVED**, not zero.

Applies to `ENT-GGV`, `ENT-BZG`, and `ENT-AMG`. Scope: the caller's assignment scope. A display name is not a match.

| proposed policy | action | approval | decisions | evidence | amount |
| --- | --- | --- | --- | --- | --- |
| Spend above the line | `SPEND_APPROVE` | required | 1 | required | min and max UNRESOLVED. Currency UNRESOLVED |
| Spend at or under the line | `SPEND_APPROVE` | UNRESOLVED whether approval is still required | 1 if required | UNRESOLVED | the line is UNRESOLVED |
| Exception | `EXCEPTION` | required | 1 | required | UNRESOLVED |
| Other material action | `GENERAL_MATERIAL` | required | 1 | required | UNRESOLVED |
| Payment approval | mapped to `SPEND_APPROVE` until a distinct type exists | required | 2 | required | UNRESOLVED. The two decisions are a control, not an amount |
| Bank-detail change | mapped to `GENERAL_MATERIAL` until a distinct type exists | required | 2 | required | every change. Not an amount |
| Material journal | mapped to `GENERAL_MATERIAL` | required only when material | 1 | required | material line UNRESOLVED |
| Refund / void | no permission and no action type | required | 2 proposed | required | UNRESOLVED |
| Payroll | no permission and no action type | required | 2 proposed | required | UNRESOLVED |

The approver comes from the finance matrix: a role that holds the approval permission, not the person who prepared the item. Those approval permissions are ungranted. This policy does not grant them.

Authority limits stay 0. A policy without a limit does not invent a ceiling. Where both would apply, the limit is still UNRESOLVED, so the action stays denied until you set one.

`ROLE-MATT` holds `approval.decide`. That grant is not a wide policy. Delegation must not collapse a two-decision item onto one person.

## What stays denied until you approve

No inactive row was inserted, so today's evaluate path is unchanged: governed actions with no active match are denied, and the Habitat publish policy remains the only active row. Approving this page does not by itself insert the row.

## APPROVE / CHANGE — Matt

Mark one:

- [ ] APPROVE this wide policy as proposed. Thresholds stay UNRESOLVED. Do not activate it in the same step. A later pack may load it `INACTIVE` only after this mark, and `ACTIVE` only under a second mark.
- [ ] CHANGE. Note the change. Leave any amount you do not want to set as UNRESOLVED.
- [ ] NO PACK. Record that no wide production policy is authorised. `CAP-CORE-07` can then leave BLOCKED_OWNER without a pack. The Habitat publish policy stays as it is.

| item | change |
| --- | --- |
| Spend line | |
| Whether under-line spend still needs approval | |
| Exception | |
| Payment decision count (proposed 2) | |
| Bank-detail change (proposed every change, 2 decisions) | |
| Journal material line | |
| Refund / void | |
| Payroll | |
| Currency | |
