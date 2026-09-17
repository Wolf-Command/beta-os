# GROK PLAN — Dual Approval (Wolf Core)

**Date:** 2026-09-17 WITA  
**Slice:** Extend existing Approval Engine for deterministic multi-decision control (prove 1 and 2).  
**Live Authority Limits:** remain 0. No real dual-approval business policy. Isolated fixtures only.

## Minimal design

1. Add `required_decision_count INTEGER NOT NULL DEFAULT 1` on `core_approval_requests` (enforce >= 1 in service). Schema may allow N>2 later; this slice proves 1 and 2 only.
2. Set at create time only. Reject client attempts to lower after insert. Include in `snapshot_hash` with entity/scope/permission/amount/currency/source/type.
3. **No PARTIALLY_APPROVED status** — stay `PENDING` until `valid_approve_count >= required_decision_count`, then `APPROVED`. Optional read helpers: `valid_approve_count`, `approvals_remaining`.
4. Any valid `REJECTED` decision → request `REJECTED` immediately. No further decisions.
5. Independence = distinct `decided_by_person_id`. Same Person via second AuthIdentity = deny second approve. Delegation: decision actor = delegate Person only (never count delegator+delegate as two).
6. Each APPROVED decision must independently pass RBAC/Scope/Authority (and Delegation when used). Keep APR-RT-001 / DLG-RT-001 fail-closed amount rules.
7. Concurrency: single SQLite transaction; re-check under write; one Person cannot insert two APPROVED rows for same request; replay denied.
8. Append-only decisions. Do not overwrite Approval 1.
9. Work Item completion still ≠ approval decision.
10. Audit: dual request created, approval_1, duplicate_person denied, approval_2, became APPROVED, reject, delegation used, authority denied, concurrency/replay.

## Out of scope

UI, live policy/thresholds, N-person committees, voting, SoD engine, payment execution, AI approver, Production, Authority seed.
