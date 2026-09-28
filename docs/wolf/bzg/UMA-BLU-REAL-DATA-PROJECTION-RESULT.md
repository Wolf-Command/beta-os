# Uma Blu real-data projection

28 Sep 2026. Pack UMAREAL-1. Owner brief from Matthew Goss. Decision served: that brief, extending the 2026-09-20 CAP-BZG-06 pick (ESB read-only, no Alchemist writes, no production). BZGRECON-1 at commit `62b2f28` was reused. Discovery was not repeated from scratch. Counts below are from queries in this session.

`staff_ready` and `human_commissioned` stay false. Nothing here is commissioned.

Code commit `926cb78` at 21:57:16 +0800. Beta `:8788` pid 13943, started Mon Sep 28 21:57:30 2026, `scripts/serve_beta.py`. That start is after `926cb78`. The previous listener was pid 96450. Production `:8787` stayed pid 15975. Atrium sidecar `:8790` stayed pid 96416. Live Beta has `BETA_PORT=8788` and no `BETA_AUTH_MODE`. Auth mode was not switched. `GET /api/health` is 200. Unsigned `GET /bzg/uma-blu` and `/bzg/uma-blu/recipes` are 403.

## 1. REAL DATA NOW VISIBLE IN BETA

BZG seats only. GGV and Atrium Finance seats receive 403. The three example purchase requests stay in the catalog with `example=1` and are not in these views.

| Dataset | Count | Route |
| --- | --- | --- |
| Dishes | 127 | `/bzg/uma-blu/recipes` |
| Ingredient lines | 756 | `/bzg/uma-blu/recipes/<id>` |
| Suppliers | 103 | `/bzg/uma-blu/purchasing` |
| Purchase orders | 504 | `/bzg/uma-blu/purchasing` |
| Receipt lines | 452 | `/bzg/uma-blu/purchasing` |
| Local evidence jpgs | 450 | `/bzg/uma-blu/notas/<filename>` |
| ESB bills | 8,762 (2026-04-05 through 2026-09-27) | `/bzg/uma-blu/sales` |
| Menu map | 49 confirmed exact-name, 0 ambiguous, 139 ESB items with no recipe, 78 recipes with no ESB item | `/bzg/uma-blu/menu-map` |
| Theoretical consumption | labelled THEORETICAL; 27 Sep has 61 finished BLZ bills | `/bzg/uma-blu/menu-map` |
| Par levels | 9 | `/api/bzg/uma-blu/real/inventory` |
| Daily close history | NONE FOUND | `/bzg/uma-blu/sales` and `/uma-blu-close` |

Every projected row carries `source_system`, `source_id`, `source_timestamp`, `import_timestamp`, `verified_by_wolf=false`, and `origin=historical` (a Wolf draft uses `origin=wolf_draft` and does not update `recipes.sqlite`).

19 dishes are INCOMPLETE. A line without a usable cost is badged MISSING COST and the dish food cost is INCOMPLETE, not a number. 108 dishes have a complete food cost. A confirmed purchase match is an exact normalised name against Alchemist `pr_vendor_items.last_price`, with the unit converted only for g/ml or the same unit. A unit that does not convert stays `not_confirmed`. A price older than the latest order of that item is badged STALE with the cost date.

The cut line on the Uma Blu pages says the historical source stays authoritative and the Wolf commissioning date is not set. ESB stays authoritative for sales. Alchemist stays authoritative for purchasing.

Screenshots, Devi subject, ephemeral handler, `development_assertion` on that handler only:

- `docs/wolf/staff/shots/umareal-recipes-desktop.png`
- `docs/wolf/staff/shots/umareal-recipes-phone.png`
- `docs/wolf/staff/shots/umareal-recipe-detail-desktop.png`
- `docs/wolf/staff/shots/umareal-recipe-detail-phone.png`
- `docs/wolf/staff/shots/umareal-purchasing-desktop.png`
- `docs/wolf/staff/shots/umareal-purchasing-phone.png`
- `docs/wolf/staff/shots/umareal-nota-desktop.png`
- `docs/wolf/staff/shots/umareal-nota-phone.png`
- `docs/wolf/staff/shots/umareal-sales-desktop.png`
- `docs/wolf/staff/shots/umareal-sales-phone.png`
- `docs/wolf/staff/shots/umareal-menu-map-desktop.png`
- `docs/wolf/staff/shots/umareal-menu-map-phone.png`

The register is `docs/wolf/bzg/UMA-BLU-DATA-SOURCE-REGISTER.md` and `state/bzg/data-source-register.json`.

## 2. REMAINING TO PULL THROUGH

- 28 Sep ESB sales. The warehouse max `biz_date` is 2026-09-27. The inline log's latest OK line is still `daily(2026-09-27)` (last seen 2026-09-28 21:37 +0800, 61 bills, 94 covers). No new ESB call was made.
- 95 PO photo references are Drive ids. The file is not on disk. The page says EVIDENCE FILE NOT RECOVERABLE and shows the source path id.
- ESB stock-branch was not called. On-hand stock is not in this projection. `goods_receipts` is 0.
- `material_usage` is 18,637 rows (2026-06-01 through 2026-09-27). The count is in the register. The page shows theoretical consumption from bills times recipe lines, not that usage table.
- Alchemist `ledger` (420) and `petty_cash` (432) already have Beta read paths from the earlier projection. This pack did not rebuild them.
- Receipt `item_raw` is an unparsed nota line and `line_price` is a line total. It is shown as receipt evidence. It is not used as a confirmed unit cost.
- PO line `price` is null on all 1,830 rows. Purchase cost comes from vendor `last_price` (163 of 918 vendor items have a price).

## 3. CONFLICTS DISCOVERED

- Supplier name `bake house` is stored twice (`suppliers` 5 and 90).
- The notas directory has 450 jpg files: 2 named `nota_`, 373 `petty_`, 75 `topup_`. BZGRECON-1 counted 448 jpg. This session counted 450. Petty and top-up photos are in the same folder as the two nota files.
- `deliveries` is 0 and `delivery_lines` is 0 while 452 receipt lines and 450 photos exist. `ledger.delivery_id` does not join a delivery row.
- `item_prices` is 0 and `unit_map` is 0. `recipe_lines.subrecipe_id` is 0. `recipe_compare` is 0. `recipes.esb_menu` is empty on every dish, so there is no stored menu link. The 49 mapped dishes are exact normalised names only.
- 126 recipe lines have a null `cost_source` and a null `unit_cost`. Card costs exist on 628 lines. Two lines are `manual`.
- One recipe is `archived`. The other 126 are `live`.

## 4. CANNOT YET BE USED

- Wolf is not the authoritative recipe, purchasing, inventory, or sales system. `state/uma/cutover.json` still has `cutover_at` null. Matt sets the commissioning date.
- Daily close history: NONE FOUND. Searched live `venue_daily_closes` (0), `venue_close_variance_policies` (0), Alchemist `cash_count` (0), Alchemist `deliveries` (0), every `catalog/backups/pre-uma-blu-daily-close-*.sqlite` `venue_daily_closes` (0). `atrium-finance/atrium_finance.sqlite` `close_checklist_item` has rows and was not projected: it is hotel finance, not an Uma Blu close. No cash-variance threshold was inserted. Matt decides.
- A closer is not assigned. `POS-BZG-CLOSER-UMA-1` was already waiting on a roster in BZGRECON-1. This pack did not assign one.
- ESB stock on hand and ESB goods receipts. Stock-branch and core/staging were not called.
- Drive nota files, until the file is on disk under the notas directory or another authorised local path.
- Confirmed menu links beyond the 49 exact name matches. Near-matches were not marked confirmed.
- Subrecipes. The column exists and no line points at one.

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=85 fail=0 |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_bzg_recon_20260928.py` | 2 tests, OK |

## Pids

| Process | Pid | Started |
| --- | --- | --- |
| Production `serve.py` :8787 | 15975 | Mon Sep 21 16:59:38 2026 |
| Atrium sidecar :8790 | 96416 | Mon Sep 28 17:36:58 2026 |
| Beta `serve_beta.py` :8788 | 13943 | Mon Sep 28 21:57:30 2026 |

No push. No production write. No ESB write. No Alchemist write.

RESULT: PASS
