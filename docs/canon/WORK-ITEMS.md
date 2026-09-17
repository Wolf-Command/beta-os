# WORK ITEMS — honesty table (Beta transitional)

**Status:** planned for Cursor implementation 2026-09-17  
**Naming:** Work Item (`core_work_items`) ≠ Organisation Assignment (`org_assignments`)

| Capability | Status |
|------------|--------|
| Work Item schema + state machine | PENDING CURSOR |
| Claimed COMPLETED ≠ VERIFIED | REQUIRED |
| RBAC work.* (Matt-only seed) | PENDING CURSOR |
| Audit integration | PENDING CURSOR |
| Test isolation from live audit ledger | REQUIRED (47-event pollution documented) |
| Project / Kanban UI | NOT BUILT |
| Recurring scheduler / notifications / approvals | NOT BUILT |

## Known audit ledger note (pre-Work-Items)

47 rows in `core_audit_events` as of 17 Sep 2026 after Audit Spine tests: predominantly `development_assertion` / integration-test traffic written because `test_core_audit.py` pointed HTTP tests at live `catalog/content_library.sqlite`. **Do not delete.** Isolate future tests. Cleanup only via separate Matt-governed migration if desired.
