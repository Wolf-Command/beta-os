# CURSOR MISSION — CAP-AMG-05 Hotel Revenue & Yield skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-AMG-REVENUE-YIELD-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `amg-revenue-yield-v1` on mission `owner-autonomous-20260920-w9`, after `amg-packages-products-v1` DONE (`c3b4ac4` / `ae245e4`). `CR-49f6461020b693fc` stays OPEN.

**Status:** the hotel revenue and yield skeleton is on Beta `:8788`. It names rates, occupancy, ADR, RevPAR, yield, and notes slots and leaves every slot empty. An empty framework is not live revenue or yield and not proof of hotel yield machinery. Rates, occupancy, ADR, and RevPAR are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-AMG-05` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-49f6461020b693fc` stays **OPEN**. Bound `beta-amg-ops-safe`.

## What landed

- `scripts/core/amg_revenue_yield.py` — Owner read of the skeleton. Schema `wolf.cap-amg-05.revenue-yield.v1` names the six slots and accepts no writes. `rates`, `occupancy`, `adr`, `revpar`, and `yield_value` stay null. `yanolja_live`, `live_revenue`, `live_yield`, and `yield_machinery` stay false. No framework file is created. `CR-49f6461020b693fc` is read and not written.
- `scripts/serve_beta.py` — `GET /api/amg/revenue-yield`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /amg-revenue-yield` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /yanolja` is `yanolja_refused`. `POST /rates`, `POST /occupancy`, `POST /adr`, `POST /revpar`, `POST /yield`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/amg-revenue-yield.html` — Owner page. It says an empty framework is not live revenue or yield and not proof of hotel yield machinery, not PROVEN, not READY, CAP-AMG-05 stays SPECIFIED, the ceiling label is BUILT, no invented rates, occupancy, ADR, or RevPAR, no Yanolja call, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_amg_revenue_yield.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-amg-revenue-yield-v1-20260920`.

No rates, occupancy, ADR, RevPAR, yield value, or Yanolja live state was stored. No Yanolja call. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The packages, daily-ops, and journey-workflow modules were not edited.

## Honesty (bound to the CR)

`CR-49f6461020b693fc` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Yield machinery`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-AMG-05` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_revenue` false, `empty_is_yield` false, `live_revenue` false, `yield_machinery` false, `rates` null, `occupancy` null, `adr` null, `revpar` null, `yield_value` null, `yanolja_live` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented rates, occupancy, ADR, or RevPAR. No payment. No Yanolja call. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_amg_revenue_yield.py` → `PASS=263 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `23093` (was `20842`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/amg/revenue-yield` → 403
- `curl http://127.0.0.1:8788/amg-revenue-yield` → 403
- Ledger `CAP-AMG-05` SPECIFIED, 77 rows. CR state OPEN, next action `Yield machinery`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
