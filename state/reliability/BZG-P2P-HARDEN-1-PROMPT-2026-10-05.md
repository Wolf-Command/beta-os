# BZG-P2P-HARDEN-1 (P0 — OWNER 5 Oct 2026 ~12:55 WITA)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Harden BZG P2P after Breach J1 CLOSED — neutralise legacy copy-seed migrations, close mark-ready precheck read leak, same-person AP-ready vs Ready-to-Pay SoD.

Bounded. staff_ready=false, human_commissioned=false, zayen_ready=false. No commit / push / merge / clean. No money execution / payment.release / payment.approve / vendor.bank.change.

## Source
`state/reliability/BREACH-REPROBE-J1-RESULT-2026-10-05.json` — finding `BREACH-2026-10-05-J1-BZG-P2P-PAY-READY-OVERGRANT` verdict **CLOSED**. Read it before writing. Keep the CLOSED matrix green; this slice closes residual risks called out there, not a re-open of J1.

## Scope (do ONLY this)

### A. Neutralise six legacy P2P copy-seed migrations
Files still containing copy-from-`work.complete` grant seed logic (re-running would reopen the over-grant):
- `scripts/migrations/migrate_bzg_p2p_po1_20261004.py`
- `scripts/migrations/migrate_bzg_p2p_recv1_20261005.py`
- `scripts/migrations/migrate_bzg_p2p_nota1_20261005.py`
- `scripts/migrations/migrate_bzg_p2p_three_way1_20261005.py`
- `scripts/migrations/migrate_bzg_p2p_ap1_20261005.py`
- `scripts/migrations/migrate_bzg_p2p_ready_to_pay1_20261005.py`

Make each **idempotent and safe to re-run**:
- Do **not** delete the migrations or their historical apply records.
- Guard so the copy-seed / `work.complete` grant-copy path **cannot insert or restore** P2P grants. Prefer: early-return with a clear note once grant-repair / explicit `P2P_PERMISSION_MATRIX` is the authority; or delete/disable only the copy-seed block while leaving schema/other idempotent work intact.
- No data loss of business rows (POs, bills, matches, AP-ready history). Grants stay as repaired by `migrate_bzg_p2p_grant_repair1_20261005.py` + `bzg_p2p_grants` matrix.
- A test that imports/runs each migration's main path twice against a catalog copy must leave `bzg.*` / pay-ready grant counts unchanged and must not re-introduce grants copied from `work.complete`.

### B. YELLOW — `bzg-p2p-mark-ready-precheck-read-leak`
`mark_ap_ready` and `mark_ready_to_pay` (see `scripts/core/bzg_ap_ready.py`, `scripts/core/bzg_ready_to_pay.py`) currently return an already-existing AP-ready / Ready-to-Pay row **before** SoD and RBAC checks (idempotent short-circuit). Unauthorised callers (e.g. PERS-HAIKAL) get `ok:true` + document fields (supplier, nota, totals) without marking.

Fix: **permission + SoD checks run BEFORE any existing-row return**. Unauthorised → clean 403 with plain-language refusal (same family as existing `po_creator_cannot_mark_pay_ready` / `nota_recorder_cannot_mark_pay_ready`). Authorised re-call on an already-marked bill may still return the existing row (true idempotent). No new mark row for denials.

### C. Segregation of duties — same person cannot mark both on one bill
J1 SoD covers PO creator and nota recorder only. Extend so the **same person cannot mark both AP-ready and Ready-to-Pay on the same bill** (regardless of role), with a plain-language refusal (no permission codes / technical jargon in the user-facing message). Enforce in the core mark functions (server-side), not UI-only. Historical rows already marked by Matt stay as history — do not rewrite them.

## Tests — `scripts/tests/test_bzg_p2p_harden1_20261005.py`
Canonical-guard isolated catalog copy. No live DB writes from tests.
1. Each of the six migrations re-runnable on a copy without restoring copy-seed grants; grant matrix still matches explicit P2P matrix after re-run.
2. Precheck leak closed: unauthorised person on an already AP-ready / Ready-to-Pay bill → 403, no document payload leak (`ok` false). Authorised person → existing row OK.
3. Same-person both-marks denied: after person A marks AP-ready, person A marking Ready-to-Pay on that bill → deny; a different authorised person may mark Ready-to-Pay (unless blocked by existing PO/nota SoD).
4. Re-run the Breach J1 matrix expectations:
   - Haikal / Misa / Yudi DENY all P2P pay/ap perms × outlets (45/45 style DENY).
   - Iza (PO creator) / Hariyanto (nota recorder) DENY mark on own docs.
   - Zayen ALLOW on others' docs, DENY on own PO/nota.
   - Amanda DENY BZG P2P mark/pay paths.
5. `payment.execute` / `payment.approve` / `vendor.bank.change` grant counts remain 0. Protected closes VDC-470e741f / VDC-64f5f529 unchanged; PETTY-UMA-6D853EEAE0 Rp552,700 unchanged. Prod pid 1297 untouched.

## Rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Reload Beta only at end if Python changed and exactly one listener on 8788; else `RELOAD_HELD`.
- Do not commit/push/merge/clean. Do not kill other processes. Do not start another agent.
- Protected closes / Uma Blu close / petty capture code untouched. No fabricated rows.
- Live DB: sqlite `mode=ro` unless a grant/migration write is required — then backup under `catalog/backups` with sha256 first.
- Do not print process command lines. Do not message staff. Do not mark staff_ready / human_commissioned.

## Output
`state/reliability/BZG-P2P-HARDEN-1-RESULT-2026-10-05.json`: pack, run_id, files_changed, migrations_neutralised, leak_fixed, sod_extended, test_file, tests_pass, tests_fail, j1_matrix_rerun, beta_reloaded/reload_held, beta_listener_pid, prod_pid_unchanged, protected_closes_unchanged, staff_ready=false, human_commissioned=false, status, exit_code.

Last printed line: `RESULT_JSON: state/reliability/BZG-P2P-HARDEN-1-RESULT-2026-10-05.json` (launcher appends `EXIT:N`).
