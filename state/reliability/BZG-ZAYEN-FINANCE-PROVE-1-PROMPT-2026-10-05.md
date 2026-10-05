# BZG-ZAYEN-FINANCE-PROVE-1
Prove PERS-ZAYEN access through a real session path (login/session fixture through the app, served HTML + API), not just policy unit calls:
- AMG finance accessible, BZG finance accessible, GGV finance DENIED.
- Make AMG <-> BZG switching obvious on the finance desk (clear entity switcher, current entity named).
- Prove historical BZG records are openable for Zayen (supplier -> PO -> lines -> receipt/nota -> evidence -> recon state) using BZG-FINANCE-USABILITY-1 routes. If any is not openable, report it and keep zayen_ready=false.
- Do not set zayen_ready true; Peaches verifies browser/session later.
Result: state/reliability/BZG-ZAYEN-FINANCE-PROVE-1-RESULT-2026-10-05.json

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

