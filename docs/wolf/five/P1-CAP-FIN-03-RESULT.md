# P1 CAP-FIN-03 — Entity Finance Boards — 28 Sep 2026

Pack F6. Beta/local only. This reads the existing GGV, Atrium, and Uma desks in one matrix. It does not start a second finance board. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 40318 (`scripts/serve_beta.py`). It was not restarted. No route was added. No money, bank, payment, ESB, or NAS write. No person, role, position, or assignment was created. No book was opened. No balance was typed. No ledger row was raised. No completion row was resolved. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_fin_03_boards.py` run through `scripts/tests/run_guarded.py`, plus the accounting-core suite through the same guard. DEPLOYED ROUTE PROOF is the unsigned checks on pid 40318. No board route was added, so those checks are the existing GGV, Atrium, and Uma desks. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-FIN-03` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, `CAP-HR-01`, `CAP-CORE-12`, `CAP-CORE-11`, `CAP-FIN-02`, and `CAP-FIN-01` are already CLOSED.

## BEFORE

SYSTEM BUILT (0.25). `CR-671ef246d8d850b2` is OPEN, blocker `NEEDS_ENGINEERING`, next action the shared prove matrix. Three further `CAP-FIN-03` rows are OPEN, blocker `NEEDS_ADOPTION`: `CR-7894d3a1f26d3ae9`, `CR-c43ba3c98d52d058`, `CR-4c75b8dec28cf8d1`. `POS-GGV-EXT-ACCT` is stored on `ENT-GGV` with role `ROLE-GGV-EXTERNAL-ACCOUNTANT` and no active assignment. `ASG-AMANDA-CM-1` is active and primary on `POS-CONTENT-MGMT-1` / `ROLE-CONTENT-MGMT`.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. All four completion rows stay OPEN. `proven` stays false. `ready` stays false. `staff_ready` stays false. `human_commissioned` stays false. `operating_adoption` stays not measured.

The read is `read_entity_finance_boards`. It opens `catalog/content_library.sqlite` with `mode=ro`. It calls the existing accounting-core read and does not open either Atrium path. A typed balance, including zero, is refused. A payment argument is refused. An open-books flag is refused. A seat, person, or assign argument is refused. An empty balance string is not a typed balance.

Three stored legal entities are covered by one matrix. Uma is the venue desk on `ENT-BZG`. It is not a fourth legal entity.

| board | entity | href | kind |
| --- | --- | --- | --- |
| GGV | `ENT-GGV` | `/ggv/finance` | notes |
| ATRIUM | `ENT-AMG` | `/amg-ops-pack` | closed desk |
| UMA | `ENT-BZG` | `/bzg/uma-blu` | operations |

The GGV page contains "Not paid from this screen". Stored notas are 0 and stored vendors are 0. Those counts are not cash. The Atrium page contains "Hotel books are not open on this desk." The commissioned books file stayed absent. The uncommissioned sample was not opened. The Uma page contains "No stock count is on this screen. Stock stays in ESB." `POS-BZG-CLOSER-UMA-1` has 0 active assignments. This read did not seat a closer. Every board money field stays null. Every books source stays UNAVAILABLE. The finance display stayed UNAVAILABLE.

`POS-GGV-EXT-ACCT` stayed stored and empty: 0 active assignments. `ASG-AMANDA-CM-1` stayed on `POS-CONTENT-MGMT-1` with `ROLE-CONTENT-MGMT`. That assignment is not the accountant position and not the accountant role. No person row was written. Persons stayed 6. Assignments stayed 10.

A temp catalog with the accountant position and no assignment stayed empty. A fixture assignment on that temp file was read as one occupant and was not written into the live catalog. The live seat stayed empty after that fixture.

## EVIDENCE

Commit `888226a`.

The first guarded run failed one check. The read-only flag sits on the URI, and the assertion required it on the `connect` line. One repair moved the assertion to the URI. The repaired run:

```
PASS=73 FAIL=0
EXIT: SUCCESS
NOTE  boards=3 seat_empty=True accountant_active=0 content_is_seat=False display=UNAVAILABLE cr_open=4
COUNTS evidence=4 exceptions=3 approvals=9 evidence_status=INVALIDATED fin03_resolved=0 persons=6 assignments=10
```

The suite log includes the guard check. The refusal text is `test process refuses canonical Beta write`.

The accounting-core suite, through the same guard:

```
PASS=56 FAIL=0
EXIT: SUCCESS
NOTE  entities=3 display=UNAVAILABLE books_source=UNAVAILABLE books_opened=False sample_present=True commissioned_present=False cr=OPEN
```

Its log includes `test process refuses canonical Beta write`. That suite did not call `read_entity_finance_boards`.

A refused seat did not write a person. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-FIN-03` stayed `BUILT`. `CR-671ef246d8d850b2` stayed `OPEN`. Resolved `CAP-FIN-03` rows stayed 0.

Unsigned checks on pid 40318:

| URL | code |
| --- | ---: |
| `GET /api/health` | 200 |
| `GET /ggv/finance` | 403 `missing_auth` |
| `GET /amg-ops-pack` | 403 `missing_auth` |
| `GET /bzg/uma-blu` | 403 `missing_auth` |
| `GET /bzg/uma-blu/bills` | 403 `missing_auth` |
| `GET` with spoofed email | 403 `missing_auth` |
| `GET` with `X-Wolf-Subject: PERS-MATT` | 403 `missing_auth` |
| `GET` with `Cf-Access-Jwt-Assertion: a.b.c` | 403 `invalid_token` |
| `POST /api/ggv/finance/pay` | 403 `missing_auth` |

None of those bodies is a seated board. The public hostname returns 302 to `wolfcommand.cloudflareaccess.com` for `/ggv/finance`. `server: cloudflare`. The login query string was not recorded. `GET /api/health` on `:8787` stayed 200.

Listeners after the suites:

```
15975  serve.py  8787
40318  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the shared desk read without a new person row. A green test did not fill `POS-GGV-EXT-ACCT`. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The accountant seat stays empty unless an owner assigns a real person. This file does not ask for that assignment. The next Cursor P1 row is CAP-FIN-05.

RESULT: PASS
