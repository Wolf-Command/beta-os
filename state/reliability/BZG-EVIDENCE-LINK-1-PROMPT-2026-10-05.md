# BZG-EVIDENCE-LINK-1
Deterministic linkage of the ~1363-1379 unlinked historical BZG evidence files (see state/reliability/BZG-HISTORY-IMPORT-1-RESULT-2026-10-05.json evidence_unlinked and the evidence queue) to imported POs, GRs, notas (supplier_bills), petty rows and bank files.
- High-confidence auto-link only on deterministic keys (exact document number, exact filename/doc id reference, exact supplier+date+amount where unique). Record match rule and confidence per link with provenance.
- Ambiguous or multi-candidate -> reconciliation queue (NEEDS RECONCILIATION) with candidates listed. Never guess. Unmatched stays UNLINKED.
- Imported notas with photo_object_ref=UNKNOWN get a real ref only if a real file is linked; never fabricate.
- Finance desk (from BZG-FINANCE-USABILITY-1) must show the linked evidence on open.
- Tests: counts before/after (mode=ro), every auto-link reproducible from its rule, zero links on ambiguous candidates, no row invented.
Result: state/reliability/BZG-EVIDENCE-LINK-1-RESULT-2026-10-05.json

## Standing rules (all factory slices)
- Single Beta writer. Workspace /Users/wolfterminal/beta-os. Today Mon 5 Oct 2026 Asia/Makassar (WITA).
- Production 127.0.0.1:8787 pid 1297 is SACRED: do not restart or touch.
- Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, via the existing beta restart path; else report RELOAD_HELD.
- Do not commit, push, merge, or clean the dirty tree. Do not kill other processes. Do not start another agent.
- Live Beta DB catalog/content_library.sqlite: read with Python sqlite3 mode=ro; never copy it. Back up under catalog/backups before any write and record sha256.
- Protected: do not mutate closes VDC-470e741f (3 Oct), VDC-64f5f529 (4 Oct); do not submit VDC-8fd544e2 (29 Sep); do not touch PETTY-UMA-6D853EEAE0 (Uma petty balance stays Rp552,700). Do not edit Uma Blu close / daily close or petty capture code.
- No fabricated operational rows, no manufactured matches or links. No payment.execute / payment.approve / vendor.bank.change. No GL/journals/debits/credits/account codes/Reconcile button on captain or staff pages.
- staff_ready=false, human_commissioned=false, zayen_ready=false.
- Do not print process command lines or environment.
- Write the result JSON named below with tests_pass, tests_fail, status (IMPLEMENTATION_DONE or BLOCKED + reason), exit_code, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false. End the log with a single final line EXIT 0 (all pass) or EXIT 1, preceded by RESULT_JSON: <path>.

