# Operationalisation first pass

28 Sep 2026. Read-only. Live Beta on port 8788 was not restarted. Unsigned pages there still return 403. Seats were opened through a short-lived signed handler, the same way the staff access tests sign in. Nothing was submitted. Nobody is staff-ready. Nobody is commissioned.

Screenshots: `docs/wolf/ops/shots/opsaudit-*.png`. Rows: `state/ops/testability-matrix.json` and `state/ops/route-audit.json`.

## A. What people can use right now

- Content Library — Haikal, Misa, Zarah, and Frail, including Atrium. Yudi, Gery, Alam, TJ, Nata, and Rapp on Habitat, Selo, Tropik, and The One.
- Content Plan and Upload — those same content seats. Approve stays with the Creative Directors.
- My Work — every seated person can open it. Today is empty on purpose.
- GGV Finance — Amanda, and Owner. Sign-in for Amanda still lands on Content. Finance is the second seat.
- Atrium Finance at `/amg/finance` — Zayen, and Owner. Zayen is refused everywhere else with a normal denial page.
- Uma Blu Today and the bills form — Devi, and Owner. The lists are empty.
- Owner command, war room, needs-you, and progress — Matthew Goss.

## B. Broken boards and links

1. Owner is refused `/amg/finance/lite` (403) and allowed `/amg/finance` (200).
2. Content Plan overflows at 390px. Library at that width fits.
3. Progress overflows at 390px and clips the owner role chip.
4. Atrium Command Centre shows a Live chip while the page says the property profile is not set and the figures are not hotel history.
5. The Atrium operations desk still has an empty Finance slot. The product is already at `/amg/finance`.
6. Lead Spine is labelled demo data. It must not be treated as the pipeline.

Twenty-three business-nav slots have no destination (BZG, Uma, GGV, Atrium, Intelligence, and Factory / Health). They are empty on purpose. Favicon requests 404. That is not a staff link.

## C. Systems that can be mounted

| System | Where it lives | Effort |
| --- | --- | --- |
| Uma recipe book | Production `dashboards/uma-blu-recipes.html` and `uma-blu/recipes.sqlite` | M |
| Shareholder monthly HTML | Production `bzg-shareholder-reports.html` and `WolfCommandSystem` reports through August 2026 | M |
| Atrium Finance product | Already mounted from `~/atrium-finance` | S to point the empty Atrium nav slot at it |
| Alchemist purchase book | `alchemist/data/alchemist.db` | L |
| ESB sales warehouse | `~/.openclaw/data/esb.sqlite` | M to read it onto Uma Today |

`~/wolf-phase2` is an old snapshot, not a product to mount.

## D. Real data that is not on the board

- Nine Habitat content plans. My Work has no work items.
- NAS library, 63,370 indexed files. This one is wired. Atrium alone is 32,692.
- Atrium chart of accounts. Posted journals are still zero.
- GGV invoice sequence sitting at 067A. Invoices 064A, 065A, and 066A are not in the catalog.
- ESB sales through 27 Sep 2026. Uma Today does not show them.
- Alchemist purchase requests, suppliers, and nota photos. Uma bills says there are no requests. The three example rows in Beta are hidden.
- Recipe cards and costs on the production recipe book.
- Shareholder HTML through August 2026.

## E. Give this to a human now

1. Library pages — Haikal. Open Content, Library, brand Atrium. Confirm the page count, open page 2, open one preview, download one file he already knows. Do not upload.
2. Empty Today — Yudi. Sign in, land on Content, open My Work. It should name Content Creator and say nothing is assigned. Leave it empty.
3. Atrium full product — Zayen. Sign in and land on Atrium Finance. Read Command Centre, Ledger, and one report. Confirm the property warning. Do not approve, post, or pay. Try one GGV page and expect the denial page.
4. GGV invoices — Amanda. From Content, open GGV Finance, then Invoices. Confirm the list is empty and the next number is not something she types. Do not issue 067A unless Matt asks for a real invoice.
5. Uma bills — Devi. Open Uma Blu, then Bills. If her real requests are missing, that is a fail of the data, not of her. Do not save a draft.

## F. Repair packs

1. **Uma operating day.** Read ESB into Today and the Alchemist request book into Bills. Do not copy nota photos into the repo. Files: Uma read adapters and the Uma boards. Collision: the Uma rebuild already owns `scripts/serve_beta.py`, `dashboards/`, and Uma code. Do this pack only with that work, or after it stops.

2. **Content desk the staff can finish.** Stop the plan header overflowing at 390px. Assign one stored Habitat plan onto a Creative Director work item so My Work is no longer blank. Leave creator brand scope as it is. Files: content page and the work-item assignment. Collision: low, unless the Uma rebuild is editing the content page in `dashboards/`.

3. **Finance retest.** Zayen retests `/amg/finance` after the property profile is set and the Live chip matches that fact. Owner either can open `/amg/finance/lite` or the link is removed. Amanda's empty invoice list stays until Owner imports 064A–066A. Files: the Atrium sidecar, the lite guard in Beta, and the GGV invoice import. Collision: the lite guard is in `scripts/serve_beta.py`, which the Uma rebuild owns. The sidecar is not.

4. **Recipe book and shareholder read.** Mount the production recipe reader for Devi. Mount the existing monthly HTML for Owner only, with send left off, and only after Matt names the readers. Etik and Scott are not seats. Files: new Beta routes plus the production pages. Collision: new routes touch `scripts/serve_beta.py`.

Do not seat a closer, an accountant, a video editor, or an HR person until a real name is given.
