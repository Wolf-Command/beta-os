# P1 CAP-CORE-12 — Delegation & Escalation Burn-down — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing burn-down read in `scripts/core/escalation_burndown.py`. It does not start a second delegation system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the burn-down named in the 2026-09-19 escalation plan. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 28954 (`scripts/serve_beta.py`). It was not restarted. No money, bank, payment, ESB, or NAS write. No delegation was created. No Needs Matt row was cleared. No ledger row was raised. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_12_independence.py` run through `scripts/tests/run_guarded.py`, plus the existing burn-down suite through the same guard. DEPLOYED ROUTE PROOF was not added: no route changed. On pid 28954, unauthenticated `GET /api/health` is 200, and unauthenticated `GET /api/core/escalation-burndown` and `GET /escalation-burndown` are 403. The burn-down suite's owner 200 is its in-process handler under `development_assertion`. It is not a Cloudflare session on pid 28954. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-CORE-12` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, and `CAP-HR-01` are already CLOSED.

## BEFORE

SYSTEM BUILT (0.25). `CR-6e3fd7b9d7edca0e` is OPEN, blocker `NEEDS_ENGINEERING`. The catalog already holds the completion register and the delegation table. The ledger next bar was the independence tests. They name what still requires the owner. They are not an authority decision.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-6e3fd7b9d7edca0e` stays OPEN. `proven` stays false. `operating_test` stays false. `any_independence_day_done` stays false.

The read is `read_owner_independence`. It opens `catalog/content_library.sqlite` with `mode=ro`. A CLEAR window means the register has no unresolved `NEEDS_MATT` row. That window is not an independence day. `independence_days_done` is empty.

| window | independence | day marked done |
| --- | --- | --- |
| 7 | CLEAR | no |
| 30 | CLEAR | no |
| 90 | CLEAR | no |
| 365 | CLEAR | no |

Unresolved `NEEDS_MATT` rows: 0. Stored delegation rows: 0. The work-loop label on `delegated_decision` is `ELIMINATE`. That label is not evidenced. Audit rows are not a current grant: `delegation.created` 3, `delegation.used` 3, `delegation.revoked` 0. No person id was selected.

Names that still require the owner, from the existing retain labels. None of these is a measured reduction:

| name | source |
| --- | --- |
| exception_authorise | work_loop |
| payment | work_loop |
| bank_change | work_loop |
| daily_picture | owner_pulse |
| authority | owner_pulse |
| empty_records | owner_pulse |

Unresolved `NEEDS_POLICY` rows: 5. They were not reclassified as `NEEDS_MATT`. Completion rows stored: 114. Unresolved completion rows: 101.

## EVIDENCE

Commit `f683bd3`.

```
PASS=39 FAIL=0
EXIT: SUCCESS
COUNTS needs_matt=0 delegations=0 windows=CLEAR,CLEAR,CLEAR,CLEAR days_done=0 retain=exception_authorise,payment,bank_change,daily_picture,authority,empty_records policy_not_reclassified=5 audit_created=3 audit_used=3 audit_revoked=0 evidenced=False
```

The existing burn-down suite, through the same guard:

```
PASS=117 FAIL=0
```

The process exit was 0. The suite does not print `EXIT: SUCCESS`. Its log includes `test process refuses canonical Beta write`. That is the guard. A refused insert did not add a delegation. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`.

One repair pass. The first guarded run failed the outside-path check because a missing file never reached the path guard. The read now guards the path before the catalog open. The second run passed. No further repair.

Listeners after the suites:

```
15975  serve.py  8787
28954  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the independence read on the existing burn-down. A new delegation system was not added. No independence day was marked done. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. A delegation that moves authority stays an owner decision. The next Cursor P1 row is CAP-CORE-11.

RESULT: PASS
