# CURSOR MISSION — CAP-INTG-06 Tech & Capability Registry — 2026-09-19

**Decision served:** 2026-09-19 PICK, Tech & Capability Registry on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-INTG-TECH-CAPABILITY-REGISTRY-2026-09-19.md`). Owner lane `intg-tech-capability-registry`.

**Status:** read-only slice is on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-INTG-06` stays **SPECIFIED**. `CR-44ffb6a57469ff25` stays **OPEN**.

## What landed

- `scripts/core/tech_capability_registry.py` — Owner registry. Seeds 77 capabilities from `docs/MODEL-C-CAPABILITY-CATALOG.md`, ledger maturity from `state/model-c-baseline-assessments.json` (read only), and known connectors/technologies. Connector health is copied from a local Integration Health read or left `NOT_CONFIGURED` when this registry did not probe. Exit notes are ownership or system facts. Replace notes say no replacement is recorded.
- `scripts/serve_beta.py` — `GET /api/tech-registry`, `GET /api/tech-registry/<id>`, `GET /tech-registry` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. `POST` and `PUT` are 405 `writes_refused` for Owner.
- `dashboards/tech-registry.html` — Owner page. It does not paint a health colour the vocabulary does not allow.
- `scripts/tests/test_tech_capability_registry.py` — seed, refuse paths, CR bind, ceiling, WIP four.

Known connectors: Yanolja, ESB, Google Workspace, bank statement file import, Metricool, Klaviyo, ActiveCampaign. Technologies also include Cloudflare Access and Alchemist. Klaviyo and ActiveCampaign are not conflated and were not called. Alchemist is not written.

## Honesty (bound to the CR)

`CR-44ffb6a57469ff25` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Tech inventory + exit conditions product`. This slice is the read registry. It does not resolve the CR and does not write the ledger.

- `CAP-INTG-06` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back.
- A health token outside UNKNOWN / NOT_CONFIGURED / READ_OK / DEGRADED / ERROR, including a healthy-colour token, becomes ERROR and is not copied into the payload.
- `CAP-INTG-01` stays ABSENT. Credits table unchanged. Ledger stays 77 rows. Score history unchanged.
- Integration Health still reports CAP-INTG-06 as NOT_CONFIGURED. That panel was not rewired in this slice, so it does not pretend the registry is a connector prove.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_tech_capability_registry.py` → `PASS=96 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listening True. `GET /api/health` → 200. Production process was not restarted.
- `:8788` listening True
- `curl http://127.0.0.1:8788/api/tech-registry` → 403 `missing_auth` (cloudflare_access, no JWT in this shell). Body does not contain GREEN.
- `curl http://127.0.0.1:8788/tech-registry` → 403
- `POST` same API path → 403

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.
