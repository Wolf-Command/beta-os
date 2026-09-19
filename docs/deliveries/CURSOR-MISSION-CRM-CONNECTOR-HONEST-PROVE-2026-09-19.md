# CURSOR MISSION — CAP-CRM-04 Honest connector prove — 2026-09-20

**Decision served:** 2026-09-19 plan `docs/deliveries/GROK-PLAN-CRM-CONNECTOR-HONEST-PROVE-2026-09-19.md`. `CR-c8719063fb940ed4` next action is Honest connector prove. Owner lane `crm-connector-honest-prove`. Wave-5 after DR failure-domains DONE (`9209284`).

**Status:** read-only prove is on Beta `:8788`. Klaviyo and ActiveCampaign are named as different connectors. Brand scopes are documented. Not a send. Not a live wire. Not PROVEN. Not READY. `CAP-CRM-04` stays **BUILT**. Ceiling is **BUILT**. `CR-c8719063fb940ed4` stays **OPEN**.

## What landed

- `scripts/core/crm_connector_prove.py` — Owner prove. Ten checklist steps, all `NOT_RUN`, every slot `EMPTY`. Two connectors: Klaviyo (`source_system` `klaviyo`) and ActiveCampaign (`source_system` `activecampaign`). They are not the same system. Five brand scopes. Habitat Klaviyo scope is `DOCUMENTED` (entity `ENT-GGV`) and not called. ActiveCampaign is `ABSENT` on every brand. Uma Blu, Atrium, Selo, and Tropik are `ABSENT`, not zero. Sends, subscribers, and profiles inserted stay null. Machine-readable schema `wolf.cap-crm-04.connector-honest-log.v1` accepts only a `NOT_RUN` log. The Habitat reader file is not imported.
- `scripts/serve_beta.py` — `GET /api/crm-connector-prove`, `/checklist`, `/schema`, `/log`, `/connectors`, `/brands`, `/gaps`, `/<id>`, and `GET /crm-connector-prove` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. `POST /api/crm-connector-prove/send` is `send_refused`. `POST /api/crm-connector-prove/klaviyo-write` is `klaviyo_write_refused`. `POST /api/crm-connector-prove/ac-write` is `ac_write_refused`. `POST /api/crm-connector-prove/crm-write` is `crm_write_refused`. `POST /api/crm-connector-prove/metricool` is `metricool_write_refused`. `POST /api/crm-connector-prove/conflate` is `conflate_refused`. `POST /api/crm-connector-prove/production` is `production_refused`. `POST /api/crm-connector-prove/prove` is `proven_refused`. `POST /api/crm-connector-prove/resolve` is `resolve_refused`. `POST /api/crm-connector-prove/fill` is `slots_refused`.
- `dashboards/crm-connector-prove.html` — Owner page. It says Klaviyo is not ActiveCampaign, scopes are not counts, and there is no send.
- `scripts/tests/test_crm_connector_prove.py` — distinct connectors, brand scopes, gaps, refuse paths, CR bind, ceiling, WIP four.

No Klaviyo page was fetched. No ActiveCampaign call was made. No mail was sent. No profile was inserted. This is not the email-wire plan in `GROK-PLAN-CRM-EMAIL-WIRE-PROVE-2026-09-20.md`.

## Honesty (bound to the CR)

`CR-c8719063fb940ed4` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Honest connector prove`. This slice does not resolve the CR and does not write the ledger.

- `CAP-CRM-04` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back.
- The emitted log has `status` `NOT_RUN`, `prove_id` null, `conflated` false, `send` false, `klaviyo_called` false, `ac_called` false, `cr_resolved` false, and `sends` / `subscribers` / `profiles_inserted` null. A log that claims a send, a call, a conflation, a count (including zero), READY, PROVEN, or a resolved CR is refused. It is not rewritten into a pass.
- Gaps: Klaviyo file present but not called (`DOCUMENTED`). ActiveCampaign reader file absent (`ABSENT`, not zero). Non-Habitat brands absent (`ABSENT`, not zero). Send refused, which is not a sent count of zero.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external CRM write. No Metricool write. No send.

## Prove

`python3 scripts/tests/test_crm_connector_prove.py` → `PASS=188 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `65818`
- `curl http://127.0.0.1:8788/api/crm-connector-prove` → 403
- `curl http://127.0.0.1:8788/crm-connector-prove` → 403
- Ledger `CAP-CRM-04` BUILT, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
