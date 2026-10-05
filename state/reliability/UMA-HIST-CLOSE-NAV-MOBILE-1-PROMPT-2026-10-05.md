# UMA-HIST-CLOSE-NAV-MOBILE-1 (OWNER P0 — Owner is actively testing on iPhone)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Uma Blu historical close list — mobile tap navigation repair (history rows open the right close on iPhone)

Slice id is **UMA-HIST-CLOSE-NAV-MOBILE-1**. Do NOT name routes, files, tests, or commits with the phrases "daily close" or "daily-close". Use e.g. `scripts/tests/test_uma_hist_close_nav_mobile1_20261005.py`.

## Owner human test FAIL (5 Oct 2026 12:14 WITA)
On Matt's iPhone, the HISTORICAL / MISSING CLOSES list on `/uma-blu-close` (built by UMA-HIST-CLOSE-QUEUE-1, BF-e4d931b0a032) renders correctly, but tapping the status buttons "does nothing".

## Diagnosis already done (Peaches, read-only) — confirm, then fix
Files: `dashboards/uma-blu-close.html` (queue render `loadOwnerQueue()` ~L285, `openQueueDate()` ~L311, `openDate()` ~L448, `showScreen()` ~L402, back buttons ~L707-711), `scripts/core/uma_hist_close_queue1.py` (`_queue_row`, `owner_history_queue`), `scripts/core/bzg_daily_close.py` (`close_date_register` ~L4658), `scripts/core/venue_close.py` (`open_or_get` ~L589), serve_beta routes `/api/venue-close/history-queue`, `/api/venue-close/by-date`, `/api/venue-close/open`, `/api/venue-close/capture`.

ROOT CAUSE (proved): the tap handler DOES fire — `core_audit_events` shows PERS-MATT (cloudflare_access_verified) taps at 12:05:49 WITA (opened+captured 13 Sep, VDC-191144ca…) and 12:06:24 WITA (opened+captured 27 Sep, VDC-667e795b…). But `#ownerQueuePanel` and `#todayPanel` are NOT `.wiz-screen`, so `showScreen()` never hides them: after a tap the backlog list and "Tonight" panel stay on top, `#wizCalendar` is hidden, and the opened close (`#wizIntro` / `#wizExceptionSummary`) renders BELOW the fold with no scroll; any error/"Protected date" message goes to `#msg` at the very bottom of the page. On a 390x844 phone the screen looks unchanged → "buttons do not work". Secondary defects: rows print internal close IDs (`VDC-…`) in the list and the exception screen; the tap target is a small pill button, not the row; no pressed/loading state; no client disable-on-tap (rapid taps can fire concurrent `/open` POSTs); Back buttons don't use browser history; protected INCOMPLETE dates (29 Sep, 4 Oct) open the editable wizard instead of read-only review.

Confirm by rendering at iPhone viewport before you change anything (Playwright webkit "iPhone 14" is installed in venv `~/pw-venv-histclose/bin/python`; or follow the in-process pattern in `scripts/audit/bzgclose_ux_photo1_shots.py`, which runs `serve_beta` in-process with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject` / `Cf-Access-Authenticated-User-Email` headers). Note `WOLF_TEST_MODE=1` refuses writes to the live catalog DB; for tests use a temp DB copy under the beta-os tree as existing tests do.

## REQUIRED BEHAVIOUR (implement all)
1. Tap OPEN → opens that business date's close. Tap INCOMPLETE → resumes that exact saved close from existing state (same close_id, no new row). Tap EXCEPTION → opens that exact close with its unresolved exception/review state (3 Oct: Rp125,000 difference, cash Rp3,225,000 vs expected Rp3,350,000 — read from the record, do not hardcode).
2. Protected = protect historical record from unsafe mutation; it must NOT block Owner from opening/viewing. Protected closes (VDC-470e741f 3 Oct, VDC-64f5f529 4 Oct, VDC-8fd544e2 29 Sep) open read-only / review mode with NO mutation: no `/open` POST, no `/capture`, no take, no declare, no submit. Client must not call mutating endpoints for protected rows, and server must refuse mutation of protected closes (keep/extend existing submit guards).
3. No duplicate closes on repeated taps: server idempotent by business date (keep `open_or_get` idempotent; make it race-safe for concurrent requests, e.g. `BEGIN IMMEDIATE` around the get-then-insert — no destructive migration) + client disable-on-tap / in-flight guard.
4. Historical close never pulls today's ESB; each date uses its frozen/date-specific sources. Verify `capture` for a historical date reads only that business date (add a test).
5. REMOVE internal IDs (e.g. `VDC-8fd544e2-2132-…`) from staff/owner UI; keep them only in audit/debug views (e.g. a collapsed owner-only "Audit details" or API JSON). Rows read e.g. "29 September 2026 · Incomplete · Protected" or "3 October 2026 · Exception · Rp125,000 difference" with an obvious action word: CONTINUE (incomplete) / REVIEW (exception or protected) / OPEN (open/missing).
6. WHOLE row/card tappable as a real link (`<a href="/uma-blu-close?business_date=YYYY-MM-DD">` progressively enhanced, or a full-width `<button>`), min 44px touch target, `touch-action: manipulation`, immediate pressed/loading feedback ("Opening 29 September…"), no double-tap duplicate state.
7. When a date opens: hide the backlog list, Tonight panel and All-dates panel; scroll to top; show the opened date heading + status at the top; show any error/protected message inline at the top of the opened screen (not only at page bottom). Use `history.pushState` (or hash route) so the iPhone/browser Back gesture AND the on-screen "← Back to history" button return to the history list (handle `popstate`; deep link `?business_date=` still works on load).
8. Authorised Owner/Finance can select/open older dates including 3 Sep 2026 (date search + list, and deep link `?business_date=2026-09-03`). Server already lists 3 Sep (MISSING) from `close_date_register`; make sure the UI path to it is reachable on phone (search input accepts 2026-09-03 and also "3 Sep"; consider a native `<input type="date">` with no min restriction for authorised roles) and that the opened screen is visible (same root cause). Respect role authz — closers without Owner/Finance rights keep existing limits.
9. Keep the simple phone flow rules: no GL/journals/debits/credits/account codes/internal IDs/Reconcile button for closers.

## Hard rules
- Single Beta writer. Production `127.0.0.1:8787` pid **1297** is SACRED: never restart/touch. Leave cursor-agent pid 2627 alone. Do not kill any process. Do not start another agent. No cloud agents, no paid on-demand.
- Live Beta DB `catalog/content_library.sqlite`: read with Python sqlite3 `file:...?mode=ro`. Do NOT write rows to the live DB from tests. Do NOT mutate protected closes VDC-470e741f, VDC-64f5f529, VDC-8fd544e2, or ANY 3 Oct / 4 Oct data (closes, edc/till/esb receipts, vision events, petty). Peaches has hashed them before your run and will re-hash after.
- Do not create closes for any date as part of your verification on the live DB (use a temp copy). No fabricated data.
- No commit, push, merge, or clean of the dirty tree.
- Never mark staff_ready or human_commissioned true.
- Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, via `scripts/beta_restart.py` (LaunchAgent kickstart); else RELOAD_HELD with reason. HTML-only changes are served from disk.
- Do not rebuild Purchase Orders, Recipe Builder, Petty Cash, or the close wizard itself; this is a navigation/visibility/read-only-mode repair around the existing surface.

## Tests (must pass)
Add `scripts/tests/test_uma_hist_close_nav_mobile1_20261005.py` proving at least:
1. Queue HTML/JS: each history row is a whole-row link/button with href or data-date, min-height ≥44px, `touch-action: manipulation`, no `VDC-` text rendered into row markup.
2. Opening a date hides `#ownerQueuePanel`, `#todayPanel`, `#wizCalendar` and scrolls to top (static check of JS or jsdom-free string/AST checks are fine; Playwright optional).
3. Protected rows (29 Sep, 3 Oct, 4 Oct) route to read-only review: client does not call `/api/venue-close/open`, `/capture`, `/till-declare`, `/staff-submit` for them; server refuses submit/declare/capture on protected close ids.
4. `open_or_get` concurrent double call for the same date (temp DB) yields exactly one non-cancelled row.
5. Exception review payload for 3 Oct returns difference 125000, cash 3225000, expected 3350000 from the record (temp DB copy), without mutation.
6. 3 Sep 2026 appears in date register search and deep link resolves for Owner identity.
7. Historical capture uses only that business date's ESB (no today rows).
8. Prior suites still pass: `scripts/tests/test_uma_hist_close_queue1_20261005.py` and any uma-blu-close tests you touch.
9. Prod pid 1297 unchanged.

## Result
Write `state/reliability/UMA-HIST-CLOSE-NAV-MOBILE-1-RESULT-2026-10-05.json` with: status IMPLEMENTATION_DONE or BLOCKED + reason; root_cause (one sentence); files_changed; tests_pass / tests_fail (all suites run); one_owner_link (`https://beta.wolfcommand.net/uma-blu-close#history-queue` or successor); beta_pid_before/after; beta_reloaded or RELOAD_HELD reason; protected_closes_unchanged true; prod_pid_unchanged 1297; staff_ready false; human_commissioned false; no_commit true; exit_code.

End cursor log with `RESULT_JSON: <path>` and `EXIT:0` or `EXIT:1`.
