# Uma Blu petty cash surface — one real OUT — 4 Oct 2026

You are editing ONLY /Users/wolfterminal/beta-os.

This slice makes the running staff page able to record one real petty-cash OUT. Finish that, then stop. Do not invent a second petty system, a second ledger, or a second recorder.

## What is wrong now

`dashboards/bzg-uma-blu-petty.html` (route `/bzg/uma-blu/petty`) is older than the recorder. It still shows an In button, and its write posts `operator`, `direction`, `amount`, `purpose`, `category`, `outlet`, `logged_by`, `evidence_id`, `receipt_path`, and `currency`. It does not post an accounting mapping. `record_petty_ops` in `scripts/core/uma_ops_console.py` rejects that write with `missing_accounting_code`. The server route is `_uma_ops_petty_post` in `scripts/serve_beta.py`.

OUT is already allowed by capability `petty_cash.record_out` on Floor Captain, Head of F&B, BZG F&B Operations Lead, and Owner. There is no record-in permission. Keep that. Do not hardcode Iza or any email address or person id.

## Staff page

Hospitality language only. OUT only. Remove the In control completely, including the button, the hidden direction that can be set to IN, and any script path that can post IN. A captain must not be able to post IN from this page.

Fields a captain can fill:

- Business: Uma Blu / BZG, shown as that name. Not a typed internal id.
- Outlet: the outlet name they already pick. Not an internal id.
- Business date.
- Time.
- Amount.
- Category.
- Reason.
- Payee (blank only when there is no payee).
- Person: the signed-in assignment, shown as a name, not a typed email and not a free-text box. If there is no signed-in assignment, do not post.
- Receipt: a real photo when they have one.

Accounting mapping is chosen from existing real codes already stored for this business. Send that chosen code with the write (`accounting_code` on the existing `record_petty_ops` call). Do not invent a code. Do not seed a code. Do not hardcode a code into the page. If no real code exists, the page says it cannot be saved yet and does not post.

A missing receipt becomes an evidence exception, using the recorder's existing exception / incomplete-proof status. It is not a silent save that looks complete, and it is not a fake photo or a made-up evidence id. Say in plain language that the receipt is missing and the movement is an evidence exception. When a real receipt photo is attached, keep attaching that real photo.

Same-day OUT must flow into expected closing cash without a second entry. Use the existing `cash_reconciliation_with_petty` path in `scripts/core/bzg_daily_close.py`. Do not create a second ledger, a second movement table, or a second write from the close page. One OUT is counted once.

Audit stays server-side inside the existing recorder audit. No internal ids on screen: no movement ids, evidence ids, person ids, entity ids, or raw accounting-code keys as labels. Staff see amount, reason, category, outlet, date, time, payee, and whether the receipt is attached or missing.

Gate the form on `petty_cash.record_out`. If that capability is absent, hide the form. Do not show a dead In control. Do not set `BETA_AUTH_MODE`.

## Do not touch

- Do not read, write, or open close VDC-470e741f-d889-437a-9a40-1ec9c083fb95.
- Tests use a tiny temporary sqlite created by the existing schema helper. NEVER copy `catalog/content_library.sqlite`. NEVER shutil.copy2, vacuum, or backup that file. NEVER write `catalog/backups`. NEVER write the live catalog. If a test would require that copy, stop and write the result as BLOCKED_DISK with no copy made.
- Do not restart or reload Beta. Do not signal Beta pid 42835. Do not signal production pid 15975. Do not reload either process.
- Leave pid 63443 alone.
- Do not commit, push, merge, reset, stash, or clean.
- Do not put secrets or process command lines in any file.

## Done

py_compile Python you edit. Run one new or existing temp-sqlite test that proves: the page cannot post IN; a write without a real accounting code is refused; a chosen existing code is sent and accepted; a missing receipt is an evidence exception and not a fake photo; one same-day OUT is included once by `cash_reconciliation_with_petty` in expected closing cash. Do not claim a person commissioned the page.

Write `state/reliability/PETTY-SURFACE-RESULT-2026-10-04.md` with files changed, what staff now see, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE, BLOCKED, or BLOCKED_DISK.

Stop when that result file is written.
