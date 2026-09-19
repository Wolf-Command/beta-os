# CURSOR MISSION — CAP-MSC-02 Automated Posture Prove framework v1 — 2026-09-20

**Decision served:** 2026-09-20 plan `docs/deliveries/GROK-PLAN-MSC-POSTURE-PROVE-V1-2026-09-20.md` and the same-day PICK in `~/.openclaw/wolf-output/decisions.md`. `CR-80296d7bc9c35452` stays OPEN. Owner lane `msc-posture-prove-v1` on mission `owner-autonomous-20260920-w8`, after wave-7 `ggv-client-profitability-v1` DONE (`1af6c36`). `intel-learning-policy-v1` stays PARKED/BLOCKED.

**Status:** the posture prove skeleton is on Beta `:8788`. It names posture, control, and evidence slots and leaves every slot empty. An empty framework is not a prove and not READY. A live posture score is not invented as current. Not PROVEN. Not READY. The live ledger row for `CAP-MSC-02` is **BUILT** (it is not SPECIFIED). This slice did not rewrite it. The ceiling label is **BUILT**. `CR-80296d7bc9c35452` stays **OPEN**.

## What landed

- `scripts/core/msc_posture_prove.py` — Owner read of the skeleton. Schema `wolf.cap-msc-02.posture-prove.v1` names the three slots and accepts no writes. `posture_score` stays null. `proved` stays false. No framework file is created. `CR-80296d7bc9c35452` is read and not written.
- `scripts/serve_beta.py` — `GET /api/msc/posture`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /msc-posture` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /score`, `POST /live-score`, and `POST /current` are `score_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /fill` and `POST /note` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/msc-posture.html` — Owner page. It says an empty framework is not a prove and not READY, a posture score is not current, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_msc_posture_prove.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-msc-posture-prove-v1-20260920`.

No evidence row was stored. No payment was stored. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved.

## Honesty (bound to the CR)

`CR-80296d7bc9c35452` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `CAP-bound automated posture prove as READY`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-MSC-02` ledger state is BUILT, not SPECIFIED. The ceiling label is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. A SPECIFIED fixture reports ceiling BUILT and is not written back.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_prove` false, `empty_is_ready` false, `posture_score` null, `control` null, `evidence` null, `current` false, `proved` false, `payment` null, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented posture score. No payment. No Cloudflare or Access mutation. `intel-learning-policy-v1` was not started.

## Prove

`python3 scripts/tests/test_msc_posture_prove.py` → `PASS=151 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807` (`serve.py 8787`). `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `2446` (was `99912`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/msc/posture` → 403
- `curl http://127.0.0.1:8788/msc-posture` → 403
- Ledger `CAP-MSC-02` BUILT, 77 rows. CR state OPEN. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
