# GROK SPEC — WOLF DESIGN-SYSTEM COMPONENT MAP
**Date:** 2026-09-22 ~15:50 WITA  
**Status:** EXTRACT / REFACTOR map — not a full visual redesign  
## Constraints
- One `#wolfnav` / `sidenav.js` chrome owner — never second Boards menu.
- Extract/refactor tokens from existing `style.css` + sidenav CSS; do not restyle every page independently.
- Box-bound; Mac live not verified. ACTIVE factory packs not killed.
- Prod `:8787` sacred.

Permissions: `GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` + RULE Permissions.

## Goal
One system feel across Empire, BZG/Uma, GGV, AMG, Intelligence, System — by **shared tokens + components**, not per-page restyles.

## Token sources (extract first)
| Source | Evidence | Action |
|--------|----------|--------|
| `dashboards/style.css` `:root` | `--bg --panel --panel-2 --border --text --muted --petrol --gold --accent --ok --warn --bad --stale --shadow --radius` | Promote to `wolf-tokens.css` |
| `sidenav.js` inline CSS | `--nav-w`, nav colors matching tokens | Move to shared CSS; JS only behavior |
| Page-local hex | UNKNOWN sprawl on Beta HTML | Ban new hex; use tokens |

## Component inventory (build / extract)

### Shell
- `WolfNav` (#wolfnav) — IA sections + filter  
- `OrgContextSwitcher`  
- `Breadcrumbs` (`.crumbs` exists)  
- `TopContextBar` (title, badges, Needs You, identity)  
- `SubnavGrammar`  
- `PhoneNavToggle` (#wolfnav-t)  
- `SearchBox` (RBAC-aware)

### Content primitives
- `Kpi` / `KpiRow` (`.kpi`, `.kpis`)  
- `Panel` / `Grid` (`.panel`, `.grid`, `.cols-*`)  
- `JobCard` / `Daemon` status  
- `Pill` / `Badge` (live, stub, stale, ok/warn/bad)  
- `EmptyState` (honest EMPTY)  
- `BrandChip` (contextual — not hierarchy)  
- `DataTable` / list (extract common)  
- `TileChevron` (collapsed-by-default standing)  
- `NeedsYouCard`

### Patterns
- DASHBOARD layout template  
- WORKSPACE loop template  
- DETAIL object template  
- MANAGEMENT form/roster template  
- SYSTEM health template  
- Client projection template (stripped)

## Refactor rules
1. New UI in Cursor packs **must** import tokens + shell — factory register gate.  
2. No second Boards menu; no page-local sidenav clone.  
3. Prefer wrapping existing HTML with shared classes over rewrite.  
4. Do not invent charts/% that claim PROVEN.  
5. Dark petrol+gold is the brand; light client mode may invert tokens under named theme — still same components.

## Debt register
Unmigrated routes that ship custom chrome/colors = **design-system debt** (RULE). Track in completion_register domain `UI-SHELL` when Mac store available (count UNKNOWN this run).
