# Business operations audit
**Question:** if Matt compares what V1 could do, what he asked for, and what these businesses need, what is still missing from Beta?  
**Answer:** the operating loops. Beta has hubs, prove pages, and a few live read cards. It does not run a sale, a stay, a purchase, a close, a publish, or a pre-open outlet.

Outlet facts are from `org_outlet_registry` (7 rows, written 2026-09-29). Interview facts are from the 14-round ledger, which is a condensation.

## OWNER / WOLF
V1 home is a 14-tile pulse plus a desk (calendar, tasks, asks, needs-you, read pile, diet, shareholders, edits, reports, overnight coder, Peaches). Beta pulse has 10 cards and several of those numbers are real. Missing: Command Brief, R2 gap, team asks, read/view pile, edit queue, report pile, overnight coder, Peaches threads, Wolf calendar **writes**, the mission meter as a work tool. Progress and Finish War Room are Beta-only finish furniture. They are not the cockpit, and they are not a completion claim.

## GGV
V1: books board, nota upload, Xero final, client invite and agreement, voice seat, supplier dedupe script. Beta: ops pack and a finance seat page. Catalog notas, invoices, vendors are **0**. Xero is **ABSENT**. Habitat investment is a `-1` shell. Lead story is split: V1 tile said 2 new in 24h across three brands; Beta pulse says 271 Habitat sheet rows and ignores `core_leads` (8). Both facts are required. Neither is a pipeline a salesperson works.

## AMG / ATRIUM
V1 sales board is 14 working views over a sqlite with 88 units, 570 leads, 399 payments. Beta AMG is an ops pack of prove pages. Yanolja supplies a vacant/rooms percent (89%, 13/114) and says arrivals are UNKNOWN. Kuta tonight price is live; the board and the pipeline are shells; Wave 8 removed Kuta from primary Boards. Inventory and management are separate V1 pages, not covered by the occ card. Voice is a `-1` page.

## BZG
Group hub exists. July and August frozen boards and the shareholder report page do not. ESB last-night money is on the pulse. Nobody has filed a venue close (`venue_daily_closes` 0). Waste/yield and venue PnL pages are not that close.

## UMA BLU
The only OPEN outlet in the registry. V1 board, recipes (127 / 756), Alchemist buying (pr_orders 543, receipts 477, petty 443). Beta has the HTML set and a recipe sqlite with the **same** 127/756, so the cards were copied. Petty movements, operator issues, and receipt events in the Beta catalog are **0**. Today API returned 403 this session. Prior “Uma is BETA_BETTER” is withdrawn.

## Rainforest, Pool Bar, Merah, Rooftop, Room Service, Catering
Registry: Rainforest, Pool Bar, Merah, Rooftop, Room Service, Catering are **PRE-OPENING**. Notes say not to invent live ops. Standing preference names the restaurant Blu Zone, mid-Oct 2026, and treats the old “Rainforest Restaurant” name as dead. The registry row still says Rainforest and mentions ~7 Oct 2026. That name clash is unresolved. There is no operating desk for any of them. Pre-open is not a failure. It is also not a built outlet system.

## Content / Marketing
Six brand boards, printable cycle, comment, Amanda apply, tick → Metricool draft → Misa, ads studio, resolve, library, training, Google review reply, Atlas. Beta Content 2.0 plus seat stubs. Metricool **read** is live (6 brands, schedules) and **write** is off. Library assets 48 against NAS shallow 38,091 and `full_tree_indexed=false`. Prior content PARITY is withdrawn.

## Finance
Fifteen Atrium finance screens (night audit, flash, procure, cash, pay run, tax, close, owner pack, core, PSAK/USALI, master, handoff) plus GGV books. Beta finance files are shells and deepen pages. SoD must stay. Payroll distribution is an HR boundary, already blocked on V1, and is not a finance win. Bank import is CONFIGURED, not a match workflow. Xero is absent. Month close by the 5th (ledger round 2) has no proved checklist.

## Procurement
Alchemist is the V1 system of record and Beta can read its counts. The receive → match → pay loop was not copied (Beta receipt and PR line tables empty). GGV notas were not copied. Three-way match is a label on a V1 screen, not a Beta job.

## Inventory
Atrium inventory is its own board. Yanolja room inventory is a different thing. Uma stock is not proved. No par-level desk on Beta even though Alchemist has `par_levels` = 9.

## Recipes / Costing
Recipe cards copied. Variance table empty. Menu engineering (ledger round 5) does not exist. COGS alert is an n8n template with Xero absent.

## Sales / CRM
Atrium lead table 570. Habitat sheet 271. `core_leads` 8. Guest profile db 1 guest. No identity graph, no speed-to-lead timer, no discount authority. GGV onboard forms not rebuilt.

## Hotel Ops
Management board, night audit screen, housekeeping, room status: the first two exist only on V1 (finance night audit is a shell on Beta). Housekeeping has no page. `reservations.db` has 1 row. That is not occupancy history.

## Guest Experience
Pre-arrival and post-stay are n8n templates, not a journey. Review reply that writes back to Google is a V1 Amanda action. No guest portal.

## Maintenance
Ledger round 8. V1 finance has a pre-opening/assets screen. No cross-entity work-order system, barcode, or tropical PM calendar was found.

## Security
Ledger round 8. No CCTV evidence desk, no incident board wired to `state/incidents.db` as a Beta surface (the db file exists on V1; it was not opened this pass).

## Events / Ballroom
No board. Catering is a PRE-OPENING registry row, not an events desk.

## Tours / Concierge
No board. Guest requests in the ledger are not implemented.

## Personal / Trading / Fitness / Travel / Learning
Fourteen trading cards, Spartacus program, travel board, learning desk, radar. Beta serves read-only partial mirrors. Wave 8 retired trading, fitness, and travel from primary Boards. Connection matrix still marks Spartacus_Fitness and Trading_Desk **ABSENT**, which is staler than the RO routes. Nothing trades. Paper only stays the rule.

## Backup / Infra
V1 home showed B2 capacity and an R2 gap, and “14/14” system. This session: 169 live LaunchAgent plists, 280 names including backups and parked files. Beta backup tile is PARTIAL / stale. Integration health is a page, not the schedule. n8n’s 11 templates are files.

## My Work / Approvals / Evidence
My Work is the right shape (role, not a person’s name) and the wrong depth. 211 work items. 0 approval requests, 0 delegations, 0 authority limits. Evidence records 28. Person-desk jobs (Amanda invoice, review reply, Misa publish, Peaches thread) are not in that queue.

## HR boundary
V1 `hr.html` and ten write APIs (roster, edit, documents, shifts, payments, service charge, reviews, payslips, exec report, tasks) plus finance “payroll & service charge” with distribution blocked. Beta: `hr-deferred-hold-stamp-1`. **Mapped. Not implemented. Not counted as done on finance, My Work, or BZG labour pages.**

## Discovered this wave and absent from the 22-surface audit
Pool Bar, Merah, Rooftop, Room Service, Catering, housekeeping, maintenance, security, events, tours, approval engine, recipe variance, GGV notas, the 14 sales views, the 15 finance screens, the 14 trading cards, six content boards, legal desk, Command Brief, R2 gap tile, Peaches threads.
