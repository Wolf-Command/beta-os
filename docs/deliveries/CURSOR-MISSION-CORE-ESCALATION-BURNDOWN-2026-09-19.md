# CURSOR MISSION — CAP-CORE-12 escalation burn-down — 2026-09-19

**Decision served:** 2026-09-19 PICK, CAP-CORE-12 escalation burn-down counters on Beta only (`~/.openclaw/wolf-output/decisions.md`). Extends already-BUILT CAP-CORE-12. Not a new system. Plan `docs/deliveries/GROK-PLAN-CORE-ESCALATION-BURNDOWN-2026-09-19.md`.

**Status:** counters are on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-CORE-12` stays **BUILT**. `CR-6e3fd7b9d7edca0e` stays **OPEN** (`NEEDS_ENGINEERING`).

## What landed

- `scripts/core/escalation_burndown.py` — read-only 7/30/90/365 counters. Accidental founder dependency is unresolved `NEEDS_MATT` only. Intentional authority is a delegation with both `effective_from` and `effective_to`. An unread source stays blank, not zero. An empty register is `EMPTY`, not independence. A resolved Needs Matt row without resolution evidence is refused and is not a burn-down.
- `scripts/serve_beta.py` — `GET /api/core/escalation-burndown` and `GET /escalation-burndown` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST`, `PUT`, and `PATCH`, including `/clear`, are 405 `writes_refused`. Nothing resolves a completion row.
- `dashboards/escalation-burndown.html` — Owner page. It does not promote the capability and does not clear Needs Matt.
- `scripts/tests/test_escalation_burndown.py` — windows, silent-clear refusal, CR bind, ceiling, WIP four.

Live read of the catalog: 103 completion rows, 0 unresolved Needs Matt, 0 delegations, 0 silent clears. All four windows read `CLEAR`. That is the register. It is not an operating independence test and it does not promote `CAP-CORE-12`.

## Honesty (bound to the CR)

`CR-6e3fd7b9d7edca0e` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Escalation burn-down + 7/30/90/365 independence tests`. This slice is those counters. It does not resolve the CR and does not write the ledger. The CR was not reclassified as Needs Matt.

- `CAP-CORE-12` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write. No silent auto-clear of Needs Matt.

## Prove

`python3 scripts/tests/test_escalation_burndown.py` → `PASS=117 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listening True. `GET /api/health` → 200. Production process was not restarted.
- `:8788` listening True
- `curl http://127.0.0.1:8788/api/core/escalation-burndown` → 403
- `curl http://127.0.0.1:8788/escalation-burndown` → 403
- `POST` same API path → 403
- Ledger `CAP-CORE-12` first field remains `BUILT`. Ledger rows remain 77.
- `CR-6e3fd7b9d7edca0e` remains `OPEN` / `NEEDS_ENGINEERING`
- Unresolved Needs Matt count remains 0

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.
