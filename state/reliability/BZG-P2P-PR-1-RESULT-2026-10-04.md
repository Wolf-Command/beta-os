# BZG-P2P-PR-1 — Purchase Request vertical slice

**Finished:** 2026-10-04 ~18:55 WITA  
**Status:** IMPLEMENTATION_DONE_LOCAL_PASS  
**Parent:** BZG-PROCURE-TO-PAY-1 / GM-024 (DESIGNED — not implemented from this slice alone)

## What was built

Canonical Purchase Request path on Beta reusing `bzg_ops_purchase_requests` + `bzg_ops_pr_lines` (single SoR).

| Requirement | Evidence |
|-------------|----------|
| Authenticated person | `requester_person_id` + audit `actor_person_id` from session identity |
| Active assignment | `requester_assignment_id` from primary ACTIVE assignment |
| Outlet required | `outlet_id` NOT NULL on create; validation `missing_outlet` if absent |
| Seven outlets from config | `org_outlet_registry` — 7 rows seeded (migration count verified) |
| Lines item/qty/unit | `bzg_ops_pr_lines` unchanged; UI + API pass unit |
| Reason / purpose | `purpose` column required |
| Timestamps | `created_at`, `submitted_at` on submit |
| Status draft → submitted | `DRAFT` / `REQUESTED` |
| Save to Beta catalog | `create_purchase_request()` in `scripts/core/bzg_purchase_request.py` |
| Audit trail | `bzg.pr.create` + existing `bzg.pr.draft` / `bzg.pr.requested` |
| My Work / approval handoff | PENDING `core_approval_requests` row on submit (`work.complete` gate) |

## Permission

- New code: `bzg.pr.create` (`PERM-BZG-PR-CREATE`)
- Granted (migration): `ROLE-BZG-FB-OPS-LEAD`, `ROLE-BZG-HFB`, `ROLE-BZG-CAPTAIN`, `ROLE-MATT`
- Operator create button: `bzg.pr.create` OR legacy `work.create` (migration-era fallback in `_caps`)

## Routes / UI

- **Page:** `/bzg/uma-blu/bills` (`dashboards/bzg-uma-blu-bills.html`) — create form with required outlet select, lines, reason
- **POST:** `/api/bzg/uma-blu/prs`
- **GET permissions + outlets:** `/api/bzg/uma-blu/permissions` includes `outlets[]`

## Migration

- `scripts/migrations/migrate_bzg_p2p_pr1_20261004.py` — idempotent re-run OK (2026-10-04)
- Added columns: `entity_id`, `requester_person_id`, `requester_assignment_id`, `department`, `alchemist_pr_order_id`, `submitted_at`
- Backup: `catalog/backups/pre-bzg-p2p-pr1-*.sqlite`

## Tests

`scripts/tests/test_bzg_p2p_pr1_20261004.py` — **20 pass / 0 fail** (schema-only temp sqlite; no `shutil.copy2` live catalog)

Covers: outlet required, auth required, assignment/scope gate, save+audit, approval enqueue on submit, protected close read-only check.

## Honest limits

- `staff_ready`: **false**
- `human_commissioned`: **false**
- `eng_proved`: **false** — not stamped ENG_PROVED / PASS
- `deployed_beta`: **false** — `:8788` process not restarted; reload needed to serve new Python
- Unsigned write: HTTP POST without CF JWT → **403** (verified)
- Protected closes `VDC-470e741f` / `VDC-87202768`: **untouched**
- No Alchemist writes; no seeded operational purchases
- Optional `alchemist_pr_order_id` provenance pointer only — not populated in tests

## Out of scope (unchanged)

PO, receiving, AP, payment, GL, God Mode denominator, prod `:8787`.
