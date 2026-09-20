# CURSOR MISSION — CAP-AMG-03 Packages as Products skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-AMG-PACKAGES-PRODUCTS-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `amg-packages-products-v1` on mission `owner-autonomous-20260920-w9`, after `amg-daily-ops-state-v1` DONE (`d917607` / `3c217c2`). `CR-f346ff7449a0bd5f` stays OPEN.

**Status:** the packages-as-products skeleton is on Beta `:8788`. It names stay, activity, stay+activity, margin, sop, and notes slots and leaves every slot empty. An empty framework is not a live package catalog and not proof of commercial package products. Live packages, sold counts, and margin IDR are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-AMG-03` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-f346ff7449a0bd5f` stays **OPEN**. Bound `beta-amg-ops-safe`.

## What landed

- `scripts/core/amg_packages_products.py` — Owner read of the skeleton. Schema `wolf.cap-amg-03.packages-products.v1` names the six slots and accepts no writes. `packages`, `sold_count`, and `margin_idr` stay null. `yanolja_live`, `live_catalog`, `live_packages`, and `commercial_products` stay false. No framework file is created. `CR-f346ff7449a0bd5f` is read and not written.
- `scripts/serve_beta.py` — `GET /api/amg/packages-products`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /amg-packages-products` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /yanolja` is `yanolja_refused`. `POST /sold`, `POST /packages`, `POST /current`, and `POST /margin` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, `POST /notes`, and `POST /stay` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/amg-packages-products.html` — Owner page. It says an empty framework is not a live package catalog and not proof of commercial package products, not PROVEN, not READY, CAP-AMG-03 stays SPECIFIED, the ceiling label is BUILT, no invented live packages, sold counts, or margin, no Yanolja call, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_amg_packages_products.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-amg-packages-products-v1-20260920`.

No live packages, sold counts, margin IDR, or Yanolja package state was stored. No Yanolja call. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The daily-ops and journey-workflow modules were not edited.

## Honesty (bound to the CR)

`CR-f346ff7449a0bd5f` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Package product machinery`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-AMG-03` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_catalog` false, `empty_is_products` false, `live_catalog` false, `commercial_products` false, `packages` null, `sold_count` null, `margin_idr` null, `yanolja_live` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented live packages, sold counts, or margin. No payment. No Yanolja call. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_amg_packages_products.py` → `PASS=250 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `20842` (was `16856`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/amg/packages-products` → 403
- `curl http://127.0.0.1:8788/amg-packages-products` → 403
- Ledger `CAP-AMG-03` SPECIFIED, 77 rows. CR state OPEN, next action `Package product machinery`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
