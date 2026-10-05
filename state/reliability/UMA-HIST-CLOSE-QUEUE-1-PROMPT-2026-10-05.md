# UMA-HIST-CLOSE-QUEUE-1 (P0)

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Uma Blu historical close completion queue (owner backlog UI + preflight freeze)

Slice id is **UMA-HIST-CLOSE-QUEUE-1**. Do NOT name routes, files, tests, or commits with the phrases "daily close" or "daily-close".

## Goal
Ship an Owner historical close completion queue for Uma Blu so Matt can finish backlog dates without fake greens and without touching Production.

## Preflight (already written — READ FIRST)
Read `state/reliability/UMA-HIST-CLOSE-QUEUE-PREFLIGHT-2026-10-05.json` (mode=ro inventory). Canonical statuses for the nine owner dates from `venue_daily_closes` only:

| Date | UI status (canonical) | close_id | Notes |
|------|-----------------------|----------|-------|
| 2026-09-25 | OPEN | (no record) | No fake CLOSED |
| 2026-09-27 | OPEN | (no record) | No fake CLOSED |
| 2026-09-28 | INCOMPLETE | VDC-4046a805-… | Draft DATA_CAPTURED |
| 2026-09-29 | INCOMPLETE | VDC-8fd544e2-… | PROTECTED — do not submit/finalise |
| 2026-09-30 | INCOMPLETE | VDC-25a3123a-… | Draft DATA_CAPTURED |
| 2026-10-01 | OPEN | VDC-3353351f-… | |
| 2026-10-02 | OPEN | VDC-da1b6621-… | CANCELLED twin exists; preserve printed vs historical ESB separately |
| 2026-10-03 | EXCEPTION | VDC-470e741f-… | PROTECTED — do not create another close; show real EXCEPTION |
| 2026-10-04 | INCOMPLETE | VDC-64f5f529-… | PROTECTED — use existing draft only |

Zero CLOSED Uma rows exist in Sep/Oct live DB. Do **not** infer CLOSED from ESB. Do **not** infer OPEN from missing photo alone when a draft exists (use INCOMPLETE).

## Product requirements (implement)

### 1) Historical date list
- Each row: BUSINESS DATE + clickable STATUS BUTTON from canonical closing record only.
- Statuses allowed: CLOSED, OPEN, INCOMPLETE, EXCEPTION, MISSING EVIDENCE, NEEDS REVIEW.
- Entire button opens that date.
- No generic OPEN for every date. No fake greens.
- Do not infer CLOSED from ESB. Do not infer OPEN from missing photo alone.

### 2) Owner queue page/section
- Nine dates at top (25,27,28,29,30 Sep + 01–04 Oct 2026) with live statuses.
- On successful submit, status flips immediately without manual register refresh.
- Tonight's current-day close (2026-10-05) stays separate from this backlog.

Preferred route: `/uma-blu-close` queue section, or a clear successor path such as `/uma-blu-close/history-queue` if cleaner. Document the one link in RESULT.

### 3) Flows
- OPEN / INCOMPLETE: DATE → SHIFT REPORT → BANK TERMINALS → CASH → PETTY (that date only) → REVIEW → SUBMIT. One next action.
- CLOSED: read-only summary (numbers, evidence, closer, approver, audit, exceptions, discrepancies) with deliberate audited REOPEN only.
- MISSING EVIDENCE on completed dates: show CLOSED + EVIDENCE MISSING; allow RECOVER / UPLOAD / ATTACH REPRINT without reopening financial close.

### 4) Preflight freeze (nine dates)
For EACH of the nine dates, freeze THAT date's ESB/sales/gross/net/tax/service/pax/bills/cancel/void/cash/EDC/QRIS/other/non-sales/printed report/EDC slips/till/petty/existing close/exceptions into the preflight matrix (extend the JSON; do not pull today's live ESB).
Petty: that business date only. Today's `PETTY-UMA-6D853EEAE0` Rp500k Cash In (business_date 2026-10-05) must not contaminate any historical freeze (preflight already proves ok_not_contaminated=true — keep it true).

### 5) All other historical Uma Blu dates
- Expected CLOSED unless Wolf proves otherwise.
- If a date is CLOSED but expected photos missing: search authorised stores (Wolf storage, upload folders, NAS, Telegram evidence, Alchemist, Drive, old Daily Close folders, ESB exports). If reprintable: reprint, capture, attach with provenance `HISTORICAL REPORT REPRINT / reprinted on [date] / for business date [X]`. Do not fabricate. Do not auto-reopen financials.
- Live DB currently has no CLOSED Uma Sep/Oct rows — do not invent CLOSED; surface honest statuses and evidence-recovery work.

### 6) Multi-source preserve
- Keep ESB warehouse vs printed shift vs terminal vs cash vs petty vs existing close as separate sources.
- **29 Sep (VDC-8fd544e2)**: do not submit/finalise. Preserve both sides:
  - warehouse cash 4135000 / 51 bills
  - printed gross 13435000 cash 3790000 bills 50 pax 79
  - payments as Owner listed; non-sales Exec Chef 78512
  - discrepancy cash 345000 bills 1; `auto_resolve` false
  - photo: SOURCE EVIDENCE PROVIDED / FILE INGEST PENDING
- **2 Oct**: preserve printed vs historical ESB separately.
- **3 Oct (VDC-470e741f)**: show real EXCEPTION/INCOMPLETE; do not create another close.
- **4 Oct (VDC-64f5f529)**: use existing draft only; do not create another close.

### 7) Do not rebuild banned surfaces
Do not rebuild Purchase Orders, Recipe Builder, or Petty Cash capture. This slice adds owner queue UX + honest status + freeze/evidence recovery paths around existing Uma Blu close surfaces.

## Rules
- Single Beta writer. Production `127.0.0.1:8787` pid **1297** is SACRED: do not restart or touch.
- Live Beta DB `catalog/content_library.sqlite`: read with Python sqlite3 `file:...?mode=ro`. Never copy the DB. Back up under `catalog/backups` before any write; record sha256.
- Protected closes: VDC-470e741f (3 Oct), VDC-64f5f529 (4 Oct), VDC-8fd544e2 (29 Sep) — rules above.
- Protected petty: PETTY-UMA-6D853EEAE0 — do not mutate.
- No commit, push, merge, or clean dirty tree. Do not kill other processes. Do not start another agent.
- Reload Beta only at the very end, only if Python changed, only if exactly one listener remains on 8788, via existing beta restart path; else RELOAD_HELD.
- `staff_ready=false`, `human_commissioned=false`. No money movement. No fabricated rows.
- Tours/Events stay off.

## Tests
Add `scripts/tests/test_uma_hist_close_queue1_20261005.py` proving:
1. Nine-date status buttons come from canonical close records (no fake CLOSED).
2. Protected closes unchanged (ids + states).
3. Petty freeze for a backlog date excludes PETTY-UMA-6D853EEAE0.
4. 29 Sep multi-source discrepancy fields preserved / auto_resolve false.
5. Queue route reachable; current-day close remains separate.
6. Prod pid 1297 unchanged.

## Result
Write `state/reliability/UMA-HIST-CLOSE-QUEUE-1-RESULT-2026-10-05.json` with:
- status IMPLEMENTATION_DONE or BLOCKED + reason
- tests_pass / tests_fail
- routes_added / one_owner_link
- nine_date_statuses (live after UI)
- ready_to_close_now count
- evidence_recovery counts
- protected_closes_unchanged true
- protected_petty_unchanged PETTY-UMA-6D853EEAE0
- prod_pid_unchanged 1297
- staff_ready false, human_commissioned false
- exit_code 0 on success
- no_commit true

End cursor log with RESULT_JSON path and EXIT:0 or EXIT:1.
