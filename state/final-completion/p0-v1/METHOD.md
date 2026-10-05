# METHOD.md — P0 V1 Surface Forensic Inventory (corrected)

Generated: 2026-09-30T10:55:00+08:00 (Asia/Makassar / WITA)
Executor: Peaches executor · machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`
Constraint: Did **not** create Exit Report · Did **not** touch prod :8787 · HR deferred · beta-only writes under `~/beta-os/state/final-completion/p0-v1/` (Mac sync pending if unreachable)

## Why prior discovery failed

Matt proved **465 requirements missed TRADING and FITNESS**. Root cause was **documents-first reconstruction**:

1. `requirements.jsonl` (465) was built from interview ledger + Master Spec constitutional bullets + domain pack seeds.
2. Keyword search of those 465 texts finds **only 2 hits**:
   - Master Spec package product list containing the word "fitness" (stay+fitness packages) — **not** Owner Fitness Command.
   - Master Spec private-domains bullet naming health / fitness / travel / investments/trading analysis — **not** expanded into capability records, routes, DBs, or bots.
3. `MODEL-C-CAPABILITY-CATALOG.md` explicitly marks **Personal Command / Trading (Spec §18) = OUT**.
4. Beta `dashboards/assets/sidenav.js` **Wave 8** retires `trading` / `travel` / `spartacus` / `mila` / `amanda` / `kuta-rates` from primary IA (soft-redirect only).

So a requirements pass that starts from the 465 list **cannot see** Owner Trading or Spartacus even though they are live on V1.

## Corrected enumeration method (this pass)

Walk **actual authorised V1 sources** on Mac + mirrors, then reconcile names back to 465 (not the other way around).

### A. Live app root (primary)
- `~/.openclaw/workspace/wolf-system/` (git remote `github.com/wolfcommand/wolf-system`)
- Dashboards: `dashboards/*.html` (55 HTML boards)
- Menu SoT: `dashboards/data/manifest.json` (23 registered live boards incl. **trading**, **spartacus**, **travel**)
- Master tiles: `dashboards/data/master.status.json` (includes **Spartacus 75** tile as of 2026-09-30)
- Nav entities: `dashboards/data/nav-entities.json`
- Desks: `trading-desk/`, `wolf-desk/`, `amanda-desk/`, `mila-desk/`, `peaches-desk/`, `uma-blu-desk/`, `training-centre/`, `resolve-studio/`
- Scripts: `scripts/` (~662)
- State/data dirs, n8n-templates (11)

### B. OpenClaw runtime & data
- `~/.openclaw/data/` — `esb.sqlite`, `wolf-catalogue.sqlite`, `competitor-rates.db`, `rate-calendar.db`
- `~/.openclaw/personal/health/` — **spartacus.sqlite**, Wolf75, diet, log (Fitness SoT)
- `~/.openclaw/hr/state/` — employees/tasks/payments/shifts/reviews (HR — deferred)
- `~/.openclaw/workspace/alchemist/` — alchemist.db
- Telegram bot roster from ACCESS-MAP (Peaches, Nirmata, ATLAS, Alchemist, **Spartacus**, Kirana)

### C. Automations
- `~/Library/LaunchAgents` — ~283 `com.wolfcommand*` / `com.wolfcommandsystem*` agents
- `~/.n8n` + `wolf-system/n8n-templates`

### D. Vault / Living Docs
- `~/WolfCommandSystem/WolfCommand/` Obsidian vault
- System-Registry: Dashboard-Map, Money-Apps-MAP, ACCESS-MAP, HOLDINGS-PERSONAL, GAPS, BASELINE-INVENTORY

### E. Mirrors / DR
- `~/WolfRecoveryPoints/2026-09-29_1220.partial/` (includes trading-desk)
- `/Volumes/05-Wolf-Vault-Mirror/wolf-command/` NAS DR package
- Box mirrors under `/workspace/state/final-completion/`

### F. Beta cross-check (replacement map only — not discovery source)
- `~/beta-os/dashboards/` + catalog
- sidenav Wave 8 retire list
- MODEL-C OUT row for Personal Command / Trading

### G. Explicit Trading + Fitness probes (mandatory)
- Paths: `*trading*`, `*sparta*`, `*fitness*`, `*workout*`, `*peptide*`, `*holdings*`
- Boards: `trading.html`, `spartacus.html`
- Data: `trading-desk/`, `personal/health/`, `spartacus-*.json`
- Bots: Telegram Spartacus
- Continue forgotten Owner surfaces (travel, learning, radar, kuta-rates, ads-studio, desks, Gatekeeper, event bus, …)

## Classification rubric

| Class | Meaning |
|-------|---------|
| REBUILT+PROVEN | Beta replacement live + proven |
| REBUILT_BUT_NOT_LIVE | Code/app exists not fully commissioned |
| PARTIAL | Beta pack/page covers some of V1 surface |
| MISSING | Evidenced on V1; no adequate beta surface |
| HISTORICAL_PRESERVATION_REQUIRED | Keep data/docs even if not rebuilt as product |
| SUPERSEDED | Parked/replaced |
| EXTERNALLY_BLOCKED | External vendor/Matt action |
| HR_DEFERRED | Per mission — do not expand HR this week |

## Outputs

- Prefer: `~/beta-os/state/final-completion/p0-v1/V1-SURFACE-MANIFEST-DRAFT.json`
- Box: `/workspace/state/final-completion/p0-v1/V1-SURFACE-MANIFEST-DRAFT.json`
- `METHOD.md` alongside

## Limits

- Starter: major surfaces + all personal/trading/fitness finds; not every one of 662 scripts.
- Did not open secrets/tokens/staff PII rows.
- Did not call :8787 (read files only).
- Pass 2: remaining HTML not in manifest.json, script families, Notion DB inventory.

## Reconcile

- 465 file: `/Users/wolfterminal/beta-os/state/final-completion/ORIGINAL-REQUIREMENTS-RECONSTRUCTION/requirements.jsonl` (box mirror `/workspace/state/final-completion/ORIGINAL-REQUIREMENTS-RECONSTRUCTION/requirements.jsonl`)
- Trading/Fitness dedicated capabilities in 465: **0**
- Newly recovered: see manifest `reconcile_465.newly_recovered_names`
