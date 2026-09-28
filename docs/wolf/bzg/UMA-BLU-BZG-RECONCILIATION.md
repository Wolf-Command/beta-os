# Uma Blu / BZG reconciliation

28 Sep 2026. Pack BZGRECON-1. Discovery and reconcile only. ClickUp is provenance in older delivery notes, not a source of truth, and this pack adds no ClickUp dependency.

No redesign. No edit to `scripts/serve_beta.py`, dashboards, atrium files, or `~/atrium-finance`. Beta was not restarted. Production `~/.openclaw` and `:8787` were not written. No ESB write. No secret value is in this note.

Branch inspected: `build/wolf-command-rebuild` at `0e906bf` (2026-09-28 17:39 +0800). `git branch -a` listed two branches: this one and `main`.

Statuses used below are exactly one of: EXISTS+WORKING, EXISTS+NEEDS WIRING, PARTIALLY BUILT, SPECIFIED ONLY, MISSING, BLOCKED BY REAL INTEGRATION/DATA.

## ESB STATUS

Classification for the credential the live ingest actually reads: **FOUND + USABLE**.

| Candidate | Where it is read | Keys (names only) | File mtime | Classification | This session |
| --- | --- | --- | --- | --- | --- |
| Production static bearer | `wolf-system/scripts/esb_ingest.py` function `token()`, file `~/.openclaw/credentials/esb-production.json` | `credential` (SET). Also `env`, `company_code`, `_notes`, `_todo` | 2026-07-13 13:21 | FOUND + USABLE | One GET, the same client the ingest uses: `GET /corev1/master/get-menu-category?page=1` on `https://core-api.esb.co.id`. HTTP 200. Body discarded. Success true |
| OMS login used by `esb_oms.py` | `~/.openclaw/wolf-secrets.env`, selected when `ESB_ENV` is prod. Script `~/.openclaw/workspace/wolf-system/scripts/esb_oms.py` | `ESB_OMS_USERNAME_PROD`, `ESB_OMS_PASSWORD_PROD` (both SET). Related SET names: `ESB_OMS_STATIC_TOKEN_PROD`, `ESB_OMS_CORE_PROD`, `ESB_OMS_FNB_PROD`, `ESB_OMS_EXT_USER_PROD`, `ESB_OMS_EXT_PASS_PROD` | env file 2026-07-21 15:16 | FOUND + USABLE on this morning's log. Not called again here | `~/.openclaw/logs/esb-oms.log` last line `2026-09-28T05:51:53+08:00 login OK`. A second login was not issued. Login is a POST and earlier bad passwords returned 400 |
| Core / staging file | `esb_inline.py` reads `~/.openclaw/credentials/esb-core.json` after the env file. Ingest does not use this file | `username`, `password`, `_erp_production.password`, `_staging_rollback.password`, `_staging_rollback.bearer_token`, `_staging_rollback.pos_pin` all SET. `_staging_rollback.brand_id` is null | 2026-07-16 17:34 | FOUND NEEDS VALIDATION | Not called. Lockout risk. Vault note `state/esb-auth-state.md` (2 Jul 2026) says CORE form login had been rejecting since about 28 Jun 2026 |
| Stock basic auth | `esb_oms.py` `_basic_request`. Sync skips it | `ESB_OMS_EXT_USER`, `ESB_OMS_EXT_PASS`, `ESB_OMS_EXT_USER_PROD`, `ESB_OMS_EXT_PASS_PROD` all SET | same env mtime | FOUND NEEDS VALIDATION | Not called. Last sync line still skips it |

Launch agents (labels only, no secret env values): `com.wolfcommand.esb-ingest` runs `esb_ingest.py` at 05:30 (`--full` on Monday). `com.wolfcommandsystem.bzg-esb-sync` runs `bzg-esb-sync.py` at 23:30. `com.wolfcommand.esb-oms-reply-watcher` is installed. Beta `.env` and `.env.example` have no `ESB_*` key.

Keychain: `security dump-keychain` without `-d` found no ESB item. `security find-generic-password -s esb`, `esb-core`, `esb-production`, and `ESB` each exited 44. Service `wolf-secrets-vault` exited 0 (account name `wolfterminal`). An AirPort item named `UMA-BLU` is a Wi-Fi entry, not the API credential. Its value was not read.

Obsidian vaults on this Mac: `WolfCommandSystem/WolfCommand` (has `.obsidian`), `Documents/Wolf-Vault`, `Documents/Wolf-Vault-Inbox`. Filename hits only, and only in the first vault: `03-BZG/ESB-Auth-State.md`, `03-BZG/ESB-Auth-Update-2026-07-19.md`, `01-Wolf-Command/Filing/ESB-BZG API Access Agreement.md`. Those notes were not treated as a second secret store. The 19 Jul note confirms branch `BLZ`, user name `BLUZSUPERADMIN`, and that goods-receipt, POS settlement, and cancel-menu reports are ERP-only. It does not record a later password change.

Password-change date: the dated note found is the regression "since ~28 June" in `state/esb-auth-state.md`, then the production cutover on 2026-07-13 and the Felix confirmation on 2026-07-19. No ESB password-change date after the env file mtime 2026-07-21 was found in `~/.openclaw/wolf-output/decisions.md` (one ESB line, the 2026-07-19 Alchemist pick) or in the September docs searched. The July files are the post-June candidates, and the bearer from 13 Jul still authenticates.

Last good sync:

- Ingest log `~/.openclaw/logs/esb-ingest.log`: `2026-09-28T05:37:19+08:00` FULL done. The same log's only `ERROR` line in the retained file is `2026-09-14` "The read operation timed out", and that run still logged done. No 401 in that file.
- Warehouse `~/.openclaw/data/esb.sqlite` opened `mode=ro`. 68,358,144 bytes. mtime 2026-09-28 05:47:43. `sales` max `pulled_at` is that same timestamp, `biz_date` 2026-04-05 through 2026-09-27, 8,762 rows. The ingest done line is 05:37 and this pulled_at is 05:47. The only `INSERT`/`upsert` into `sales` found under `wolf-system/scripts` is `esb_ingest.py`. What wrote the later timestamp is UNKNOWN.
- `esb-inline.log` last line `2026-09-28T17:54:37+08:00` `daily(2026-09-27) OK (oms-prod)`. Bill count on that line: 61. Cover count: 94. Amounts from the log are not copied here.
- `bzg-esb-sync.log` last done line `2026-09-27T23:31:10+08:00` with `daily_sales` 1. `stock_position` skipped: pending Basic-auth verification of `/external/general/stock-branch`. `petty_cash` skipped: no OMS endpoint. `goods_receipt` 0.

Warehouse counts (read-only, no payloads): `gl_journal` 5,917; `goods_receipts` 0; `material_usage` 18,637 (`biz_date` 2026-06-01..2026-09-27); `members` 0; `menu_categories` 5; `menu_templates` 4; `menus` 188; `products` 426; `promotions` 2; `sales_menu_summary` 119.

Beta's close snapshot (`scripts/core/esb_close_snapshot.py`) reads this warehouse and still sets `settlement_api` to UNAVAILABLE. That module was not asked to call ESB.

Human action for the live read path: none. The ingest file and key are `~/.openclaw/credentials/esb-production.json` key `credential`. Do not paste a token into chat.

Human action only if someone wants the skipped stock read: confirm the external basic credential with Felix, then the switch is `STOCK_SOURCE` in `wolf-system/scripts/bzg_inventory.py` (code default is `esb`; the sync still skips the call). This pack did not flip it.

## Capability matrix

Real-data column is yes only when this session counted rows or files. Tests named below were not re-run this session. Last pytest run: UNKNOWN.

| Capability | Status | Where | Evidence | Real data | Gap to Beta |
| --- | --- | --- | --- | --- | --- |
| Recipe builder | EXISTS+WORKING | Prod `dashboards/serve.py` routes `/api/uma-blu-recipes` and `/api/uma-blu-recipes/photo` (around lines 4362 and 4402). Store `wolf-system/scripts/uma_blu_recipes.py`. DB `wolf-system/uma-blu/recipes.sqlite` mtime 2026-09-12. Page `dashboards/uma-blu-recipes.html` mtime 2026-09-10 | `recipes` 127, all `kind=dish`. `recipe_lines` 756, all `line_kind=ingredient`. Beta has no recipe route | yes | No reader and no route on Beta. `serve_beta.py` only carries the honesty flags `recipe_cost_standards: False` |
| Recipe DB / costing | PARTIALLY BUILT | Same sqlite. Formula in `uma_blu_recipes.py`. Sheet extractor `scripts/bzg_recipe_costs.py`. Notion engine `scripts/recipes_system.py` (separate, not the sqlite) | Cost source on lines: `card` 628, null 126, `manual` 2. `recipe_compare` 0 rows. Log `bzg-recipe-costs.log` `2026-09-28T05:47:49+08:00`: 101 cards (49 food, 52 drinks), 104 ESB items costed, 6 unmatched cards. ESB `goods_receipts` 0, so receipt prices are not in the warehouse | yes, card costs. Receipt-price link no | Beta `scripts/core/bzg_bom_yield.py` is a skeleton. Commit `6e33bb4` message: stays SPECIFIED. `writes_accepted` false. Tests `scripts/tests/test_bzg_bom_yield.py` (`test_empty_framework`, `test_refuses`). Not re-run |
| Ingredients | EXISTS+WORKING | `recipe_lines` plus ESB `products` 426 and `material_usage` 18,637. Alchemist `pr_vendor_items` 918 | Counts above | yes | Not a Beta table |
| Units / conversions | PARTIALLY BUILT | Hard-coded maps `_UNIT_TO_G` and `_UNIT_TO_ML` in `uma_blu_recipes.py`. Alchemist table `unit_map` | `unit_map` 0 rows | maps in code, no conversion rows | No Beta conversion table |
| Yield / portions | EXISTS+WORKING | `recipes.yield_n` / `yield_unit` | `yield_n` set on 127 of 127 | yes | Beta yield slot is an empty kind in `bzg_bom_yield.py` (`bom`, `yield`, `waste`, `theoretical_cost`, `menu_engineering`, `notes`) |
| Subrecipes | PARTIALLY BUILT | Column `recipe_lines.subrecipe_id` | 0 lines with a subrecipe id. Every recipe `kind` is `dish` | schema only | Same |
| Menu items | EXISTS+WORKING | ESB `menus`, `menu_categories`, `menu_templates` | 188 / 5 / 4. Pulled 2026-09-28 05:32 | yes | Beta does not serve this master. Read-only warehouse is already the SoT |
| Food cost / margin | PARTIALLY BUILT | Card formula in `uma_blu_recipes.py`. Match log above. `target_cos` set 127/127. `real_sell` set 107/127 | Today's cost log. Unmatched remainder 6. No `recipe_compare` rows | yes for card cost and target COS. Live margin page on Beta: no | Skeleton refuses theoretical cost |
| Suppliers | EXISTS+WORKING | Alchemist `~/.openclaw/workspace/alchemist/data/alchemist.db` mtime 2026-09-28 14:07. Table `suppliers`. Location row: id 1, name Uma Blu | 103 suppliers. `contact` nonempty: 0. `pr_vendors` 38. `esb_id_map` 3 | yes names. Contact field empty | Beta has no supplier table. `esb_procurement.py` can GET `/supplier` and defaults writes to dry-run until `ESB_PROC_WRITE=1`. That flag's value was not used |
| Purchase requests | EXISTS+WORKING | Alchemist `pr_orders` 504. Beta catalog `bzg_ops_purchase_requests` | Alchemist status counts: Paid 304, Received 116, Awaiting Devi 38, Ordered 24, Cancelled 21, Rejected 1. Beta rows are 3 and `example=1`: `PR-UMA-EXAMPLE-WAIT`, `PR-UMA-EXAMPLE-POLICY`, `PR-UMA-EXAMPLE-CLAIM` (created 2026-09-18). `state/uma/cutover.json` has `cutover_at` null | yes in Alchemist. Beta rows are examples | `scripts/core/uma_alchemist_ro.py` can read Alchemist `mode=ro` and map statuses. It does not copy rows into `bzg_ops_*`. Routes already exist under `/api/bzg/uma-blu/prs` |
| Approvals | PARTIALLY BUILT | Alchemist status and `approver` columns. Wolf Core `scripts/core/approvals.py` | Awaiting Devi 38 is the live queue in Alchemist. Wolf approval rows for these PRs: not counted as a join this session | yes as Alchemist statuses | Uma PR states on Beta are the 3 examples. Core approvals are not the Alchemist queue |
| Purchasing / purchase orders | PARTIALLY BUILT | Alchemist `pr_orders` is the order book. `esb_procurement.py` documents GET `/purchase/purchase-order` and POST dry-run | Ordered 24 in the status split above. ESB create body "NOT yet confirmed" in that script's header | yes locally. ESB PO post not confirmed | Do not enable `ESB_PROC_WRITE` from Beta |
| Receiving | PARTIALLY BUILT | Alchemist `pr_receipt_lines` 452, `pr_order_lines` 1,830. `deliveries` 0. `delivery_lines` 0. Nota files `alchemist/notas` 448 `.jpg`. Beta `bzg_ops_receipt_*` | Receipt line counts. Beta receipt events, lines, and slots: 0 | yes lines and photos. Structured `deliveries` table empty | Beta receive API exists (`uma_devi_p0.py`, routes under `/api/bzg/uma-blu`). Tables empty. ESB `goods_receipts` 0, matching Felix 19 Jul: goods receipt is ERP-only |
| Stock / inventory | PARTIALLY BUILT | `scripts/bzg_inventory.py` (Google sheet tab `Inventory`, read-only against ESB). `par_levels` 9. ESB `products` and `material_usage` | Sheet itself was not opened. `STOCK_SOURCE` default in code is `esb`. Sync still skips `/external/general/stock-branch` | par rows yes. On-hand sheet: UNKNOWN. ESB on-hand: not verified | Beta `/api/bzg/uma-blu/stock` exists. Five-pack note says the Uma page tells the operator stock stays in ESB. This session did not load the page |
| Counts | PARTIALLY BUILT | `scripts/bzg_stocktake.py` expects table `stock_counts`. Alchemist `cash_count` | `stock_counts` is not a table. `cash_count` 0 | no count rows | No Beta count table |
| Transfers | MISSING | Outlet name lists only. No transfer table found in Alchemist or Beta BZG modules | `bzg_receive.py` and `petty_cash.py` list outlets. Beta "transfer" hits are money-word refusals in the skeletons | no | Nothing to wire until a transfer record exists |
| Waste | PARTIALLY BUILT | Beta `scripts/core/bzg_variance_waste.py`. Alchemist `variances` | Beta skeleton, commit `3533492` stays SPECIFIED. `variances` 0. Stock-take script cannot run without `stock_counts` | no waste rows | Empty framework is not a live waste book |
| Variance (cash close) | BLOCKED BY REAL INTEGRATION/DATA | `venue_close.py` and `venue_close_variance_policies` | Policy rows 0. Code path sets display `BLOCKED BY BUSINESS POLICY` when no active policy. Closer seat below | no | A threshold row is a Matt decision. This pack did not insert one |
| Daily close | PARTIALLY BUILT | `scripts/core/venue_close.py`, `scripts/core/esb_close_snapshot.py`, migration `021_uma_blu_daily_close.sql`, dashboard `dashboards/uma-blu-close.html` | `venue_daily_closes` 0. Position `POS-BZG-CLOSER-UMA-1` status ACTIVE, label "Closing Operator · Uma Blu (WAITING roster)". No active assignment on that position. Role `ROLE-BZG-CLOSER` status SPECIFIED. Tests live in `scripts/tests/test_uma_blu_daily_close.py` (not re-run) | ESB days yes. Close rows no | Route `/api/bzg/uma-blu/closes` already on Beta. Blocker is the empty policy and the empty closer seat, not a missing module |
| ESB reconciliation | EXISTS+WORKING | Ingest, inline, and `bzg-esb-sync.py`. Beta snapshot is payment lines, not settlement | Sync and ingest times above. `settlement_api` remains UNAVAILABLE in the Beta snapshot module | yes warehouse. Settlement report no | Beta already reads the warehouse for close. It does not call the API |
| Bills / notas | PARTIALLY BUILT | Alchemist `ledger` 420 (paid 362, unpaid 53, cancelled 5). 448 nota jpgs. Beta pages `dashboards/bzg-uma-blu-bills.html` | Counts. `item_prices` 0. `deliveries` 0 | yes ledger and photos | Beta bill tables were not a separate sqlite. The bills page is a Beta dashboard over the ops console, which has example PRs only |
| Evidence | EXISTS+NEEDS WIRING | Wolf Core `scripts/core/evidence.py`. Nota jpg directory. Beta `dashboards/bzg-uma-blu-evidence.html` | 448 photos on disk. Beta PR `quote_evidence_id` / `payment_evidence_id` not read (example rows). Core evidence is not the nota folder | photos yes. Beta evidence rows UNKNOWN (not counted; table name in the catalog dump did not include a BZG evidence table) | Point evidence at the existing nota files. Do not copy them into the repo |
| Outlet dashboards | EXISTS+WORKING | Beta pages: `dashboards/bzg-uma-blu.html`, `uma-blu-close.html`, petty, exceptions, evidence, pr, issues, bills. Prod recipes page | Files present. This session did not click them. `serve_beta.py` was not restarted and was not edited | pages exist. Live browser check this session: not done | Already on Beta. ATRIUMFIN-FULL-1 owns `serve_beta.py` and dashboard files, so this pack left them untouched |
| BZG master dashboard | PARTIALLY BUILT | `dashboards/bzg.html`, `dashboards/bzg-mgmt-cluster.html`, `scripts/core/bzg_mgmt_cluster.py` | Cluster is a desk over empty skeletons plus the Uma console | desk yes. Live BOM/variance/PnL no | Routes `/api/bzg/mgmt-cluster` already registered |
| Venue P&L | SPECIFIED ONLY | `scripts/core/bzg_venue_pnl.py` commit `a75181b` | Skeleton refuses books, ESB writes, and fill. No PnL sqlite in `catalog/` | no | Do not start a second P&L |
| Shared-cost allocation | SPECIFIED ONLY | `scripts/core/bzg_allocation_engine.py` commit `62f4eca` | Same pattern. No allocation sqlite in `catalog/` | no | Same |
| Reputation observe | SPECIFIED ONLY | `scripts/core/bzg_reputation_observe.py` commit `b88f274` | `catalog/bzg_reputation.sqlite` absent. Venue set in code: `UMA`, `RAINFOREST`, `MERAH`, `ROOFTOP`. No observation rows counted | no | Same |
| SOPs / checklists | PARTIALLY BUILT | Beta `scripts/core/sop_factory.py` (tables `sop_versions`, `sop_approvals`, `sop_acknowledgements`, `sop_uses`, `sop_learnings`). Prod `dashboards/sops/uma-blu-recipes.html` | Those SOP tables are not in the live catalog `content_library.sqlite` (83 tables; the SOP names were absent). Factory sqlite files found are under `catalog/backups/tmp-sop-factory-*` and `state/build-factory/tmp-f1/` | recipe SOP page exists on prod. Live Beta SOP rows: no | Uma checklists are not commissioned in the catalog |
| Shareholder reports | PARTIALLY BUILT | See the shareholder section | HTML through 2026-08. Send path gated | drafts yes. September pack: not found | Not a Beta route |
| Shareholder contacts | PARTIALLY BUILT | See below | BZG names in a test and a 5 Sep note. Live access key absent | names yes. Live allow list no | Do not invent a Beta access list |

People on Beta catalog (read-only): `PERS-DEVI` display name Ni Putu Devi Parwati is ACTIVE and primary on `POS-BZG-FB-OPS-1` / `ROLE-BZG-FB-OPS-LEAD`. Her Head of F&B assignment `ASG-DEVI-HFB-UMA-1` is ENDED at 2026-09-19 15:55 +0800. Roles `ROLE-BZG-HFB`, `ROLE-BZG-CLOSER`, `ROLE-BZG-FB-OPS-LEAD` are status SPECIFIED. Assignment totals in `org_assignments`: 21 (17 ACTIVE, 4 ENDED).

## Canonical chain

INGREDIENT → UNIT/CONVERSION → PURCHASE COST → SUBRECIPE → RECIPE → PORTION/YIELD → MENU ITEM → PRICE → FOOD COST → MARGIN

| Link | Today |
| --- | --- |
| Ingredient | Yes. 756 recipe lines, 426 ESB products, 918 vendor items |
| Unit / conversion | Code maps for g and ml only. `unit_map` 0 rows |
| Purchase cost | Card cost on 628 lines. 126 lines have a null cost source. ESB `goods_receipts` 0. Alchemist `item_prices` 0. Vendor items have a `last_price` column (918 rows); amounts were not read |
| Subrecipe | Column exists. 0 links |
| Recipe | 127 dishes in `recipes.sqlite` |
| Portion / yield | `yield_n` on all 127 |
| Menu item | ESB `menus` 188. Cost log matched 104 ESB items on 28 Sep 05:47. 6 cards unmatched |
| Price | `real_sell` on 107 of 127 recipes. ESB menu price payload was not parsed |
| Food cost | Card formula in `uma_blu_recipes.py`. Not a Beta calculation |
| Margin | `target_cos` stored on all 127. `recipe_compare` 0, so a stored actual-versus-target row was not found |

The chain is connected in the wolf-system recipe store through yield and card cost. It is not connected through subrecipes, unit conversion rows, ESB goods receipts, or a Beta page.

## Ops chain

SUPPLIER → PR → APPROVAL → PURCHASE → RECEIVING → INVENTORY → CONSUMPTION/ESB SALES → COUNT → WASTE → VARIANCE → DAILY CLOSE → EXCEPTION → DASHBOARD

| Link | Today |
| --- | --- |
| Supplier | Alchemist 103. Contact column empty |
| PR | Alchemist 504. Beta 3 examples |
| Approval | Alchemist "Awaiting Devi" 38. Wolf Core is a separate engine |
| Purchase | Those orders. ESB PO write is dry-run |
| Receiving | 452 receipt lines, 116 status Received, 448 nota jpgs. `deliveries` 0. ESB goods receipts 0 |
| Inventory | Script plus 9 par rows. ESB stock branch skipped. On-hand sheet not opened |
| Consumption / ESB sales | Warehouse sales 8,762 and material usage 18,637 through 2026-09-27. Inline OK at 17:54 today |
| Count | No `stock_counts` table. `cash_count` 0 |
| Waste | Skeleton plus 0 variance rows |
| Variance | 0 policies. Close screen copy is BLOCKED BY BUSINESS POLICY |
| Daily close | Module and route exist. 0 close rows. Closer seat empty |
| Exception | Beta routes `/api/bzg/uma-blu/exceptions` and owner/manager variants. `bzg_ops_operator_issues` 0. `bzg_ops_loop_notes` 0 |
| Dashboard | Uma pages and `bzg.html` exist on Beta. This session did not browse them |

`ACTIVE_OUTLETS` in Alchemist `petty_cash.py` and `bzg_receive.py` is `["Uma Blu Cafe"]`. The longer `OUTLETS` list is Uma Blu Cafe, Blu Zone Restaurant, Underground Bar, Pool Bar, Rooftop Bar, Catering, Room Service. The comment in those files says more than one active outlet re-enables the outlet question. Reputation's venue set adds Rainforest and Merah as names only. Alchemist `locations` has one row. There is no cloned app per venue.

## Shareholder reporting

What exists:

- `wolf-system/scripts/shareholder_report.py`. Four-page PDF for BZG, AMG, GGV. Header says revenue, occupancy, covers, and headcount are not wired and render pending. `send_to_shareholders()` is a gated stub. `SHAREHOLDER_EMAILS` is not a key in `wolf-secrets.env`.
- `wolf-system/scripts/bzg_monthly_report.py`. Draft unless bank ingest and a non-empty `state/bzg-md-summary-<YYYY-MM>.txt` both pass. This session did not run `--status`.
- `wolf-system/scripts/build_bzg_shareholder_report.py` and prod pages `dashboards/bzg-shareholder-reports.html`, `bzg-august-2026.html` (mtime 2026-09-10).
- Vault HTML, one shareholder file per company, for 2026-05, 2026-06, 2026-07, and 2026-08 under `WolfCommandSystem/WolfCommand/06-Strategy/Monthly-Reports/`. August also has `2026-08-BZG-shareholder-GAPS.md`. No 2026-09 folder was listed.
- Sable owned state `WolfCommand/01-Wolf-Command/System-Registry/Sable-OWNED-STATE-2026-09-05.md`. Autopilot described there: on the 5th, Peaches pulls ESB, banks, and Nirmata, Sable drafts, Peaches grills Matthew, send only when Matthew says. That file says three Gmail drafts were unsent as of 5 Sep. This session did not open Gmail.

Contacts. Emails are not copied into this note.

| Company | Names found | Email canonical? |
| --- | --- | --- |
| BZG | Matthew, Scott, Etik, Maciej. Source: `dashboards/test_bzg_shareholder_access.py` asserts `bzg_shareholder_allow` is exactly those four, and `Sable-OWNED-STATE-2026-09-05.md` names the same four. Devi and Carolus are asserted absent | The test and the 5 Sep note are the records. Live `dashboards/access-config.json` mtime 2026-09-15 has no key `bzg_shareholder_allow`. Its `page_access` (39 entries) does not point the shareholder HTML pages at that key. The only BZG page in that map is `bzg-finance.html` → `bzg_finance_allow`. So the live gate is not that list |
| AMG | No shareholder name list found. Monthly HTML exists | UNKNOWN. `SHAREHOLDER_EMAILS` is absent from the env file |
| GGV | No shareholder name list found. Monthly HTML exists. The 17 Aug client map says the evidenced content client is Selong Selo and that this is not a shareholder roll | UNKNOWN |

`uma_blu_allow` in the live access config is a list of 4. The note beside it contains addresses, so the note was not copied. Those four were not assumed to be the shareholder list.

## Fastest to Beta

Ranked for a later pack. This pack did not start them. ATRIUMFIN-FULL-1 owns `scripts/serve_beta.py` and `dashboards/*.html`. A route or dashboard edit collides. A new read module under `scripts/core/` does not, until someone imports it from `serve_beta.py`.

1. **S. Read the existing recipe sqlite.** New module that opens `uma-blu/recipes.sqlite` `mode=ro` and returns the 127 dishes, yield, and card-cost coverage. Files: the new module and `scripts/tests/`. Collision with `serve_beta.py`: no, until a route is added. The route would collide.
2. **S. Prefer the Alchemist read-only projection on the Uma PR, petty, and history reads.** `uma_alchemist_ro.py` and `cutover.json` already exist. Files: `scripts/core/uma_alchemist_ro.py`, `scripts/core/uma_ops_console.py`, and the handlers in `serve_beta.py`. Collision: yes if the handlers change. The 3 example PRs should stay labelled `example=1`.
3. **S. Read the 28 Sep cost-match log and the recipe `cost_source` counts onto a Beta read model.** Files: new module next to `bzg_bom_yield.py`. Do not turn the skeleton into a writer. Collision: no, until a route is added. `bzg_recipe_costs.py` writes a Google tab; the Beta reader must not call that writer.
4. **M. Consumption read for Uma from the warehouse.** `material_usage` and `sales` are already pulled. A read model can show theoretical usage without stock-branch and without a count table. Files: new module using `esb_close_snapshot.py`'s read-only connect. Collision: no, until a route is added. Do not fill `STOCK_SOURCE` or call stock-branch.
5. **M. Shareholder draft status, no send.** Read whether 2026-08 HTML exists and whether `bzg_monthly_report.py` gates would pass. Files: new module. Do not call `send_to_shareholders`. Collision: no, until a route is added.

Daily close is already on Beta. The next step there is Matt's policy and a named closer, not a new module.

## Proposed build order

These are outlines for later packs. They reuse Wolf Core identity, permissions, approvals, evidence, audit, and exceptions. One venue config, Uma Blu first. Rainforest, Merah, rooftop, pool bar, and the other names in `OUTLETS` stay config on that same code. `ACTIVE_OUTLETS` is the switch that already exists in Alchemist. No cloned apps.

**C. Recipe builder.** Read `recipes.sqlite`. Do not replace it with the empty BOM skeleton. Keep subrecipe as a real link only when a row has `subrecipe_id`. Show card cost, null cost, yield, and the ESB menu match. Refuse ESB writes. Refuse a second recipe database.

**D. Ops chain.** Keep Alchemist as the purchasing record until `cutover_at` is set. Project supplier, PR, receipt lines, and notas. Leave ESB procurement POST dry-run. Inventory stays theoretical usage from `material_usage` until a count table exists. Waste and variance stay empty until counts exist. Daily close stays the current venue-close module.

**E. Shareholder engine.** Keep Sable's draft gate: no send unless Matthew says. Read the monthly HTML and the two gates in `bzg_monthly_report.py`. Do not rebuild the PDF scaffold in `shareholder_report.py` as a second engine. Do not add a recipient list that is not already in a source file.

## Questions only Matt can answer

1. Cash variance: should a mismatch be closable, and if so who sets the threshold? The policy table has 0 rows and the close module already says BLOCKED BY BUSINESS POLICY.
2. Who is the Uma closer? `POS-BZG-CLOSER-UMA-1` is waiting on a roster. Devi is on the F&B operations lead seat, not this one.
3. When does Alchemist stop being the purchasing record? `state/uma/cutover.json` has `cutover_at` null.
4. May Beta stay on warehouse sales and material usage, and leave ESB stock-branch and goods-receipt uncalled, until Felix confirms those APIs?
5. Shareholder send: the 5 Sep note left August drafts unsent, and the live access config no longer has `bzg_shareholder_allow`. Who may receive the next BZG pack, and is September's pack meant to start?
6. Which outlets are actually operating now? Active code list is Uma Blu Cafe only. The other names are present and not active.

## Search record

Authorised and read: `docs/wolf/five/CREDENTIAL-DISCOVERY.md`, `docs/wolf/five/VAULT-FINDING.md`, `~/beta-os` (this branch and `main`), `~/.openclaw/workspace/wolf-system` (read), `~/WolfCommandSystem`, `~/wolf-phase2` (launch-agent backups of the ingest plist), the three vaults above, `beta-os/.env` key names, `~/Library/LaunchAgents` ESB plists, keychain names, ESB logs, `esb.sqlite` schema and counts, Alchemist schema and counts, Beta `catalog/content_library.sqlite` schema and the BZG counts above.

Not done: no pytest re-run, no browser pass, no ESB login POST, no stock-branch call, no Google sheet open, no Gmail open, no write to `~/.openclaw`.

EXIT:0
RESULT: PASS
