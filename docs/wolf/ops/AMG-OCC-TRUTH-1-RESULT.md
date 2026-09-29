# AMG-OCC-TRUTH-1 RESULT — AMG occupancy truth desk (UNKNOWN when PMS blocked)

**As of:** 2026-09-30 ~03:45 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral · Sidecar `:8790` not required for this pack  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start SOP-LESSON-LIVE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OCC-TRUTH-1** (armed 2026-09-30 after CONN-HEALTH-BOARD-1 PASS_VERIFIED) plus **2026-09-20 PICK CAP-AMG-01** (no invent PMS / occupancy numbers).  
Occupancy honesty over **AMG-OS-SHELL-1**. **Does not unblock CAP-AMG-01** (Yanolja).

## What landed

### 1) Occupancy honesty desk
- Page `/amg/occ-truth-1` (`dashboards/amg-occ-truth-1.html`; aliases `/amg-occ-truth-1`, `/amg/occ-truth`)
- Slots: **occupancy % · rooms sold · rooms available · ADR · RevPAR**
- Every slot: **BLOCKED_EXTERNAL** stamp · display **UNKNOWN** · `value`/`occupancy_pct`/`count`/`amount` null
- Banner + stamps: invented_occupancy=false · cap_amg_01_unblocked=false · staff_ready=false · human_commissioned=false
- Links: AMG OS shell, integrations honesty, AMG Today, connection health

### 2) API
- `GET /api/amg/occ-truth-1` (auth) → occupancy truth payload
- Unsigned → **403** (fail-closed)
- POST invent-occupancy / unblock-PMS / proven / ready → **403** with refuse codes

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| Occupancy slots | **UNKNOWN** · **BLOCKED_EXTERNAL** (never zeros-as-success) |
| INT-YAN-WOLF | **BLOCKED_EXTERNAL** · last_success null |
| `cap_amg_01_unblocked` | **false** |
| `invented_occupancy` | **false** |
| AMG-OS-SHELL-1 | **PRESERVED** (PMS tiles still blocked) |
| `staff_ready` / `human_commissioned` | **false** |
| CAP-AMG occupancy ceiling | **BUILT** · maturity **SPECIFIED** (not PROVEN/READY) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_amg_occ_truth1_20260930.py` | **PASS=187 FAIL=0** |

Shots: `docs/wolf/ops/shots/amgocctruth1-desk-desktop.png`, `amgocctruth1-desk-phone.png`, `amgocctruth1-occ-unknown.png`, `amgocctruth1-shell-preserved.png`, `amgocctruth1-unsigned-deny.png`.

## Files

- Core: `scripts/core/amg_occ_truth1.py`
- Serve: `scripts/serve_beta.py` (`_amg_occ_truth1_dispatch` / `_amg_occ_truth1_write_refused`)
- UI: `dashboards/amg-occ-truth-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_amg_occ_truth1_20260930.py`
- Stamp: `state/final-completion/packs/AMG-OCC-TRUTH-1-ARM.json`

## Out of scope (not started from this EXIT)

- **SOP-LESSON-LIVE-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake occupancy, unblocking PMS / CAP-AMG-01, inventing ADR/RevPAR
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
