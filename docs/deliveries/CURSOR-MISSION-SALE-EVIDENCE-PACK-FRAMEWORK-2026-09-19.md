# CURSOR MISSION — CAP-SALE-01 Sale evidence pack framework — 2026-09-19

**Decision served:** 2026-09-19 PICK, sale evidence pack framework on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-SALE-EVIDENCE-PACK-FRAMEWORK-2026-09-19.md`). Owner lane `sale-evidence-pack-framework`.

**Status:** read-only skeleton is on Beta `:8788`. Not PROVEN. Not a buyer data room. Model C maturity not raised. `CAP-SALE-01` stays **SPECIFIED**. `CR-b7ce6d6668848b6e` stays **OPEN**.

## What landed

- `scripts/core/sale_evidence_pack.py` — Owner framework. Lists Finance, HR, Legal, Ops, Compliance, and Tech as required source domains. Reads the 60 diligence controls from `docs/canon/build-dashboard/Sale_Readiness.csv`. An empty evidence cell stays empty. A current-state or target sentence is not evidence. Growth opportunities stays unmapped rather than being forced into a domain.
- `scripts/serve_beta.py` — `GET /api/sale-evidence-pack`, `GET /api/sale-evidence-pack/domains`, `GET /api/sale-evidence-pack/<id>`, `GET /sale-evidence-pack` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST` and `PUT` are 405 `writes_refused` for Owner. `POST /api/vdr/export` is `vdr_export_refused`. `GET /api/buyer-mode/export` is `buyer_export_refused`.
- `dashboards/sale-evidence-pack.html` — Owner page. It says empty slots stay empty and buyer export is refused.
- `scripts/tests/test_sale_evidence_pack.py` — empty slots, refuse paths, CR bind, ceiling, WIP four.

CAP-SALE-02, CAP-SALE-03, and CAP-SALE-04 were not built. No VDR file. No buyer export.

## Honesty (bound to the CR)

`CR-b7ce6d6668848b6e` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Evidence pack automation consuming domains`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-SALE-01` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back.
- Live source cells are empty. `empty_slots` is 60 and `filled_slots` is 0. A fixture status word of PROVEN with an empty evidence cell stays EMPTY and is not treated as proved.
- `CAP-SALE-02` stays SPECIFIED. Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_sale_evidence_pack.py` → `PASS=116 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `36736`
- `curl http://127.0.0.1:8788/api/sale-evidence-pack` → 403
- `curl http://127.0.0.1:8788/sale-evidence-pack` → 403
- `POST http://127.0.0.1:8788/api/vdr/export` → 403 (no JWT in this shell; Owner 405 `vdr_export_refused` is the same handler in the test)
- Ledger `CAP-SALE-01` SPECIFIED, `CAP-SALE-02` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.
