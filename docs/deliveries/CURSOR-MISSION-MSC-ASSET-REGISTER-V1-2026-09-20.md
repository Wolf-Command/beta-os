# CURSOR MISSION — CAP-MSC-01 Asset & Maintenance Register v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-MSC-ASSET-REGISTER-V1-2026-09-20.md`. `CR-7ea69933a9d39ba9` stays OPEN. Owner lane `msc-asset-register-v1` on mission `owner-autonomous-20260920-w6`, after `dr-crown-jewel-framework` DONE (`e40e7c7`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the asset register is on Beta `:8788`. A row is an id, a venue that already exists, a type, status `NOTED`, and a last-service note. The live register is empty. Empty is not an inventory count and not a payment. A location is not an asset. Not PROVEN. Not READY. `CAP-MSC-01` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-7ea69933a9d39ba9` stays **OPEN**.

## What landed

- `scripts/core/msc_asset_register.py` — Owner register. Schema `wolf.cap-msc-01.asset-register.v1` accepts only venue, type, status, and a last-service note. Venue must already exist on `org_locations`. Status must be `NOTED`. `inventory_count` stays null. The content-library media table is not read. `CR-7ea69933a9d39ba9` is read and not written.
- `scripts/serve_beta.py` — `GET /api/msc/assets`, `/schema`, `/venues`, `/register`, and `/<id>`, plus `GET /msc-assets` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /api/msc/assets/register` records one noted row for the Owner. `POST /payment` is `payment_refused`. `POST /inventory` is `inventory_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` is `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/msc-assets.html` — Owner page. It says an empty register is not an inventory count, a location is not an asset, and the page does not resolve the completion row.
- `scripts/tests/test_msc_asset_register.py` — empty register, refuse paths, ceiling, CR bind, WIP four.

No inventory count was stored. No payment was stored. No Production write. No Alchemist write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-7ea69933a9d39ba9` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Register`. This slice does not resolve the CR and does not write the ledger.

- `CAP-MSC-01` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `recorded_count` 0, `inventory_count` null, `payment` null, `service_proved` false, and `cr_resolved` false. One location on `org_locations` is not one asset.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented inventory count. No payment.

## Prove

`python3 scripts/tests/test_msc_asset_register.py` → `PASS=126 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `86629` (was `84149`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/msc/assets` → 403
- `curl http://127.0.0.1:8788/msc-assets` → 403
- Ledger `CAP-MSC-01` SPECIFIED, 77 rows. CR state OPEN. Live register file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
