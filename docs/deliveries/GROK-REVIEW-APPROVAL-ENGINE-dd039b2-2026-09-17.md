# GROK ENGINEERING REVIEW + RED TEAM — Approval Engine

**Role:** GROK (engineering review / red-team) — distinct from Peaches evidence verify  
**Commit reviewed:** `dd039b2f123e890478e3abdceb437b5ab6a0b836`  
**Subject:** `feat(core): add deterministic approval engine`  
**Date:** 2026-09-17 WITA  
**Method:** Read actual diff + full `scripts/core/approvals.py`, `013_approval_engine.sql`, `migrate_approval_engine.py`, `serve_beta.py` approval handlers, `test_approval_engine.py`. Not a Peaches test-count claim.

**Verdict:** **FAIL — 1 MATERIAL defect** (bounded fix required before Delegation)

---

## Diff scope reviewed

| Path | Notes |
|------|-------|
| `scripts/core/approvals.py` | +1125 create/decide/cancel/list |
| `scripts/migrations/013_approval_engine.sql` | requests + append-only decisions |
| `scripts/migrations/migrate_approval_engine.py` | Matt-only `approval.*`, auth_limits must stay 0 |
| `scripts/serve_beta.py` | HTTP gates; client actor spoof nulled |
| `scripts/tests/test_approval_engine.py` | 56 isolated tests |
| `scripts/core/audit.py` | minor |

---

## Attack checklist (actual code)

| Attack | Result | Evidence |
|--------|--------|----------|
| Client forges requester | **BLOCKED** | HTTP sets `requested_by_person_id=None`; create refuses mismatch (`forged_requester`) |
| Client forges decider | **BLOCKED** | HTTP sets `decided_by_person_id=None`; decide refuses mismatch (`forged_decider`) |
| Self-approval on material | **BLOCKED** | `deny_self_approval_enabled` + `is_material_request` → 403 `self_approval_denied` + audit |
| WI complete/verify ≈ approve | **BLOCKED** | decide never completes WI; `executed_source=False`; tests assert no decision after WI verify |
| Approve executes source | **BLOCKED** | Hard rule comment + return flags; no source executor call |
| RBAC `approval.decide` missing | **BLOCKED** | evaluate before decide |
| Required permission missing | **BLOCKED** | second evaluate on `required_permission_code` |
| Inactive assignment | **BLOCKED** | assignment must be ACTIVE + `end_at IS NULL` |
| Amount above Authority | **BLOCKED** | `within_authority` on APPROVE when `material_amount` set |
| Live Authority = 0 + amount | **BLOCKED** | `within_authority` → `higher_approval_required` / no matching limit |
| Expired request decide | **BLOCKED** | lazy expire + 409 |
| Second decide | **BLOCKED** | decision count + `UPDATE … WHERE status=PENDING` → 409 |
| Decision UPDATE/DELETE | **BLOCKED** | SQL triggers + Python `NotImplementedError` |
| Cross-entity list leak | **BLOCKED** | list filtered by `visible_entity_ids_for_person` |
| GET one out of scope | **BLOCKED** | `person_can_see_entity` |
| Non-Matt `approval.*` grants | **BLOCKED** | migrate deletes other role grants; asserts other_grants=0 |
| Live auth seed | **BLOCKED** | migrate refuses if auth_limits ≠ 0 |
| Prod / wolf-system path | **BLOCKED** | `db_connect` refuses |
| Test write to live catalog | **BLOCKED** | `assert_catalog_writable` + `WOLF_TEST_MODE` |
| Dual / SoD / UI / LLM | **ABSENT** | honesty flags NOT_BUILT |
| Concurrent double-decide | **ACCEPTABLE (Beta)** | SQLite writer serialize + PENDING guard |
| Request row SQL mutate amount | **AMBER** | no UPDATE API; no DB trigger on requests (decisions protected). App path OK. |
| **SPEND/EXCEPTION with empty amount skips Authority** | **MATERIAL FAIL** | `is_material_request` true for SPEND/EXCEPTION; decide only calls `within_authority` when `req.get("material_amount")`. Create does not require amount for SPEND. Approver can APPROVE spend-typed request with no amount and **no Authority check**. Self-approval still denies (type-based). Authority gate bypassed for non-self decider. |

---

## MATERIAL FINDING (must fix)

**ID:** APR-RT-001  
**Title:** Spend-typed approval without `material_amount` skips `within_authority`  
**Severity:** MATERIAL (fail-closed Authority path hole)  
**Where:** `create_approval_request` (no SPEND/EXCEPTION amount require) + `_decide` (`if dec == "APPROVED" and req.get("material_amount")`)  
**Fix (bounded):**
1. Create: if `request_type in {SPEND, EXCEPTION}` require non-empty `material_amount` + `currency` (same coerce rules).
2. Decide APPROVE: if `is_material_request(req)` always run `within_authority` (missing amount → deny via authority/`missing_amount` path — do not skip).
3. Add tests: create SPEND without amount → fail; create SPEND without amount via raw insert + decide → authority deny; existing 56 still green.
4. Do **not** seed live Authority Limits. Do not widen scope.

**Commit expected:** amend via new commit `fix(core): require amount on material approval types` (no force; no remote).

---

## Non-blocking notes (do not block Delegation after APR-RT-001 fixed)

- Cancel requires `approval.cancel` RBAC even for requester — live only Matt has it (by design for now).
- `PERS_MATT` hardcoded cancel privilege alongside RBAC — governance shortcut, documented.
- `snapshot_hash` stored but not re-checked on decide (no mutate API).
- Idempotent migrate bumps `org_permissions.updated_at` on re-run (metadata only; counts stay clean).

---

## Peaches verify (separate; not this review)

Peaches previously re-ran tests on Mac: `pass=56 fail=0`; live auth/approvals/decisions/audit = 0/0/0/47. That is **evidence verify**, not this Grok engineering review.

---

## Gate

- APPROVAL GROK REVIEWED ACTUAL DIFF: **YES**
- APPROVAL GROK RED TEAM: **FAIL** (APR-RT-001)
- APPROVAL FIX REQUIRED: **YES**
- Delegation slice: **HOLD** until fix commit + Grok re-review PASS

---

## Build note (Cursor APR-RT-001 fix — 2026-09-17)

Bounded fix applied on `build/wolf-command-rebuild` starting clean at `a1a09f0`:
- `create_approval_request`: SPEND/EXCEPTION require non-empty `material_amount` + `currency` (coerce reused).
- `_decide` APPROVE: always `within_authority` when `is_material_request` (missing amount fail-closed).
- Tests: create SPEND/EXCEPTION without amount fail; forged NULL-amount PENDING → approve authority-denied.
- Live `org_authority_limits` / approval rows untouched; no dual/SoD/delegation/UI.
- Commit: `fix(core): require amount on material approval types`

