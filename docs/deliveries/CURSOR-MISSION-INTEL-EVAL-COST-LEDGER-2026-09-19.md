# CURSOR MISSION — Intel evaluation + cost ledger — 2026-09-19

**Decision served:** 2026-09-19 PICK, intelligence evaluation + cost ledger v1 on Beta only (`docs/deliveries/GROK-PLAN-INTEL-EVAL-COST-LEDGER-2026-09-19.md`). Owner lane `intel-eval-cost-ledger`.

**Status:** BUILT on Beta. Not PROVEN. Model C maturity not raised.

## What landed

- `scripts/core/intel_eval_cost.py` — append-only schema, `record_call`, `read_summary`. Dedicated Beta file `catalog/intel_eval_cost_ledger.sqlite` (created only on a successful Owner record; gitignored).
- `scripts/serve_beta.py` — `GET` and `POST /api/intel/eval-cost` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403.
- `scripts/tests/test_intel_eval_cost.py` — schema, record, read, and refuse paths.

## Honesty

- A cost is stored only when the caller sends a decimal string and `cost_source=caller_supplied`. Floats, rate cards, price lookup, spend APIs, and auto-billing are refused and write no row.
- Missing cost stays `NOT_SUPPLIED`. Token totals are not derived. Currencies are not merged and USD is not assumed.
- The Owner summary says it is not a bill. No external spend call. No auto-instrument of other routes.
- `CAP-INTEL-01` stays BUILT. `CAP-INTEL-05` stays SPECIFIED. Ledger stays 77 rows. Credits table unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No Devi retest. No score change.

## Prove

`python3 scripts/tests/test_intel_eval_cost.py` → `PASS=109 FAIL=0`.
