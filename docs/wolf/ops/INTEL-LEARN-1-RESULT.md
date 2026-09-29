# INTEL-LEARN-1 RESULT — Wolf Intelligence learning board (ties SOP factory)

**As of:** 2026-09-30 ~01:16 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta harness ephemeral (+ live `:8788` routes wired)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start BZG-OPS-DESK-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **2026-09-20 PICK CAP-INTEL-05** approve-to-rule learning loop (deepened) plus **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INTEL-LEARN-1** (armed after FIN-INTERCO-1 PASS_VERIFIED).  
Ties **2026-09-19 PICK SOP Factory v1 / SOP-FACTORY-1** review gate.  
Composes `sop_factory.py` lesson candidates — **no second SOP system / no second learning ledger**.  
**Not PROVEN/READY.** No auto-approve. No fake performance / experiment success metrics.

## What landed

### 1) Intel learning board over SOP factory candidates
- Core `scripts/core/intel_learn1.py` lists lesson candidates from SOP factory DEMO path (`tmp-sop-factory-1`)
- Human review gate required before approved rule
- APPROVE/DENY reuses `POST /api/sop/review-decision` (SOP-FACTORY-1 API)
- DEMO rows labeled **DEMO / NOT LIVE STAFF ADOPTION**
- `catalog/sop_factory.sqlite` stayed **absent**

### 2) Thin Beta UI + API
- Page: `/intel/learning` (aliases `/ops/intel-learning`, `/intel-learning`)
- API: `GET /api/intel/learning` (Owner or authorised `intel.rule.read` / `core.sop.read`)
- Unsigned → **403** · Amanda → Access denied · Matt → queue + DEMO candidate
- POST auto-approve / fake performance → **403** (`auto_approve_refused` / `fake_metrics_refused`)
- Does not swallow `/api/intel/learning-policy*`

### 3) Honesty
| Pin | Value |
| --- | --- |
| CAP-INTEL-05 | **SPECIFIED** · ceiling BUILT · `cap_intel_05_proven=false` |
| Human review gate | **true** |
| Auto-approve | **false** |
| Fake performance / experiment success | **false** |
| Second SOP / learning system | **false** |
| `staff_ready` / `human_commissioned` / operating adoption | **false** |
| Live catalog SOP | **absent** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_intel_learn1_20260930.py` | **PASS=129 FAIL=0** |
| `scripts/tests/test_sop_factory1_20260930.py` (re-run) | **PASS=88 FAIL=0** |

## Shots (8/8)

Under `docs/wolf/ops/shots/`:
- `intellearn1-queue-{desktop,phone}.png` — human review queue / PENDING_REVIEW
- `intellearn1-demo-{desktop,phone}.png` — DEMO candidate label
- `intellearn1-amanda-deny-{desktop,phone}.png` — Amanda Access denied
- `intellearn1-unsigned-deny-{desktop,phone}.png` — unsigned Access denied

## Files

- Core: `scripts/core/intel_learn1.py`
- UI: `dashboards/intel-learning.html`
- Serve: `scripts/serve_beta.py` (`_intel_learn1_dispatch` + write refuse)
- Tests: `scripts/tests/test_intel_learn1_20260930.py`
- Stamp: `state/final-completion/packs/INTEL-LEARN-1-ARM.json`

## Out of scope (not started from this EXIT)

- **BZG-OPS-DESK-1** (next queue — Peaches/parent arms after verify; Cursor must not auto-chain)
- Auto-approve, fake performance metrics, HEADCHEF / Exit Report
- Claiming CAP-INTEL-05 PROVEN/READY / LIVE staff adoption
- Prod mutate, push, flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
