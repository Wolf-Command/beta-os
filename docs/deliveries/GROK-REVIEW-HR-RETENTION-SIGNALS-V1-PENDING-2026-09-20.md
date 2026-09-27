# GROK REVIEW — CAP-HR-05 Retention & Succession Signals v1 — PENDING — 2026-09-20

## Class
NEW CAPABILITY Beta. CR-1ade9354d7443ed5. At most BUILT ceiling label. Live ledger SPECIFIED.

## Lane
`hr-retention-signals-v1` on mission `owner-autonomous-20260920-w11` after `hr-payroll-inputs-v1` DONE (`bf4fecd`).

## Expected surfaces
- `scripts/core/hr_retention_signals.py` (new)
- `dashboards/hr-retention-signals.html` (new)
- `scripts/serve_beta.py` (wire)
- `scripts/tests/test_hr_retention_signals.py` (new)
- `state/build-claims/2026-09-20.json` claim row `bf-hr-retention-signals-v1-20260920`

## Prove gates
- Focused tests green (`PASS=291 FAIL=0`)
- Live `:8788` anon `GET /api/hr/retention-signals` → **403**; page `/hr-retention-signals` → **403**
- CAP-HR-05 stays SPECIFIED; CR stays OPEN; WIP four unchanged; `:8787` untouched
- No Production. No Alchemist writes. No score gaming / invent PROVEN.
