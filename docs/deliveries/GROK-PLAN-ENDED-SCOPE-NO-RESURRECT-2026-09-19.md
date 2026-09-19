# GROK PLAN — ENDED scopes must not resurrect — 2026-09-19

## Goal
Fix documented defect: `migrate_uma_blu_daily_close.upsert_asg_scope` (and any similar upsert helpers) must **not** force an ENDED assignment-scope row back to ACTIVE / clear end_at.

## Evidence
- `docs/deliveries/GROK-REVIEW-DEVI-UMA-COMMISSION-AUTH-275d1c7-2026-09-19.md`
- Completion Register item: ENDED scope resurrection on daily-close assignment upsert
- Devi `SCOPE-BZG-ENTITY` was surgically ENDED then revived by test/migrate upsert

## Design
1. Find all upsert paths that write `org_assignment_scopes` / equivalent with `status='ACTIVE', end_at=NULL` on conflict.
2. On conflict: if existing row status is ENDED (or end_at set), **leave ENDED** unless caller passes explicit `revive=True` gated for Owner-only tooling (default False). Prefer: never revive from migrate/seed/test helpers.
3. Add unit test: insert ACTIVE → end to ENDED → upsert without revive → still ENDED.
4. Add regression in daily-close / Devi scope prove path.
5. After fix, mark matching Completion Register item RESOLVED with resolution_evidence (commit + test name).

## Non-goals
- No bulk re-end of unrelated scopes
- No Production
- No CF / Access changes
- Preserve WIP four files

## Success
- Test proves ENDED survives upsert
- Devi ENTITY stays ENDED after running daily-close migrate/test helpers
- Completion Register item closed with evidence
- SYSTEM % unchanged

## Slice
`BF-ended-scope-no-resurrect-20260919`
