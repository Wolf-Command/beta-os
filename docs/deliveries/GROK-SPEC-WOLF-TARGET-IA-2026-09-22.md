# GROK SPEC — WOLF TARGET INFORMATION ARCHITECTURE
**Date:** 2026-09-22 ~15:50 WITA (Asia/Makassar UTC+8)  
**Status:** TARGET SPEC (Grok) — implement via migration order, not big-bang rewrite  
## Evidence / constraints
- Box-bound audit; live Mac Beta tree not opened. Specs are **TARGET** + evidenced current patterns — do not invent PROVEN/READY maturity.
- One chrome: `#wolfnav` / `sidenav.js`. Never second Boards menu.
- Production `:8787` sacred. Do not rewrite business logic in this doc pack.
- ACTIVE factory Cursor packs: **not killed**.

See also: `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` and RULE Permissions section.

## Canonical org hierarchy (always visible in context, never replaced by brand alone)
```
WOLF / GROUP
  → LEGAL ENTITY
    → SITE
      → BU / VENUE
        → DEPT / FUNCTION
          → WORKSPACE / LOOP
            → OBJECT / DETAIL
```
**Brand is contextual** (Uma Blu, Habitat, Selo, Tropik, Atrium). Brand chips decorate; they do **not** replace Entity / Site / BU in breadcrumb or scope.

## Owner conceptual primary nav (do NOT expose every technical route)

### 1. HOME
| Item | Purpose | Default page-type |
|------|---------|-------------------|
| Empire Pulse | Cross-group health / money / risk pulse | DASHBOARD |
| Needs You | Assignment-scoped action queue | WORKSPACE |
| Exceptions | Failures / SLA / integrity breaks | DASHBOARD |
| Priorities | Owner/exec priorities (Radar absorb) | DASHBOARD |

### 2. BUSINESSES
| Business | Entry Overview | Grammar (subnav) | Drill examples |
|----------|----------------|------------------|----------------|
| **GGV** | GGV Overview | Overview · Operations · People · Customers · Finance · Standards · Issues · Intelligence | Habitat client → project; Lead Spine under Customers/Ops |
| **Atrium / AMG** | Atrium/AMG Overview | same grammar | Inventory · Sales · Legal (scoped) · Coral ops Today |
| **Blu Zone / BZG** | BZG Overview | same grammar | **Uma Blu** venue → Today / Bills / Issues / Petty / Close |

Business grammar is **stable labels**; empty sections show honest EMPTY — never fake % or invent PROVEN.

### 3. INTELLIGENCE
| Item | Purpose |
|------|---------|
| Intelligence Home | Decision Memory / AKR entry — **inherits requester permissions** |
| Brand / Competitive (authorised) | Scoped intel — not a side door |
| Content (operator) | May live here **or** under BU Standards — pick one primary; other is alias |

### 4. SYSTEM (Owner / Admin primarily)
| Item | Purpose |
|------|---------|
| Progress | Owner build/sale progress |
| Integrations | Connector health |
| Sale Readiness | Exit / DD prep (separate export perms) |
| Build Factory / System Health | Factory state, claims, health |

Technical routes (completion register raw, WIP modules, mgmt-cluster debug) stay **out of primary nav**.

## Landing vs primary vs hidden
- **Landing:** role/assignment default (see Role-Nav Matrix + Permissions).  
- **Primary nav:** HOME / BUSINESSES / INTELLIGENCE / SYSTEM sections with **permission-filtered** children.  
- **Hidden:** specialist boards, legacy HTML, depth pages, System for non-admins — reachable via drill, search (RBAC), or bookmark **only if API allows**.

## Brand vs entity rule
- Wrong: top nav = Habitat | Uma | Selo as peer empires.  
- Right: BUSINESSES → GGV → (brand/client context) Habitat.  
- Wrong: Uma Blu replaces BZG in breadcrumb.  
- Right: `WOLF › Blu Zone › Uma Blu › Today`.

## Cross-links
- Page types → `GROK-SPEC-WOLF-PAGE-TYPES-2026-09-22.md`  
- Shell → `GROK-SPEC-WOLF-GLOBAL-SHELL-2026-09-22.md`  
- Merge plan → `GROK-PLAN-WOLF-ROUTE-MERGE-RETIRE-REDIRECT-2026-09-22.md`
