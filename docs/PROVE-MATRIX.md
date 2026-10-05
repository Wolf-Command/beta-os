# PROVE MATRIX — Mac Reachability supervised recovery

**Authority:** RULE-Wolf-Mac-Exec-Autonomy-No-Matt-Restart-2026-09-23  
**Requirement:** Controlled prove — not unit tests alone.  
**Gate:** `FAILURE → DETECT → AUTO-RECOVER → VERIFY → RESUME` proved **TWICE** end-to-end **without Matt**.

Pipe is currently DOWN on box write — cases below are the apply-time checklist when Mac GREEN. Do not mark proved until both runs recorded in `state/mac-reachability/prove-runs.jsonl`.

---

## Global pass criteria (every case)

1. DETECT fires (audit.jsonl reason_code) without human
2. CLASSIFY correct code
3. AUTO-RECOVER within ceiling; **no** Matt open/pkill/reconnect ask
4. VERIFY: `connected=true` + Shell echo OK + (`bf_watch` readable **or** Pulse :8787 proves)
5. RESUME: LKG/ACTIVE restored or independent park rules held
6. health returns `HEALTHY` (or `BLOCKED` only for ceiling/Needs-Matt classes)

Wrong if: Matt pinged for routine reconnect; fake GREEN; ACTIVE wiped; infinite restart.

---

## Cases

| ID | Inject | Expect DETECT | Expect recover | Expect after VERIFY | Notes |
|----|--------|---------------|----------------|---------------------|-------|
| P1 | Kill local-exec-daemon only | `LOCAL_EXEC_DEAD` | LaunchAgent/kickstart restart daemon | Shell+bf_watch OK; factory resumes | GUI may stay; prove path not process alone |
| P2 | Kill / quit Grok Bot agent (or force agent exit) | `GROK_BOT_DEAD` or `PIPE_DISCONNECTED` | Supervised relaunch (LaunchAgent), not Matt open | connected=true + prove | Must survive later GUI close |
| P3 | Half-dead: leave process, break exec path (e.g. stuck daemon accepting no Shell) | `HALF_DEAD_PATH` | Restart path | Prove passes | Process-alive alone must fail VERIFY before recover |
| P4 | Freeze heartbeat writer (stale file > STALE_AFTER_SEC) | `STALE_HEARTBEAT` | Probe; recover if prove fail else heal writer | Fresh heartbeat + HEALTHY | STALE ≠ automatic kill if prove still OK |
| P5 | Factory ACTIVE (`WAITING_CURSOR` or similar) during pipe fail | `FACTORY_ACTIVE_DURING_FAIL` (+ pipe code) | Recover; **preserve ACTIVE/LKG** | bf_watch resumes same run; no Matt re-arm | Mirror overnight failure mode |
| P6 | Idle-with-work (queue has staged work, no ACTIVE) during fail | `IDLE_WITH_WORK_DURING_FAIL` | Recover; park Mac apply until GREEN | On GREEN, supervisor may pick next; no Matt | Independent box work never stops |
| P7 | Force retries to ceiling | `CEILING_REACHED` | Stop thrash; health=`BLOCKED` | Park pipe-dependent only; continue independent; escalate only if Needs Matt class | No Matt open-app card |
| P8 | Independent branch (box docs / CR) during fail | n/a detect on pipe | n/a | Independent work continues uninterrupted | Prove non-coupling |
| P9 | Resume persisted work after recover | post-recover | LKG reload | ACTIVE stage continues from LKG | Twice: run A then run B |

---

## Double-prove protocol

### Run A (first)
1. Snapshot LKG + ACTIVE + heartbeat → `prove-runs.jsonl` prelude
2. Execute P1→P9 (or critical subset P1,P2,P3,P5,P7,P9 if time-boxed — full matrix preferred)
3. Record each: inject_ts, detect_ts, recover_method, verify_evidence, resume_evidence, matt_contacted=false
4. Require full chain on at least P1, P2, P5, P9

### Run B (second — after cool-down ≥ INCIDENT_WINDOW or clean state reset)
1. Repeat critical chain P1, P2, P5, P9 minimum
2. Confirm no residual thrash (retry_counter reset after HEALTHY)
3. Confirm `mac-computers-pipe-watch` did **not** emit Matt fix-card

### Pass stamp
Only when Run A **and** Run B both have `matt_contacted=false` and VERIFY evidence attached:
```
PROVED_TWICE=true
proved_wita=<stamp>
proved_by=Link+Pulse
```

Until then: completion register stays OPEN (`/workspace/state/completion-register/wolf-mac-exec-autonomy-20260923.json`).

---

## Explicit fail conditions

- Any “please open Grok Bot” to Matt
- GREEN claimed from ListMachines alone
- ACTIVE cleared to dodge resume
- LaunchAgent not installed yet but case marked proved
- Pipe still DOWN and cases marked proved from box alone
