# CURSOR MISSION — CAP-GGV-06 Intercompany Client Mode skeleton v1 — 2026-09-20

**Decision served:** 2026-09-20 PICK in `decisions.md` and plan `docs/deliveries/GROK-PLAN-GGV-INTERCOMPANY-CLIENT-V1-2026-09-20.md`. Owner order this session: KEEP BUILDING WITHOUT MATT, lane `ggv-intercompany-client-v1` on mission `owner-autonomous-20260920-w9`, after `amg-revenue-yield-v1` DONE (`ce6fe39` / `1fd4931`). `CR-6a19c9221cab0178` stays OPEN.

**Status:** the intercompany client-mode skeleton is on Beta `:8788`. It names service record, invoice, allocation, arms-length, AR/AP, and notes slots and leaves every slot empty. An empty framework is not live intercompany billing and not proof of GGV, AMG, and BZG client machinery. Invoices, allocations, AR/AP balances, and tax treatment are not recorded. Not PROVEN. Not READY. The live ledger row for `CAP-GGV-06` is **SPECIFIED**. This slice did not rewrite it. The ceiling label is **BUILT**. `CR-6a19c9221cab0178` stays **OPEN**. Bound `beta-ggv-ops-safe`.

## What landed

- `scripts/core/ggv_intercompany_client.py` — Owner read of the skeleton. Schema `wolf.cap-ggv-06.intercompany-client.v1` names the six slots and accepts no writes. `service_record`, `invoice`, `allocation`, `arms_length`, `ar_ap`, and `tax_treatment` stay null. `tax_claimed`, `live_billing`, and `client_machinery` stay false. No framework file is created. `CR-6a19c9221cab0178` is read and not written.
- `scripts/serve_beta.py` — `GET /api/ggv/intercompany-client`, `/schema`, `/kinds`, `/framework`, and `/<kind>` plus `GET /ggv-intercompany-client` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST /payment` is `payment_refused`. `POST /bank` is `bank_refused`. `POST /zayen` and `POST /books` are `books_refused`. `POST /tax` is `tax_refused`. `POST /invoice`, `POST /allocation`, `POST /ar-ap`, `POST /arms-length`, `POST /service-record`, and `POST /current` are `current_refused`. `POST /cloudflare` is `cloudflare_refused`. `POST /access` is `access_refused`. `POST /prove` is `proven_refused`. `POST /ready` is `ready_refused`. `POST /resolve` is `resolve_refused`. `POST /production` is `production_refused`. `POST /score` is `score_refused`. `POST /alchemist` is `alchemist_refused`. `POST /fill`, `POST /note`, and `POST /notes` are `slots_refused`. Bare `POST`, `PUT`, and `PATCH` are 405 `writes_refused`.
- `dashboards/ggv-intercompany-client.html` — Owner page. It says an empty framework is not live intercompany billing and not proof of GGV, AMG, and BZG client machinery, not PROVEN, not READY, CAP-GGV-06 stays SPECIFIED, the ceiling label is BUILT, no invented invoices, allocations, or AR/AP, no tax treatment claim, no money move, Cloudflare and Access are not mutated, and the page does not resolve the completion row.
- `scripts/tests/test_ggv_intercompany_client.py` — empty framework, refuse paths, ceiling, CR bind, WIP four.
- `state/build-claims/2026-09-20.json` — claim `bf-ggv-intercompany-client-v1-20260920`.

No invoice, allocation, AR/AP balance, service record, arms-length evidence, or tax treatment was stored. No payment was executed. No bank write. No Zayen or books write. No Cloudflare or Access call. No Production write. No Alchemist write. The completion row was not resolved. The revenue-yield, client-profitability, and strategy-machine modules were not edited.

## Honesty (bound to the CR)

`CR-6a19c9221cab0178` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Intercompany client mode implementation`. That next-action text is the stored row. This slice does not resolve the CR and does not write the ledger.

- Live `CAP-GGV-06` ledger state is SPECIFIED. The ceiling label is BUILT. A fixture that is already PROVEN is reported as PROVEN with ceiling BUILT and is not written back. A fixture that is already READY is reported as READY with ceiling BUILT and is not written back. A fixture marked GREEN is reported as UNKNOWN, not as a pass. This slice does not invent PROVEN or READY on the live row.
- The live payload has `recorded_count` 0, `empty` true, `empty_is_billing` false, `empty_is_client_machinery` false, `live_billing` false, `client_machinery` false, `invoice` null, `allocation` null, `ar_ap` null, `tax_treatment` null, `tax_claimed` false, `current` false, `payment_executed` false, and `cr_resolved` false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Content-library media `assets` count unchanged. Live framework file absent.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`. Those files were already dirty versus HEAD before this slice. This slice did not edit them.

No Production (`:8787`). No Alchemist write. No score change. No invented invoices, allocations, AR/AP, or tax treatment. No payment. No Cloudflare or Access mutation.

## Prove

`python3 scripts/tests/test_ggv_intercompany_client.py` → `PASS=257 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200 before and after. Production process was not restarted.
- `:8788` restarted, listener pid `25408` (was `23093`). `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/ggv/intercompany-client` → 403
- `curl http://127.0.0.1:8788/ggv-intercompany-client` → 403
- Ledger `CAP-GGV-06` SPECIFIED, 77 rows. CR state OPEN, next action `Intercompany client mode implementation`. Live framework file absent.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
