# GROK PLAN — Decision Memory v1 (P4 overnight continue)

**Date:** 2026-09-18
**Authority:** Matt CONTINUE overnight: P3 then P4 (do not ask). Peaches named P4.
**CAP:** CAP-INTEL-04 Decision Memory
**Why this cap:** Next highest-value safe software after AKR. No money, no payroll, no legal opinion, no Habitat/Uma disturbance, no external writes.
**Beta only. No Production.**

## Scope

Smallest deterministic store + recall. Reuse append-only habit of `scripts/core/audit.py` (no silent rewrite). Do not replace the audit spine.

`scripts/core/decision_memory.py`:

1. `record_decision(...)` INSERT only:
   - decision_id, scope (entity/brand/object), title
   - options_considered (list, required, may be empty only if reason recorded)
   - chosen_option
   - approval_ref (optional pointer; no invented approver)
   - outcome (optional; UNKNOWN allowed; never invented)
   - actor, occurred_at, provenance
2. `recall(scope, query)` returns matching decisions with provenance. Bounded (max 50).
3. Corrections are new INSERT rows that reference prior decision_id. No UPDATE/DELETE of history.
4. States: RECORDED | OUTCOME_UNKNOWN | NOT FOUND
5. Tests: append-only, no silent rewrite, scope isolation (Habitat decision not returned for Uma), empty outcome ≠ invented outcome, recall cap.

## Non-goals

- New agent / UI cockpit / vector search
- Auto-deciding
- Inventing approvals, money, or outcomes
- Touching Habitat content_planner, Uma close, Metricool, ESB, Production
- Promoting into memory_items
- Raising maturity past BUILT without red-team (Grok review is Peaches lane after Cursor)

## Success

- `python3 scripts/tests/test_decision_memory.py` green
- Commit message references CAP-INTEL-04
- Print CURSOR_DONE + git log -1 --oneline + PASS/FAIL
