# GROK PLAN — WOLF ROUTE MERGE / RETIRE / REDIRECT
**Date:** 2026-09-22 ~15:50 WITA  
**Status:** PLAN · preserve capability when removing top-level routes  
## Constraints
- One `#wolfnav` / `sidenav.js` chrome owner — never second Boards menu.
- Extract/refactor tokens from existing `style.css` + sidenav CSS; do not restyle every page independently.
- Box-bound; Mac live not verified. ACTIVE factory packs not killed.
- Prod `:8787` sacred.

Permissions: `GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` + RULE Permissions.

## Principles
1. **Redirect > delete** until prove pack green on Beta `:8788`.  
2. Preserve capability under Target IA parent (BU grammar / System).  
3. Never leave staff with bookmark 404 without alias.  
4. Mac `find` for `mgmt-cluster` / `operator-depth` **before** mass retire.  
5. Do not kill ACTIVE factory packs; schedule merge work as new slices.

## Top 10 merge / retire candidates

| # | Candidate | Action | Preserve via | Primary nav |
|---|-----------|--------|--------------|-------------|
| 1 | Flat sidenav "Dashboards" dump of all HTML | **Restructure** to HOME/BUSINESSES/INTEL/SYSTEM | Same hrefs, new grouping | Keep links; change structure |
| 2 | `*mgmt-cluster*` pages (OWNER-CLAIMED) | **Merge** into Entity/BU MANAGEMENT Overview | `/{biz}` → Management grammar | Drop top-level |
| 3 | `*operator-depth*` / `*opdepth*` | **Nest** under BU/Venue WORKSPACE | Parent Ops URL + redirect | Drop top-level |
| 4 | Legacy `uma-blu.html` (prod-style) | **Redirect** → `/bzg/uma-blu` | Beta Uma + APIs | Drop |
| 5 | Per-brand `content-*.html` top Boards | **Merge** → Content workspace + brand context | content-2.0 + switcher | Drop brand peers |
| 6 | `radar.html` standalone | **Merge** → HOME Priorities / Empire | Empire panels | Drop |
| 7 | Duplicate `/dashboards/foo.html` vs `/foo` | **Canonical clean URL**; old path rewrite | existing serve_beta aliases | Prefer clean |
| 8 | Specialist: trading/travel/spartacus/mila/amanda/kuta-rates | **Retire from primary**; keep route | Search / System tools / Owner | Drop primary |
| 9 | Progress/Factory/Integrations/Sale as peer Boards | **Move** under SYSTEM section | Same routes | Hidden for non-Owner |
| 10 | Parallel "Boards" menus if any page forks sidenav | **Delete fork**; one sidenav.js | — | Enforce |

## Redirect table (initial)

| From | To | Until |
|------|----|-------|
| `/uma-blu.html`, `/uma-blu` | `/bzg/uma-blu` | legacy bookmarks die |
| `/dashboards/bzg-uma-blu*.html` | `/bzg/uma-blu…` | already partially aliased |
| `/dashboards/habitat-operator.html` | `/habitat-operator` | done pattern |
| `/dashboards/lead-spine.html` | `/lead-spine` | done pattern |
| `/content-habitat.html` etc. | `/content-2.0?brand=…` (or successor) | after Content pack |
| `/radar.html` | `/wolf#priorities` (or `/home/priorities`) | after Empire pack |
| `/mgmt-cluster/…` (when found) | owning BU MANAGEMENT path | after Mac inventory |
| `/operator-depth/…` (when found) | owning WORKSPACE path | after Mac inventory |

## Capability preservation checklist
- [ ] Alias in `serve_beta.py`  
- [ ] Manifest/IA entry points to parent  
- [ ] Needs You cards updated  
- [ ] API unchanged (no business logic rewrite)  
- [ ] Prove script: old URL → 302/200 to new; API still auth-correct  
- [ ] completion_register / factory claim note if slice exists  

## Out of scope this plan
- Production `:8787` redirects  
- Killing ACTIVE Cursor packs  
- Inventing PROVEN maturity
