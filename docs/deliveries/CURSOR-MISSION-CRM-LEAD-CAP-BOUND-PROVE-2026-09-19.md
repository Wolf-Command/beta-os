# CURSOR MISSION — CAP-CRM-01 Lead CRM bound prove — 2026-09-19

**Decision served:** 2026-09-19 owner correction `keep_building_without_matt` (lane `crm-lead-cap-bound-prove`). Extends already-BUILT CAP-CRM-01. Not a new system. Plan `docs/deliveries/GROK-PLAN-CRM-LEAD-CAP-BOUND-PROVE-2026-09-19.md`.

**Status:** bound prove is on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-CRM-01` stays **BUILT**. `CR-ff42f3a7c49caa79` stays **OPEN** (`NEEDS_ENGINEERING`).

## What landed

- `scripts/core/crm_lead_cap_prove.py` — read-only red-team. A brand-scoped read that contains another brand, or a row with no entity, fails closed. Unread is not zero. An empty brand read is empty, not an invented lead. Closed, claimed, and verified are counted and are not a sale. No SLA number is computed.
- Atrium is named by the ledger and has no `core_leads` rows on Beta. That surface is **ABSENT**. The count is not reported as zero and is not an operating board.
- Habitat rows are read without email, source id, or the provenance blob. The Klaviyo reader is not imported and `run_ingest` is not called. Metricool write is refused.
- `scripts/serve_beta.py` — `GET /api/crm/lead-cap-prove` and `GET /crm-lead-cap-prove` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. Owner `POST`, `PUT`, and `PATCH` are 405. `POST .../klaviyo` is `klaviyo_write_refused`. `POST .../metricool` is `metricool_write_refused`. `POST .../leads` is `invent_lead_refused`.
- `dashboards/crm-lead-cap-prove.html` — Owner page. It does not promote the CAP and does not invent a lead.
- `scripts/tests/test_crm_lead_cap_prove.py` — bounds, refusals, CR bind, ceiling, WIP four.

No lead row was inserted. No Klaviyo page was fetched. No Metricool call was made.

## Honesty (bound to the CR)

`CR-ff42f3a7c49caa79` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `CAP-bound tests/red-team`. This slice is that prove pack. It does not resolve the CR and does not write the ledger. The ledger missing-for-next cell is still `CAP-bound tests/red-team`.

- `CAP-CRM-01` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back.
- `CAP-CRM-02` is not this prove.
- `AU-CRM-01-HABITAT` was read as `NOT STARTED`. It was not commissioned.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Gaps still open

- Atrium board: ABSENT on Beta. Not zero.
- Habitat rows read by this pack are demo fixtures, not a live operating board.
- Klaviyo write path exists in the reader and was not called. Network ingest was not run.
- Metricool write refused.
- Model E unit still `NOT STARTED`.
- Ledger gap text left as read.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_crm_lead_cap_prove.py` → `PASS=114 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `42982`
- `curl http://127.0.0.1:8788/api/crm/lead-cap-prove` → 403
- `curl http://127.0.0.1:8788/crm-lead-cap-prove` → 403
- `POST` same API path → 403
- Ledger `CAP-CRM-01` first field remains `BUILT`. Gap cell remains `CAP-bound tests/red-team`. 77 rows.
- `CR-ff42f3a7c49caa79` remains `OPEN`

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
