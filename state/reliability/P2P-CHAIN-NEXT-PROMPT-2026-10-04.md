# P2P-CHAIN-NEXT — one purchase order page

Workspace: `/Users/wolfterminal/beta-os` only. Beta only. No commit. No push. No merge. Do not clean the git tree. Do not print process command lines.

## The one step

The purchase-request page already exists at `/bzg/uma-blu/bills` (https://beta.wolfcommand.net/bzg/uma-blu/bills). Approval already exists as the segregated approve action on the request detail. There is no purchase-order record: `ORDERED` is only a request-state flip.

Build the next step only: a real Beta **purchase order** page that an authenticated person can save from an already **APPROVED** purchase request, reload, and see again. Do not build receiving, nota/bill, three-way match, AP, or ready-to-pay. Do not execute a bank payment.

## What already exists (reuse, do not rebuild)

- Request create/list: `scripts/core/bzg_purchase_request.py`, page `dashboards/bzg-uma-blu-bills.html`, routes `/bzg/uma-blu/bills` and `/api/bzg/uma-blu/prs`.
- Detail actions submit / approve / order / receive: `dashboards/bzg-uma-blu-pr.html`. Leave them working.
- Segregated approval: `approve_purchase_segregated` in `scripts/core/uma_devi_p0.py`. Requester cannot approve. Keep that.
- Request states in `scripts/core/uma_ops_console.py`. Legal step into this slice is `APPROVED` → `ORDERED` only, and only when a purchase order row is actually saved. Do not jump to `RECEIVED`, `BILL_RECEIVED`, or any `PAYMENT_*` / `PAID_CLAIMED` / `CLOSED` state.
- Real suppliers already served read-only from Alchemist by `scripts/core/uma_real_projection.py` `list_suppliers` and `GET /api/bzg/uma-blu/real/suppliers`. Use that list. Do not insert suppliers. Do not copy Alchemist into the catalog.
- Outlet registry `org_outlet_registry`. Uma Blu `BZG-UMA`, Rainforest `BZG-RAIN`, Pool Bar `OU-BZG-RAIN-POOL` are OPEN. Do not change outlet status. Do not hardcode Uma. Outlet on the order is the outlet already stored on the approved request.
- One legal entity: `ENT-BZG`. Do not add a second BZG bank or a payment path.

## Save rules

- Eligible source: one non-example `bzg_ops_purchase_requests` row whose `state` is `APPROVED`, with a non-null `outlet_id` that exists in `org_outlet_registry`, at least one existing line, and a requester person id.
- Refuse example rows (`example=1`). Refuse `PR-UMA-0E65E353A422` (already `RECEIVED`, `outlet_id` NULL). Do not backfill it. Do not invent a live approved request so the page looks full. If none are approved, the Beta page shows an honest empty state.
- Supplier must be an id returned by the existing read-only supplier projection at save time. Store that id and the name the projection returned. No free-text supplier. If the projection cannot be read, stop and write the result. Do not create a supplier.
- Lines are copied from that request's `bzg_ops_pr_lines` only (item, qty, unit). Qty may be equal or lower, never higher, never a new item name. Do not read or invent Rainforest or Pool Bar menus, recipes, or purchasing history. Do not copy historical Alchemist `pr_orders` into new order rows.
- Authenticated person with an active assignment. Do not hardcode a person name. The requester cannot turn their own request into an order unless a different person already approved it (state is already `APPROVED`). Do not let the requester approve. Keep separation of duties.
- Permission: reuse an existing assignment permission if one truly fits; otherwise add one small permission and grant it only to roles that already hold purchasing approval (`work.complete` holders), not by person name. No new role for a named human.
- Persist in the Beta catalog (new `bzg_ops_purchase_orders` / `bzg_ops_po_lines`, or the existing store if you find a real unused PO table — do not invent a second system of record if one exists). Idempotent migration. Audit the create.
- Saving the order may transition that request `APPROVED` → `ORDERED` through the existing transition helper. If the order save fails, do not leave the request `ORDERED`.
- Reload of the page and GET of the order return the same supplier id, outlet id, source request id, and lines.

## Page

- New staff page, linked from the existing bills page, not a replacement of the request form. Suggested route `/bzg/uma-blu/purchase-orders`.
- Shows saved orders and approved requests that do not yet have an order.
- Outlet display name comes from the registry.
- No GL, journals, account codes, or engineering labels on the page.
- Say clearly this is not a payment and not a goods receipt.
- `staff_ready` stays false. `human_commissioned` stays false. Do not mark HUMAN COMMISSIONED. Do not stamp PASS, READY, or ENG_PROVED.

## Hard locks

- Do not mutate `catalog/content_library.sqlite` rows:
  - `VDC-470e741f-d889-437a-9a40-1ec9c083fb95` (business date 2026-10-03, state EXCEPTION, declared_cash_amount 3225000, variance_cash_amount -125000, updated_at 2026-10-03T13:47:39Z)
  - `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` (state CANCELLED)
  - `VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5` (business date 2026-10-04, submitted_by_person_id PERS-IZA, taken_by_person_id PERS-MATT, declared_cash_amount stays NULL, do not edit esb_totals_json)
- Read catalog only with Python `sqlite3` `mode=ro` for checks. The sqlite3 CLI often fails. Tests use a temp sqlite. Never `shutil.copy2` the live catalog.
- Prod pid 1297 on 127.0.0.1:8787 is sacred. Do not signal it. Do not restart it.
- Beta pid at launch was 42936, the only listener on 127.0.0.1:8788. Reload Beta only if Python changed, and only when exactly one listener remains on 8788. HTML-only changes do not need a reload. After any reload, 8788 must still have exactly one listener and 1297 must still be the only listener on 8787. If the listener count is not exactly one, do not reload.
- Leave cursor pid 2627 in `/Users/wolfterminal/.openclaw/workspace/wolf-system` alone.
- No second writer. No `--trust`. No messaging Matt.

## Tests

Add a focused temp-sqlite test. Cover: unauthenticated denied, non-approved request denied, example row denied, missing outlet denied, supplier id not in the projection denied, line item not on the request denied, qty above the request denied, save then reload returns the same order, requester self-approval still denied, protected close ids untouched in the temp fixture, no payment state. Do not clone the live catalog.

## Result

Write `state/reliability/P2P-CHAIN-NEXT-RESULT-2026-10-04.json` with:

- pack_id `BZG-P2P-PO-1`
- status
- staff_ready false
- human_commissioned false
- eng_proved false
- routes
- tests_pass / tests_fail
- deployed_beta true only if the page is actually served on :8788
- protected_close_untouched
- no_prod true
- no_shutil_copy2_live_catalog true
- what was not built (receiving, nota, match, AP, ready to pay, payment)
- stop_reason null or a real blocker

`EXIT:0` when the result file is written and tests are recorded. `EXIT:1` if you changed a protected close, touched prod, or copied the live catalog.
