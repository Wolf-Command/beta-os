# Organisation Registry — Transitional Architecture

**Slice:** WOLF CORE — ORGANISATION REGISTRY  
**Scope:** `/Users/wolfterminal/beta-os/` only  
**Date:** 2026-09-16

## Status (DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE)

| Piece | Status |
| --- | --- |
| Schema (`org_entities`, `org_brands`, `org_locations`, `org_brand_locations`, `org_departments`) | **BUILT** |
| Canon seed (GGV/AMG/BZG + Brands_Locations Unit IDs) | **BUILT** |
| Repository `scripts/core/organisation.py` | **BUILT** |
| Read APIs `/api/core/...` | **BUILT** (TESTED via automated suite when serve up) |
| Admin UI | **NOT BUILT** |
| Person / Auth / RBAC | **NOT BUILT** (next slices) |
| LIVE for staff use | **NO** |

## Content Machine compatibility

Content Engine still owns:

- table `brands` (content planner brand keys, e.g. `habitat`)
- table `brand_external_ids` (Metricool blogIds)

Organisation Registry owns legal/operating structure in `org_*` tables.

**Adapter (transitional):**

- `brands.org_brand_id` nullable → links content brand to `org_brands.brand_id` when ownership is clear
- `brand_external_ids.org_brand_id` nullable → same

**Mapped this slice:**

- `umablu` → `BZG-UMA` (BZG-owned)
- `atrium` → `AMG-ATR` (AMG-owned)

**Explicitly NOT mapped (client brands — not GGV legal ownership):**

- `habitat`, `selo`, `tropik` → `org_brand_id` NULL

Do not treat GGV service relationship as ownership.

## Shared campus

`LOC-ATRIUM-LOMBOK` is stewarded by `ENT-AMG`.  
BZG venue brands link via `org_brand_locations` (Brand ↔ Location M:N).  
A brand has exactly one `entity_id` (legal owner).

## Migration

- SQL: `scripts/migrations/005_org_registry.sql`
- Runner: `scripts/migrations/migrate_org_registry.py` (idempotent)
- Recorded in `schema_migrations` id `005_org_registry`

## Forbidden

- Production / wolf-system paths
- Emails as organisation IDs
- Merging AMG+BZG because services are shared
