# CURSOR MISSION — CAP-INTG-04 CAP-bound connector tests skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-INTG-CONNECTOR-CAP-TESTS-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `intg-connector-cap-tests-v1` on mission `owner-autonomous-20260920-w8`, after `intg-connector-contract-v1` DONE (`141d30b` / `6c6ef51`). `decisions.md` has no separate PICK line for this lane. `CR-859e7cad64e7e4ad` stays OPEN. `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the connector tests skeleton is on Beta `:8788`. It names cap, fixture, and refuse slots and leaves every slot empty. An empty framework is not a live bank-connector prove and not a live bank feed. Not PROVEN. Not READY. The live ledger row for `CAP-INTG-04` is **BUILT**. This slice did not rewrite it. The ceiling label is **BUILT**. `CAP-INTG-01` stays **ABSENT**. `CR-859e7cad64e7e4ad` stays **OPEN**.

## What landed

- `scripts/core/intg_connector_cap_tests.py` — Owner read of the skeleton. Schema `wolf.cap-intg-04.connector-cap-tests.v1` names the three slots and accepts no writes. `bank_api_called` stays false. `bank_feed_called` stays false. `live_bank_connector` stays false. `current` stays false. No framework file is created. `CR-859e7cad64e7e4ad` is read and not written. `CAP-INTG-01` is read and not written.
- `scripts/serve_beta.py` — `GET /api/intg/connector-cap-tests`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /connector-cap-tests` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` and `POST /live-bank` are `bank_refused`. `POST /bank-feed` is `feed_refused`. `POST /current` is `current_refused`. `POST /connector` is `connector_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /rewrite` is `rewrite_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/connector-cap-tests.html` — Owner page. It says an empty framework is not a live bank-connector prove and not a live bank feed, not READY, CAP-INTG-04 stays BUILT, the ceiling label is BUILT, CAP-INTG-01 stays ABSENT, no bank API, no payment, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_intg_connector_cap_tests.py` — empty framework, refuse paths, ceiling, CR bind, CAP-INTG-01 untouched, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-intg-connector-cap-tests-v1-20260920`.

No cap row was stored. No fixture was stored. No bank API call. No bank feed. No payment was executed. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The connector-contract module was not edited.

## Honesty (bound to the CR)

`CR-859e7cad64e7e4ad` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `CAP-bound connector tests`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-INTG-04` ledger state is BUILT. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_prove` false, `empty_is_ready` false, `empty_is_bank_feed` false, `bank_api_called` false, `bank_feed_called` false, `live_bank_connector` false, `current` false, `fixture` null, `bank_feed` null, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent. `CAP-INTG-01` stays ABSENT.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented bank connector. No payment. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_intg_connector_cap_tests.py` → `PASS=206 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `6914` (was `4649`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/intg/connector-cap-tests` → 403
- `curl http://127.0.0.1:8788/connector-cap-tests` → 403
- Ledger `CAP-INTG-04` BUILT, `CAP-INTG-01` ABSENT, 77 rows. CR state OPEN. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
