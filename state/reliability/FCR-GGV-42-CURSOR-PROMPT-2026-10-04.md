# FCR-GGV-42 — GGV receipt confirm form, optional tax field

You are the engineer for this one slice. Workspace is the existing dirty tree at `/Users/wolfterminal/beta-os`.

## Do not
- Do not commit. Do not push. Do not start a worktree.
- Do not edit anything except `dashboards/ggv-finance.html` and, if needed, one new temp-db test.
- Do not edit `serve_beta.py`. The API `POST /api/ggv/finance/accounting/receipts/{key}/confirm` already stores tax only when the body sends it.
- Do not invent a tax amount. Do not add currency. Do not add invoices or notas.
- Do not hardcode Amanda's email or person id. Amanda is the operator; the form is staff-facing only.
- Do not `shutil.copy2` (or otherwise copy) the live `catalog/content_library.sqlite`. Use a schema-only or tiny temp sqlite. If the test cannot run without that copy, stop and write `BLOCKED_DISK` in the result file. Do not copy.
- Do not write the live catalog. Do not load any chart into `catalog/atrium-bzg.sqlite`.
- Do not touch close `VDC-470e741f`. Do not write the protected close.
- Do not reload Beta. Do not kill pid 47590 or pid 15975. Do not signal either listener.
- Do not print process command lines, tokens, or emails.

## Change
The GGV receipt confirm form currently posts vendor, amount, date, category, account, and notes.

Add an optional tax input in staff language. Label it `Tax`.

- Blank or omitted must store null, never 0.
- A supplied tax value is sent with the existing confirm POST so the API can store it.
- No other product change.

## Test
One new temp-db test only if needed to prove blank or omitted tax stores null and a supplied tax is stored. Schema-only or tiny temp sqlite. No copy of `catalog/content_library.sqlite`.

## Result
Write `/Users/wolfterminal/beta-os/state/reliability/FCR-GGV-42-RESULT-2026-10-04.md` with:
- status
- pass/fail counts
- whether Beta was reloaded (must be no)

Stop when that result file is written.
