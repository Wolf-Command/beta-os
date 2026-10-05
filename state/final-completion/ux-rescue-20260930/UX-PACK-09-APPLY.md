# UX-PACK-09 APPLY — Owner Home live pulse
**Status:** PACK_09_APPLIED · 2026-09-30T22:30:24+08:00 (WITA)
**Bound:** Beta :8788 only · Prod :8787 READ-ONLY untouched
**finance_sod_unchanged:** true · **staff_ready:** false · **desktop_gate_ready:** false

## What landed
- Dense **Pulse** strip on `/owner-empire-pack` (alias `/wolf`)
- New RO API `GET /api/owner/pulse-ro` aggregating existing SoT loaders
- Tile contract: WHAT · number/state · WHERE · honesty (LIVE / PARTIAL / EMPTY / BLOCKED)
- Preserved FINISH WOLF hero, My Work, Needs You, Personal Command, packs 01–08

## URLs
- Owner Home: https://beta.wolfcommand.net/owner-empire-pack
- Local API: http://127.0.0.1:8788/api/owner/pulse-ro
- Backup: `/Users/wolfterminal/beta-os/backups/ux-pack-09-20260930-222559`

## Files
- `dashboards/owner-empire-pack.html`
- `scripts/core/owner_pulse_ro.py` (new)
- `scripts/serve_beta.py` (route + import)

## RO test (local)
- pulse-ro HTTP 200 · counts `{"tiles": 7, "LIVE": 1, "PARTIAL": 5, "EMPTY": 0, "BLOCKED": 1}`
- fitness-ro 200 · kuta-rates-ro 200
- Owner Home page without CF JWT: 403 expected
- Prod :8787 still listening

### Tile snapshot
- **BLOCKED** `atrium_occ` — Atrium occupancy: `None` → /amg/occ-truth-1
  - PMS blocked → occupancy UNKNOWN (not zero, not invented).
- **PARTIAL** `kuta_rates` — Kuta rates tonight: `1,978,000 IDR` → /kuta-rates
  - Atrium scrape 2026-09-30 · stay 2027-09-30 · Signature Studio. Competitor rates may be EMPTY. LEARN only — no booking.
- **PARTIAL** `bzg_night` — BZG / Uma last-night: `closes EMPTY · today attention 308 · blocked 1` → /bzg/uma-blu
  - No previous closes recorded in Wolf yet Night revenue/covers not on record. Showing Uma Today attention only — not inventing last-night sales.
- **PARTIAL** `leads` — Leads (GGV): `8 on board · 8 DEMO-labeled · 3 needs-you` → /ggv-ops-pack
  - GGV ops pack rows are DEMO-labeled. Not claiming live Habitat pipeline.
- **PARTIAL** `purchasing` — Purchasing / Alchemist: `unpaid 106 · unpaid sum 195,268,172 · awaiting Devi 39 · received 166` → /bzg/uma-blu/purchasing
  - Alchemist attention summary (RO). Legacy projection — PARTIAL. Not a finance settle action. SoD unchanged.
- **LIVE** `fitness` — Fitness / Spartacus day: `day 1 · plan 0/3 · workouts open` → /owner/fitness
  - From /api/owner/fitness-ro (Spartacus sqlite RO). Fitness ≠ HR.
- **PARTIAL** `backup` — Backup / pipe health: `backup PRESENT · atrium snap STALE · drill DRILL_RAN_NON_DESTRUCTIVE · pipe ORIGIN_REACHABLE/AMBER` → /ops/backup-health-1
  - From BACKUP-HEALTH-1 + external_route_health latest. Last backup ≠ restore proven. staff_ready false.

## Residuals
- Occ BLOCKED (PMS) · Uma closes EMPTY · GGV DEMO leads · Kuta stay may be far-future · Alchemist legacy · Backup STALE/AMBER
- Screenshots BLOCKED_AUTH until Owner CF

## Next packs
- UX-PACK-10 authenticated screenshot pass (BLOCKED until Owner CF — do not fake screenshots)
- Optional UX-PACK-11 Travel RO / Learning RO if cheap after pulse

## Matt
Owner Home now has a dense Pulse strip (after FINISH WOLF / My Work / Needs You, before Personal Command) fed by /api/owner/pulse-ro — seven glance tiles with WHAT · value/state · Open link · LIVE/PARTIAL/EMPTY/BLOCKED stamps. Right now: Fitness LIVE from Spartacus RO; Kuta rate + BZG Uma Today attention + GGV DEMO leads + Alchemist unpaid + backup/pipe are PARTIAL with reasons; Atrium occupancy stays BLOCKED (PMS) — no invented percent; Uma last-night closes remain EMPTY so we do not invent revenue/covers. Prod :8787 untouched; finance SoD unchanged; staff_ready stays false. Desktop gate is still NOT ready — need your Owner CF session for screenshots and a few more real SoT feeds before it feels like the V1 evening brief.
