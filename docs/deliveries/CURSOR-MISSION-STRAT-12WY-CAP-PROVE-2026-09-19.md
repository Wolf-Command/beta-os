# CURSOR MISSION — CAP-STRAT-01 12WY deterministic prove — 2026-09-19

**Decision served:** 2026-09-19 owner correction `keep_building_without_matt` (lane `strat-12wy-cap-prove`). Extends already-BUILT CAP-STRAT-01. Not a new system. Plan `docs/deliveries/GROK-PLAN-STRAT-12WY-CAP-PROVE-2026-09-19.md`.

**Status:** prove pack is on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-STRAT-01` stays **BUILT**. `CR-6535f7cb02370850` stays **OPEN** (`NEEDS_ENGINEERING`).

## What landed

- `scripts/core/strat_12wy_prove.py` — read-only prove. LOCK C: planned 0 is EMPTY and has no percent. On-track only when evidenced done/planned is at least 85. A tactic counts only with an explicit 12WY flag and a matching week. Done counts only when status is `done`.
- Radar binding is the existing `radar_board.py` text (`weekly_scorecard`, `score_tactics`, `SCORE_LOCK_PCT = 85`). The file is not imported and not executed. `create_task` is not called.
- Wolf tasks are read from `wolf-desk/tasks.json` when that file is present. The Wolf desk reader is not called, because that reader can write. A missing or unreadable file is `NOT_READ`, not EMPTY and not 0%.
- Helm binding is the dated coach pack `dashboards/deliveries/12wy-2026-09-18.html`. It states EMPTY, week 2, planned 0, done 0. That pack is not treated as a new score.
- `scripts/serve_beta.py` — `GET /api/strat/12wy-prove` and `GET /12wy-prove` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH` are 405 `writes_refused` for Owner.
- `dashboards/12wy-prove.html` — Owner page. It does not paint a percent when the score is EMPTY.
- `scripts/tests/test_strat_12wy_prove.py` — contract, filters, CR bind, ceiling, WIP four.

Live week-2 tasks on this machine scored EMPTY (planned 0, percent absent). That is the read. No tactic row was inserted.

## Honesty (bound to the CR)

`CR-6535f7cb02370850` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Deterministic CAP prove`. This slice is that prove pack. It does not resolve the CR and does not write the ledger.

- `CAP-STRAT-01` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back.
- `CAP-STRAT-02` is not this prove. Progress was not used as a substitute score.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_strat_12wy_prove.py` → `PASS=100 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listening True. `GET /api/health` → 200. Production process was not restarted.
- `:8788` listening True
- `curl http://127.0.0.1:8788/api/strat/12wy-prove` → 403 `missing_auth`
- `curl http://127.0.0.1:8788/12wy-prove` → 403
- `POST` same API path → 403
- Ledger `CAP-STRAT-01` first field remains `BUILT`
- `CR-6535f7cb02370850` remains `OPEN`

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.
