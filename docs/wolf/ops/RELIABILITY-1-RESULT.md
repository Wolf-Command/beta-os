# RELIABILITY-1 RESULT — Beta health/reliability board

**As of:** 2026-09-30 ~02:00 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `766e5f8`)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` live · Sidecar `:8790` honest **DOWN**  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start CONTENT-ENGINE-LIVE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack RELIABILITY-1** (armed after DASH-LIVE-1 PASS_VERIFIED).  
Beta board `/ops/reliability` surfaces real lsof/kill(0) probes for listeners **8788 / 8790 / prod 15975**.  
**No invented uptime %.** Sidecar DOWN stays DOWN. Prod probe is READ-ONLY only.  
Preserves **INTG-TRUTH-1** honesty. Honest close-toward: **IL-R8** + MasterSpec reliability (ceiling **BUILT**; not PROVEN/READY).

## What landed

### 1) Probe targets (real status at EXIT)
| Target | Port / Pid | Status | Uptime % | Honesty |
| --- | --- | --- | --- | --- |
| Beta listener | `:8788` | **UP** | `null` | lsof LISTEN |
| Atrium sidecar | `:8790` | **DOWN** | `null` | no listener — not painted UP |
| Prod (RO) | `:8787` pid **15975** | **UP** | `null` | lsof + kill(0); no mutate |

### 2) Auth page + API
- Page `/ops/reliability` (+ aliases) — honesty banner + probe table
- API `GET /api/ops/reliability` — targets envelope from real probes
- Unsigned / deny → **403** (fail-closed)
- POST/PATCH/PUT invent-uptime / prod-mutate / commissioning flips → **403** refused

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| `staff_ready` / `human_commissioned` | **false** |
| `fake_uptime` / `invented_uptime` / `invented_green_health` | **false** |
| `uptime_pct` on every target | **null** (never invent) |
| `prod_mutate` | **false** · pid 15975 held RO |
| Ceiling | **BUILT** · not PROVEN/READY |
| Next pack | **CONTENT-ENGINE-LIVE-1** (parent/Peaches only — Cursor did not auto-chain) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_reliability1_20260930.py` | **PASS=106 FAIL=0** |

Shots: `docs/wolf/ops/shots/reliability1-board-desktop.png`, `reliability1-board-phone.png`, `reliability1-sidecar-status.png`, `reliability1-unsigned-deny.png` (4 distinct sha256).

## Files

- Core: `scripts/core/reliability1.py`
- Wire: `scripts/serve_beta.py` (page/API/POST·PATCH·PUT refuse)
- Shell alias: `scripts/core/wolf_shell.py`
- UI: `dashboards/reliability.html`
- Tests: `scripts/tests/test_reliability1_20260930.py`
- Stamp: `state/final-completion/packs/RELIABILITY-1-ARM.json`

## Out of scope (not started from this EXIT)

- **CONTENT-ENGINE-LIVE-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake uptime, invented green health, flipping commissioning flags
- HEADCHEF / Exit Report / prod mutate / push

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · sidecar DOWN honest · no push · did not auto-chain next pack.
