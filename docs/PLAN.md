# Mac Reachability — Supervised Recovery Lifecycle (Link)

**Role:** Link (Mac Reachability) on Wolf Command  
**Authority:** `/workspace/docs/RULE-Wolf-Mac-Exec-Autonomy-No-Matt-Restart-2026-09-23.md`  
**Companion:** `/workspace/docs/deliveries/MAC-PIPE-RECOVERY-ARCHITECTURE-2026-09-23.md`  
**Status:** DRAFT on box — Mac pipe `connected=false` (machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`). Not GREEN. Do not invent Studio online.  
**Target Mac paths (apply when pipe returns):**
- Doc: `/Users/wolfterminal/beta-os/docs/MAC-REACHABILITY-RECOVERY.md`
- Scripts: `/Users/wolfterminal/beta-os/scripts/mac-reachability/`
- State: `/Users/wolfterminal/beta-os/state/mac-reachability/`

---

## Goal

Eliminate Matt as the Mac / Grok Bot restart button. Factory must survive Grok Bot GUI close, local-exec death, and half-dead pipes via **supervised bounded auto-recovery** — never via “ask Matt to open app / pkill / reconnect.”

## Law (non-negotiable)

| Class | Action |
|-------|--------|
| Routine pipe death, daemon crash, GUI close, stale heartbeat, half-dead local-exec | AUTO-RECOVER (bounded) |
| Ask Matt to open Grok Bot / Cmd-Q / `pkill local-exec` / approve reconnect | **DEFECT** — file `wrong_escalation` |
| Physical power-off, physical macOS auth, Owner credential / Cloudflare gate, catastrophic hardware | Escalate to Matt **only** |

## Health enum (honest; never fake GREEN)

| State | Meaning |
|-------|---------|
| `HEALTHY` | Heartbeat fresh + execution path proved (Shell ping + bf_watch readable OR Pulse :8787 prove) |
| `DEGRADED` | Connected but prove weak / intermittent / one probe failing |
| `RECOVERING` | Inside bounded auto-recovery window |
| `BLOCKED` | Ceiling reached OR legitimate Needs Matt class |
| `STALE` | Heartbeat file older than stale threshold; process may still look “alive” |

**Invariant:** Process alive ≠ execution path proved. ListMachines `connected=true` alone is **not** GREEN. Require Shell machineId echo OK + factory path prove (`bf_watch` readable or Pulse content GETs).

---

## Lifecycle

```
HEALTH → DETECT → CLASSIFY → BOUNDED AUTO-RECOVERY → VERIFY → RESUME FACTORY STATE → AUDIT
                                    ↓ (ceiling)
                         PARK pipe-dependent only → CONTINUE independent work → escalate if genuine Needs Matt
```

### 1. HEALTH (continuous)

- **Heartbeat writer** (Mac LaunchAgent / supervised daemon): write `state/mac-reachability/heartbeat.json` every `HEARTBEAT_INTERVAL_SEC` (default 30s).
- Fields: `ts_wita`, `machineId`, `local_exec_pid`, `grok_bot_running` (bool), `path_prove_ok` (bool), `lkg_pointer`.
- **LKG (last-known-good):** on every successful VERIFY, atomically update `state/mac-reachability/lkg.json` (factory ACTIVE id/stage, cursor_pid if any, pipe prove stamp).
- Box-side Link/Pulse consumers read heartbeat age; if age > `STALE_AFTER_SEC` (default 120s) → health=`STALE`.

### 2. DETECT

Triggers (any):
- ListMachines missing or `connected=false` for `36d8fa4b…` / `Wolfs-Mac-Studio.local`
- Heartbeat stale
- Shell to machineId fails
- `path_prove_ok=false` while process claims alive (half-dead)
- Pulse Studio doctor RED (content APIs) while pipe claims up

Emit detect event → `state/mac-reachability/audit.jsonl` + optional Peaches ping (silent to Matt).

### 3. CLASSIFY → reason codes

| Code | Meaning | Auto-recover? |
|------|---------|---------------|
| `PIPE_DISCONNECTED` | Computers connected=false | Yes |
| `LOCAL_EXEC_DEAD` | local-exec-daemon not running | Yes |
| `GROK_BOT_DEAD` | Grok Bot agent path down (GUI or agent) | Yes (LaunchAgent / non-GUI relaunch preferred) |
| `HALF_DEAD_PATH` | Process up, Shell/prove fail | Yes (restart daemon path) |
| `STALE_HEARTBEAT` | Heartbeat aged out | Yes (probe + recover if prove fails) |
| `SERVE_8787_RED` | Pipe up, content API fail | Pulse lane; Link assists if Shell dead |
| `FACTORY_ACTIVE_DURING_FAIL` | ACTIVE run + pipe fail | Yes; preserve ACTIVE; do not clear |
| `IDLE_WITH_WORK_DURING_FAIL` | Queue has work, pipe fail | Park Mac apply only |
| `CEILING_REACHED` | retries ≥ ceiling | No further auto; park + continue independent |
| `NEEDS_MATT_POWER` | Physical power-off suspected | Escalate Matt |
| `NEEDS_MATT_AUTH` | Physical macOS auth | Escalate Matt |
| `NEEDS_MATT_CRED_CF` | Owner credential / CF approval | Escalate Matt |
| `NEEDS_MATT_HW` | Catastrophic hardware | Escalate Matt |
| `WRONG_ESCALATION` | Someone asked Matt to open/pkill | Defect audit |

### 4. BOUNDED AUTO-RECOVERY

Parameters (defaults; tune in `state/mac-reachability/config.json` once applied):

| Param | Default |
|-------|---------|
| `RETRY_CEILING` | 3 per incident window |
| `BACKOFF_SEC` | 15, 45, 120 (exponential) |
| `INCIDENT_WINDOW_SEC` | 1800 |
| `RECOVER_METHODS` | ordered: (1) restart local-exec-daemon via LaunchAgent kickstart (2) relaunch Grok Bot agent **without** requiring Matt GUI session if LaunchAgent owns it (3) soft reconnect probe |

Rules:
- Set health=`RECOVERING` for duration.
- Increment `retry_counter` in `state/mac-reachability/recovery.json`.
- Never infinite loop. On ceiling → `BLOCKED` + `CEILING_REACHED`.
- Never ask Matt for open app / pkill / reconnect.
- Do not wipe factory ACTIVE / LKG.

### 5. VERIFY (must prove execution path)

All required for `HEALTHY`:
1. ListMachines: `connected=true` for machineId
2. Shell: `echo OK` (or equivalent) on that machineId
3. Factory path: `python3 scripts/build-factory/bf_watch.py` readable / exits clean **OR** (Pulse lane) GET `:8787/api/content/today?brand=uma-blu` 200+week keys AND GET `:8787/api/content/habitat` 200

Process list alone = fail VERIFY.

### 6. RESUME FACTORY STATE

On VERIFY success:
1. Write new LKG
2. Reset retry_counter for this incident
3. health=`HEALTHY`
4. Peaches: unpark Mac-dependent branches
5. If LKG had ACTIVE (`WAITING_CURSOR` etc.): `bf_watch` → resume (child_alive WAIT; EXIT → Grok review path) — **no Matt re-arm**
6. Independent box work that continued during fail stays uninterrupted

### 7. AUDIT

Append every transition to `state/mac-reachability/audit.jsonl`:
`ts_wita, from_health, to_health, reason_code, retry, method, verify_result, wrong_escalation?`

Incident files under `/workspace/state/incidents/` when disappearance / ceiling / wrong escalation.

---

## Roles (reuse existing Pulse watches; Link owns recover)

| Lane | Owner | Box evidence today |
|------|-------|--------------------|
| Detect (doctor) | Pulse `studio-local-exec-watch` | `/home/box/sand-data/agents/2f05b355-…/automations/studio-local-exec-watch/` |
| Detect (pipe) | `mac-computers-pipe-watch` (**must stop Matt fix-card**) | `/home/box/sand-data/agents/3e37ef74-…/automations/mac-computers-pipe-watch/` |
| Cheap doctor | Pulse `pulse-doctor-watch` | `/home/box/sand-data/agents/3e37ef74-…/automations/pulse-doctor-watch/` |
| Recover | **Link** (this package) | Draft only on box until pipe GREEN |
| Orchestrate | Peaches | Park/unpark; no Matt reconnect |

**Wolf Pulse/Link persistent supervised service on Mac:** not found as installed LaunchAgent or local supervisor on the box filesystem. Prefer creating LaunchAgent templates in this package (see `scripts/`). `.config/pulse` on box is only a runtime symlink to `/tmp/pulse-*` — not Mac reachability supervision.

---

## Factory coupling

- Canon skill: `/home/box/sand-data/workflows/build-factory-self-drive/SKILL.md` → `bf_watch.py` on Mac.
- Current box idle: `/workspace/state/build-factory/IDLE-REASON.json` — `RUNNING_BUT_UNSUPERVISED` / `mac_studio_grok_bot_app_offline` (do not invent ACTIVE state change).
- On fail: park only Mac Shell / live-apply / :8787 prove / supervised factory apply. Keep box docs, CR drafts, cloud-agent briefs moving.

## Explicit non-goals (this draft)

- No Mac Shell apply while `connected=false`
- No LaunchAgent install from box
- No prod wolf-system DB touch
- No Ask Matt reconnect card

---

## Architecture docs (2026-09-23 Link pass — no thrash)

Next architecture (not recover thrash) while pipe DOWN:

- `LAUNCHAGENT-DESIGN.md` — supervised LaunchAgent labels (heartbeat / supervisor / optional local-exec); KeepAlive; heartbeat must not require GUI window; process alive ≠ path proved
- `BOOTSTRAP-PARADOX.md` — first install = one-time commission prove (not routine Needs Matt); apply checklist when pipe greens
- `ACTUATOR-AUDIT.md` — SSH/Tailscale/ansible/ping ABSENT; only path today Computers/local-exec; `BLOCKED_NEEDS_ACTUATOR`

Do not install LaunchAgents from box. Do not invent GREEN.

## SPEC alignment
See Peaches SPEC `/workspace/docs/deliveries/SPEC-Mac-Exec-Supervised-Recovery-2026-09-23.md` — A-class LaunchAgent KeepAlive; B-class physical/auth/Owner CF only; FD OPEN until prove ×2.
