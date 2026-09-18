# Grok review — Intel Needs You + Uma Issues 181acb2

Date: 19 September 2026
Commit: 181acb2cc496f0944e3c06298cdfdff4e4cb1a03
Run: BF-intel-needs-uma-20260919
Reviewer: Peaches

## Verdict

PASS.

## Prove

- New `scripts/core/blocker_explain.py` — deterministic why + classification.
- Live Issues sample: POLICY_REQUIRED → why “No approved monetary authority limit…” · classification NEEDS_POLICY · example true.
- Tests: `test_blocker_explain` PASS=54 FAIL=0; Cursor suite 191/0.
- OPENING BALANCE / CLOSER do not auto-land in Needs You.
- Example issues excluded from Owner Pulse.
- Progress shows Needs you / staff / policy / external access buckets.
- SYSTEM unchanged 19.45 → 25.3. Routes `/progress` and `/bzg/uma-blu/issues` 200. Production untouched.
- Factory: WAITING_CURSOR → GROK_REVIEW via supervisor auto-advance (`require_matt` false). No Matt status used.

## Red team

- Knowledge resolution enrichment is optional; templates cover the required kinds.
- Needs You emptiness depends on curated overlay + classification filter — verify after P3 if Today starts emitting owner exceptions.
