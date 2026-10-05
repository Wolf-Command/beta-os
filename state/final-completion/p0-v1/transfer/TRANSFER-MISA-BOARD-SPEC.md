# TRANSFER-MISA-BOARD-SPEC — Beta Content Admin seat (P0)

Generated: 2026-09-30T11:12:13+08:00 (WITA)  
Owner oversight: **Matthew** · Executor: Peaches  
Constraint: **People ≠ Roles** · wire via ROLE/Assignment · no post / no spend · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report · skip Ads Studio / pipelines / HR

## Purpose

Restore the V1 **Misa Board** (Content Creator Administration Assistant due-list desk) as a reachable Beta **seat** surface with PARTIAL honesty. Desk may keep the historical seat name in labels; authorization is **ROLE → Assignment**, never `PERS-MISA` as permission model.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `~/.openclaw/workspace/wolf-system/dashboards/misa.html` | Daily / Weekly / Monthly / As needed / Escalations |
| JS | `dashboards/assets/mila-desk.js` (data-desk=mila) | Tick-after-work-in-live-apps pattern |
| SOP | `dashboards/sops/misa.html` · SOP-MISA-001 | Printable; owner Amanda historically |
| Role truth | RULE People-Are-Not-Roles | Misa seated on ROLE-CONTENT-CREW — use role, not person |

## Beta target (seat + Owner-reachable)

| Item | Value |
|------|-------|
| Canonical route | `/seats/content-admin` |
| HTML | `~/beta-os/dashboards/seat-content-admin-1.html` |
| Historical aliases | `/misa`, `/misa.html`, `/dashboards/misa.html` → `/seats/content-admin` |
| IA | INTELLIGENCE "Content Admin (seat)" key=`seat_content_admin` |
| Authz | ROLE-CONTENT-CREW · ROLE-CONTENT-MGMT · ROLE-CONTENT* → SPECIALIST_CONTENT; Owner oversight |
| Forbidden | `PERS-MISA` / person-name ACL; post / boost / spend / create accounts from board |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| APIs | **not wired** this pass — honesty stamp + static provenance only |

## Transfer steps

1. Ship `seat-content-admin-1.html` honesty strip (PARTIAL · no post/spend · V1 SoT · People≠Roles).
2. Alias historical `/misa*` URLs → `/seats/content-admin`.
3. IA INTELLIGENCE item + crumbs; SPECIALIST_CONTENT audience pages include seat route.
4. Do **not** re-wire mila-desk tick APIs or invent spend paths.
5. Human prove: Matthew opens `/seats/content-admin` + `/misa`; confirms PARTIAL; not REBUILT+PROVEN.

## Non-goals

- Full due-list cockpit rebuild / tick persistence
- Money, posting, Metricool mutate, Canva mutate from Beta
- Merging into Amanda / Mila Wave-8 soft-redirects
- Claiming REBUILT+PROVEN or staff_ready

## Honesty / provenance

- V1 `misa.html` remains SoT for admin due-list UX until Beta prove + optional read-only mirror.
- Historical PERS-MISA→SPECIALIST_AMG fixture coupling is succession debt — this pack wires the **board** via Content Crew / Content roles, not AMG ops pack.
