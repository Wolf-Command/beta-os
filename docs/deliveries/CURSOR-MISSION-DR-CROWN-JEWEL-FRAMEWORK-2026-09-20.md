# CURSOR MISSION — CAP-DR-02 Crown Jewel framework — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-DR-CROWN-JEWEL-FRAMEWORK-2026-09-20.md`. `CR-01fc21cfe028333b` stays OPEN. Owner lane `dr-crown-jewel-framework` on mission `owner-autonomous-20260920-w6`, after `crm-package-intel-v1` DONE (`b39f762`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the crown-jewel register is on Beta `:8788`. Three systems are named and their contents stay closed. Each system carries Beta, Production, NAS, and B2 as separate failure domains. Every independence slot stays empty. Naming a system is not protecting it. Not a live restore. Not PROVEN. Not READY. `CAP-DR-02` stays **SPECIFIED**. The ceiling label is **BUILT**. `CR-01fc21cfe028333b` stays **OPEN**.

## What landed

- `scripts/core/dr_crown_jewel.py` — Owner register. Systems are `CJ-PLAYBOOK`, `CJ-REGISTRY`, and `CJ-WOLF-IP`. Visibility is `HIDDEN`. Contents are null. Each system has its own Beta, Production, NAS, and B2 rows, all uncontacted, slots `EMPTY`. Ten checklist steps stay `NOT_RUN`. Machine-readable schema `wolf.cap-dr-02.crown-jewel-register.v1` accepts only a `NOT_RUN` log. `protected_count` stays null.
- `scripts/serve_beta.py` — `GET /api/crown-jewels`, `/checklist`, `/schema`, `/register`, `/systems`, `/log`, `/domains`, and `/<id>`, plus `GET /crown-jewels` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /open` is `playbook_refused`. `POST /protect` is `protection_refused`. `POST /resolve` is `resolve_refused`. `POST /run` is `live_restore_refused`. `POST /nas` is `nas_destructive_refused`. `POST /b2` is `b2_destructive_refused`. `POST /production` is `production_refused`. `POST /prove` is `independence_refused`. `POST /ready` is `ready_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/crown-jewels.html` — Owner page. It says contents stay closed, slots stay empty, and the page does not resolve the completion row.
- `scripts/tests/test_dr_crown_jewel.py` — closed register, refuse paths, ceiling, CR bind, WIP four.

No playbook was opened. No NAS or B2 call. No Production write. No protection proof was recorded.

## Honesty (bound to the CR)

`CR-01fc21cfe028333b` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Independent failure domains prove`. This slice does not resolve the CR and does not write the ledger.

- `CAP-DR-02` ledger state stays SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass.
- The live payload has `identified_count` 3, `protected_count` null, `crown_jewels_opened` false, `contents` null, `protection_proved` false, `independence_proved` false, and `cr_resolved` false. Three named systems are not three protected systems.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No live restore. No destructive NAS or B2 operation.

## Prove

`python3 scripts/tests/test_dr_crown_jewel.py` → `PASS=163 FAIL=0`.

`python3 scripts/tests/test_failure_domains.py` → `PASS=157 FAIL=0` after the server edit.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `84149` (was `81754`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/crown-jewels` → 403
- `curl http://127.0.0.1:8788/crown-jewels` → 403
- Ledger `CAP-DR-01` SPECIFIED, `CAP-DR-02` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
