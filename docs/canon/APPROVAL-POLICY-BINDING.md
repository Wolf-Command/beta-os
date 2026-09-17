# Approval Policy Binding — Canon (Wolf Core)

**LOCKED 2026-09-17.** Deterministic bridge: ACTION → REQUIRED CONTROL.  
**Status:** BUILT+TESTED on Beta (`build/wolf-command-rebuild`) — migration `016_approval_policy_binding`.

## Constitution

NO MATCHING POLICY ≠ ALLOW for material governed path. FAIL CLOSED.

Policy ≠ Authority Limits. Policy says whether Authority evaluation is required; Limits say how much a Person may exercise.

Policy ≠ Approval Decision. Policy sets required_decision_count; Approvals record Person decisions.

Delegation never rewrites policy.

PROHIBITED cannot be bypassed by Permission.

Historical requests keep governing_policy_id + version.

## API

`evaluate_governance_policy(...)` always available.  
`create_approval_request(..., bind_policy=False)` — default unbound (APR/DLG/Dual regressions).  
`bind_policy=True` — fail-closed evaluate; server sets `required_decision_count` + `governing_policy_*`; client lower count refused. Production material path will set `bind_policy=True` later.

## Live

Live Authority Limits = 0. Live governance policies = 0. Not configured. No `governance.policy.manage` live grants.
