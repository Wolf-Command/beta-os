# Dashboard eyes
**How this was looked at.** No browser session. Prod `:8787` was read with GET only (`/api/health` 200, `/api/desk-health` 200 and FAIL, 13 faults). Beta page `/` was **403** in the Peaches sample and was not hammered again. Beta JSON reads that returned 200 this session are quoted below. Uma and content coverage routes returned **403**. Screenshots were not taken. Eyes are HTML, API payloads, and sqlite.

`staff_ready=false`. A live number on a card is not an actable board.

## Owner Home
V1 source: `wolf.html` tiles and `master.status.json` at 18:44 WITA. Beta source: `/api/owner/pulse-ro` at 19:06 WITA, 10 tiles, honesty string says staff_ready false and no invented metrics.

| Card | Question it actually answers | Real or decorative | Can the Owner act | V1 absence |
|---|---|---|---|---|
| Atrium occ | How many rooms are vacant vs 114, from Yanolja at 07:16 | Real read. **Not** guest in-house. V1 tile at 18:44 said **1.75% occ**. Different question, different number | Open `/amg-ops-pack`, which is a hub, not the 14-view sales desk | The sales, inventory, and management boards |
| Kuta | Cheapest official rate tonight (1,274,000 IDR, Montana) | Real | Prove page, not the V1 grid. Off primary nav (Wave 8) | The board |
| BZG night | ESB grand and covers for biz 2026-09-30 | Real. Copy says no daily close was filed | Cannot file the close from the card | Uma today (403), July/August history |
| Leads | How many rows are on the Habitat sheet (271) and 3 needs-you | Real for that sheet. Silent on “2 new in 24h” across GGV and Atrium | Lead spine is not the V1 lead workbench | GGV and Atrium 24h, and the 570-row sales lead table |
| Purchasing | Alchemist unpaid, petty, PR orders, suppliers | Real counts. V1 tile said “2 open PRs”, which matches `purchase_requests=2`, while the pulse counts `pr_orders=543` | Cannot receive or pay | The buying desk |
| GWS | Are Gmail, Drive, Calendar readable, and is send off | Real policy card | Draft only. No Wolf calendar edit | Wolf calendar as the calendar |
| NAS/B2 | Shallow media count and index flag | Real stamp. `full_tree_indexed=false` | No. It does not open the 38,091 | Library that can find a file |
| Metricool | How many scheduled posts exist | Real. Engagement not filled in. WRITE off | Cannot publish | Tick, Misa queue, six boards |
| Fitness | What day number Spartacus says | Real day counter | Program not on the card | Peptides, breathwork, board |
| Backup | Is backup fresh | **PARTIAL**, atrium snap stale | No restore from the card | V1’s B2 capacity figure and the R2 gap tile, which are **not** on this 10-card pulse |
| Money, Command Brief, Content, HR, System 14/14, R2 | V1 home questions | **Missing from the Beta pulse** | — | Those tiles |
| Asks, Read/View, Shareholders, Edits, Reports, Coder, Peaches | V1 desk questions | Not on the pulse | — | The rails |

Local Owner Home as a **page** is still behind Cloudflare (Peaches 403). The JSON pulse is reachable. Those are different eyes. Do not tell Matt the home page rendered.

## AMG pack
Question the pack should answer: what do I sell, who owes, what is the rate tonight, who arrives. What the files are: `amg-ops-pack` plus many `*-1` and truth pages classed SHELL. The occ card answers only vacant vs rooms. Decorative risk: a hub of links feels like a hotel OS. The 14 sales views are the actual OS, and they are on V1.

## Uma Blu set
Question: what did we sell, what do we buy, what cash moved, what broke, what is the recipe cost. Files exist for today, PR, issues, petty, evidence, exceptions, bills. Tables behind them are empty where it matters (closes, petty movements, issues, receipts). Recipe rows exist as a copy. **403** on the today API, so this pass did not watch a human click. Class PARTIAL/SHELL per function, not “venue done”.

## GGV pack
Question: which client is profitable, which nota is unpaid, what did Xero post. Pack exists. Notas table 0. Xero ABSENT. Decorative if the hub is read as books.

## Content 2.0
Question: what do we shoot, what is ticked, what did Misa publish, what should change next cycle. Hub exists. Brand cadence pages do not. Publish write is off. NAS is not the library.

## Finance shells
Question: what is cash, what matches, what is the flash, what is the close, what can a shareholder read. Filenames say shell. Prior “BETA_BETTER” was the auth model, not these screens. Auth staying closed is correct. The screens are still missing.

## My Work / Finish
Question: what is mine, what did I prove, what is blocked. My Work is the right IA and an unproved queue (approvals 0). Finish War Room answers “how is the rebuild going”. That question is for the build, not for a guest, a supplier, or a shareholder. It must not be the Owner’s picture of the businesses.

## What was not seen
Phone layout, collapsed-tile behaviour on Beta, any click that writes, any staff login. Desk-health on V1 already reports 13 faults; that line was not root-caused here.
