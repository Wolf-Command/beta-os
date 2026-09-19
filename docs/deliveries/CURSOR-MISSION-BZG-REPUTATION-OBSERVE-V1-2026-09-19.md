# CURSOR MISSION — CAP-BZG-07 Reputation observe v1 — 2026-09-19

**Decision served:** 2026-09-19 PICK, reputation observe v1 on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-BZG-REPUTATION-OBSERVE-V1-2026-09-19.md`). Owner lane `bzg-reputation-observe-v1`.

**Status:** observe skeleton is on Beta `:8788`. Not PROVEN. No review source is connected. Model C maturity not raised. `CAP-BZG-07` stays **SPECIFIED**. `CR-d1aacda59180eba7` stays **OPEN**.

## What landed

- `scripts/core/bzg_reputation_observe.py` — Owner or already-authorised staff can read an empty honesty view, or store one append-only observation with provenance. No connector. `summary_rating` stays null. A missing rating is stored as null, not 5. Scrape and guest reply raise. The ledger is read, not written.
- `scripts/migrations/migrate_bzg_reputation_permissions.py` — adds `bzg.reputation.read` and `bzg.reputation.observe`. Role grants stay 0.
- `scripts/serve_beta.py` — `GET /api/bzg/reputation`, `POST /api/bzg/reputation/observe`, `GET /bzg-reputation` on `:8788`. Anonymous is 403. Scrape, reply, and summary post are 405 after auth. `PUT` is 405 `append_only`.
- `dashboards/bzg-reputation.html` — says Wolf does not solicit reviews, no source is connected, no star rating is invented, there is no scrape and no reply to guests.
- `scripts/tests/test_bzg_reputation_observe.py` — empty when no source, no invented 5-star, scrape refused, auto-reply refused, CR bind, ceiling, WIP four.

A human-supplied `observed_rating` of 5 is stored on that row only. It does not become a reputation summary.

## Honesty (bound to the CR)

`CR-d1aacda59180eba7` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Observe/ingest path`, resolution empty. This slice does not resolve the CR and does not write the ledger.

- `CAP-BZG-07` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN or READY is reported as that state and is not written back.
- `source_connected` is false. `configured_sources` is empty. `summary_rating` is null. `five_star_invented` is false. `scraped` is false. `auto_reply` is false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. No live `catalog/bzg_reputation.sqlite` was created by the tests.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No scrape. No guest reply.

## Prove

`python3 scripts/tests/test_bzg_reputation_observe.py` → `PASS=112 FAIL=0`.

Permission migration on the Beta catalog: `bzg.reputation perms=2; role_grants=0`. CR state remained OPEN. Ledger `CAP-BZG-07` remained SPECIFIED, 77 rows.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `53359`
- `curl http://127.0.0.1:8788/api/bzg/reputation` → 403 `missing_auth`
- `curl http://127.0.0.1:8788/bzg-reputation` → 403
- `POST http://127.0.0.1:8788/api/bzg/reputation/scrape` → 403 `missing_auth`

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner empty 200, scrape 405, reply 405, stars 400, and append-only PUT were proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`. Logged-in browser layout was not opened.
