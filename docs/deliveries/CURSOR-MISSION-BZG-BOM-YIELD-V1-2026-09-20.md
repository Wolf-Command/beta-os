# CURSOR MISSION — CAP-BZG-06 Recipe / Cost Standards (BOM/yield) skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-BZG-BOM-YIELD-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `bzg-bom-yield-v1` on mission `owner-autonomous-20260920-w10`, after `bzg-allocation-engine-v1` DONE (`62f4eca` / `5006d1d`). `CR-bbabeb11ff864169` stays OPEN.

**Status:** the BOM / yield / theoretical-cost / menu-engineering framework skeleton is on Beta `:8788`. It names bom, yield, waste, theoretical_cost, menu_engineering, and notes slots and leaves every slot empty. An empty framework is not live BOM/yield machinery and not proof of recipe cost standards. BOM, yield, waste, theoretical cost, and menu-engineering numbers are not recorded. ESB remains transactional SoT (read-only note only; no ESB mutate). Not PROVEN. Not READY. The live ledger row for `CAP-BZG-06` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-bbabeb11ff864169` stays **OPEN**. Bound `beta-bzg-ops-safe`.

## What landed

- `scripts/core/bzg_bom_yield.py` — Owner read of the skeleton. Schema `wolf.cap-bzg-06.bom-yield.v1` names the six slots and accepts no writes. `bom`, `yield`, `waste`, `theoretical_cost`, and `menu_engineering` stay null. `live_bom_yield_machinery` and `recipe_cost_standards` stay false. `esb_mutated` stays false. No framework file is created. `CR-bbabeb11ff864169` is read and not written.
- `scripts/serve_beta.py` — `GET /api/bzg/bom-yield`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /bzg-bom-yield` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /esb` is `esb_refused`. `POST /bom`, `POST /yield`, `POST /waste`, `POST /theoretical_cost`, `POST /menu_engineering`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/bzg-bom-yield.html` — Owner page. It says an empty framework is not live BOM/yield machinery and not proof of recipe cost standards, not PROVEN, not READY, CAP-BZG-06 stays SPECIFIED, the ceiling label is BUILT, no invented BOM, yield, waste, theoretical cost, or menu engineering, ESB remains transactional SoT with no ESB mutate, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_bzg_bom_yield.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-bzg-bom-yield-v1-20260920`.

No BOM, yield, waste, theoretical cost, or menu-engineering number was stored. No payment was executed. No bank write. No Zayen or books write. No ESB mutate. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The allocation-engine, variance/waste, venue P&L, and reputation modules were not edited.

## Honesty (bound to the CR)

`CR-bbabeb11ff864169` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `BOM/yield machinery`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-BZG-06` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_bom_yield_machinery` false, `empty_is_recipe_cost_standards` false, `live_bom_yield_machinery` false, `recipe_cost_standards` false, `bom` null, `yield` null, `waste` null, `theoretical_cost` null, `menu_engineering` null, `esb_mutated` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented BOM/yield numbers. No payment. No ESB mutate. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_bzg_bom_yield.py` → `PASS=272 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `42637` (was `38597`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/bzg/bom-yield` → 403
- `curl http://127.0.0.1:8788/bzg-bom-yield` → 403
- Ledger `CAP-BZG-06` SPECIFIED, 77 rows. CR state OPEN, next action `BOM/yield machinery`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
