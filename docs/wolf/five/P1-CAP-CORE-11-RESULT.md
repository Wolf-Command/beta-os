# P1 CAP-CORE-11 — SOP Factory — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing factory in `scripts/core/sop_factory.py`. It does not start a second SOP system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the SOP loop named in the 2026-09-19 factory. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted because the learn, acknowledge, and use routes were added. The old pid was 28954. The new pid is 38716 (`scripts/serve_beta.py`). No money, bank, payment, ESB, or NAS write. No live SOP file was created. No ledger row was raised. No completion row was resolved. No person was created. No permission row was inserted. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_11_loop.py` run through `scripts/tests/run_guarded.py`, plus the existing factory suite and the core management cluster suite through the same guard. DEPLOYED ROUTE PROOF is the unsigned checks on pid 38716. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-CORE-11` stays SPECIFIED, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, `CAP-HR-01`, and `CAP-CORE-12` are already CLOSED.

## BEFORE

SYSTEM SPECIFIED (0.05). `CR-c4ed4e3fa9f15a40` is OPEN, blocker `NEEDS_ENGINEERING`. The factory already stored a draft, an append-only version, and an approval. Learning, acknowledgement, and use were not stored. `catalog/sop_factory.sqlite` was absent.

## AFTER

The queue row is CLOSED. The ledger stays SPECIFIED. `CR-c4ed4e3fa9f15a40` stays OPEN. `proven` stays false. `ready` stays false. `staff_ready` stays false. `human_commissioned` stays false. `operating_adoption` stays false.

The loop is on the same factory file, and the proof used a temp file under `state/build-factory/tmp-f1/`. A draft carries an evidence note. A learning row points at that version and does not change its body. A later version is a new row. Approval appends an approver and does not rewrite the version. The earlier body stays readable. Acknowledgement is refused until an approver row exists. Use is refused unless the version is the current live one. A rewritten text file stores no version. Update and delete of a version row abort.

The temp walk stored version count 2, learning count 1, approval count 2, acknowledgement count 1, and use count 1. The change approver was the role gate on that temp file. That id is not a stored person and is not a permission grant. `catalog/sop_factory.sqlite` stayed absent, so the live factory count is not 0 versions. The file is absent.

Acknowledgement does not train staff. A use row does not measure operating adoption.

## EVIDENCE

Commit `08f480a`.

```
PASS=61 FAIL=0
EXIT: SUCCESS
COUNTS versions=2 learnings=1 approvals=2 acks=1 uses=1 approver_recorded=True prior_retained=True staff_ready=False commissioned=False adoption=False
```

The existing factory suite, through the same guard:

```
PASS=113 FAIL=0
```

The process exit was 0. The suite does not print `EXIT: SUCCESS`. Its log includes `test process refuses canonical Beta write`. That is the guard.

The core management cluster suite, through the same guard:

```
PASS=116 FAIL=0
EXIT: SUCCESS
```

A refused insert did not add a SOP. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`.

Unsigned checks on pid 38716:

| URL | code |
| --- | ---: |
| `GET /api/health` | 200 |
| `GET /api/sop` | 403 |
| `GET /api/sop/learn` | 403 |
| `POST /api/sop/learn` | 403 |
| `POST /api/sop/acknowledge` | 403 |
| `POST /api/sop/use` | 403 |
| `POST /api/sop/draft` | 403 |
| `POST /api/sop/approve` | 403 |

`GET /api/health` on `:8787` stayed 200. Those POST bodies were `{}`. They did not create `catalog/sop_factory.sqlite`.

No repair pass. The first guarded run passed.

Listeners after the restart:

```
15975  serve.py  8787
38716  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the versioned change with an approver. A rewritten file did not close it. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. A real approval inside the loop is still a human session. The next Cursor P1 row is CAP-FIN-02.

RESULT: PASS
