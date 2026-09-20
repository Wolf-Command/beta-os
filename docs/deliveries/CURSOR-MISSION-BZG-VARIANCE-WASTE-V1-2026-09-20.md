# CURSOR MISSION — CAP-BZG-04 Variance / Waste Analysis skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-BZG-VARIANCE-WASTE-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `bzg-variance-waste-v1` on mission `owner-autonomous-20260920-w10`, after `amg-sla-incident-v1` DONE (`7758176` / `49ee985`). `CR-72671b592b8f8631` stays OPEN.

**Status:** the variance / waste analysis skeleton is on Beta `:8788`. It names variance, waste, comps, voids, analysis, and notes slots and leaves every slot empty. An empty framework is not a live variance/waste analysis and not proof of inventory variance machinery. Variance, waste, comps, voids, and analysis numbers are not recorded. ESB remains transactional SoT (read-only note only; no ESB mutate). Not PROVEN. Not READY. The live ledger row for `CAP-BZG-04` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-72671b592b8f8631` stays **OPEN**. Bound `beta-bzg-ops-safe`.

## What landed

- `scripts/core/bzg_variance_waste.py` — Owner read of the skeleton. Schema `wolf.cap-bzg-04.variance-waste.v1` names the six slots and accepts no writes. `variance`, `waste`, `comps`, `voids`, and `analysis` stay null. `live_variance_waste` and `inventory_variance_machinery` stay false. `esb_mutated` stays false. No framework file is created. `CR-72671b592b8f8631` is read and not written.
- `scripts/serve_beta.py` — `GET /api/bzg/variance-waste`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /bzg-variance-waste` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /esb` is `esb_refused`. `POST /variance`, `POST /waste`, `POST /comps`, `POST /voids`, `POST /analysis`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/bzg-variance-waste.html` — Owner page. It says an empty framework is not a live variance/waste analysis and not proof of inventory variance machinery, not PROVEN, not READY, CAP-BZG-04 stays SPECIFIED, the ceiling label is BUILT, no invented variance, waste, comps, voids, or analysis, ESB remains transactional SoT with no ESB mutate, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_bzg_variance_waste.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-bzg-variance-waste-v1-20260920`.

No variance, waste, comps, voids, or analysis number was stored. No payment was executed. No bank write. No Zayen or books write. No ESB mutate. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The venue P&L, SLA, and reputation modules were not edited.

## Honesty (bound to the CR)

`CR-72671b592b8f8631` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Variance/waste analysis machinery`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-BZG-04` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_variance_waste` false, `empty_is_inventory_variance_machinery` false, `live_variance_waste` false, `inventory_variance_machinery` false, `variance` null, `waste` null, `comps` null, `voids` null, `analysis` null, `esb_mutated` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented variance/waste numbers. No payment. No ESB mutate. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_bzg_variance_waste.py` → `PASS=267 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `36117` (was `34188`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/bzg/variance-waste` → 403
- `curl http://127.0.0.1:8788/bzg-variance-waste` → 403
- Ledger `CAP-BZG-04` SPECIFIED, 77 rows. CR state OPEN, next action `Variance/waste analysis machinery`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
