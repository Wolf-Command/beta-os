# GROK REVIEW — Progress Dashboard v2 Owner Cockpit `d8f39b4`

**Date:** 2026-09-17 WITA  
**Factory run:** `BF-progress-dashboard-v2-20260917`  
**VERDICT: PASS** — no material findings. Fix loop NOT REQUIRED.

## Evidence
- Cursor log: `CURSOR_DONE` · pid 32140 gone · HEAD `d8f39b4` exact message `feat(progress): Owner Cockpit v2 — factory health split + Empire UX`
- Peaches re-run: **152 passed, 0 failed** (`python3 scripts/tests/test_progress_dashboard.py`)
- Deployed-route prove: **PASS all** (`GET /progress` 200, `:8788` up)
- Dirty Phase2.6 WIP: **not in commit** (phase26_team.py unchanged vs parent); left unstaged as required
- Forbidden: no Production `serve.py`, no ESB/Metricool writes, no Habitat workflow mutate

### Diff stat
```
 dashboards/progress.html                           | 365 ++++++++--
 docs/canon/PROGRESS-DASHBOARD.md                   |  48 +-
 ...SOR-MISSION-PROGRESS-DASHBOARD-V2-2026-09-17.md |  19 +
 .../GROK-PLAN-PROGRESS-DASHBOARD-V2-2026-09-17.md  |  57 ++
 scripts/core/progress_read_model.py                | 744 ++++++++++++++++++---
 scripts/tests/test_progress_dashboard.py           | 114 +++-
 state/build-claims/2026-09-17.json                 |  21 +
 state/progress-dashboard-v2-backup-20260917.sha256 |   3 +
 state/progress/v1_overlay.json                     |  80 ++-
 9 files changed, 1281 insertions(+), 170 deletions(-)
```

## Mission checklist
| Must | Result |
|------|--------|
| Factory health removed from mission weighted % | YES — 7 domains sum weight 1.0; Factory absent from domains |
| Separate `factory_health` HEALTHY/DEGRADED/FAILING | YES — status HEALTHY; checks ACTIVE/Beta/prove/Production |
| Overall recompute + why vs prior 27% | YES — **28%** PARTIAL ESTIMATE; reconcile show_why true (+1 from re-norm, not inflate) |
| Core denominator clarity | YES — item_count denominator note on Core card |
| Empire Owner Cockpit hierarchy | YES — How far / chips / pulse / next moves / wins / road / domains |
| Status chips + tooltips; COMMISSIONED out of hero | YES — BUILT · HUMAN TESTING · LIVE · WAITING · POLICY NEEDED |
| Next moves ≤3 with class; RECOMMENDED ≠ APPROVED | YES — 2 WAITING + 1 RECOMMENDED |
| Hide raw IDs in owner fields | MOSTLY — plain pulse/moves/wins/road clean; see nit |
| Habitat/Uma owner stage ladders | YES — PLAN→…→LEARN / ESB→…→VERIFIED CLOSE |
| Mobile first = progress + phase + next move | YES — `.mobile-next` panel |
| Tests + deployed-route prove | YES — 152/0 + prove PASS |
| No HUMAN COMMISSIONED flip | YES — First Human Commission milestone still LOCKED |

## Red-team
| Attack | Result |
|--------|--------|
| Factory still in weighted % | absent (weight sum 1.0 over 7 domains) |
| Inflate % to look good | 27→28 explained by re-norm only |
| Staff `/api/progress` | 403 (suite) |
| Fake precision / unlabelled estimate | PARTIAL ESTIMATE preserved |
| Mark HUMAN COMMISSIONED without Matt | milestone locked; no commission flip |
| Production / Metricool write / Habitat mutate | untouched in commit |
| Wipe Phase2.6 dirty tree | absent from commit |

## Gaps (non-blocking nits)
1. Habitat owner stage PROOF note still includes `EVR-HABITAT-CONTENT-PUBLISH` (one ID leak in Empire stage rail). Pulse/moves/wins/road/domain plain copy are clean. Optional polish later — not a fix-loop FAIL.
2. Not HUMAN COMMISSIONED until Matt retests `/progress` himself (approved scope).

## Production
NONE. Beta `:8788` only.
