# DELEGATION — honesty table (Beta transitional)

**Status:** BUILT+TESTED on Beta (`build/wolf-command-rebuild`) — 2026-09-17  
**Lock:** Live Authority Limits remain **0**. Live `core_delegations` seed = **0**. Identity never delegates.

| Capability | Status |
|------------|--------|
| Delegation model + evaluator | BUILT+TESTED |
| Approval integration (`authority_basis_*=DELEGATION`) | BUILT+TESTED |
| Re-delegation | DENIED (this slice; `allow_redelegation=0`) |
| Delegation UI | NOT BUILT |
| Dual approval / SoD | Dual BUILT (Approval Engine); SoD NOT BUILT |
| Live Authority policy | NOT CONFIGURED |

## Constitutional

IDENTITY NEVER DELEGATES. Actor = authenticated Person. Authority basis may be DELEGATION from delegator. Never impersonate.

Delegate effective capability ≤ min(delegator capability, explicit grant). Fail-closed if delegator later loses capability. No re-delegation. Self-approval still binds the actual authenticated decider.

## Path

```
Person (delegate, verified) → valid core_delegations row
  → delegator still holds native Permission + Scope + Authority
  → Approval Decision: decided_by=delegate, authority_basis_type=DELEGATION
```

## Tables / APIs

- `core_delegations` — SCHEDULED|ACTIVE|EXPIRED|REVOKED (lazy activate/expire; revoke sticky)
- `core_approval_decisions.authority_basis_type` / `authority_basis_delegation_id`

| method | path | perm |
|--------|------|------|
| POST | `/api/core/delegations` | delegation.create |
| GET | `/api/core/delegations` | delegation.read |
| GET | `/api/core/delegations/{id}` | delegation.read |
| POST | `/api/core/delegations/{id}/revoke` | delegation.revoke |

Honesty flags: `redelegation: DENIED`, `impersonation: BLOCKED`.

## Build record

- **Date:** 2026-09-17 (WITA)
- **Commit message:** `feat(core): add deterministic delegation`
- **Backup:** `catalog/backups/pre-delegation-20260917-113925.sqlite`
- **Backup SHA256:** `6d64db792877f6a14aa4a30935a6ee5fdc433d270a7c7353113267e4eb450c0a` (`state/delegation-backup-20260917-113925.sha256`)
- **Live `org_authority_limits`:** 0 (before/after)
- **Live `core_delegations`:** 0 (after migrate)
- **Tests:** `python3 scripts/tests/test_delegation.py` → pass=55 fail=0 (temp DB only)
