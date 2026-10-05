# HARYANTO-UX — Recipe Builder human-test repair

**Status:** REPAIR COMPLETE (Beta filesystem + catalog registry; Beta listener reload pending)

**Date:** 2026-10-04

## Summary

Head Chef Recipe Builder UX repair: Rainforest and Pool Bar registry OPEN, honest empty outlet menus, ingredient type-ahead combobox, navigation that never sends Head Chef to `/bzg/uma-blu`, and plain-language recipe costing on the detail card.

## Files changed

| File | Change |
|------|--------|
| `scripts/core/bzg_outlet_registry.py` | Seed: `BZG-RAIN` + `OU-BZG-RAIN-POOL` → OPEN |
| `catalog/content_library.sqlite` | Live `org_outlet_registry` status only for Rainforest + Pool Bar |
| `scripts/core/recipe_builder.py` | `ingredient_id` on new lines; `search_ingredients`; outlet truth messages; duplicate-line guard |
| `scripts/serve_beta.py` | `?q=` ingredient search on GET ingredients |
| `scripts/core/wolf_shell.py` | `HEAD_CHEF` audience (no uma-blu); registry-driven outlet strip; recipe-builder crumbs/up |
| `dashboards/bzg-recipe-builder.html` | Ingredient combobox, nav stack/back, chef summary card |
| `scripts/tests/test_haryanto_ux_20261004.py` | New proofs (temp sqlite) |

## Tests

```
PYTHONPATH=scripts python3 scripts/tests/test_haryanto_ux_20261004.py
SUMMARY  pass=35  fail=0
```

Did **not** run `scripts/tests/test_petty_cash_record_out_20261004.py`. Did **not** modify the live almond-milk recipe.

## Outlet statuses after change

| outlet_id | display_name | status |
|-----------|--------------|--------|
| BZG-UMA | Uma Blu | OPEN |
| BZG-RAIN | Rainforest | OPEN |
| OU-BZG-RAIN-POOL | Pool Bar | OPEN |
| BZG-MERAH | Merah | PRE-OPENING |
| BZG-ROOF | Rooftop | PRE-OPENING |
| BZG-RS | Room Service | PRE-OPENING |
| BZG-CAT | Catering | PRE-OPENING |

## Rainforest / Pool Bar menu source

**NOT FOUND** — authorised search covered:

- `catalog/bzg_recipes.sqlite` (0 `outlet_menu_items`; 0 `recipe_outlet_links` for BZG-RAIN / OU-BZG-RAIN-POOL)
- `~/.openclaw/workspace/wolf-system/uma-blu/recipes.sqlite` + `recipes-export.json` (Uma Blu only; no BZG-RAIN)
- `beta-os/library_v2/EDIT/rainforest_EDIT_image_opening-menu_*` (marketing images only — not structured menu rows)

UI shows honest empty state: *"Wolf has no menu items and no recipes for Rainforest yet."*

## RELOAD_REQUIRED

**yes** — `recipe_builder.py`, `wolf_shell.py`, and `serve_beta.py` changed. Peaches must reload Beta listener (pid 76967 on 127.0.0.1:8788). HTML is served from disk and is already live on refresh.

## Prod / protected close

- **Prod pid 15975** on `127.0.0.1:8787` — **not touched** (verified listening).
- **Protected close** `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` — **not written** (`EXCEPTION`, cash `3225000`, variance `-125000`, `updated_at` `2026-10-03T13:47:39Z` unchanged).

## Head Chef nav

- `ROLE-BZG-HEAD-CHEF` → audience `HEAD_CHEF` (pages: Needs You, `/bzg`, `/bzg/recipe-builder`, `/bzg/outlets` — **no** `/bzg/uma-blu`).
- `venue.close.read` still **denied** for Head Chef fixture.
- Outlet strip rewrites any legacy uma-blu href to `/bzg/recipe-builder?outlet_id=…` for Head Chef; strip contains no uma-blu link.
