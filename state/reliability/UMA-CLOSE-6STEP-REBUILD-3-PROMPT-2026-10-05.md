# UMA-CLOSE-6STEP-REBUILD-3 (OWNER ORDER — fix cycle 3 of 3, LAST ALLOWED)

Single Beta writer. Workspace `/Users/wolfterminal/beta-os`. Mon 5 Oct 2026 WITA. Never use "daily close"/"daily-close" in names.

**Read first, in full:** `state/reliability/UMA-CLOSE-6STEP-REBUILD-1-PROMPT-2026-10-05.md` (Matt's spec + button standard + hard rules), `...REBUILD-2-PROMPT-2026-10-05.md` (13 defects), `...UMA-CLOSE-EVIDENCE-ISOLATION-1-PROMPT/RESULT-2026-10-05.*` (evidence isolation — keep it intact).

## Peaches' independent rendered acceptance of REBUILD-2 (14:15–14:25 WITA, WebKit iPhone 14, real taps, isolated copy, zero live writes proven)
PASSED: 29 Sep end to end — figures (all 10), YES persists + advances, ESB difference 3,790,000/50 vs 4,135,000/51 → 345,000/1, banks only BNI+BRI + "MANDIRI — not used", ADD RECEIPT opens chooser in one tap, failed read shows "Couldn't read" with NO expected-as-receipt fill, bank EDIT/SAVE/CORRECT works, cash lines incl. opening float (1,000,000 + 3,790,000 − 370,000 + 0 = 4,420,000), review layout, SUBMIT WITH EXCEPTION ×10 taps = 1 POST, 11 extra API submits = same single row (EXCEPTION, variance −20,000, updated_at unchanged), result "Cash short Rp20.000 · ESB data difference Rp345.000 / 1 bill kept as exceptions", exception view complete, 3 Sep shift photo discovered with thumbnail, opening a date creates no close.

FAILED — fix ALL, each proven by your own rendered test:
A. **Shift EDIT is a no-op.** `btnShiftEdit` only shows a message. It must open editable fields for all 10 figures (gross, bills, pax, cash, BNI EDC/QRIS, BRI EDC/QRIS, Scott & Etik, Exec Chef non-sales), save as an append-only human correction (original image + raw extraction kept), then return to "DO THESE FIGURES MATCH THE REPORT?".
B. **YES accepted an empty read.** On 3 Sep the dry-run read returned nothing ("Gross sales —, Bills null, Pax null, …") and YES confirmed it, after which all banks showed "not used". If nothing (or no sales/cash) was read, YES must not confirm: show "Nothing read — tap EDIT and type the figures from the report."
C. Raw "null" shown for Bills/Pax — show "—".
D. **3 Sep's 4 card slips are not offered.** Discovered EDC slips (`bzg_ops_evidence_unlinked`, 4 × `media/nightly/edc_8946416960_…`, 3 Sep 21:28–21:33) are only rendered when no close exists (`if (unlinkedEdc.length && !close)` ~L669), and only the first 2, the same 2 for every bank (`|| true` filter). After linking the shift report a close exists, so the slips vanish. Required: bank step lists ALL discovered, not-yet-linked slips for that date (thumbnail + USE THIS RECEIPT → choose bank if unknown → read/EDIT → Expected/Receipt/Difference → CORRECT), regardless of whether a close exists; a used slip disappears from the list; bank cards derive from confirmed (possibly edited) figures; if the shift report has no bank figures, still show found slips with a bank choice.
E. **JS ReferenceError** `Can't find variable: amtEntered` in the `cashAmt` input handler (~L1008). Fix it; "Continue to review" must stay hidden until a count is entered (currently visible before counting, so cash can be skipped).
F. **Duplicate actions on shift step.** After upload / when a photo exists, the screen shows "Shift report photo found + VIEW PHOTO / USE THIS REPORT / REPLACE" AND "TAKE PHOTO / UPLOAD PHOTO" AND "Read shift report" at once. Spec: existing photo → only VIEW PHOTO / USE THIS REPORT / REPLACE – ADD BETTER PHOTO; USE THIS REPORT starts the read directly (one action, loading state). No photo → only TAKE PHOTO / UPLOAD PHOTO.
G. While a bank's CORRECT/EDIT panel is open, that card's own ADD RECEIPT is still shown — hide it (one action at a time).
H. Review shows the WHY note twice; differences use mixed signs ("Rp-20.000" on cash step, "DIFFERENCE Rp20.000" on review, "Rp-5.000" for BNI QRIS). Use plain words everywhere: "Short Rp20.000" / "Over Rp5.000" / "Matches".
I. VIEW CLOSE after submit shows a read-only review whose only button is "← Back", which returns into the cash step of a submitted close. Read-only view must offer BACK TO MISSING CLOSES and never re-enter edit steps for a submitted close.
J. Stale status messages persist across steps ("Figures confirmed." on the bank screen, "Human-entered amounts ready — tap CORRECT." on the cash screen). Clear messages on step change.
K. Status vocabulary still differs between Missing-closes cards and the Search-date list (e.g. 30 Sep "Incomplete" vs "OPEN"; 25 Sep "Open" vs "OPEN"); exception dates show action "REVIEW" — spec says "REVIEW EXCEPTION". One vocabulary from one source.
L. Sticky top header covers the step title: opening 3 Sep lands with the step panel top at y≈62–120 under the ~310px sticky header. On every step change scroll the step's top into view below the header.

## Acceptance you must self-prove before EXIT:0
Rendered page, real `page.tap` only (no `dispatch_event` on hidden elements), WebKit iPhone 14, isolated copy via `~/hist-close-nav-work/probe_server.py <port> <tag>` started with `WOLF_CLOSE_VISION_DRY=1 BETA_LLM_DRY_RUN=1 WOLF_EVIDENCE_ROOT=<your temp dir>/evroot`. Prove ZERO writes into live `state/bzg-daily-close/receipts`, `state/uma-petty-receipts`, `state/bzg-supplier-notas` (file list + sha before/after, photo-index.jsonl sha unchanged). Walk 29 Sep fully (as above) AND 3 Sep: discover shift photo → USE THIS REPORT → (dry-run empty read) → YES blocked → EDIT figures → YES → banks show all 4 found slips → USE THIS RECEIPT for each needed bank → cash → review → submit on the copy → one result. Stop your probe; delete only your own temp dir (leave `tmp-histnav-probe-rb2debug` unless it is yours).

## Hard rules (unchanged)
3/4 Oct (VDC-470e741f, VDC-64f5f529) and all their data byte-unchanged; live VDC-8fd544e2 stays INCOMPLETE; the 52 quarantined synthetic files + index rows stay preserved (no delete/move/edit); never upload/declare/submit on live. Prod :8787 pid 1297 SACRED; leave cursor-agent 2627 alone; never print process command lines; no cloud agents; nothing paid; no commit/push/clean; staff_ready/human_commissioned false; no fabricated data; no internal IDs/GL/Reconcile in UI. Reload Beta only via `scripts/beta_restart.py` with exactly one 8788 listener.

## Tests
Add `scripts/tests/test_uma_close_6step_rebuild3_20261005.py` for A–L; re-run rebuild1/2, evidence_isolation1, complete1/2, nav_mobile1/2, queue1.

## Result
`state/reliability/UMA-CLOSE-6STEP-REBUILD-3-RESULT-2026-10-05.json` (per-defect fix + rendered proof text, zero-live-write proof, idempotency, 3 Sep slips, suites, beta pid, protections, no_commit, exit_code). End log with `RESULT_JSON: <path>` and `EXIT:0`/`EXIT:1`.
