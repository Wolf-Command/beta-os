# DELEGATION — honesty table (Beta transitional)

**Status:** PLANNED (Grok mission 2026-09-17) — not built until Cursor lands  
**Lock:** Live Authority Limits remain **0**. Identity never delegates.

| Capability | Status |
|------------|--------|
| Delegation model + evaluator | PLANNED |
| Approval integration | PLANNED |
| Re-delegation | DENIED (this slice) |
| Delegation UI | NOT BUILT |
| Dual approval / SoD | NOT BUILT |
| Live Authority policy | NOT CONFIGURED |

## Constitutional

IDENTITY NEVER DELEGATES. Actor = authenticated Person. Authority basis may be DELEGATION from delegator. Never impersonate.

Delegate effective capability ≤ min(delegator capability, explicit grant). Fail-closed if delegator later loses capability.
