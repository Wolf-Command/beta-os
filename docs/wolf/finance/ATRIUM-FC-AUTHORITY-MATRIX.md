# ATRIUM FC AUTHORITY MATRIX

Decision served: HUMFIX-1 / Matt relay 29 Sep 2026 ~11:14 WITA.  
Seat: `PERS-ZAYEN` · `ASG-ZAYEN-FC-1` · `ROLE-AMG-FINANCIAL-CONTROLLER` · ENT-AMG only.  
Surfaces: live `/amg/finance` (sidecar `:8790` via Wolf proxy) and lite `/amg/finance/lite`.

## Journal lifecycle

| Step | Who | Wolf permission | Product behaviour |
| --- | --- | --- | --- |
| Prepare (draft) | FC or Officer with draft grant | `atrium.journal.draft` | Allowed |
| Review / validate | Same preparer seat | `atrium.journal.draft` / canEdit | Allowed |
| Approve | Financial Controller, **not** the preparer | `atrium.journal.approve` | Allowed for FC with SoD |
| Reject / return | Financial Controller, **not** the preparer | `atrium.journal.reject` | Returns VALIDATED/APPROVED → DRAFT |
| Post | — | `atrium.journal.post` | **DENIED** — open Matt policy (HUMFIX-1). Existing hold kept |

## Segregation of duties

- FC may **not** approve or reject a journal they prepared (`created_by` matches their identity / display name).
- A different preparer is required. Record who prepared and who approved on the journal header.
- Self-approve → 403 `sod_self_approve`.

## Still denied on this seat

| Action | Permission / gate |
| --- | --- |
| Post journal | `atrium.journal.post` + mount sensitive block |
| Reverse journal | mount sensitive block |
| Payments | `payment.execute` / `payment.approve` |
| Bank-detail change | `vendor.bank.change` + `/bank` path block |
| Owner / admin | `finance.policy.admin`, `/api/admin/*` |
| Other companies | ENT-GGV / ENT-BZG routes 403 |

## Canonical matrix note

`docs/wolf/five/PROPOSED-FINANCE-CONTROL-MATRIX.md` was silent / UNRESOLVED on ENT-AMG journal approve for FC. HUMFIX-1 implements approve + reject/return only. **Post remaining denied is an open policy point for Matt — do not invent posting authority.**

## Verification

- Catalog: FC role has `atrium.journal.approve` + `atrium.journal.reject`; not `atrium.journal.post`.
- Assertion: Wolf emits `ROLE-AMG-FINANCIAL-CONTROLLER` for `ASG-ZAYEN-FC-1`.
- Sidecar maps that role to accountant pillar + `accounting-core.canApprove` override.
- Approve of own journal → 403. Approve of another preparer’s VALIDATED journal → 200.
- Post / pay / bank / admin → 403.
