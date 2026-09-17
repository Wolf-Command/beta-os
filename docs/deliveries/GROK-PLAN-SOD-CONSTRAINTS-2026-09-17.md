# GROK PLAN — Segregation of Duties Constraints (Wolf Core)

**Date:** 2026-09-17 WITA  
**Live:** Authority Limits 0 · Governance Policies 0 · SoD Constraints 0. Fixtures only.

## Separate from Dual Approval / Policy Binding

- Dual = how many independent APPROVED decisions required
- Policy Binding = ACTION → required controls (count, authority, prohibited…)
- SoD = same Person forbidden for incompatible participation pairs even if otherwise authorised

## Minimal model `core_sod_constraints`

- `constraint_id` TEXT + `constraint_version` INTEGER (unique pair; append versions, do not rewrite history)
- `entity_id` TEXT NOT NULL
- `scope_id` TEXT NULL (NULL = entity-wide)
- `process_family` TEXT NOT NULL (e.g. APPROVAL, PAYMENT — free string namespace for fixtures)
- `prior_action` TEXT NOT NULL (e.g. approval.request, payment.prepare)
- `proposed_action` TEXT NOT NULL (e.g. approval.decide, payment.approve)
- `relationship` TEXT NOT NULL — this slice: `SAME_PERSON_FORBIDDEN` only
- `effective_from`, `effective_to` NULL, `status` ACTIVE|INACTIVE
- `created_at`, `updated_at`

No opaque JSON rule language.

Optional participation ledger `core_sod_participation` (or derive from existing tables):
- For APPROVAL family: derive prior from `core_approval_requests.requested_by_person_id` and `core_approval_decisions.decided_by_person_id` — trustworthy system evidence
- For generic fixtures: allow test-only insert of participation rows with person_id + action + subject_id + entity_id; production path prefers canonical tables
- Client-supplied `requester_is_different` / forged participation IGNORED

## Evaluator `evaluate_sod(...)`

Input: verified_person_id, entity_id, scope_id?, process_family, proposed_action, subject_id (e.g. approval_request_id), as_of?

1. Load ACTIVE constraints matching entity + (scope exact OR NULL) + process_family + proposed_action, effective window
2. Precedence: exact scope > entity-wide; equal specificity conflict → FAIL CLOSED `sod_constraint_conflict`
3. For each matching SAME_PERSON_FORBIDDEN: resolve prior participation persons for `prior_action` on subject from system evidence
4. If evidence required but unresolvable → FAIL CLOSED `sod_evidence_unavailable`
5. If verified_person_id ∈ prior participants → DENY `sod_same_person_conflict` with constraint_id/version + conflicting person + actions
6. Else ALLOW with reason `sod_ok` / no applicable constraint `sod_not_applicable` (not the same as missing evidence)

Person-based: AuthIdentity / Assignment / Role / Delegation basis do NOT multiply identity. Decision actor = verified Person. Delegation cannot launder: if Person A is prior participant, A still DENY even with B's delegation.

## Integration

- `approvals._decide` APPROVED path: after self-approval check (keep), call SoD with proposed_action=`approval.decide`, prior=`approval.request`, subject=request_id. When `enforce_sod=True` OR any ACTIVE constraint matches — fail closed. Default: call evaluate; if no ACTIVE constraints for entity/family → sod_not_applicable (legacy tests green). When ACTIVE fixture constraints exist for that entity+action, enforce.
- Dual: each approver independently SoD-checked
- Authority / Permission / Policy Binding cannot override SoD deny
- Store on decision optional `sod_constraint_id`/`sod_constraint_version` when evaluated material (or audit metadata only — prefer audit + optional columns on decisions if clean)

## Permissions

`sod.constraint.read` / `sod.constraint.manage` — no live manage grants. Test insert hook only.

## Out of scope

UI, real SoD matrix, exception override, AI, Production, live seeds.
