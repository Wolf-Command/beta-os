# GROK AUDIT — WOLF CURRENT ROUTE MAP
**Date:** 2026-09-22 ~15:50 WITA (Asia/Makassar UTC+8)  
**Lane:** Beta `:8788` / `beta.wolfcommand.net` (intent) · Production `:8787` listed only as sibling, not target  
**Author:** Grok Engineering Lead (Peaches / Wolf Command)

## Evidence basis (honest)
- **Executor:** BOX-BOUND (`hostname=grok-bot-vm-*`). Shell/`machineId` did **not** route to Wolfs-Mac-Studio this run.
- **Live Mac tree** `/Users/wolfterminal/beta-os` and live `:8788` process: **NOT opened**.
- **Live Beta public host** `https://beta.wolfcommand.net/*`: Cloudflare Access **302** for all probed paths (incl. nonsense path) — confirms host exists; cannot distinguish 200 vs 404 vs app 403 without auth.
- **Sources used:** Owner directive (this turn); box mirrors `/workspace/dashboards/{sidenav.js,serve.py,style.css,access-config.json}`; `/workspace/bf-review-dump.txt` (Beta `serve_beta` alias diffs); progress/habitat/Devi/compressed-sprint deliveries; Model C baseline; factory claim JSON; `wave1-smoke` atrium-finance notes.
- Fields marked **UNKNOWN** require Mac-routed `ls`/`rg`/`curl 127.0.0.1:8788` before Cursor implement packs treat them as PROVEN.
- **Production `:8787` sacred** — cited only as sibling evidence; do not mutate.
- **ACTIVE factory packs:** NOT killed. Devi commission claim + compressed-sprint plans left untouched.


## Standing chrome law
- **One** `#wolfnav` owner: `sidenav.js` (manifest-driven Boards list).
- **Never** a second Boards menu.
- Nav visibility ≠ permission (`access_key` / `whoami.pages` filter chrome only; APIs enforce).

## Inventory method
1. Harvest unique `*.html` names from Beta-related dumps + deliveries + prod dashboards mirror.  
2. Map known clean aliases from `serve_beta` / progress pack patches.  
3. Classify each row: role, org level, job, page-type, how reached, how back, overlaps, merge?, drop from primary nav?  
4. Mark live status: **EVIDENCED** (file/alias seen in dump) · **SIBLING-PROD** (prod dashboards mirror) · **OWNER-CLAIMED** (directive sprawl names without file proof) · **UNKNOWN**.

## Summary counts (this audit)
| Bucket | Count | Notes |
|--------|------:|-------|
| Unique user-facing HTML names harvested | **42** | Deduped; includes prod sibling boards |
| Clean Beta URL aliases evidenced | **10+** | `/progress`, `/bzg`, `/bzg/uma-blu*`, `/habitat-operator`, `/lead-spine`, `/uma-blu-close`, … |
| API families noted (not full API map) | **8+** | `/api/bzg/uma-blu/*`, `/api/progress`, `/api/planner*`, `/api/atrium`, `/whoami`, catalogue, HR/money (prod), venue-close |
| OWNER-CLAIMED sprawl (`*mgmt-cluster*`, `*operator-depth*`) | **UNKNOWN live count** | Must `find` on Mac Beta before merge plan execution |
| Drop from primary nav (recommendation) | **Most specialist + all System technical** | Keep capability via drill / System section / search |

---

## A. Empire / HOME surfaces

| Route / file | Live status | Who (role) | Org level | Job | Page-type | How reached | How back | Overlaps | Merge? | Drop primary nav? |
|---|---|---|---|---|---|---|---|---|---|---|
| `/wolf` → `wolf.html` / `dashboards/wolf.html` | EVIDENCED (name) | Owner / Exec | GROUP | Empire Pulse command | DASHBOARD | Primary HOME | Context / HOME | Radar, Needs You, Progress | Keep as Empire shell; absorb pulse tiles | No (Owner) |
| `/progress` → `progress.html` | EVIDENCED (alias pack + CF host) | Owner only | GROUP/SYSTEM | Build/sale readiness progress | SYSTEM | System / Owner | System | completion-register, factory | Keep; hide from staff | Yes for non-Owner |
| `radar.html` | SIBLING-PROD / EVIDENCED name | Owner / Exec | GROUP | Radar / priorities | DASHBOARD | HOME → Priorities | HOME | Empire tiles | Merge into Empire Priorities panel | Prefer hide standalone |
| Needs You surface | UNKNOWN path on Beta | Role-scoped | Assignment scope | Action queue | WORKSPACE | HOME / badge | Prior context | Issues boards per BU | Canonical HOME card → scoped workspace | Never dump all issues in global Boards |
| Exceptions / Priorities | UNKNOWN dedicated HTML | Owner / Mgr | Scope | Exception queue | DASHBOARD | HOME | HOME | Radar | Panels inside Empire / BU Overview | Drop standalone if exist |

## B. BZG / Uma Blu (Business)

| Route / file | Live status | Who | Org level | Job | Page-type | How reached | How back | Overlaps | Merge? | Drop primary? |
|---|---|---|---|---|---|---|---|---|---|---|
| `/bzg` → `bzg.html` | EVIDENCED | BZG leadership / ops | LEGAL ENTITY / SITE | BZG Overview | DASHBOARD | BUSINESSES → Blu Zone | HOME / Empire | Uma shells | Keep entity Overview | No |
| `/bzg/uma-blu` → `bzg-uma-blu.html` | EVIDENCED | Devi / Uma ops | VENUE | Uma Today / Overview | WORKSPACE | BZG → Uma Blu | BZG Overview | legacy `uma-blu.html` | Keep Beta path; retire prod-style top-level | Drop bare `/uma-blu.html` from primary |
| `/bzg/uma-blu/bills` → `bzg-uma-blu-bills.html` | EVIDENCED | Uma ops / F&B | VENUE | Bills | WORKSPACE | Uma subnav | Uma Today | Alchemist paydesk | Stay under Uma | Yes (not top Boards) |
| `/bzg/uma-blu/issues` → `bzg-uma-blu-issues.html` | EVIDENCED | Uma ops | VENUE | Issues | WORKSPACE | Uma → Issues | Uma | Needs You cards | Stay under Uma | Yes |
| `/bzg/uma-blu/petty` → `bzg-uma-blu-petty.html` | EVIDENCED | Uma ops | VENUE | Petty | WORKSPACE | Uma → Finance/Ops | Uma | Payment (NOT_BUILT) | Stay under Uma | Yes |
| `/uma-blu-close` → `uma-blu-close.html` | EVIDENCED | Closer-capable roles | VENUE | Daily close | WORKSPACE | Uma → Close CTA | Uma | venue_close APIs | Stay drill | Yes |
| `uma-blu.html` (legacy) | SIBLING-PROD | Ops | VENUE | Legacy Alchemist board | WORKSPACE | Historical Boards | Boards | Beta `/bzg/uma-blu` | **Redirect → Beta Uma** when ready | Yes drop primary |
| `uma-blu-recipes.html` | SIBLING-PROD name | Ops / kitchen | VENUE/DEPT | Recipes | DETAIL/WORKSPACE | Uma → Standards | Uma | Content assets | Nested | Yes |

## C. GGV / Content / Clients

| Route / file | Live status | Who | Org level | Job | Page-type | How reached | How back | Overlaps | Merge? | Drop primary? |
|---|---|---|---|---|---|---|---|---|---|---|
| `/lead-spine` → `lead-spine.html` | EVIDENCED | GGV ops / Amanda lane | BU / CLIENT proj | Lead spine operator | WORKSPACE | GGV → Operations/Customers | GGV Overview | Habitat operator, CRM scraps | Keep under GGV | Yes |
| `/habitat-operator` → `habitat-operator.html` | EVIDENCED | Habitat operators / Haikal lane | BRAND/CLIENT | Human operator UI | WORKSPACE | GGV → Habitat drill | GGV | content-habitat | Stay scoped to Habitat | Yes |
| `content-2.0.html` (+ `/` remap historically) | EVIDENCED | Content leads | BRAND | Content planner | WORKSPACE | Intelligence/Content or BU Standards | Prior | content-*.html brands | One Content workspace + brand context | Drop per-brand top Boards |
| `content.html`, `content-atrium.html`, `content-goss-group.html`, `content-habitat.html`, `content-selong-selo.html`, `content-tropik.html`, `content-uma-blu.html` | EVIDENCED names | Content | BRAND | Brand content boards | WORKSPACE | Content → brand | Content hub | content-2.0 | Merge into Content + brand switcher | Yes |
| `ggv-finance.html` | EVIDENCED name | Finance / Amanda | BU | GGV finance | DASHBOARD/MGMT | GGV → Finance | GGV | atrium-finance, money | Keep under GGV Finance | Yes |
| Client portal projection | UNKNOWN / future | CLIENT | CLIENT PROJECT | Client-safe view | DASHBOARD | Client landing | n/a | Must NOT inherit GGV nav | Separate audience shell | Never show internal Boards |

## D. Atrium / AMG

| Route / file | Live status | Who | Org level | Job | Page-type | How reached | How back | Overlaps | Merge? | Drop primary? |
|---|---|---|---|---|---|---|---|---|---|---|
| `atrium-sales.html` | SIBLING-PROD + access-config | Amanda / Scott / Owner | SITE/BU | Sales | WORKSPACE | Atrium → Customers/Sales | Atrium Overview | inventory, management | Cluster under Atrium | Prefer subnav |
| `atrium-inventory.html` | SIBLING-PROD | View allow list | SITE | Inventory RO | WORKSPACE | Atrium → Operations | Atrium | sales | Stay | Yes |
| `atrium-management.html` | SIBLING-PROD | atrium_allow | SITE | Management | MANAGEMENT | Atrium → Standards/Mgmt | Atrium | sales | Stay | Yes |
| `atrium-finance.html` | EVIDENCED (wave1-smoke Zayen) | Zayen / Finance | SITE/ENTITY | Finance desk | MANAGEMENT | Atrium → Finance OR Finance desk | Prior | ggv-finance, money | Finance grammar under entity | Yes |
| `legal.html` | SIBLING-PROD | Amanda/Scott/Owner | ENTITY+ | Legal | MANAGEMENT/DETAIL | System or entity Standards | Prior | contracts sensitive | Not primary Boards | Yes |
| AMG Coral ops boards | UNKNOWN dedicated | Coral / AMG ops | BU | Ops Today | WORKSPACE | BUSINESSES → Atrium/AMG | HOME | atrium-* | Need Mac inventory | UNKNOWN |

## E. Intelligence / System / Specialist

| Route / file | Live status | Who | Org level | Job | Page-type | How reached | How back | Overlaps | Merge? | Drop primary? |
|---|---|---|---|---|---|---|---|---|---|---|
| Intelligence hub | UNKNOWN path | Owner / authorised | GROUP | Intel / Decision Memory | DASHBOARD | INTELLIGENCE | HOME | wolf_intelligence WIP | One hub; inherit requester perms | Hide technical modules |
| Sale Readiness | UNKNOWN | Owner | SYSTEM | Sale readiness | SYSTEM | SYSTEM | SYSTEM | Progress | Panel under System | Yes for staff |
| Integrations | UNKNOWN | Owner / Admin | SYSTEM | Integration health | SYSTEM | SYSTEM | SYSTEM | factory | System only | Yes |
| Build Factory / System Health | UNKNOWN UI; state on Mac | Owner / eng | SYSTEM | Factory | SYSTEM | SYSTEM | SYSTEM | Progress | System only | Yes |
| Completion register UI | UNKNOWN | Owner | SYSTEM | Eng debt register | SYSTEM | SYSTEM / Progress | Progress | factory | Nested | Yes |
| `hr.html` | SIBLING-PROD | HR allow | DEPT | HR | MANAGEMENT | People (scoped) | Prior | payroll sensitive | Never global Boards for all | Scoped |
| Money / bank boards | SIBLING-PROD APIs | money_allow | ENTITY+ | Money | MANAGEMENT | Finance | Prior | atrium-finance | Scoped | Yes |
| `trading.html`, `travel.html`, `spartacus.html`, `mila.html`, `amanda.html`, `kuta-rates.html` | SIBLING-PROD names | Specialist / Owner | various | Specialist | WORKSPACE/DETAIL | Search / specialist | Prior | — | Keep capability; retire primary | **Yes** |
| `index.html` | SIBLING-PROD | Landing | GROUP | Hub | DASHBOARD | Root | — | Empire | Point role landings | — |

## F. Sprawl candidates (compressed sprint)

| Pattern | Live status | Notes |
|---|---|---|
| `*mgmt-cluster*` pages | **OWNER-CLAIMED / UNKNOWN on disk** | Likely MANAGEMENT page-type duplicates of BU Overview grammar — **merge into entity/BU Management + business grammar subnav** |
| `*operator-depth*` / `*opdepth*` | **OWNER-CLAIMED / UNKNOWN on disk** | Likely WORKSPACE depth under venue/BU — **nest under BU → Ops; retire top-level** |
| Duplicate Boards entries for every technical route | Standing problem | sidenav manifest lists flat "Dashboards" — violates Owner conceptual HOME/BUSINESSES/INTELLIGENCE/SYSTEM |

## G. How reached / how back (global rules for audit)
- **Reached:** `#wolfnav` Boards (today) · clean URL alias · deep link · Needs You card · search (future RBAC).  
- **Back:** Browser back is insufficient — shell must provide **org breadcrumb + explicit parent** (Empire ← BU ← Venue ← Object).  
- **Overlaps:** Empire vs Radar vs Progress; Uma Beta vs legacy `uma-blu.html`; content-2.0 vs content-{brand}; finance desks across entities.

## H. Mac verify checklist (before Cursor merge packs)
```bash
# On Wolfs-Mac-Studio — read-only
cd /Users/wolfterminal/beta-os
find dashboards -name '*.html' | sort
rg -n 'self.path = |path in \(' serve_beta.py | head -200
rg -n 'mgmt-cluster|operator-depth|opdepth' -g '*.html' -g '*.js' -g '*.py' | head -100
ls dashboards/assets/sidenav.js dashboards/data/manifest.json 2>/dev/null
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8788/progress
# Do NOT restart :8788 unless Owner pack allows; do NOT touch :8787
```

## I. Top findings
1. Flat **Dashboards** list in `#wolfnav` fights Owner IA (HOME / BUSINESSES / INTELLIGENCE / SYSTEM).  
2. Beta already has **good nested BZG/Uma aliases** — extend that pattern; don't invent parallel menus.  
3. Sprawl names `mgmt-cluster` / `operator-depth` need Mac find before delete; capability must redirect.  
4. Permissions: sidenav filters are **not** security — see Permissions Audience spec.  
5. Factory ACTIVE claims remain; this audit does not arm/kill packs.

## Permissions cross-ref
Normative audience/RBAC: `GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` — SHELL·API·DOMAIN must agree; Hidden menu ≠ permission.

## Mac live inventory (Peaches apply 2026-09-22 ~15:49 WITA)

- `dashboards/*.html` count: **77**
- `*mgmt-cluster*.html` present (**11**): amg, bzg, core, crm, dr, ggv, intel, intg, msc, sale, strat
- Also: `habitat-operator.html` (operator surface, not mgmt-cluster)
- No `*operator-depth*.html` filenames — opdepth is API/section under cluster pages (confirm in `serve_beta.py`)
- Docs applied from box mirror via CopyFromBox
