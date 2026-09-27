# P1 CAP-INTG-04 — Bank Statement Connector — 27 Sep 2026

Pack S4. Beta/local only. This extends the existing connector skeleton. It does not start a second bank system. Decision served: 2026-07-30, no bank feed, monthly statement files. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 78725 to pid 82010 (`scripts/serve_beta.py`) so the file-read route loaded. No payment, no bank API, no ESB write, no NAS write. No amount was parsed. No books row was written. No JWT was minted. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_intg_04_file_read.py` plus the existing connector suite. DEPLOYED ROUTE PROOF is the unsigned deny on pid 82010 and the public Access redirect. A seated allow was not observed. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%. The ledger stays BUILT.

The row was taken because it is the first OPEN P1 with no prerequisite. CAP-GGV-02 is already READY_FOR_HUMAN. CAP-BZG-03 is already BLOCKED_OWNER.

## BEFORE

SYSTEM BUILT (0.25). The connector framework named empty cap, fixture, and refuse slots. Integration health said no authorised bank-statement reader was called. The owner archive `~/.openclaw/state/bank` was already on disk from the 19 Sep filing. The skeleton did not read it.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-859e7cad64e7e4ad` stays unresolved.

The reader opened 54 files already in that archive: 30 pdf, 16 csv, 8 spreadsheet, 4210187 bytes. Manifest sha256 `7436bd97bc6f33195f71a5df3756b55730b079833dc72ed4cc87a37992eb74e2`. Names in the report have digit runs removed. JSON and other files in the same directory were not opened. A temp pdf is not treated as the archive.

The four states stay separate:

| state | this run |
| --- | --- |
| CONFIGURED | true. The owner archive directory is the file source. |
| CONNECTED | false. No bank API was called. A file on disk is not a bank connection. |
| TESTED | true. The read attempt finished. |
| COMMISSIONED | false. No person accepted this. |

`payment_executed`, `money_moved`, `amounts_parsed`, `persisted`, `books_written`, `reconciled`, and `management_report` are false. Reconcile and a management report stay on CAP-FIN-02.

On pid 82010:

| caller | request | status |
| --- | --- | --- |
| no header | `GET /api/intg/connector-cap-tests/file-read` | 403 `missing_auth` |
| spoofed email | same | 403 `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | same | 403 `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | same | 403 `invalid_token` |
| no header | `POST /api/intg/connector-cap-tests/payment` | 403 `missing_auth` |

None of those bodies is a file list. The public hostname returns 302 to `wolfcommand.cloudflareaccess.com` for the file-read path. `server: cloudflare`. The login query string was not recorded.

## EVIDENCE

Commit `80b8a3e`. Test: `scripts/tests/test_cap_intg_04_file_read.py`.

```
NOTE  beta_pid=82010 prod_pid=15975
NOTE  opened=54 pdf=30 csv=16 spreadsheet=8 bytes=4210187 manifest=7436bd97bc6f33195f71a5df3756b55730b079833dc72ed4cc87a37992eb74e2
NOTE  configured=True connected=False tested=True commissioned=False
SUMMARY pass=38 fail=0
EXIT: SUCCESS
```

`scripts/tests/test_intg_connector_cap_tests.py`: PASS=206 FAIL=0. The empty framework is still empty. Ledger file unchanged. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-INTG-04` is still `BUILT`. Row count 77.

Previously green suites, this session:

| suite | result |
| --- | --- |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_uma_ops_console.py` | PASS=24 FAIL=0 |
| `test_uma_daily_loop_finish.py` | PASS=47 FAIL=0 |
| `test_uma_blu_daily_close.py` | 71 passed, 0 failed |
| `test_progress_dashboard.py` | 198 passed, 0 failed |
| `test_blocker_explain.py` | PASS=55 FAIL=1. The failure is `issues page keeps Example label`. This pack did not edit that page. |

Listeners after the restart and the suites:

```
Python  15975  127.0.0.1:8787  serve.py
Python  82010  127.0.0.1:8788  scripts/serve_beta.py
```

## FINAL STATE

CLOSED.

The closure test is the authorised file read, no money movement, and the four states kept apart. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The next system row is CAP-FIN-02, which still has to reconcile an ingested file without a payment.

RESULT: PASS
