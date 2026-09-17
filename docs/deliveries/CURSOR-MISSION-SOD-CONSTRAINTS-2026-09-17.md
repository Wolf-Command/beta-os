# CURSOR MISSION — Segregation of Duties Constraints

**Workspace:** `/Users/wolfterminal/beta-os`
**Branch:** `build/wolf-command-rebuild`
**Commit:** `feat(core): add segregation of duties constraints`
**Production:** DO NOT TOUCH.
**Live:** Authority 0 · Governance policies 0 · SoD constraints 0.

You are Cursor Local Agent. Peaches does not write application code.

## Read first

- `docs/deliveries/GROK-PLAN-SOD-CONSTRAINTS-2026-09-17.md`
- `docs/canon/SEGREGATION-OF-DUTIES.md`
- Approval / Dual / Policy Binding / Delegation canons + `scripts/core/approvals.py`, `governance_policy.py`, `delegation.py`
- Migrations 013–016 patterns
- Tests: test_approval_engine, test_delegation, test_dual_approval, test_approval_policy_binding

## Implement

### Migration `017_sod_constraints.sql` + `migrate_sod_constraints.py`

- Backup `catalog/backups/pre-sod-constraints-<ts>.sqlite` + SHA-256
- `core_sod_constraints` per Grok plan
- Optional `core_sod_participation` for generic fixture evidence (person_id, action, subject_id, entity_id, scope_id, recorded_at, source_type SYSTEM|TEST)
- Idempotent. NO live seed rows.
- Permission codes `sod.constraint.read` / `sod.constraint.manage` if pattern exists — no live manage grants

### `scripts/core/sod.py`

- `evaluate_sod(...)` fail-closed as planned
- Resolve APPROVAL participation from request requester + prior decisions (Person ids only)
- Ignore client independence claims
- Audit: sod.evaluated ok / conflict / evidence_unavailable / constraint_conflict

### Wire `approvals._decide`

- On APPROVED (and optionally REJECTED if constrained — prefer APPROVED only for this slice): evaluate SoD for `approval.decide` vs prior `approval.request`
- If ACTIVE constraints apply and conflict → deny `sod_same_person_conflict` before inserting decision
- Keep existing self_approval_denied (SoD generalises; both may fire)
- Dual: each distinct Person checked independently
- Do not break unbound tests when zero ACTIVE SoD rows

### Tests `scripts/tests/test_sod_constraints.py`

Cover Matt mandatory list. Re-run APR + DLG + Dual + Policy Binding suites — all green. Live counts stay 0.

### Docs + Commit

Update APPROVAL-ENGINE.md pointer. Commit message exact. Print backup+SHA. Last line `EXIT:0` or `EXIT:1`.
