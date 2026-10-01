# Beta surface inventory — summary
**As of:** 2026-10-01 ~19:06 WITA · `:8788` read only · `staff_ready=false`

## Floor
Beta HTML **158** (Peaches). This pass classifies those 158 page files and adds **30** function rows that a page file would have hidden. **HUMAN_PROVEN = 0.**

## Classification
| Class | Records |
|---|---|
| SHELL | 63 |
| PARTIAL | 104 |
| READ_ONLY_MIRROR | 11 |
| FUNCTIONAL_REAL_DATA | 8 |
| MISSING | 2 |
| HUMAN_PROVEN | 0 |
| FUNCTIONAL (writes proved) | 0 |

The 8 real-data rows are **read glances** on `/api/owner/pulse-ro` and the NAS stamp: Atrium vacant-based occupancy, Kuta tonight, BZG night from ESB, Habitat lead stock, Alchemist counts, fitness day, Metricool schedule, NAS/B2 stamp. Each one is a card. None of them is the board behind the card.

Page files ending in `-1`, or named shell / prove / deepen / stamp, were classed **SHELL**. Everything else that was not a proved read defaulted to **PARTIAL**. That is deliberate.

## A working feature did not close its page
| Working read | Still open on the same topic |
|---|---|
| Pulse Atrium 89% · 13 vacant / 114 | Guest in-house, arrivals, ADR UNKNOWN. Sales board’s 14 views are not this number. |
| Pulse BZG IDR 15,140,000 · 87 covers | `venue_daily_closes` = 0 |
| Pulse purchasing unpaid 106 · PRs 543 | `bzg_ops_receipt_events` = 0, `bzg_ops_pr_lines` = 0 |
| Metricool 6 brands, schedules | WRITE off. Tick → draft → Misa not running |
| Fitness day 1 | Spartacus program, peptides, breathwork not rebuilt |
| Recipe sqlite 127 / 756 | Same counts as V1, so this is a copy. `recipe_compare` = 0. UI not proved (`/api/bzg/uma-blu/today` → **403**) |
| `core_work_items` 211 | `core_approval_requests` 0, `core_delegations` 0 |

## Auth note
Peaches: `GET /` on `:8788` → **403**. This session: `GET /api/health` and `GET /api/owner/pulse-ro` → **200**; `GET /api/bzg/uma-blu/today` and `/api/content/nas-coverage` → **403**. Open read routes and closed desks are both true.

## Overturns of “page done”
- Atrium finance is not ahead. `fin-tax-shell-1`, `fin-recon-shell-1`, `fin-ap-ar-shell-1`, `atrium-fc-truth-deepen-1` are shells. SoD stays.
- Content 2.0 is not the six brand boards and not the publish loop.
- Uma HTML set (today, PR, petty, issues, evidence, bills) is not one finished venue. Petty, issues, receipts are empty tables.
- Voice `-1` pages are not the three V1 voice seats.
- `habitat-investment-1` is not parity with the V1 board.
