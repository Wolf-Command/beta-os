# CURSOR MISSION — CAP-SALE-04 Buyer attack and transition readiness framework — 2026-09-19

**Decision served:** 2026-09-20 PICK, buyer attack and transition readiness framework on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-SALE-ATTACK-AUDIT-FRAMEWORK-2026-09-19.md`). Owner lane `sale-attack-audit-framework`.

**Status:** named audit sections, empty transition-pack slots, and the preserved Wolf licence boundary are on Beta `:8788`. Not PROVEN. Not READY. Not a live attack, filled pack, or buyer grant. Model C maturity not raised. `CAP-SALE-04` stays **SPECIFIED**. `CR-c6e1a48e4a3e8a91` stays **OPEN**.

## What landed

- `scripts/core/sale_attack_audit.py` — Owner framework. Names 30 company-specific audit sections (GGV, AMG, BZG × the ten CAP-SALE-04 control areas, including Growth opportunities). Source text is not copied. Controls that are not those areas stay outside the audit and are not packed. An unexpected company is not approved. Twelve transition-pack slots stay empty (shared-service continuity, transition services, post-sale obligations, transaction permissions × three companies). The Wolf licence post-sale boundary stays preserved: no licence grant, no Wolf IP transfer, no architecture copy. Nothing is written to disk.
- `scripts/serve_beta.py` — `GET /api/attack-audit`, `GET /api/attack-audit/sections`, `GET /api/attack-audit/packs`, `GET /api/attack-audit/licence`, `GET /api/attack-audit/<id>`, `GET /attack-audit` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner. Run, fill, grant, share, transfer, and export are refused.
- `dashboards/attack-audit.html` — Owner page. It says audit sections are named, transition-pack slots stay empty, the Wolf licence stays preserved, and there is no buyer grant.
- `scripts/tests/test_sale_attack_audit.py` — named sections, empty packs, closed licence, refuse paths, CR bind, ceiling, WIP four.

No attack was run. No pack was filled. No buyer was granted. No licence was granted. No finding was invented.

## Honesty (bound to the CR)

`CR-c6e1a48e4a3e8a91` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Attack audit + transition pack`. This slice is the framework skeleton. It does not resolve the CR and does not write the ledger.

- `CAP-SALE-04` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN or READY is reported as that state and is not written back.
- Live transition-pack slots are empty. `empty_packs` is 12, `filled_packs` is 0, `buyer_count` is 0. A fixture status word of PROVEN with an evidence filename stays off the surface and the filename is not copied.
- `CAP-SALE-01`, `CAP-SALE-02`, and `CAP-SALE-03` stay SPECIFIED. Ledger stays 77 rows. Score history unchanged. Resolved CR count unchanged.

## Gaps

No live attack run. No filled transition pack. No licence grant. Ask of weaknesses is not answered. Wolf IP is not copied. The completion row is not closed.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_sale_attack_audit.py` → `PASS=170 FAIL=0`.

`python3 scripts/tests/test_sale_buyer_mode.py` → `PASS=170 FAIL=0`.

`python3 scripts/tests/test_sale_evidence_pack.py` → `PASS=116 FAIL=0`.

`python3 scripts/tests/test_sale_buyer_dataroom.py` → `PASS=148 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `71407`. `GET /api/health` → 200.
- `curl http://127.0.0.1:8788/api/attack-audit` → 403
- `curl http://127.0.0.1:8788/attack-audit` → 403
- `POST http://127.0.0.1:8788/api/attack-audit/run` → 403
- Ledger `CAP-SALE-04` SPECIFIED, 77 rows. CR state OPEN, next action unchanged.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`. The Owner page was not clicked in a browser.
