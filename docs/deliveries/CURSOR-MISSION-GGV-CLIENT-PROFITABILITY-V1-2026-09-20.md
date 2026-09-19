# CURSOR MISSION — CAP-GGV-03 Client / Contract Profitability skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-GGV-CLIENT-PROFITABILITY-V1-2026-09-20.md`. `CR-ccb3287dabe91d4b` stays OPEN. Owner lane `ggv-client-profitability-v1` on mission `owner-autonomous-20260920-w7`, after `intg-secrets-env-separation-v1` DONE (`256ad67`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the client / contract / allocation skeleton is on Beta `:8788`. It names client, contract, and allocation slots and leaves every slot empty. An empty framework is not a live P&L and not proof of profitability. Revenue, cost, margin, and FX are not recorded. Not PROVEN. Not READY. `CAP-GGV-03` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-ccb3287dabe91d4b` stays **OPEN**. Bound `beta-ggv-ops-safe`.

## What landed

- `scripts/core/ggv_client_profitability.py` — Owner read of the skeleton. Schema `wolf.cap-ggv-03.client-profitability.v1` names the three slots and accepts no writes. `client`, `contract`, and `allocation` stay empty. `revenue`, `cost`, `margin`, and `fx` stay null. `live_pnl` and `profitability_proved` stay false. `CR-ccb3287dabe91d4b` is read and not written.
- `scripts/serve_beta.py` — `GET /api/ggv/client-profitability`, `/schema`, `/kinds`, `/register`, and `/<kind>` plus `GET /ggv-client-profitability` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /revenue`, `POST /cost`, `POST /margin`, `POST /fx`, `POST /live-pnl`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/ggv-client-profitability.html` — Owner page. It says an empty framework is not a live P&L, not proof of profitability, revenue/cost/margin/FX are not shown, money does not move, a bank is not written, Zayen books are not written, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_ggv_client_profitability.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-ggv-client-profitability-v1-20260920`.

No revenue, cost, margin, or FX number was stored. No payment was stored. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-ccb3287dabe91d4b` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Build client/contract P&L allocation`. This slice does not resolve the CR and does not write the ledger.

- `CAP-GGV-03` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_pnl` false, `revenue` null, `cost` null, `margin` null, `fx` null, `live_pnl` false, `current` false, `profitability_proved` false, `target_is_actual` false, `payment` null, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented P&L. No payment. No bank write. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_ggv_client_profitability.py` → `PASS=181 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `99912` (was `97247`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/ggv/client-profitability` → 403
- `curl http://127.0.0.1:8788/ggv-client-profitability` → 403
- Ledger `CAP-GGV-03` SPECIFIED, 77 rows. CR state OPEN. Live P&L file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
