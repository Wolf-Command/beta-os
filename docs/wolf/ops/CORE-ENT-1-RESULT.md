# CORE-ENT-1 RESULT — Wolf Finance Core: entity isolation + access

**As of:** 2026-09-29 ~21:20 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os) + atrium-finance `wolf/beta-mount-20260928`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` · Sidecar `:8790` restarted for schema  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push**

## Owner addendum (locked)

After Finance Core + BZG multi-outlet + non-HR V1 retirement finishes: **do NOT chain another major feature pack**. Next = **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK. This EXIT does not propose follow-on feature packs.

## Decision / canon

Serves Matt-ordered Owner sprint Finance Core (inventory `state/finance-core-sprint/INVENTORY-20260929.json`).  
RULE registered: `docs/RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md`

**ONE FINANCE PRODUCT · THREE ENTITY CONFIGS · SHARED CODE ≠ SHARED DATA ≠ SHARED AUTHORITY.**

### Canonical legal entities (AMG ↔ Atrium alias)

| Legal entity | `legal_entity_id` | Alias / note |
| --- | --- | --- |
| AMG | `ENT-AMG` | **Atrium** hotel books |
| BZG | `ENT-BZG` | Blu Zone Group |
| GGV | `ENT-GGV` | GGV |

## Design choice (smallest honest)

- **Column scoping** on the existing Beta sidecar DB (`data/beta/atrium.sqlite`): additive `legal_entity_id TEXT NOT NULL DEFAULT 'ENT-AMG'` on money/COA/journal/GL/config tables; backfills existing AMG rows in one step.
- **Not** three product forks and **not** three merged company stores. Sidecar `entityConfig.ts` exposes three config slots; only `ENT-AMG` has `books_enabled=true` on this mount.
- Pool Bar: measurable operating unit `OU-BZG-RAIN-POOL` under parent brand `BZG-RAIN` (no second `brand_id`). Hook doc: `state/finance-core-sprint/BZG-OPERATING-UNITS.json`. Nullable `journal_lines.operating_unit_id`. Deep outlet registry = sibling pack.

## What landed

### 1) Sidecar entity isolation
- `atrium-finance/server/entityConfig.ts` — three entity configs; AMG books on; BZG/GGV config slots without books.
- `atrium-finance/server/entityIsolation.ts` + `db.ts` open hook — additive `legal_entity_id` + Pool Bar registry hook.
- Python migrate also applied columns to live Beta atrium.sqlite (33 tables + OU registry).

### 2) AMG SoD preserved (ATRIUM-SOD-1C)
- `ASG-ZAYEN-FC-1`, `ASG-ZAYEN-AR-1`, `ASG-ZENITALFATHAN-AP-1` ACTIVE.
- Finance Officer vacant.
- SoD still person-based (`preparer_person_id` ≠ actor). Suite `test_atrium_sod1_20260929.py` **pass=69 fail=0**.

### 3) Zayen BZG Financial Controller (Owner-authorized)
| Object | Id |
| --- | --- |
| Role | `ROLE-BZG-FINANCIAL-CONTROLLER` |
| Position | `POS-BZG-FINANCIAL-CONTROLLER-1` @ `ENT-BZG` |
| Scope | `SCOPE-BZG-FINANCE` → `ENT-BZG` |
| Assignment | `ASG-ZAYEN-BZG-FC-1` ACTIVE (secondary; AMG FC stays primary) |

Proved:
- `finance_entities(Zayen)` = AMG + BZG (no GGV)
- `rbac.can` AMG+BZG board allow; GGV nota/board **deny**
- HTTP `/bzg/finance` **200**; `/ggv/finance` + `/api/ggv/finance/notas` **403** (not empty 200)
- Nav pages include `/amg/finance` + `/bzg/finance`; hide `/ggv/finance`
- Finance-only wall updated so AMG+BZG seats still cannot open `/amg-ops-pack` / Owner / Uma ops

### 4) External / Tax Accountant shells (unseated)
| Entity | Role | Position | Scope |
| --- | --- | --- | --- |
| AMG | `ROLE-AMG-EXTERNAL-ACCOUNTANT` | `POS-AMG-EXT-ACCT` | `SCOPE-AMG-FINANCE` |
| BZG | `ROLE-BZG-EXTERNAL-ACCOUNTANT` | `POS-BZG-EXT-ACCT` | `SCOPE-BZG-FINANCE` |
| GGV | `ROLE-GGV-EXTERNAL-ACCOUNTANT` (existing) | `POS-GGV-EXT-ACCT` | `SCOPE-GGV-FINANCE` |

ALLOW: nota/invoice read/review, evidence export, vendor read (entity-scoped).  
DENY: `payment.execute` / `payment.approve` / `vendor.bank.change` / Owner/admin / Controller approve-post.  
**No invented people. No ACTIVE accountant seats.**

### 5) Thin BZG Finance entry
- `dashboards/bzg-finance.html` + `scripts/core/bzg_finance_desk.py` + `serve_beta` dispatch.
- Honest empty OK — books not opened for BZG on this pack.

## Tests (honest)

| Suite | Result |
| --- | --- |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |
| `test_atrium_sod1_20260929.py` | **pass=69 fail=0** |
| `test_humfix1c_20260929.py` | **pass=54 fail=0** |
| `test_mywork1b_20260929.py` | **pass=53 fail=0** (earlier this session) |
| `test_humancomm1_20260929.py` | **PASS=60 FAIL=0** (earlier this session) |
| `test_staff_access_20260928.py` | **pass=275 fail=0** (expectations updated for Owner-authorized BZG FC) |

## Shots

Under `docs/wolf/ops/shots/`:
- `coreent1-zayen-amg-finance-{desktop,phone}.png`
- `coreent1-zayen-bzg-finance-{desktop,phone}.png`
- `coreent1-zayen-ggv-deny-{desktop,phone}.png`

## Migration / files

- `scripts/migrations/migrate_core_ent1_20260929.py`
- Catalog backup: `catalog/backups/pre-core-ent1-20260929-210939.sqlite`
- RULE: `docs/RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md`

## Out of scope (sibling packs — not started from this EXIT)

- BZG multi-outlet registry depth
- V1 retirement sweep execution
- Human commissioning / CF / Gmail
- Prod deploy / push / `staff_ready` / `human_commissioned`
- Inventing External Accountant people
- Chaining another major feature pack
