# Uma Blu data source register

Pack UMAREAL-1. Generated 2026-09-29T11:35:10+08:00. Counts are live queries from this run.
Wolf commissioning date is null on every domain. `verified_by_wolf` stays false. `staff_ready` and `human_commissioned` stay false.

## Cut lines

| Domain | Historical source | Wolf commissioning date | Wolf authoritative going forward |
| --- | --- | --- | --- |
| recipes | wolf-system uma-blu/recipes.sqlite | null | not commissioned — historical recipe store stays the record |
| suppliers | Alchemist suppliers | null | external stays authoritative (Alchemist) |
| purchasing/PO | Alchemist pr_orders | null | external stays authoritative (Alchemist) |
| receiving | Alchemist pr_receipt_lines | null | external stays authoritative (Alchemist) |
| notas/evidence | Alchemist notas directory and PO photo refs | null | external stays authoritative (Alchemist files) |
| inventory | Alchemist par_levels; ESB material_usage is usage history | null | external stays authoritative (ESB for stock; stock-branch not called) |
| sales | ESB warehouse esb.sqlite sales | null | external stays authoritative (ESB) |
| daily close | NONE FOUND | null | not commissioned — venue close module exists, no historical rows |
| costs | recipe card unit_cost plus Alchemist vendor last_price | null | not commissioned — card and Alchemist prices stay the record |
| menu mapping | no stored recipe-to-ESB map (recipes.esb_menu empty) | null | not commissioned — exact name match is a report, not a confirmed map unless 1:1 |

## Datasets

| SOURCE | WHAT IT CONTAINS | DATE RANGE | RECORD COUNT | ROLE | READ ACCESS VERIFIED | SAFE TO PROJECT | TRANSFORMATION | CONFLICTS | PROVENANCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| wolf-system/uma-blu/recipes.sqlite recipes | Uma Blu dishes | 2026-08-25T12:26:40+08:00 .. 2026-09-12T09:59:41+08:00 | 127 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | read-through; costing badges; no rewrite | 1 archived dish; esb_menu column empty on every row | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| wolf-system/uma-blu/recipes.sqlite recipe_lines | ingredient lines | 2026-08-25T12:26:40+08:00 .. 2026-09-12T09:59:41+08:00 | 756 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | unit conversion g/ml only; missing unit_cost stays MISSING COST | null unit_cost 128; subrecipe_id 0; cost_source null 126 | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| wolf-system/uma-blu/recipes.sqlite recipe_compare | stored actual-versus-target rows | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none — empty | empty; margin is calculated at read time, not stored here | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db suppliers | supplier names | n/a — no created_at column | 103 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | read-through, label Alchemist historical | contact column not projected; location_id null on part of the table | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db pr_orders | purchase orders | 2026-07-27 .. 2026-09-29 | 514 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | read-through; example Beta PRs are not included | 98 rows point at a Drive photo that is not a local file | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db pr_order_lines | PO lines | 2026-07-27 .. 2026-09-29 | 1883 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | names used for stale-price dates only | price column is null on every row | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db pr_receipt_lines | receipt lines | no date column; parent PO dates apply | 466 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | shown as receipt evidence; not used as a confirmed unit cost | item_raw is an unparsed nota line; line_price is a line total; 30 rows have null line_price | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db pr_vendor_items | vendor item last price | last_seen on the row | 924 | REFERENCE | y — sqlite mode=ro query_only | y | exact normalised name match only | last_price empty on 755 rows | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist/notas jpg files | local evidence photos | file mtime | 451 | HISTORICAL | y — directory listing, files opened only by exact filename under the notas directory | y | serve the file if it resolves; otherwise EVIDENCE FILE NOT RECOVERABLE | prefixes {'nota': 2, 'petty': 373, 'topup': 76}; earlier note said 448 jpg; this query counted 451 | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db pr_orders receipt_photo_url | Drive photo references | 2026-07-27 .. 2026-09-29 | 98 | HISTORICAL | y — sqlite mode=ro query_only | y | source path id only; file not fetched | not on local disk | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db ledger | supplier bills | 2026-08-02 .. 2026-09-29 | 435 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | counted; bill page already reads Alchemist via the existing projection | deliveries table is 0 so ledger.delivery_id does not join a delivery row | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db petty_cash | petty movements | 2026-01-09 .. 2026-09-28 | 433 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | existing Beta petty projection | none found in this count | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db par_levels | par quantities | n/a | 9 | REFERENCE | y — sqlite mode=ro query_only | y | shown as par, not on-hand | no on-hand column | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db cash_count | cash counts | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none — empty | empty | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db unit_map | unit conversions | n/a | 0 | REFERENCE | y — sqlite mode=ro query_only | n | none — empty; g/ml map is code | empty | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db item_prices | item price history | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none — empty | empty; prices live on pr_vendor_items.last_price | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| alchemist.db deliveries | structured deliveries | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none — empty | empty while receipt lines and photos exist | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite sales | ESB bills | 2026-04-05 .. 2026-09-28 | 8823 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | read-through; customer phone, email, and member fields are not projected | warehouse max biz_date is 2026-09-27; inline log latest OK day is the same; no new ESB call | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite menus | ESB menu master | 2026-07-20T05:31:35.853208+08:00 .. 2026-09-28T05:32:29.052153+08:00 | 188 | AUTHORITATIVE | y — sqlite mode=ro query_only | y | exact normalised name match to recipes | recipes.esb_menu is empty, so there is no stored confirmed link | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite products | ESB products | pulled_at on the row | 426 | REFERENCE | y — sqlite mode=ro query_only | y | count only in this pack | goods_receipts is 0 so product price is not a receipt price | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite material_usage | ESB material usage | 2026-06-01 .. 2026-09-28 | 18790 | REFERENCE | y — sqlite mode=ro query_only | y | count only; theoretical consumption is calculated from sales x recipe lines | not a stock-on-hand figure | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite goods_receipts | ESB goods receipts | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none — empty | empty; Felix 19 Jul said goods receipt is ERP-only | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite gl_journal | ESB journal | 2026-04-01 .. 2026-09-28 | 5937 | REFERENCE | y — sqlite mode=ro query_only | n | counted only; not a Beta finance book | not opened as Atrium books | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| esb.sqlite sales_menu_summary | ESB menu sales summary | 2026-06-01 .. 2026-09-28 | 120 | REFERENCE | y — sqlite mode=ro query_only | y | count only; line qty comes from sales.raw | summary is not the bill line | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| catalog content_library.sqlite bzg_ops_purchase_requests example=1 | Beta example purchase requests | 2026-09-18 | 3 | HISTORICAL | y — sqlite mode=ro | n | kept as fixtures; excluded from operational projection | must not render as real Uma Blu purchasing | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |
| catalog content_library.sqlite venue_daily_closes | Uma Blu daily close rows | n/a | 0 | HISTORICAL | y — sqlite mode=ro query_only | n | none | NONE FOUND | source_system, source_id, source_timestamp, import_timestamp, verified_by_wolf=false, origin=historical |

## Daily close search

Status: NONE FOUND

- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite` venue_daily_closes: 0
- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite` venue_close_variance_policies: 0
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db` cash_count: 0
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db` deliveries: 0
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite` close_checklist_item: 12 hotel finance checklist, not an Uma Blu daily close
- `/Users/wolfterminal/beta-os/catalog/backups` venue_daily_closes: 0

No cash-variance threshold was inserted.
