# UX-PACK-09b APPLY — Pulse deepen (+ UX-PACK-11 cheap)
**Status:** PACK_09b_APPLIED · 2026-09-30T22:39:35+08:00 (WITA)
**Bound:** Beta :8788 only · Prod :8787 READ-ONLY untouched
**finance_sod_unchanged:** true · **staff_ready:** false · **desktop_gate_ready:** false

## Tile counts
| | tiles | LIVE | PARTIAL | EMPTY | BLOCKED |
|--|--:|--:|--:|--:|--:|
| before (09) | 7 | 1 | 5 | 0 | 1 |
| after (09b) | 7 | 2 | 3 | 1 | 1 |

## Tile snapshot (after)
- **BLOCKED** `atrium_occ` — Atrium occupancy: `None` → /amg/occ-truth-1
  - PMS blocked → occupancy UNKNOWN (not zero, not invented). Blocker: INT-YAN-WOLF / CAP-AMG-01 external. WHERE: /amg/occ-truth-1 · /amg/occupancy-external-hold-1.
- **LIVE** `kuta_rates` — Kuta rates tonight: `from 1,050,000 IDR · Raja Hotel Kuta Mandalika` → /kuta-rates
  - Tonight competitor signal (2026-09-30 → 2026-10-01) · cheapest official 1,050,000 IDR · Deluxe King — not labeled studio. Headline: Raja Deluxe King BB IDR 1.050.000 · cheaper than 2jt. Official 20 · sold_out 25. LEARN o
- **EMPTY** `bzg_night` — BZG / Uma last-night: `no close filed` → /bzg/uma-blu#closes
  - No close filed — No previous closes recorded in Wolf yet. Night revenue/covers not on record (not invented). File/review at /bzg/uma-blu#closes or Close desk /uma-blu-close. Uma Today attention 308 · blocked 1 is ops noi
- **PARTIAL** `leads` — Leads (GGV / Habitat): `0 live Habitat · 8 DEMO fixture · 3 needs-you` → /ggv-ops-pack
  - No non-DEMO Habitat/GGV lead SoT found. Board rows are DEMO/fixture seed (8 fixture-tagged). live_pipeline=False. Not claiming live sales pipeline. WHERE: /ggv-ops-pack.
- **PARTIAL** `purchasing` — Purchasing / Alchemist: `unpaid 106 · unpaid sum 195,268,172 · awaiting Devi 39 · received 166` → /bzg/uma-blu/purchasing
  - Alchemist attention summary (RO). Legacy projection — PARTIAL, not greenwashed. Unpaid fields are real counts from SoT. Not a finance settle action. SoD unchanged.
- **LIVE** `fitness` — Fitness / Spartacus day: `day 1 · plan 0/3 · workouts open` → /owner/fitness
  - From /api/owner/fitness-ro (Spartacus sqlite RO). Fitness ≠ HR.
- **PARTIAL** `backup` — Backup / pipe health: `backup PRESENT · atrium snap STALE · drill DRILL_RAN_NON_DESTRUCTIVE · pipe ORIGIN_REACHABLE/AMBER` → /ops/backup-health-1
  - From BACKUP-HEALTH-1 + external_route_health latest. Atrium snapshot STALE — not inventing fresh backup. Pipe AMBER (CF Access / unauth probe). Last backup ≠ restore proven. staff_ready false.

## UX-PACK-11 (cheap)
- Travel + Learning unhidden in PERSONAL IA (sidenav + wolf_shell)
- Owner Home Personal Command cards + RO glances (`/api/owner/travel-ro`, `/api/owner/learning-ro`)
- Desks remain PARTIAL (no book / TTC paper only)
- Habitat Investment stays hidden

## Files
- `scripts/core/owner_pulse_ro.py`
- `dashboards/owner-empire-pack.html`
- `dashboards/assets/sidenav.js`
- `scripts/core/wolf_shell.py`
- `dashboards/owner-travel-1.html` / `owner-learning-1.html` (crumbs)

## Backup
`/Users/wolfterminal/beta-os/backups/ux-pack-09b-20260930-223458`

## Residuals
- Occ BLOCKED (Yanolja) · Uma no close filed · GGV DEMO fixture · Alchemist legacy · Backup STALE/AMBER
- Screenshots BLOCKED_AUTH until Owner CF

## Next
- UX-PACK-10 authenticated screenshot pass (BLOCKED until Owner CF — do not fake)

## Matt
Pulse deepen (09b) landed on Beta: Kuta rates tonight is now LIVE from the morning competitor status (from IDR 1,050,000 Raja Deluxe King for 30 Sep–1 Oct) instead of a far-future Atrium stay scrape; Uma last-night is honest EMPTY — no close filed — with links to /bzg/uma-blu#closes and the Close desk; leads demoted to 0 live Habitat / 8 DEMO fixture; Atrium occ stays BLOCKED with clearer Yanolja blocker + WHERE. Also cheap Pack-11: Travel + Learning unhidden under PERSONAL with Owner Home RO glances (PARTIAL, no book / TTC paper only). Counts moved LIVE 1→2, PARTIAL 5→3, EMPTY 0→1, BLOCKED 1. Prod :8787 untouched; finance SoD unchanged; staff_ready false; desktop_gate_ready still false until your Owner CF session for screenshots and more real SoT.
