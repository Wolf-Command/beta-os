# CURSOR MISSION — CAP-BZG-02 Venue P&L / Management Rollup skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-BZG-VENUE-PNL-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `bzg-venue-pnl-v1` on mission `owner-autonomous-20260920-w9`, after `ggv-intercompany-client-v1` DONE (`d07fdc9` / `d40c3f7`). `CR-1f136175afbcf7d4` stays OPEN.

**Status:** the venue P&L / management rollup skeleton is on Beta `:8788`. It names venue, revenue, cost, contribution, rollup, and notes slots and leaves every slot empty. An empty framework is not a live venue P&L and not proof of management rollup machinery. Revenue, cost, contribution, and rollup numbers are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-BZG-02` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-1f136175afbcf7d4` stays **OPEN**. Bound `beta-bzg-ops-safe`.

## What landed

- `scripts/core/bzg_venue_pnl.py` — Owner read of the skeleton. Schema `wolf.cap-bzg-02.venue-pnl.v1` names the six slots and accepts no writes. `venue`, `revenue`, `cost`, `contribution`, and `rollup` stay null. `live_pnl` and `rollup_machinery` stay false. No framework file is created. `CR-1f136175afbcf7d4` is read and not written.
- `scripts/serve_beta.py` — `GET /api/bzg/venue-pnl`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /bzg-venue-pnl` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /tax` is `tax_refused`. `POST /venue`, `POST /revenue`, `POST /cost`, `POST /contribution`, `POST /rollup`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/bzg-venue-pnl.html` — Owner page. It says an empty framework is not a live venue P&L and not proof of management rollup machinery, not PROVEN, not READY, CAP-BZG-02 stays SPECIFIED, the ceiling label is BUILT, no invented revenue, cost, contribution, or rollup, no tax treatment claim, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_bzg_venue_pnl.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-bzg-venue-pnl-v1-20260920`.

No revenue, cost, contribution, rollup, or venue P&L number was stored. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The intercompany, yield, and reputation modules were not edited.

## Honesty (bound to the CR)

`CR-1f136175afbcf7d4` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Venue P&L dashboards as capability`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-BZG-02` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_pnl` false, `empty_is_rollup_machinery` false, `live_pnl` false, `rollup_machinery` false, `venue` null, `revenue` null, `cost` null, `contribution` null, `rollup` null, `tax_claimed` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented P&L numbers. No payment. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_bzg_venue_pnl.py` → `PASS=261 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `28433` (was `25408`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/bzg/venue-pnl` → 403
- `curl http://127.0.0.1:8788/bzg-venue-pnl` → 403
- Ledger `CAP-BZG-02` SPECIFIED, 77 rows. CR state OPEN, next action `Venue P&L dashboards as capability`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
