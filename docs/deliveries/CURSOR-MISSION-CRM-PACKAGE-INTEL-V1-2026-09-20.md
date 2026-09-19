# CURSOR MISSION — CAP-CRM-03 Package Intelligence v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-CRM-PACKAGE-INTEL-V1-2026-09-20.md`. `CR-e5ff219bb1d585f7` next action is Implementation. Owner lane `crm-package-intel-v1`. Wave-6 after `intg-gws-integrate-prove` DONE (`3ac2f28`). `intel-learning-policy-v1` stays PARKED.

**Status:** the package register is on Beta `:8788`. The live register file is absent, so the register is empty. A brand is not a package. A price is not stored. No booking is changed. Not PROVEN. Not READY. `CAP-CRM-03` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-e5ff219bb1d585f7` stays **OPEN**.

## What landed

- `scripts/core/crm_package_intel.py` — Owner register. A row is name, an existing `org_brands` brand id, status `NAMED`, and evidence refs (`EV-…` or `docs/….md`). There is no price column. `market_package_count`, margin, and demand stay null. A missing register file is an empty list, not a market census. Machine-readable schema `wolf.cap-crm-03.package-register.v1`.
- `scripts/serve_beta.py` — `GET /api/crm/package-intel`, `/schema`, `/products`, `/brands`, and `/<id>`, plus `GET /crm-package-intel` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /api/crm/package-intel/register` records one evidenced row for the Owner. `POST /price` is `price_refused`. `POST /booking` is `booking_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` is `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/crm-package-intel.html` — Owner page. It says an empty register is not a price, no booking is changed, and the page does not resolve the completion row.
- `scripts/tests/test_crm_package_intel.py` — empty register, refuse paths, ceiling, CR bind, WIP four.

No package was seeded into the live register. `catalog/crm_package_intel.sqlite` is absent. No booking file was written. No price was stored.

## Honesty (bound to the CR)

`CR-e5ff219bb1d585f7` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Implementation`. This slice does not resolve the CR and does not write the ledger.

- `CAP-CRM-03` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `empty` true, `recorded_count` 0, `market_package_count` null, `price` null, `pricing_is_truth` false, and `booking_mutated` false. Zero recorded rows is the register, not a count of packages in the market.
- Brands read from `org_brands` are listed with `package` null. Habitat and Uma Blu are not turned into products.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No live booking mutation.

## Prove

`python3 scripts/tests/test_crm_package_intel.py` → `PASS=137 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `81754` (was `78495`).
- `curl http://127.0.0.1:8788/api/crm/package-intel` → 403
- `curl http://127.0.0.1:8788/crm-package-intel` → 403
- Ledger `CAP-CRM-03` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
