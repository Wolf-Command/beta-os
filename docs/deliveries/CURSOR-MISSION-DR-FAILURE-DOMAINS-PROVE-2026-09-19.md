# CURSOR MISSION — CAP-DR-02 Independent failure domains — 2026-09-20

**Decision served:** 2026-09-20 PICK, independent failure-domain prove on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-DR-FAILURE-DOMAINS-PROVE-2026-09-19.md`). Owner lane `dr-failure-domains-prove`. Wave-5 after sale-buyer-dataroom DONE (`23ed1aa` / `a6f8d31`).

**Status:** read-only skeleton is on Beta `:8788`. Beta and Production are named as separate failure domains. Independence slots stay empty. Not a live restore. Not PROVEN. Not READY. `CAP-DR-02` stays **SPECIFIED**. Ceiling is **BUILT**. `CR-01fc21cfe028333b` stays **OPEN**.

## What landed

- `scripts/core/failure_domains.py` — Owner framework. Ten checklist steps, all `NOT_RUN`, every slot `EMPTY`. Four named domains: Beta, Production, NAS, B2. Beta `distinct_from` includes Production and the reverse. Separation is `DOCUMENTED`, not proved. Machine-readable schema `wolf.cap-dr-02.failure-domain-log.v1` accepts only a `NOT_RUN` log. The Matt-only playbook is cited as unread and is not opened.
- `scripts/serve_beta.py` — `GET /api/failure-domains`, `GET /api/failure-domains/checklist`, `GET /api/failure-domains/schema`, `GET /api/failure-domains/log`, `GET /api/failure-domains/domains`, `GET /api/failure-domains/<id>`, `GET /failure-domains` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. `POST /api/failure-domains/run` is `live_restore_refused`. `POST /api/failure-domains/nas` is `nas_destructive_refused`. `POST /api/failure-domains/b2` is `b2_destructive_refused`. `POST /api/failure-domains/production` is `production_refused`. `POST /api/failure-domains/prove` is `independence_refused`. `POST /api/failure-domains/collapse` is `collapse_refused`. `POST /api/failure-domains/fill` is `slots_refused`.
- `dashboards/failure-domains.html` — Owner page. It says Beta is not Production, slots stay empty, and live restore is refused.
- `scripts/tests/test_failure_domains.py` — empty slots, Beta≠Production, refuse paths, CR bind, ceiling, WIP four.

No restore was run. No NAS or B2 call. No Production write. This is not the crown-jewel register in `GROK-PLAN-DR-CROWN-JEWEL-FRAMEWORK-2026-09-20.md`.

## Honesty (bound to the CR)

`CR-01fc21cfe028333b` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Independent failure domains prove`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-DR-02` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back.
- The emitted log has `status` `NOT_RUN`, `prove_id` null, `beta_equals_production` false, `independence_proved` false, and `slots_filled` false. A log that claims success, a restore, a collapse, a filled slot, a NAS delete, a B2 delete, READY, or a maturity raise is refused. It is not rewritten into a pass.
- `CAP-DR-01` stays SPECIFIED. Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write. No destructive NAS or B2.

## Prove

`python3 scripts/tests/test_failure_domains.py` → `PASS=157 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `63464`
- `curl http://127.0.0.1:8788/api/failure-domains` → 403
- `curl http://127.0.0.1:8788/failure-domains` → 403
- Ledger `CAP-DR-01` SPECIFIED, `CAP-DR-02` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
