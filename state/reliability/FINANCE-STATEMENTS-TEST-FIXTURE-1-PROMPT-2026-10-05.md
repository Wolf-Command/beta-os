# FINANCE-STATEMENTS-TEST-FIXTURE-1

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Finance statements test fixture isolation (+ small close-history opening-message visibility fix)

Slice id **FINANCE-STATEMENTS-TEST-FIXTURE-1**. Do NOT name routes, files, tests, or commits with the phrases "daily close" or "daily-close".

## Part A (main) — statements tests must be isolated
`scripts/tests/test_finance_core_statements1_20261005.py` now has **4 errors** (`test_idempotency_and_overlap`, `test_raw_preserved`, and 2 others; run it with `WOLF_TEST_MODE=1 python3 scripts/tests/test_finance_core_statements1_20261005.py`). Cause (verified by Peaches): `setUp` copies the LIVE catalog (`catalog/content_library.sqlite`) into a temp DB, and the real GGV Jan–Jun PDF `account_statement_asof_20260630.pdf` (`GGV_PDF`, line ~41) has since been genuinely imported into live, so the copied import table already holds that `content_sha256` → `core/finance_core_statements.py::import_statement` (~L683-697) correctly raises `ALREADY IMPORTED`.

Fix the TESTS, not the product:
- Tests must never read from or write to live statement folders or the live catalog's statement import rows. Use isolated fixtures: a temp library/statement dir under a `tempfile` dir (or `catalog/backups/tmp-<test>-<pid>/` cleaned up in tearDown), and a temp DB whose statement import/txn tables for the entities under test start empty (e.g. build schema via `ensure_schema` on a fresh temp DB, or delete those rows only in the temp copy). Copy the source PDFs into the temp fixture dir (read-only read of the original is fine) or use a small committed fixture file under `scripts/tests/fixtures/`.
- Keep duplicate detection behaviour UNCHANGED: the test that imports the same bytes twice must still get `ALREADY IMPORTED` (409, `already_imported`) on the second import inside the isolated fixture.
- Do not delete or modify the live GGV import row or any live data. Live DB is read-only (`mode=ro`).
- Run and report: `test_finance_core_statements1_20261005.py` (target 0 errors/0 fail) plus any finance-core suites that share helpers.

## Part B (only if trivial) — "Opening…" message hidden by sticky shell header on `/uma-blu-close`
On iPhone (390 wide), when the history list is scrolled, `#topMsgGlobal` ("Opening 28 September 2026…", set by `setOpeningMsg()` in `dashboards/uma-blu-close.html`) sits under the fixed shell header from `assets/sidenav.js` / `wolf-shell.css` (~310px tall on phone). Make the loading text visible at the point of tap — simplest: also put "Opening…" text inside the tapped `.queue-card` (e.g. replace its action label while `.loading`), restoring on completion/failure. Do not change navigation, read-only/protected behaviour, or any of UMA-HIST-CLOSE-NAV-MOBILE-1/2 behaviour. Keep `test_uma_hist_close_nav_mobile1_20261005.py` (51), `test_uma_hist_close_nav_mobile2_20261005.py` (95), `test_uma_hist_close_queue1_20261005.py` (34) green and add a check for the in-card loading text. If not trivial, skip Part B and say so.

## Hard rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Leave cursor-agent pid 2627 alone. Do not kill processes. No other agents, no cloud agents.
- Protected closes VDC-470e741f, VDC-64f5f529, VDC-8fd544e2 and all 3 Oct / 4 Oct data untouched.
- No commit, push, merge, or clean. staff_ready / human_commissioned stay false. No fabricated data.
- Reload Beta only if Python product code changed (it should not), only with exactly one listener on 8788, via `scripts/beta_restart.py`; else say "no reload needed".

## Result
Write `state/reliability/FINANCE-STATEMENTS-TEST-FIXTURE-1-RESULT-2026-10-05.json`: status, root_cause, files_changed, per-suite pass/fail/errors, part_b done/skipped, live_data_untouched true, prod_pid_unchanged 1297, staff_ready false, human_commissioned false, no_commit true, exit_code.

End cursor log with `RESULT_JSON: <path>` and `EXIT:0` or `EXIT:1`.
