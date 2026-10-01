# V1 surface inventory — summary
**As of:** 2026-10-01 ~19:06 WITA · Phase A discovery · prod `:8787` not restarted

## Floor this does not re-argue
Peaches sample: V1 HTML **55**, manifest boards **23**, prior parity **22 surfaces**. This file explodes those pages into functions. **177** is this wave’s function count. It is not a finished denominator. 191 V1 `/api/` paths in `dashboards/serve.py` were folded into the function that owns them. A later pass that splits every write verb will grow Y again.

## What a row is
One useful job. `atrium-sales.html` is **14** rows (the view registry: Overview, Milestones, Payments, New sale, Inventory, Deal types, Leads, Commissions, CV Cash, CV Payables, Tax Ceiling, Vendors, Common Area, Exceptions). `atrium-finance.html` is **15** screens plus report export. `trading-desk.js` is **14** cards. Content is **6** brand boards plus **20** shared workflows. Owner Home is the **14** `master.status.json` tiles plus the Wolf desk rails, not one “home” row.

`master.status.json` `generated_at` **2026-10-01T18:44:57+08:00**.

## Counts
| Slice | Rows |
|---|---|
| Owner home + Wolf desk | 26 |
| Atrium sales views | 14 |
| Atrium finance screens + export | 16 |
| Content boards + workflows | 26 |
| Trading cards | 14 |
| Uma / BZG | 16 |
| GGV | 5 |
| Person desks (jobs, not page names) | 7 |
| n8n templates | 11 |
| HR boundary (mapped, not built) | 10 |
| Business needs with **no V1 page** | 20 |
| Other (inventory, management, kuta, voice, legal, admin, learning, radar, travel, fitness, launchd set) | remainder |
| **Total** | **177** |

Domain tags on a row can be more than one, so a domain tally sums past 177. Largest tags: AMG/ATRIUM 33, OWNER/WOLF 32, Content/Marketing 29, Finance 25.

## Multi-function pages, called out
| Page | Rows |
|---|---|
| `wolf.html` + master tiles | 26 (pulse + desk rails) |
| `atrium-sales.html` | 14 |
| `atrium-finance.html` | 15 screens |
| `trading.html` | 14 |
| `content.html` + `content-*.html` | 6 boards + 20 workflows |
| `uma-blu.html` / recipes / alchemist | 10 Uma jobs |
| `hr.html` | 10 boundary rows, not completions |
| `n8n-templates/*.json` | 11 |

## Evidence anchors (this session)
- Atrium sales sqlite: units 88, payments 399, leads 570, commissions 68, cv_transactions 642.
- Recipes sqlite: 127 recipes, 756 lines, `recipe_compare` 0.
- Alchemist `data/alchemist.db`: suppliers 103, purchase_requests 2, pr_orders 543, ledger 473, petty_cash 443, pr_receipt_lines 477.
- Footage catalogue: 61,719 footage rows.
- LaunchAgents: **169** names ending in `.plist`. **280** names match `com.wolfcommand*` once `.bak`, `.parked`, and `.disabled` siblings are included. Prior parity said ~283. Those are the same pile, not 283 live jobs.
- `GET http://127.0.0.1:8787/api/health` → 200. `GET /api/desk-health` → 200, summary “Desk health FAIL · 13 faults.”

## HR
Ten HR routes are in the inventory so the boundary is visible. They are not counted as done in finance, payroll, or My Work.
