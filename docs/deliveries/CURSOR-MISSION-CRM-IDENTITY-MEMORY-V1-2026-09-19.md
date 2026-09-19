# CURSOR MISSION — CAP-CRM-02 Customer identity & memory v1 — 2026-09-19

**Decision served:** 2026-09-19 PICK, customer identity and memory v1 on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-CRM-IDENTITY-MEMORY-V1-2026-09-19.md`). Owner lane `crm-identity-memory-v1`.

**Status:** bounded slice is on Beta `:8788`. Not PROVEN. Not a complete identity graph. Model C maturity not raised. `CAP-CRM-02` stays **SPECIFIED**. `CR-820682ce791563fa` stays **OPEN**.

## What landed

- `scripts/core/crm_identity_memory.py` — a customer record (`CUST-`) that is not a lead (`LEAD-`) and not an `org_persons` row. Append-only memory notes. A correction is a new note. Owner can read every entity. Staff can read only when `crm.identity.read` is already granted, and a staff list requires an entity. No live role grant was inserted.
- `scripts/migrations/migrate_crm_identity_permissions.py` — adds `crm.identity.read`, `crm.identity.note`, `crm.identity.register`. Role grants stay 0.
- `scripts/serve_beta.py` — `GET/POST /api/crm/identity`, `POST /api/crm/identity/note`, `POST /api/crm/identity/link`, `POST /api/crm/identity/merge`, `GET /crm-identity` on `:8788`. Anonymous is 403. Marketing blast paths are 405 `marketing_refused` for Owner. `PUT` is 405 `append_only`. A `LEAD-` id is 404 `not_a_customer`.
- `dashboards/crm-identity.html` — Owner/staff page. It says this is not a complete identity graph and there is no marketing blast.
- `scripts/tests/test_crm_identity_memory.py` — distinct from lead, append-only, merge without evidence refused, evidence does not collapse rows, blast refused, CR bind, ceiling, WIP four.

Same display name does not merge two customers. Evidence on a merge records `REVIEW_REQUIRED` and leaves both rows. A lead pointer is an unverified candidate, not a customer.

## Honesty (bound to the CR)

`CR-820682ce791563fa` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Identity graph`, resolution empty. This slice does not resolve the CR and does not write the ledger.

- `CAP-CRM-02` ledger state stays SPECIFIED. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back.
- `identity_graph_complete` is false. `merged` is false. `marketing_blast` is false.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged. `core_leads` and `org_persons` were not inserted by this slice.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No marketing send.

## Prove

`python3 scripts/tests/test_crm_identity_memory.py` → `PASS=103 FAIL=0`.

Permission migration on the Beta catalog: `crm.identity perms=3; role_grants=0`. CR state remained OPEN.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `50406`
- `curl http://127.0.0.1:8788/api/crm/identity` → 403 `missing_auth`
- `curl http://127.0.0.1:8788/crm-identity` → 403 `missing_auth`
- `POST http://127.0.0.1:8788/api/marketing/blast` → 403 `missing_auth` (no JWT in this shell; Owner 405 `marketing_refused` is the same handler in the test)

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path, staff 403, append-only PUT, and merge-without-evidence 400 were proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`. Logged-in browser layout was not opened.
