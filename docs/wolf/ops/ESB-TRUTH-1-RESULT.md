# ESB-TRUTH-1 RESULT — ESB warehouse truth board (PARTIAL_IN_BETA deepen)

**As of:** 2026-09-30 ~02:42 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start BACKUP-HEALTH-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack ESB-TRUTH-1** (armed after OWNER-NEEDS-YOU-1 PASS_VERIFIED).  
Read-only ESB warehouse status board on Beta — deepens **PARTIAL_IN_BETA** honesty beyond INTG-TRUTH-1 summary.  
**No fake settlement · no invented P&L · no ESB write · UNKNOWN when missing.**  
Preserves **INTG-TRUTH-1** + **BZG-VENUEPL-1**.  
Honest close-toward: **INT-ESB** + **CAP-BZG ESB**.

## What landed

### 1) Warehouse truth board
- Page `/ops/esb-truth-1` (`dashboards/esb-truth-1.html`; alias `/esb-truth-1`)
- Audit stamp **PARTIAL_IN_BETA** (not a full connector prove)
- Warehouse RO probe (`READ_OK` when sales table present)
- Table inventory with live RO row counts (facts only)
- Sales date-range facts (`min_biz_date` / `max_biz_date` / `row_count`) — **not settlement, not P&L**
- `venue_daily_closes` surfaced honestly (0 this run)
- `settlement_api=UNAVAILABLE` · `pnl=null` · `last_success=null`

### 2) API
- `GET /api/ops/esb-truth-1` (auth) → same slice
- Unsigned → **403** (fail-closed)
- POST `esb_write` / `settlement` / `pnl` → **403** (`esb_write_refused` / `settlement_refused` / `pnl_refused`)

### 3) Honesty stamps
| Pin | Value |
| --- | --- |
| audit_status | **PARTIAL_IN_BETA** |
| settlement_api | **UNAVAILABLE** |
| pnl / settlement | **null** (UNKNOWN — not invented) |
| pnl_invented / settlement_invented / fake_settlement | **false** |
| esb_write / esb_mutated | **false** |
| last_success | **null** |
| `staff_ready` / `human_commissioned` | **false** |

### 4) Preserved packs (read-only)
| Pack | Status |
| --- | --- |
| INTG-TRUTH-1 | **PRESERVED** — INT-ESB-WOLF stays PARTIAL_IN_BETA · pnl_invented=false |
| BZG-VENUEPL-1 | **PRESERVED** — no invented revenue/cost · live_pnl=false |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_esb_truth1_20260930.py` | **PASS=152 FAIL=0** |

Shots: `docs/wolf/ops/shots/esbtruth1-board-desktop.png`, `esbtruth1-board-phone.png`, `esbtruth1-partial-stamps.png`, `esbtruth1-warehouse-inventory.png`, `esbtruth1-unsigned-deny.png`.

## Files

- Core: `scripts/core/esb_truth1.py`
- Serve: `scripts/serve_beta.py` (`_esb_truth1_dispatch` + write refuse)
- UI: `dashboards/esb-truth-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_esb_truth1_20260930.py`
- Stamp: `state/final-completion/packs/ESB-TRUTH-1-ARM.json`

## Out of scope (not started from this EXIT)

- **BACKUP-HEALTH-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake settlement, invent P&L, write ESB, flipping commissioning flags
- HEADCHEF / Exit Report / prod mutate / push

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
