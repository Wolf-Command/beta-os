# CURSOR MISSION — Integration Health read-only

Date: 2026-09-19
Repo: /Users/wolfterminal/beta-os
Branch: build/wolf-command-rebuild
HEAD at start of this slice: bc8ec65
Bound: beta-integration-health-readonly
Decision: dated plan `docs/deliveries/GROK-PLAN-INTEGRATION-HEALTH-READONLY-2026-09-19.md`. No matching line in `~/.openclaw/wolf-output/decisions.md`.

This is a technical prove. It is not a Model C promotion.

## Do not

- Do not write Metricool, ESB, Cloudflare seats, or Alchemist.
- Do not probe Gmail, Drive, Calendar, bank imports, or JWKS.
- Do not invent GREEN or treat a missing file as readable.
- Do not edit the Model C ledger or score history. CAP-INTG-01 stays ABSENT. CAP-INTG-07 stays SPECIFIED.
- Do not touch the WIP four: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- Do not touch Production `:8787` or wolf-system.

## What landed

- `scripts/core/integration_health.py` — local reads only.
- `GET /api/integration-health` and `GET /integration-health` on Beta. Owner (`PERS-MATT` via `resolve_request_identity`) only. Unauth 403.
- `POST /api/integration-health` is 403 unauth and 405 `writes_refused` for Owner.
- Page: `dashboards/integration-health.html`.

Status vocabulary is only UNKNOWN, NOT_CONFIGURED, READ_OK, DEGRADED, ERROR.

| Cap | Source | Rule |
| --- | --- | --- |
| CAP-INTG-01 Yanolja | none | NOT_CONFIGURED. Ledger note stays ABSENT. |
| CAP-INTG-02 ESB | `esb_close_snapshot` readonly open | Missing file NOT_CONFIGURED. `sales` present READ_OK. Table missing DEGRADED. wolf-system path ERROR. |
| CAP-INTG-03 Google Workspace | none | NOT_CONFIGURED. Not probed. |
| CAP-INTG-04 Bank statement | none | NOT_CONFIGURED. Not probed. |
| CAP-INTG-05 Metricool | `metricool_status()` only | Disabled or no path NOT_CONFIGURED. Path set but unread UNKNOWN. Never READ_OK from status(). |
| CAP-INTG-06 Registries | none | NOT_CONFIGURED. |
| CAP-INTG-07 Separation | local file checks | Missing `.env.example` NOT_CONFIGURED. Checks pass READ_OK as config-file evidence only. Not a vault. Ledger stays SPECIFIED. |

Extra sources on the same payload, not extra caps: Cloudflare Access config presence (no JWKS) and Alchemist readonly file flag (no purchase projection, no write).

## Prove

`python3 scripts/tests/test_integration_health.py` → `PASS=69 FAIL=0`.

That run included Owner `GET /api/integration-health` 200, Owner `GET /integration-health` 200, anon and staff 403, Owner POST 405, CAP-INTG-01 NOT_CONFIGURED, ledger bytes unchanged, CAP-INTG-01 ABSENT, CAP-INTG-07 SPECIFIED, 77 rows, WIP four hashes unchanged.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listening True (PID left untouched)
- `:8788` listening True
- `curl http://127.0.0.1:8788/api/integration-health` → 403 `missing_auth` (cloudflare_access, no JWT in this shell)
- `curl http://127.0.0.1:8788/integration-health` → 403
- `POST` same path → 403
- Response body does not contain GREEN

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

## Not done

- No Model C write.
- No live Metricool, ESB, or Alchemist mutation.
- No JWT-authenticated browser pass on the public Access hostname.
