# P1 CAP-FIN-02 — Bank Statement Ingest & Reconcile — 28 Sep 2026

Pack F6. Beta/local only. This extends the existing statement read in `scripts/core/intg_connector_cap_tests.py`. It does not start a second bank system. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5, on the file ingest named by the 2026-07-30 decision (no bank feed). Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted because the reconcile route was added. The old pid was 38716. The new pid is 40318 (`scripts/serve_beta.py`). No payment, no bank API, no ESB write, no NAS write. No amount was parsed. No books row was written. No ledger row was raised. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_fin_02_reconcile.py` run through `scripts/tests/run_guarded.py`, plus the existing file-read suite and the connector framework suite through the same guard. DEPLOYED ROUTE PROOF is the unsigned checks on pid 40318. The connector suite's owner 200 is its in-process handler under `development_assertion`. It is not a Cloudflare session on pid 40318, and that suite did not call the reconcile path. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-FIN-02` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, `CAP-HR-01`, `CAP-CORE-12`, and `CAP-CORE-11` are already CLOSED.

## BEFORE

SYSTEM BUILT (0.25). `CAP-INTG-04` is CLOSED on the file read. Reconcile was still false on that read. `CR-e9e5e79e7b41bac3` is OPEN, blocker `NEEDS_ENGINEERING`. `CR-8244b1ea58370c70` is OPEN, blocker `NEEDS_ADOPTION`.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. Both completion rows stay OPEN. `proven` stays false. `ready` stays false. `staff_ready` stays false. `human_commissioned` stays false. `operating_adoption` stays false.

The reconcile is a second read of the same statement files. The output matches when the opened count, the pdf count, the csv count, the spreadsheet count, the byte count, the manifest, and the row hashes agree. That match is file identity. `books_reconciled` stays false. `amounts_parsed` stays false. `books_written` stays false. `payment_executed` stays false.

The authorised archive matched. Opened 54, pdf 30, csv 16, spreadsheet 8, bytes 4210187, manifest `7436bd97bc6f33195f71a5df3756b55730b079833dc72ed4cc87a37992eb74e2`. That is the same manifest as the CAP-INTG-04 read. A temp pdf matched itself and did not close the row. A doctored manifest did not match. A typed balance, including zero, was refused. A balance placed on the ingest report was refused. A payment argument was refused. An empty balance string is not a typed balance.

CONFIGURED, CONNECTED, TESTED, and COMMISSIONED stay separate. The archive is configured. It is not a bank connection. No person accepted this.

## EVIDENCE

Commit `0fda620`.

```
SUMMARY pass=44 fail=0
EXIT: SUCCESS
NOTE  opened=54 pdf=30 csv=16 spreadsheet=8 bytes=4210187 manifest=7436bd97bc6f33195f71a5df3756b55730b079833dc72ed4cc87a37992eb74e2 match=True
COUNTS evidence=4 exceptions=3 approvals=9 evidence_status=INVALIDATED fin02_resolved=0
```

The existing file-read suite, through the same guard:

```
SUMMARY pass=38 fail=0
EXIT: SUCCESS
```

The connector framework suite, through the same guard:

```
PASS=206 FAIL=0
```

The process exit was 0. The suite does not print `EXIT: SUCCESS`. Its log includes `test process refuses canonical Beta write`. That is the guard.

A refused balance did not write a book. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`, reason `P4-TEST cleanup`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-INTG-04` stayed `BUILT`. `CAP-FIN-02` stayed `BUILT`.

Unsigned checks on pid 40318:

| URL | code |
| --- | ---: |
| `GET /api/health` | 200 |
| `GET /api/intg/connector-cap-tests/reconcile` | 403 `missing_auth` |
| `GET /api/intg/connector-cap-tests/reconcile?balance=1` | 403 `missing_auth` |
| `GET /api/intg/connector-cap-tests/reconcile?amount=1` | 403 |
| `GET` with spoofed email | 403 `missing_auth` |
| `GET` with `X-Wolf-Subject: PERS-MATT` | 403 `missing_auth` |
| `GET` with `Cf-Access-Jwt-Assertion: a.b.c` | 403 `invalid_token` |
| `POST /api/intg/connector-cap-tests/reconcile` | 403 `missing_auth` |
| `POST /api/intg/connector-cap-tests/payment` | 403 `missing_auth` |

None of those bodies is a reconcile match. The public hostname returns 302 to `wolfcommand.cloudflareaccess.com` for the reconcile path. `server: cloudflare`. The login query string was not recorded. `GET /api/health` on `:8787` stayed 200.

No repair pass. The first guarded run passed.

Listeners after the restart and the suites:

```
15975  serve.py  8787
40318  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the file-identity match against the ingested file, with no payment. A typed balance did not close it. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. A books balance is still unparsed. The next Cursor P1 row is CAP-FIN-01.

RESULT: PASS
