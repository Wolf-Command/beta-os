# MAC-APPLY — LaunchAgent commission (Link)

**Status:** READY ON BOX — do **not** run while pipe RED.  
**Owner:** Link (Mac Reachability)  
**Gate:** ListMachines `connected=true` for `36d8fa4b-2d58-4983-b227-e5bfa5495e78` **AND** Shell prove OK. Process-alive alone = no.  
**Ceiling:** ATTEMPT#3 FAIL_CEILING ~08:32 WITA. No box thrash. This doc is the **when-GREEN** path only.  
**Never:** Matt open-app / Cmd-Q / pkill / reconnect as apply or recover.

Canon Mac roots:

| What | Path |
|------|------|
| Root | `/Users/wolfterminal/beta-os` |
| Scripts | `/Users/wolfterminal/beta-os/scripts/mac-reachability/` |
| State | `/Users/wolfterminal/beta-os/state/mac-reachability/` |
| Logs | `/Users/wolfterminal/beta-os/state/mac-reachability/logs/` |
| Doc | `/Users/wolfterminal/beta-os/docs/MAC-REACHABILITY-RECOVERY.md` |

Box draft source: `/workspace/mac-reachability/`

---

## Preflight (box, once GREEN)

1. `ListMachines` → `Wolfs-Mac-Studio.local` / `36d8fa4b…` `connected=true`
2. Shell: `echo PROVE_OK; hostname; date; whoami` → must print `PROVE_OK`
3. Optional: `test -d /Users/wolfterminal/beta-os && echo ROOT_OK`
4. If any fail → **STOP**. Do not invent GREEN. Do not ask Matt.

---

## Steps (Mac via Shell after GREEN)

1. **Mkdir**
   ```bash
   mkdir -p /Users/wolfterminal/beta-os/scripts/mac-reachability \
            /Users/wolfterminal/beta-os/state/mac-reachability/logs \
            /Users/wolfterminal/beta-os/docs
   ```
2. **Copy** from box draft (via CopyFromBox / Shell write) into Mac paths:
   - `scripts/*.sh` → Mac scripts dir (chmod +x)
   - plist TEMPLATEs → strip `.TEMPLATE`, fill paths if needed → `~/Library/LaunchAgents/com.wolf.mac-reachability.{heartbeat,supervisor}.plist`
   - `local-exec` plist **only** if `ProgramArguments` real (else skip)
   - docs: PLAN / LAUNCHAGENT-DESIGN / PROVE-MATRIX / this MAC-APPLY → docs tree
3. **Bootstrap** (gui domain):
   ```bash
   UID_N=$(id -u)
   launchctl bootstrap "gui/${UID_N}" ~/Library/LaunchAgents/com.wolf.mac-reachability.heartbeat.plist
   launchctl bootstrap "gui/${UID_N}" ~/Library/LaunchAgents/com.wolf.mac-reachability.supervisor.plist
   launchctl kickstart -k "gui/${UID_N}/com.wolf.mac-reachability.heartbeat"
   launchctl kickstart -k "gui/${UID_N}/com.wolf.mac-reachability.supervisor"
   ```
4. **VERIFY** (not process list):
   - Shell prove again
   - `test -f …/state/mac-reachability/heartbeat.json` fresh
   - `bf_watch` readable **or** leave Pulse `:8787` prove to Pulse after Link Shell OK
5. **PROVE-MATRIX ×2** (`PROVE-MATRIX.md` Run A + Run B); `matt_contacted=false`
6. **Rewrite** `mac-computers-pipe-watch` — strip Matt fix-card; RED → Link/Peaches only
7. **Ping** Peaches + Pulse (+ Vesper if waiting) — verified Shell PROVE_OK only

---

## Abort / park

| Condition | Action |
|-----------|--------|
| Pipe drops mid-apply | Stop bootstrap; file attempt JSON; no Matt card |
| local-exec plist path unknown | Skip third label; heartbeat+supervisor still ship |
| Ceiling on Mac-side recover | `BLOCKED`; park pipe-dependent; continue independent |

---

## Script

Gated helper: `scripts/mac-apply.sh` — refuses unless `MAC_APPLY_CONFIRM=GREEN` **and** local prove env set. Box must not run it against Studio while `connected=false`.
