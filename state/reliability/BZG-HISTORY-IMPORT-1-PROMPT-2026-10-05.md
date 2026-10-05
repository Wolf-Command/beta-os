# BZG-HISTORY-IMPORT-1

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar.

Read first: `state/reliability/BZG-HISTORY-REGISTER-2026-10-05.json`. Those counts were read from disk. Re-count before you write. If a count moved, use the new count and say so. Do not treat the 29 Sep snapshot (514 / 1883 / 435 / 433) as canonical.

## Do not

- Do not kill or restart other workers. Production pid 1297 on 127.0.0.1:8787 is sacred. Do not restart it.
- Do not commit, push, merge, or clean the dirty tree.
- Do not mutate protected closes: VDC-470e741f (3 Oct EXCEPTION, declared_cash_amount 3225000, variance_cash_amount -125000, updated_at 2026-10-03T13:47:39Z), VDC-87202768 CANCELLED, VDC-64f5f529 (4 Oct DATA_CAPTURED, declared_cash_amount NULL).
- Do not duplicate Iza rows PETTY-UMA-6E512800FE Rp430,000 and PETTY-UMA-80867C2504 Rp21,000.
- Do not overwrite the live Uma petty balance. Proved formula: petty day 2026-10-02 opening_float 56000 plus movements dated on or after 2026-10-02 = Rp52,700. Do not insert Rp2,300. Do not force Rp55,000.
- Do not invent missing values, workflow events, links, menus, or reconciliation. UNKNOWN stays UNKNOWN.
- Do not open credential files. Do not scrape new secrets.
- sqlite3 CLI often fails. Use Python `mode=ro` for reads. Do not copy the full content_library.sqlite for tests. Minimal fixtures only.
- Do not hardcode people. PERSON → ASSIGNMENT → ROLE → SCOPE → PERMISSION.
- One legal entity ENT-BZG. Outlets are views: Uma Blu, Blu Zone Restaurant & Bar / Rainforest, Pool Bar, Merah, Rooftop, Room Service, Catering. Do not invent Rainforest or Pool Bar menus or procurement history.
- staff_ready=false. Do not mark a human commissioned. Do not call Zayen ready unless the tests below pass.
- No money movement. No bank payment.

## Import

Import authorised historical BZG / Uma Blu records into the canonical Beta models the new P2P already uses:

- `bzg_ops_purchase_orders`, `bzg_ops_po_lines`
- `bzg_ops_goods_receipts`, `bzg_ops_gr_lines` (and the existing receipt event tables only if that is the same canonical receipt)
- `bzg_ops_supplier_bills`, `bzg_ops_bill_lines`
- `bzg_ops_ap_ready` only when a real unpaid ledger row is imported, not as a fake queue
- `bzg_ops_petty_movements` for historical petty that is not already present

Source of purchasing truth: `/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db` (`pr_orders` 543, `pr_order_lines` 2017, `pr_receipt_lines` 477, `ledger` 473, `petty_cash` 443, `suppliers` 103 at the register read).

Mark rows **MIGRATED HISTORICAL** where modern workflow state cannot be reconstructed. Preserve original ids, source system, timestamps, business date, supplier, outlet, amount, status, creator, approver, relationships, evidence refs, and migration provenance.

Skip rows already present. Match on original id + source system so the live petty rows are not duplicated. The 4 existing purchase requests (3 examples + PR-UMA-0E65E353A422) stay. Do not delete examples.

Receipt lines have no date column. Do not invent a receipt date. Store the parent order date only as the parent date, and leave the receipt business date UNKNOWN if it is not on the row.

`deliveries` is empty. Do not invent delivery headers from photos.

## Links

Link PR → PO → lines → receiving → nota/bill → AP → payment → bank → ledger only with a deterministic key.

Already proved inside Alchemist: 464 `pr_orders.linked_payment` values match `ledger.id` as `L-{id}`. You may record that link. You may not invent any other link.

If the key is not deterministic, status **NEEDS RECONCILIATION**. Bake House is two supplier ids (5 and 90). Do not merge them.

Petty fingerprint duplicates (33 groups, 36 extra rows) stay as separate source rows. Do not collapse them.

## Evidence

Possessed files:

- `/Users/wolfterminal/.openclaw/workspace/alchemist/notas` — 462 jpg (382 petty_, 78 topup_, 2 nota_)
- `/Users/wolfterminal/.openclaw/workspace/alchemist/media/receive` — 497 jpg
- `/Users/wolfterminal/.openclaw/workspace/alchemist/media/nightly` — 404 jpg
- `/Users/wolfterminal/beta-os/state/uma-petty-receipts` — 16 jpg already linked to live petty

If a file is possessed and the row points at that exact path or filename, link it. If it cannot be tied to one row, keep it and set **EVIDENCE UNLINKED** on a reconciliation queue. Do not drop it. Drive http links are refs, not possessed files.

## Bank

Inventory every authorised historical BZG statement already on disk under `/Users/wolfterminal/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/BZG` (15 files, Mar–Aug 2026). Import raw and normalized only where the parse is safe. States: MATCHED / POSSIBLE MATCH / UNMATCHED / EXCEPTION. Do not manufacture a reconciliation. Sep and Oct 2026 are absent. GGV bank rows already in Beta are not BZG. Transaction counts in the register are UNKNOWN until you parse; do not copy a guessed count.

## Display

Entity switcher at the top of Finance Core, driven by assignment + scope, not by a hardcoded name list.

- Zayen (PERS-ZAYEN, ASG-ZAYEN-FC-1 / ASG-ZAYEN-AR-1 scope AMG, ASG-ZAYEN-BZG-FC-1 scope BZG) sees AMG/Atrium and BZG, never GGV.
- Matt sees GGV, AMG, and BZG.
- Amanda sees GGV only.

Switching business changes dashboard, banking, transactions, bills, suppliers, procurement, petty, reconciliation, reports, exceptions, and audit. No cross-entity leakage. Inside BZG, an outlet filter includes consolidated BZG. Not seven accounting systems.

Owner completeness view: each dataset COMPLETE or GAP. Clicking GAP shows what is missing (source count, beta count, date span, unresolved). No fake 100%.

## Tests

Use several REAL historical rows already in Alchemist (real pr_num, real ledger id, real petty id). No fabricated rows.

Prove:

- GGV is denied for the Zayen assignment.
- AMG ↔ BZG switch changes the books and does not leak the other entity.
- Imported PO, receipt, nota, and petty counts match a fresh source recount minus rows skipped as already present.
- Live petty balance is still Rp52,700 unless a real historical row was missing and was added as a new immutable migrated row. If the balance changes, report the new balance and the new movement ids. It must not change because of a duplicate or a plug figure.
- Protected closes unchanged (same ids, states, cash, variance, updated_at).
- Prod pid 1297 still the listener on 8787.

Reload Beta on 8788 only if Python changed and exactly one listener is on 8788.

Do not call Zayen ready unless real POs, receipts, notas, petty history, evidence links where files exist, the bank inventory, and the switcher tests pass.

Write the result to `state/reliability/BZG-HISTORY-IMPORT-1-RESULT-2026-10-05.json` with source, imported, skipped, linked, needs_reconciliation, evidence_unlinked, petty balance before and after, and protected-close checksums.
