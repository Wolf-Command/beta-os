# WOLF CONNECTION COMMISSIONING REGISTER — 2026-09-22

**Draft for Owner YES/NO.** Not commissioned.  
**Compiled:** 2026-09-22 20:31 WITA  
**Executor:** Peaches executor (box `grok-bot-vm-405718730`) — **Mac local-exec NOT attached** (machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78` ignored by this Shell schema; same class as overnight-audit 2026-09-18).  
**Beta root (target):** `/Users/wolfterminal/beta-os` — **NOT opened live this pass**.  
**Evidence bases:** ACCESS-MAP 7 Sep; B2-R2-MAP; WEEK2-NAS-COUNT 17 Aug; CONSULTANT-REPORT 22 Sep; WOLF-COMMAND-CURSOR-BRIEF 21 Aug; Money-Apps-MAP 17 Aug; beta-os-work `serve_beta.py` mirror; live SuperGrok MCP probes 2026-09-22 20:31 WITA; public CF Access challenge on beta/dash; NAS mounts as provided by Owner brief + Atlas 22 Sep.

**Legend — CURRENT COMMISSIONING STATE:** DISCOVERED | CONFIGURED | CONNECTED (evidence) | PARTIAL | RETIRED | UNKNOWN | AWAITING_OWNER

---

## Rollup (this draft)

| Bucket | Count |
|---|---:|
| Systems inventoried (rows below) | 28 |
| RETIRED / HISTORICAL (do not commission) | 2 (ClickUp, Telegram) + R2-write lane parked |
| SuperGrok MCP CONNECTED (live probe 2026-09-22 20:31 WITA) | Metricool, Google Drive, Gmail, Google Calendar, Notion, Cloudflare-docs, Jotform |
| Mac-side operational (dated evidence, not re-probed live) | NAS SMB, B2, CF Tunnel/Access hostnames, Prod :8787, Beta :8788 (public CF gate), Alchemist tile, Metricool Atlas freshness |
| UNKNOWN live health (need Mac prove) | Yanolja API, Klaviyo keys, ESB live API, Xero live API, Mews, OpenClaw bots, Integration Health UI, GATES.json presence, file counts on NAS roots |
| READY FOR STAFF TOMORROW (NAS) | **NO** |
| HAIKAL HUMAN TEST | **not started** |

---

## NAS roots (inventory-first)

| Volume | Role | Entries (last evidence) | File count | Notes |
|---|---|---|---|---|
| `00-Editing-Workspace` (+ aliases) | Edit scratch | `-3` entries=9 (22 Sep Atlas); bare/`-1`/`-2` stubs/ghosts | UNKNOWN this pass | Do not unmount `-3` |
| `01-Media-Library` | **Canonical media candidate** | Brands/clients listed ACCESS-MAP / WEEK2-NAS | Historical video counts (17 Aug) only; **live wc UNKNOWN** | P0 inventory |
| `02-Stock-Assets` (+ `-1`) | Stock | stub + `-1` entries=8 (22 Sep) | UNKNOWN | Ghost hygiene Owner-gated |
| `03-Templates` | Templates | Observed mounted (Owner brief) | UNKNOWN | |
| `04-Time-Machine` | TM dest share | Observed mounted (Owner brief) | UNKNOWN | Separate from TM dest name in Access-Map |
| `05-Wolf-Vault-Mirror` | Vault off-box mirror | wolf-command pack 31 Aug 07:41 | UNKNOWN full tree | md/maps only in pack notes |

**SMB source:** `192.168.77.130` (Mr Wolf / Synology). Auth: SMB (credentials not opened).

---

## Connection rows

### 1. Synology NAS / SMB mounts
- **SYSTEM:** Synology NAS (Mr Wolf) via SMB  
- **BUSINESS/DOMAIN:** Media · Vault · TM · Edit  
- **PURPOSE:** Local high-capacity store for footage, templates, vault mirror  
- **SOURCE OF TRUTH FOR:** Operational media files (candidate: `01-Media-Library`)  
- **DATA RECEIVED:** Files from cameras/editors/sync jobs  
- **DATA SENT:** Footage→B2 sync; vault→B2 archive; Time Machine  
- **READ CAPABILITY:** Yes (when mounted)  
- **WRITE CAPABILITY:** Yes (dangerous — inventory-only until commissioned)  
- **CURRENT ACCESS:** Mounts observed (Owner brief + Atlas 22 Sep). This executor **cannot** `ls /Volumes` (box-bound).  
- **CURRENT HEALTH:** PARTIAL — ghosts noted; real shares present. Overall Atlas health red 22 Sep (ghost NAS expected).  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 Atlas / Owner brief  
- **FRESHNESS:** Same-day mount evidence; file counts stale/UNKNOWN  
- **AUTH METHOD:** SMB to `192.168.77.130` (secret not opened)  
- **PERMISSION SCOPE:** Mac Studio user `wolfterminal` mounts  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (media ops)  
- **RISK:** HIGH if bulk mutate; MEDIUM if inventory-only  
- **CURRENT COMMISSIONING STATE:** DISCOVERED / PARTIAL — AWAITING_OWNER  
- **REQUIRED TEST:** Root `ls` each volume; timed `find | wc` on `01-Media-Library` top-level only; Haikal human browse test  
- **FAILURE BEHAVIOUR:** Leave mounts; mark UNKNOWN; no rmdir of non-empty  
- **ROLLBACK:** N/A inventory; remount via NAS keepalive if drop

### 2. Backblaze B2
- **SYSTEM:** Backblaze B2 (`b2:`, `wolfb2:`, `wolfb2crypt:`, `b2nas:`)  
- **BUSINESS/DOMAIN:** DR / cold archive / footage  
- **PURPOSE:** Only off-site that gets updates (ACCESS-MAP)  
- **SOURCE OF TRUTH FOR:** Cold archive + encrypted footage archive (not live edit)  
- **DATA RECEIVED:** Daily tarballs, vault-mirror sync, footage sync  
- **DATA SENT:** Restore drills (read)  
- **READ CAPABILITY:** rclone list/copy (proved restore 29 Aug)  
- **WRITE CAPABILITY:** Daily backup + archive jobs (historically ON)  
- **CURRENT ACCESS:** CONFIGURED on Mac (rclone remotes named). Cap 5282.37GB / 42.3% ok (Consultant 22 Sep).  
- **CURRENT HEALTH:** Updates ON per Access-Map/B2 maps; 22 Sep B2 ok tile. Live rclone this pass: **UNKNOWN** (no Mac).  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 consultant B2 size; restore proof 2026-08-29  
- **FRESHNESS:** Size same-day; restore proof ~24d old  
- **AUTH METHOD:** rclone remote credentials (files not opened)  
- **PERMISSION SCOPE:** Mac backup jobs / Phoenix weekday check  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** HIGH (data loss if delete); MEDIUM for read-list  
- **CURRENT COMMISSIONING STATE:** CONNECTED (dated) — AWAITING_OWNER for Beta commissioning  
- **REQUIRED TEST:** `rclone lsd b2:wolf-cold-archive` + list latest daily object; no deletes  
- **FAILURE BEHAVIOUR:** Alert; do not invent size; leave R2 alone  
- **ROLLBACK:** Stop launchd backup plists only with Owner YES

### 3. Cloudflare R2
- **SYSTEM:** Cloudflare R2 (`r2:`, `r2archive:`)  
- **BUSINESS/DOMAIN:** Legacy media seed  
- **PURPOSE:** Old seed; cost-parked  
- **SOURCE OF TRUTH FOR:** None (superseded by B2)  
- **DATA RECEIVED/SENT:** Writes OFF since 18 Aug 2026  
- **READ/WRITE:** Read possible; Write OFF  
- **CURRENT ACCESS:** Remotes named; plists `*.disabled-r2-cost-20260818`  
- **CURRENT HEALTH:** Quiet / writes OFF (7 Sep still unloaded)  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-07 Access-Map  
- **FRESHNESS:** Stale for writes (intentional)  
- **AUTH METHOD:** rclone `r2:` (not opened)  
- **PERMISSION SCOPE:** Disabled jobs  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TRANSITIONAL → keep objects; do not seed; do not delete (R2-clean clock)  
- **RISK:** Cost if re-enabled  
- **CURRENT COMMISSIONING STATE:** CONFIGURED · WRITE RETIRED/PARKED  
- **REQUIRED TEST:** Confirm launchctl has no r2 jobs  
- **FAILURE BEHAVIOUR:** Leave disabled  
- **ROLLBACK:** Keep disabled

### 4. Google Drive (SuperGrok MCP + Mac clutter)
- **SYSTEM:** Google Drive  
- **BUSINESS/DOMAIN:** Docs / finance sheets / Obsidian-adjacent clutter  
- **PURPOSE:** Working files; **not** clean Obsidian mirror  
- **SOURCE OF TRUTH FOR:** Specific sheets (e.g. Alchemist Control) — not vault canon  
- **DATA RECEIVED:** Uploads / sheet edits  
- **DATA SENT:** Agent reads via MCP  
- **READ CAPABILITY:** YES — MCP `list_recent_files` succeeded 2026-09-22 20:31 WITA (e.g. BZG Alchemist Control spreadsheet visible)  
- **WRITE CAPABILITY:** MCP can create/update — **Owner-gated**  
- **CURRENT ACCESS:** CONNECTED via `user-Google-drive`  
- **CURRENT HEALTH:** CONNECTED (MCP). Mac “messy Claude copies” (Access-Map).  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA MCP  
- **FRESHNESS:** Live  
- **AUTH METHOD:** OAuth (MCP)  
- **PERMISSION SCOPE:** Matt Google account  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET for read of named sheets; TRANSITIONAL as vault mirror  
- **RISK:** MEDIUM write / LOW read  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** Open one named finance sheet read-only; confirm no write  
- **FAILURE BEHAVIOUR:** Soft-fail; mark UNKNOWN  
- **ROLLBACK:** Disconnect MCP / revoke OAuth

### 5. Google Sheets (subset of Drive)
- **SYSTEM:** Google Sheets (via Drive)  
- **BUSINESS/DOMAIN:** Leads / Alchemist / finance trackers  
- **PURPOSE:** Lead tabs + Alchemist Control + bookkeeping  
- **SOURCE OF TRUTH FOR:** Brand lead tabs (Atrium/Habitat scripts); Alchemist control sheet (ops)  
- **DATA RECEIVED:** Klaviyo sync scripts (Mac) historically write leads  
- **DATA SENT:** Board/tile reads  
- **READ/WRITE:** Read via Drive MCP proved; Mac script write CONFIGURED historically  
- **CURRENT ACCESS:** Sheet IDs referenced in Cursor brief; MCP sees sheet titles  
- **CURRENT HEALTH:** Sheet content freshness UNKNOWN without tab prove  
- **LAST SUCCESSFUL OBSERVATION:** Drive list 2026-09-22 20:31 WITA; lead scripts last proven context 21 Aug brief  
- **FRESHNESS:** MCP live; sheet rows UNKNOWN  
- **AUTH METHOD:** OAuth / service paths on Mac (not opened)  
- **PERMISSION SCOPE:** Brand lead sheets + finance  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (leads display)  
- **RISK:** HIGH if automated write without gate  
- **CURRENT COMMISSIONING STATE:** PARTIAL  
- **REQUIRED TEST:** Read-only open Leads tab row count; no write  
- **FAILURE BEHAVIOUR:** Empty tile; no invent  
- **ROLLBACK:** Disable lead-sync launchd

### 6. ESB CORE
- **SYSTEM:** ESB CORE (+ local `esb.sqlite` pull)  
- **BUSINESS/DOMAIN:** BZG / Uma Blu restaurant ops + books  
- **PURPOSE:** Sales/menus/GL pull; POS-adjacent  
- **SOURCE OF TRUTH FOR:** Restaurant sales (alongside sheet/Notion) — **do not pick winner vs Xero**  
- **DATA RECEIVED:** OMS pull via `esb_ingest.py`  
- **DATA SENT:** None from SuperGrok  
- **READ CAPABILITY:** Local sqlite historically; live API **no SuperGrok hook**  
- **WRITE CAPABILITY:** None commissioned  
- **CURRENT ACCESS:** Credential **filenames** exist (`esb-production.json`) — not opened. Sqlite mtime 17 Aug in Money-Apps-MAP.  
- **CURRENT HEALTH:** UNKNOWN live API; Alchemist/ESB-adjacent tiles warn 22 Sep  
- **LAST SUCCESSFUL OBSERVATION:** Money-Apps-MAP 2026-08-17  
- **FRESHNESS:** Stale for live  
- **AUTH METHOD:** JSON credential file on Mac (type only)  
- **PERMISSION SCOPE:** Ingest script  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET for BZG ops read  
- **RISK:** HIGH mutate; MEDIUM stale read  
- **CURRENT COMMISSIONING STATE:** CONFIGURED / UNKNOWN connected  
- **REQUIRED TEST:** Schema count on sqlite OR authenticated read-only API with Owner present  
- **FAILURE BEHAVIOUR:** Empty tiles  
- **ROLLBACK:** Stop `esb_ingest.py` schedule

### 7. Yanolja (AMG PMS)
- **SYSTEM:** Yanolja  
- **BUSINESS/DOMAIN:** Atrium / AMG hotel  
- **PURPOSE:** PMS occ/ADR/folios  
- **SOURCE OF TRUTH FOR:** Hotel inventory/occupancy when live  
- **DATA RECEIVED:** Import/night-audit paths (store raw)  
- **DATA SENT:** None invented  
- **READ/WRITE:** API live status historically `yanolja_live=false` in atrium finance inventory; Access-Map says “in use” for product  
- **CURRENT ACCESS:** Cloud product in use by humans; agent API **UNKNOWN / not live** in board notes  
- **CURRENT HEALTH:** Tile occ noted historically; 22 Sep not re-proved here  
- **LAST SUCCESSFUL OBSERVATION:** Access-Map 7 Sep “in use”; finance inventory “not live” for figures  
- **FRESHNESS:** Conflicting evidence → UNKNOWN agent health  
- **AUTH METHOD:** UNKNOWN (not opened)  
- **PERMISSION SCOPE:** Hotel finance allow lists  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (hotel)  
- **RISK:** HIGH if invent rows  
- **CURRENT COMMISSIONING STATE:** PARTIAL / UNKNOWN  
- **REQUIRED TEST:** Read-only occ snapshot with source stamp; zero invented AR  
- **FAILURE BEHAVIOUR:** Empty tiles; `yanolja_live=false`  
- **ROLLBACK:** Disable import jobs

### 8. Alchemist
- **SYSTEM:** Alchemist (local DB + board + Telegram bot RETIRED channel)  
- **BUSINESS/DOMAIN:** Uma Blu / BZG procurement & pay desk  
- **PURPOSE:** Orders, owe/paid, tin  
- **SOURCE OF TRUTH FOR:** Supplier owe/paid (ops) — verify vs sheet  
- **DATA RECEIVED:** POs / payments  
- **DATA SENT:** Pay desk actions (Owner/money_allow)  
- **READ CAPABILITY:** Tile + local `alchemist.db`  
- **WRITE CAPABILITY:** Pay desk — **Owner-gated**  
- **CURRENT ACCESS:** Tile live on Prod path evidence 22 Sep (owe Rp 62,950,910 — tile-only, do not invent cause)  
- **CURRENT HEALTH:** WARN (owe jump vs 20 Sep)  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 consultant  
- **FRESHNESS:** Same-day tile  
- **AUTH METHOD:** Local DB path; bot tokens RETIRED/historical for Telegram  
- **PERMISSION SCOPE:** `money_allow` + confirm phrase for pay  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (board/DB); Telegram surface RETIRED  
- **RISK:** CRITICAL for pay write  
- **CURRENT COMMISSIONING STATE:** CONNECTED (tile) — WRITE not commissioned for agents  
- **REQUIRED TEST:** Read-only owe/paid/tin reconcile vs Alchemist Control sheet  
- **FAILURE BEHAVIOUR:** Show warn; no pay  
- **ROLLBACK:** Freeze pay desk route

### 9. Klaviyo
- **SYSTEM:** Klaviyo  
- **BUSINESS/DOMAIN:** AMG/Atrium/Habitat CRM leads  
- **PURPOSE:** Lead ingest → sheets / (historical ClickUp/Telegram)  
- **SOURCE OF TRUTH FOR:** Marketing leads when keys live  
- **DATA RECEIVED:** Form/list events  
- **DATA SENT:** Lead sync scripts; **board push OFF**  
- **READ/WRITE:** Scripts CONFIGURED; SuperGrok hook **none** (Access-Map)  
- **CURRENT ACCESS:** Cloud “live” per Access-Map; keys not probed  
- **CURRENT HEALTH:** UNKNOWN this pass  
- **LAST SUCCESSFUL OBSERVATION:** Access-Map 7 Sep; Cursor brief 21 Aug (push off)  
- **FRESHNESS:** Stale for API  
- **AUTH METHOD:** Env/API key on Mac (name only; not opened)  
- **PERMISSION SCOPE:** Brand lists  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET read; WRITE/push Owner-gated OFF  
- **RISK:** HIGH push  
- **CURRENT COMMISSIONING STATE:** CONFIGURED / UNKNOWN connected  
- **REQUIRED TEST:** Read-only list count; confirm push flag off  
- **FAILURE BEHAVIOUR:** No notify invent  
- **ROLLBACK:** Stop lead-sync plists; keep push off

### 10. Metricool
- **SYSTEM:** Metricool  
- **BUSINESS/DOMAIN:** Content analytics (5 produce brands + Goss Group shell)  
- **PURPOSE:** Analytics / scheduling UI for humans  
- **SOURCE OF TRUTH FOR:** Follower/engagement snapshots  
- **DATA RECEIVED:** Network insights  
- **DATA SENT:** Humans upload; Wolf **must not auto-post**; Beta `/api/admin/sync-metricool` READ sync only  
- **READ CAPABILITY:** YES — MCP `getBrandSettings` returned 6 brands 2026-09-22 20:31 WITA; Atlas metricool GREEN 22 Sep 07:38  
- **WRITE CAPABILITY:** Schedule/post exists in product — **Owner NO default for agents**  
- **CURRENT ACCESS:** MCP CONNECTED; Mac sync endpoint CONFIGURED in serve_beta mirror  
- **CURRENT HEALTH:** GREEN freshness 22 Sep; MCP live  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA MCP + 22 Sep Atlas  
- **FRESHNESS:** Live  
- **AUTH METHOD:** MCP OAuth / Metricool user token (not printed)  
- **PERMISSION SCOPE:** Brands under mrwolf@wolfcommand.net  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET read  
- **RISK:** HIGH post; LOW read  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** Analytics read one brand; publish-gate rejects non-approved  
- **FAILURE BEHAVIOUR:** Soft-fail sync; no post  
- **ROLLBACK:** Disable sync route / MCP

### 11. Email / Gmail
- **SYSTEM:** Gmail (multi-account MCP: primary + gosscap, mojozigzag, bluzone*, goss-*)  
- **BUSINESS/DOMAIN:** Comms  
- **PURPOSE:** Mail triage / drafts  
- **SOURCE OF TRUTH FOR:** Inbox threads  
- **DATA RECEIVED:** Mail  
- **DATA SENT:** Send/draft — **Owner-gated**  
- **READ CAPABILITY:** YES — primary `search_threads` succeeded 2026-09-22 20:31 WITA  
- **WRITE CAPABILITY:** send/draft tools present — default NO for commissioning  
- **CURRENT ACCESS:** MCP CONNECTED (primary probed)  
- **CURRENT HEALTH:** CONNECTED  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA  
- **FRESHNESS:** Live  
- **AUTH METHOD:** OAuth (MCP)  
- **PERMISSION SCOPE:** Connected mailboxes  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET read; WRITE external action gated  
- **RISK:** HIGH send  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** Read inbox metadata only; no send  
- **FAILURE BEHAVIOUR:** Soft-fail  
- **ROLLBACK:** Revoke MCP

### 12. Cloudflare (Access + Tunnel + Docs MCP)
- **SYSTEM:** Cloudflare Access / cloudflared tunnel / DNS  
- **BUSINESS/DOMAIN:** Edge identity for Beta/Prod dashboards  
- **PURPOSE:** Gate `beta.wolfcommand.net`, `dash.wolfcommand.net`, money/hr hostnames  
- **SOURCE OF TRUTH FOR:** Who can hit dashboards  
- **DATA RECEIVED:** Auth JWT / email header  
- **DATA SENT:** Tunnel to Mac :8787/:8788  
- **READ CAPABILITY:** Public challenge observed 2026-09-22 20:31 WITA (302→Access login) for beta+dash  
- **WRITE CAPABILITY:** CF dashboard (not via this agent)  
- **CURRENT ACCESS:** Access **CONNECTED** (challenge live). Tunnel status on Mac **UNKNOWN** this pass. Docs MCP CONNECTED.  
- **CURRENT HEALTH:** Edge gate up; app behind gate not opened without JWT  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA curl CF Access  
- **FRESHNESS:** Live edge  
- **AUTH METHOD:** Cloudflare Access (email IdP); tunnel token on Mac (not opened)  
- **PERMISSION SCOPE:** wolfcommand Access apps  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** HIGH if bypass  
- **CURRENT COMMISSIONING STATE:** CONNECTED (edge) — AWAITING_OWNER for Beta JWT wiring prove  
- **REQUIRED TEST:** Browser CF login → Beta 200; anon API missing_auth≠404  
- **FAILURE BEHAVIOUR:** Fail-closed  
- **ROLLBACK:** Keep Access on; do not open anon

### 13. Wolf Intelligence model/tool providers (Beta)
- **SYSTEM:** Beta LLM dispatch (`/api/llm/generate` in serve_beta)  
- **BUSINESS/DOMAIN:** Intelligence  
- **PURPOSE:** Multi-LLM generate on :8788  
- **SOURCE OF TRUTH FOR:** None (generative)  
- **DATA RECEIVED:** Prompts  
- **DATA SENT:** Provider API calls when keys present  
- **READ/WRITE:** Provider calls = external action  
- **CURRENT ACCESS:** Code path in beta-os-work mirror; `BETA_LLM_DRY_RUN` env; live keys **UNKNOWN** (not opened)  
- **CURRENT HEALTH:** UNKNOWN  
- **LAST SUCCESSFUL OBSERVATION:** Code mirror only  
- **FRESHNESS:** UNKNOWN  
- **AUTH METHOD:** Provider API keys via env (names not enumerated from live .env)  
- **PERMISSION SCOPE:** Beta only  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (Beta)  
- **RISK:** MEDIUM cost / data leak  
- **CURRENT COMMISSIONING STATE:** CONFIGURED (code) / UNKNOWN keys  
- **REQUIRED TEST:** Dry-run generate; confirm no prod port  
- **FAILURE BEHAVIOUR:** Soft-fail JSON error  
- **ROLLBACK:** Set dry-run; stop serve-beta

### 14. Beta infra (:8788 / beta.wolfcommand.net)
- **SYSTEM:** Wolf Beta dashboards (`serve_beta` / LaunchAgent `net.wolfcommand.serve-beta`)  
- **BUSINESS/DOMAIN:** Platform  
- **PURPOSE:** Staff Beta UI + APIs  
- **SOURCE OF TRUTH FOR:** Beta boards/state under beta-os  
- **DATA RECEIVED:** Uploads/API  
- **DATA SENT:** UI  
- **READ/WRITE:** Local full when on Mac loopback; CF Access when remote  
- **CURRENT ACCESS:** Public hostname challenges Access. Loopback **not opened** this executor.  
- **CURRENT HEALTH:** Edge up; process health UNKNOWN  
- **LAST SUCCESSFUL OBSERVATION:** Edge 2026-09-22 20:31 WITA; prior packs claim Progress 200 after restart (historical)  
- **FRESHNESS:** Edge live; app UNKNOWN  
- **AUTH METHOD:** CF Access JWT intended; serve_beta notes JWT not fully wired in older mirror comments — **re-prove on Mac**  
- **PERMISSION SCOPE:** Beta only (refuse :8787)  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** HIGH if prod confusion  
- **CURRENT COMMISSIONING STATE:** PARTIAL  
- **REQUIRED TEST:** `curl 127.0.0.1:8788/progress` on Mac; confirm :8787 untouched  
- **FAILURE BEHAVIOUR:** Fail loud if port busy/wrong  
- **ROLLBACK:** launchctl kickstart Beta only

### 15. Production infra (:8787 / dash.wolfcommand.net)
- **SYSTEM:** Production dashboards (`dashboards/serve.py`)  
- **BUSINESS/DOMAIN:** Platform  
- **PURPOSE:** Live staff boards  
- **SOURCE OF TRUTH FOR:** Prod tiles (Alchemist, Atlas, money, etc.)  
- **DATA RECEIVED/SENT:** Ops data  
- **READ CAPABILITY:** Allowed read-only for evidence  
- **WRITE CAPABILITY:** **FORBIDDEN** for this pack  
- **CURRENT ACCESS:** CF Access challenge live 2026-09-22 20:31 WITA  
- **CURRENT HEALTH:** Consultant 22 Sep system 14/14 / Atlas red — tiles updating  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 consultant  
- **FRESHNESS:** Same-day  
- **AUTH METHOD:** CF Access email header; local Mac full  
- **PERMISSION SCOPE:** Production sacred  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (protect)  
- **RISK:** CRITICAL if mutated  
- **CURRENT COMMISSIONING STATE:** CONNECTED — READ-ONLY commissioning  
- **REQUIRED TEST:** Read tile JSON only; no restart/write  
- **FAILURE BEHAVIOUR:** Stop pack  
- **ROLLBACK:** N/A (no changes)

### 16. Google Calendar
- **SYSTEM:** Google Calendar  
- **BUSINESS/DOMAIN:** Scheduling  
- **PURPOSE:** Calendar read/suggest  
- **READ CAPABILITY:** YES — `list_calendars` 2026-09-22 20:31 WITA  
- **WRITE CAPABILITY:** create/update events — Owner-gated  
- **CURRENT ACCESS:** MCP CONNECTED  
- **CURRENT HEALTH:** CONNECTED  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA  
- **AUTH METHOD:** OAuth MCP  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** MEDIUM write  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** List calendars; no create  
- **FAILURE BEHAVIOUR:** Soft-fail  
- **ROLLBACK:** Revoke MCP

### 17. Notion
- **SYSTEM:** Notion  
- **BUSINESS/DOMAIN:** Working docs  
- **PURPOSE:** HQ docs / tasks notes  
- **READ CAPABILITY:** YES — search succeeded 2026-09-22 20:31 WITA  
- **WRITE CAPABILITY:** Page create/update — Owner-gated  
- **CURRENT ACCESS:** MCP CONNECTED  
- **CURRENT HEALTH:** CONNECTED  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA  
- **AUTH METHOD:** OAuth MCP  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET (working); Obsidian remains vault canon  
- **RISK:** MEDIUM write  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** Search-only  
- **FAILURE BEHAVIOUR:** Soft-fail  
- **ROLLBACK:** Revoke MCP

### 18. Obsidian vault (local)
- **SYSTEM:** Obsidian at `~/WolfCommandSystem/WolfCommand`  
- **BUSINESS/DOMAIN:** Canonical Living Docs  
- **PURPOSE:** Source of truth docs  
- **CURRENT ACCESS:** On Mac only — **not opened** this pass  
- **CURRENT HEALTH:** UNKNOWN live  
- **LAST SUCCESSFUL OBSERVATION:** Access-Map 7 Sep “live”  
- **AUTH METHOD:** Local filesystem  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** HIGH if bulk edit  
- **CURRENT COMMISSIONING STATE:** CONFIGURED / UNKNOWN this executor  
- **REQUIRED TEST:** Path exists + open Access-Map  
- **FAILURE BEHAVIOUR:** Do not invent vault  
- **ROLLBACK:** Time Machine / B2

### 19. Time Machine
- **SYSTEM:** Time Machine  
- **BUSINESS/DOMAIN:** Mac restore  
- **PURPOSE:** Fast local restore  
- **CURRENT ACCESS:** Dest historically `/Volumes/Backups of Wolf’s Mac Studio`; share `04-Time-Machine` also observed in brief  
- **CURRENT HEALTH:** Running evidenced 7 Sep; `tmutil latestbackup` needs FDA  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-07  
- **AUTH METHOD:** Local + FDA  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** HIGH if delete backups  
- **CURRENT COMMISSIONING STATE:** CONNECTED (dated)  
- **REQUIRED TEST:** `tmutil status` read-only  
- **FAILURE BEHAVIOUR:** Note FDA block  
- **ROLLBACK:** N/A

### 20. Xero (GGV)
- **SYSTEM:** Xero  
- **BUSINESS/DOMAIN:** GGV books  
- **PURPOSE:** Group accounting until custom pack proved  
- **CURRENT ACCESS:** Cloud live for humans; credential file name `xero.json` (not opened); **no SuperGrok hook**  
- **CURRENT HEALTH:** UNKNOWN agent; do not cancel  
- **LAST SUCCESSFUL OBSERVATION:** Access-Map / Money-Apps 17 Aug–7 Sep  
- **AUTH METHOD:** OAuth/json on Mac  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TRANSITIONAL (cutover to custom books)  
- **RISK:** CRITICAL post  
- **CURRENT COMMISSIONING STATE:** CONFIGURED / UNKNOWN connected for agents  
- **REQUIRED TEST:** Human login only unless Owner YES read-only API  
- **FAILURE BEHAVIOUR:** No post  
- **ROLLBACK:** Leave login

### 21. Jotform
- **SYSTEM:** Jotform  
- **BUSINESS/DOMAIN:** GGV intake forms  
- **PURPOSE:** Client intake  
- **READ CAPABILITY:** YES — search listed GGV Client Intake forms 2026-09-22 20:31 WITA  
- **WRITE CAPABILITY:** Form edit / assign — Owner-gated  
- **CURRENT ACCESS:** MCP CONNECTED  
- **CURRENT HEALTH:** CONNECTED  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA  
- **AUTH METHOD:** MCP API  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TARGET  
- **RISK:** MEDIUM  
- **CURRENT COMMISSIONING STATE:** CONNECTED — AWAITING_OWNER  
- **REQUIRED TEST:** List forms; no edit  
- **FAILURE BEHAVIOUR:** Soft-fail  
- **ROLLBACK:** Revoke MCP

### 22. GitHub (`wolfcommand/wolf-system`)
- **SYSTEM:** GitHub  
- **BUSINESS/DOMAIN:** Code remote (stale vs live Mac)  
- **PURPOSE:** Remote origin — **not** live tree SoT  
- **CURRENT ACCESS:** origin URL known; live tree dirty/ahead (21 Aug brief). MCP Github present.  
- **CURRENT HEALTH:** Remote stale vs Mac  
- **LAST SUCCESSFUL OBSERVATION:** Cursor brief 21 Aug  
- **AUTH METHOD:** HTTPS/gh  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** TRANSITIONAL until push gate  
- **RISK:** HIGH force-push  
- **CURRENT COMMISSIONING STATE:** PARTIAL  
- **REQUIRED TEST:** `gh repo view` read-only; no push  
- **FAILURE BEHAVIOUR:** Do not push  
- **ROLLBACK:** N/A

### 23. GitLab MCP
- **SYSTEM:** GitLab  
- **BUSINESS/DOMAIN:** Optional remotes  
- **PURPOSE:** Unclear for Beta SoT  
- **CURRENT ACCESS:** MCP servers present; `search_repositories` 403 insufficient scope on PAT; public list noise  
- **CURRENT HEALTH:** PARTIAL / scope-limited  
- **LAST SUCCESSFUL OBSERVATION:** 2026-09-22 20:31 WITA  
- **AUTH METHOD:** PAT (granular) / OAuth  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** UNKNOWN need  
- **RISK:** LOW if unused  
- **CURRENT COMMISSIONING STATE:** PARTIAL  
- **REQUIRED TEST:** whoami + project list with proper scope  
- **FAILURE BEHAVIOUR:** Ignore  
- **ROLLBACK:** Revoke token

### 24. Slack MCP
- **SYSTEM:** Slack  
- **BUSINESS/DOMAIN:** Comms  
- **PURPOSE:** Channel messaging  
- **CURRENT ACCESS:** MCP tools listed in catalog — **not probed** this pass (avoid SendToUser)  
- **CURRENT HEALTH:** UNKNOWN  
- **AUTH METHOD:** OAuth MCP  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** UNKNOWN / optional  
- **RISK:** HIGH send  
- **CURRENT COMMISSIONING STATE:** CONFIGURED (MCP present) / UNKNOWN  
- **REQUIRED TEST:** list channels read-only  
- **FAILURE BEHAVIOUR:** No send  
- **ROLLBACK:** Revoke

### 25. ActiveCampaign
- **SYSTEM:** ActiveCampaign  
- **BUSINESS/DOMAIN:** Selong Selo client CRM  
- **PURPOSE:** Client email CRM  
- **CURRENT ACCESS:** Access-Map “live for client” — no MCP  
- **CURRENT HEALTH:** UNKNOWN  
- **OWNER:** Matt + client  
- **TARGET/TRANSITIONAL/RETIRE:** CLIENT-scoped  
- **RISK:** MEDIUM  
- **CURRENT COMMISSIONING STATE:** DISCOVERED  
- **REQUIRED TEST:** Human-only unless Owner YES  
- **FAILURE BEHAVIOUR:** Leave  
- **ROLLBACK:** N/A

### 26. Mews / Origin
- **SYSTEM:** Mews; Origin  
- **BUSINESS/DOMAIN:** Hotel/booking (if any)  
- **PURPOSE:** Referenced in investigation list  
- **CURRENT ACCESS:** **No solid CONFIGURED evidence** in Access-Map / Money-Apps / Cursor brief this pass  
- **CURRENT HEALTH:** UNKNOWN / likely absent  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** UNKNOWN — do not invent  
- **RISK:** N/A  
- **CURRENT COMMISSIONING STATE:** NOT FOUND (evidence-absent)  
- **REQUIRED TEST:** Mac `rg mews|origin` in beta-os + credentials dir **names only**  
- **FAILURE BEHAVIOUR:** Remain NOT FOUND  
- **ROLLBACK:** N/A

### 27. ClickUp — RETIRED
- **SYSTEM:** ClickUp  
- **BUSINESS/DOMAIN:** Tasks (historical)  
- **PURPOSE:** Was tasks / lead sink  
- **CURRENT ACCESS:** MCP `user-Clickup` still exists in SuperGrok catalog; Access-Map 7 Sep still said live — **Owner directive 22 Sep: RETIRED**  
- **CURRENT HEALTH:** RETIRED / HISTORICAL ONLY  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** **RETIRE**  
- **RISK:** Confusion if used  
- **CURRENT COMMISSIONING STATE:** **RETIRED**  
- **REQUIRED TEST:** None — do not commission  
- **FAILURE BEHAVIOUR:** Refuse new writes  
- **ROLLBACK:** N/A

### 28. Telegram — RETIRED
- **SYSTEM:** Telegram bots (Peaches, Nirmata, ATLAS, Alchemist, Spartacus, Kirana, …)  
- **BUSINESS/DOMAIN:** Historical bot runtime via OpenClaw  
- **PURPOSE:** Staff/owner messaging (historical)  
- **CURRENT ACCESS:** Tokens historically in OpenClaw; mute flags; many jobs parked 20 Aug  
- **CURRENT HEALTH:** RETIRED / HISTORICAL ONLY (Owner 22 Sep). Prior “on but broken” notes are historical.  
- **OWNER:** Matt  
- **TARGET/TRANSITIONAL/RETIRE:** **RETIRE**  
- **RISK:** Accidental blast if revived  
- **CURRENT COMMISSIONING STATE:** **RETIRED**  
- **REQUIRED TEST:** None — do not commission  
- **FAILURE BEHAVIOUR:** Refuse new bots/tokens  
- **ROLLBACK:** Keep mute / parked plists

---

## Evidence gaps / blockers

1. **Mac local-exec not attached** — cannot write `/Users/wolfterminal/beta-os/...` from this executor; cannot `ls /Volumes` or curl `:8788` loopback.  
2. Live `.env` / credential files **not opened** (by design).  
3. Integration Health UI on Beta **not opened**.  
4. `state/build-factory/GATES.json` / `PRIORITY-QUEUE.json` **existence on Mac UNKNOWN** — staged copies prepared for apply.  
5. NAS file counts **UNKNOWN** this pass.  
6. Mews/Origin **not found** in available evidence.

## Staging note

Files also staged at `/workspace/deliveries-connection-commissioning-2026-09-22/` with `MAC-APPLY.sh` for Mac Shell apply to `beta-os`.

---

*End register draft.*
