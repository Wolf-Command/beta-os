# GROK ENGINEERING REVIEW + RED TEAM — Delegation

**Role:** GROK (engineering review / red-team) — distinct from Peaches verify  
**Commit:** `8c4285ac0ce6b7fc918c213efa5d340b8a41bd61`  
**Date:** 2026-09-17 WITA  
**Method:** Read actual `delegation.py`, `014_delegation.sql`, `migrate_delegation.py`, approvals `_decide` integration, serve handlers, `test_delegation.py`.

**Verdict:** **FAIL — 1 MATERIAL defect** (bounded fix before Matt final report)

---

## Attack checklist

| Attack | Result | Evidence |
|--------|--------|----------|
| Identity impersonation | **BLOCKED** | decided_by = verified; basis may be DELEGATION |
| Forge delegator | **BLOCKED** | create forged_delegator unless Matt governance |
| Forge delegate / assignment mismatch | **BLOCKED** | assignment must belong to named person |
| Self-delegation | **BLOCKED** | self_delegation |
| Re-delegation flag | **BLOCKED** | allow_redelegation must be 0 + DB CHECK |
| Re-delegate via delegated power | **BLOCKED** | create requires **native** RBAC on delegator |
| Wrong entity / scope widen | **BLOCKED** | entity match + `_scope_covers_target` |
| Before/after window | **BLOCKED** | lazy SCHEDULED/EXPIRED |
| Revoked | **BLOCKED** | status REVOKED |
| Stale assignments | **BLOCKED** | both assignments re-checked at use |
| Delegator lost permission | **BLOCKED** | native re-evaluate at use |
| Cap / authority escalation | **BLOCKED** | min(grant, delegator threshold); fail-closed if no limit |
| Self-approval laundering | **BLOCKED** | self_approval still on verified actor (test 21) |
| Client forge decide actor | **BLOCKED** | forged_decider |
| Live Authority seed | **BLOCKED** | migrate refuse; live=0 |
| Prod path | **BLOCKED** | db_connect refuse |
| **Material APPROVE via delegation with NULL amount** | **MATERIAL FAIL** | `amount_ctx` only set when `material_amount is not None`. Delegation authority branch calls `evaluate_delegation(..., amount_ctx)` — with `None`, amount rules skipped → allow. Native branch still calls `within_authority` with missing amount → deny. Asymmetric fail-open on delegation path for forged/legacy NULL-amount material rows. |

---

## MATERIAL FINDING DLG-RT-001

**Title:** Material APPROVE via delegation skip Authority when `material_amount` is NULL  
**Where:** `scripts/core/approvals.py` `_decide` — `amount_ctx` construction + delegation authority branch  
**Fix:**
1. If `dec == APPROVED` and `is_material_request(req)` and not `material_amount`: deny immediately (`missing_amount`) before permission/authority success — both native and delegation paths.
2. Always build `amount_ctx` for material requests (include amount key even if None) when calling `evaluate_delegation` for required_permission / authority so missing amount fails closed.
3. Test: forge PENDING SPEND NULL amount + valid spend delegation to Bob → Matt/Bob approve → denied; status stays PENDING.
4. No live Authority seed. No scope widen.

**Commit:** `fix(core): deny material approve via delegation without amount`

---

## Non-blocking notes

- `basis_dlg_id = req_dlg_id or decide_dlg_id if used_delegation else None` precedence is OK.
- Matt may create on behalf of another delegator (governance) — still requires native hold on that delegator.
- Peaches verify (separate): tests 55/0; live auth/dlg/audit = 0/0/47.

## Gate

Delegation Grok red-team: **FAIL** until DLG-RT-001 fixed + re-review PASS.
