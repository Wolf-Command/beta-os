# CURSOR MISSION — CAP-AMG-04 Daily hotel operating state skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-AMG-DAILY-OPS-STATE-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `amg-daily-ops-state-v1` on mission `owner-autonomous-20260920-w9`, after wave-8 `amg-journey-workflow-v1` DONE (`4a35fb1` / `abb98e6`). `CR-bc5785d66c981fd4` stays OPEN.

**Status:** the daily hotel operating-state skeleton is on Beta `:8788`. It names occupancy, arrivals, departures, in-house, out-of-order, and notes slots and leaves every slot empty. An empty framework is not a live daily ops state and not proof of hotel operations. Occupancy, ADR, and RevPAR are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-AMG-04` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-bc5785d66c981fd4` stays **OPEN**. Bound `beta-amg-ops-safe`.

## What landed

- `scripts/core/amg_daily_ops_state.py` — Owner read of the skeleton. Schema `wolf.cap-amg-04.daily-ops-state.v1` names the six slots and accepts no writes. `occupancy`, `adr`, and `revpar` stay null. `yanolja_live`, `live_ops`, and `hotel_operations` stay false. No framework file is created. `CR-bc5785d66c981fd4` is read and not written.
- `scripts/serve_beta.py` — `GET /api/amg/daily-ops-state`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /amg-daily-ops-state` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /yanolja` is `yanolja_refused`. `POST /adr`, `POST /revpar`, `POST /current`, and `POST /occupancy` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/amg-daily-ops-state.html` — Owner page. It says an empty framework is not a live daily ops state and not proof of hotel operations, not PROVEN, not READY, CAP-AMG-04 stays SPECIFIED, the ceiling label is BUILT, no invented occupancy, ADR, or RevPAR, no Yanolja call, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_amg_daily_ops_state.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-amg-daily-ops-state-v1-20260920`.

No occupancy, ADR, RevPAR, or Yanolja live state was stored. No Yanolja call. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The journey-workflow module was not edited.

## Honesty (bound to the CR)

`CR-bc5785d66c981fd4` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Machine-generated daily ops`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-AMG-04` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_ops` false, `empty_is_operations` false, `live_ops` false, `hotel_operations` false, `occupancy` null, `adr` null, `revpar` null, `yanolja_live` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented occupancy, ADR, or RevPAR. No payment. No Yanolja call. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_amg_daily_ops_state.py` → `PASS=245 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `16856` (was `13110`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/amg/daily-ops-state` → 403
- `curl http://127.0.0.1:8788/amg-daily-ops-state` → 403
- Ledger `CAP-AMG-04` SPECIFIED, 77 rows. CR state OPEN, next action `Machine-generated daily ops`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
