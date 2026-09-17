# WORK ITEMS — honesty table (Beta transitional)

**Status:** BUILT + TESTED 2026-09-17 (Cursor Local Agent)  
**Naming:** Work Item (`core_work_items`) ≠ Organisation Assignment (`org_assignments`)  
**API:** `/api/core/work-items` · Service: `scripts/core/work_items.py`

| Capability | Status |
|------------|--------|
| Work Item schema + state machine | **BUILT** (`012_work_items`) |
| Claimed COMPLETED ≠ VERIFIED | **BUILT + TESTED** (verify only via `/verify`) |
| RBAC `work.*` (Matt-only seed) | **BUILT** (`work.read/create/update/assign/complete/verify`) |
| Entity scope on list/get/create | **BUILT** (Assignment scopes → visible entities) |
| Audit integration (create/assign/start/block/complete/verify/cancel) | **BUILT** |
| Test isolation from live audit ledger | **BUILT** (`WOLF_TEST_MODE` + temp DB; `test_core_audit.py` off LIVE_DB) |
| Live seed work items | **0** (empty table) |
| Project / Kanban UI | **NOT BUILT** |
| Recurring scheduler / notifications / approvals | **NOT BUILT** |
| Evidence File Store | **NOT BUILT** (reference string hook only) |
| Daily-3 ranking engine | **NOT BUILT** (priority 1–5 field only) |
| AI / LLM task manager | **NOT BUILT** |

## Known audit ledger note (pre-Work-Items)

**47 rows** in `core_audit_events` as of 17 Sep 2026 after Audit Spine tests: predominantly `development_assertion` / integration-test traffic written because `test_core_audit.py` previously pointed HTTP tests at live `catalog/content_library.sqlite`.

**Rules (this slice):**

1. **Do not delete** those 47 events — append-only evidence.
2. Isolation fixed: audit + work-item tests use a **temp DB copy**; `WOLF_TEST_MODE=1` refuses accidental writes to the live catalog.
3. Any governed cleanup of the 47 requires a **separate Matt-approved migration** — not silent delete.

## State machine (honesty)

`OPEN` → `IN_PROGRESS` → `BLOCKED` ↔ `IN_PROGRESS` → `COMPLETED` → `VERIFIED`  
Any non-terminal → `CANCELLED`.  
`COMPLETED` = claimed done (`work.complete`). `VERIFIED` = separate (`work.verify`). No DELETE.
