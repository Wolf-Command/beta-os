# ESB-SETTLEMENT-PATH-1 RESULT — Settlement path probe → EXTERNAL_BLOCKER

**As of:** 2026-09-30 ~08:20 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start SOP-CATALOG-SEED-ROUTE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack ESB-SETTLEMENT-PATH-1** (armed after METRICOOL-RUNTIME-WIRE-1 PASS_VERIFIED).  
Challenges ESB PARTIAL / settlement UNAVAILABLE ceiling.  
**Probe first. No authorised settlement path or credentials → stamp EXTERNAL_BLOCKER with evidence (not UNKNOWN forever).**  
**No fake settlement · no invented P&L · no ESB write.**  
Preserves **ESB-TRUTH-1** warehouse RO honesty (`settlement_api=UNAVAILABLE` on that board).  
Honest close-toward: **INT-ESB** + **CAP-INTG-02**.

## Probe findings

| Probe | Result | Evidence |
| --- | --- | --- |
| Settlement API path / client | **EXTERNAL_BLOCKER** | No settlement client in `scripts/`; Felix 2026-07-19 CONFIRMED UNAVAILABLE via API |
| Settlement / ESB API credentials | **EXTERNAL_BLOCKER** | No `SETTLEMENT` / `ESB_API` / `ESB_URL` / `ESB_TOKEN` keys in process env, `.env`, or `.env.example` (names only; values never loaded) |
| Authorised connector scope | **EXTERNAL_BLOCKER** | Owner approval: ESB YES observe / WRITE NO FOR NOW; settlement not authorised |
| Warehouse RO (ESB-TRUTH-1) | **PRESERVED** | `PARTIAL_IN_BETA` · `settlement_api=UNAVAILABLE` · pnl/settlement null |
| Human commissioning | **ABSENT** | Vendor API missing — commissioning cannot unlock a non-existent settlement report path |
| Settlement amounts / P&L / last_success | **null** | Never invent |

Felix pin: `docs/deliveries/BZG-UMA-BLU-OPERATIONS-DISCOVERY-2026-09-17.md` (2026-07-19).  
Canon: `docs/canon/UMA-BLU-DAILY-CLOSE.md` — Settlement API **UNAVAILABLE** (Felix).

## What landed

### 1) Probe board
- Page `/ops/esb-settlement-path-1` (`dashboards/esb-settlement-path-1.html`)
- Classification pin **EXTERNAL_BLOCKER**
- Surfaces: path / creds / connector / warehouse / amounts / last_success / human-commissioning
- `settlement=null` · `pnl=null` · `fake_settlement=false`

### 2) API
- `GET /api/ops/esb-settlement-path-1` (auth) → same board
- Unsigned → **403**
- POST `settlement` / `pnl` / `esb_write` / `prod_mutate` / `staff_ready` → **403**

### 3) INTG overlay
- INT-ESB-WOLF stays **PARTIAL_IN_BETA** (warehouse)
- `probe_status` → `WAREHOUSE_READ_OK_PARTIAL_SETTLEMENT_EXTERNAL_BLOCKER`
- `honesty.esb_settlement` → **EXTERNAL_BLOCKER**

### 4) Honesty stamps
| Pin | Value |
| --- | --- |
| classification | **EXTERNAL_BLOCKER** |
| settlement_api (this pack) | **EXTERNAL_BLOCKER** |
| ESB-TRUTH-1 settlement_api | **UNAVAILABLE** (preserved) |
| pnl / settlement | **null** |
| fake_settlement / pnl_invented / esb_write | **false** |
| `staff_ready` / `human_commissioned` | **false** |
| unknown_forever_replaced | **true** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_esb_settlement_path1_20260930.py` | **PASS=122 FAIL=0** |

Shots: `docs/wolf/ops/shots/esbsettlement1-desk-desktop.png`, `esbsettlement1-desk-phone.png`, `esbsettlement1-blocker-stamps.png`, `esbsettlement1-unsigned-deny.png`.

## Files

- Core: `scripts/core/esb_settlement_path1.py`
- Serve: `scripts/serve_beta.py` (`_esb_settlement_path1_dispatch` + write refuse)
- UI: `dashboards/esb-settlement-path-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- INTG overlay: `scripts/core/intg_truth_board.py`
- Tests: `scripts/tests/test_esb_settlement_path1_20260930.py`
- Stamp: `state/final-completion/packs/ESB-SETTLEMENT-PATH-1-ARM.json`
- Classification: `state/final-completion/CLASSIFICATION-LOG-20260930.json`

## Out of scope (not started from this EXIT)

- **SOP-CATALOG-SEED-ROUTE-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake settlement, invent P&L, write ESB, flipping commissioning flags
- HEADCHEF / Exit Report / prod mutate / push

## Classification

Ceiling **ESB PARTIAL_IN_BETA / settlement UNAVAILABLE** → **EXTERNAL_BLOCKER** (evidenced).  
Warehouse RO remains PARTIAL_IN_BETA. Settlement path is no longer UNKNOWN forever.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification EXTERNAL_BLOCKER · ESB-TRUTH-1 preserved · no push · did not auto-chain next pack.
