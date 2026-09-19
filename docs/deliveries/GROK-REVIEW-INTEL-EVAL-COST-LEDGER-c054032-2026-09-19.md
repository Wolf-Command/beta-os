# Grok review — Intelligence evaluation + cost ledger c054032

Date: 19 September 2026 (2026-09-19 ~17:10 WITA)
Commit: `c054032958b89d5b4ddbcae04dbec8eb46a71e34`
Run: BF-intel-eval-cost-ledger-20260919
Slice: BF-intel-eval-cost-ledger-20260919
Lane: intel-eval-cost-ledger
Mission: owner-autonomous-20260919
Reviewer: Peaches (independent of Cursor's own report)

## Verdict

**PASS.** Close the lane. Ledger is BUILT on Beta only. Do not invent CAP PROVEN. CAP-INTEL-01 stays BUILT. CAP-INTEL-05 stays SPECIFIED (CR-be51980bd1194448 remains OPEN).

## What landed

- `scripts/core/intel_eval_cost.py` — append-only schema, `record_call`, `read_summary`; Beta sqlite under `catalog/` (gitignored; created only on successful Owner record).
- `scripts/serve_beta.py` — `GET`/`POST /api/intel/eval-cost` on `:8788`; Owner (`PERS-MATT`) via progress-owner gate; anon/staff 403.
- `scripts/tests/test_intel_eval_cost.py` — schema/record/read + refuse paths; WIP four digests locked.

## Independent prove (FACTORY_ADVANCE → GROK_REVIEW)

- `python3 scripts/tests/test_intel_eval_cost.py` → **PASS=109 FAIL=0**
- Live anon `GET /api/intel/eval-cost` on `:8788` → **403** `missing_auth` (fail-closed)
- Live anon `POST /api/intel/eval-cost` → **403**
- Ports: `:8787` listening (Production untouched); `:8788` listening (Beta)
- Diff scoped: `intel_eval_cost.py` + `serve_beta.py` route handlers + tests + plan/mission docs. No credits table. No Model C ledger row edits.
- WIP four still modified and **unstaged** (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)

## Red team

| Attack | Result |
| --- | --- |
| Invent prices / rate card / float cost | PASS — refused; no row |
| Auto-billing / spend API / stripe route | PASS — refused |
| Anon or staff API open | PASS — 403 |
| Production :8787 mutate | PASS — Beta route only; :8787 still up |
| Raise CAP-INTEL-05 / invent PROVEN | PASS — assessments untouched; CR stays OPEN |
| Touch WIP four | PASS — digests green; not in commit |
| Alchemist / wolf-system path ledger | PASS — path refused |
| Score gaming / credits edit | PASS — not in diff |

## Completion Register

No CAP maturity change this slice. CAP-INTEL-05 Learning CR stays **OPEN**. Do not false-resolve. Delivery evidence is commit `c054032` + this review.

## Out of scope (unchanged)

Production, CAP PROVEN, Devi retest, Alchemist writes, finance/HR, score gaming.

## Close action

Mark lane COMPLETED with `c054032958b89d5b4ddbcae04dbec8eb46a71e34`, clear ACTIVE, `close_slice` → next PENDING (`bzg-fb-today-ops-polish`).
