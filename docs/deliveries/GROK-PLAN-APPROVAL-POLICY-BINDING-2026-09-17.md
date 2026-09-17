# GROK PLAN — Approval Policy Binding (Wolf Core)

**Date:** 2026-09-17 WITA  
**Live Authority Limits:** 0. **Live governance policies:** 0. Test fixtures only.

## Smallest model

Table `core_governance_policies` (append-oriented versions; do not mutate historical rows in place for meaning):

- `policy_id` TEXT PK (stable identity across versions) + `policy_version` INTEGER NOT NULL
- Unique `(policy_id, policy_version)`
- `entity_id` TEXT NOT NULL
- `scope_id` TEXT NULL (NULL = entity-wide)
- `action_type` TEXT NOT NULL (e.g. SPEND_APPROVE, EXCEPTION, GENERAL_MATERIAL)
- `request_type` TEXT NULL (align with approval request_type when set)
- `required_permission_code` TEXT NULL
- `authority_required` INTEGER NOT NULL DEFAULT 0
- `approval_required` INTEGER NOT NULL DEFAULT 0
- `required_decision_count` INTEGER NOT NULL DEFAULT 0  (0 = no approval seats; when approval_required=1 must be >=1)
- `evidence_required` INTEGER NOT NULL DEFAULT 0
- `prohibited` INTEGER NOT NULL DEFAULT 0
- `amount_min` TEXT NULL, `amount_max` TEXT NULL (inclusive decimal strings; NULL/NULL = no amount band)
- `currency` TEXT NULL (required if amount band set)
- `effective_from` TEXT NOT NULL, `effective_to` TEXT NULL
- `status` TEXT NOT NULL (ACTIVE|INACTIVE)
- `created_at`, `updated_at`, `created_by_person_id` NULL

No opaque JSON rule language.

## Evaluator `evaluate_governance_policy(...)`

Input: entity_id, scope_id?, action_type, request_type?, amount?, currency?, as_of?

Matching ACTIVE policies where effective_from <= as_of and (effective_to is NULL or as_of < effective_to), entity exact, scope: exact scope_id OR (policy.scope_id IS NULL for entity-wide).

**Precedence (deterministic):**
1. Exact scope match beats entity-wide (NULL scope)
2. Then more specific amount band (both min/max set) beats open-ended band beats no band
3. Then higher policy_version for same policy_id if somehow both active (prefer: only one ACTIVE version per policy_id enforced)
4. If two distinct ACTIVE policies remain equally specific → **FAIL CLOSED** `policy_conflict`

Amount band: inclusive [min, max]. Boundary exact. Overlaps among candidates after precedence → conflict. Gaps: no match → `no_matching_policy` for material governed path.

**NULL amount** when any candidate or action is amount-governed material → DENY `missing_amount` (preserve APR-RT-001 / DLG-RT-001 lessons).

**PROHIBITED** match → DENY `action_prohibited` (Permission cannot override).

**No match** on material governed evaluate → DENY `no_matching_policy` (NOT allow).

Return explainable dict: matched_policy_id/version, permission_required, authority_required, approvals_required (required_decision_count), evidence_required, result (REQUIREMENTS|PROHIBITED|NO_MATCH|CONFLICT), reason_code.

## Integration

- `create_approval_request` for material path: when `bind_policy=True` or material types under policy gate — server calls evaluate; sets `required_decision_count` from policy; stores `governing_policy_id` + `governing_policy_version` on request; **ignores/refuses client lower count**.
- Client-supplied required_decision_count below policy → deny or clamp-up only via server (prefer deny override attempt).
- Delegation does not change policy outcome.
- Authority still independent after policy says authority_required.

## Permissions

Seed codes only on temp/test: `governance.policy.read`, `governance.policy.manage`. Live: no manage grant. Manage API Matt-only / denied for normal users. No live policy rows.

## Out of scope

UI, real thresholds, exception override, SoD, AI policy, Production, Authority seed.
