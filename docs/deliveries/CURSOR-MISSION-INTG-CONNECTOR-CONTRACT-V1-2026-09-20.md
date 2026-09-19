# CURSOR MISSION — CAP-INTG-01 Connector Contract / Tests framework v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-INTG-CONNECTOR-CONTRACT-V1-2026-09-20.md` and the same-day PICK in `~/.openclaw/wolf-output/decisions.md`. `CR-227e2514ac8dcd02` stays OPEN. Owner lane `intg-connector-contract-v1` on mission `owner-autonomous-20260920-w8`, after `msc-posture-prove-v1` DONE (`01858ec` / `463d84a`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the connector contract skeleton is on Beta `:8788`. It names contract, fixture, and refuse slots and leaves every slot empty. An empty framework is not a live connector prove and not Yanolja or ESB. Not SPECIFIED. Not PROVEN. Not READY. The live ledger row for `CAP-INTG-01` is **ABSENT**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-227e2514ac8dcd02` stays **OPEN**.

## What landed

- `scripts/core/intg_connector_contract.py` — Owner read of the skeleton. Schema `wolf.cap-intg-01.connector-contract.v1` names the three slots and accepts no writes. `yanolja_called` stays false. `esb_called` stays false. `live_connector` stays false. No framework file is created. `CR-227e2514ac8dcd02` is read and not written.
- `scripts/serve_beta.py` — `GET /api/intg/connector-contract`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /connector-contract` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /yanolja` and `POST /live-yanolja` are `yanolja_refused`. `POST /esb` and `POST /live-esb` are `esb_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /specified` is `specified_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/connector-contract.html` — Owner page. It says an empty framework is not a live connector prove and not Yanolja and not ESB, not READY, CAP-INTG-01 stays ABSENT, the ceiling label is BUILT, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_intg_connector_contract.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-intg-connector-contract-v1-20260920`.

No contract row was stored. No fixture was stored. No Yanolja call. No ESB call. No payment was stored. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-227e2514ac8dcd02` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Connector code/tests/contract`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-INTG-01` ledger state is ABSENT. The ceiling label is BUILT. A fixture that is already SPECIFIED is reported as SPECIFIED with ceiling BUILT and is not written back. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent SPECIFIED, PROVEN, or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_prove` false, `empty_is_ready` false, `empty_is_yanolja` false, `empty_is_esb` false, `yanolja_called` false, `esb_called` false, `live_connector` false, `contract` null, `fixture` null, `current` false, `proved` false, `payment` null, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented connector. No payment. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_intg_connector_contract.py` → `PASS=178 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807` (`serve.py 8787`). `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `4649` (was `2446`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/intg/connector-contract` → 403
- `curl http://127.0.0.1:8788/connector-contract` → 403
- Ledger `CAP-INTG-01` ABSENT, 77 rows. CR state OPEN. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
