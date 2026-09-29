# BZG-XOUTLET-1 RESULT — Cross-outlet foundations for BZG

**As of:** 2026-09-29 ~22:29 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `dec78f2` working tree) + atrium-finance `wolf/beta-mount-20260928` @ `21325be` (+ local entityIsolation hooks)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` · Sidecar `:8790`  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start V1-SWEEP-1 / HEADCHEF**

## Owner addendum (locked)

After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: **do NOT chain another major feature pack**. Next = **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK.  
**This Cursor EXIT does not auto-start V1-SWEEP-1** (Peaches/parent arms next per Matt auto-continue).

## Decision / canon

Serves Matt-ordered Owner sprint BZG-XOUTLET-1 (inventory `state/finance-core-sprint/INVENTORY-20260929.json` §D; after CORE-BOOKS-1 PASS_VERIFIED).  
**Matt-ordered sprint overrides breadth veto / credit conservation for this pack.**

Hierarchy: **LEGAL ENTITY (`ENT-BZG`) → OUTLET → cost_centre_id / revenue_centre_id (nullable hooks)** — now usable across outlets for shared foundations only (not fake P&L).

## What landed

### 1) Cross-outlet shared foundations
- `bzg_shared_vendors` — entity-scoped vendors; `outlet_id` nullable (null = entity-shared). **Empty OK** — no invented suppliers.
- `bzg_ops_purchase_requests.outlet_id` (+ centre hooks) — nullable; example rows with `venue=BZG-UMA` backfilled to `outlet_id=BZG-UMA` (identity copy only).
- `venue_daily_closes.outlet_id` (+ centre hooks) — nullable; **0 closes** (honest empty).
- Books: `journal_lines.outlet_id` already present (CORE-BOOKS-1); additive `outlet_id` on `inventory_purchase_orders` / receipts / requisitions / `ap_payments` across AMG/BZG/GGV Beta files.
- Cost/revenue centre IDs remain **null hooks** — not populated; no allocations invented.

### 2) Statuses + authority preserved
| Outlet | Status |
| --- | --- |
| Uma Blu (`BZG-UMA`) | **OPEN** |
| Rainforest (`BZG-RAIN`) | **PRE-OPENING** |
| Pool Bar (`OU-BZG-RAIN-POOL`) | **PRE-OPENING** under `BZG-RAIN` |
| Merah / Roof / RS / CAT | **PRE-OPENING** future |

- `SCOPE-BZG-FB` still entity `ENT-BZG` (no brand hardcodes); `SCOPE-BZG-UMA` brand-only spirit.
- Zayen AMG+BZG allow; GGV deny; Amanda GGV-only; BZG outlets/finance 403 for Amanda.
- No invented people. Ext Acct unseated. BZG books shell still empty (0 journals / 0 accounts).

### 3) Thin Beta surface
- `/bzg/outlets` + `/api/bzg/outlets/overview` — registry **plus** Cross-outlet foundations panel (hooks + nullable `outlet_id`; honest empty OK).
- `/api/bzg/outlets/foundations` — foundations-only JSON.
- No READY claim. `staff_ready=false` · `human_commissioned=false`.

## Tests (honest)

| Suite | Result |
| --- | --- |
| `test_bzg_xoutlet1_20260929.py` | **PASS=89 FAIL=0** |
| `test_bzg_outlet1_20260929.py` | **PASS=82 FAIL=0** |
| `test_core_books1_20260929.py` | **pass=64 fail=0** |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |

## Shots

Under `docs/wolf/ops/shots/` (8/8, distinct allow/deny pairs):
- `bzgxoutlet1-foundations-{desktop,phone}.png` — cross-outlet foundations panel
- `bzgxoutlet1-uma-open-{desktop,phone}.png` — Uma OPEN still
- `bzgxoutlet1-rain-pool-{desktop,phone}.png` — Rainforest + Pool Bar PRE-OPENING
- `bzgxoutlet1-amanda-deny-{desktop,phone}.png` — Amanda 403

## Migration / files

- `scripts/migrations/migrate_bzg_xoutlet1_20260929.py`
- Catalog backup: `catalog/backups/pre-bzg-xoutlet1-20260929-222714.sqlite`
- Core: `scripts/core/bzg_xoutlet_foundations.py` · outlets overview panel in `bzg_outlet_registry.py`
- UI: `dashboards/bzg-outlets.html`
- Doc: `state/finance-core-sprint/BZG-XOUTLET-FOUNDATIONS.json`
- Stamp: `state/finance-core-sprint/BZG-XOUTLET-1-ARM.json`
- Atrium: `server/entityIsolation.ts` (`ensureCrossOutletFoundationHooks`)
- Shots: `scripts/audit/bzgxoutlet1_shots.py`

## Out of scope (not started from this EXIT)

- **V1-SWEEP-1** (next map — Peaches/parent arms after verify; Cursor must not auto-chain)
- HEADCHEF / random breadth
- Fake multi-outlet P&L / sales / costs / covers / allocations / go-live money
- Prod / push / inventing people / flipping `staff_ready` / `human_commissioned`
- Chaining another major feature pack after Finance Core + BZG multi-outlet + V1 retirement
