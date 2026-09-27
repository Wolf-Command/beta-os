# P1 CAP-GGV-01 — Content Machine — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing content catalog read on `scripts/core/ggv_strategy_machine.py`. It does not start a second content system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the machine named in the 2026-09-20 strategy-machine plan. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 28954 (`scripts/serve_beta.py`). It was not restarted. No money, bank, payment, ESB, or NAS write. No Metricool call. No ledger row was raised. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_ggv_01_content_path.py` run through `scripts/tests/run_guarded.py`, plus the existing strategy-machine suite through the same guard. DEPLOYED ROUTE PROOF was not added: no route changed. On pid 28954, unauthenticated `GET /api/health` is 200, and unauthenticated `GET /api/ggv/strategy-machine` and `GET /ggv-strategy-machine` are 403. The strategy suite's 200s are its in-process handler. They are not a Cloudflare session on pid 28954. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-GGV-01` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the first OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-02` stays READY_FOR_HUMAN.

## BEFORE

SYSTEM BUILT (0.25). The strategy skeleton names five empty slots. `CR-8c1fa12404180c02` is OPEN. The content catalog already holds plans, cards, assets, planner rows, and revisions.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-8c1fa12404180c02` stays OPEN. The skeleton stays empty. `live_strategy_machine` stays false. `governed_learning` stays false.

The read is `read_content_path`. It opens `catalog/content_library.sqlite` with `mode=ro`. Test-lane rows are excluded from the operational counts.

| kind | source | lane | stored | test lane excluded |
| --- | --- | --- | ---: | ---: |
| strategy | `content_plans.strategy_json` | operational | 6 | 3 |
| plan | `content_plans` | operational | 6 | 3 |
| asset | `assets` | UNKNOWN | 17 | no `data_lane` column |
| workflow | `plan_revisions` | operational | 20 | 9 |
| learn | `important_learnings` inside operational strategy JSON | operational | 12 | counted only on operational plans |

Operational plan status: Working_Draft 5, Human_Approved 1. Review marks on those rows: WORKING 5, APPROVED 1. Operational cards 102. Test cards excluded 51.

Assets have no `data_lane`, so that lane is UNKNOWN. Stored brand status: atrium indexed 1, habitat VERIFIED 1, habitat indexed 15. The brand table has one row, `habitat`, status ACTIVE.

Planner has no `data_lane`, so that lane is UNKNOWN. Stored rows: bzg Human_Approved 1, habitat Draft 4, habitat Ready_for_Render 1. One planner row has a `raw_asset_id` that exists in `assets`. `core_approval_request_id` is set on 0 planner rows. `approved_is_published` is false. Publish stays on CAP-GGV-02.

Operational revisions: AI_PROPOSAL 6, HUMAN_APPROVED 11, REQUEST_REVISION 3. Test revisions excluded: 9.

Learn items are 12 stored rows and 2 distinct statements. Sources: `performance`. Surfaces: `post`, `story`. Six operational plans carry the stored label `performance_data=connected`. This read did not call Metricool. `metricool_called` and `metricool_write` are false. No learning-library table exists. `learning_library` is NOT CONNECTED. `learn_outcome` is null. `strategy_score` and `revenue` are null.

Statement text, themes, objectives, and scripts are not in the report.

## EVIDENCE

Commit `e982a90`.

```
PASS=30 FAIL=0
EXIT: SUCCESS
```

`scripts/tests/test_ggv_strategy_machine.py` through `run_guarded.py`: PASS=238 FAIL=0. The suite log includes `test process refuses canonical Beta write`. That is the guard. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`.

One repair: the first guarded run failed because `core_evidence_records` uses `evidence_id`. The column was corrected and the suite then passed. That was the repair pass.

Listeners after the suites:

```
15975  serve.py  8787
28954  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the content-path tests on the existing catalog. A new content product was not added. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The publish walk stays on CAP-GGV-02. The next Cursor P1 row is CAP-GGV-04.

RESULT: PASS
