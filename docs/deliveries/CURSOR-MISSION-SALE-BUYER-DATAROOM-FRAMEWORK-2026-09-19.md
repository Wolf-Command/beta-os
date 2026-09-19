# CURSOR MISSION — CAP-SALE-02 Buyer data room framework — 2026-09-19

**Decision served:** 2026-09-20 PICK, buyer data room framework on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-SALE-BUYER-DATAROOM-FRAMEWORK-2026-09-19.md`). Owner lane `sale-buyer-dataroom-framework`.

**Status:** empty folder tree and checklist are on Beta `:8788`. Not PROVEN. Not READY. Not a live share. Model C maturity not raised. `CAP-SALE-02` stays **SPECIFIED**. `CR-766f242208e401ad` stays **OPEN**.

## What landed

- `scripts/core/sale_buyer_dataroom.py` — Owner framework. Names a virtual root `VDR` and six required folders (Finance, HR, Legal, Ops, Compliance, Tech). Checklist slots come from the 60 diligence controls in `docs/canon/build-dashboard/Sale_Readiness.csv`. Every slot stays empty. A source evidence cell is not copied into a document. Growth opportunities stays unmapped rather than being forced into a folder. Nothing is written to disk.
- `scripts/serve_beta.py` — `GET /api/buyer-dataroom`, `GET /api/buyer-dataroom/tree`, `GET /api/buyer-dataroom/checklist`, `GET /api/buyer-dataroom/<folder>`, `GET /buyer-dataroom` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST` and `PUT` are 405 `writes_refused` for Owner. Live share, export, and buyer grant are refused. `POST /api/vdr/export` stays the CAP-SALE-01 refuse.
- `dashboards/buyer-dataroom.html` — Owner page. It says empty slots stay empty, no buyer access, and live share is refused.
- `scripts/tests/test_sale_buyer_dataroom.py` — empty slots, refuse paths, CR bind, ceiling, WIP four.

No buyer was granted. No share link. No export file. No filled document.

## Honesty (bound to the CR)

`CR-766f242208e401ad` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Continuously updated VDR product`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-SALE-02` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN or READY is reported as that state and is not written back.
- Live checklist slots are empty. `empty_slots` is 60, `filled_slots` is 0, `document_count` is 0, `buyer_count` is 0. A fixture status word of PROVEN with an evidence filename stays EMPTY and the filename is not copied.
- `CAP-SALE-01` and `CAP-SALE-03` stay SPECIFIED. Credits table unchanged. Ledger stays 77 rows. Score history unchanged. Resolved CR count unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_sale_buyer_dataroom.py` → `PASS=148 FAIL=0`.

`python3 scripts/tests/test_sale_evidence_pack.py` → `PASS=116 FAIL=0` after the Beta route edit.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `59179`
- `curl http://127.0.0.1:8788/api/buyer-dataroom` → 403
- `curl http://127.0.0.1:8788/buyer-dataroom` → 403
- `POST http://127.0.0.1:8788/api/vdr/share` → 403 (no JWT in this shell; Owner 405 `vdr_share_refused` is the same handler in the test)
- Ledger `CAP-SALE-01` SPECIFIED, `CAP-SALE-02` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`. The Owner page was not clicked in a browser.
