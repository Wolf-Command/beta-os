# FC-ISOLATION-LABELS-SWEEP-1 — Finance access matrix + plain-language sweep; AP and Ready to Pay reachable from Zayen's BZG Finance
Owner order 5 Oct 2026 19:01 WITA — overnight finance queue, PRIORITY 1 (Finance Core → Zayen usable), slice 4 of 4. Bounded slice: aim for 15–40 minutes. Single Beta writer.
Measure first: re-check the gap facts below on live Beta (mode=ro) and in code before changing anything. If a capability already works, prove it in the test and move on — never rebuild what exists.

## Context — build on what exists
FINANCE-SWITCHER-REPAIR-1/2 and FINANCE-UI-HUMAN-LABELS-1 fixed the main finance pages; BZG-P2P-GRANT-REPAIR-1 / BZG-P2P-HARDEN-1 closed BREACH J1. Sub-pages added since (and tonight) have not been swept.

## Scope (only this)
A. Access matrix: enumerate every finance route and API (grep `scripts/serve_beta.py`): `/finance`, `/amg/finance*`, `/amg-finance-ops`, `/bzg/finance*`, `/bzg/uma-blu/{ap,ready-to-pay,bills,evidence,exceptions,pr,purchase-orders}`, `/ggv/finance*`, and anything FC-* slices added tonight. Test as Zayen, Amanda, Matt, and one non-finance staff member. Expected: Zayen AMG+BZG allow / GGV 403; Amanda GGV allow / AMG+BZG 403; Matt all; staff deny. Fix leaks server-side, deny-by-default, no RBAC broadening. Only read the status code of `/uma-blu-close` and petty routes; change nothing there. Save the matrix in the result JSON.
B. Plain-language sweep: visible rendered text (scripts, attributes, comments stripped) of all those pages has no engineering tokens (see hard rules) and no raw enum codes; map codes to plain words in one place.
C. Zayen's BZG Finance navigation reaches AP and Ready to Pay (read views; no Pay button anywhere).

## HARD RULES (Owner order 5 Oct 2026 19:01 WITA — non-negotiable, apply to every step)
- You are the ONLY Beta writer. Workspace `/Users/wolfterminal/beta-os`. Time zone Asia/Makassar (WITA, UTC+8). Do not start another agent; no cloud agents; no paid on-demand.
- Production `127.0.0.1:8787` pid **1297** is SACRED: never restart, signal, reconfigure, or write to it.
- Do NOT commit, push, merge, stash, reset, checkout, or clean the git tree. Delete or archive nothing; preserve every evidence file.
- Never print process command lines (no `ps aux`, `ps -ef`, `ps -o args`, `pgrep -fl`); use `ps -o pid=,comm=` only. Leave cursor-agent pid **2627** alone. Do not kill or signal any process (the only allowed restart is the gated Beta reload below).
- Live DB checks: python `sqlite3.connect("file:...?mode=ro", uri=True)` only. Tests use the in-process harness with an isolated runtime catalog. A live write is allowed only through an idempotent migration/job this slice explicitly needs, after a sqlite backup to `catalog/backups/pre-<slice>-<YYYYMMDD-HHMMSS>.sqlite`; never hand-edit live rows. No fabricated data: if a source does not exist, show an honest empty state.
- Protected closes VDC-470e741f, VDC-64f5f529, VDC-8fd544e2: never mutate or submit. All 3 Oct and 4 Oct 2026 data stays byte-unchanged.
- Do NOT touch Uma Blu Daily Close or Petty Cash code or data tonight (Matt is human-testing them): no edits to uma-blu-close / venue close / petty modules, templates, routes, or tables (`bzg_ops_petty_*`, `venue_daily_close*`, petty evidence). PETTY-UMA-6D853EEAE0 stays Rp552,700; the unresolved Rp2,300 petty difference stays unresolved and visible.
- Money: `payment.execute` stays 0 ALLOW; payment.approve and vendor-bank-change grants stay 0; no bank API, transfer, disbursement, or payment file. Recording only. Segregation of duties kept (and extended where this slice says).
- Entity isolation: Zayen = AMG + BZG allowed, GGV denied (server-side 403); Amanda = GGV only (AMG/BZG 403); Matt = all three. Every route/API you add or change enforces this server-side and is tested.
- Staff/Owner UI never shows internal ids or engineering language (`SCOPE-*`, `ENT-*`, `ROLE-*`, `*_ready` flags, `human_commissioned`, raw enum codes such as `UNPAIRED_INTERNAL_TRANSFER` / `HISTORICAL_UNPAID`, slice ids, "shell", "stub"). Plain business words only; ids may live in data-* attributes, audit, or debug.
- No new major scope. Do only this slice. Do not rebuild Purchase Orders, Recipe Builder, Daily Close, or Petty Cash. ClickUp and Telegram are retired. Do not message Matt, Zayen, Amanda, or anyone.
- `staff_ready=false`, `human_commissioned=false`, `zayen_ready=false` always. The best final state is READY FOR HUMAN TEST.

## Beta reload (only at the very end, only if Python/HTML/JS served by Beta changed)
1. `python3 scripts/build-factory/bf_reload_gate.py` — read-only; prints JSON; exit 0 = allowed, exit 3 = held (Uma close / petty activity in the last 10 min, or not exactly one listener on :8788).
2. Allowed: `python3 scripts/beta_restart.py` (kickstarts net.wolfcommand.serve-beta only). Confirm :8788 is back and pid 1297 still listens on :8787.
3. Held: do NOT reload. Record `reload_held: true` with the gate reasons. Tests run in-process, so the slice can still finish; a later slice or FINANCE-OVERNIGHT-REPROVE-1 reloads.

## Done criteria
- New test file `scripts/tests/test_fc_isolation_labels_sweep1_20261005.py` using the in-process harness (`serve_beta.BetaHandler` on an ephemeral port, `BETA_AUTH_MODE=development_assertion`, `X-Wolf-Subject`, `canonical_guard.isolate_runtime_catalog()`; copy the pattern from `scripts/tests/test_bzg_zayen_finance_prove1_20261005.py` and `scripts/tests/test_finance_ui_human_labels1_20261005.py`). All new tests pass.
- Regressions pass: `test_finance_ui_human_labels1_20261005.py`, `test_finance_switcher_repair2_20261005.py`, `test_bzg_zayen_finance_prove1_20261005.py`, `test_bzg_p2p_harden1_20261005.py`, `test_finance_switcher_repair1_20261005.py`, `test_bzg_p2p_ap1_20261005.py`, `test_bzg_p2p_ready_to_pay1_20261005.py`. Update only assertions that pinned text you intentionally changed, and list them.
- UI changes: rendered-page check at iPhone (390x844) and desktop (1440x900). Prefer real headless Chrome/Playwright screenshots saved under `state/reliability/shots/FC-ISOLATION-LABELS-SWEEP-1/`; otherwise an HTML-render test asserting the key elements, working links, and no fixed-width overflow. Record the method used.
- Evidence/proof JSON `state/reliability/FC-ISOLATION-LABELS-SWEEP-1-RESULT-2026-10-05.json` with: pack, run_id (read `state/build-factory/ACTIVE`), gap_before (what you measured first), files_changed, routes_and_apis, real_record_counts (live DB mode=ro, per entity), data_changes ("none" or migration name + backup path + before/after counts), test_file, tests_pass, tests_fail, regression, render_check, beta_reloaded, reload_held (+ gate reasons), beta_listener_pid, prod_pid_unchanged (1297), protected_closes_unchanged, oct3_oct4_unchanged, petty_and_daily_close_untouched, staff_ready=false, human_commissioned=false, zayen_ready=false, state ("READY FOR HUMAN TEST" when done), status ("IMPLEMENTATION_DONE" or "BLOCKED" + blocker), exit_code.
- If tests fail and you cannot fix them inside this slice, write status "BLOCKED" with the failing test names. The dispatcher reads this file: BLOCKED (or tests_fail>0, or a missing file) triggers one automatic fix slice. Never claim done with failing tests.
- Last printed line: `RESULT_JSON: state/reliability/FC-ISOLATION-LABELS-SWEEP-1-RESULT-2026-10-05.json` (do not print EXIT; the launcher appends it).
