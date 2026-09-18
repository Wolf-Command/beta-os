# Grok review — Dashboard truth eb79710

Date: 18 September 2026
Commit: eb79710937fc0b39549d01fd039e3e6070048b9e
Run: BF-2efe5973cc8a
Reviewer: Peaches (independent of Cursor's own report)

## Verdict

PASS. Close the lane. Do not change the ledger.

## What landed

- `scripts/core/progress_read_model.py` `compute_system_from_ledger` reads `state/model-c-baseline-assessments.json`.
- Live call on the Mac: sum_credits 19.45, counts ABSENT 1 / SPECIFIED 42 / BUILT 19 / PROVEN 12 / READY 3, system_pct 25.3, status OK, stale_reason None.
- Primary dial binds `system.system_pct`. A non-OK status renders `SCORING PROJECTION STALE` and hides the percentage.
- `dashboards/progress.html` has no hard-coded 25.3 and no live 28.
- `docs/RULE-Dashboard-Projection-2026-09-18.md` records the projection rule.
- Tests `scripts/tests/test_dashboard_truth.py`: PASS=50 FAIL=0, including SPECIFIED to BUILT delta 0.20 credits, percent delta 0.20/77×100, score restored, disagreeing integrity goes STALE, n not equal to 77 goes STALE, live ledger unchanged by tests.
- Cursor log: TESTS PASS=236 FAIL=0, EXIT 0.
- Live `GET http://127.0.0.1:8788/progress` returned 200. Production `GET http://127.0.0.1:8787/wolf.html` returned 200.
- Commit file list is seven files. The four dirty WIP scripts are still unstaged and were not in the commit.

## What the raw HTML curl is not

`/api/progress` without a Cloudflare JWT returns 403. The static HTML contains the stale branch as a template string. The rendered number is proven by the read model on the live ledger and by the tests, not by grepping the unexecuted template.

## Not done in this slice

SYSTEM still appears twice on the card: the large percent and a SYSTEM row in the Model E list. The foundations phase line and vocabulary chips are still on the primary card. That is the next bounded slice, not a fail of this one.

## Forbidden untouched

No ledger write. No credit-table write. No Model E score. No Production mutation. No CAP promotion.
