# P1 CAP-FIN-05 — Management Reporting — 28 Sep 2026

Pack F6. Beta/local only. This reads the existing management-reporting framework and the accounting-core books read. It does not start a second reporting system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 40318 (`scripts/serve_beta.py`). It was not restarted. No route was added. No money, bank, payment, ESB, or NAS write. No statement was typed. No book was opened. No ledger row was raised. No completion row was resolved. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_fin_05_reporting.py` run through `scripts/tests/run_guarded.py`, plus the existing management-reporting suite and the accounting-core suite through the same guard. DEPLOYED ROUTE PROOF is the unsigned checks on pid 40318. No report route was added, so those checks are the existing management-reporting route. The management-reporting suite's owner 200 is its in-process handler. It is not a Cloudflare session on pid 40318, and that suite did not call `read_management_report`. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-FIN-05` stays SPECIFIED, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, `CAP-HR-01`, `CAP-CORE-12`, `CAP-CORE-11`, `CAP-FIN-02`, `CAP-FIN-01`, and `CAP-FIN-03` are already CLOSED.

## BEFORE

SYSTEM SPECIFIED (0.05). `CR-20b4dd71cc0fcc88` is OPEN, blocker `NEEDS_ENGINEERING`, next action the full P&L, balance sheet, and cash-flow pack. `catalog/fin_mgmt_reporting.sqlite` is absent. The finance display is UNAVAILABLE. The commissioned books file is absent. The uncommissioned sample is present and was not opened.

## AFTER

The queue row is CLOSED. The ledger stays SPECIFIED. `CR-20b4dd71cc0fcc88` stays OPEN. `proven` stays false. `ready` stays false. `staff_ready` stays false. `human_commissioned` stays false. `operating_adoption` stays not measured.

The read is `read_management_report`. It calls the existing accounting-core read and the existing empty framework. It does not pass an Atrium path to `sqlite3.connect`. A typed P&L, balance sheet, cash flow, cash figure, trial balance, statement, or amount, including zero, is refused. A payment argument is refused. An open-books flag is refused. An empty figure string is not a typed statement.

While the books source stays `UNAVAILABLE`, `report_state` is `UNAVAILABLE`. That word is not a statement and not zero. `statements_rendered` stays false. `pnl`, `balance_sheet`, `cash_flow`, `cash`, `trial_balance`, and `statement` stay null. The five named slots stay empty. `recorded_count` stays 0. That count is the empty framework. It is not cash.

The finance display stayed UNAVAILABLE. It is not shown as current. The commissioned books file stayed absent. The uncommissioned sample stayed present and was not opened. Its file stat did not change. The framework file stayed absent. A green read sets `green_test_renders_pack` false. Opening the books is still an owner act. This row does not ask for a second books decision.

A temp catalog with one fixture entity did not render a statement and did not open the sample. That fixture has no completion row. The live completion row stayed open after that fixture.

## EVIDENCE

Commit `089e8a7`.

The guarded run passed on the first attempt. No repair pass.

```
PASS=58 FAIL=0
EXIT: SUCCESS
NOTE  report=UNAVAILABLE display=UNAVAILABLE books_source=UNAVAILABLE books_opened=False statements_rendered=False sample_present=True commissioned_present=False ledger=SPECIFIED cr=OPEN
COUNTS evidence=4 exceptions=3 approvals=9 evidence_status=INVALIDATED fin05_resolved=0
```

The guard check passed. The refusal text is `test process refuses canonical Beta write`.

The existing management-reporting suite, through the same guard:

```
PASS=266 FAIL=0
```

The process exit was 0. The suite does not print `EXIT: SUCCESS`. Its log includes `test process refuses canonical Beta write`. The owner 200 in that log is the in-process handler. It is not pid 40318. That suite did not call `read_management_report`.

The accounting-core suite, through the same guard:

```
PASS=56 FAIL=0
EXIT: SUCCESS
NOTE  entities=3 display=UNAVAILABLE books_source=UNAVAILABLE books_opened=False sample_present=True commissioned_present=False cr=OPEN
```

Its log includes the same guard check. That suite did not call `read_management_report`.

A refused statement did not write a book. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-FIN-05` stayed `SPECIFIED`. `CR-20b4dd71cc0fcc88` stayed `OPEN`. Resolved `CAP-FIN-05` rows stayed 0.

Unsigned checks on pid 40318:

| URL | code |
| --- | ---: |
| `GET /api/health` | 200 |
| `GET /api/fin/mgmt-reporting` | 403 `missing_auth` |
| `GET /api/fin/mgmt-reporting?pnl=1` | 403 `missing_auth` |
| `GET /fin-mgmt-reporting` | 403 `missing_auth` |
| `GET` with spoofed email | 403 `missing_auth` |
| `GET` with `X-Wolf-Subject: PERS-MATT` | 403 `missing_auth` |
| `GET` with `Cf-Access-Jwt-Assertion: a.b.c` | 403 `invalid_token` |
| `POST /api/fin/mgmt-reporting/books` | 403 `missing_auth` |
| `POST /api/fin/mgmt-reporting/current` | 403 `missing_auth` |

None of those bodies is a statement. The public hostname returns 302 to `wolfcommand.cloudflareaccess.com` for `/api/fin/mgmt-reporting`. `server: cloudflare`. The login query string was not recorded. `GET /api/health` on `:8787` stayed 200.

Listeners after the suites:

```
15975  serve.py  8787
40318  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the report that says unavailable while the books stay unopened. A green test did not render a P&L, a balance sheet, or a cash figure. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The books stay unavailable until an owner opens a real source. This file does not ask for that decision. The next Cursor P1 row is CAP-INTG-02.

RESULT: PASS
