# TRANSFER-TRAVEL-SPEC — Beta Owner Travel (P0)

Generated: 2026-09-30T11:04:38+08:00 (WITA)  
Owner: **Matthew only** · Executor: Peaches  
Constraint: **NO live booking** · no spend · no hotel mail · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report

## Purpose

Restore Owner Travel as a first-class Beta Owner surface so it is **not** Wave-8 soft-redirect retired into Empire. Preserve V1 provenance. Migration stays **PARTIAL** until human prove.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/travel.html` | Draft board; "Nobody books from here." |
| Manifest | `dashboards/data/manifest.json` | name=travel |
| Party | Matthew + Amanda · 2 adults + kids 5 and 7 | Banner on V1 |
| Planner | Peaches on-board tiles (Europe etc.) | Draft suggestions; Google Flights links only |
| Beta Wave-8 | soft-redirect `/travel` → `/wolf` | **reversed** this pack → `/owner/travel` |

## Beta target (Owner-only)

| Item | Value |
|------|-------|
| Canonical route | `/owner/travel` |
| HTML | `~/beta-os/dashboards/owner-travel-1.html` |
| Legacy aliases | `/travel`, `/travel.html`, `/dashboards/travel.html` → `/owner/travel` (not Empire) |
| IA | HOME "Travel (Owner)" key=`owner_travel` |
| Audience | Owner / Matthew only |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| live booking | **FORBIDDEN** |

## Transfer steps

1. Un-retire `travel` from Wave-8 `SPECIALIST_PRIMARY_*` + `SPECIALIST_SOFT_REDIRECT_PATHS` + sidenav `HIDDEN_SPECIALIST_PRIMARY`.
2. Ship `owner-travel-1.html` with honesty strip (PARTIAL · no book · provenance).
3. Route legacy travel URLs → `/owner/travel` via DASHBOARDS_HTML_CANONICAL / route_merge.
4. IA HOME item + crumbs + parent under Empire.
5. Human prove: Matthew opens `/owner/travel`; confirms no Empire soft-redirect.

## Non-goals

- Live booking APIs, payment, hotel mail, spend
- Staff Travel desk
- Claiming REBUILT+PROVEN or staff_ready
- Breadth dump of other MISSING caps

## Honesty / provenance

- V1 `travel.html` remains authoritative until Beta prove.
- Wave-8 "hidden ≠ deleted" history retained; Owner surface is the re-entry.
