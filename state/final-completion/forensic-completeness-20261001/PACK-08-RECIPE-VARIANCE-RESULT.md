# Pack 8 — Recipe variance

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No yield was invented. ESB was not written. Prod `:8787` was health-checked and not restarted.

## Recipes that already have lines

Beta `catalog/bzg_recipes.sqlite`: 127 recipes, 756 lines, 127 with at least one line. The file mtime did not change.

V1 `uma-blu/recipes.sqlite` `recipe_compare` count is 0. There is no stored theoretical-versus-actual history.

## Product mix

Source: `esb.sqlite` `sales_menu_summary`, business date `2026-09-30`, branch `BLZ`, branch name UMA BLU. 76 menus, quantity sum 292. Amounts and tax were not copied onto this wire. The ESB file mtime did not change.

26 recipe names match that mix by the same normalised-name rule as the existing menu map. Ambiguous matches: 0. A sample theoretical quantity is sold quantity times the stored first-line quantity. That sample is labeled THEORETICAL. It is not a variance.

## Variance

UNKNOWN. Amount null. Quantity null.

`material_usage` for the same day and branch has 160 rows. Those rows are branch-day product totals. They were not joined to recipe lines. Subtracting a day total from a partial recipe explosion would invent a variance.

`venue_close_variance_policies` count is 0. Stored recipe yield was not used to rescale quantities.

## Pack 2

Close `VDC-25a3123a-3e26-43db-8085-10c6f208bbcd` is still `DATA_CAPTURED` for `2026-09-30`, venue `BZG-UMA`, ESB finished count 50, declared-cash evidence null. That close is not a recipe variance. The recipes desk href is `/bzg/uma-blu/recipes`.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/bzg/uma-blu/recipe-variance` | 200, variance UNKNOWN, amount null |
| `GET /uma/recipe-variance` | 200, three tiles, none start open |
| `POST /api/bzg/uma-blu/recipe-variance` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_uma_recipe_variance_pack8.py`: 13 passed, 0 failed.

## Left undone

A joined actual. A variance amount. A yield rescale. An ESB write. `recipe_compare` history. `staff_ready`.

## NEXT — Pack 9, not started

Pre-open outlets, config only: Pool Bar, Merah, Rooftop, Room Service, Catering, Blu Zone Restaurant. Registry rows and a blank close template. No fake sales. Resolve the Rainforest name against the standing Blu Zone name before any UI title ships. Pack 10 approvals was not started.
