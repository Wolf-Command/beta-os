# INTG-TRUTH-1 RESULT — Integration honesty board (no fake live feeds)

**As of:** 2026-09-30 ~00:33 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` restarted (LaunchAgent) with board routes · Sidecar `:8790` RO only (not required for this pack)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start AMG-OS-SHELL-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INTG-TRUTH-1** (armed 2026-09-30) — closes toward **MB-015 / INT-\* SPECIFIED honesty**.  
Seed: `docs/canon/build-dashboard/Integrations.csv` + `state/final-completion/PHASE3-INTEGRATIONS-AUDIT.json`.

## What landed

### 1) Honesty board
- Page `/ops/integrations-status` (`dashboards/integrations-status.html`)
- Lists every connector from CSV ∪ Phase3 audit (deduped by `integration_id`)
- Fields: integration_id, source→target, audit_status, probe_status, last_success (**null if unknown — never invented**), blocked_external, write_authority=`NONE_EXPANDED`, secrets_exposed=`false`

### 2) API
- `GET /api/ops/integrations-status` (auth) → same registry
- Unsigned → **403** (fail-closed). Live Beta CF-Access mode also denies bare `X-Wolf-Subject` without JWT (same posture as `/api/ops/v1-status`).

### 3) Safe probes only
| Connector | Honesty stamp | Probe |
| --- | --- | --- |
| INT-YAN-WOLF | **BLOCKED_EXTERNAL** | DOCUMENTED_BLOCKER — no live call |
| INT-ESB-WOLF | **PARTIAL_IN_BETA** | Warehouse RO (`READ_OK`) + `venue_daily_closes=0`; **P&L not invented**; last_success null |
| INT-BANK-WOLF | file-import-only | FILE_IMPORT_ONLY — no bank API |
| INT-MET-WOLF | Wolf runtime | **NOT_RUNTIME** (status() no creds/network) |
| MCP-Metricool | **AGENT_HOST_ONLY** | Agent-host MCP ≠ Wolf runtime |

### 4) Audit sync
`PHASE3-INTEGRATIONS-AUDIT.json` status → `BOARD_SYNCED_READ_ONLY` with live probe fields; still read-only posture (`secrets_exposed=false`, `write_authority_expanded=false`).

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_intg_truth1_20260930.py` | **PASS=130 FAIL=0** |

Shots: `docs/wolf/ops/shots/intgtruth1-board-desktop.png`, `intgtruth1-board-phone.png`, `intgtruth1-yanolja-blocked.png`, `intgtruth1-unsigned-deny.png`.

## Files

- Core: `scripts/core/intg_truth_board.py`
- Serve: `scripts/serve_beta.py` (`_intg_truth_dispatch`)
- UI: `dashboards/integrations-status.html`
- Shell alias: `scripts/core/wolf_shell.py` (html → `/ops/integrations-status`)
- Tests: `scripts/tests/test_intg_truth1_20260930.py`
- Audit: `state/final-completion/PHASE3-INTEGRATIONS-AUDIT.json`
- Stamp: `state/final-completion/packs/INTG-TRUTH-1-ARM.json`

## Out of scope (not started from this EXIT)

- **AMG-OS-SHELL-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Seating Yanolja keys, fake live feeds, bank payment write, expanding secrets UI write
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
