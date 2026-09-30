# OCCUPANCY-EXTERNAL-HOLD-1 RESULT — Occupancy EXTERNAL hold (Yanolja/Mews)

**As of:** 2026-09-30 ~09:21 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start WAVE9-SYNTH-CONTINUE / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack OCCUPANCY-EXTERNAL-HOLD-1** (armed after CONTENT-PUBLISH-PATH-1 PASS_VERIFIED).  
Challenges AMG occupancy UNKNOWN / Yanolja BLOCKED ceiling.  
**Stamp EXTERNAL_BLOCKER with Yanolja evidence (not UNKNOWN forever).**  
**No invent occupancy · no invent ADR · no unblock CAP-AMG-01.**  
Google NPWP remains **MATT_ACTION non-blocking**.  
Preserves **AMG-OCC-TRUTH-1** honesty (UNKNOWN/BLOCKED slots · invented_occupancy=false).  
Honest close-toward: **CAP-AMG occupancy** + **CAP-AMG-01** + **INT-YAN-WOLF**.

## Hold findings

| Probe | Result | Evidence |
| --- | --- | --- |
| Yanolja PMS (INT-YAN-WOLF) | **EXTERNAL_BLOCKER** | INTG audit BLOCKED_EXTERNAL; CAP-AMG-01 not unblocked; no live Wolf reader |
| Mews / Origin | **EXTERNAL_BLOCKER** | Commissioning register 2026-09-22 — Mews/Origin not found |
| Yanolja / Mews credentials | **EXTERNAL_BLOCKER** | Credential discovery: yanolja.json api_key empty (names-only); no invent live feed |
| Occupancy % / rooms / ADR / RevPAR | **null** | Never invent |
| last_success | **null** | Never invent |
| AMG-OCC-TRUTH-1 | **PRESERVED** | Slots UNKNOWN/BLOCKED_EXTERNAL · invented_occupancy=false |
| Google NPWP | **MATT_ACTION** | Non-blocking — does not fail EXIT |
| CAP-AMG-01 unblock | **EXTERNAL_BLOCKER** | External seating required |

Yanolja pins: `docs/wolf/ops/INTG-TRUTH-1-RESULT.md`, `docs/wolf/five/CREDENTIAL-DISCOVERY.md`, `docs/wolf/p0/P1-QUEUE.json` (CAP-INTG-01).  
Mews pin: `docs/deliveries/WOLF-CONNECTION-COMMISSIONING-REGISTER-BOX-ENRICHMENT-2026-09-22.md`.  
AMG-OCC pin: `docs/wolf/ops/AMG-OCC-TRUTH-1-RESULT.md`.

## What landed

### 1) Hold board
- Page `/amg/occupancy-external-hold-1` (`dashboards/occupancy-external-hold-1.html`)
- Classification pin **EXTERNAL_BLOCKER**
- Surfaces: Yanolja / Mews / creds / occupancy amounts / last_success / AMG-OCC preserved / NPWP / CAP-AMG-01
- `occupancy=null` · `adr=null` · `invented_occupancy=false`

### 2) API
- `GET /api/amg/occupancy-external-hold-1` (auth) → same board (alias `/api/ops/occupancy-external-hold-1`)
- Unsigned → **403**
- POST invent occupancy / ADR / unblock PMS / invent NPWP / prod_mutate / staff_ready → **403**

### 3) Honesty stamps
| Pin | Value |
| --- | --- |
| classification | **EXTERNAL_BLOCKER** |
| yanolja_status | **EXTERNAL_BLOCKER** |
| occupancy / adr / revpar | **null** |
| invented_occupancy / invented_adr / fake_occupancy | **false** |
| AMG-OCC-TRUTH-1 | **PRESERVED** |
| NPWP | **MATT_ACTION** · non-blocking |
| `staff_ready` / `human_commissioned` | **false** |
| unknown_forever_replaced | **true** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_occupancy_external_hold1_20260930.py` | **PASS=136 FAIL=0** |

Shots: `docs/wolf/ops/shots/occupancyhold1-desk-desktop.png`, `occupancyhold1-desk-phone.png`, `occupancyhold1-blocker-stamps.png`, `occupancyhold1-unsigned-deny.png`.

## Files

- Core: `scripts/core/occupancy_external_hold1.py`
- Serve: `scripts/serve_beta.py` (`_occupancy_external_hold1_dispatch` + write refuse)
- UI: `dashboards/occupancy-external-hold-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_occupancy_external_hold1_20260930.py`
- Stamp: `state/final-completion/packs/OCCUPANCY-EXTERNAL-HOLD-1-ARM.json`
- Classification: `state/final-completion/CLASSIFICATION-LOG-20260930.json`

## Out of scope (not started from this EXIT)

- **WAVE9-SYNTH-CONTINUE** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake occupancy, invent ADR/RevPAR, unblocking Yanolja/Mews / CAP-AMG-01
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags

## Classification

Ceiling **AMG occupancy UNKNOWN / Yanolja BLOCKED** → **EXTERNAL_BLOCKER** (evidenced).  
AMG-OCC honesty preserved. Occupancy path is no longer UNKNOWN forever — pinned EXTERNAL with Yanolja/Mews evidence. NPWP stays MATT_ACTION non-blocking.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification EXTERNAL_BLOCKER · AMG-OCC preserved · NPWP MATT_ACTION non-blocking · no push · did not auto-chain next pack.
