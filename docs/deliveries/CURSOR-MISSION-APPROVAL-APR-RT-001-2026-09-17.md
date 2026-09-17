# CURSOR MISSION — Approval Engine APR-RT-001 (bounded fix)

**Date:** 2026-09-17 WITA  
**Factory:** Peaches govern → Grok reviewed `dd039b2` FAIL → Cursor fix → tests → Grok re-review → Peaches verify  
**Branch:** `build/wolf-command-rebuild`  
**Workspace:** `/Users/wolfterminal/beta-os`  
**Start HEAD:** `dd039b2` (or current if already there; tree must be CLEAN before start)

## Sole defect

Grok APR-RT-001: SPEND/EXCEPTION without `material_amount` skips `within_authority` on APPROVE.

## Required changes ONLY

1. `scripts/core/approvals.py` `create_approval_request`:
   - If `request_type` in `MATERIAL_TYPES` (`SPEND`, `EXCEPTION`): require non-empty `material_amount` and `currency` (reuse existing coerce; reject missing/invalid).
2. `scripts/core/approvals.py` `_decide`:
   - On `APPROVED`, if `is_material_request(req)`: **always** call `within_authority` (do not gate only on truthy `material_amount`). Missing/empty amount must deny fail-closed.
3. `scripts/tests/test_approval_engine.py`:
   - Assert create SPEND without amount fails.
   - Assert create EXCEPTION without amount fails.
   - Optionally: forge PENDING SPEND with NULL amount in temp DB → approve → authority denied / not succeeded.
   - Keep isolation: temp DB; live `org_authority_limits` stays 0; live audit count must not rise.
4. Update `docs/canon/APPROVAL-ENGINE.md` one-line honesty if needed.
5. Append build note to Grok review file or canon Build record.

## Do NOT

- Seed live Authority Limits
- Dual / SoD / Delegation / UI / LLM
- Touch Production / wolf-system
- Remote push
- Unrelated refactors

## Commit

`fix(core): require amount on material approval types`

One commit. End CLEAN. No remote.

## Report back

pass/fail counts, live auth/approvals/audit counts, commit hash.
