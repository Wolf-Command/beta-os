# End-to-end chains
A chain is incomplete wherever the middle has no write, an empty table, or a feed marked ABSENT. Read cards at the ends do not repair the middle.

## Lead → sale
1. Lead appears (V1 sales leads 570; Habitat sheet 271; GGV onboard form; n8n `01-ggv-new-lead`).
2. **Broken.** Beta `core_leads` = 8 and is ignored by the pulse. No single identity. GGV invite/agreement not rebuilt. Speed-to-lead has no timer.
3. Quote / deal type / commission (V1 views `deals`, `comms`). **Missing on Beta.**
4. Record sale (V1 button “Record this sale”, payments 399). **Missing on Beta.**
5. Downstream owner report. **Shell.**

## Booking → departure
1. Rate tonight: **live read** (Kuta card).
2. Availability: Yanolja vacant/rooms **live**. Arrivals and in-house **UNKNOWN**.
3. Reservation store: `reservations.db` = **1 row**. Not a book.
4. Pre-arrival message: n8n template only. Calendly **BLOCKED_EXTERNAL**.
5. In-house requests, housekeeping, room damage: **no board**.
6. Night audit → journal: V1 screen exists, Beta is not that screen. Yanolja `yanolja_live` was false inside the V1 finance payload shape (`nightaudit` screen sets `yanolja_live: False` in `atrium_finance.py`). The pulse read and the finance night-audit flag are not the same pipe.
7. Post-stay review → training: n8n template. Google reply action is V1-only.
8. Departure folio → cash: **not built**.

## Purchase request → general ledger
1. PR exists in Alchemist (`purchase_requests` 2 open-style rows, `pr_orders` 543, lines 2,017). Pulse can **show** counts.
2. **Broken.** Beta `bzg_ops_pr_lines` = 0, `bzg_ops_receipt_events` = 0, `bzg_ops_receipt_lines` = 0.
3. Three-way match: V1 procure screen. Beta AP shell.
4. Payment run: V1 screen. Alchemist pay API is preview/confirm on V1; Beta RO says pay stays NO. Correct until governed. The governed version does not exist (`core_approval_requests` 0).
5. Xero bill: template 09, connection **ABSENT**.
6. GL: Atrium accounting core is a V1 screen. Beta core is a deepen page.

## Recipe → variance
1. Recipe and lines: **copied** (127 / 756 both sqlite files).
2. Theoretical cost: not evidenced as a maintained field this pass.
3. Actual consumption from ESB: night sales are a total, not a recipe depletion.
4. `recipe_compare` = 0. `venue_close_variance_policies` = 0.
5. COGS alert template points at Xero, which is absent.
**Middle missing:** actual vs theoretical.

## Content idea → publish → learn
1. Idea / demand / brief: V1 APIs. Beta hub only.
2. Brand card with cadence: six V1 boards. **Not** Content 2.0.
3. Comment → Amanda apply: V1. **Missing.**
4. Tick → Metricool draft → Misa queue: V1 machine routes. Metricool WRITE **off**. Misa desk not rebuilt.
5. Learn: `performance_records` 1,103 rows exist and engagement on the pulse is explicitly not invented. The next brief does not read them as a loop.
6. File to shoot: NAS 38,091 shallow vs library assets 48. **Middle missing:** the asset the brief points at.

## Issue → verify
1. Raise issue: Uma issues page. `bzg_ops_operator_issues` = **0**.
2. Assign: My Work 211 items, delegations **0**.
3. Evidence: 28 records. Not a verify step.
4. Close with proof: approvals **0**.
**Broken** at the first write.

## Month-end → shareholder
1. Flash and close screens: V1. Beta shells.
2. Bank match: Bank_Import CONFIGURED, cash screen not rebuilt. No bank feed (standing rule) so the job is a monthly file. The file workflow is still V1.
3. Payroll / service charge: HR boundary, distribution blocked. Do not “finish” this chain by skipping HR.
4. Pack export: V1 report modules. **Not proved on Beta.**
5. July and August HTML packs: on V1 disk only.
6. Intercompany and GGV books: Xero absent, notas 0.
**Broken** from close through pack.

## Cash chain (BZG)
Petty on V1 = 443 rows. Petty on Beta = 0 movements. Daily close = 0. This is the cash-theft control from ledger round 2, unread as a workflow.
