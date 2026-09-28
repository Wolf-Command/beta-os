# P1 CAP-CRM-01 — Lead CRM — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing lead-CRM read in `scripts/core/crm_lead_cap_prove.py`. It does not start a second CRM. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 28954 (`scripts/serve_beta.py`). It was not restarted. No money, bank, payment, ESB, or NAS write. No Klaviyo or Metricool call. No ledger row was raised. No lead was created. No person was created. No assignment was created. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_crm_01_stored_leads.py` run through `scripts/tests/run_guarded.py`, plus the existing lead-CRM suite through the same guard. DEPLOYED ROUTE PROOF was not added: no route changed. On pid 28954, unauthenticated `GET /api/health` is 200, and unauthenticated `GET /api/crm/lead-cap-prove` and `GET /crm-lead-cap-prove` are 403. The existing suite's 200 is its in-process handler. It is not a Cloudflare session on pid 28954. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-CRM-01` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01` and `CAP-GGV-04` are already CLOSED.

## BEFORE

SYSTEM BUILT (0.25). `CR-ff42f3a7c49caa79` is OPEN. The catalog already holds lead rows. The ledger next bar was tests on that store. CAP-GGV-04 does not replace this row.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-ff42f3a7c49caa79` stays OPEN. `operating_board` stays false. `proved` stays false.

The read is `read_stored_crm`. It opens `catalog/content_library.sqlite` with `mode=ro`. Demo rows are excluded from the operational counts. There is no `data_lane` column, so that lane is UNKNOWN. There is no email column. Owned means `owner_person_id` is present. Aged means `source_observed_at` is present. Followed means `first_human_touch_at` is present. No age window and no follow policy were written.

| count | value |
| --- | ---: |
| stored rows | 8 |
| demo fixtures | 8 |
| operational rows | 0 |
| other brand rows | 0 |
| persons stored | 6 |
| assignments stored | 10 |
| persons created | 0 |
| assignments created | 0 |
| leads created | 0 |

Brand: habitat 8, all demo. Entity: ENT-GGV 8, all demo. Atrium is ABSENT. That is not a zero board. Source system on every stored row: `fixture`.

Stored bound, on the demo fixtures only: owned 1, unowned 7, aged 8, not aged 0, followed 1, not followed 7. Operational bound is empty. Client boundary is HELD: every stored row has an entity and a brand. The report lists neither a person id nor an assignment id.

The one owned row also has an assignment. Person without assignment is 0. Assignment without person is 0. The owner id matches one stored person. The assignment id matches one stored assignment. A person is not an assignment. Closed rows are 3, and closed is not a sale. Conversion status on the fixtures: claimed 1, verified 1. `sales` stays null.

## EVIDENCE

Commit `8fe76f2`.

```
PASS=41 FAIL=0
EXIT: SUCCESS
COUNTS stored=8 demo=8 operational=0 owned=1 unowned=7 aged=8 followed=1 persons=6 assignments=10 boundary=HELD
```

`scripts/tests/test_crm_lead_cap_prove.py` through `run_guarded.py`: PASS=114 FAIL=0. The suite log includes `test process refuses canonical Beta write`. That is the guard. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Persons stayed 6. Leads stayed 8. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`.

No repair pass. The first guarded run passed.

Listeners after the suites:

```
15975  serve.py  8787
28954  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the stored-lead tests on the existing lead store. A new CRM was not added. A demo lead was not created to supply the evidence. The eight rows already stored are demo fixtures, and they are not counted as operational. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. Speed-to-lead stays on CAP-GGV-04. The next Cursor P1 row is CAP-HR-01.

RESULT: PASS
