# P1 CAP-FIN-01 — Wolf Accounting Core — 28 Sep 2026

Pack F6. Beta/local only. This reads the existing finance display and the stored legal entities. It does not start a second ledger. Decision served: owner brief 28 Sep 2026 06:46 WITA, item 5. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 40318 (`scripts/serve_beta.py`). It was not restarted. No route was added. No money, bank, payment, ESB, or NAS write. No journal was read. No book was opened. No balance was typed. No ledger row was raised. No completion row was resolved. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_fin_01_core.py` run through `scripts/tests/run_guarded.py`, plus the existing dashboard-truth suite and the owner-command suite through the same guard. DEPLOYED ROUTE PROOF is the unsigned checks on pid 40318. No accounting-core route was added, so those checks are the existing finance and owner routes. The owner-command suite's owner 200 is its in-process handler. It is not a Cloudflare session on pid 40318, and that suite did not call `read_accounting_core`. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM was not recalculated. The ledger file bytes were unchanged, `CAP-FIN-01` stays BUILT, and the F5 figure 19.65 / 77 = 25.52% was not raised.

The row was taken because it is the next OPEN P1 marked CURSOR CAN CLOSE. `CAP-INTG-07` is still the open P0 in that file. `CAP-GGV-01`, `CAP-GGV-04`, `CAP-CRM-01`, `CAP-HR-01`, `CAP-CORE-12`, `CAP-CORE-11`, and `CAP-FIN-02` are already CLOSED.

## BEFORE

SYSTEM BUILT (0.25). `CR-fd6bf6778c5874ab` is OPEN, blocker `NEEDS_ENGINEERING`. The finance display is UNAVAILABLE. `catalog/fin_mgmt_reporting.sqlite` is absent. No books, journal, or consolidation table is in the catalog. `data/atrium.sqlite` is absent. `data/uncommissioned/atrium.sqlite` is present. That sample was not opened.

## AFTER

The queue row is CLOSED. The ledger stays BUILT. `CR-fd6bf6778c5874ab` stays OPEN. `proven` stays false. `ready` stays false. `staff_ready` stays false. `human_commissioned` stays false. `operating_adoption` stays not measured.

The read is `read_accounting_core`. It opens `catalog/content_library.sqlite` with `mode=ro`. It stats the two Atrium paths and does not pass either path to `sqlite3.connect`. A typed balance, including zero, is refused. A payment argument is refused. An open-books flag is refused. An empty balance string is not a typed balance.

Three stored legal entities were read: `ENT-AMG`, `ENT-BZG`, `ENT-GGV`. Each is `LEGAL_ENTITY` and `LIVE`. Each books source is UNAVAILABLE. No consolidation figure was read. No mapping table is stored, so `mapping_rows` stays null. That is not zero mappings and not a group total. Legal names were not selected.

The finance display stayed UNAVAILABLE. It is not shown as current. It is not commissioned. Unavailable is not cash. The commissioned books file stayed absent. The uncommissioned sample stayed present and was not opened. Its file stat did not change. `journal_count` stays null because no journal was read. A null journal count is not zero journals.

A temp catalog with one fixture entity did not open the sample and did not replace the live entity count. A green read sets `green_test_opens_books` false. Opening the books is still an owner act.

## EVIDENCE

Commit `7af6446`.

The first guarded run of the read passed, PASS=52 FAIL=0. A later assertion treated a comment that names `sqlite3.connect` as a call. One repair excluded comment lines. The repaired run:

```
PASS=56 FAIL=0
EXIT: SUCCESS
NOTE  entities=3 display=UNAVAILABLE books_source=UNAVAILABLE books_opened=False sample_present=True commissioned_present=False cr=OPEN
COUNTS evidence=4 exceptions=3 approvals=9 evidence_status=INVALIDATED fin01_resolved=0
```

The suite log includes `test process refuses canonical Beta write`. That is the guard.

The dashboard-truth suite, through the same guard:

```
PASS=62 FAIL=0
```

The process exit was 0. The suite does not print `EXIT: SUCCESS`.

The owner-command suite, through the same guard:

```
PASS=66 FAIL=0
EXIT: SUCCESS
```

Its log includes `test process refuses canonical Beta write`. The owner 200 in that log is the in-process handler. It is not pid 40318.

A refused balance did not write a book. Evidence stayed 4, exceptions stayed 3, approval decisions stayed 9. `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` stayed `INVALIDATED`. Ledger SHA256 stayed `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-FIN-01` stayed `BUILT`. `CR-fd6bf6778c5874ab` stayed `OPEN`.

Unsigned checks on pid 40318:

| URL | code |
| --- | ---: |
| `GET /api/health` | 200 |
| `GET /api/fin/mgmt-reporting` | 403 |
| `GET /api/owner/command` | 403 |
| `GET /api/owner/command?balance=1` | 403 |
| `GET` with spoofed email | 403 |
| `GET` with `X-Wolf-Subject: PERS-MATT` | 403 |
| `GET` with `Cf-Access-Jwt-Assertion: a.b.c` | 403 |
| `POST /api/fin/mgmt-reporting/books` | 403 |

None of those bodies is an opened book. The public hostname returns 302 to `wolfcommand.cloudflareaccess.com` for `/api/owner/command`. `server: cloudflare`. The login query string was not recorded. `GET /api/health` on `:8787` stayed 200.

Listeners after the suites:

```
15975  serve.py  8787
40318  scripts/serve_beta.py  8788
```

## FINAL STATE

CLOSED.

The closure test is the core read without a typed balance. A green test did not open the books. SYSTEM was not raised. Staff ready, human commissioned, and operating adoption were not set.

## HUMAN NEXT

No sign-in is required for this row. Do not mark anyone commissioned from this file. The books stay unavailable until an owner opens a real source. The next Cursor P1 row is CAP-FIN-03.

RESULT: PASS
