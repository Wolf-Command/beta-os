# UMA-HIST-CLOSE-NAV-MOBILE-2 (OWNER P0 — bounded fix cycle 1 of 2 after rendered iPhone proof)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Uma Blu historical close list — remove remaining internal ref from owner page + tap feedback polish

Slice id **UMA-HIST-CLOSE-NAV-MOBILE-2**. Do NOT name routes, files, tests, or commits with the phrases "daily close" or "daily-close".

## Context
UMA-HIST-CLOSE-NAV-MOBILE-1 (BF-ba91f44026f9) shipped the iPhone navigation repair in `dashboards/uma-blu-close.html` + `scripts/core/uma_hist_close_queue1.py` + `scripts/core/venue_close.py` + `scripts/serve_beta.py`. Peaches rendered it with Playwright webkit "iPhone 14" (real tap()) and it PASSES: whole-row links, backlog hides, opened date visible at top, protected 29 Sep / 3 Oct / 4 Oct open read-only with zero POSTs, rapid taps create no duplicates, Back button + browser back return to history, 3 Sep opens via search and deep link, each date uses its own warehouse source.

Remaining FAILS from the rendered proof (fix ONLY these, do not refactor anything else):
1. **Internal ID still in owner page DOM.** On the 3 Oct exception screen, `showExceptionSummary()` writes `"Close ref: " + row.close_id` (`VDC-470e741f-…`) into `#exceptionAuditBody` inside `<details id="exceptionAudit">Audit details (owner)`. Requirement: NO `VDC-` string anywhere in rendered owner/staff HTML (DOM, not just visible text). Remove the close ref (and any other `VDC-` / close_id text) from every rendered element on `/uma-blu-close` — list, intro/wizard, exception, closed, evidence, review, messages, data attributes, hrefs, alt/title attributes. Keep IDs only in API JSON / server audit logs. If you keep an owner "Audit details" affordance, it must link to an existing audit/debug view (not render the id on this page), or simply drop it. Error messages from the API that might contain a close id must be sanitised before display (replace `VDC-[0-9a-f-]+` with "this close").
2. **Immediate loading feedback on wizard rows.** Tapping an OPEN/CONTINUE/protected-INCOMPLETE row sets "Opening <date>…" but `openDate()` clears `#topMsgIntro` immediately, so only the card `.loading` style shows. Keep a visible "Opening 25 September 2026…" message (top of page, visible under the sticky shell header) until the opened screen renders, for every row type.
3. **Stale prior-suite assertion.** `scripts/tests/test_uma_hist_close_queue1_20261005.py` fails 1 because it hardcodes 27 Sep = OPEN, but 27 Sep now has a real DATA_CAPTURED close (VDC-667e795b…) that Matt opened from his iPhone at 12:06 WITA today (core_audit_events, cloudflare_access_verified). Update that assertion to derive the expected status from the canonical record (INCOMPLETE when a non-cancelled draft exists) — do not delete the test, do not touch data.

## Hard rules (unchanged)
- Single Beta writer. Production `127.0.0.1:8787` pid **1297** is SACRED: never restart/touch. Leave cursor-agent pid 2627 alone. Do not kill any process. No other agents, no cloud agents.
- Live Beta DB `catalog/content_library.sqlite`: read-only (`mode=ro`). Do NOT write rows to the live DB. Do NOT mutate protected closes VDC-470e741f, VDC-64f5f529, VDC-8fd544e2, or ANY 3 Oct / 4 Oct data. Peaches hashes them before and after.
- No commit, push, merge, or clean. Never mark staff_ready / human_commissioned true. No fabricated data.
- Keep all MOBILE-1 behaviour intact (whole-row links, hide panels, pushState/popstate, read-only protected, no duplicate opens, 3 Sep reachable).
- Reload Beta only if Python changed, only with exactly one listener on 8788, via `scripts/beta_restart.py`; HTML-only changes are served from disk (say so).

## Tests
Extend `scripts/tests/test_uma_hist_close_nav_mobile1_20261005.py` (or add `..._mobile2_...`) proving: no code path in `dashboards/uma-blu-close.html` writes `close_id` / `VDC-` into the DOM (string/AST check of every `textContent`/`innerHTML` assignment that references close_id); API error text is sanitised; loading message persists until screen shown. Run and report BOTH suites (`test_uma_hist_close_nav_mobile1_20261005.py` and `test_uma_hist_close_queue1_20261005.py`) — target 0 fail.

## Result
Write `state/reliability/UMA-HIST-CLOSE-NAV-MOBILE-2-RESULT-2026-10-05.json` with status, files_changed, tests per suite pass/fail, beta_pid_before/after + reload or "HTML-only, served from disk", protected_closes_unchanged, prod_pid_unchanged 1297, staff_ready false, human_commissioned false, no_commit true, exit_code.

End cursor log with `RESULT_JSON: <path>` and `EXIT:0` or `EXIT:1`.
