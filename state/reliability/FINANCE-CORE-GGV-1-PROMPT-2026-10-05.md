# FINANCE-CORE-GGV-1 (P0 — OWNER 5 Oct ~11:16 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Finance Core — GGV first human proving ground (operational desk + nota upload + bank statement upload/recon)

Model: composer-2.5 via factory launcher (`cursor-agent -p --force`). staff_ready=false, human_commissioned=false. No commit, push, merge, or clean.

## Goal
ONE shared Finance Core product; THREE isolated entities GGV / AMG / BZG. Shared code ≠ shared data. This slice makes **GGV** the first human proving ground for Matt:

1. **Nota / receipt upload** (image first → record → extract → draft → Matt confirms → canonical save)
2. **Bank statement upload + reconciliation** (file first → parse txns → idempotent import → propose match only)

After GGV PASS (eng proved), later slices FINANCE-CORE-AMG-PROVE-1 and FINANCE-CORE-BZG-PROVE-1 reuse the SAME core and prove entity config + permissions independently. **No money execution / payment release** in any of these slices.

## Product — Operational GGV Finance page
`/ggv/finance` must be an **operational** desk (not completeness-only), with sections (tabs or nav):

OVERVIEW · BANKING · TRANSACTIONS · RECEIPTS/NOTAS · BILLS · INVOICES · RECONCILIATION · SUPPLIERS · MISSING EVIDENCE · REPORTS · AUDIT

Preserve Beta history (mode=ro verified 2026-10-05): **46 invoices, 33 notas, 605 bills** — openable and searchable. Do not wipe or re-import these.

Reuse / extend existing modules (do not rebuild from scratch):
- `scripts/core/ggv_finance_nota.py` — notas, uploads, vendors; routes under `/ggv/finance` and `/api/ggv/finance`
- `scripts/core/ggv_finance_invoice.py`, `ggv_invoice_history.py`
- `scripts/core/ggv_bank_statement1.py` — FILE_IMPORT_ONLY statement import + propose-only match; originals under `state/ggv-bank-statements/originals`
- `scripts/core/ggv_receipt_intake_ro.py`, `ggv_receipt_accounting1.py`, `fin_recon_shell1.py`, `fin_entity_boards.py`
- Live DB: `catalog/content_library.sqlite` (tables `ggv_invoices`, `ggv_notas`, `ggv_bills`, `ggv_bank_statement_imports`, `ggv_bank_transactions`, …)

Known existing hrefs (extend, do not orphan): `/ggv/finance`, `/ggv/finance/invoices`, `/ggv/finance/notas`, `/ggv/finance/vendors`, `/ggv/finance/customers`, `/ggv/finance/history`, `/ggv/finance/reports`, `/ggv/finance/receipts`.

### Nota upload path (Matt test)
GGV → RECEIPTS/NOTAS → UPLOAD

Pipeline (strict order):
1. Store **original image FIRST** (blob on disk + upload row)
2. Create receipt/nota **record** tied to that evidence
3. Extract → draft fields
4. Matt confirms / edits
5. Canonical save

Fields: merchant, date, amount, tax, currency, payment method, description, nota number, possible category.

Rules:
- **No accounting mapping before evidence is saved.**
- Keep image if extraction fails; offer simple manual entry.
- **Never surface provider/OCR errors to Matt** (friendly copy only).
- Preserve: original extraction, human correction, confirmed fields, who / when / entity / evidence / audit.
- Auto queue states: `NEEDS CODING` / `NEEDS REVIEW` / `UNMATCHED` / `POSSIBLE DUPLICATE` / `MATCHED` / `COMPLETED`.

### Bank statement path (Matt test)
GGV → BANKING → UPLOAD STATEMENT

Pipeline:
1. Original file first (sha256; idempotent — `UNIQUE (entity_id, content_sha256)` already on imports)
2. Parse txns with: date, value date, description, ref, debit, credit, running balance, bank account, statement, import batch, raw+normalized, recon status, audit
3. Idempotent import — **no silent duplicates**; surface `ALREADY IMPORTED` / `POSSIBLE DUPLICATE IMPORT`
4. Auto match vs notas / bills / expenses / invoices / payments / transfers / reimbursements with confidence only: `PROPOSE MATCH` / `HUMAN REVIEW` / `UNMATCHED`
5. **Never fabricate** matches. Propose-only; no auto-post; no Reconcile button on captain pages.

### Business switcher / permissions
- Matt: GGV + AMG + BZG
- Zayen: AMG + BZG; **GGV deny**
- Amanda: GGV per assignment (live: `PERS-AMANDA` → `ASG-AMANDA-GGV-FIN-1` → `POS-GGV-FINANCE-OPERATOR-1` → `ROLE-GGV-FINANCE-OPERATOR` → `SCOPE-GGV-FINANCE`; role holds `PERM-FIN-NOTA-CREATE` / `finance.nota.create`)

Chain must be: **PERSON → ASSIGNMENT → ROLE → ENTITY SCOPE → PERMISSION → RESOURCE ENTITY**. No hardcoded people in new code paths (resolve via org_* tables / rbac).

## Discovery already done (2026-10-05 WITA) — verify, do not assume stale
- Counts mode=ro: ggv_invoices=46, ggv_notas=33, ggv_bills=605, ggv_bank_statement_imports=2, ggv_bank_transactions=6, ggv_nota_files=0, ggv_uploads=0, ggv_receipt_accounting=484
- Amanda GGV finance assignment ACTIVE with nota create on ROLE-GGV-FINANCE-OPERATOR
- Beta http://127.0.0.1:8788/ggv/finance currently returns 403 unauthenticated (expected); prove with authed test client / session fixtures used by existing tests
- BZG usability (BF-75bdba189a90) and bank-recon (BF-2e9a971acc74) already shipped for BZG desk patterns — reuse UX patterns where they fit GGV, keep data isolated to ENT-GGV

## Rules
- Single Beta writer. Production `127.0.0.1:8787` pid **1297** is SACRED — do not restart or touch.
- Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on **8788**, via existing beta restart path; else report `RELOAD_HELD`.
- Do not commit, push, merge, or clean the dirty tree. Do not kill other processes. Do not start another agent.
- Live Beta DB: read with Python sqlite3 `file:...?mode=ro`; never copy `content_library.sqlite`. Back up under `catalog/backups` before any write and record sha256.
- Protected: do not mutate closes VDC-470e741f (3 Oct), VDC-64f5f529 (4 Oct); do not submit VDC-8fd544e2 (29 Sep); do not touch PETTY-UMA-6D853EEAE0 (Uma petty stays Rp552,700). Do not edit Uma Blu close / daily close or petty capture code (Historical Close / Daily Close run in parallel — leave them alone).
- No payment.execute / payment.approve / vendor.bank.change / money movement. No GL/journals/debits/credits/account codes/Reconcile button on captain or staff pages.
- Entity isolation: GGV writes must not appear in AMG/BZG tables and vice versa. Shared helpers OK; shared rows NOT OK.
- staff_ready=false, human_commissioned=false. Do not message Matt. Peaches owns the READY-FOR-MATT block.
- Do not print process command lines or environment.
- Slice id must remain `FINANCE-CORE-GGV-1` (no `daily-close` / `daily close` substring in id or title — rebuild ban).

## Tests (required)
Add `scripts/tests/test_finance_core_ggv1_20261005.py` proving:
1. GGV finance page exposes the operational sections listed above (not completeness-only).
2. History counts: invoices 46, notas 33, bills 605 (mode=ro) and UI/API can open/search at least one of each.
3. Nota upload: original stored before extract; failed extract keeps image + manual path; audit fields present; queue state set; no provider error text in user-facing payload.
4. Bank statement upload: original stored; idempotent re-upload → ALREADY IMPORTED / POSSIBLE DUPLICATE IMPORT; txns have required fields; propose-only match never fabricates; captain HTML has no Reconcile/pay/execute.
5. Permissions: Matt can access GGV finance; Amanda can `finance.nota.create` on GGV via assignment chain; Zayen denied on GGV; no hardcoded person ids in new permission checks.
6. Entity isolation smoke: a GGV nota/import does not write AMG/BZG entity_id rows.
7. Protected closes + petty + prod pid 1297 unchanged.

## Output
Write `state/reliability/FINANCE-CORE-GGV-1-RESULT-2026-10-05.json` with:
pack, run_id (from ACTIVE), routes_added (nota upload URL, bank upload URL, reconciliation URL — absolute beta paths Matt will use),
test_file, tests_pass, tests_fail, counts (desk vs DB),
matt_test_urls: { nota, bank_statement, reconciliation },
beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged,
staff_ready=false, human_commissioned=false,
status (IMPLEMENTATION_DONE or BLOCKED + reason), exit_code.

When IMPLEMENTATION_DONE, also write `state/reliability/PEACHES-GGV-FINANCE-READY-2026-10-05.json` containing exactly this block for Peaches to send (do not message Matt yourself):

```
GGV FINANCE — READY FOR MATT TEST
NOTA TEST: [url]
BANK STATEMENT TEST: [url]
RECONCILIATION: [url]
```

Then the factory should auto-continue AMG/BZG prove slices (already armed with depends_on GGV) without waiting for Matt.

Your last printed line: `RESULT_JSON: state/reliability/FINANCE-CORE-GGV-1-RESULT-2026-10-05.json`
(Do NOT write EXIT yourself; launcher appends it.)
