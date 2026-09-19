# CURSOR MISSION — CAP-DR-01 Restore drill framework — 2026-09-19

**Decision served:** 2026-09-19 PICK, restore-drill framework on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-DR-RESTORE-DRILL-FRAMEWORK-2026-09-19.md`). Owner lane `dr-restore-drill-framework`.

**Status:** read-only skeleton is on Beta `:8788`. Not a live restore. Not PROVEN. Not READY. Model C maturity not raised. `CAP-DR-01` stays **SPECIFIED**. `CR-667f31959d1bbe82` stays **OPEN**.

## What landed

- `scripts/core/restore_drill.py` — Owner framework. Nine checklist steps, all `NOT_RUN`. Machine-readable schema `wolf.cap-dr-01.restore-drill-log.v1` accepts only a `NOT_RUN` log. RTO/RPO tiers stay empty. NAS, B2, and Production are recorded as not contacted. The 2026-08-29 historical note is cited as history and is not this drill.
- `scripts/serve_beta.py` — `GET /api/restore-drill`, `GET /api/restore-drill/checklist`, `GET /api/restore-drill/schema`, `GET /api/restore-drill/log`, `GET /api/restore-drill/<step>`, `GET /restore-drill` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. `POST /api/restore-drill/run` is `live_restore_refused`. `POST /api/restore-drill/nas` is `nas_destructive_refused`. `POST /api/restore-drill/b2` is `b2_destructive_refused`. `POST /api/restore-drill/production` is `production_refused`.
- `dashboards/restore-drill.html` — Owner page. It says the log stays `NOT_RUN` and live restore is refused.
- `scripts/tests/test_restore_drill.py` — checklist, schema, refuse paths, CR bind, ceiling, WIP four.

CAP-DR-02 was not built. No restore was run. No NAS or B2 call. No Production write.

## Honesty (bound to the CR)

`CR-667f31959d1bbe82` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Deterministic canonical restore-drill proof for PROVEN; fresh CAP-bound Beta drill for READY`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-DR-01` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back.
- The emitted log has `status` `NOT_RUN`, `drill_id` null, and `live_restore` false. A log that claims success, a restore, a NAS delete, a B2 delete, READY, or a maturity raise is refused. It is not rewritten into a pass.
- `CAP-DR-02` stays SPECIFIED. Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write. No destructive NAS or B2.

## Prove

`python3 scripts/tests/test_restore_drill.py` → `PASS=128 FAIL=0`.

`python3 scripts/tests/test_sale_evidence_pack.py` → `PASS=116 FAIL=0` after the `serve_beta.py` route add.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `39683`
- `curl http://127.0.0.1:8788/api/restore-drill` → 403
- `curl http://127.0.0.1:8788/restore-drill` → 403
- `POST http://127.0.0.1:8788/api/restore-drill/run` → 403 (no JWT in this shell; Owner 405 `live_restore_refused` is the same handler in the test)
- Ledger `CAP-DR-01` SPECIFIED, `CAP-DR-02` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
