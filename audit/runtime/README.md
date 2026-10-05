# Wolf Runtime / Agent / Disk Forensic Audit

**Generated:** 2026-10-05T22:16:21+08:00 (Asia/Makassar)  
**Mode:** DISCOVERY ONLY — no retires, deletes, prod changes, factory restarts, or Wolf Intelligence build  
**Machine:** Wolfs-Mac-Studio (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)  
**Repo path:** `audit/runtime/`  
**Emergency pause taken:** NO  

## Executive summary (Matt fields)

| Field | Value |
|---|---|
| TOTAL AGENTS | 33 |
| GROK AGENTS | 2 |
| ACTIVE | 24 |
| IDLE | 15 |
| DUPLICATE/OVERLAPPING | 5 |
| ORPHANED | 5 |
| RETIRE CANDIDATES | 6 |
| V1 ONLY | see v1-retirement-map.json (alchemist/reel/atlas-auto/content-fleet/aios/alpha et al.) |
| BETA ONLY | serve-beta :8788, catalog/*, build-factory, catalog-backup-retention, llm_orchestrator |
| SHARED | openclaw gateway, peaches, ollama, cloudflared patterns, atrium sidecar, Grok/Cursor |
| CURRENT STUDIO FREE SPACE | **102.0 GB** (Data volume ~77% used) |
| ESTIMATED EVENTUAL RECLAIMABLE GB | **~110 GB** conservative after NAS archive (up to ~140 aggressive) |
| BACKUP GROWTH ROOT CAUSE | Migrations/tests copied live `content_library.sqlite` (~110MB) into `catalog/backups` (`pre-*.sqlite` 24.65GB + test tmpdirs); factory `tmp-f1` held 53GB copies (cleaned earlier today −57GB); prod `daily-backup` wrote **44GB** wolf-system tree on 2026-10-05. Growth now largely contained (0 new pre-*.sqlite in last 60m; retention every 6h). |
| UNNECESSARY AI/CREDIT CONSUMPTION | Overlapping Grok ↔ Cursor ↔ Peaches ↔ OpenClaw for same owner/factory work; stale Ollama; keepalive polling; PARKED factory items still configured; multi-LLM Content Engine keys present with dry-run flag |
| FACTORY ORCHESTRATION PROBLEMS | Soft-held OWNER P0 single-track; multi-queue; ACTIVE.done residue; human-gate backlog (5+); credit-conservation idle; watch WAIT_SILENT_IDLE; undelivered GATEFAIL notifications; do-not-restart |
| UNKNOWN ITEMS | Desktop media 14.6GB; Library App Support 34GB; Codex usage; which callers hit Ollama; opsfix3 scratch catalogs; some parked plist still-loaded state |

## Configured vs running

- Wolf-related LaunchAgent **plists configured:** ~179  
- **Running with PID:** 22  
- **Loaded idle (no PID):** 139  
- Parked/disabled/bak files in LaunchAgents: ~109  
- Docker: unavailable  

## Key running services

| Name | PID | Port | Env |
|---|---|---|---|
| prod dashboards serve | 1297 | 8787 | PROD |
| beta serve | 47807 | 8788 | BETA |
| openclaw gateway | 1308 | 18789 | SHARED |
| cloudflared wolf-dash | 1307 | 20241 | PROD |
| ollama | 1328 | 11434 | SHARED |
| peaches-command / voice | 1336 / 1338 | — | PROD |
| spartacus / nirmata / kirana | 1354 / 2626 / 1333 | — | PROD |

## Grok agent audit (section 4)

- **Exist:** Grok Bot.app + `com.wolfcommand.grok-bot-keepalive` + `~/.grokbot` local-exec daemon state  
- **Running/meaningful:** YES — this Studio local-exec audit session  
- **No caller / historical:** keepalive is polling-style; no separate Grok “fleet” beyond Bot  
- **Overlap:** Grok ↔ Cursor ↔ Peaches ↔ OpenClaw for owner tasking and factory work  
- **Credit waste risk:** concurrent Cursor factory launches + Grok sessions; keepalive keeps app warm  
- **Polling vs event-driven:** keepalive = poll/respawn; local-exec = event/session  
- **Future Wolf Intelligence routing candidates:** owner task fan-out currently split across Grok/Cursor/Peaches — control plane NOT built (inventory only)

## Factory audit (section 5)

See `factory.json`. Lifecycle documented; supervisor soft-held; PRIORITY-QUEUE 44 items (30 PARKED); NOTIFY undelivered gatefails; disk guard thresholds 100/50/25 GB.

## Disk / backup (sections 6–7)

See `disk-inventory.json`. Largest Wolf dirs: `.openclaw` 137G (backups 80G + workspace 49G), `beta-os` 45G (catalog/backups 35G).  
Backup explosion traced in `docs/BACKUP-RETENTION.md` (Owner P0 5 Oct 2026). **No deletes performed by this audit.**

## V1 retirement map (section 8)

See `v1-retirement-map.json`. Map only — **do not retire**.

## Models (section 9)

See `models.json`. Providers: OpenAI, Anthropic/Claude, Gemini, xAI/Grok, Cursor, Ollama, HF cache. Credentials referenced by **key names / paths only**.

## Proof: Daily Close / Petty / Prod untouched by this audit

- Audit wrote **only** under `audit/runtime/` (+ git commit of those files).  
- Production tree `~/.openclaw/workspace/wolf-system` not modified (`serve.py` mtime still 2026-09-16).  
- No factory restart; no beta reload; no process pause.  
- Pre-existing dirty `dashboards/uma-blu-close.html` / `bzg-uma-blu-petty.html` were **left out of the audit commit**.

## Files in this folder

- runtime-inventory.json  
- agents.json  
- services.json  
- schedules.json  
- factory.json  
- models.json  
- disk-inventory.json  
- v1-retirement-map.json  
- dependency-map.json  
- retirement-candidates.json  
- README.md  

## Classification legend (recommendation only)

KEEP | MERGE CANDIDATE | REPLACE CANDIDATE | RETIRE CANDIDATE | UNKNOWN/INVESTIGATE  

**STOP.** Next phase not started.
