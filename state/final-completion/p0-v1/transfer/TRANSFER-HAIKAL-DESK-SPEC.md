# TRANSFER-HAIKAL-DESK-SPEC — Beta Content Desk seat (P0)

Generated: 2026-09-30T11:12:13+08:00 (WITA)  
Owner oversight: **Matthew** · Executor: Peaches  
Constraint: **People ≠ Roles** · wire via ROLE/Assignment · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report · skip Ads Studio / pipelines / HR

## Purpose

Restore the V1 **Haikal Desk** (Content hub) as a reachable Beta **seat** surface with PARTIAL honesty. Desk may keep the historical seat name in labels; authorization is **ROLE → Assignment**, never `PERS-HAIKAL` / email as permission model.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Hub | `~/.openclaw/workspace/wolf-system/dashboards/haikal.html` | Content hub · brand doors · Atlas · Training · nobody posts |
| Desk alias | `dashboards/haikal-desk.html` | Earlier static Content desk + Metricool glance bake |
| SOP | `dashboards/sops/haikal.html` | Printable SOP |
| Role truth | RULE People-Are-Not-Roles 2026-09-24 | Creative Director / Content roles — not person ACL |

## Beta target (seat + Owner-reachable)

| Item | Value |
|------|-------|
| Canonical route | `/seats/content-desk` |
| HTML | `~/beta-os/dashboards/seat-content-desk-1.html` |
| Historical aliases | `/haikal`, `/haikal.html`, `/haikal-desk`, `/haikal-desk.html`, `/dashboards/haikal.html`, `/dashboards/haikal-desk.html` → `/seats/content-desk` |
| Live CE (do not collide) | `/content-2.0` remains Content Engine seat landing (`haikal_landing_content`) |
| IA | INTELLIGENCE "Content Desk (seat)" key=`seat_content_desk` |
| Authz | ROLE-GGV-CREATIVE-DIRECTOR · ROLE-CONTENT · ROLE-CONTENT-MGMT · ROLE-CONTENT-CREW · ROLE-CONTENT-CREATOR → SPECIALIST_CONTENT; Owner oversight |
| Forbidden | `PERS-HAIKAL` / email hardcode as permission gate |
| migration_state | **PARTIAL** |
| staff_ready | **false** |

## Transfer steps

1. Ship `seat-content-desk-1.html` honesty strip (PARTIAL · People≠Roles · V1 SoT · link to live `/content-2.0`).
2. Alias historical `/haikal*` URLs → `/seats/content-desk` (not Empire soft-redirect).
3. IA INTELLIGENCE item + crumbs under Intelligence → Content; SPECIALIST_CONTENT audience pages include seat route.
4. Do **not** invent a second Content Engine or stub that replaces `/content-2.0`.
5. Human prove: Matthew opens `/seats/content-desk` + `/haikal`; confirms PARTIAL stamp + Content link; not REBUILT+PROVEN.

## Non-goals

- Rebuilding full content-hub.js / brand doors / Metricool glance on this stamp
- Person-named ROLE-HAIKAL or PERS-HAIKAL ACL
- Ads Studio / pipelines / HR
- Claiming REBUILT+PROVEN or staff_ready

## Honesty / provenance

- V1 `haikal.html` remains SoT for hub UX until parity prove against `/content-2.0`.
- Live Content Engine stays at `/content-2.0`; this pack is transfer stamp + route restore only.
