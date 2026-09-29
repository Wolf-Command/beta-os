# CORE-BOOKS-1 RESULT — Open honest per-entity books slots (BZG + GGV)

**As of:** 2026-09-29 ~22:19 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `9e0da04` working tree) + atrium-finance `wolf/beta-mount-20260928`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` · Sidecar `:8790` restarted for books shells  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start BZG-XOUTLET-1 / V1-SWEEP / HEADCHEF**

## Owner addendum (locked)

After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: **do NOT chain another major feature pack**. Next = **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK. This EXIT does not auto-start XOUTLET.

## Decision / canon

Serves Matt-ordered Owner sprint CORE-BOOKS-1 (inventory `state/finance-core-sprint/INVENTORY-20260929.json`).  
RULE addendum: `docs/RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md`

**ONE FINANCE PRODUCT · THREE ENTITY CONFIGS · SHARED CODE ≠ SHARED DATA ≠ SHARED AUTHORITY.**

## Design choice (documented)

**Separate SQLite files per entity** under `~/atrium-finance/data/beta/` (preferred path — not single-DB column-only isolation):

| Legal entity | File | Shell |
| --- | --- | --- |
| ENT-AMG | `atrium.sqlite` | **Live** AMG books preserved (200 accounts, 7 journals incl. SoD COMM1) |
| ENT-BZG | `atrium-bzg.sqlite` | Empty shell (0 accounts, 0 journals) |
| ENT-GGV | `atrium-ggv.sqlite` | Empty shell (0 accounts, 0 journals) |

Shared code opens the correct file by `legal_entity_id` (`server/entityBooks.ts` + `scripts/core/entity_books.py`).  
AMG mount path unchanged (`DATABASE_FILE=…/atrium.sqlite`). No company data merged across files. No fake journals, sales, P&L, invoices, customers, or go-live numbers.

## What landed

### 1) Config slots — all three `books_enabled=true`
- `atrium-finance/server/entityConfig.ts` — AMG/BZG/GGV books on; `db_file` per slot; `books_isolation: separate_sqlite_files`
- Sidecar boot `ensureAllEntityBooks()` creates/stamps shells
- Unsigned loopback `GET :8790/api/health` includes `books_slots` + entity config (no money figures)

### 2) Authority stays separate
- Zayen: AMG+BZG allow; GGV HTTP **403** (not empty 200)
- Amanda: GGV only; BZG/AMG **403**
- Ext Accountant shells still **unseated**
- SoD COMM1 intact on AMG: `JRN-ATRIUMSOD1B-COMM1` POSTED / `preparer_person_id=PERS-ZENITALFATHAN` / `wolf_created=1`
- `outlet_id` / `operating_unit_id` nullable on journal lines (all three files)

### 3) Thin Beta surfaces
- `/amg/finance` (lite) — AMG books live honesty
- `/bzg/finance` — BZG books shell (`books_opened`, empty OK, stamps `staff_ready=false`)
- `/ggv/finance` (Amanda) — GGV books shell stamp on overview
- No READY banners

## Tests (honest)

| Suite | Result |
| --- | --- |
| `test_core_books1_20260929.py` | **pass=64 fail=0** |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |
| `test_bzg_outlet1_20260929.py` | **PASS=82 FAIL=0** |
| `test_atrium_sod1_20260929.py` | **pass=69 fail=0** |
| `test_staff_access_20260928.py` | **pass=275 fail=0** |

Isolation probe: write token into BZG only → absent from AMG + GGV files.

## Shots

Under `docs/wolf/ops/shots/` (8/8, distinct allow/deny pairs):
- `corebooks1-amg-books-live-{desktop,phone}.png`
- `corebooks1-bzg-books-shell-{desktop,phone}.png`
- `corebooks1-ggv-books-shell-{desktop,phone}.png` (Amanda)
- `corebooks1-cross-entity-deny-{desktop,phone}.png` (Zayen→GGV)

## Migration / files

- `scripts/migrations/migrate_core_books1_20260929.py`
- `scripts/core/entity_books.py`
- `scripts/core/bzg_finance_desk.py` + `dashboards/bzg-finance.html`
- `scripts/core/ggv_finance_nota.py` + `dashboards/ggv-finance.html` (books shell stamp)
- atrium: `entityConfig.ts`, `entityBooks.ts`, `entityIsolation.ts`, `db` open path, `server.ts`, `betaMount.ts`, `routeAccess.ts`
- Stamp: `state/finance-core-sprint/CORE-BOOKS-1-ARM.json`

## Out of scope (not started from this EXIT)

- BZG-XOUTLET-1 / V1-SWEEP-1 (next map — Peaches arms after verify)
- HEADCHEF / random breadth
- Prod / push / CF / inventing people / flipping staff_ready / human_commissioned
