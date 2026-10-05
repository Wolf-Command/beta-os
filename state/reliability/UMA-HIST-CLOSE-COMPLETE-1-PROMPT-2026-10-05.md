# UMA-HIST-CLOSE-COMPLETE-1 (OWNER P0 — Owner is testing live on iPhone right now)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Uma Blu historical close — Owner/Finance can complete an INCOMPLETE protected historical close (29 Sep first)

Slice id **UMA-HIST-CLOSE-COMPLETE-1**. Do NOT name routes, files, tests, or commits with the phrases "daily close" or "daily-close".

## Owner human test FAIL (12:47 WITA)
On his iPhone Matt taps 29 Sep on `/uma-blu-close` history (taps now work), it opens, but shows "Protected close — read-only review. No changes will be saved." with Sales Rp13.435.000 / Bills 50 / Cash Rp3.790.000 and "Add the printed shift report." — he CANNOT complete the close.

**Owner order:** "Protected" must NOT stop the Owner from completing an INCOMPLETE historical close. Protected means: protect saved history from unsafe mutation (no overwrite, no duplicate close, no silent auto-resolve) — not "read-only forever".

## Where the block lives (Peaches read-only pointers)
- `scripts/core/uma_hist_close_queue1.py`: `PROTECTED_CLOSE_PREFIXES` (~L50, includes VDC-8fd544e2), `DO_NOT_SUBMIT_PREFIXES` (~L56, includes VDC-8fd544e2), `submit_block_reason()` (~L254: "29 Sep close is protected … do not submit or finalise"), `mutation_block_reason()` (~L280), `_queue_row()` (protected / do_not_submit / action_label / flow).
- `scripts/core/bzg_daily_close.py`: staff submit (~L3750-3770 returns `CANNOT SUBMIT` / `protected_close`), review/readiness (~L4580-4600 sets `submit_enabled=False`, `missing.append("protected_close")`), 29 Sep `OWNER_TYPED_PRINTED_SOURCES` (~L3934).
- `scripts/core/venue_close.py`: `mutation_block_reason` callers in capture (~L933) and declare (~L1222) added by UMA-HIST-CLOSE-NAV-MOBILE-1.
- `dashboards/uma-blu-close.html`: `openQueueDate()` routes `row.protected` → `openDate(iso,{readOnly:true})`; `applyReadOnlyUi()` hides Take photo / Upload photo / Read / Submit / Confirm bank / disables cash.

## REQUIRED BEHAVIOUR
1. Owner (and authorised Finance — use existing RBAC/authz, not email ACL) can CONTINUE an INCOMPLETE historical close, including protected 29 Sep (VDC-8fd544e2) and any other INCOMPLETE date: upload/take printed shift report photo → shift report values → card terminals → cash count → MATCHES / DIFFERENCE shown plainly → petty (that date only) → review → ONE submit.
2. Submit returns exactly ONE result, shown plainly at the top: **CLOSE COMPLETE** / **CLOSE SAVED WITH EXCEPTION** (with the plain reason, e.g. "Cash Rp345.000 short vs warehouse" / "Bills differ by 1") / **CANNOT SUBMIT** (with the one thing missing). 29 Sep's preserved warehouse-vs-printed discrepancy (warehouse cash 4,135,000 / 51 bills vs printed cash 3,790,000 / 50 bills, `auto_resolve` false) must NOT be silently resolved: unless the Owner explicitly resolves it, submit gives CLOSE SAVED WITH EXCEPTION with that discrepancy recorded. No fake CLOSED.
3. Only that business date's frozen/date-specific sources (warehouse snapshot for that date, owner-typed printed values for 29 Sep, that date's petty). Never today's ESB.
4. Append-only: never overwrite or delete existing saved evidence, printed values, captures, or audit rows; new photo/count/submit add new evidence rows + audit events (actor, assurance, before/after state). If a field already has a confirmed value, a new value is recorded as a correction (append) not an overwrite.
5. Idempotent: no duplicate close (same close_id resumed); repeated submit taps → one result, one state transition (server-side guard + client disable-on-tap).
6. **3 Oct (VDC-470e741f) and 4 Oct (VDC-64f5f529) stay READ-ONLY for now** (Owner order) — their rows and all 3 Oct / 4 Oct data must stay byte-unchanged. Keep their review-only screens and server refusals. Peaches hashes them before/after.
7. Non-Owner/non-Finance closers keep existing limits; protected-close completion is Owner/Finance only.
8. Keep the simple phone flow: no internal IDs (`VDC-` must not appear in rendered HTML), no GL/journals/debits/credits/account codes/Reconcile button for closers. Keep all UMA-HIST-CLOSE-NAV-MOBILE-1/2 + FINANCE-STATEMENTS-TEST-FIXTURE-1 behaviour (whole-row links, hidden backlog on open, Back/popstate, in-card "Opening…", no duplicate opens, 3 Sep reachable).
9. The 29 Sep row label in the history list should read CONTINUE (Incomplete) for Owner/Finance, not REVIEW; 3 Oct / 4 Oct stay REVIEW.

## Hard rules
- Production `127.0.0.1:8787` pid **1297** SACRED. Leave cursor-agent pid 2627 alone. Do not kill processes. No other agents, no cloud agents.
- Live Beta DB `catalog/content_library.sqlite`: read-only (`mode=ro`) for you. NEVER submit, declare, upload or capture on the live DB in tests or verification — use temp copies (`catalog/backups/tmp-<name>-<pid>/`, removed in tearDown). Live 29 Sep must stay unchanged until Matt does it himself.
- No commit, push, merge, or clean. staff_ready / human_commissioned stay false. No fabricated data (test photos only in temp copies, clearly marked test).
- Reload Beta at the end only if Python changed, only with exactly one listener on 8788, via `scripts/beta_restart.py`; else RELOAD_HELD with reason.

## Tests
Add `scripts/tests/test_uma_hist_close_complete1_20261005.py` (temp DB copy) proving: Owner can upload photo + declare cash + submit on 29 Sep copy → exactly one result (expected CLOSE SAVED WITH EXCEPTION with the 345,000 / 1-bill discrepancy unless resolved); a second submit is idempotent; existing evidence/printed rows unchanged (append-only, row-hash compare); 3 Oct + 4 Oct row hashes unchanged and their mutations still refused; closer without Owner/Finance cannot complete protected; only 29 Sep sources used; no `VDC-` written to DOM. Run and report: this suite + `test_uma_hist_close_nav_mobile1_20261005.py`, `test_uma_hist_close_nav_mobile2_20261005.py`, `test_uma_hist_close_queue1_20261005.py` (update any assertion that encoded "29 Sep must never submit" to the new Owner order — keep 3/4 Oct assertions).

## Result
Write `state/reliability/UMA-HIST-CLOSE-COMPLETE-1-RESULT-2026-10-05.json`: status, root_cause, files_changed, per-suite pass/fail, beta_pid_before/after or RELOAD_HELD reason, live_29sep_unchanged true, oct3_oct4_unchanged true, prod_pid_unchanged 1297, staff_ready false, human_commissioned false, no_commit true, exit_code.

End cursor log with `RESULT_JSON: <path>` and `EXIT:0` or `EXIT:1`.
