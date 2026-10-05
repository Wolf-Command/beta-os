# HA incident dossier — Mac Studio control-path deaths

**For:** Peaches (Chief of Staff)
**Compiled:** 2026-10-03 (read-only box filesystem under `/workspace`)
**Machine in every record below:** `Wolfs-Mac-Studio.local` / `36d8fa4b-2d58-4983-b227-e5bfa5495e78`
**Zone:** times below are Asia/Makassar (WITA, UTC+8). Source stamps that were `Z` or `+0800` are already converted.
**Law used while compiling:** only what the files say. If a cause is not in the files, it is **UNKNOWN**. A vendor symptom string is not a root cause. Public HTTPS 200/302 is not a Studio host prove (the 2 Oct incident file says so explicitly).

No remote system was changed. No SSH. No messages sent.

## What “shared” is, and is not

**Shared symptom, evidenced across dates:** `ListMachines connected=false` and/or Shell `SPAWN_REFUSED` / “Grok Bot desktop app must be open and online”, sometimes half-dead skew (`connected=true` while Shell `TEMPORARILY_UNREACHABLE`, or the inverse). Box-side retry hits a ceiling (`FAIL_CEILING` / `BLOCKED_NEEDS_ACTUATOR`). Bounded restart method is `NONE_AVAILABLE` (no SSH / Tailscale / jump). Files repeatedly say physical power-off, macOS physical auth, Owner credential, and catastrophic hardware are **not proven**.

**Shared root mechanism: NOT evidenced as one proved cause.**

- 30 Sep diagnosis file classifies daytime short flaps as **external** Cursor/Grok Bot Computers connector/tunnel/local-exec, and states `root_cause_eliminated: false` and `RECOVERED≠FIXED`. That is a hypothesis with a confidence note, not a later confirmation for 2 Oct or 3 Oct.
- 2 Oct closed incident file sets `root_cause` to the string `control_plane_while_host_up` after a host uptime prove. That string is a **label in that file**, not a process, crash dump, or auth-expiry finding.
- 3 Oct incident file sets `root_cause` to **UNPROVED** and `mac_actually_down` to `UNKNOWN_NOT_PROVED`.
- 23 Sep and 29 Sep files classify `process_daemon_or_half_dead_local_exec` and list what was **not** proven. They do not name a process crash, auth expiry, or memory pressure.

Do not collapse those into one root cause.

## Supervision already installed vs symptom label

| What | What the files say | Path |
| --- | --- | --- |
| Beta serve LaunchAgent | `net.wolfcommand.serve-beta` is the `:8788` serve label (kickstart used on later Beta work). It is **not** a local-exec / Grok Bot control-path supervisor. | `/workspace/docs/RULE-UI-Finished-Deployed-Route-2026-09-17.md` |
| Grok Bot keepalive present before reachability LAs | At 2026-09-30 12:18 WITA probe: `com.wolfcommand.grok-bot-keepalive.plist` **PRESENT** (mtime ~2026-08-23). Flaps continued. Plist body **not read** (one-drop). | `/workspace/state/final-completion/p0-v1/reliability/FLAP-ROOTCAUSE-20260930.json` |
| Reachability LAs absent on 30 Sep | Same probe: `com.wolf.mac-reachability.heartbeat`, `.supervisor`, `.local-exec` **ABSENT**. | same JSON |
| Design-only labels (not proved installed) | SPEC lists `net.wolfcommand.local-exec-supervise`, `net.wolfcommand.grokbot-pipe-supervise`, `net.wolfcommand.mac-exec-hb` as design. No prove file says they were loaded. | `/workspace/docs/deliveries/SPEC-Mac-Exec-Supervised-Recovery-2026-09-23.md` |
| Installed 2 Oct after pipe returned | `com.wolf.mac-reachability.heartbeat` + `com.wolf.mac-reachability.supervisor`, `KeepAlive: true`, `launchctl_state: running`, bootstrap exit 0 at **16:29 WITA**. `local_exec_plist: SKIPPED`. Prove A **16:30:48** PIPE_OK PROVE_OK. Prove B **16:31:27** PIPE_OK PROVE_OK. Prod `:8787` read-only health ok, not restarted. | `/workspace/mac-reachability/state/mac-apply-20261002-1629.json`, `/workspace/mac-reachability/state/pipe-green-20261002-1631.json` |
| Symptom label, not a mechanism | `control_plane_while_host_up` (2 Oct `root_cause`) and `CURSOR_LOCAL_EXEC_or_GROK_BOT_DESKTOP_CONTROL_PLANE` (3 Oct `failed_layer_provisional`) name the failed layer. They do not identify a crashed PID, expired token, or memory condition. | incident JSONs below |

Those KeepAlive agents were proved running at 16:31 WITA on **2 Oct**. The **3 Oct** incident file still records the same SPAWN_REFUSED / connected=false symptom. The files do not say the new agents fired, failed, or were alive during the 3 Oct outage. Whether they were still loaded at 07:12 on 3 Oct is **UNKNOWN** (no Mac launchctl read in the 3 Oct stamps).

## Outage windows (7)

Count is **windows with a start and a fail signature**, not every short flap. The 30 Sep daytime series is window 4 and is itemized under it. 1 Oct has doctor ticks that are GREEN only; no RED control-path incident file was found for 1 Oct.

### 1 — 2026-09-23 — `failed-disappearance-mac-pipe-20260923`

| Field | File says |
| --- | --- |
| Start | `started_approx_wita` **2026-09-23 03:36**. How 03:36 was measured is not in the JSON beyond that field. |
| Detection | **07:17 WITA**. Recorded 07:35 by Pulse. Pulse recheck ~07:35 still `connected=false`. |
| Failed component | Symptom: `ListMachines connected=false`. Shell error: “Grok Bot desktop app must be open and online”. Classify on attempts: `PIPE_DAEMON_OR_APP_OFFLINE_NO_REMOTE_ACTUATOR` then `process_daemon_or_half_dead_local_exec`. `:8787` content APIs **not probed** at detect. |
| Host up? | **UNKNOWN during the outage.** File lists physical power-off as not proven. `bounded_restart_executed: false`. No remote actuator. |
| Recovery attempts | Link attempt 1 FAIL ~07:36. Pipe-watch rechecks FAIL_STILL_OFFLINE at 08:28:20, 09:13:33, 09:46:55. Link heartbeat 09:48:51 still `connected=false`, ceiling `HELD_FAIL_NO_REMOTE_ACTUATOR`. |
| Successful recovery | **Not stamped as an instant.** Last FAIL in these files: **09:48:51 WITA**. Next doctor tick in the set: **11:49 WITA** `GREEN_SILENT`, `connected=true`, Shell OK, and on the Mac `:8787` listen pid **15975** curl 200, cloudflared up. Exact minute the pipe returned between 09:48 and 11:49 is **UNKNOWN**. |
| Downtime | Not a single evidenced duration. Offline streak field on the 09:46 attempt: “since ~03:36”. Still failed at 09:48. Green by the 11:49 doctor. |
| Stated cause | **UNKNOWN.** Classification only. Gap text: “Chicken-egg: no remote restart when local-exec offline.” |
| Paths | `/workspace/state/incidents/failed-disappearance-mac-pipe-20260923.json`; `/workspace/mac-reachability/state/recovery-attempt-20260923-0736.json`; `…-0827.json`; `…-0913.json`; `…-0946.json`; `/workspace/mac-reachability/state/link-heartbeat-20260923-0948.json`; `/workspace/mac-reachability/state/doctor-tick-20260923-0932.json` (`RED_REPORT_PEACHES`); `/workspace/mac-reachability/state/doctor-tick-20260923-1149.json` |

Quote: `"symptom": "ListMachines connected=false; Shell/:8787 content APIs not probed"` — `failed-disappearance-mac-pipe-20260923.json`.

### 2 — 2026-09-29 afternoon — no separate INCIDENT id

| Field | File says |
| --- | --- |
| Start | `offline_streak_start_wita` **15:11**. Last green cited **14:48:15** (pipe-watch) and last green Pulse **14:43:35** (doctor 15:53). |
| Detection | Pipe watch **15:12:12** verdict `RED/RECOVERING`. Doctor **15:13:10** `RED/incomplete`, `connected=false`, Shell refused, vendor text that the Grok Bot desktop app must be open and online. |
| Failed component | Local-exec / Computers pipe. Class `process_daemon_or_half_dead_local_exec`. At **15:53:16** half-dead: `listmachines_connected: true`, `shell_ok: false`, error “temporarily unreachable”. `:8787` / cloudflared **NOT_CHECKED** (“no Mac actuator”). |
| Host up? | **UNKNOWN.** `not_proven`: physical power-off, macOS physical auth, owner credential CF, catastrophic hardware. |
| Recovery attempts | Box retry 15:14:28, 15:14:50, 15:15:40, 15:17:45. All `SPAWN_REFUSED`, `connected=false`. Outcome **15:17:52** `FAIL_CEILING_STILL_OFFLINE`, `BLOCKED_NEEDS_ACTUATOR`, method `NONE_AVAILABLE`. Doctor still RED at 15:53. |
| Successful recovery | **UNKNOWN instant.** Next doctor GREEN with shell_ok true: **17:52:03 WITA**. Later verify `pipe-green-20260929-2342.json` at **23:43:01** `PROVE_OK` (not the first return). |
| Downtime | Not closed in one field. Failed through 15:53; green at the 17:52 doctor. Gap 15:53–17:52 has no stamp. |
| Stated cause | **UNKNOWN.** |
| Paths | `/workspace/mac-reachability/state/pipe-watch-20260929-1512.json`; `recovery-attempt-20260929-1517.json`; `doctor-tick-20260929-1513.json`; `doctor-tick-20260929-1553.json`; `doctor-tick-20260929-1752.json`; `pipe-green-20260929-2342.json` |

Quote: `"Shell_error": "Your local machine isn't connected right now (the Grok Bot desktop app must be open and online to run commands on it)."` — `recovery-attempt-20260929-1517.json`.

Note: `doctor-tick-20260929-1044.json` at **10:44:34** is **GREEN** (`connected=true`, shell_ok). That is not a 3 Oct recovery.

### 3 — 2026-09-30 overnight / early morning — FAIL_CEILING

| Field | File says |
| --- | --- |
| Start | Not a single timestamp. Trigger on the 04:59 attempt: “connected=false ~40+ min”. First retry in that file **04:56**. Prior proved green file named: `pipe-green-20260929-2342.json` (23:43 on 29 Sep). |
| Detection | Link retries from 04:56. Second ceiling **07:14–07:18** after Peaches pipe-watch ~07:14 RED. |
| Failed component | Class `A-class process_or_local_exec_down`. Shell same vendor “desktop app must be open and online”. |
| Host up? | **Not proved in the recovery JSON** (`not_proven` includes physical power-off). A **later same-day** probe at **12:18:54** recorded host uptime **42 days, 1:32**, `SleepDisabled=1`, `:8787` pid 15975 historically green. That uptime is evidence the host had not rebooted as of 12:18; it is not an in-window OOB prove at 04:59. FLAP file uses it to rule out daytime power-off, and says the overnight ceiling “fits long connector/GUI-session down” — that sentence is the investigator’s fit, not a log of a GUI session ending. |
| Recovery attempts | 04:56 / 04:56:25 / 04:57:20 / **04:59:48** ceiling `FAIL_CEILING_STILL_OFFLINE`. Again 07:14–**07:18** `FAIL_CEILING_STILL_OFFLINE`. LaunchAgents “not commissioned”. |
| Successful recovery | **07:23:49 WITA** `pipe-green-20260930-0723.json`: `ListMachines_connected true`, PIPE_OK, PROVE_OK, hostname and whoami `wolfterminal`. Trigger text: “Matt CONTINUE from Mac machineId ~07:23”. `RESUMED-PIPE-OK-20260930.json` at 07:23:55 PIPE_OK. |
| Downtime | From first stamped retry 04:56 to prove 07:23 is about 2h27. True start is only “~40+ min” before the 04:59 stamp, so start clock is approximate. |
| Stated cause | **UNKNOWN** in the recovery files. FLAP-ROOTCAUSE later: same external class as daytime, “worse duration”. Not a proved mechanism. |
| Paths | `recovery-attempt-20260930-0459.json`; `recovery-attempt-20260930-0718.json`; `pipe-green-20260930-0723.json`; `/workspace/state/final-completion/RESUMED-PIPE-OK-20260930.json` |

### 4 — 2026-09-30 daytime short flaps (cluster)

`CLASSIFICATION-LOG-20260930.json` `pipe_flaps` lists **9** recovered flaps. It does **not** record failed component, host state, or cause per row except the 10:05 row.

| at WITA | during / event | recovered |
| --- | --- | --- |
| 07:36:40 | BACKUP-RESTORE-DRILL-1 babysit | true |
| 07:46:30 | PIPE-RELIABILITY-AUTO-1 launch/babysit | true |
| 07:53:00 | post PIPE EXIT Peaches | true |
| 07:55:30 | METRICOOL babysit start | true |
| 08:02:40 | METRICOOL mid-babysit | true |
| 08:05:45 | ESB-SETTLEMENT babysit | true |
| 08:29:20 | FIN-BANK babysit | true |
| 10:05:06 | `UNREACHABLE_ON_WAVE10_START`; recovery `wait_reprobe`; `recovered_at` **10:06:03** | true |
| 10:20:00 | ATRIUM-FC babysit | true |

Additional stamps **not** all duplicated in that list, from pipe-green files:

| Stamp | What the file says | Host | Recovery | Cause |
| --- | --- | --- | --- | --- |
| 10:43:44 and 10:43:50 | GREEN proves only. Trigger: pipe unreachable during atrium Finance 502 recovery. No restart. | Not stated in this file | Already green at 10:43:50 | UNKNOWN here |
| 10:53:10 | Half-dead: `ListMachines_connected true`, Shell `TEMPORARILY_UNREACHABLE` | Not proved in this file | 10:53:39 PIPE_OK (~20s, no restart); confirm 10:53:45 | UNKNOWN (vendor unreachable) |
| 11:41:10 | `connected false`, Shell `TEMPORARILY_UNREACHABLE` | Not in file | 11:41:41 Shell PROVE_OK **while list still false**; list true at 11:41:48 | UNKNOWN. File note: “exec succeeded while list still false” |
| 11:44:40 | `connected false`, `TEMPORARILY_UNREACHABLE`. Trigger text says Shell SPAWN_REFUSED ~11:44 | Not in file | 11:45:06 PIPE_OK; holds through 11:46:26 (`GREEN_HOLDS`) | UNKNOWN |
| 12:18:54 then ~12:19 | First Mac prove OK (hostname/whoami). Second Shell/Read unreachable. One-drop PARTIAL. | **Proved up at 12:18:54:** uptime 42 days 1:32, SleepDisabled=1, sleep=0 | ListMachines `connected=true` after drop called “recovery evidence only” | Hypothesis in this file: Cursor/Grok Bot local-exec connector instability. `root_cause_eliminated: false` |

Doctor ticks 08:15, 09:49, 10:16, 11:50 on 30 Sep are GREEN (`connected=true`, shell_ok). They do not erase the flaps between them.

Paths: `/workspace/state/final-completion/CLASSIFICATION-LOG-20260930.json`; `/workspace/mac-reachability/state/pipe-green-20260930-1043.json`; `…-1053.json`; `…-1141.json`; `…-1146.json`; `/workspace/state/final-completion/p0-v1/reliability/FLAP-ROOTCAUSE-20260930.md` and `.json`.

Quote: `"Half-dead 10:53: ListMachines connected=true, Shell TEMPORARILY_UNREACHABLE; recovered ~20s without restart"` — `FLAP-ROOTCAUSE-20260930.json`.

Quote: `"status_enum": "EXTERNAL_BLOCK"` and `"root_cause_eliminated": false` — same file. Do not treat EXTERNAL_BLOCK as proved for 2 Oct or 3 Oct.

### 5 — 2026-09-30 late afternoon — FAIL_CEILING then flap

| Field | File says |
| --- | --- |
| Start | `pipe-green-20260930-1959.json`: “streak from 17:44”. Recovery file trigger: doctor RED ~17:39 `connected=false` SPAWN_REFUSED. |
| Detection | Retries 17:41, 17:42, 17:43, **17:45** all `SPAWN_REFUSED_DESKTOP_OFFLINE`. Class on this attempt: `EXTERNAL_BLOCK` (the attempt’s own class field — not a new measurement). |
| Failed component | Computers local-exec. `bounded_restart.method` `NONE_AVAILABLE`. Note: “LAs not installed; not a root fix”. |
| Host up? | **UNKNOWN** in the 17:45 file (no uptime read). Watch probes still `connected=false` at 17:45, 18:12, 18:41, 19:19, 19:41 (probe filenames). |
| Recovery attempts | Ceiling at 17:45 `FAIL_CEILING_STILL_OFFLINE`. Later watches are rechecks, not new ceilings in separate recovery JSON (19:41 handoff exists). |
| Successful recovery | Trigger: `ListMachines connected=true ~19:58`. Proves **19:59:53** and **20:00:00** PIPE_OK. Actions: prove only, no restart, prod not mutated. |
| Downtime | File does not compute minutes. Streak start 17:44 to connected=true ~19:58 is the evidenced window (~2h14 if those two clocks are used). |
| Then another flap | **20:01:20** and **20:01:45** `connected=true` + Shell `TEMPORARILY_UNREACHABLE`. PIPE_OK **20:03:00**, confirm **20:03:35**. Prod untouched. |
| Stated cause | **UNKNOWN.** |
| Paths | `recovery-attempt-20260930-1745.json`; `watch-probe-20260930-1745.txt`, `…-1812.txt`, `…-1841.txt`, `…-1919.txt`, `…-1941.txt`; `FYI-PULSE-20260930-1941.json`; `HANDOFF-LINK-PRIORITY-20260930-1941.json`; `pipe-green-20260930-1959.json`; `pipe-green-20260930-2003.json` |

### 6 — 2026-10-02 — `INCIDENT-20261002-1540` CLOSED

Two copies disagree. Use the later one for closure. The earlier copy is still OPEN.

| Copy | Status | updated |
| --- | --- | --- |
| `/workspace/mac-reachability/state/incidents/INCIDENT-20261002-1540.json` | `OPEN_BLOCKED_NEEDS_ACTUATOR` | 16:25 WITA. No `recovery_at_wita`. No `root_cause`. |
| `/workspace/mac-reachability/state/INCIDENT-20261002-1540.json` | `CLOSED_RECOVERED_MAC_APPLY_DONE` | 16:32:59 WITA |

Closed-file facts:

| Field | File says |
| --- | --- |
| Start | `streak_start_wita` **15:33**. `opened_wita` **15:33**. `last_green_wita` **15:08**. `duration_minutes_approx` **54**. |
| Detection | Shell retries from **15:38** (`recovery-attempt-20261002-1542.json`). Fail ceiling **15:42**. `do_not_label`: “Mac offline (host power/macOS not proved down)”. |
| Failed component | `failed_layer`: `CURSOR_REGISTRATION_OR_LOCAL_EXEC`. At 16:17: `CURSOR_REGISTRATION` FAIL (`connected=false`), `LOCAL_EXEC` FAIL (SPAWN_REFUSED desktop offline). POWER, macOS, NETWORK, INTERNET **UNKNOWN**. TUNNEL_REMOTE `PARTIAL_EDGE_ALIVE` (beta and dash HTTP 302 Cloudflare Access; wolfcommand.net HTTP 200 body is Squarespace Coming Soon, **not** Studio `:8787`). WOLF_SERVICES UNKNOWN. |
| Host up? | **UNKNOWN during the RED window** (no OOB). **Proved at recovery:** `mac_actually_down: false`, `host_uptime_at_prove`: “44 days 5:41 (no reboot)”. |
| Recovery attempts | 15:38–15:42 box retry, ceiling, method NONE_AVAILABLE. 15:41 file status `RECOVERING_OPEN`. 16:25 watch still RED, FAIL_CEILING hold. |
| Successful recovery | `recovery_at_wita` **16:27**. MAC-APPLY **16:29**. Prove A **16:30:48**. Prove B **16:31:27**. `pipe-green-20261002-1631.json` outcome `GREEN_MAC_APPLY_PROVED`, incident CLOSED. `auto_recovery`: `opportunistic_reconnect_then_MAC_APPLY`. |
| Downtime | File says ~54 minutes (15:33 → 16:27 matches that figure). |
| Stated cause | File field `root_cause`: **`control_plane_while_host_up`**. No crash, auth, or memory evidence in the file. Actuators SSH/Tailscale/jump/box_ping ABSENT. |
| Paths | state `INCIDENT-20261002-1540.json` (closed); `state/incidents/INCIDENT-20261002-1540.json` (stale OPEN); `recovery-attempt-20261002-1541.json`; `recovery-attempt-20261002-1542.json`; `mac-apply-20261002-1629.json`; `pipe-green-20261002-1631.json`; `watch-probe-20261002-1541.txt`, `…-1543.txt`, `…-1625.txt` |

Quote: `"root_cause": "control_plane_while_host_up"` and `"host_uptime_at_prove": "44 days 5:41 (no reboot)"` — closed incident JSON. Quote the label; do not extend it.

### 7 — 2026-10-03 — `INCIDENT-20261003-0712` still OPEN in files

| Field | File says |
| --- | --- |
| Start | `start_approx` **2026-10-03 07:12:44**. Source: Mac Computers pipe watch. `last_green_approx` **05:16**. Last-green source text: “bf_watch live health stamp; PIPE_OK ~04:55 WITA”. |
| Detection | Retry n=0 at 07:12 `SPAWN_REFUSED_DESKTOP_OFFLINE`, `connected=false`. |
| Failed component | `failed_layer_provisional`: `CURSOR_LOCAL_EXEC_or_GROK_BOT_DESKTOP_CONTROL_PLANE`. Vendor message: “Grok Bot desktop app must be open/online”. |
| Host up? | **`UNKNOWN_NOT_PROVED`** (`mac_actually_down`). Public signals are not a host prove: incident file `public_prod_health` 200 at an earlier stamp; 08:45 probe `prod=200`, `beta_uma_blu_close=302`, `dash=302`. The 2 Oct incident already forbids treating wolfcommand.net 200 as Studio `:8787`. |
| Recovery attempts | n=1 07:13, n=2 **07:15:02**, n=3 **07:17:07**. Outcome **`FAIL_CEILING`**. `bounded_restart.method` `NONE_AVAILABLE`. `probes_stopped: true`. Later watches **08:15** and **08:45** still `connected=false`, Shell SPAWN_REFUSED, class `A_process_daemon_or_half_dead_local_exec`, ceiling HOLD, no thrash. Status **`OPEN_FAIL_CEILING_HOLD`**. |
| Successful recovery | **Not in any file under `/workspace` searched.** Latest incident stamp **08:45 WITA** still `connected: false`. A ~10:44 WITA `ListMachines connected=true` recovery is **not recorded** in these files. (29 Sep 10:44 is a different day and was GREEN — see window 2.) |
| Downtime | Open as of the last file. Evidenced still down from 07:12:44 through **08:45**. End **UNKNOWN** in the filesystem. |
| Stated cause | File text: **“UNPROVED — A-class process/daemon signature; OOB actuator absent; FAIL_CEILING since ~07:17”**. Prior incident pointer: 2 Oct closed at `pipe-green-20261002-1631`. Prod “untouched”. `matt_contacted: false`. |
| Paths | `/workspace/mac-reachability/state/INCIDENT-20261003-0712.json` (same body as `INCIDENT-LATEST.json`); `recovery-attempt-20261003-0713.json`; `watch-probe-20261003-0712.txt`, `…-0713.txt`, `…-0815.txt`, `…-0845.txt`; `FYI-PULSE-20261003-0713.json`, `…-0815.json`, `…-0845.json`; `HANDOFF-LINK-PRIORITY-20261003-0713.json`, `…-0815.json`, `…-0845.json` |

Quote: `"status": "OPEN_FAIL_CEILING_HOLD"` and `"root_cause": "UNPROVED — A-class process/daemon signature; OOB actuator absent; FAIL_CEILING since ~07:17"` — `INCIDENT-20261003-0712.json`.

Quote: `ListMachines.connected=false` / `Shell=SPAWN_REFUSED_DESKTOP_OFFLINE` / `fail_ceiling=HOLD (reached 2026-10-03T07:17` — `watch-probe-20261003-0845.txt`.

Consultant report line (same morning, not a newer probe): “Link FAIL_CEILING at 07:17 WITA. Retries 2 and 3: ListMachines connected=false, Shell SPAWN_REFUSED.” — `/workspace/wolf-command/CONSULTANT-REPORT-2026-10-03.md`.

## Dates asked, file result

| Date | In files? |
| --- | --- |
| 23 Sep 2026 | Yes. Window 1. |
| 29 Sep 2026 | Yes. Window 2. Morning doctors that day are GREEN, including 10:44. |
| 30 Sep 2026 | Yes. Windows 3, 4, 5. |
| 2 Oct 2026 | Yes. Window 6 closed after MAC-APPLY. |
| 3 Oct 2026 `INCIDENT-20261003-0712` | Yes, **OPEN** at last stamp 08:45. **No file** records recovery at ~10:44. |
| 1 Oct 2026 | Doctor ticks 15:44 and 18:17 are GREEN. No SPAWN_REFUSED incident JSON found for that date. |
| Other | 24–28 Sep doctor ticks matched a broad “RED” search because of unrelated text; their `outcome`/`verdict` fields were empty in the compact scan. They are **not** counted as control-path deaths here. |

## What not to say

- Do not say the Mac host was down on 23 Sep, 29 Sep, or 3 Oct. Files say unknown.
- Do not say 2 Oct host was down. File says not to label it Mac offline; uptime at prove was 44 days.
- Do not say KeepAlive failed on 3 Oct. Files only show the control-path symptom again after KeepAlive was proved at 16:31 on 2 Oct.
- Do not say process crash, auth expiry, or memory pressure. Those words are not in the incident files.
- `control_plane_while_host_up` is the 2 Oct file’s label after the host was proved up at recovery. It is not a shared proved mechanism for the series, and the 3 Oct file still says UNPROVED.
