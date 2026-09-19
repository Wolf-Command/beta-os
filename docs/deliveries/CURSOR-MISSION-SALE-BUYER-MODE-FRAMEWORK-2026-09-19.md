# CURSOR MISSION — CAP-SALE-03 Buyer mode / controlled export framework — 2026-09-19

**Decision served:** 2026-09-20 PICK, buyer mode / controlled export framework on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-SALE-BUYER-MODE-FRAMEWORK-2026-09-19.md`). Owner lane `sale-buyer-mode-framework`.

**Status:** named surfaces, hidden classes, and empty export slots are on Beta `:8788`. Not PROVEN. Not READY. Not a live grant, share, or export. Model C maturity not raised. `CAP-SALE-03` stays **SPECIFIED**. `CR-b428ac5cbc8986b5` stays **OPEN**.

## What landed

- `scripts/core/sale_buyer_mode.py` — Owner framework. Names 18 company-specific diligence surfaces (GGV, AMG, BZG × Finance, HR, Legal, Ops, Compliance, Tech) and 3 company-specific Ask context slots. Source text is not copied. Growth opportunities stays unmapped and is not exported. An unexpected company is not approved. Four hides stay closed by default: full Wolf backup playbook, Technology and Provider Registry, generic Wolf IP and architecture, and cross-company intelligence. Twenty-one export slots stay empty. Nothing is written to disk.
- `scripts/serve_beta.py` — `GET /api/buyer-mode`, `GET /api/buyer-mode/surfaces`, `GET /api/buyer-mode/hides`, `GET /api/buyer-mode/exports`, `GET /api/buyer-mode/<id>`, `GET /buyer-mode` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. Grant, share, reveal, blend, and fill are refused. `GET /api/buyer-mode/export` stays the earlier `buyer_export_refused` path.
- `dashboards/buyer-mode.html` — Owner page. It says approved surfaces are named, crown jewels stay hidden, cross-company intelligence stays hidden, export slots stay empty, and there is no buyer grant.
- `scripts/tests/test_sale_buyer_mode.py` — named surfaces, closed hides, empty exports, refuse paths, CR bind, ceiling, WIP four.

No buyer was granted. No share link. No export file. No Ask answer was copied. No hide was opened.

## Honesty (bound to the CR)

`CR-b428ac5cbc8986b5` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Buyer mode implementation`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-SALE-03` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN or READY is reported as that state and is not written back.
- Live export slots are empty. `empty_exports` is 21, `filled_exports` is 0, `buyer_count` is 0. A fixture status word of PROVEN with an evidence filename stays off the surface and the filename is not copied.
- `CAP-SALE-01`, `CAP-SALE-02`, and `CAP-SALE-04` stay SPECIFIED. Ledger stays 77 rows. Score history unchanged. Resolved CR count unchanged.

## Gaps

No live buyer grant. No live share. No controlled export of real data. Ask context is a name only. Crown-jewel contents are not read. Cross-company intelligence is not blended. The completion row is not closed.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_sale_buyer_mode.py` → `PASS=170 FAIL=0`.

`python3 scripts/tests/test_sale_evidence_pack.py` → `PASS=116 FAIL=0`.

`python3 scripts/tests/test_sale_buyer_dataroom.py` → `PASS=148 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `68426`. `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/buyer-mode` → 403
- `curl http://127.0.0.1:8788/buyer-mode` → 403
- `curl http://127.0.0.1:8788/api/buyer-mode/export` → 403
- `POST http://127.0.0.1:8788/api/buyer-mode/grant` → 403
- Ledger `CAP-SALE-03` SPECIFIED, 77 rows. CR state OPEN.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`. The Owner page was not clicked in a browser.
