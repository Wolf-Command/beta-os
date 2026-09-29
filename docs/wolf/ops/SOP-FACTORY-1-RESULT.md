# SOP-FACTORY-1 RESULT — SOP Factory vertical slice (evidence → lesson → human review)

**As of:** 2026-09-30 ~00:18 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` restarted (launchd) for new routes  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start MYWORK-PROVE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **2026-09-19 · PICK: SOP Factory v1** (extended by FINAL_WOLF_COMPLETION_MISSION Phase 2 pack SOP-FACTORY-1).  
Closes toward CAP-CORE-11 / MB-012 / IL-R7 — **eng vertical slice only; not LIVE adoption / PROVEN / READY**.

## What landed

### 1) Vertical slice on one factory
- Extended `scripts/core/sop_factory.py` (same factory — not a second SOP system)
- Flow: evidence note → lesson candidate → human review gate → (only after APPROVE) versioned approved draft
- DENY refuses the rule without minting approval / live
- Append-only: versions, learnings, candidates, review decisions, approvals — update/delete aborted by triggers
- Demo fixture under `state/build-factory/tmp-sop-factory-1/sop_factory.sqlite` labeled **DEMO / NOT LIVE STAFF ADOPTION**
- `catalog/sop_factory.sqlite` stayed **absent** (not inventing live catalog adoption)

### 2) Thin Beta UI + API
- Page: `/core/sop-factory` (aliases `/ops/sop-factory`, `/sop-factory`)
- APIs: `GET /api/sop/review-queue`, `GET /api/sop/candidates`, `POST /api/sop/lesson-candidate`, `POST /api/sop/review-decision` (+ existing draft/learn/approve)
- Unsigned → 403 · Amanda → Access denied · Matt → queue + DEMO candidate
- Honesty stamps on every payload: not staff_ready, not human_commissioned, not operating_adoption

### 3) Honesty
- No auto-approve production rules
- No silent history rewrite
- CAP-CORE-11 stays SPECIFIED; CR-c4ed4e3fa9f15a40 stays OPEN
- Acknowledgement ≠ training; use ≠ adoption (prior loop preserved)

## Tests

| Suite | Result |
| --- | --- |
| `test_sop_factory1_20260930.py` | **PASS=88 FAIL=0** |
| `test_sop_factory.py` | **PASS=113 FAIL=0** |
| `test_cap_core_11_loop.py` | **PASS=61 FAIL=0** |

## Shots (8/8)

Under `docs/wolf/ops/shots/`:
- `sopfactory1-queue-{desktop,phone}.png` — human review queue
- `sopfactory1-demo-{desktop,phone}.png` — DEMO candidate label
- `sopfactory1-amanda-deny-{desktop,phone}.png` — Amanda Access denied
- `sopfactory1-unsigned-deny-{desktop,phone}.png` — unsigned Access denied

## Files

- Core: `scripts/core/sop_factory.py`
- UI: `dashboards/sop-factory.html`
- Serve: `scripts/serve_beta.py`
- Tests: `scripts/tests/test_sop_factory1_20260930.py`
- Shots: `scripts/audit/sopfactory1_shots.py`
- Demo DB: `state/build-factory/tmp-sop-factory-1/sop_factory.sqlite`
- Stamp: `state/final-completion/packs/SOP-FACTORY-1-ARM.json`

## Out of scope (not started from this EXIT)

- **MYWORK-PROVE-1** (next queue — Peaches/parent arms after verify; Cursor must not auto-chain)
- HEADCHEF / Exit Report / claiming CAP-CORE-11 PROVEN/READY / LIVE staff adoption
- Auto-approve production rules, fake training metrics, flipping commissioning flags, prod mutate, push

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
