# GROK REVIEW — Dual Approval `c054ac3`

**Date:** 2026-09-17 WITA  
**Commit:** `c054ac3` `feat(core): add dual approval control`  
**Reviewer:** Grok (Engineering Lead) via Peaches factory  
**Method:** Actual diff + live code paths + Peaches re-run of isolated tests

## VERDICT: PASS

No material red-team findings. No Cursor fix loop required.

## Evidence reviewed

- `scripts/migrations/015_dual_approval.sql` + `migrate_dual_approval.py`
- `scripts/core/approvals.py` (`required_decision_count`, `_decide`, snapshot, immutability)
- Unique partial index `idx_core_approval_dec_one_approve_per_person`
- `scripts/tests/test_dual_approval.py` (Peaches re-run: **84/0**)
- Regressions: `test_approval_engine.py` **60/0**, `test_delegation.py` **56/0**
- Live DB after tests: Authority Limits **0**, approval requests **0**, decisions **0**, audit **47** unchanged
- Backup: `catalog/backups/pre-dual-approval-20260917-125412.sqlite`  
  SHA-256 `b0b3dee26a88880301cf17ce4a58de003a96abc69730c8e414ff82f8002095b3`

## Attack checklist

| Attack | Result |
|--------|--------|
| Same-human double APPROVED | BLOCKED (`duplicate_person_approval` + unique index) |
| Alternate AuthIdentity same Person | BLOCKED (Person-id check; test with AUTH-MATT-ALT) |
| Requester self-approval | BLOCKED (existing material deny) |
| Delegator + delegate double count | BLOCKED (one Person stamp = delegate only) |
| NULL amount material / APR-RT-001 | FAIL-CLOSED preserved |
| DLG-RT-001 via delegation | FAIL-CLOSED preserved |
| Lower required_decision_count after create | No mutate API; snapshot includes count |
| Amount/currency/entity/source mutation | Immutable security fields |
| Concurrent same Person | One APPROVED row |
| Concurrent distinct Persons | Both rows → APPROVED when N met |
| Replay after terminal | Denied |
| REJECT then approve | Denied |
| WI completion = approval | NOT equated |
| Execute on approve | `executed_source=False` |
| Test pollution of live | PASS (0/0/47) |

## Design notes (non-findings)

- Status stays `PENDING` until N independent APPROVED (no PARTIALLY_APPROVED) — matches Grok plan.
- Partial audits as `approval.decision_recorded`; terminal as `approval.granted`.
- Live dual-approval business policy NOT configured (correct).

## Roles

Cursor authored application code. Peaches did not. Production untouched.
