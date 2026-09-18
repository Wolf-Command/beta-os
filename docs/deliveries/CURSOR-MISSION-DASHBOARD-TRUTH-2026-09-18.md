# CURSOR MISSION — Dashboard reads canonical SYSTEM

**Beta only.** Workspace `/Users/wolfterminal/beta-os`.
**Do not** change `docs/MODEL-C-CAPABILITY-CATALOG.md`, the credit values in `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`, or any maturity state in `state/model-c-baseline-assessments.json`.
**Do not** touch Production `:8787`, CRM cutover, Zayen finance, or Tisa HR.
**Do not** invent scores for Operating Adoption, Data, Founder Independence, Financial Control, or Sale Readiness.

## Defect

`scripts/core/progress_read_model.py` `overall_from_card` still returns `PARTIAL ESTIMATE` from the old Master_Build mix. The Progress page shows that as the mission percentage (about 28%). The canonical ledger is already `state/model-c-baseline-assessments.json` (77 rows). Credits are ABSENT 0, SPECIFIED 0.05, BUILT 0.25, PROVEN 0.80, READY 1.00. Current sum is 19.45 / 77. Display one decimal: 25.3%. Do not store 25.3. Compute it on each read.

## SYSTEM dial

Add a function that, on every read:

1. Loads the 77 rows from `state/model-c-baseline-assessments.json`. First field is the maturity state.
2. Maps each state through the locked credits. Unknown state is a hard fail, not a zero.
3. If the row count is not 77, do not show a percentage. Status `SCORING_PROJECTION_STALE`.
4. `system_pct` = round half up to 1 decimal of `sum(credits) / 77 * 100`.
5. Return the sum, the counts (ABSENT, SPECIFIED, BUILT, PROVEN, READY), and the formula. No second scoring table.

The Owner cockpit primary number is this `system_pct`, label `SYSTEM`. The old `PARTIAL ESTIMATE` / `overall_pct` must not be the primary number. Keep the old calculation in code or docs as history, marked legacy, not rendered as current progress.

## Model E dials

Same view, six lines:

- SYSTEM — the computed percentage
- OPERATING ADOPTION — Not scored yet
- DATA / MEASUREMENT — Not scored yet
- FOUNDER INDEPENDENCE — Not scored yet
- FINANCIAL CONTROL — Not scored yet
- SALE READINESS — Not scored yet

No interim percentages. No 0% pretending to be a score.

## SYSTEM detail

A section the owner can open. Human words. Shows:

- 77 capabilities
- the five counts
- counts by domain, domain taken from `docs/MODEL-C-CAPABILITY-CATALOG.md` (do not invent domains)
- recent movements from `state/model-c-score-history.jsonl` (read it; do not rewrite it)
- capabilities whose evidence note still says the next bar is open (waiting evidence)
- health stays a separate block. Do not fold factory/pulse health into the maturity percentage.

## Integrity

One check, same process:

- score from the ledger file
- score from the read model / API
- score in the rendered Progress HTML

If they differ, the page shows `SCORING PROJECTION STALE` and does not show a percentage. Test this by pointing the read model at a temp ledger that disagrees, not by editing the real ledger.

## Regression

Temp copy of the ledger only. Tests must not write `state/model-c-baseline-assessments.json`.

Move one SPECIFIED row to BUILT. Expected delta is `0.20 / 77 * 100` on the computed percentage. Move it back. Score returns to the original. A grep-style test fails if `progress.html` or the read model contains a hard-coded `25.3` or `28` as the live percentage. The history note may still mention 28% as retired.

## Navigation

Progress/Empire links:

- Empire
- GGV
- AMG
- BZG → existing `/bzg` and `/bzg/uma-blu`

Do not rebuild the Uma pages.

## BZG pulse

If the Beta operational state is readable, the BZG card may show Daily Close status, PR attention count, POLICY REQUIRED count, and unresolved issues. Skip any row with `example: true`. Example bills must not increment the counts. If the read fails, show nothing rather than a fake zero alert.

## Rule

Write `docs/RULE-Dashboard-Projection-2026-09-18.md`. One page. The rule is: a dashboard is a projection. If the canonical state changes, the next read shows the new value, or it shows stale. No manual percentage copy.

## Deploy

After tests pass, restart Beta only:

`python3 scripts/beta_restart.py`

Then GET `http://127.0.0.1:8788/progress` and require the computed SYSTEM percentage and the words `Not scored yet`. Require that `PARTIAL ESTIMATE` is not the primary dial. Production `:8787` must still listen. Do not use nohup.

## Tests

`scripts/tests/test_dashboard_truth.py` plus existing progress tests still green.

## Commit

Only this slice. No `git add -A`. Do not commit a changed maturity ledger.

End the log with:

```
COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
SYSTEM: <computed one-decimal>
EXIT:0
CURSOR_DONE
```

If the live ledger does not sum to 19.45, print `EXIT:1` and the sum you computed. Do not paper over it.
