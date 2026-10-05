# UMA-CLOSE-6STEP-REBUILD-4 (fix cycle 4 — approved 17:13 WITA; narrow scope, Beta only)

Single Beta writer. Workspace `/Users/wolfterminal/beta-os`. Mon 5 Oct 2026 WITA. Never use "daily close"/"daily-close" in names.

## SCOPE — strictly these three items, nothing else
(a) EDIT-typed shift figures (`/save-shift-figure-edits` then YES `/confirm-shift-figures`) become THE confirmed shift report for that close: bank cards (which banks are used + expected EDC/QRIS) derive from the confirmed figures; cash step "Shift report cash" and EXPECTED CASH (= opening float + confirmed cash − petty OUT + petty IN for that date) derive from the confirmed cash; review + submit use the same confirmed figures. Precedence: latest confirmed human correction > confirmed raw read > Owner-typed printed source. Provenance (original image, raw read, human correction) stays append-only.
(b) Reopening a date must never skip found slips: while discovered, not-yet-used card slips exist for the date and any bank still needs a receipt, resume lands on the bank step and keeps offering USE THIS RECEIPT; a bank with an expected amount is not "done" until a receipt is confirmed.
(c) Minor: Search-date list uses the same status/action as Missing closes (29 Sep incomplete protected → CONTINUE, exception → REVIEW EXCEPTION); refresh both lists after a submit; after an empty read never show "Figures read — confirm…" (show "Nothing read — tap EDIT and type the figures from the report.").

## MUST NOT REGRESS (Peaches' 29 Sep PASS at 14:34 WITA)
Photo-only first screen; VIEW/USE THIS REPORT/REPLACE after upload; one-tap read; all 10 figures; YES → ESB DATA DIFFERENCE FOUND 3,790,000/50 vs 4,135,000/51 → 345,000/1; banks only BNI+BRI + "MANDIRI — not used"; one-tap ADD RECEIPT; failed read shows "Couldn't read" with NO expected-as-receipt fill; bank EDIT/SAVE/CORRECT; cash 1,000,000 + 3,790,000 − 370,000 + 0 = 4,420,000; review spec layout; SUBMIT WITH EXCEPTION ×10 taps = 1 POST, extra API submits idempotent; result "CLOSE SAVED WITH EXCEPTION — Cash short Rp20.000 · ESB data difference Rp345.000 / 1 bill kept as exceptions"; VIEW CLOSE read-only with BACK TO MISSING CLOSES; no internal IDs; no page errors. Evidence isolation (ISOLATION-1) stays intact.

## Background (Peaches' finding on REBUILD-3)

Read REBUILD-1/2/3 prompts + EVIDENCE-ISOLATION-1. All hard rules unchanged.

Peaches' independent rendered acceptance of REBUILD-3 (14:34–14:40 WITA, WebKit iPhone 14, isolated copy, zero live writes):
29 Sep PASSED end to end (incl. idempotent exception submit with Expected Rp4.420.000 / Short Rp20.000).
3 Sep FAILED:
1. After EDIT → SAVE (`/save-shift-figure-edits` 200) → YES (`/confirm-shift-figures` 200) with BNI EDC 2,000,000 / QRIS 100,000, BRI EDC 3,000,000 / QRIS 500,000, cash 3,000,000, the bank step still shows "BNI — not used / BRI — not used" and the cash step shows "Shift report cash —" and "EXPECTED CASH —". The human-corrected confirmed figures must drive bank expectations (`wizard_bank_cards` / `_shift_expected_by_bank`), cash expected, review and submit — the latest confirmed human correction wins over raw read and owner-typed source, with provenance kept.
2. Because the banks are treated as "not used", a fresh page resumes 3 Sep straight to cash and the 4 FOUND CARD SLIPS (shown once after YES) are skipped. Once the banks have expected amounts, the step must require/offer receipts, and found slips must stay offered until used or explicitly marked not needed.
3. Minor: Search-date list shows 29 Sep "INCOMPLETE · Protected | REVIEW" while Missing closes shows "CONTINUE" (and the list isn't refreshed after submit); after an empty read the message says "Figures read — confirm they match" (should say "Nothing read").

## Acceptance you must self-prove before EXIT:0
Rendered page, real `page.tap` only, WebKit iPhone 14, isolated copy via `~/hist-close-nav-work/probe_server.py <port> <tag>` with `WOLF_CLOSE_VISION_DRY=1 BETA_LLM_DRY_RUN=1 WOLF_EVIDENCE_ROOT=<tempdir>/evroot`. Zero writes into live `state/bzg-daily-close/receipts`, `state/uma-petty-receipts`, `state/bzg-supplier-notas` (list + sha before/after; photo-index.jsonl sha unchanged). 29 Sep full walk (above) AND 3 Sep full walk: find photo → USE THIS REPORT → empty read → "Nothing read" → EDIT figures (e.g. cash 3,000,000; BNI EDC 2,000,000 / QRIS 100,000; BRI EDC 3,000,000 / QRIS 500,000) → YES → banks BNI/BRI with those expected amounts + 4 found slips → fresh-page resume lands on banks → USE THIS RECEIPT (BNI, BRI) → read/EDIT → CORRECT → cash shows confirmed cash 3,000,000 and EXPECTED = 1,000,000 + 3,000,000 − 310,500 + 300,000 → count → review → submit on copy (×10 taps = 1 POST) → one result. Stop your probe; delete only your own temp dir(s) — also remove your own leftover `tmp-histnav-probe-rb3-wolf-*` / `rb3debug*` dirs only if you can confirm they were created by factory workers' harness runs (not Peaches'), else leave them.

## Hard rules (unchanged)
3/4 Oct (VDC-470e741f, VDC-64f5f529) + all their data byte-unchanged; live VDC-8fd544e2 stays INCOMPLETE; quarantined synthetic files/index rows preserved; never upload/declare/submit on live. Prod :8787 pid 1297 SACRED; leave cursor-agent 2627 alone; never print process command lines; no cloud agents; nothing paid; no commit/push/clean; staff_ready/human_commissioned false; no fabricated data. Reload Beta only via `scripts/beta_restart.py` with exactly one 8788 listener.

## Tests
Add `scripts/tests/test_uma_close_6step_rebuild4_20261005.py` for (a)(b)(c); re-run rebuild1/2/3, evidence_isolation1, complete1/2, nav_mobile1/2, queue1 — all must pass.

## Result
`state/reliability/UMA-CLOSE-6STEP-REBUILD-4-RESULT-2026-10-05.json` (per-item fix + rendered proof, 29 Sep non-regression, 3 Sep walk, zero-live-write, idempotency, suites, beta pid, protections, no_commit, exit_code). End log with `RESULT_JSON: <path>` and `EXIT:0`/`EXIT:1`.
