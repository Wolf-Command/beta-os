# BZG-RECIPE-MULTI-OUTLET-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-29 PICK HEADCHEF-1 + Owner order `BZG-RECIPE-MULTI-OUTLET-20261002`  
**Prod `:8787`:** READ-ONLY untouched · **Beta store:** `catalog/bzg_recipes.sqlite`  
**Flags:** `staff_ready=false` · `human_commissioned=false`

## Goal

One BZG Recipe Builder with **outlet context** (not seven apps). Haryanto can build Rainforest / multi-outlet menus on Beta after Peaches credit-light verify — not commissioned for mere outlet switching.

## What landed

### Single builder + visible outlet context
- Page `/bzg/recipe-builder` — prominent **Working outlet** selector (registry-driven)
- Default = OPEN Uma Blu, surfaced as defaulted — never silent wrong outlet
- **All BZG** = catalogue + assignments only (`not_merged_menu=true`)
- APIs: `/api/bzg/recipe-builder/context`, `recipes?outlet_id=`, `menu-items`, `ingredients`, `reporting`, `recipes/{id}/outlets`

### Registry-driven outlets
- Outlets from `org_outlet_registry` via `bzg_outlet_registry.list_outlets()` — no hardcoded seven strings
- Rainforest registry `display_name` remains **Rainforest** (Owner board name “Blu Zone Rainforest…” not overwritten)

### Preserve Uma Blu 127 / 756
- Live store after migrate: **127 recipes · 756 lines · 127 assigned to `BZG-UMA`**
- `brand_id=BZG-UMA` provenance kept — **not** relabelled all-BZG (`v1_import_relabelled_all_bzg=0`)

### Recipe associate without duplication
- `recipe_outlet_links` + `recipe_all_bzg` — one recipe row, multi/all associations
- Create requires explicit `outlet_id` / `outlet_ids` / `all_bzg` / legacy `brand_id` (no silent default brand)

### Menu ≠ recipe
- `outlet_menu_items` — shared recipe can have different menu name / portion / sell price per outlet
- All BZG menu list refused (not a fake merged menu)

### Shared ingredient master
- `ingredient_master` seeded from distinct line names (292 rows) — one master, not seven

### INCOMPLETE COST
- Missing purchase/card cost → **INCOMPLETE COST** (never silent zero)
- Reporting foundation refuses fake Rainforest FC / ESB theoretical / inventory variance when uncommissioned

### Permissions
- Head Chef `SCOPE-BZG-FB` + `recipe.*` server-side; finance/Owner/HR/AMG/GGV deny preserved
- Zayen Recipe Builder 403

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_recipe_multi_outlet_1.py` | **pass=85 fail=0** |
| `scripts/tests/test_headchef1_20260929.py` | **pass=92 fail=0** |

## Commissioning honesty

- `staff_ready=false` · `human_commissioned=false`
- Outlet switching alone is **not** human commissioning
- After Peaches credit-light verify: send Haryanto to real Beta for real Rainforest menu work — PASS or what blocked

## Files

- `scripts/core/recipe_builder.py`
- `dashboards/bzg-recipe-builder.html`
- `scripts/serve_beta.py` (context / menu / reporting / outlets routes)
- `scripts/tests/test_bzg_recipe_multi_outlet_1.py`
- `scripts/tests/test_headchef1_20260929.py` (INCOMPLETE COST + explicit outlet on HTTP create)
- `catalog/bzg_recipes.sqlite` (schema migrate + Uma links + ingredient master; recipe/line counts unchanged)

RESULT: **PASS** (engineering). Human commissioning PENDING.
