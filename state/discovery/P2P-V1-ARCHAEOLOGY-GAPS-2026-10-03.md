# P2P V1 Archaeology Gaps Closure — 2026-10-03

Scope honored: discovery only; no implementation; no service restarts; no edits outside `state/discovery/`.

Resolved targets: section 6 UNKNOWN items (1) through (4) only.

## 1) Current ESB sqlite location

Verdict: `FOUND`

- Current path: `/Users/wolfterminal/.openclaw/data/esb.sqlite`
- Existence check: `exists=True`
- Size check: `70602752` bytes

Counts queried from this file:
- `sales`: `9044`
- `products`: `426`
- `menus`: `188`
- `material_usage`: `19433`
- `goods_receipts`: `0`
- `gl_journal`: `5998`
- `salesPayments`: `ERROR (table not present under this exact name)`

Paths checked while closing this item:
- `/Users/wolfterminal/.openclaw/data/esb.sqlite` (opened and queried)
- `/Users/wolfterminal/beta-os/scripts/core/esb_close_snapshot.py` (read default path constant)
- `/Users/wolfterminal/beta-os/state/bzg-daily-close/FORENSIC-ESB-RECON-20261002.json` (warehouse path reference)
- `/Users/wolfterminal/beta-os/state/historical-recon/HIST-RECON-BZG-UMA-20261002/RECONCILIATION.json` (warehouse path reference)
- Filesystem scans run over:
  - `/Users/wolfterminal/beta-os` for `*.sqlite`
  - `/Users/wolfterminal/.openclaw/workspace` for `*.sqlite`

## 2) Any Uma three-way match execution path

Verdict: `MISSING` (Uma-specific path in Beta)

Evidence:
- In Beta Uma ops path, only receiving path is present:
  - `/Users/wolfterminal/beta-os/scripts/core/uma_ops_console.py` (`goods_receipt` found; no `ap_invoice`/`purchase_order`/`match_exception`/`payment_run` references in this file).
- No three-way/match execution strings found in `/Users/wolfterminal/beta-os/scripts` for Uma flow terms.

Closest non-Uma execution path found on disk (not a Beta Uma path):
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/atrium_finance.py`
  - `action_match(...)` updates `ap_invoice.match_status` and inserts into `match_exception`
  - `action_record_grn(...)` inserts `goods_receipt` + `goods_receipt_line`

Counts queried supporting this verdict:
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite`
  - `ap_invoice`: `0`
  - `goods_receipt`: `0`
  - `goods_receipt_line`: `0`
  - `match_exception`: `0`
  - `purchase_order`: `0`
  - `payment_run`: `0`

## 3) Ready-to-pay queue for Uma in Beta or on-disk historical source

Verdict:
- Beta Uma queue: `MISSING`
- On-disk historical source: `FOUND` (Alchemist payment-run source, not a Beta queue table)

Evidence for Beta `MISSING`:
- No `ready_to_pay` / `ready-to-pay` / `ready for payment` string hits in:
  - `/Users/wolfterminal/beta-os/scripts`
  - `/Users/wolfterminal/.openclaw/workspace` (searched `*.py`, `*.md`, `*.json`)
- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite` has no ready-to-pay table by name pattern.

Historical source found:
- `/Users/wolfterminal/.openclaw/workspace/alchemist/payment_run.py`
  - Reads unpaid ledger rows and composes "to pay" vs held-back list for Monday payment run.
- Backing DB: `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
  - `ledger_unpaid_total`: `106`
  - `ledger_unpaid_not_hold`: `106`
  - `ledger_unpaid_hold`: `0`

Related table-name scans and counts:
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
  - `pr_receipt_lines`: `477`
  - `purchase_requests`: `2`
- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite`
  - `content_misa_queue`: `1` (queue exists but not "ready-to-pay" semantics for Uma AP)

## 4) AP payment posting from Uma PR/receiving into populated AP tables

Verdict: `MISSING` (for populated AP tables)

Evidence:
- No Uma AP posting bridge found in Beta Uma ops code:
  - `/Users/wolfterminal/beta-os/scripts/core/uma_ops_console.py` has `goods_receipt` but no AP table posting path references.
- AP table populations remain zero in Atrium finance DB:
  - `/Users/wolfterminal/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite`
    - `ap_invoice`: `0`
    - `ap_invoice_line`: `0`
    - `payment_run`: `0`
    - `payment_line`: `0`
    - `purchase_order`: `0`
    - `goods_receipt`: `0`
    - `goods_receipt_line`: `0`

Historical linkage signal (not AP-table posting):
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
  - `pr_orders_total`: `543`
  - `pr_orders_with_linked_payment`: `464`
  - This indicates legacy linkage text/field in Alchemist, but not posting into populated Atrium AP tables.

## Paths opened in this closure run

Files read directly:
- `/Users/wolfterminal/beta-os/state/discovery/P2P-V1-ARCHAEOLOGY-2026-10-03.md`
- `/Users/wolfterminal/beta-os/scripts/core/esb_close_snapshot.py`
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/atrium_finance.py`
- `/Users/wolfterminal/.openclaw/workspace/alchemist/payment_run.py`
- `/Users/wolfterminal/beta-os/state/bzg-daily-close/FORENSIC-ESB-RECON-20261002.json` (via search hit)
- `/Users/wolfterminal/beta-os/state/historical-recon/HIST-RECON-BZG-UMA-20261002/RECONCILIATION.json` (via search hit)

SQLite files opened and queried:
- `/Users/wolfterminal/.openclaw/data/esb.sqlite`
- `/Users/wolfterminal/beta-os/catalog/content_library.sqlite`
- `/Users/wolfterminal/beta-os/catalog/atrium-bzg.sqlite`
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite`
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
- `/Users/wolfterminal/.openclaw/workspace/alchemist/alchemist.db`
- `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist_outbox.db`
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/ggv-finance/money.sqlite`

Filesystem paths scanned for candidate DBs/files:
- `/Users/wolfterminal/beta-os`
- `/Users/wolfterminal/.openclaw/workspace`
