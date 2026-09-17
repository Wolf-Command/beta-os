# CURSOR MISSION — Wolf Core Approval Engine (Beta OS only)

**Date:** 2026-09-17 (WITA)  
**Grok planned:** YES against HEAD `7114b95`  
**Peaches:** Governor only — no application coding.  
**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio  
**Repo:** `/Users/wolfterminal/beta-os/` · Branch `build/wolf-command-rebuild` (start CLEAN)  
**Commit:** `feat(core): add deterministic approval engine`  
**No remote. No Production. No live Authority Limits seed (must remain 0). No dual approval / SoD / delegation / UI / LLM.**

---

## Relationship to existing Core

| Primitive | Answers | This slice uses |
|-----------|---------|-----------------|
| RBAC | WHAT permission | required_permission_code on request |
| Scope | WHERE | owning_entity_id + target context |
| Authority | HOW MUCH material allowance | `within_authority` on decide — **does not create limits** |
| Work Item | something must be done | optional linked `APPROVAL_REQUIRED` WI — completing WI ≠ approving |
| Audit | evidence of decisions | append events on request/attempt/grant/reject/cancel/expire/deny |

**REQUESTED ≠ APPROVED ≠ EXECUTED ≠ OUTCOME** — approval never marks source action executed.

---

## Preflight + backup

```bash
cd /Users/wolfterminal/beta-os
git status -sb   # CLEAN
TS=$(TZ=Asia/Makassar date +%Y%m%d-%H%M%S)
cp -p catalog/content_library.sqlite "catalog/backups/pre-approval-engine-${TS}.sqlite"
shasum -a 256 "catalog/backups/pre-approval-engine-${TS}.sqlite" | tee "state/approval-engine-backup-${TS}.sha256"
# Prove live authority limits still 0 before and after migrate
```

---

## Schema

### `core_approval_requests`

Structured columns (not opaque JSON for security meaning):

- `approval_request_id` TEXT PK  
- `request_type` TEXT NOT NULL — closed set starter: `GENERAL`, `SPEND`, `EXCEPTION`, `ACCESS`, `HR`, `CONTRACT`  
- `title` TEXT NOT NULL  
- `description` TEXT NULL  
- `owning_entity_id` TEXT NOT NULL  
- `brand_id` / `location_id` / `department_id` TEXT NULL (scope context)  
- `requested_by_person_id` TEXT NOT NULL  
- `requested_by_assignment_id` TEXT NULL  
- `required_permission_code` TEXT NOT NULL — store code (resolve id at decide); also `required_permission_id` TEXT NOT NULL  
- `material_amount` TEXT NULL — store as text decimal string for stability; parse via authority helpers  
- `currency` TEXT NULL  
- `source_type` TEXT NOT NULL — `HUMAN`, `SYSTEM`, `WORK_ITEM`, `EXTERNAL`  
- `source_id` TEXT NULL  
- `evidence_reference` TEXT NULL — hook only  
- `status` TEXT NOT NULL — `PENDING|APPROVED|REJECTED|CANCELLED|EXPIRED`  
- `requested_at` / `decided_at` / `expires_at` / `created_at` / `updated_at` TEXT  
- `correlation_id` TEXT NOT NULL  
- `linked_work_item_id` TEXT NULL  
- `prior_request_id` TEXT NULL — resubmission link  
- `snapshot_hash` TEXT NULL — hash of immutable material fields at create (see below)

**Immutable after create (while PENDING or any terminal):** entity, brand/location/department, required_permission_*, material_amount, currency, source_type, source_id.  
Any attempt to change → 400; client must cancel + create new request (`prior_request_id` set).

### `core_approval_decisions` (append-only)

- `approval_decision_id` TEXT PK  
- `approval_request_id` TEXT NOT NULL  
- `decision` TEXT NOT NULL — `APPROVED|REJECTED` (attempts that fail auth/authority may still log audit without decision row, or store `decision=DENIED_ATTEMPT` — prefer **audit only** for failed attempts; decision rows only for successful state-changing approve/reject)  
- `decided_by_person_id` TEXT NOT NULL  
- `decided_by_assignment_id` TEXT NULL  
- `identity_assurance` TEXT NULL  
- `reason` TEXT NULL  
- `decided_at` TEXT NOT NULL  
- `authority_allowed` INTEGER NOT NULL  
- `authority_reason` TEXT NULL  
- `authority_matched_limit_id` TEXT NULL  
- `correlation_id` TEXT NOT NULL  
- `created_at` TEXT NOT NULL  

**No UPDATE/DELETE** on decisions (service raise + optional SQL triggers).  
Multiple decision rows allowed structurally (future dual) — this slice: **first successful APPROVED/REJECTED wins**; further decide → 409. Dual orchestration NOT BUILT.

Indexes: request status, entity, requester, decided_by, correlation.

---

## State machine

`PENDING` → `APPROVED` | `REJECTED` | `CANCELLED` | `EXPIRED`  
Terminal: APPROVED, REJECTED, CANCELLED, EXPIRED.  
On decide: if `expires_at` set and now ≥ expires_at → set EXPIRED, deny decide.  
Lazy expire on get/list/decide is OK.

---

## Self-approval

Module constant / env `BETA_APPROVAL_DENY_SELF_APPROVAL=1` default **on**.  
When on: if `decided_by_person_id == requested_by_person_id` on material requests (any request with amount set OR request_type in SPEND/EXCEPTION) → DENY + audit `self_approval_denied`.  
Design so later policy can flip without schema rewrite (read flag; no hard-coded forever).  
This slice tests: self-approval DENIED.

---

## Decide path (deterministic)

1. Resolve verified identity (Cloudflare fail-closed).  
2. Load request; refuse if not PENDING (after expire check).  
3. Self-approval check.  
4. RBAC: approver must have `approval.decide` AND `required_permission_code` in target context (entity/scope).  
5. Active Assignment required.  
6. `within_authority(approver, required_permission_code, target, {amount, currency})` when material_amount present; if amount present and live/fixture has no matching limit → deny (existing Authority behaviour).  
7. Insert decision row; set request status; audit.  
8. **Do not** execute source action. **Do not** mark Work Item complete/verified.

Reject path: same identity/RBAC; Authority not required for reject; insert REJECTED decision.

Cancel: requester with `approval.cancel` on own PENDING, or Matt `approval.cancel`; no decision row required (or SYSTEM decision) — audit `approval.cancelled`.

---

## Permissions (Matt-only seed; live)

`approval.read` | `approval.request` | `approval.decide` | `approval.cancel` → ROLE-MATT only.

Tests may grant fixtures on **temp DB only**.

---

## Work Item integration (minimal)

On create: optionally create linked Work Item:

- `work_type=APPROVAL_REQUIRED`  
- title/description from request  
- `owning_entity_id` same  
- `source_type=SYSTEM`, `source_id=approval_request_id`  
- `owner_person_id` = optional `review_owner_person_id` if provided (else null)  
- store `linked_work_item_id`

**HARD RULE:** `claim_complete` / `verify` / any WI transition must **not** call approve/reject. Test this.

---

## API (`/api/core/approvals`)

| method | path | perm |
|--------|------|------|
| POST | `/api/core/approvals` | approval.request |
| GET | `/api/core/approvals` | approval.read |
| GET | `/api/core/approvals/{id}` | approval.read |
| POST | `/api/core/approvals/{id}/approve` | approval.decide |
| POST | `/api/core/approvals/{id}/reject` | approval.decide |
| POST | `/api/core/approvals/{id}/cancel` | approval.cancel |

Requester from verified identity only — ignore client `requested_by_*` / `decided_by_*`.

---

## Audit actions

`approval.requested`, `approval.decide_attempt`, `approval.granted`, `approval.rejected`, `approval.cancelled`, `approval.expired`, `approval.authority_denied`, `approval.self_denied`  
(Use consistent naming; document in canon.)

---

## Test isolation (mandatory)

- All tests on **temp DB copy**.  
- Seed **fixture** Authority Limits + activate `PERM-TEST-SPEND` / `test.spend.approve` **only on temp** (same pattern as `test_authority_limits.py`).  
- **Live** `org_authority_limits` count must remain **0** before/after.  
- Live `core_audit_events` count must **not increase** from test runs.  
- Live approval request count = **0**.  
- `WOLF_TEST_MODE=1` refuse writes to live catalog (extend audit/work patterns).

---

## Migration

`013_approval_engine.sql` + `migrate_approval_engine.py` — idempotent; seed perms; **0** live requests/decisions; **0** live authority limits.

---

## Docs

`docs/canon/APPROVAL-ENGINE.md` honesty table.

---

## Explicit DO NOT

Live Authority policy/thresholds, dual approval orchestration, SoD engine, delegation, escalation, reminders, domain purchase/payment/leave/hire workflows, approval UI, AI approver, Peaches app code, deleting the 47 audit rows.

---

## Build record

_(Cursor appends)_
