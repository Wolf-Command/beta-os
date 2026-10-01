# Wave 2.04 — Menu engineering

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No margin and no menu class were written. Prod `:8787` was health-checked and not restarted. ESB was not written.

## Recipes are a copy

Source: `catalog/bzg_recipes.sqlite`, opened read-only. 127 recipes, 756 lines, 127 with at least one line. The file mtime did not change.

Line cost is stored, not scored. 108 recipes have a cost on every line. 2 are partial. 17 have no line cost. Lines with a positive `unit_cost`: 628. Lines with a zero cost: 0. Lines with a null cost: 128. Cost source `card` 628, `manual` 2, missing 126.

`target_cos` is filled on 127 rows. `real_sell` is filled on 107. `esb_menu` links are 0. Those columns are stored fields. They were not turned into a score.

V1 `uma-blu/recipes.sqlite` `recipe_compare` count is 0. No stored engineering history.

## Product mix

Source: `esb.sqlite` `sales_menu_summary`, business date `2026-09-30`, branch `BLZ`, branch name UMA BLU. 76 menus, quantity sum 292. Amounts were not copied. This quantity mix is not a popularity class. The ESB file mtime did not change.

Name join uses the same normalised-name rule as Pack 8. Matched recipes 26. Ambiguous 0. Of the matches, 23 have complete line cost and 3 do not. Unmatched menus 50.

## Usage and contribution

`material_usage` for `2026-09-30` and branch `BLZ` has 160 rows. `joined` is false. Those rows are branch-day totals. They are not a plate cost.

Contribution state UNAVAILABLE. `margin_pct` null. `amount` null. A margin from stored line cost and a mix amount would invent a score while usage is unjoined.

## Classes

`quadrants.drawn` is false. Stars, plowhorses, puzzles, and dogs are null. No class was assigned.

Pack 8 variance stays UNKNOWN. This desk does not replace it.

## HTTP

Verified 2026-10-01T22:10:31+08:00 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/bzg/uma-blu/menu-engineering` | 200, contribution UNAVAILABLE, margin null, classes unassigned |
| `GET /uma/menu-engineering` | 200, four tiles, none start open |
| `POST /api/bzg/uma-blu/menu-engineering` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_menu_engineering_wave2_04.py`: 14 passed, 0 failed.

## Left undone

A joined plate cost. A contribution margin. A popularity class. Star, plowhorse, puzzle, and dog counts. `staff_ready`.

## NEXT — Wave 2.05, not started

Content learn-back, register row `need.content.learn`. Not started.
