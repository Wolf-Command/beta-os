# RELIABILITY-PIPE-EPISODE-ROLLUP-1 RESULT — Pipe flap episode rollup

**As of:** 2026-09-30 ~10:38 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `e2e9889`)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start WAVE11-SYNTH-CONTINUE / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave10 pack RELIABILITY-PIPE-EPISODE-ROLLUP-1** (armed after HR-DEFERRED-HOLD-STAMP-1 PASS_VERIFIED 135/0).  
Rolls up Wave7–10 Mac local-exec pipe flaps from `CLASSIFICATION-LOG-20260930.json#pipe_flaps` (+ `pipe_flap_observed`) merged with prior **PIPE-RELIABILITY-AUTO-1** episodes into an evidence-only rollup board.  
Live probe stays **GREEN / DOWN / UNKNOWN** with `last_probe_at` — **no invented uptime %**.  
Preserves **PIPE-RELIABILITY-AUTO-1** + **RELIABILITY-1**. Classification **INTERNALLY_SOLVABLE**. Ceiling **BUILT** only (SHELL≠COMPLETE).

## What landed

### 1) Live probe (real status at EXIT)
| Field | Value |
| --- | --- |
| status | **GREEN** (hostname Wolfs-Mac-Studio proven) |
| last_probe_at | live on each board load |
| probe | `hostname+date` (delegates to PIPE-RELIABILITY-AUTO-1) |
| uptime % | **null** (never invent) |
| painted_green / fake_pipe_up | **false** |

### 2) Episode rollup (evidence — not uptime %)
| Count | Value |
| --- | --- |
| episode_count | **10** |
| flap_count | **9** |
| wave_span | Wave7–10 |
| overnight | PARKED_MAC_PIPE → UNPARKED_PIPE_OK ~07:23 |

Sources:
- `CLASSIFICATION-LOG-20260930.json#pipe_flaps` (8 flaps) + `#pipe_flap_observed`
- `PIPE-RELIABILITY-AUTO-1-EPISODES.json` (overnight + early flaps)

Stamp: `state/final-completion/packs/RELIABILITY-PIPE-EPISODE-ROLLUP-1-EPISODES.json`

### 3) Auth page + API
- Page `/ops/reliability-pipe-episode-rollup-1` (+ aliases)
- API `GET /api/ops/reliability-pipe-episode-rollup-1`
- Unsigned → **403**
- POST/PATCH/PUT invent-uptime / fake-pipe-up / force-green / prod-mutate / staff_ready → **403** refused

### 4) Preserved
| Surface | Status |
| --- | --- |
| PIPE-RELIABILITY-AUTO-1 (3 episodes, probe board) | **PRESERVED** |
| RELIABILITY-1 (`mac_pipe` + 3 listeners) | **PRESERVED** |

## Classification pin

| Shell / residue | Classification | Why |
| --- | --- | --- |
| Pipe flap episode rollup (this pack) | **INTERNALLY_SOLVABLE** | Wire evidence only; never invent uptime |
| Ceiling | **BUILT** | Not COMPLETE · TESTS≠STAFF READY |
| Next WAVE11-SYNTH-CONTINUE | **parent/Peaches** | Cursor did not auto-chain |
| Exit Report / HEADCHEF | **MATT_ACTION** | Forbidden until Phase 13 / separate Matt arm |
| Prod mutate / push / fake uptime | **EXTERNAL_BLOCKER** | Hard rule — pid 15975 held RO |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_reliability_pipe_episode_rollup1_20260930.py` | **PASS=129 FAIL=0** |

Shots: `docs/wolf/ops/shots/piperollup1-desk-desktop.png`, `piperollup1-desk-phone.png`, `piperollup1-episodes.png`, `piperollup1-unsigned-deny.png` (4 distinct sha256).

## Files

- Core: `scripts/core/reliability_pipe_episode_rollup1.py`
- Serve: `scripts/serve_beta.py` (`_reliability_pipe_episode_rollup1_dispatch` + write refuse)
- Shell: `scripts/core/wolf_shell.py`
- UI: `dashboards/reliability-pipe-episode-rollup-1.html`
- Tests: `scripts/tests/test_reliability_pipe_episode_rollup1_20260930.py`
- Stamp: `state/final-completion/packs/RELIABILITY-PIPE-EPISODE-ROLLUP-1-EPISODES.json`
- ARM: `state/final-completion/packs/RELIABILITY-PIPE-EPISODE-ROLLUP-1-ARM.json`

## Out of scope (not started from this EXIT)

- **WAVE11-SYNTH-CONTINUE** (next — Peaches/parent synthesizes after verify; Cursor must not auto-chain)
- Fake uptime %, invent GREEN, flip staff_ready
- HEADCHEF / Exit Report / prod mutate / push

## Classification

Ceiling **BUILT** · classification **INTERNALLY_SOLVABLE**.  
Evidence rollup only. Mac pipe = Reliability completion issue — flaps stamped, never painted as continuous uptime.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification INTERNALLY_SOLVABLE · ceiling BUILT · episodes=10 · flaps=9 · live GREEN · no fake uptime · no push · did not auto-chain next pack.
