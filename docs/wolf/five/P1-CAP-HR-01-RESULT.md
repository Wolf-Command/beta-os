# P1 CAP-HR-01 — People Master Record — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing person, position, and assignment read in `scripts/core/staffing.py`. It does not start a second people master. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 28954 (`scripts/serve_beta.py`). It was not restarted. No money, bank, payment, ESB, or NAS write. No person was created. No role, position, or assignment was created. No ledger row was raised. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_hr_01_stored_people.py` run through `scripts/tests/run_guarded.py`. DEPLOYED ROUTE PROOF was not added: no route changed. On pid 28954, unauthenticated `GET /api/health` is 200, and unauthenticated `GET /api/core/persons`, `GET /api/core/roles`, `GET /api/core/positions`, and `GET /api/core/me/assignments` are 403. Unauthenticated `GET /api/core/persons/<stored id>` is 200, and an id that is not stored is 404. The handler `_get_core_person` does not check `organisation.person.read`. The list handler does. The auth-identity handler source returns `identifier`. That URL was not called. The record body was not printed. This pack did not change those handlers. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-HR-01` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, and `CAP-CRM-01` are already CLOSED.

`scripts/tests/test_person_auth_identity.py` and `scripts/tests/test_role_position_assignment.py` were not re-run. They insert and delete assignment rows, and they still expect 4 persons and 4 positions. The store now has 6 persons and 12 positions. They are not this closure test.

## BEFORE

SYSTEM BUILT (0.25). `CR-6e8a5493b94e788a` is OPEN. The catalog already holds persons, roles, positions, and assignments. The ledger next bar was tests on that store. People are not roles.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-6e8a5493b94e788a` stays OPEN. `operating_board` stays false. `proved` stays false.

The read is `read_stored_people`. It opens `catalog/content_library.sqlite` with `mode=ro`. A demo person is a person id containing DEMO, SEED, FIXTURE, or TEST. A fixture seat is a position id containing those tokens, or a role whose type is `fixture`. Operational occupancy is an active assignment of a non-demo person on a seat that is not a fixture. There is no `data_lane` column on `org_persons`, so that lane is UNKNOWN. There is no email column on `org_persons`. The report lists no person id, role id, position id, assignment id, display name, legal name, or auth identifier.

| count | value |
| --- | ---: |
| stored persons | 6 |
| demo persons | 1 |
| operational persons | 5 |
| fixture-only persons | 0 |
| unseated persons | 0 |
| ended-only persons | 0 |
| roles stored | 12 |
| positions stored | 12 |
| assignments stored | 10 |
| active assignments | 8 |
| ended assignments | 2 |
| operational active assignments | 5 |
| fixture active assignments | 3 |
| persons created | 0 |

Person id overlap with role id is 0. No assignment uses a role id or a position id as its person. People are not roles. This read does not authorize anyone.

Legal entities stored: 3. All three are `LEGAL_ENTITY` and `LIVE`. None is absent. A legal name is stored on each entity. The name is not in the report.

| entity | positions | fixture positions | operational persons | empty operational seats | occupancy |
| --- | ---: | ---: | ---: | ---: | --- |
| ENT-AMG | 1 | 1 | 0 | 0 | EMPTY |
| ENT-BZG | 3 | 0 | 1 | 2 | PRESENT |
| ENT-GGV | 8 | 2 | 4 | 2 | PRESENT |

ENT-AMG has one stored position and it is a fixture seat. Empty operational occupancy is not an absent entity. ENT-BZG empty seats are `POS-BZG-CLOSER-UMA-1` (no assignment) and `POS-BZG-HFB-UMA-1` (ENDED). ENT-GGV empty seats are `POS-GGV-EXT-ACCT` (no assignment) and `POS-VIDEO-EDITOR-1` (ENDED). No closer was seated. No accountant was invented.

Two stored persons also hold a fixture seat. Both of those persons have an operational seat, so fixture-only persons stay 0. The demo person is not in the operational count.

Role rows: ACTIVE 2, SPECIFIED 10. Role types: EXECUTIVE 1, EXTERNAL 1, OPERATING 8, SHARED_SERVICE 1, fixture 1. One role has no position. That role is not a person.

Legal name is present on 3 operational persons and absent on 2. The absent field is empty. It is not an invented name. Auth identities stored: 5, provider `email`, status ACTIVE. All 5 match a stored person. Persons without an active auth identity: 1. Operational persons without one: 0. Identifiers were not selected.

No payroll table exists. No wage column exists on `org_persons`. `pay_figure` stays null. `payroll_source` stays UNAVAILABLE. That is CAP-HR-04. It was not tested here.

Seat boundary is HELD: every assignment has a person and a position, every position has a role and a known entity.

## EVIDENCE

Commit `8394a49`.

```
PASS=40 FAIL=0
EXIT: SUCCESS
COUNTS stored=6 demo=1 operational=5 fixture_only=0 roles=12 positions=12 assignments=10 active_operational=5 entities=3 boundary=HELD
```

The suite log includes `test process refuses canonical Beta write`. That is the guard. A refused insert did not add a person. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Persons stayed 6. Roles stayed 12. Positions stayed 12. Assignments stayed 10. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`.

No repair pass. The first guarded run passed.

Listeners after the suite:

```
15975  serve.py  8787
28954  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the stored-person tests on the existing people store. A new people master was not added. A demo person was not created to supply the evidence. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. Payroll stays on CAP-HR-04. The next Cursor P1 row is CAP-CORE-12.

RESULT: PASS
