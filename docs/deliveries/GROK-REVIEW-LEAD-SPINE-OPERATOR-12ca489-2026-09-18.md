# GROK REVIEW — Lead Spine operator 12ca489

**Commit:** `12ca489` feat(crm): add Beta Lead Spine operator path
**Date:** 2026-09-18 (factory watch ADVANCE → GROK_REVIEW)
**Bound:** beta-lead-spine-operator
**Verdict:** **PASS**

## Diff vs mission

| Requirement | Present in 12ca489 | Result |
| --- | --- | --- |
| `dashboards/lead-spine.html` mobile + demo banner | demo banner + closed-is-not-a-sale copy | PASS |
| Routes `/lead-spine` + `/api/leads*` in `serve_beta.py` | list/get/touch/note/stage/assign/unassign/work-item/claim | PASS |
| Identity via `resolve_request_identity` | route uses existing auth; unauth API fail-closed 403 | PASS |
| Wolf stage change does not mutate `source_stage` | `set_wolf_stage` + test | PASS |
| claim ≠ verify | claim CLAIMED only; no evidence skip | PASS |
| list_leads + unassign | both present; events appended | PASS |
| 8 DEMO fixtures + PERS-LEAD-DEMO habitat-only | seed + tests; staff lead grants=0 | PASS |
| Dirty WIP four files untouched | not in commit | PASS |
| No Model C/E / SYSTEM score edit | not in commit | PASS |
| No `BETA_AUTH_MODE` / port 8787 | Cursor log + live curl on :8788 | PASS |
| Beta path guard | `assert_beta` / refuses wolf-system | PASS |

## Soft note (not FAIL)

Commit also rewrote `state/build-claims/2026-09-18.json` (not in mission stage list) and dropped same-day AKR + Decision Memory claims. Peaches restored those claims as a FIX during verify. Not a product-code widen.

## Red team

| Attack | Result |
| --- | --- |
| Unauthenticated `/api/leads` | PASS — 403 missing_auth |
| Staff ROLE-MATT lead.* grant | PASS — staff grants=0; demo fixture role only |
| Claim verifies without evidence | PASS — claim stays CLAIMED |
| Cross-brand list leak | PASS — temp test hides other brand |
| Source stage rewrite via Wolf stage | PASS — source unchanged |
| Production / dirty WIP | PASS — not in commit |

## Verification

- `python3 scripts/tests/test_lead_spine_operator.py` → **PASS=30 FAIL=0** (re-run 2026-09-18 10:17 WITA)
- Cursor log: PASS=30 FAIL=0 · commit `12ca489` · `/lead-spine`=200 · `/api/leads`=403 · EXIT:0 · CURSOR_DONE
- Live curl re-check: `/lead-spine` 200 (Demo data + not a sale); `/api/leads?brand=habitat` 403

## Out of scope leftovers

Human commissioning of live staff on Lead Spine; live Habitat import; Metricool/external writes — still blocked by bound.
