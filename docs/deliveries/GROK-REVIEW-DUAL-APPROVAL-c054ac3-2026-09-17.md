# GROK ENGINEERING REVIEW + RED TEAM — Dual Approval

**Role:** GROK (engineering review / red-team) — distinct from Peaches evidence verify  
**Commit reviewed:** `c054ac334f49d14079d60835208dc7a4bed8eb42`  
**Subject:** `feat(core): add dual approval control`  
**Date:** 2026-09-17 WITA  
**Method:** Read actual diff + `scripts/core/approvals.py` decide path, `015_dual_approval.sql`, `migrate_dual_approval.py`, `docs/canon/DUAL-APPROVAL.md`, `serve_beta.py` approval handlers, `test_dual_approval.py`. Not a Peaches test-count claim alone.

**Verdict:** **PASS** — no MATERIAL security defect in approved scope

---

## Diff scope reviewed

| Path | Notes |
|------|-------|
| `scripts/core/approvals.py` | required_decision_count, valid_approve_count, dual decide, IMMEDIATE lock, honesty BUILT |
| `scripts/migrations/015_dual_approval.sql` | unique APPROVED per Person index |
| `scripts/migrations/migrate_dual_approval.py` | backup+SHA, refuse non-beta / auth≠0, idempotent column |
| `scripts/serve_beta.py` | create accepts `required_decision_count`; actor spoof nulled |
| `scripts/tests/test_dual_approval.py` | 84 isolated tests |
| `docs/canon/DUAL-APPROVAL.md` | constitution + live policy not configured |

---

## Attack checklist (actual code)

| Attack | Result | Evidence |
|--------|--------|----------|
| Client forges requester/decider | **BLOCKED** | HTTP nulls client actor fields |
| Self-approval on material | **BLOCKED** | existing path retained; dual tests |
| Same Person second APPROVED | **BLOCKED** | pre-insert check + unique partial index → `duplicate_person_approval` |
| Same Person via second AuthIdentity | **BLOCKED** | Person-keyed; dual tests |
| Delegation double-counts Persons | **BLOCKED** | actor = delegate Person only; tests |
| First of N marks APPROVED | **BLOCKED** | stays PENDING; audit `approval.decision_recorded` not `granted` |
| REJECT does not terminate | **BLOCKED** | immediate REJECTED; further decide 409 |
| Lower `required_decision_count` after create | **BLOCKED** | immutable + `update_approval_request` raises; in snapshot_hash |
| Client sets count on decide | **BLOCKED** | decide ignores body count (HTTP test) |
| APR-RT-001 / DLG-RT-001 amount hole | **CLOSED** | material APPROVE still fail-closed; dual tests |
| WI complete ≈ approve | **BLOCKED** | `work_item_completed=False`; dual tests |
| Approve executes source | **BLOCKED** | `executed_source=False` |
| Concurrent same Person double APPROVED | **BLOCKED** | BEGIN IMMEDIATE + unique index + tests |
| Concurrent two Persons race | **OK** | both rows; flips APPROVED at threshold |
| Live Authority seed / dual policy | **BLOCKED** | migrate refuses auth≠0; no policy seed; live requests=0 |
| Prod / wolf-system path | **BLOCKED** | migrate FORBIDDEN fragments + beta-os require |
| Test pollution of live catalog | **BLOCKED** | FINAL live approvals=0 audit=47 |

---

## Non-blocking notes (AMBER — do not FAIL slice)

1. **`serve_beta.py` honesty drift:** three responses still hardcode `"dual_approval": "NOT_BUILT"` while core `HONESTY` is `BUILT` and create accepts `required_decision_count`. Under-claim (conservative). Hygiene follow-up OK; not a fail-open security hole.
2. **`get_approval_request` does not call `_enrich_request`:** `valid_approve_count` / `approvals_remaining` appear on create/decide returns; GET raw row omits helpers (mission marked optional).
3. Same Person may REJECT after their own partial APPROVE (constitution allows any REJECT → REJECTED). Documented behaviour; not exploited as bypass.

---

## Gate

- DUAL GROK REVIEWED ACTUAL DIFF: **YES**
- DUAL GROK RED TEAM: **PASS**
- DUAL FIX REQUIRED: **NO**
- Material findings: **NONE**

