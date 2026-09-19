# CURSOR MISSION — CAP-INTG-07 Secrets & Environment Separation v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-INTG-SECRETS-ENV-SEPARATION-V1-2026-09-20.md`. `CR-273f30371bd52c8a` stays OPEN. Owner lane `intg-secrets-env-separation-v1` on mission `owner-autonomous-20260920-w7`, after `msc-records-defensibility-v1` DONE (`5945509`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the secrets / rotation / Beta↔Production separation skeleton is on Beta `:8788`. It names vault, rotation, and Beta↔Production slots and leaves every slot empty. An empty framework is not proof of separation and not a live vault. Existing `.env.example`, gitignore, and sacred-rule checks are evidence pointers only. Not PROVEN. Not READY. `CAP-INTG-07` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-273f30371bd52c8a` stays **OPEN**. Bound `beta-integration-health-readonly`.

## What landed

- `scripts/core/intg_secrets_env.py` — Owner read of the skeleton. Schema `wolf.cap-intg-07.secrets-env-separation.v1` names the three slots and accepts no writes. `vault`, `rotation`, and `separation` stay null. `live_vault` and `separation_proved` stay false. Pointer rows name `.env.example`, `.gitignore`, and the sacred rule without reading their contents. `pointer_is_proof` stays false. No vault file is created. `CR-273f30371bd52c8a` is read and not written.
- `scripts/serve_beta.py` — `GET /api/intg/secrets`, `/schema`, `/kinds`, `/register`, `/pointers`, and `/<kind>` plus `GET /intg-secrets` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /current`, `POST /live-vault`, and `POST /rotation-status` are `current_refused`. `POST /secret-store` is `secret_store_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/intg-secrets.html` — Owner page. It says an empty framework is not proof of separation, not a live vault, rotation is not current, repo checks are evidence pointers only, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_intg_secrets_env.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-intg-secrets-env-separation-v1-20260920`.

No secret value was stored. No payment was stored. No Cloudflare or Access call. No Production write. No Alchemist write. No external secret-store write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-273f30371bd52c8a` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Deterministic vault/rotation/separation prove for PROVEN; vault product for READY`. This slice does not resolve the CR and does not write the ledger.

- `CAP-INTG-07` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_separation` false, `vault` null, `rotation` null, `separation` null, `live_vault` false, `current` false, `separation_proved` false, `pointer_is_proof` false, `contents_read` false, `payment` null, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented vault, rotation, or separation. No payment. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_intg_secrets_env.py` → `PASS=167 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `97247` (was `93913`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/intg/secrets` → 403
- `curl http://127.0.0.1:8788/intg-secrets` → 403
- Ledger `CAP-INTG-07` SPECIFIED, 77 rows. CR state OPEN. Live vault file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
