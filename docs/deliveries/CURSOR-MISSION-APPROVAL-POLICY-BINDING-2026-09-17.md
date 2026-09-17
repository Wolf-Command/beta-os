# CURSOR MISSION — Approval Policy Binding

**Workspace:** `/Users/wolfterminal/beta-os`
**Branch:** `build/wolf-command-rebuild`
**Commit:** `feat(core): add deterministic approval policy binding`
**Production:** DO NOT TOUCH. Beta only.
**Live Authority Limits:** 0. **Live governance policies:** 0. No real business thresholds.

You are Cursor Local Agent. Peaches does not write application code.

## Read first

- `docs/deliveries/GROK-PLAN-APPROVAL-POLICY-BINDING-2026-09-17.md`
- `docs/canon/APPROVAL-POLICY-BINDING.md`
- `docs/canon/APPROVAL-ENGINE.md`, `DUAL-APPROVAL.md`, `DELEGATION.md`
- `scripts/core/approvals.py`, `authority.py`, `delegation.py`, `rbac.py`, `audit.py`
- `scripts/migrations/015_dual_approval.sql`, migrate patterns
- `scripts/tests/test_dual_approval.py`, `test_approval_engine.py`, `test_delegation.py`

## Implement

### Migration `016_approval_policy_binding.sql` + `migrate_approval_policy_binding.py`

- Backup Beta DB → `catalog/backups/pre-approval-policy-binding-<ts>.sqlite` + SHA-256
- Create `core_governance_policies` per Grok plan
- Add to `core_approval_requests`: `governing_policy_id TEXT NULL`, `governing_policy_version INTEGER NULL`
- Idempotent. Do NOT seed live policies.
- Optionally seed permission codes `governance.policy.read` / `governance.policy.manage` in org_permissions if pattern exists — ACTIVE in temp tests only; no broad live grants

### `scripts/core/governance_policy.py` (new)

- `evaluate_governance_policy(...)` fail-closed matcher + precedence + conflict
- helpers for amount coerce (reject NULL/malformed/negative for amount-governed)
- read helpers; **no public manage/write for normal callers** — if insert helper exists for tests only, guard with explicit test hook / manage permission check that defaults deny
- Audit: policy.evaluated match / no_match / conflict / prohibited (not every noop read)

### Wire `approvals.create_approval_request`

- For material request types (SPEND/EXCEPTION) OR when `require_policy_binding=True`: evaluate policy first
- Server sets `required_decision_count` from policy (approvals_required)
- Store governing_policy_id/version on request
- Client cannot supply lower count than policy; refuse override
- PROHIBITED / NO_MATCH / CONFLICT → raise ApprovalError with reason codes
- Non-material / unbound path: preserve existing behavior for tests that don't use policy (dual/approval regressions). Clear flag: `require_policy_binding` default False for backward compat OR only gate MATERIAL when any ACTIVE policy exists for entity+action — **prefer explicit `require_policy_binding` for create API + material types when evaluating; existing unit tests that create material without policies must still pass** — so: policy gate activates when (a) require_policy_binding=True OR (b) caller asks bind_from_policy=True. Dual/approval tests stay green without live policies.

Actually Matt said fail-closed for material actions requiring governed policy. Design: `evaluate` is always available. `create_approval_request(..., bind_policy: bool = False)`. When `bind_policy=True`, fail-closed evaluate required. New tests use bind_policy=True. Old tests unchanged (bind_policy=False). Document that production material path will set bind_policy=True later — this slice builds machinery.

### Tests `scripts/tests/test_approval_policy_binding.py`

Isolated temp DB. Cover Matt's mandatory list. Keep APR/DLG/Dual regressions green (re-run those three suites). Live counts stay 0/0/47.

### Docs

Update APPROVAL-ENGINE.md pointer. Keep APPROVAL-POLICY-BINDING.md.

### Commit + EXIT

Commit message exact. Print backup path+SHA, migration name. Last line `EXIT:0` or `EXIT:1`.
