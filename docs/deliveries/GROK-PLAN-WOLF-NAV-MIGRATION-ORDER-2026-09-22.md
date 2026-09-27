# GROK PLAN — WOLF NAV MIGRATION ORDER
**Date:** 2026-09-22 ~15:50 WITA  
**Status:** ORDERED PLAN · keep working routes during migration  
## Constraints
- One `#wolfnav` / `sidenav.js` chrome owner — never second Boards menu.
- Extract/refactor tokens from existing `style.css` + sidenav CSS; do not restyle every page independently.
- Box-bound; Mac live not verified. ACTIVE factory packs not killed.
- Prod `:8787` sacred.

Permissions: `GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` + RULE Permissions.

## First Cursor pack (recommended scope)
**Shell + tokens only** — no BU business logic, no API rewrites, no factory kill.
- Extract `wolf-tokens.css` from `style.css` + sidenav CSS.  
- Evolve `sidenav.js` → IA sections (HOME/BUSINESSES/INTEL/SYSTEM) with **same hrefs**.  
- Add `data-wolf-page-type` / org attrs optional non-breaking.  
- Prove: Boards still one `#wolfnav`; phone toggle; whoami filter; no second menu.  
- Lane: Beta `:8788` only.

## Ordered waves

| Wave | Scope | Keep working | Exit prove |
|------|-------|--------------|------------|
| **1** | Global shell + tokens | All existing routes/aliases | Visual one-system chrome on 3 sample pages (Empire if present, Uma, Progress) |
| **2** | Owner / Empire HOME | `/wolf`, Needs You stub, Priorities absorb radar later | Owner landing = Empire; staff still blocked from Progress |
| **3** | BZG + Uma | `/bzg`, `/bzg/uma-blu*` , close | Devi landing Today; grammar subnav; legacy uma redirect |
| **4** | GGV | lead-spine, habitat-operator, content hub | Amanda landing GGV; client projection **not** yet unless perms pack |
| **5** | AMG / Atrium | atrium-* cluster under AMG Overview | Coral/Amanda scoped; finance nested |
| **6** | Intelligence | Intel hub + content home decision | Inherits requester perms; no side door |
| **7** | System / Progress / Integrations / Sale / Factory | Existing Progress etc. | Owner-only SYSTEM section; staff hidden |
| **8** | Remaining specialist | trading/travel/spartacus/… | Removed from primary; redirects ok |

## Parallel work (allowed)
- Permissions/catalog commissioning (Devi API gate) — **separate ACTIVE pack**; do not block Wave 1.  
- Mac inventory of mgmt-cluster/opdepth — feeds Wave 3–5 merge redirects.

## Guardrails
- No Production `:8787` mutation.  
- No `git add` of WIP quartet (`wolf_intelligence.py`, phase26, skills `__init__`).  
- Do not invent PROVEN/READY.  
- Do not kill ACTIVE factory packs — add new slices (`BF-wolf-shell-tokens-…`).  
- Each wave: clean URL aliases remain until wave+1 proves.

## Dependency
Wave N content migration assumes Wave 1 shell exists. Role landings (Wave 2+) need Permissions agreement (this doc pack) but can soft-land via whoami until catalog complete.
