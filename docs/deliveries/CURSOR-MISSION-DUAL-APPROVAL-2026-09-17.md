# CURSOR MISSION — Dual Approval

**Workspace:** `/Users/wolfterminal/beta-os`
**Branch:** `build/wolf-command-rebuild`
**Commit message:** `feat(core): add dual approval control`
**Production:** DO NOT TOUCH. Beta only.
**Live Authority Limits:** stay 0. Do not seed dual business policy.

You are Cursor Local Agent. Implement Dual Approval by extending the existing Approval Engine. Peaches does not write application code.

## Read first

- `docs/deliveries/GROK-PLAN-DUAL-APPROVAL-2026-09-17.md`
- `docs/canon/DUAL-APPROVAL.md`
- `docs/canon/APPROVAL-ENGINE.md`
- `docs/canon/DELEGATION.md` (if present)
- `scripts/core/approvals.py`
- `scripts/core/delegation.py`
- `scripts/migrations/013_approval_engine.sql`
- `scripts/migrations/014_delegation.sql`
- `scripts/migrations/migrate_approval_engine.py`
- `scripts/migrations/migrate_delegation.py`
- `scripts/tests/test_approval_engine.py`
- `scripts/tests/test_delegation.py`

## Implement

### Migration `015_dual_approval.sql` + `scripts/migrations/migrate_dual_approval.py`

- Backup Beta DB before apply (`catalog/backups/pre-dual-approval-<ts>.sqlite`) and print SHA-256
- Add `required_decision_count INTEGER NOT NULL DEFAULT 1` to `core_approval_requests`
- Idempotent migrate; existing rows → 1
- Enforce `required_decision_count >= 1` in service layer

### `scripts/core/approvals.py`

1. `create_approval_request(..., required_decision_count: int = 1)`
   - Validate integer >= 1 (tests use 1 or 2)
   - Persist column; include in `compute_snapshot_hash`
   - Audit metadata includes required_decision_count
   - No update API that can change security fields after create

2. `_decide` / approve / reject
   - On APPROVED:
     - Deny if request not PENDING
     - Keep self-approval deny
     - Deny if this Person already has APPROVED decision on this request (`duplicate_person_approval`)
     - Independently evaluate RBAC/Scope/Permission/Authority/Delegation as today
     - Insert append-only decision
     - Count distinct `decided_by_person_id` with decision=APPROVED
     - If count < required_decision_count: leave status PENDING; audit partial decision recorded (NOT full `approval.granted` as terminal)
     - If count >= required: set APPROVED + decided_at; audit granted
   - On REJECTED: insert decision; set REJECTED immediately; further decisions denied
   - Replace old "first APPROVED wins → status APPROVED" for multi-count; keep concurrency-safe transaction
   - Concurrent same Person: only one APPROVED row
   - Concurrent distinct Persons: both rows; status flips when threshold met

3. Immutability: refuse mutation of required_decision_count, amount, currency, entity, permission, source, type after create (snapshot)

4. Honesty: REQUESTED ≠ APPROVED ≠ EXECUTED; note N decisions when count>1

5. Work items: do NOT complete WI on partial or full approval

6. Serve routes: accept `required_decision_count` on create only if API exists; never on decide

### Tests `scripts/tests/test_dual_approval.py` (+ keep approval/delegation regressions green)

Isolated test DB only. Cover Matt mandatory list including one-approval compat, two-person flow, same-person / alternate AuthIdentity block, requester self-approval, RBAC/scope/permission/assignment denials, Authority cases + APR-RT-001 + DLG-RT-001, delegation once / not double-count, expired/revoked/re-delegation, REJECT terminates, immutability after first decision, concurrency + replay, both decisions preserved, no execute source, WI≠approval, audit, live audit/limits isolation, migration idempotent.

### Docs

Update `docs/canon/APPROVAL-ENGINE.md` briefly pointing to Dual Approval. Keep `docs/canon/DUAL-APPROVAL.md`.

### Commit

`feat(core): add dual approval control`
No remote push. No Production.

### Done

Run tests green. Print backup path+SHA and migration name. Last log lines must be `EXIT:0` (success) or `EXIT:1` (failure).
