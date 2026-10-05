# LaunchAgent Design — Supervised local-exec (Link)

**Role:** Link (Mac Reachability) on Wolf Command  
**Status:** DESIGN DRAFT on box — pipe `connected=false` (machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`). **Not GREEN. Do not invent Studio online.**  
**Authority:** `/workspace/docs/RULE-Wolf-Mac-Exec-Autonomy-No-Matt-Restart-2026-09-23.md`  
**Companion:** `PLAN.md`, `BOOTSTRAP-PARADOX.md`, `ACTUATOR-AUDIT.md`, `AUDIT-GUI-DEPENDENCY.md`  
**Scripts:** `/workspace/mac-reachability/scripts/`  
**Do NOT install LaunchAgents from this draft.** Apply only when pipe greens (see BOOTSTRAP-PARADOX apply checklist).

---

## Goal

Supervised Mac-side local-exec that:

1. **Starts at login** via LaunchAgent(s) (`RunAtLoad`)
2. **Restarts on death** via `KeepAlive` + `launchctl kickstart` (bounded; see PLAN ceiling)
3. **Factory heartbeat MUST NOT require Grok Bot GUI window open**
4. Survives GUI close / half-dead daemon without Matt as restart button

**Invariant (explicit):** **process alive ≠ path proved.** `pgrep` / LaunchAgent “running” alone is never GREEN. VERIFY still requires Shell-class prove + `bf_watch` readable **or** Pulse `:8787` content proves (see `PROVE-MATRIX.md` / `verify.sh`).

---

## Preferred label split

| Label | Program | Role |
|-------|---------|------|
| `com.wolf.mac-reachability.heartbeat` | `scripts/mac-reachability/heartbeat.sh` | Writes `state/mac-reachability/heartbeat.json` every `HEARTBEAT_INTERVAL_SEC` (default 30). **Must run without GUI window.** |
| `com.wolf.mac-reachability.supervisor` | `scripts/mac-reachability/supervisor.sh` | DETECT → CLASSIFY → BOUNDED recover → VERIFY → AUDIT loop. Kickstarts peer labels; drives `recover.sh`. |
| `com.wolf.mac-reachability.local-exec` *(if product allows)* | vendor local-exec-daemon binary / wrapper | Own KeepAlive for daemon restart independent of GUI session. |

Plist TEMPLATEs live under `scripts/`:

- `com.wolf.mac-reachability.heartbeat.plist.TEMPLATE` *(this design pass)*
- `com.wolf.mac-reachability.supervisor.plist.TEMPLATE` *(improved this pass)*
- `com.wolf.mac-reachability.local-exec.plist.TEMPLATE` *(conditional; see uncertainty)*

Target install (Mac, when GREEN):

```
~/Library/LaunchAgents/com.wolf.mac-reachability.heartbeat.plist
~/Library/LaunchAgents/com.wolf.mac-reachability.supervisor.plist
~/Library/LaunchAgents/com.wolf.mac-reachability.local-exec.plist   # only if vendor path known + allowed
```

Logs (StandardOut / StandardError) — under beta-os state, **not** `/tmp`:

```
/Users/wolfterminal/beta-os/state/mac-reachability/logs/heartbeat.stdout.log
/Users/wolfterminal/beta-os/state/mac-reachability/logs/heartbeat.stderr.log
/Users/wolfterminal/beta-os/state/mac-reachability/logs/supervisor.stdout.log
/Users/wolfterminal/beta-os/state/mac-reachability/logs/supervisor.stderr.log
/Users/wolfterminal/beta-os/state/mac-reachability/logs/local-exec.stdout.log   # if used
/Users/wolfterminal/beta-os/state/mac-reachability/logs/local-exec.stderr.log
```

Create `state/mac-reachability/logs/` at first MAC-APPLY.

---

## Keys every plist MUST carry

| Key | Value | Why |
|-----|-------|-----|
| `RunAtLoad` | `true` | Start at login / bootstrap |
| `KeepAlive` | `true` (or dict with `SuccessfulExit=false` if we want exit-0 to stay down — default **true** for heartbeat+supervisor) | Restart on death |
| `ThrottleInterval` | `30` | Bound crash-loop thrash (aligns with recover backoff floor) |
| `StandardOutPath` / `StandardErrorPath` | paths under `…/state/mac-reachability/logs/` | Auditable; survives `/tmp` wipe |
| `WorkingDirectory` | `/Users/wolfterminal/beta-os` | Stable relative scripts |
| `EnvironmentVariables` | `MAC_REACH_ROOT`, `MAC_MACHINE_ID` | Same as scripts |

Install / load (Mac session, once commissioned — **not from box while DOWN**):

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.wolf.mac-reachability.heartbeat.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.wolf.mac-reachability.supervisor.plist
# optional local-exec label if TEMPLATE filled with real ProgramArguments
launchctl kickstart -k gui/$(id -u)/com.wolf.mac-reachability.supervisor
```

Death recovery preferred path inside `recover.sh`: `launchctl kickstart -k gui/$(id -u)/<label>` — **never** “ask Matt to open -a Grok Bot”.

---

## Uncertainty: Grok Bot headless / non-GUI agent API

**Unknown from box (pipe DOWN; no vendor docs installed here):** whether Grok Bot exposes a **headless agent / local-exec owner API** that can be launched without a GUI window (separate from the desktop app process that owns the window).

| What we **can** supervise regardless | What may **still couple to vendor app** |
|--------------------------------------|-----------------------------------------|
| Heartbeat writer LaunchAgent (our bash) | Computers `connected=true` if vendor ties pipe to GUI session lifecycle |
| Supervisor LaunchAgent (our bash + kickstart peers) | Soft reconnect / token refresh that only the GUI app performs |
| Restart of **our** local-exec **wrapper** LaunchAgent (if we own the ProgramArguments binary path) | Restart of vendor `local-exec-daemon` if its only supported spawn is “open Grok Bot.app” |
| Bounded recover / ceiling / audit / LKG | Any Owner CF / credential gate inside vendor stack |

**Design stance until proved on Mac:**

1. Ship heartbeat + supervisor LaunchAgents as **first-class** (no vendor API required).
2. Prefer a **third** label `com.wolf.mac-reachability.local-exec` **only when** we know the real daemon path / `--headless` flag / agent CLI. Until then leave TEMPLATE with `ProgramArguments` as `REPLACE_ME` and treat relaunch as “kickstart whatever label owns the daemon” — if none exists, classify remains recovery-blocked for daemon spawn and do **not** invent GUI Matt ritual as recovery.
3. Heartbeat `grok_bot_running` may stay false while GUI closed; **that alone is not failure** if `path_prove_ok=true` and box ListMachines+Shell prove pass. GUI window ≠ agent path.
4. If vendor proves pipe **requires** GUI session: document as **vendor coupling defect**; escalate as product constraint, **not** as routine Needs Matt open-app. Escalation classes stay: physical power-off, physical auth, Owner CF/creds, catastrophic hardware.

---

## Factory heartbeat without GUI window

Requirements for `com.wolf.mac-reachability.heartbeat`:

- Launched by launchd at login; KeepAlive; **no** dependence on Grok Bot.app frontmost / window open
- Writes `heartbeat.json` with: `ts_wita`, `machineId`, `local_exec_pid`, `grok_bot_running`, `path_prove_ok`, `lkg_pointer`
- `path_prove_ok` from local prove (`bf_watch.py --ping` or equivalent) — **process list alone must not set prove true** (see `heartbeat.sh`)
- Box consumers (Link/Pulse) treat stale heartbeat as `STALE`; still require VERIFY for HEALTHY

If GUI closes and vendor drops pipe: supervisor on Mac can still restart **local** daemons it owns; box remains `connected=false` until vendor path returns — honest BLOCKED/DEGRADED, not fake GREEN.

---

## Mapping to existing scripts

| Script | Owned by label | Notes |
|--------|----------------|-------|
| `heartbeat.sh` | `.heartbeat` | Separate agent — do not rely on supervisor e.g. to spawn it only in-loop |
| `supervisor.sh` | `.supervisor` | Orchestrates classify/recover/verify/audit |
| `classify.sh` / `recover.sh` / `verify.sh` | called by supervisor | recover prefers kickstart; never Matt GUI |

Supervisor comment already says “prefer separate LaunchAgent” for heartbeat — this design makes that binding.

---

## Explicit non-goals (this design)

- Install / `launchctl bootstrap` from box while `connected=false`
- Claim Studio GREEN from process alive or LaunchAgent “loaded”
- Use Matt open-app / Cmd-Q / `pkill` as recovery method
- Invent headless Grok Bot API that we have not proved

---

## Apply gate

See `BOOTSTRAP-PARADOX.md`: one-time commission prove, then auto path only. Until then: templates + docs only.
