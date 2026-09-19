# CURSOR MISSION — CAP-MSC-04 Cybersecurity Baseline v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-MSC-CYBER-BASELINE-V1-2026-09-20.md`. `CR-7dae8b389cce6f9a` stays OPEN. Owner lane `msc-cyber-baseline-v1` on mission `owner-autonomous-20260920-w7`, after `msc-compliance-pack-v1` DONE (`6561ac6`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the cybersecurity baseline skeleton is on Beta `:8788`. It names MFA, device posture, and audited-access slots and leaves every slot empty. An empty baseline is not proof of security. MFA and device posture are not invented as current. Not PROVEN. Not READY. `CAP-MSC-04` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-7dae8b389cce6f9a` stays **OPEN**.

## What landed

- `scripts/core/msc_cyber_baseline.py` — Owner read of the skeleton. Schema `wolf.cap-msc-04.cyber-baseline.v1` names the three slots and accepts no writes. `mfa_status` and `device_posture` stay null. `security_proved` stays false. No baseline file is created. `CR-7dae8b389cce6f9a` is read and not written.
- `scripts/serve_beta.py` — `GET /api/msc/cyber`, `/schema`, `/kinds`, `/baseline`, and `/<kind>` plus `GET /msc-cyber` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /current`, `POST /mfa-status`, and `POST /device-posture-status` are `posture_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/msc-cyber.html` — Owner page. It says an empty baseline is not proof of security, MFA is not current, device posture is not current, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_msc_cyber_baseline.py` — empty baseline, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-msc-cyber-baseline-v1-20260920`.

No evidence row was stored. No payment was stored. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-7dae8b389cce6f9a` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `MFA/device posture CAP`. This slice does not resolve the CR and does not write the ledger.

- `CAP-MSC-04` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_security` false, `mfa_status` null, `device_posture` null, `audited_access` null, `current` false, `security_proved` false, `payment` null, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented MFA or device posture. No payment. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_msc_cyber_baseline.py` → `PASS=146 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `91438` (was `89018`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/msc/cyber` → 403
- `curl http://127.0.0.1:8788/msc-cyber` → 403
- Ledger `CAP-MSC-04` SPECIFIED, 77 rows. CR state OPEN. Live baseline file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
