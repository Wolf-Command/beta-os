# BZG-FINANCE-USABILITY-1 (P0)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: BZG Finance desk usability: browse and open imported BZG history

## Goal
Turn the imported BZG history into a usable Finance desk for Zayen (PERS-ZAYEN: AMG YES, BZG YES, GGV NO). Today `https://beta.wolfcommand.net/bzg/finance` is only a completeness GAP/COMPLETE dashboard. Do NOT leave it as a completeness-only dashboard. Zayen must be able to:

1. search suppliers
2. open a supplier
3. open a historical PO
4. see PO lines
5. open a receipt (GR)
6. open a nota (supplier_bill)
7. open linked evidence where available (honest "no evidence linked" otherwise; imported nota photo_object_ref=UNKNOWN must show as missing, not fabricated)
8. see reconciliation state (incl. NEEDS RECONCILIATION rows)
9. browse petty cash history
10. browse bank transactions (honest UNMATCHED / empty is OK)
11. see AP (read-only list)
12. see exceptions (read-only investigation list)

Keep the existing completeness view as a secondary tab/section, not the only content. Reuse existing routes, models, permission checks and templates. Prefer successor routes under `/bzg/finance/...` (e.g. suppliers, suppliers/<id>, po/<id>, receipts/<id>, notas/<id>, petty, bank, ap, exceptions) plus JSON API endpoints the pages use. Phone-usable layout.

## Context (prior slice BZG-HISTORY-IMPORT-1, run BF-c8050a817e81)
- Result: `state/reliability/BZG-HISTORY-IMPORT-1-RESULT-2026-10-05.json`; migration `scripts/migrations/migrate_bzg_history_import1_20261005.py`; tests `scripts/tests/test_bzg_history_import1_20261005.py`. Read these first to learn the table names.
- Live Beta DB: `catalog/content_library.sqlite`. For reads in tests use Python sqlite3 with `file:...?mode=ro` URI. The sqlite3 CLI often fails; do not rely on it. Do NOT copy content_library.sqlite anywhere.
- Counts: PO 543/543 (66 NEEDS RECONCILIATION), PO lines 2017, receipt lines 477 on 104 migrated GR headers (GR headers total 474), notas 473 supplier_bills (photo_object_ref=UNKNOWN), petty 442 imported / 1 unresolved PETTY-HIST-317, evidence queue ~1363-1379 unlinked, bank 15 files months 2026-03..08 only, provenance NEEDS RECONCILIATION ~808 rows.
- zayen_ready is false and stays false in this slice.
- One BZG entity ENT-BZG; outlets (Uma Blu / Rainforest / Pool Bar) are filters, not entities.

## Rules
- Operational staff record; Wolf calculates; Finance accounts. Captain/staff pages: no GL, journals, debits, credits, account codes, or Reconcile button. The Finance desk MAY show reconciliation state for Zayen / Finance roles only.
- Read-only investigation. Do NOT add payment.execute, payment.approve, bzg.pr.payment_approve, vendor.bank.change, or any money movement. No new reconcile/match writes in this slice.
- Permissions: Finance desk views require BZG finance access. Prove PERS-ZAYEN allowed on BZG; prove a GGV-only/content person (e.g. PERS-HAIKAL) is denied. Do not widen grants beyond what is needed for read views; do not reopen BREACH-2026-10-05-J1 (do not grant bzg.ap.mark_ready / bzg.pay.* to new people).
- Do not fabricate operational rows. Do not invent matches or evidence links. Do not write into the imported history tables except via read paths (no data mutation is expected in this slice; if a schema/index addition is truly needed, back up first under catalog/backups and record it).
- Protected: do not mutate closes VDC-470e741f (3 Oct), VDC-64f5f529 (4 Oct); do not submit VDC-8fd544e2 (29 Sep). Do not touch petty row PETTY-UMA-6D853EEAE0 (Uma petty balance must stay Rp552,700). Do not edit Uma Blu close / daily close code or petty capture code. Matt is testing the close in parallel.
- Production (127.0.0.1:8787, pid 1297) is SACRED: do not restart, do not touch.
- Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, using the existing beta restart path. If a reload would not be safe, leave it and report RELOAD_HELD; prove with tests.
- Do not commit, push, merge, or clean the dirty tree. Do not kill other processes. Do not start another cursor/agent.
- Do not print process command lines or environment (an API key can appear there).
- staff_ready=false, human_commissioned=false, zayen_ready=false. Do not describe anything as staff ready.

## Tests (required)
Add `scripts/tests/test_bzg_finance_usability1_20261005.py` (follow the style of existing scripts/tests). Tests run against the live Beta DB read-only (mode=ro counts) plus app/API/UI contract tests (test client or served HTML/JSON), proving:
1. Supplier search returns real imported suppliers; open supplier shows its POs/notas.
2. End-to-end path on a real imported record: search supplier -> open supplier -> open PO -> PO lines (count matches DB) -> receipt and/or nota -> evidence if linked (or honest missing) -> recon state visible.
3. Counts surfaced by the desk equal mode=ro DB counts (PO 543, PO lines 2017, notas 473, petty 442 etc. as actually present).
4. Petty history browse and bank transaction browse exist and return rows or honest empty/UNMATCHED.
5. AP list and exceptions list exist, read-only, no pay/execute actions in HTML.
6. Zayen allowed on BZG finance views; GGV-only person denied; captain pages still contain no GL/journal/debit/credit/account code/Reconcile terms.
7. `/bzg/finance` is no longer completeness-only (navigation to the browse views present).
8. Protected close rows VDC-470e741f and VDC-64f5f529 unchanged (updated_at + declared cash before/after); PETTY-UMA-6D853EEAE0 unchanged; prod pid 1297 still listening.

## Output
Write `state/reliability/BZG-FINANCE-USABILITY-1-RESULT-2026-10-05.json` with: pack, run_id (BF id from state/build-factory/ACTIVE), routes added, test_file, tests_pass, tests_fail, end_to_end_path (ids used), counts (desk vs DB), beta_reloaded / reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false, zayen_ready=false, status (IMPLEMENTATION_DONE or BLOCKED + reason), exit_code (0 if all tests pass, else 1).

Do NOT write any EXIT line yourself; the launcher appends the single final EXIT line from your result JSON. Your last printed line should be `RESULT_JSON: state/reliability/BZG-FINANCE-USABILITY-1-RESULT-2026-10-05.json`.
