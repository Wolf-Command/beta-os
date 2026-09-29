# PIPE-RELIABILITY-AUTO-1 RESULT — Mac local-exec pipe detect/recover

**As of:** 2026-09-30 ~07:51 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `981fcf5`)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start METRICOOL-RUNTIME-WIRE-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack PIPE-RELIABILITY-AUTO-1** (armed after BACKUP-RESTORE-DRILL-1 PASS_VERIFIED).  
Matt: Mac pipe = Reliability completion issue — detect/recover under reliability reqs.  
Surfaces Mac local-exec pipe as **GREEN / DOWN / UNKNOWN** with `last_probe_at` on `/ops/reliability` + dedicated board.  
Auto-detect probe = `hostname` + `date` heartbeat. Documented recover path (retry / re-attach).  
Stamps overnight PARKED_MAC_PIPE → UNPARKED_PIPE_OK + observed flaps as **evidence only** — **no invented uptime %**.  
Preserves **RELIABILITY-1** + **BACKUP-HEALTH-1**. Classification **INTERNALLY_SOLVABLE**.

## What landed

### 1) Mac pipe probe (real status at EXIT)
| Field | Value |
| --- | --- |
| status | **GREEN** (hostname Wolfs-Mac-Studio.local proven) |
| last_probe_at | live on each board load |
| probe | `hostname+date` |
| uptime % | **null** (never invent) |
| painted_green / fake_pipe_up | **false** |
| expected_hostname | Wolfs-Mac-Studio |
| expected_machine_id | `36d8fa4b-2d58-4983-b227-e5bfa5495e78` |

### 2) Episodes stamped (evidence — not uptime %)
| Episode | WITA | Transition |
| --- | --- | --- |
| overnight unpark | ~07:23 → 07:27 | PARKED_MAC_PIPE → UNPARKED_PIPE_OK (hostname proven) |
| brief unreachable | ~07:28 | flap during unpark work → PIPE_OK |
| babysit flap | ~07:36–07:40 | flap during BACKUP-RESTORE-DRILL-1 → PIPE_OK |

Log: `state/final-completion/packs/PIPE-RELIABILITY-AUTO-1-EPISODES.json`

### 3) Recover path (documented)
- Confirm machineId routes to Wolfs-Mac-Studio (not box sameMachine)
- Retry Shell / agent on Mac workspace `/Users/wolfterminal/beta-os`
- Re-probe hostname + date; unpark stamps UNPARKED_PIPE_OK when reachable
- Never invent GREEN or uptime %; DOWN stays DOWN until probe proves Mac

### 4) Auth page + API
- Page `/ops/pipe-reliability-auto-1` (+ aliases) — status / episodes / recover
- API `GET /api/ops/pipe-reliability-auto-1` — envelope with GREEN/DOWN/UNKNOWN + last_probe_at
- Reliability board `/ops/reliability` + API surface `mac_pipe` object
- Unsigned → **403**
- POST/PATCH/PUT invent-uptime / force-green / prod-mutate / staff_ready → **403** refused

### 5) Preserved
| Surface | Status |
| --- | --- |
| RELIABILITY-1 listeners (8788 / 8790 / prod RO) | **PRESERVED** (targets still 3; sidecar honesty intact) |
| BACKUP-HEALTH-1 | **PRESERVED** |

## Classification pin

| Shell / residue | Classification | Why |
| --- | --- | --- |
| Mac local-exec pipe detect/recover (this pack) | **INTERNALLY_SOLVABLE** | Probe + episodes + recover path on Beta |
| Next pack METRICOOL-RUNTIME-WIRE-1 | **INTERNALLY_SOLVABLE** | Parent/Peaches arms after verify — Cursor did not auto-chain |
| Exit Report / HEADCHEF | **MATT_ACTION** | Forbidden until Phase 13 / separate Matt arm |
| Prod mutate / push / fake uptime | **EXTERNAL_BLOCKER** | Hard rule — pid 15975 held RO |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_pipe_reliability_auto1_20260930.py` | **PASS=111 FAIL=0** |

Shots: `docs/wolf/ops/shots/pipe1-desk-desktop.png`, `pipe1-desk-phone.png`, `pipe1-reliability-surface.png`, `pipe1-unsigned-deny.png` (4 distinct sha256).

## Files

- Core: `scripts/core/pipe_reliability_auto1.py`
- Reliability surface: `scripts/core/reliability1.py` (`mac_pipe` on board)
- Serve: `scripts/serve_beta.py` (`_pipe_reliability_auto1_dispatch` + write refuse)
- Shell: `scripts/core/wolf_shell.py`
- UI: `dashboards/pipe-reliability-auto-1.html` + `dashboards/reliability.html` Mac pipe section
- Tests: `scripts/tests/test_pipe_reliability_auto1_20260930.py`
- Episodes: `state/final-completion/packs/PIPE-RELIABILITY-AUTO-1-EPISODES.json`
- Stamp: `state/final-completion/packs/PIPE-RELIABILITY-AUTO-1-ARM.json`

## Out of scope (not started from this EXIT)

- **METRICOOL-RUNTIME-WIRE-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake uptime %, inventing GREEN, continuous-uptime claims
- HEADCHEF / Exit Report / prod mutate / push
- Flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · Mac pipe GREEN with last_probe_at · episodes stamped · no fake uptime · no push · did not auto-chain next pack.
