# GROK PLAN — Exception / Override Governance (Wolf Core)

**Date:** 2026-09-17 WITA  
**Build authorises mechanism only. Live exceptions = 0.**

## Principle

EXCEPTION ≠ COMPLIANCE. Normal control failure is preserved; exception is a separate authorised path. Never rewrite FAIL → PASS.

## Matt gate

Authorise/revoke only when `verified_person_id == PERS-MATT` (canonical Person). Not email. Not ROLE alone. Delegation from Matt does **not** authorise. Termination: authorising an exception does **not** itself require an exception (hard-coded Matt Person gate is the base case — no recursive exception loop).

## NON_EXCEPTIONABLE (hard)

Never overridable via this primitive:
- authentication / verified Person binding
- Entity / tenant isolation
- audit recording (must still record)
- historical attribution immutability (no rewrite)
- controls marked `exceptionable=0` / NON_EXCEPTIONABLE
- Production sacred / wrong-environment mutation
- generic force/override/skip client flags

## Exceptionable (fixture-only for now)

Registry `core_exceptionable_controls`:
- control_type: EVIDENCE_REQUIREMENT | SOD_CONSTRAINT | APPROVAL_REQUIREMENT | AUTHORITY_LIMIT (optional future)
- control_ref: id/code
- exceptionable: 0|1
- No live rows that enable production bypass. Tests seed isolated.

## Tables

### `core_governance_exceptions`
exception_id, entity_id, scope_id NULL, governed_object_type, governed_object_id,
control_type, control_reference, requested_by_person_id, authorised_by_person_id NULL,
reason TEXT, evidence_id NULL (FK canonical evidence),
effective_from, expires_at NULL, status REQUESTED|AUTHORISED|CONSUMED|REJECTED|REVOKED|EXPIRED,
usage_limit INTEGER NOT NULL DEFAULT 1, used_count INTEGER NOT NULL DEFAULT 0,
created_at, authorised_at NULL, rejected_at NULL, revoked_at NULL, consumed_at NULL,
correlation_id, revoke_reason NULL

### Optional link table for multi-evidence later — start with single evidence_id + require present when policy says.

## API (`scripts/core/exceptions.py`)

- `request_exception(...)` — any verified Person with request perm; reason min length ≥ 12 meaningful chars; reject blank/n/a/because/whitespace; status REQUESTED; does NOT bypass
- `authorise_exception(..., verified_person_id)` — Matt only; binds evidence if required; AUTHORISED
- `reject_exception` / `revoke_exception` — Matt only
- `evaluate_exception_for_control(...)` — find AUTHORISED matching entity/scope/object/control/time; client flags ignored
- `consume_exception(exception_id, ...)` — transactional: used_count+1; if used_count>=usage_limit → CONSUMED; concurrent safe (UPDATE WHERE used_count < usage_limit AND status=AUTHORISED)

## Integration (minimal prove)

When evidence/SoD/approval gate would DENY:
1. Optionally call `evaluate_exception_for_control` for that exact control_type+ref+object
2. If valid exception → return DENIED_NORMAL + EXCEPTION_AUTHORISED path result (e.g. `result=ALLOWED_UNDER_EXCEPTION`, `normal_result=DENIED`, preserve reason codes) then consume
3. Never mutate the normal evaluator to PASS

Wire at least:
- evidence gate: exception for EVIDENCE_REQUIREMENT + specific requirement_id
- SoD decide path: exception for SOD_CONSTRAINT + specific constraint_id  
Do NOT allow one exception to cover both.

Approval count downgrade: out of scope for broad mutate; optional narrow prove: exception for APPROVAL_REQUIREMENT bound to request may allow proceed under exception without rewriting required_decision_count history — prefer document + one test that approvals still record original count + exception ref.

## Reason validation

Reject if stripped length < 12 or lowercased in {n/a, na, because, test, asdf, override, force, skip}.

## Out of scope

UI, real policies, break-glass infra, AI authoriser, dual-approval for exceptions, delegation of authorise.
