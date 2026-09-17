# GROK PLAN — Evidence Requirement Enforcement (Wolf Core)

**Date:** 2026-09-17 WITA  
**Live:** Authority/Policies/SoD/Evidence-requirements all 0. Fixtures only.

## Existing Audit Spine

`011_audit_evidence_spine` = append-only `core_audit_events` + optional `evidence_reference` string.  
**NOT** a canonical evidence object model. This slice **extends** (does not replace) the spine:
- Reuse `audit.record_event` for lifecycle (submitted/verified/rejected/requirement evaluated/denials)
- Add canonical evidence + requirement tables
- Cryptographic immutability remains **NOT BUILT**

## Claimed ≠ Evidenced ≠ Verified

- Claim = free text / client flag (ignored for enforcement)
- Evidence = `core_evidence_records` SUBMITTED
- Verified = verification_status VERIFIED by Person (submitter ≠ verifier when SoD/fixture requires; minimal: deny self-verify when require_independent_verify)

## Tables

### `core_evidence_types` (registry)
evidence_type TEXT PK (e.g. receiving_document, photo) — governed; free client labels do not match

### `core_evidence_records`
evidence_id, entity_id, scope_id NULL, evidence_type, source_type, source_reference NULL,
object_ref NULL (file path/URI string — no blobs), content_hash NULL (optional SHA-256 of test bytes),
submitted_by_person_id, submitted_by_assignment_id NULL, submitted_at, captured_at NULL,
status ACTIVE|INVALIDATED, verification_status SUBMITTED|VERIFIED|REJECTED,
verified_by_person_id NULL, verified_at NULL, verification_reason NULL,
governed_object_type, governed_object_id, classification NULL, metadata_json NULL (size-capped, no secrets),
created_at, updated_at, invalidated_at NULL, invalidate_reason NULL

Hard-delete refused (trigger or service). Invalidate = status INVALIDATED + reason.

### `core_evidence_requirements`
requirement_id + requirement_version, entity_id, scope_id NULL, action_type, request_type NULL,
evidence_type, min_count INTEGER >=1, verification_needed INTEGER 0|1,
effective_from/to, status ACTIVE|INACTIVE, created_at/updated_at

No live seed.

## Evaluator `evaluate_evidence_requirements(...)`

Input: entity, scope?, action_type, request_type?, governed_object_type+id, as_of?

1. Load ACTIVE requirements matching entity+(scope exact|NULL)+action (+request_type if set)
2. Precedence: exact scope > entity-wide; conflicts fail closed
3. For each requirement: count ACTIVE evidence records of that type bound to same entity/scope/object with status ACTIVE and (if verification_needed: verification_status=VERIFIED)
4. Missing/insufficient → DENY `missing_required_evidence` with missing list
5. Wrong entity/scope/object evidence never counted
6. Client `evidence_present` / `evidence_required=false` ignored

## Integration

- When `governance_policy.evidence_required` and bind_policy path: call evaluator before approval create or decide (prefer before create when bind_policy + evidence_required; also gate decide if requirements exist for approval.decide)
- Cleaner: `create_approval_request(..., enforce_evidence=False)` default; `enforce_evidence=True` or bind_policy when policy.evidence_required → evaluate fail-closed
- Approvals/Authority/Delegation cannot override deny
- Work Item complete ≠ evidence
- Optional SoD on verify: SAME_PERSON_FORBIDDEN prior evidence.submit vs evidence.verify via existing sod.py when ACTIVE fixture exists

## Access

Minimal: submit/read within Entity+Permission `evidence.record.submit` / `evidence.record.read` / `evidence.requirement.manage` — no universal read-all. Matt-only manage defaults. No UI.

## Out of scope

DMS UI, OCR, AI verify, Production B2/NAS, real business requirements, crypto chain.
