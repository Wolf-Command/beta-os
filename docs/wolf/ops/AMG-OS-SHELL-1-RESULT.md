# AMG-OS-SHELL-1 RESULT — AMG operating shell without Yanolja live

**As of:** 2026-09-30 ~00:39 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral · Sidecar `:8790` not required for this pack  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start GGV-CONTENT-PROVE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OS-SHELL-1** (armed 2026-09-30) — structure toward **CAP-AMG-02 / CAP-AMG-04 / MB-008** only.  
**Does not unblock CAP-AMG-01** (Yanolja). INTG honesty board remains source of truth for INT-YAN-WOLF.

## What landed

### 1) AMG operating shell
- Page `/amg/os-shell` (`dashboards/amg-os-shell.html`; aliases `/amg-os-shell`)
- Day-ops tiles: **arrivals · departures · rooms · guest requests · occupancy**
- Every PMS-dependent tile: **BLOCKED_EXTERNAL** stamp · display **UNKNOWN** · `value`/`count`/`occupancy_pct` null · link to `/ops/integrations-status`
- Non-PMS structure links: My Work, AMG Today desk, Atrium finance desk, daily-ops framework, honesty board
- Commissioning OPEN holds from catalog (real count) — not hotel occupancy

### 2) API
- `GET /api/amg/os-shell` (auth) → shell payload
- Unsigned → **403** (fail-closed)

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| INT-YAN-WOLF | **BLOCKED_EXTERNAL** · last_success null |
| PMS tiles | **BLOCKED_EXTERNAL** · UNKNOWN (never zeros-as-success) |
| `cap_amg_01_unblocked` | **false** |
| `staff_ready` / `human_commissioned` | **false** |
| `fake_pms_data` / invented occupancy/arrivals | **false** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_amg_os_shell1_20260930.py` | **PASS=97 FAIL=0** |

Shots: `docs/wolf/ops/shots/amgoshell1-shell-desktop.png`, `amgoshell1-shell-phone.png`, `amgoshell1-yanolja-blocked.png`, `amgoshell1-unsigned-deny.png`.

## Files

- Core: `scripts/core/amg_os_shell.py`
- Serve: `scripts/serve_beta.py` (`_amg_os_shell_dispatch`)
- UI: `dashboards/amg-os-shell.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_amg_os_shell1_20260930.py`
- Stamp: `state/final-completion/packs/AMG-OS-SHELL-1-ARM.json`

## Out of scope (not started from this EXIT)

- **GGV-CONTENT-PROVE-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Seating Yanolja, inventing occupancy/arrivals, claiming CAP-AMG-01 unblocked
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
