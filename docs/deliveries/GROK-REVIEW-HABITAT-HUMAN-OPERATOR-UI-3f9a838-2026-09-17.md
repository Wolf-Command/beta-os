# GROK REVIEW — Habitat Human Operator UI `3f9a838`

**Date:** 2026-09-17 WITA  
**Factory run:** `BF-habitat-human-ui-20260917`  
**VERDICT: PASS** — no material findings. Fix loop NOT REQUIRED.

## Evidence
- Cursor log: `EXIT:0` · pid 14098 gone · commit `3f9a838` exact message `feat(content): habitat human operator UI for core publish gate`
- Smoke: **14 passed, 0 failed** (`scripts/tests/test_habitat_operator_smoke.py`)
- Publish-gate regression: **51 passed, 0 failed** (`scripts/tests/test_habitat_publish_gate.py`)
- Live page: `http://127.0.0.1:8788/habitat-operator.html` → **200** (served from `dashboards/` root handler)
- Claim `habitat-operator-ui-021` recorded
- Forbidden files in commit: none (`serve_beta.py` / `.env` / wolf-system untouched)
- Haikal dirty tree left unstaged (as required)

### Diff stat
```
 dashboards/habitat-operator.html                   | 663 +++++++++++++++++++++
 ...MISSION-HABITAT-HUMAN-OPERATOR-UI-2026-09-17.md | 223 +++++++
 scripts/tests/test_habitat_operator_smoke.py       |  51 ++
 state/build-claims/2026-09-17.json                 |   7 +
 4 files changed, 944 insertions(+)
```

## Mission checklist
| Must | Result |
|------|--------|
| Producer pick/edit/submit | YES — planner GET/save/submit-for-approval |
| Approver approve / Core reject / publish gate | YES |
| Who-am-I | YES — `/api/core/me` + `/api/core/me/permissions` |
| READY_TO_PUBLISH + Metricool WRITE DISABLED copy | YES |
| Mobile-first / big buttons | YES — max-width 640, full-width btns |
| No thin `/api/planner/reject` | YES (Core reject only) |
| No Metricool write flip | YES |
| No person spoof in POST bodies | YES |
| credentials same-origin | YES |

## Red-team
| Attack | Result |
|--------|--------|
| X-Wolf-Subject always-on spoof | FAIL closed — only when server `development_assertion_allowed` |
| `verified_person_id` in POST | ABSENT |
| METRICOOL_WRITE_ENABLED=true in page | ABSENT |
| Thin planner reject inventing Core | ABSENT |
| serve_beta / Production / :8787 | UNTOUCHED |
| Save forcing Human_Approved | OMIT status on save (comment + body) |

## Gaps (non-blocking)
1. Staff eyes still needed on phone (Producer + Approver live action) — Delivery WHERE for Matt.
2. Week control is `type=date` forced to Monday (label says Week) — fine UX, not a gate fail.
3. Approver list filters Core PENDING with `content_planner:` source — correct for Habitat pilot.

## Production
NONE. Beta `:8788` only.
