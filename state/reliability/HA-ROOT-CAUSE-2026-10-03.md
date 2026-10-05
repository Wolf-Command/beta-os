# HA ROOT CAUSE — 2026-10-03

**Workspace:** `/Users/wolfterminal/beta-os` only (wolf-system not used)  
**Decision / Owner order:** `state/reliability/HA-OS-P0-2026-10-03.md` (3 Oct 2026). Offer to log into `~/.openclaw/wolf-output/decisions.md` if not already entered.  
**Prod `:8787`:** READ-ONLY — not mutated this run  
**Stamps:** no ENG_PROVED · no staff_ready · LaunchAgents installed ≠ PASS · reconnect ≠ PASS

## Host language (now)

| Probe | Evidence | Classification |
| --- | --- | --- |
| Host uptime | `uptime` → 45 days; Darwin Wolfs-Mac-Studio | **HOST ONLINE** |
| Prod listen | `lsof :8787` → Python pid **15975** | WOLF SERVICE ONLINE (prod) |
| Beta listen | `lsof :8788` → Python (restarted this run; was 34207, now new pid) | WOLF SERVICE ONLINE (beta) |
| Tunnel | `cloudflared … tunnel run wolf-dash` running | NETWORK path present |
| Cursor GUI | `/Applications/Cursor.app` pid 63110 since 18 Sep | GUI process alive |
| Private agent worker | pid 63443 · sock since 18 Sep · workspace **wolf-system** | worker process alive |
| `local-exec-daemon` OS process | `pgrep -f local-exec-daemon` → **absent**; heartbeat `local_exec_pid: null` | probe class LOCAL_EXEC_DEAD |
| Mac-reach supervisor | LaunchAgent running; audit spam LOCAL_EXEC_DEAD → CEILING_REACHED every ~20s since 2026-10-02 16:29 | CONTROL recovery **BLOCKED** (sticky ceiling) |

**Current overall (honest):** **HOST ONLINE / CONTROL DEGRADED**  
Control can execute via this Cursor Agent CLI session on `beta-os` (PIPE_OK class ~10:44 WITA per Owner brief + vision pack STATUS). The Mac-reach supervisor still classifies LOCAL_EXEC_DEAD permanently. Do **not** say “Mac offline.”

Incident INCIDENT-20261003-0712: **CONTROL PATH DOWN** at ~07:12 per Owner brief until host-down proved — host-down **not** proved → `legitimate_needs_matt=false`.

---

## Phase 1 — failure mechanism (evidence vs UNKNOWN)

### PROVED (mechanism / contributing defects)

1. **Supervisor probe looks for a process name that is not present**  
   - Code: `scripts/mac-reachability/supervisor.sh` → `pgrep -f 'local-exec-daemon'`  
   - Live: no such process; heartbeat writes `"local_exec_pid": null` continuously.  
   - Cursor agent-worker logs show in-process **`exec-daemon` / `exec_daemon`** (bridge mode), not a separate OS binary named `local-exec-daemon`.

2. **Recovery cannot spawn the missing control daemon**  
   - `watchdog-path.json`: `"local_exec_plist": "SKIPPED_unknown_ProgramArguments"`  
   - `recover.sh` only `launchctl kickstart` on **supervisor itself** (circular), then exits 0 until sticky ceiling.  
   - `recovery.json` frozen at `retry_counter: 3` / ceiling 3 since 2026-10-02 16:31 → every loop immediately **CEILING_REACHED**.

3. **Host + Wolf services can be healthy while control probe is red**  
   - Matches Owner symptom class. Audit from MAC-APPLY install (2026-10-02 16:29) through 2026-10-03 morning is **only** `LOCAL_EXEC_DEAD` + `CEILING_REACHED` (no HOST OFFLINE reason codes in this file).

4. **Private worker ≠ beta-os factory path**  
   - Worker started with workspace `/Users/wolfterminal/.openclaw/workspace/wolf-system` (forbidden for this pack).  
   - Beta factory work in this run uses `cursor-agent -p --workspace /Users/wolfterminal/beta-os`.

5. **Secondary OOB actuator absent by design**  
   - `docs/REMOTE-ACTUATOR-OPTIONS.md`: SSH / Tailscale **not** provisioned.  
   - This run obeyed DO NOT: no SSH, no Tailscale, no new remote actuator installed.

### UNKNOWN (do not invent)

| Question | Status |
| --- | --- |
| Ultimate shared root cause across 23 Sep / 29 Sep / 30 Sep / 2 Oct / 3 Oct | **UNKNOWN** — this audit.jsonl only starts meaningful LOCAL_EXEC_DEAD spam at MAC-APPLY 2026-10-02 16:29; no Sep entries |
| Why INCIDENT-20261003-0712 specifically at ~07:12 (crash vs auth expiry vs cloud controller vs registration) | **UNKNOWN** |
| Agent-worker frames at 07:12 | Worker log shows `Received frame` through 07:12–07:19 — **does not prove** box Shell path was live; also does not prove crash |
| Controller disconnects | Clusters of `controller_disconnected` / Agent Store `deadline_exceeded` appear later (~08:00+) — **not proved** as the 07:12 trigger |
| Whether GUI app is mandatory to spawn vendor local-exec | **UNKNOWN / unproved** — LaunchAgent template still REPLACE_ME; do not pretend launchd label is PASS |
| Whether product renamed `local-exec-daemon` → in-process `exec-daemon` | **Hypothesis only** — probe mismatch is proved; rename-as-root-cause is **UNKNOWN** |

**Phase 1 verdict:** Failure *mechanism* that keeps control recovery blocked is **proved** (absent `local-exec-daemon` process + non-spawning recover + sticky ceiling). Ultimate *why* the control path died at 07:12 / across prior dates: **UNKNOWN**.

---

## Phase 2 — supervise what is proved (design only — Matt approves before activation)

**DO NOT install SSH / Tailscale / new remote actuator in this run.** Secondary path design only:

| Service | Expected | Health check | Restart policy | Ceiling | Deps | Alert | Failure state |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Host | macOS up | uptime / heartbeat age | n/a | n/a | power | HOST OFFLINE only if proved | HOST OFFLINE |
| Prod `:8787` | listen | lsof/curl RO | existing launchd | no thrash | host | WOLF SERVICE DOWN | degrade; do not restart Beta because Prod fails |
| Beta `:8788` | listen | lsof/curl | `net.wolfcommand.serve-beta` KeepAlive | 3 | host | WOLF SERVICE DOWN | isolate from Prod |
| Mac-reach heartbeat | write heartbeat.json ≤30s | file age | LaunchAgent KeepAlive | — | host | STALE | CONTROL DEGRADED |
| Mac-reach supervisor | classify + bounded recover | audit.jsonl | LaunchAgent KeepAlive | 3 then park | heartbeat | CEILING | BLOCKED — continue independent work |
| Vendor exec path | **Unknown binary** until proved | must not be `pgrep local-exec-daemon` alone | **no LaunchAgent until ProgramArguments known** | 3 | Cursor/Grok product | CONTROL DOWN | UNKNOWN spawn |
| Cursor private worker | optional | sock + frames | product-owned | — | GUI? UNKNOWN | — | do not treat as beta-os PASS |
| Cursor Agent CLI (`cursor-agent -p`) | factory apply path | command echo + bf_watch | operator/automation | — | network+auth | CONTROL DEGRADED if fail | continue local |
| cloudflared | tunnel | process | existing | — | network | NETWORK DOWN | external |
| Databases / backup / index / integration workers | existing | existing boards | existing | — | — | — | do not restart healthy deps for one fail |

**Independent watchdog rule:** heartbeat + supervisor already independent of vendor exec (proved labels). They must **not** keep thrashing after ceiling — today they re-audit every 20s while ceiling sticky (noise defect; fix later with Owner approval).

**Secondary path (Owner-approvable — not activated):** Tier 1A SSH Studio←box **or** Tier 1B Tailscale+SSH per `docs/REMOTE-ACTUATOR-OPTIONS.md`. Until then: opportunistic GREEN / CLI path only. No Matt open-app ritual.

---

## Phase 3 pointer

Finance Control Repair continued from last proved checkpoint — see  
`state/reliability/FINANCE-CONTROL-CHECKPOINT-2026-10-03.md`.

Close `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` + receipt photos **preserved**.  
`staff_ready=false` · `eng_proved=false` · CODE COMPLETE / INTEGRATION UNPROVED where external bar unmet.
