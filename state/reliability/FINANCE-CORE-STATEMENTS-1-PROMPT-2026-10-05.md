# FINANCE-CORE-STATEMENTS-1 (P0 — OWNER 5 Oct 2026 11:34 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Finance Core shared BANK STATEMENT LIBRARY + UPLOAD for every entity (GGV first, then AMG, BZG)

ONE shared Finance Core capability. NOT per-entity importers. Shared code ≠ shared data. Entities GGV / AMG / BZG stay isolated.
staff_ready=false, human_commissioned=false. No commit / push / merge / clean. No money execution / payment release.

## Context (verified read-only 5 Oct 11:30–11:40 WITA by Peaches verify)
- FINANCE-CORE-GGV-1 (BF-a4fa599323e0) and FINANCE-CORE-AMG-PROVE-1 (BF-8b4c355ea62f) are IMPLEMENTATION_DONE. Read their RESULT JSONs and `scripts/core/ggv_finance_desk.py`, `scripts/core/ggv_bank_statement1.py`, `scripts/core/ggv_finance_nota.py`, the AMG prove changes (entity config `_fce.entity_config(...)["bank_originals"]`), `scripts/core/bzg_bank_recon1.py`, `scripts/core/bzg_finance_usability_ro.py` before writing code. Extend the shared core; do not fork per entity.
- Live Beta DB `catalog/content_library.sqlite`: tables `ggv_bank_statement_imports` (2 rows), `ggv_bank_transactions` (6), `bzg_bank_statement_imports` (15), `bzg_bank_transactions` (1257). Read with Python sqlite3 `file:...?mode=ro`. Back up under `catalog/backups` (sha256 recorded) before ANY write.
- **The 2 GGV imports (GBSI-cf68360b…, GBSI-2608830d…, filename `ggv-prove-statement.csv`, txns "Prove coffee receipt"/"Client transfer" + one blank UNIDENTIFIED row each) are 3 Oct prove/test fixtures, NOT real bank statements.** They must NOT appear in the GGV statement library as real history. Mark them `TEST_FIXTURE` (hidden from library/recon/completeness) via a backed-up, audited flag — do not delete rows.
- Test-fixture leak: GGV-1 and AMG-prove tests wrote fixture originals into LIVE `state/ggv-bank-statements/originals` and `state/amg-bank-statements/originals` (e.g. `*__fc1-ggv-statement.csv`, `*__amg-fc1-statement.csv`, `*__amg-idem.csv`). Fix the tests so originals go to a temp dir (patch `_originals_dir` / entity config in setUp). Do not count leaked fixture files as historical statements. Do not delete them; list them in the result under `fixture_files_ignored`.
- Defect to fix: `/api/ggv/finance/desk`, `/api/ggv/finance/reconciliation`, `/api/ggv/finance/audit` raise uncaught `GgvFinanceDeskError` for a denied person (PERS-ZAYEN) → connection dropped instead of clean JSON 403. Map to a clean 403 JSON `{ok:false,error:"forbidden"}` for every entity's desk APIs (check AMG equivalents too).
- Duplicate detection today is filename-based ("same filename, different content" → POSSIBLE DUPLICATE IMPORT). That is wrong for real banks (a different month can share a filename; an overlapping statement can have a different filename). Replace with signature-based detection (below).
- Parser today is CSV-only (Mandiri semicolon CSV / BRI IBIZ CSV / generic CSV). Real statements include PDFs and BNI .xls (BZG BNI 5 files are parse EXCEPTION, 0 txns). `pdftotext` exists at `/opt/homebrew/bin/pdftotext`.

## Authorised historical statement stores (real files — register these; NEVER synthesise)
Build the historical registry ONLY from these files. Dedupe across stores by content sha256 (the same BZG files exist in 3–4 places).

**GGV — Mandiri 1610015100972 (GOSS GROUP VENTURES)**
- `~/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/GGV/Mandiri-1610015100972/account_statement_asof_20260630.pdf` — Livin' Mandiri PDF, Period 01 Jan 2026 – 30 Jun 2026, has Opening/Closing Balance (multi-month)
- `.../Acc_Statement_1610015100972_2026-05-01_2026-05-31_20260603180944.csv` — May 2026 (overlaps the PDF)
- `.../Acc_Statement_1610015100972_2026-07-01_2026-08-31_matthew-drop-20260905.csv` — Jul–Aug 2026
- `.../ggv_jan_jun_ledger_export.txt` — text ledger export, NOT a bank statement: do not import as a statement (may show as supporting evidence only)
- Same files also under `~/.openclaw/state/bank/_sources/GGV/` (dedupe by hash).
- Matt will personally upload **Jun 2026** and **Sep 2026** Mandiri statements through the UI. Do NOT seed or synthesise them. Note: Jun 2026 transactions are already inside the Jan–Jun PDF; Matt's Jun upload must therefore land on the POSSIBLE DUPLICATE IMPORT (overlap) path and must never create duplicate transactions.

**AMG — CIMB Niaga, 5 accounts** (store: `~/.openclaw/workspace/wolf-system/atrium/statements/`, index `atrium/archive/parsed.json` + `parsed-aug-2026-from-matt.json`)
- 800203739400 (CKM / Cipta Karya), 800203720100 (PPL / Pasir Putih), 800203718200 (FRJ / Fortuna Rinjani), 800203745100 (KAS / Karya Anak Sasak), 800203774400 (PLI / Pesona Lombok)
- e-statement PDFs Dec 2025 → Jun 2026 and Aug 2026 per account; Jul 2026 only as "*_juli.pdf" scans + OCTO transaction-inquiry scans (mark evidence quality accordingly, not a formal e-statement); FRJ 800203718200 has no Apr 2026 file; Sep 2026 missing for all. Some files are byte-duplicates (e.g. AUG_* vs *-2026-08-CIMB-E-Statement.pdf) — dedupe by hash.
- Map these to ENT-AMG only if the existing entity/company config says these PTs belong to AMG; if mapping is ambiguous, register them as `NEEDS ENTITY CONFIRMATION` and report — never guess.
- `state/shareholder-bank-statements/AMG/` is an empty scaffold.

**BZG** (already in Beta: `state/bzg-bank-statements/originals/` + `bzg_bank_statement_imports`)
- Mandiri 1610555335558: Mar, Apr, May, Jun 2026 + Jul–Aug 2026 combined (5 files)
- BRI 19101003489305: Apr–Aug 2026 (5 files)
- BNI 2177177110: Apr–Aug 2026 (5 .xls, currently parse EXCEPTION / 0 txns — parse if the format allows, else keep as evidence with honest PARSE FAILED)
- Extra BNI originals in `~/.openclaw/state/bank/_sources/BZG/` ("Account Statement_Download Single_*.xls", "Account Statement_2177177110_2026-07/08_*.xls") — dedupe by hash; register only if they are distinct real statements. `account_balances_*.xlsx` is not a statement.
- Gaps: Sep 2026 all accounts; Mar 2026 BRI/BNI.

Do not import from Telegram, mail, or any other source. Uploads are permanent accounting evidence (not temp files).

## Product spec
1. Finance nav for EVERY entity: **BANKING → BANK STATEMENTS**. Obvious **UPLOAD STATEMENT** button at top.
2. **Library** for the selected entity (assignment-scoped): bank, account (masked OK, e.g. ••••0972), period, opening balance, closing balance, txn count, reconciliation status, evidence status, **OPEN**. No filesystem paths, no technical import IDs in UI.
3. **Month completeness strip per account**, from real records only: e.g. `JUN RECONCILED` / `SEP MISSING STATEMENT` / `OCT CURRENT`. Missing statement ≠ zero activity. Multi-month files (Jan–Jun PDF, Jul–Aug CSV) cover each month they span.
4. **Statement OPEN view**: original file retrievable (download through an authorised route, never a raw path), parsed transactions (raw + normalized), reconciliation state, matches, exceptions, audit trail.
5. **Duplicate handling** (signature based: entity + bank + account + period + file sha256 + transaction signatures (date, amount, direction, normalised description/ref, running balance)):
   - exact same file → **ALREADY IMPORTED** with a link to the existing statement; zero new rows.
   - partial overlap → **POSSIBLE DUPLICATE IMPORT**: show overlapping period/txn count; never create a second set of the overlapping txns. Keep the original file as evidence. A human may confirm importing only the non-overlapping txns (audited).
   - same filename but different period/account and no txn overlap → normal import (not a duplicate).
6. **Upload** recognises bank, account, period, opening/closing balances; parses txns; lands in library + Banking; triggers auto-recon proposals (`PROPOSE MATCH` / `HUMAN REVIEW` / `UNMATCHED`, never fabricated, never auto-posted); state persists across refresh. If parse fails: keep the original, show a friendly message, statement shows `PARSE FAILED — ORIGINAL KEPT` (no provider/stack errors to the user).
7. **Formats**: Mandiri semicolon CSV (`AccountNo;Ccy;PostDate;Remarks;AdditionalDesc;Credit Amount;Debit Amount;Close Balance`), Mandiri Livin' PDF ("Account Statement / Period / Opening Balance / Closing Balance / Posting Date / Effective Date"), BRI IBIZ CSV, CIMB e-statement PDF, BNI xls (best effort). Use the real files above as parser fixtures in tests (read-only, copied to temp), not synthetic look-alikes of Matt's Jun/Sep files.
8. **GGV Finance home** must visibly show four primary actions: **UPLOAD STATEMENT**, **UPLOAD NOTA / RECEIPT**, **HISTORICAL STATEMENTS**, **RECONCILIATION**.
9. **Permissions** strictly PERSON → ASSIGNMENT → ROLE → ENTITY SCOPE → PERMISSION → RESOURCE ENTITY (rbac / org_* tables; no hardcoded person ids): Matt GGV+AMG+BZG allow; Zayen AMG+BZG allow, **GGV deny server-side (clean 403)**; Amanda GGV only. A statement/transaction/original-file request for another entity's record returns 403/404 even with a guessed id.
10. **Commissioning queue cards** (add to `scripts/core/owner_commissioning_queue.py` seed templates, status READY_TO_TEST, never COMMISSIONED):
    - `HUMAN TEST — MATT — GGV FINANCE` (business GGV, person_to_test Matt, audience NEEDS_MATT, open_href /ggv/finance)
    - `HUMAN TEST — ZAYEN — AMG FINANCE` (business AMG, person_to_test Zayen, audience NEEDS_STAFF, open_href /amg/finance)
    - `HUMAN TEST — ZAYEN — BZG FINANCE` (business BZG, person_to_test Zayen, audience NEEDS_STAFF, open_href /bzg/finance)
    AMG/BZG cards must NOT appear in Matt's (NEEDS_MATT) queue. Ownership record: `state/completion-register/finance-core-human-test-ownership-20261005.json`.

## Rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, via the existing beta restart path; else `RELOAD_HELD`.
- Do not commit/push/merge/clean. Do not kill other processes. Do not start another agent. Leave cursor-agent pid 2627 alone.
- Protected: closes VDC-470e741f, VDC-64f5f529 untouched; do not submit VDC-8fd544e2; do not touch PETTY-UMA-6D853EEAE0 (Rp552,700). Do not edit Uma Blu close / daily close / petty capture code. Historical Close and the factory keep running.
- No fabricated rows, matches, statements, or months. No payment.execute / payment.approve / vendor.bank.change. No GL/journal/Reconcile button on captain/staff pages.
- Do not print process command lines or environment.
- Do not message Matt or Zayen. Peaches owns the READY block.

## Tests (required) — `scripts/tests/test_finance_core_statements1_20261005.py`
All write-tests on a temp catalog copy (canonical_guard isolation) AND temp originals dir (no writes into live `state/*-bank-statements/originals`).
1. Library per entity lists only that entity's real statements; GGV prove fixtures hidden; counts/months match the registry above.
2. Isolation: GGV statements never visible to AMG/BZG scope and vice versa (list, open, original download, txn APIs) — including guessed ids.
3. Idempotency: same file twice → ALREADY IMPORTED + link, zero new txns; overlapping file (e.g. real GGV May CSV after the Jan–Jun PDF) → POSSIBLE DUPLICATE IMPORT, zero duplicate txns; same filename different content/period without overlap → imports normally.
4. Raw preserved: original bytes sha256 retrievable; raw + normalized txn fields stored.
5. Parsers: real Mandiri CSV, Mandiri PDF, BRI CSV, CIMB PDF parse (bank, account, period, opening/closing where present); BNI xls parses or honest PARSE FAILED with original kept.
6. Completeness strip: real months only; missing months show MISSING STATEMENT, never zero.
7. Permissions: Matt allow all three; Zayen AMG/BZG allow, GGV clean 403 on pages AND desk/recon/audit/statement APIs; Amanda GGV allow, AMG/BZG deny.
8. GGV home shows UPLOAD STATEMENT, UPLOAD NOTA / RECEIPT, HISTORICAL STATEMENTS, RECONCILIATION.
9. GGV-1 history counts unchanged (invoices 46 / notas 33 / bills 605); protected closes/petty/prod pid unchanged.
10. Re-run `test_finance_core_ggv1_20261005.py` and the AMG prove tests — still pass, now without leaking fixtures into live originals.

## Output
`state/reliability/FINANCE-CORE-STATEMENTS-1-RESULT-2026-10-05.json`: pack, run_id (from ACTIVE), routes_added, test_file, tests_pass, tests_fail, registry (per entity: account → months covered / missing / statement count / parse status), fixture_files_ignored, ggv_prove_fixtures_flagged, beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false, status (IMPLEMENTATION_DONE or BLOCKED + reason), exit_code.

When IMPLEMENTATION_DONE also (re)write `state/reliability/PEACHES-GGV-FINANCE-READY-2026-10-05.json` with public links (https://beta.wolfcommand.net/...):
```
GGV FINANCE — READY FOR MATT TEST
NOTA TEST: https://beta.wolfcommand.net/ggv/finance/notas
BANK STATEMENT TEST: https://beta.wolfcommand.net/ggv/finance/banking  (or the new BANK STATEMENTS route)
RECONCILIATION: https://beta.wolfcommand.net/ggv/finance/reconciliation
HISTORICAL STATEMENTS: <route>
```

Last printed line: `RESULT_JSON: state/reliability/FINANCE-CORE-STATEMENTS-1-RESULT-2026-10-05.json` (do NOT print an EXIT line; the launcher appends `EXIT:N`).
