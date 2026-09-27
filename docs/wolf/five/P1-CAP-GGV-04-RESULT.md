# P1 CAP-GGV-04 — Lead Triage & Speed-to-Lead — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing speed-to-lead read in `scripts/core/ggv_speed_to_lead_prove.py`. It does not start a second triage system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 28954 (`scripts/serve_beta.py`). It was not restarted. No money, bank, payment, ESB, or NAS write. No Klaviyo, Metricool, or ActiveCampaign call. No ledger row was raised. No lead was created. No person was created. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_ggv_04_stored_leads.py` run through `scripts/tests/run_guarded.py`, plus the existing speed-to-lead suite through the same guard. DEPLOYED ROUTE PROOF was not added: no route changed. On pid 28954, unauthenticated `GET /api/health` is 200, and unauthenticated `GET /api/ggv/speed-to-lead-prove` and `GET /speed-to-lead-prove` are 403. The existing suite's 200 is its in-process handler. It is not a Cloudflare session on pid 28954. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-GGV-04` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01` is already CLOSED. `CAP-CRM-01` stays OPEN.

## BEFORE

SYSTEM BUILT (0.25). `CR-f089b11530ab4673` is OPEN. The catalog already holds Habitat lead rows. The ledger next bar was tests on those stored leads.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-f089b11530ab4673` stays OPEN. `operating_board` stays false. `proved` stays false.

The read is `read_stored_leads`. It opens `catalog/content_library.sqlite` with `mode=ro`. Demo rows are excluded from the operational counts. There is no `data_lane` column, so that lane is UNKNOWN.

| count | value |
| --- | ---: |
| stored rows | 8 |
| demo fixtures | 8 |
| operational rows | 0 |
| other brand rows | 0 |
| persons stored | 6 |
| persons created | 0 |
| leads created | 0 |

Brand: habitat 8, all demo. Ivy is ABSENT. That is not a zero board. Source system on every stored row: `fixture`.

Stored speed, on the demo fixtures only: waiting 7, measured 1, unavailable 0. Receipt present 1, absent 7, unreadable 0. Operational speed is empty. No SLA target was written. `sales` stays null. Closed rows are 3, and closed is not a sale. Conversion status on the fixtures: blank 6, CLAIMED 1, VERIFIED 1. Wolf stage: blank 1, ACTIVE 2, CLOSED 3, OPEN 1, PARKED 1. Source stage tokens stored: banana, closed, followup, new, parked, process, reserved/bought, won. One row each.

Owner set on 1 stored row, and that id matches one stored person. The person id is not in the report. Work item set on 0 rows.

Events already stored: observed 8, conversion_claimed 2, assigned 1, conversion_verified 1, human_touch_recorded 1. Thirteen event rows across 8 leads. Event payloads are not in the report.

## EVIDENCE

Commit `cdfd870`.

```
PASS=31 FAIL=0
EXIT: SUCCESS
COUNTS stored=8 demo=8 operational=0 waiting=7 measured=1 unavailable=0 persons=6
```

`scripts/tests/test_ggv_speed_to_lead_prove.py` through `run_guarded.py`: PASS=159 FAIL=0. The suite log includes `test process refuses canonical Beta write`. That is the guard. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Persons stayed 6. Leads stayed 8.

One repair: the first guarded run failed because a missing file returned unread before the path guard. The guard now runs first. The suite then passed. That was the repair pass.

Listeners after the suites:

```
15975  serve.py  8787
28954  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the stored-lead tests. A demo lead was not created to supply the evidence. The eight rows already stored are demo fixtures, and they are not counted as operational. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The lead CRM stays on CAP-CRM-01. The next Cursor P1 row is CAP-CRM-01.

RESULT: PASS
