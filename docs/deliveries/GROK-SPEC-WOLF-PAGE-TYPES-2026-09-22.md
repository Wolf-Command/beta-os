# GROK SPEC — WOLF PAGE-TYPE STANDARD
**Date:** 2026-09-22 ~15:50 WITA (Asia/Makassar UTC+8)  
**Status:** TARGET STANDARD  
## Evidence / constraints
- Box-bound audit; live Mac Beta tree not opened. Specs are **TARGET** + evidenced current patterns — do not invent PROVEN/READY maturity.
- One chrome: `#wolfnav` / `sidenav.js`. Never second Boards menu.
- Production `:8787` sacred. Do not rewrite business logic in this doc pack.
- ACTIVE factory Cursor packs: **not killed**.

See also: `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` and RULE Permissions section.

Every user-facing HTML/route declares **one** page-type. Shell chrome adapts; content templates share tokens.

| Type | Job | Typical org level | Chrome | Subnav | Examples (current/target) |
|------|-----|-------------------|--------|--------|---------------------------|
| **DASHBOARD** | Situational awareness; KPIs; links out | GROUP → BU | Full global shell | Optional section pills | Empire Pulse, BZG Overview, GGV Overview |
| **WORKSPACE** | Do the day's work; queues; loops | VENUE / DEPT / BRAND | Full shell + strong Needs You | **Business grammar** or loop tabs | Uma Today, Habitat operator, Lead Spine, Content |
| **DETAIL** | Single object deep view | OBJECT | Shell + breadcrumb emphasis | Object tabs | Bill detail, person, lead, asset |
| **MANAGEMENT** | Configure standards, rosters, policies | ENTITY → DEPT | Full shell; quieter pulse | Standards/People/Finance mgmt | atrium-management, HR admin, finance desks |
| **SYSTEM** | Platform health, factory, sale, integrations | SYSTEM | Full shell; Owner-weighted | System items only | Progress, Integrations, Factory |

## Rules
1. **One type per route.** Don't ship a MANAGEMENT page labeled as DASHBOARD in nav.  
2. Depth pages (`operator-depth`, object detail) are WORKSPACE or DETAIL — **not** new primary Boards entries.  
3. `mgmt-cluster` sprawl → MANAGEMENT under the owning BU/Entity Overview — not top-level.  
4. Client projections may **look** like DASHBOARD but use **Client Mode** permission + stripped shell (see Permissions).  
5. Summary tiles on DASHBOARD may omit DETAIL fields; drill requires `CAN SEE DETAIL` (payroll, labour, campaign spend examples in Permissions spec).  
6. Unmigrated routes = **design-system debt** (RULE).

## Declaration (target)
```html
<body data-wolf-page-type="WORKSPACE" data-wolf-org="BZG/UMA" data-wolf-shell="global">
```
Shell reads attributes; factory gate rejects new pages missing them (register gate).
