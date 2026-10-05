# P2P V1 Archaeology — 2026-10-03

Scope followed: read-only archaeology only, no Finance implementation, no Beta/Prod restart, no commit.

## 1) Verdict: does a working Uma Blu V1 purchasing workflow exist on this Mac?

Yes, a **partial working chain** exists in Beta catalog + service code for:
- PR creation
- Segregated approval (requester cannot self-approve)
- Receiving with receipt evidence
- Petty movement
- Daily-close card visibility

Evidence points:
- `scripts/core/uma_ops_console.py` functions: `create_pr`, `goods_receipt`, `record_petty_ops`, `today_cards`
- `scripts/core/uma_devi_p0.py` functions: `approve_purchase_segregated`, `ops_advance`
- `scripts/core/venue_close.py` functions: `open_or_get`, `capture_esb_snapshot`
- `catalog/content_library.sqlite` live rows:
  - `bzg_ops_purchase_requests`: 4 (1 real + 3 example)
  - `bzg_ops_pr_lines`: 15
  - `core_approval_requests`: 1
  - `bzg_ops_receipt_events`: 1
  - `bzg_ops_receipt_lines`: 15

Not a full Procure-to-Pay implementation yet (details by stage below).

## 2) Historical sources directly visible now (counts + paths)

## 2.1 Beta catalog (local)
- Path: `/Users/wolfterminal/beta-os/catalog/content_library.sqlite`
- P2P-relevant counts read now:
  - `bzg_ops_purchase_requests`: 4
  - `bzg_ops_pr_lines`: 15
  - `bzg_ops_receipt_events`: 1
  - `bzg_ops_receipt_lines`: 15
  - `core_approval_requests`: 1
  - `core_approval_decisions`: 10
  - `bzg_ops_petty_movements`: 11
  - `venue_daily_closes`: 4
  - `bzg_shared_vendors`: 0
  - `org_outlet_registry`: 7
  - `ggv_notas`: 0
  - `ggv_nota_files`: 0
  - `ggv_nota_history`: 0
  - `ggv_invoices`: 0
  - `ggv_invoice_history`: 0
  - `ggv_invoice_documents`: 0
  - `ggv_bank_statement_imports`: 2
  - `ggv_bank_transactions`: 6

## 2.2 Alchemist sqlite (external historical/ops source)
- Path: `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
- Counts read now:
  - `suppliers`: 103
  - `pr_orders`: 543
  - `pr_order_lines`: 2017
  - `pr_receipt_lines`: 477
  - `ledger`: 473
  - `petty_cash`: 443
  - `par_levels`: 9
  - `deliveries`: 0
  - `item_prices`: 0
  - `unit_map`: 0
- Notas directory:
  - Path: `/Users/wolfterminal/.openclaw/workspace/alchemist/notas`
  - `*.jpg` count read now: 462

## 2.3 wolf-system sqlite paths (visible subset)
- Path: `/Users/wolfterminal/.openclaw/workspace/wolf-system/uma-blu/recipes.sqlite`
  - `recipes`: 127
  - `recipe_lines`: 756
  - `recipe_compare`: 0
- Path: `/Users/wolfterminal/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite`
  - Present and queryable; key table counts now:
    - `purchase_request`: 1
    - `purchase_order`: 0
    - `goods_receipt`: 0
    - `ap_invoice`: 0
    - `ap_invoice_line`: 0
    - `payment_run`: 0
    - `payment_line`: 0
    - `vendor`: 0
    - `vendor_bank_account`: 0
    - `bank_account`: 0
    - `item_master`: 0
    - `store_location`: 0
    - `match_exception`: 0
    - `journal_header`: 64
    - `journal_line`: 126
- ESB sqlite at previously referenced wolf-system candidate paths:
  - Checked and missing at:
    - `/Users/wolfterminal/.openclaw/workspace/wolf-system/esb.sqlite`
    - `/Users/wolfterminal/.openclaw/workspace/wolf-system/warehouse/esb.sqlite`
    - `/Users/wolfterminal/.openclaw/workspace/wolf-system/data/esb.sqlite`
    - `/Users/wolfterminal/.openclaw/workspace/esb.sqlite`
  - `UNKNOWN` for current actual ESB sqlite path in this run.

## 2.4 Beta history/report artifacts read now
- `state/final-completion/forensic-completeness-20261001/PACK-02-UMA-BUY-CLOSE-RESULT.md`
- `state/historical-recon/HIST-RECON-BZG-UMA-20261002/RECONCILIATION.md`
- `state/historical-recon/HIST-RECON-BZG-UMA-20261002/RECONCILIATION.json`
- `docs/wolf/bzg/UMA-BLU-DATA-SOURCE-REGISTER.md`
- `docs/wolf/bzg/UMA-BLU-BZG-RECONCILIATION.md`

These documents are discoverable and readable now; some counts inside them differ from live recounts above (normal drift over time).

## 3) Function-by-function P2P map (requested stages)

Status legend:
- `WORKING`: verified function + data path exists
- `PARTIAL`: function exists but not full business completion
- `UNKNOWN`: source/path for this stage not visible in this run
- `MISSING`: no stage-specific implementation found

1) PR
- `WORKING`
- Code: `scripts/core/uma_ops_console.py` → `create_pr`
- Data: `bzg_ops_purchase_requests`, `bzg_ops_pr_lines`

2) Approval
- `WORKING` (segregation proven in implementation/test history)
- Code: `scripts/core/uma_devi_p0.py` → `approve_purchase_segregated`, `ops_advance`
- Guard evidence in code: `self_approval_denied`; permission basis `work.complete`
- Data: `core_approval_requests`, `core_approval_decisions`

3) PO (purchase order)
- `PARTIAL`
- In Beta ops flow, PR states move through ordered/received semantics, but no dedicated Beta `purchase_order` table found.
- Historical source exists in Alchemist as `pr_orders` (543 rows), but that is external source.

4) Receiving
- `WORKING` (Beta receive event/lines path exists)
- Code: `scripts/core/uma_ops_console.py` → `goods_receipt`
- Data: `bzg_ops_receipt_events` (1), `bzg_ops_receipt_lines` (15)
- External historical receiving source: Alchemist `pr_receipt_lines` (477)

5) Nota/Bill
- `PARTIAL`
- Alchemist bill-like ledger exists: `ledger` (473)
- Beta GGV Nota module exists (`scripts/core/ggv_finance_nota.py` functions like `save_nota`, `submit_nota`, `review_nota`) but Beta nota tables currently have 0 rows.
- Therefore structure exists, active Uma P2P nota flow in Beta is not evidenced in this recount.

6) Three-way match
- `MISSING` in active Beta Uma flow
- Atrium finance schema has `match_exception` table, but current count is 0.
- No verified live Uma three-way match execution path found in this run.

7) AP (accounts payable)
- `PARTIAL`
- Atrium finance has AP schema (`ap_invoice`, `ap_invoice_line`) but both 0 rows.
- Beta has no active Uma AP posting evidence in catalog recount.

8) Ready to pay
- `UNKNOWN`
- No explicit ready-to-pay queue/table found in Beta catalog or atrium tables queried by name.

9) Payment
- `PARTIAL`
- Atrium schema exists: `payment_run`, `payment_line` (both 0 rows).
- Beta has payment-adjacent permissions and bank statement imports, but no proven Uma AP payment run in recount.

10) Bank allocation
- `PARTIAL/UNKNOWN`
- Atrium has `ar_receipt_allocation` table name present; AP-specific bank allocation path not proven here.
- Beta has `ggv_bank_statement_imports` (2) and `ggv_bank_transactions` (6), and code `scripts/core/ggv_bank_statement1.py` states propose-only matching, no auto-reconcile.

11) GL
- `PARTIAL`
- Atrium GL-like journaling evidence exists: `journal_header` 64, `journal_line` 126.
- Uma-specific PR→AP→payment posting to GL not proven in this run.

## 4) Supplier master, ingredient/item master, outlet model, permissions

## 4.1 Supplier master
- External primary source evidenced: Alchemist `suppliers` (103) at `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db`
- Beta local vendor tables:
  - `bzg_shared_vendors`: 0
  - `ggv_vendors`: 0
  - `ggv_vendor_bank_observed`: 0
- Conclusion: supplier master is externally sourced (Alchemist) in practice; Beta vendor master not populated.

## 4.2 Ingredient/item master
- `recipes.sqlite` at wolf-system path provides recipe + ingredient line coverage (`recipes` 127, `recipe_lines` 756).
- Atrium `item_master` exists but 0 rows.
- Alchemist purchasing item detail exists in `pr_order_lines` and `pr_vendor_items` (table exists; counts reflected in history docs, not recounted directly this run except table presence).
- Conclusion: item truth is fragmented across recipe/alchemist artifacts; no single populated Beta item master found.

## 4.3 Outlet model
- Beta outlet registry in catalog: `org_outlet_registry` count 7.
- Includes `BZG-UMA` row as `OPEN` and additional pre-opening brands/units.
- Core code uses `VENUE_UMA = "BZG-UMA"` and `ENTITY_BZG = "ENT-BZG"` in `scripts/core/uma_ops_console.py`.

## 4.4 Permissions / segregation
- RBAC evaluator lives in `scripts/core/rbac.py`.
- Permission codes active in catalog include:
  - `work.create`, `work.update`, `work.complete`
  - `venue.receive`, `venue.close.submit`
  - `approval.decide`, `finance.nota.edit`, `payment.approve`
- Active assignment snapshot queried:
  - `PERS-DEVI`: `ROLE-BZG-FB-OPS-LEAD`, `ROLE-BZG-CLOSER` (brand `BZG-UMA`)
  - `PERS-MATT`: `ROLE-MATT`, `ROLE-GGV-FINANCIAL-CONTROLLER`
- Segregation path is implemented in code (`self_approval_denied`) and aligns with role-based permission checks.

## 5) Non-collision guard against frozen Finance checkpoint

Requested reference file:
- `/Users/wolfterminal/beta-os/state/reliability/FINANCE-CHECKPOINT-FREEZE-2026-10-03.json`

Observed content:
- File contains run metadata (`head`, `branch`, `dirty_count`, `classification`, etc.).
- It does **not** list a file-by-file freeze manifest.

Therefore:
- Exact “frozen Finance files listed in ...json” = `UNKNOWN` (no file list present in that JSON).
- Closest explicit touched-file hints are in:
  - `/Users/wolfterminal/beta-os/state/reliability/FINANCE-CONTROL-CHECKPOINT-2026-10-03.md`
  - which names `scripts/core/venue_close.py`, `scripts/core/bzg_daily_close.py`, `scripts/core/ggv_receipt_intake_ro.py`, `scripts/core/ggv_bank_statement1.py`, `scripts/core/ggv_finance_nota.py`, `scripts/serve_beta.py`, `dashboards/uma-blu-close.html`, `dashboards/ggv-finance.html`.

Practical non-collision rule for future implementation worker:
- Treat the above checkpoint-mentioned files as freeze-sensitive unless Owner explicitly re-opens them.
- Build P2P discovery outputs into separate modules/routes first, then integrate deliberately.

## 6) Direct unknowns (explicit)

- Current ESB sqlite location on this Mac in this run: `UNKNOWN` (candidate wolf-system paths were missing).
- A proven end-to-end Uma three-way match execution path: `UNKNOWN/MISSING`.
- A proven ready-to-pay queue implementation for Uma in Beta: `UNKNOWN`.
- AP payment posting path from Uma PR/receiving into populated AP tables: `UNKNOWN/PARTIAL` (schema exists elsewhere, rows mostly zero).
- Exact freeze file list from `FINANCE-CHECKPOINT-FREEZE-2026-10-03.json`: `UNKNOWN` (not present in JSON).

