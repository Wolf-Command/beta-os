# CURSOR MISSION — CAP-BZG-05 Central Kitchen & Shared Cost Allocation skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-BZG-ALLOCATION-ENGINE-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `bzg-allocation-engine-v1` on mission `owner-autonomous-20260920-w10`, after `bzg-variance-waste-v1` DONE (`3533492` / `e43bd56`). `CR-777c285859b3b745` stays OPEN.

**Status:** the central kitchen / shared cost allocation skeleton is on Beta `:8788`. It names kitchen, venues, shared_cost, allocation, drivers, and notes slots and leaves every slot empty. An empty framework is not a live allocation engine and not proof of shared-cost allocation machinery. Allocation, shared cost, kitchen, venue, and driver numbers are not recorded. ESB remains transactional SoT (read-only note only; no ESB mutate). Not PROVEN. Not READY. The live ledger row for `CAP-BZG-05` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-777c285859b3b745` stays **OPEN**. Bound `beta-bzg-ops-safe`.

## What landed

- `scripts/core/bzg_allocation_engine.py` — Owner read of the skeleton. Schema `wolf.cap-bzg-05.allocation-engine.v1` names the six slots and accepts no writes. `kitchen`, `venues`, `shared_cost`, `allocation`, and `drivers` stay null. `live_allocation_engine` and `shared_cost_allocation_machinery` stay false. `esb_mutated` stays false. No framework file is created. `CR-777c285859b3b745` is read and not written.
- `scripts/serve_beta.py` — `GET /api/bzg/allocation-engine`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /bzg-allocation-engine` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /esb` is `esb_refused`. `POST /kitchen`, `POST /venues`, `POST /shared_cost`, `POST /allocation`, `POST /drivers`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/bzg-allocation-engine.html` — Owner page. It says an empty framework is not a live allocation engine and not proof of shared-cost allocation machinery, not PROVEN, not READY, CAP-BZG-05 stays SPECIFIED, the ceiling label is BUILT, no invented allocation, shared cost, kitchen, venues, or drivers, ESB remains transactional SoT with no ESB mutate, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_bzg_allocation_engine.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-bzg-allocation-engine-v1-20260920`.

No allocation, shared cost, kitchen, venue, or driver number was stored. No payment was executed. No bank write. No Zayen or books write. No ESB mutate. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The variance/waste, venue P&L, and reputation modules were not edited.

## Honesty (bound to the CR)

`CR-777c285859b3b745` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Allocation engine`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-BZG-05` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_allocation_engine` false, `empty_is_shared_cost_allocation_machinery` false, `live_allocation_engine` false, `shared_cost_allocation_machinery` false, `kitchen` null, `venues` null, `shared_cost` null, `allocation` null, `drivers` null, `esb_mutated` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented allocation numbers. No payment. No ESB mutate. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_bzg_allocation_engine.py` → `PASS=268 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `38597` (was `36117`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/bzg/allocation-engine` → 403
- `curl http://127.0.0.1:8788/bzg-allocation-engine` → 403
- Ledger `CAP-BZG-05` SPECIFIED, 77 rows. CR state OPEN, next action `Allocation engine`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
