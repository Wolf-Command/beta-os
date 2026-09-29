# RULE — One Finance Product · Three Entity Configs (2026-09-29)

**Owner lock:** Matthew Goss · **Governor:** Peaches · **Pack:** CORE-ENT-1  
**Surface:** Beta Wolf Finance Core (`:8788`) + Atrium sidecar (`:8790`) · **Production `:8787` sacred — do not mutate**

## Canon (exact)

**ONE FINANCE PRODUCT · THREE ENTITY CONFIGS · SHARED CODE ≠ SHARED DATA ≠ SHARED AUTHORITY.**

| Legal entity | Canonical id | Alias / note |
| --- | --- | --- |
| AMG | `ENT-AMG` | **Atrium** hotel books (AMG ↔ Atrium alias) |
| BZG | `ENT-BZG` | Blu Zone Group |
| GGV | `ENT-GGV` | GGV |

## Non-negotiables

1. **One product.** Shared Finance Core code serves all three entities. Do not fork three finance apps.
2. **Three configs.** Each entity has its own config slot (COA / bank / tax / branding / workflows / scope). Slots may be present before books are opened.
3. **Shared code ≠ shared data.** Never merge company records, COA, journals, or GL stores across entities. Every money/config/journal/GL row carries `legal_entity_id` (org registry id).
4. **Shared code ≠ shared authority.** Assignments and scopes are entity-scoped. A seat on AMG does not grant BZG or GGV. Prove deny with `rbac.can` false + HTTP **403** (not empty 200).
5. **Additive schema only.** Nullable → backfill existing Beta AMG rows to `ENT-AMG` → NOT NULL when safe. No prod schema writes from this rule's packs without explicit Owner order.
6. **SoD stays person-based.** Approver/poster ≠ preparer (`preparer_person_id` vs actor). Never SoD by role set alone (ATRIUM-SOD-1C).
7. **External / Tax Accountant** = role + position + scope + assignment **shell**. Default DENY payment/bank/Owner/admin/Controller approve-post. ALLOW read/review evidence, notas/invoices/reports within scoped entity only. Do not invent people; prefer unseated positions.
8. **Pool Bar** is a measurable BZG operating unit under Rainforest (`BZG-RAIN`) — e.g. `OU-BZG-RAIN-POOL`. Do not invent a second `brand_id` that fights Rainforest ownership. Deep outlet registry is a sibling pack.
9. **Exit discipline.** After Finance Core + BZG multi-outlet + non-HR V1 retirement finish: next is **Rebuild Completion & Exit Report** only. Bug fixes + human commissioning OK. Do not chain another major feature pack from that EXIT.
10. Never flip `staff_ready` / `human_commissioned` from engineering alone. Never touch Production `:8787`.

## Related

- Inventory: `state/finance-core-sprint/INVENTORY-20260929.json`
- RESULT: `docs/wolf/ops/CORE-ENT-1-RESULT.md`
- CORE-BOOKS-1 RESULT: `docs/wolf/ops/CORE-BOOKS-1-RESULT.md`
- Operating units hook: `state/finance-core-sprint/BZG-OPERATING-UNITS.json`
- Sidecar: `atrium-finance/server/entityConfig.ts`, `entityIsolation.ts`, `entityBooks.ts`

## Addendum — CORE-BOOKS-1 (2026-09-29)

**Books isolation = separate SQLite files per entity** under `atrium-finance/data/beta/`:

| Entity | File | Shell |
| --- | --- | --- |
| ENT-AMG | `atrium.sqlite` | Live AMG books (preserved) |
| ENT-BZG | `atrium-bzg.sqlite` | Empty/minimal shell |
| ENT-GGV | `atrium-ggv.sqlite` | Empty/minimal shell |

Shared code opens the correct file by `legal_entity_id`. Do not merge company data across files. `books_enabled=true` for all three config slots on the Beta mount. Empty shells carry schema + SoD columns (`preparer_person_id`) + nullable `outlet_id` / `operating_unit_id` — **no** fake journals, sales, P&L, invoices, customers, or go-live numbers. Authority stays separate (Zayen AMG+BZG / Amanda GGV only).
