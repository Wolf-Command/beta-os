# CURSOR MISSION — Delegation DLG-RT-001 (bounded fix)

**Date:** 2026-09-17 WITA  
**Start HEAD:** `8c4285a` (CLEAN)  
**Sole defect:** Grok DLG-RT-001 — material APPROVE via delegation with NULL `material_amount` skips Authority.

## Required ONLY

1. `scripts/core/approvals.py` `_decide`:
   - After load PENDING request, if `decision==APPROVED` and `is_material_request(req)` and missing/blank `material_amount`: raise `ApprovalError(code=missing_amount, http=400)` fail-closed (before treating as allowed).
   - When calling `evaluate_delegation` for required_permission / material authority on material requests, pass an `amount_ctx` that always includes the `amount` key (value may be None) so evaluator hits malformed/missing amount path.
2. `scripts/tests/test_delegation.py`: forge NULL-amount SPEND + valid delegation → approve denied; stays PENDING.
3. Keep isolation; live auth/dlg/audit unchanged.
4. No UI/dual/SoD/redelegation/Authority seed/prod.

## Commit

`fix(core): deny material approve via delegation without amount`

End CLEAN. No remote.
