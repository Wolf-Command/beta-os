# BZG-OUTLET-1 RESULT — Canonical BZG Outlet Registry + hierarchy scopes

**As of:** 2026-09-29 ~21:40 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os) + atrium-finance OU status update  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` · Sidecar `:8790`  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push**

## Owner addendum (locked)

After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: **do NOT chain another major feature pack**. Next = **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK. This EXIT does not propose follow-on feature packs outside the Owner sprint map (CORE-BOOKS / XOUTLET / V1-SWEEP remain later map packs — not started here).

## Decision / canon

Serves Matt-ordered Owner sprint Finance Core / BZG multi-outlet (inventory `state/finance-core-sprint/INVENTORY-20260929.json` §D; sibling of CORE-ENT-1).  
**Matt-ordered sprint overrides breadth veto / credit conservation for this pack.**

Hierarchy: **LEGAL ENTITY (`ENT-BZG`) → OUTLET (brand / operating unit) → cost_centre_id / revenue_centre_id (nullable hooks).**

## Status choices (PRE-OPENING vs COMMISSIONING)

| Outlet | Status | Rationale |
| --- | --- | --- |
| Uma Blu (`BZG-UMA`) | **OPEN** | Primary operating outlet; brand LIVE |
| Rainforest (`BZG-RAIN`) | **PRE-OPENING** | Target ~7 Oct; **no human F&B commissioning evidence** for this outlet (content brand lists ≠ outlet commissioning). Prefer PRE-OPENING over COMMISSIONING |
| Pool Bar (`OU-BZG-RAIN-POOL`) | **PRE-OPENING** | Under `BZG-RAIN`; not a second `brand_id`; no human confirm |
| Merah / Rooftop / Room Service / Catering | **PRE-OPENING** | Future config rows (APPROVED/SPECIFIED brands); not OPEN; no fake ops |

## What landed

### 1) Canonical registry
- Catalog table `org_outlet_registry` (7 rows) — statuses only from `{OPEN, PRE-OPENING, COMMISSIONING, TEMPORARILY CLOSED, CLOSED}`
- Mirror doc: `state/finance-core-sprint/BZG-OUTLET-REGISTRY.json`
- Thin Beta surface: `/bzg/outlets` + `/api/bzg/outlets/overview` (`dashboards/bzg-outlets.html`, `scripts/core/bzg_outlet_registry.py`)
- No invented sales / costs / covers / P&L / go-live numbers; cost/revenue centre IDs left **null**

### 2) Hierarchy hooks for Finance Core / future books
- Pool Bar remains `OU-BZG-RAIN-POOL` under parent outlet/brand `BZG-RAIN`
- Sidecar: `operating_unit_registry` status **HOOK → PRE-OPENING**; additive nullable `journal_lines.outlet_id` (alongside existing `operating_unit_id`)
- Updated `state/finance-core-sprint/BZG-OPERATING-UNITS.json` (pack `BZG-OUTLET-1`, supersedes CORE-ENT-1 HOOK)

### 3) Hariyanto / Devi scopes via hierarchy
- `SCOPE-BZG-FB` stays **entity `ENT-BZG`** (no brand name list in grants) — expands to brands + outlet registry rows
- `SCOPE-BZG-UMA` stays **brand `BZG-UMA`** — covers Uma outlet only (not Rainforest / Pool Bar)
- `resolve_effective_scope_context` now lists `outlets` + `operating_units` from registry under entity/brand targets
- `outlets_for_person()` resolves membership via active scopes → hierarchy (used by registry read gate)
- Finance wall allowlist: Zayen (AMG+BZG FC) may open `/bzg/outlets` (same pattern as `/bzg/finance`); Uma ops / Owner / GGV still denied for finance-only seats
- No new people. No finance seating. No HEADCHEF feature depth.

### 4) Regression preserved
- Zayen BZG FC / AMG SoD / GGV isolation untouched
- Devi / Hariyanto assignments remain ACTIVE and coherent

## Tests (honest)

| Suite | Result |
| --- | --- |
| `test_bzg_outlet1_20260929.py` | **pass=82 fail=0** |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |
| `test_staff_access_20260928.py` | **pass=275 fail=0** |

## Shots

Under `docs/wolf/ops/shots/`:
- `bzgoutlet1-registry-{desktop,phone}.png` — full list (Owner)
- `bzgoutlet1-uma-open-{desktop,phone}.png` — Uma OPEN visible (Hariyanto)
- `bzgoutlet1-rain-pool-{desktop,phone}.png` — Rainforest + Pool Bar PRE-OPENING
- `bzgoutlet1-amanda-deny-{desktop,phone}.png` — Amanda 403 (not on assignment)

## Migration / files

- `scripts/migrations/migrate_bzg_outlet1_20260929.py`
- Catalog backup: `catalog/backups/pre-bzg-outlet1-20260929-213536.sqlite`
- Core: `scripts/core/bzg_outlet_registry.py` · scope outlet expansion in `scripts/core/scope.py`
- Serve + shell: `serve_beta.py`, `wolf_shell.py` (BZG grammar Outlets), `staff_access.py` wall allowlist
- Sidecar TS: `atrium-finance/server/entityIsolation.ts` (PRE-OPENING + `outlet_id`)

## Out of scope (not started from this EXIT)

- CORE-BOOKS / XOUTLET / V1-SWEEP (later map packs)
- HEADCHEF recipe builder depth / random breadth
- Prod / push / CF / Gmail / inventing people / fake ops / money movement
- Flipping `staff_ready` / `human_commissioned`
- Chaining another major feature pack after Finance Core + BZG multi-outlet + V1 retirement
