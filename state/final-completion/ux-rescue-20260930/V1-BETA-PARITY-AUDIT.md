# V1–BETA PARITY AUDIT (user perspective)
**Generated:** 2026-09-30T21:52:00+08:00 (WITA) · UX Rescue P0 · Peaches executor
**Honesty:** audits only · not LIVE_USABLE · not staff_ready · no Exit Report · finance SoD unchanged

## Summary counts
- Surfaces audited: **22**
- `BETA_BETTER`: **5**
- `BETA_MISSING_FUNCTION`: **3**
- `BETA_MORE_CONFUSING`: **2**
- `PARITY`: **5**
- `V1_BETTER`: **5**
- `V1_OBSOLETE`: **2**

## Classification legend
| Class | Meaning |
|-------|---------|
| V1_BETTER | V1 delivers clearer/usable function for the user today |
| BETA_BETTER | Beta is ahead (auth, SoD, structure, depth) |
| PARITY | Roughly equivalent capability (UI may differ) |
| BETA_MISSING_FUNCTION | User cannot do a V1 thing in Beta |
| BETA_MORE_CONFUSING | Capability exists but IA/pages worse |
| V1_OBSOLETE | Do not port as primary product |

## Surfaces
### Wolf Owner Home / Control — `V1_BETTER`
- **V1:** http://127.0.0.1:8787/, wolf.html, master.status.json tiles
- **User could (V1):** See live pulse tiles: Atrium occ, Kuta rates tonight, BZG last-night revenue/covers, leads, purchasing, Alchemist owe/paid, Spartacus day, backup; Open Boards drawer + Ask Peaches; Navigate WOLF TOOLS: Spartacus, Trading, Learning, Radar, Admin Access; One-glance Owner evening brief
- **Useful / bad (V1):** Dense live command glance; few clicks to ops reality / Some tiles locked/restricted without clear path; person-centric; loading hangs on wolf.html content body in headless
- **Beta:** /owner-empire-pack, /wolf, /business-dashboard, /owner-needs-you-1, /staff-ops-routing
- **User can (Beta):** Empire pack hub (when CF Access JWT present); Needs You / staff-ops routing; Honesty stamps on migration state
- **Gap:** Local :8788 Owner home BLOCKED_AUTH without Cloudflare JWT; no equivalent live multi-tile pulse in one screen from anon/headless; capability fragmented across prove packs
- **Preserve capability:** Owner live pulse (occ, rates, BZG night, leads, purchasing, health day, backup) on one Owner Home

### Trading Desk — `V1_BETTER`
- **V1:** trading.html, trading-desk/journal.jsonl, QUANT_PROGRAM.md
- **User could (V1):** Browse 14 research/hub cards: Holdings, Trade journal, TTC paper method, Morning brief, Filings, Earnings, Sector, Insider, Chatter, Floor, Research desk, 8-step desk, Sandbox, Agent OS; Paper-only research; LIVE badge with WITA timestamp; Sidebar stay in Wolf Tools
- **Useful / bad (V1):** Real navigable trading research workspace / Sprawl of cards; some may be stubs
- **Beta:** /owner/trading, /owner-trading-1.html
- **User can (Beta):** See PARTIAL honesty page: migration_state, provenance, holdings registry warnings; RO API /api/owner/trading-ro (+ history) wired; No live broker (correct)
- **Gap:** Not a usable desk — status/transfer page, not Holdings/Journal/TTC cards UI
- **Preserve capability:** Holdings glance + trade journal + TTC paper method UI under Owner Personal

### Spartacus Fitness / Health Command — `V1_BETTER`
- **V1:** spartacus.html, ~/.openclaw/personal/health/spartacus.sqlite
- **User could (V1):** Track Sparta/Wolf75, peptides, breathwork; See day counter on master tile; Telegram Spartacus bot (Mac)
- **Useful / bad (V1):** Live personal health command / Owner-only sprawl in primary tools list
- **Beta:** /owner/fitness, /owner-fitness-1.html
- **User can (Beta):** PARTIAL Spartacus transfer surface; Honesty stamps
- **Gap:** Not live health command; peptide schedule not rebuilt
- **Preserve capability:** Sparta/Wolf75 + peptide tracker with live sqlite-backed UI

### Travel Board — `V1_BETTER`
- **V1:** travel.html
- **User could (V1):** View/manage personal travel board
- **Useful / bad (V1):** Dedicated travel surface / Wave-era personal sprawl
- **Beta:** /owner/travel, /owner-travel-1.html
- **User can (Beta):** Owner travel stub in IA
- **Gap:** Thin vs V1 board
- **Preserve capability:** Owner travel itinerary/board

### Learning Desk / TTC learn — `BETA_MISSING_FUNCTION`
- **V1:** learning.html, learning-desk/, ttc-learn-base
- **User could (V1):** Learning entries, TTC paper quant pipeline views
- **Useful / bad (V1):** Ties to Flint quant learning / Niche; coupled to Discord ingest
- **Beta:** /owner/learning, /owner-learning-1.html, /intel-learning.html
- **User can (Beta):** Owner learning stub; intel-learning pack
- **Gap:** No full learning desk / TTC entries UI
- **Preserve capability:** TTC/learning entries + paper quant drafts (no live trade)

### Wolf Radar (Owner plan) — `BETA_MISSING_FUNCTION`
- **V1:** radar in Wolf Tools, radar boards
- **User could (V1):** Owner plan/radar board from Wolf Tools
- **Useful / bad (V1):** Owner planning glance / Unclear freshness
- **Beta:** /radar-prove
- **User can (Beta):** Prove pack only
- **Gap:** No Owner Radar as first-class Home item
- **Preserve capability:** Owner Radar / plan board on Home

### Atrium Sales / Management / Inventory — `BETA_MORE_CONFUSING`
- **V1:** atrium-sales.html, atrium-management.html, atrium-inventory.html
- **User could (V1):** Sales board, management, inventory on dedicated HTML
- **Useful / bad (V1):** Clear hotel ops surfaces / Three separate boards; limited auth model
- **Beta:** /amg-ops-pack, /amg-daily-ops-state, /amg-journey-workflow, /amg-occ-truth-1, /amg-os-shell
- **User can (Beta):** Ops pack hub + many deepen/prove shells; Day ops / journey / packages APIs
- **Gap:** Capability richer but UX more confusing — many *-1 prove pages
- **Preserve capability:** Atrium sales+occ+inventory+day-ops under one AMG hub with tabs

### Atrium Finance Desk — `BETA_BETTER`
- **V1:** atrium-finance.html, atrium-finance app
- **User could (V1):** Finance desk UI on V1
- **Useful / bad (V1):** Known FC desk / Auth weaker historically
- **Beta:** /amg/finance, /atrium-fc-truth-deepen-1, fin-* shells
- **User can (Beta):** SoD-aware finance routes; FC truth deepen; bank/recon/tax shells
- **Gap:** Human retest in parallel — do not change SoD; UX consolidation only
- **Preserve capability:** Finance SoD + FC desk; consolidate shells as tabs without weakening auth

### GGV Books / Finance — `BETA_MORE_CONFUSING`
- **V1:** ggv-finance.html
- **User could (V1):** View GGV books board
- **Useful / bad (V1):** Simple books surface / Limited ops breadth
- **Beta:** /ggv-finance, /ggv-ops-pack, /ggv-client-profitability, /ggv-strategy-machine, /ggv-pipeline-truth-1
- **User can (Beta):** Ops pack + client profitability + strategy machine + finance seat (GGV FC just landed)
- **Gap:** Many parallel pages; Owner confusion risk
- **Preserve capability:** GGV finance+ops+content under GGV hub; preserve FC seat SoD

### Uma Blu Ops + Recipes — `BETA_BETTER`
- **V1:** uma-blu.html, uma-blu-recipes.html
- **User could (V1):** Venue ops console; Recipes
- **Useful / bad (V1):** Focused venue board / Less depth on PR/petty/evidence loops
- **Beta:** /bzg/uma-blu, /bzg-uma-blu-*, /bzg-recipe-builder
- **User can (Beta):** Today, PR, issues, petty, evidence, exceptions, real, bills, recipe builder, APIs
- **Gap:** Split across many HTML files — should be tabs
- **Preserve capability:** Full Uma Blu today/PR/petty/evidence/recipe loops as tabs

### BZG Group / Finance / Monthly — `PARITY`
- **V1:** bzg boards, bzg-july-2026.html historical
- **User could (V1):** Group board, venue PnL-ish, monthly historical
- **Useful / bad (V1):** Monthly boards for shareholders historically / Monthly HTML freeze pattern obsolete as primary
- **Beta:** /bzg, /bzg-ops-desk, /bzg-finance, /bzg-venue-pnl, /bzg-waste-yield
- **User can (Beta):** Ops desk, finance, venue pnl, waste/yield, outlets
- **Gap:** Hub vs many merge candidates
- **Preserve capability:** BZG ops+finance+venue PnL; monthly boards historical preserve

### Content Hub + Brand Boards + Ads/Resolve — `PARITY`
- **V1:** content.html, content-* brand boards, ads-studio.html
- **User could (V1):** Per-brand content boards; Ads studio; Resolve studio; Catalogue
- **Useful / bad (V1):** Brand-specific content navigation / Duplication across brand HTML
- **Beta:** /content-2.0, /content-engine-live, /seats/content-desk, /seats/content-admin, /seats/ads-studio
- **User can (Beta):** Content 2.0 + seat surfaces in IA; Metricool wire packs
- **Gap:** Ads/Resolve seats exist as HTML but depth vs V1 unclear; brand boards collapsed
- **Preserve capability:** Content pipeline + Ads Studio + Resolve Studio seats

### Kuta Rates Competitor Board — `V1_BETTER`
- **V1:** kuta-rates.html, competitor-rates pipeline, rate-calendar.db
- **User could (V1):** See tonight competitor rate intel on master tile + dedicated board
- **Useful / bad (V1):** Actionable rate glance for Atrium / Pipeline Mac LaunchAgent coupled
- **Beta:** /kuta-rates, /kuta-rates-1.html, /ops-competitor-rates-pipeline-1.html, /ops-rate-calendar-1.html
- **User can (Beta):** IA item Kuta Rates (AMG); prove/pipeline packs
- **Gap:** Primary useful board vs prove sprawl; pipeline may not be live in Beta
- **Preserve capability:** Tonight competitor rates board + pipeline health under AMG

### Person desks (Wolf/Amanda/Mila/Haikal/Peaches) + ClickUp — `BETA_BETTER`
- **V1:** amanda.html, mila.html, haikal-desk
- **User could (V1):** Open named desk boards for tasks/routines
- **Useful / bad (V1):** Familiar per-person work queues / People≠Roles violation; brittle when staff changes
- **Beta:** /my-work, /my-work-item, /staff-ops-routing, /execution-report
- **User can (Beta):** Role/assignment oriented My Work; receivers API
- **Gap:** My Work blocked without auth; depth incomplete vs V1 desk habits
- **Preserve capability:** Per-assignment work queue (not person-named primary IA)

### Habitat Investment 2026 — `PARITY`
- **V1:** habitat-investment board on V1
- **User could (V1):** Owner investment board
- **Useful / bad (V1):** Owner personal investment view / Niche
- **Beta:** /habitat-investment-2026, /habitat-investment-1.html, /habitat-operator.html
- **User can (Beta):** In primary IA as Habitat Investment (Owner)
- **Gap:** May be thin pack
- **Preserve capability:** Habitat investment Owner surface

### AMG/BZG/GGV Voice Boards — `PARITY`
- **V1:** amg-voice.html, bzg-voice, ggv-voice on V1
- **User could (V1):** Voice/ops seat boards
- **Useful / bad (V1):** Seat-specific voice / Separate HTML sprawl
- **Beta:** /amg-voice, /bzg-voice, /ggv-voice, *-voice-1.html
- **User can (Beta):** In IA as voice seats
- **Gap:** Prove-level depth
- **Preserve capability:** Voice seats under each business

### HR Board — `V1_OBSOLETE`
- **V1:** hr.html
- **User could (V1):** HR board (often restricted)
- **Useful / bad (V1):** Historical HR entry / Policy deferred domain
- **Beta:** /hr-* deferred stamps
- **User can (Beta):** Deferred hold stamps only
- **Gap:** Intentionally deferred
- **Preserve capability:** HR deferred — do not commission this phase

### Gatekeeper + Event Bus — `BETA_MISSING_FUNCTION`
- **V1:** Gatekeeper vault, event_bus.db
- **User could (V1):** Owner gate/automation visibility (historical)
- **Useful / bad (V1):** System control plane awareness / Not polished product UI
- **Beta:** /owner-gatekeeper-1.html, /ops-event-bus-1.html
- **User can (Beta):** Prove/deepen pages only
- **Gap:** No Owner-usable Gatekeeper/Event Bus home
- **Preserve capability:** Owner-visible gatekeeper + event bus health under System

### Finish / commissioning (V1 absent as product) — `BETA_BETTER`
- **V1:** n/a — V1 was live boards not finish desk
- **User could (V1):** Operate live boards; no FINISH WOLF desk
- **Useful / bad (V1):** n/a / No single finish queue for Owner
- **Beta:** /finish-war-room, /commissioning-live, /progress, /v1-status
- **User can (Beta):** Finish war room + progress (when authed); Honesty scoreboards
- **Gap:** Not yet ONE start link containing FINISH WOLF on Owner Home; auth blocks local screenshot
- **Preserve capability:** FINISH WOLF desk on Owner Home as primary finish entry

### Integrations / Backup / LaunchAgents — `PARITY`
- **V1:** System tile 14/14, B2/R2 tiles, ~283 LaunchAgents
- **User could (V1):** See system green + backup capacity on home
- **Useful / bad (V1):** Home-level system faith / Opaque agent sprawl
- **Beta:** /integration-health, /backup-health-1, /restore-drill, /conn-health-1, /connector-*
- **User can (Beta):** Dedicated integration/backup packs
- **Gap:** Not on Owner Home pulse; prove naming
- **Preserve capability:** Integrations+backup health visible from System and Owner exceptions

### Global nav + auth model — `BETA_BETTER`
- **V1:** Boards + Wolf Tools sidebar, access_key=wolf era
- **User could (V1):** Simple local nav; often open :8787
- **Useful / bad (V1):** Fast Owner access on LAN / Weak auth; People≠Roles debt
- **Beta:** #wolfnav, sidenav.js IA_TREE, CF Access JWT, nav_authority
- **User can (Beta):** Clearance-driven IA; Business chips; UP/BACK/HOME; fail-closed auth
- **Gap:** Owner local UX blocked without JWT — hurts desktop commissioning screenshots
- **Preserve capability:** Authority-derived nav + fail-closed auth; need Owner session path for desktop UX test

### Alpha System DB — `V1_OBSOLETE`
- **V1:** ~/.openclaw/alpha/data/alpha.db
- **User could (V1):** Legacy alpha
- **Useful / bad (V1):** Historical only / Parked
- **Beta:** —
- **User can (Beta):** —
- **Gap:** n/a
- **Preserve capability:** Historical preserve only — no Beta product surface

## Top 10 V1_BETTER / BETA_MISSING (action priority)
1. **Wolf Owner Home / Control** (`V1_BETTER`) — Owner live pulse (occ, rates, BZG night, leads, purchasing, health day, backup) on one Owner Home
2. **Trading Desk** (`V1_BETTER`) — Holdings glance + trade journal + TTC paper method UI under Owner Personal
3. **Spartacus Fitness / Health Command** (`V1_BETTER`) — Sparta/Wolf75 + peptide tracker with live sqlite-backed UI
4. **Travel Board** (`V1_BETTER`) — Owner travel itinerary/board
5. **Learning Desk / TTC learn** (`BETA_MISSING_FUNCTION`) — TTC/learning entries + paper quant drafts (no live trade)
6. **Wolf Radar (Owner plan)** (`BETA_MISSING_FUNCTION`) — Owner Radar / plan board on Home
7. **Kuta Rates Competitor Board** (`V1_BETTER`) — Tonight competitor rates board + pipeline health under AMG
8. **Gatekeeper + Event Bus** (`BETA_MISSING_FUNCTION`) — Owner-visible gatekeeper + event bus health under System
