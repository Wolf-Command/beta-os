# GROK TRIAGE — UMA BLU DAILY CLOSE NITS (OVERNIGHT P2)

**Date:** 2026-09-17
**Source:** `docs/deliveries/GROK-REVIEW-UMA-BLU-DAILY-CLOSE-909954d-2026-09-17.md`
**Rule:** Fix genuine engineering defects only. Preserve business semantics. No cash variance thresholds. No inventing closer. Habitat undisturbed. Production sacred.

| # | Nit | Verdict | Action |
| --- | --- | --- | --- |
| 1 | Empty `branchCode` bills in BLZ snapshot | **DEFECT** | Fail-closed: exclude blank/missing `branchCode` from Uma (BLZ) totals |
| 2 | HFB grants omit `venue.close.submit` vs plan text | **DOC DEFECT** (not grant widen) | Amend canon/plan text: HFB = exception resolve/verify path; submit stays ROLE-BZG-CLOSER + Matt. Do **not** add submit to HFB overnight (closer still WAITING) |
| 3 | `RECONCILED` never assigned | **DEFECT** | On clean path set state `RECONCILED` then transition to `VERIFIED_CLOSED` (preserve SUBMITTED ≠ RECONCILED ≠ VERIFIED honesty) |
| 4 | Dead SoD `sod_self_close` branch | **DEFECT** | Independently block `submitter == verified` on exception path (even when resolver differs) |
| 5 | Override refuse incomplete on exception/resolve/verify | **DEFECT** | Call `_venue_close_refuse_overrides` on remaining POST handlers |
| 6 | Tautology test assertion | **DEFECT** | Replace with real assertion that clean path hits RECONCILED (or never ACCEPT without policy) |

OUT OF SCOPE: cash variance thresholds, inventing closer person, Metricool, Habitat, Production, ESB writes.

## Success
- `python3 scripts/tests/test_uma_blu_daily_close.py` PASS
- Core regressions still green if run
- Grok actual-diff review PASS
- Beta runtime: Uma routes still 200 Owner; no Production touch
