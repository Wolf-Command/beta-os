# CURSOR MISSION — CAP-GGV-04 Speed-to-Lead prove — 2026-09-19

**Decision served:** 2026-09-19 owner correction `keep_building_without_matt` (lane `ggv-speed-to-lead-cap-prove`). Extends already-BUILT CAP-GGV-04. Not a new system. Plan `docs/deliveries/GROK-PLAN-GGV-SPEED-TO-LEAD-CAP-PROVE-2026-09-19.md`.

**Status:** bound prove is on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-GGV-04` stays **BUILT**. `CR-f089b11530ab4673` stays **OPEN** (`NEEDS_ENGINEERING`).

## What landed

- `scripts/core/ggv_speed_to_lead_prove.py` — read-only red-team. Habitat scope only. A non-Habitat brand, a foreign row, or a row with no entity fails closed. Unread is not zero. An empty Habitat read is empty, not an invented lead. A missing first touch stays absent. No receipt timestamp is written. No SLA target is computed. Closed is counted and is not a sale.
- Ivy is named by the ledger evidence and has no `core_leads` rows on Beta. That surface is **ABSENT**. The count is not reported as zero and is not an operating board.
- Habitat rows are read without email, source id, or the provenance blob. The Klaviyo reader is not imported and `run_ingest` is not called. ActiveCampaign has no reader file and is not called. Metricool write is refused. External CRM write is refused. The existing triage board is not executed.
- `scripts/serve_beta.py` — `GET /api/ggv/speed-to-lead-prove` and `GET /speed-to-lead-prove` on `:8788`. Owner (`PERS-MATT`) only. Anonymous and staff are 403. Owner `POST`, `PUT`, and `PATCH` are 405. `POST .../proven` is `score_refused`. `POST .../leads` is `invent_lead_refused`. `POST .../receipts` is `invent_receipt_refused`. `POST .../klaviyo` is `klaviyo_write_refused`. `POST .../metricool` is `metricool_write_refused`. `POST .../activecampaign` is `activecampaign_write_refused`. `POST .../crm` is `external_crm_write_refused`.
- `dashboards/speed-to-lead-prove.html` — Owner page. It does not promote the CAP and does not invent a lead or a receipt.
- `scripts/tests/test_ggv_speed_to_lead_prove.py` — bounds, refusals, red-team table, CR bind, ceiling, WIP four.

No lead row was inserted. No first-touch receipt was written. No Klaviyo page was fetched. No Metricool call was made. No ActiveCampaign call was made.

## Honesty (bound to the CR)

`CR-f089b11530ab4673` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Governed speed-to-lead capability with tests/red-team`. This slice is that prove pack. It does not resolve the CR and does not write the ledger. The ledger missing-for-next cell is still that sentence.

- `CAP-GGV-04` ledger state stays BUILT. Ceiling is BUILT because the ledger is not already PROVEN or READY. A fixture that is already PROVEN is reported as PROVEN and is not written back. A fixture that is already READY is reported as READY and is not written back.
- `CAP-GGV-05` is not this prove.
- `AU-GGV-04-HABITAT` was not in the adoption file. It was not commissioned. Absence is not ADOPTED.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Red team

| Case | Result |
| --- | --- |
| Invent PROVEN / READY | REFUSED — `score_refused`. Ledger not written. |
| Invent leads | REFUSED — `invent_lead_refused`. Empty is not a lead. |
| Invent first-touch receipts | REFUSED — `invent_receipt_refused`. Missing touch stays absent. |
| Write locks | REFUSED — Metricool, Klaviyo, ActiveCampaign, external CRM. |
| Anon / staff | FAIL CLOSED — live anon `GET` and `POST` are 403. Owner 200 proved on the test handler, not by a live Cloudflare session. |

## Gaps still open

- Ivy board: ABSENT on Beta. Not zero.
- Habitat rows read by this pack are demo fixtures, not a live operating board. One row already had a first touch. Seven did not. Those seven were not filled in.
- Klaviyo write path exists in the reader and was not called. Network ingest was not run.
- ActiveCampaign reader file is absent. It was not called.
- Metricool write refused. External CRM write refused.
- Model E unit `AU-GGV-04-HABITAT` still absent. Not commissioned.
- Ledger gap text left as read.
- Change request left OPEN.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change. No external write.

## Prove

`python3 scripts/tests/test_ggv_speed_to_lead_prove.py` → `PASS=159 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `74084`
- `curl http://127.0.0.1:8788/api/ggv/speed-to-lead-prove` → 403
- `curl http://127.0.0.1:8788/speed-to-lead-prove` → 403
- `curl http://127.0.0.1:8788/speed-to-lead-prove.html` → 403
- `POST` same API path → 403
- Ledger `CAP-GGV-04` first field remains `BUILT`. Gap cell remains `Governed speed-to-lead capability with tests/red-team`. 77 rows.
- `CR-f089b11530ab4673` remains `OPEN` / `NEEDS_ENGINEERING`

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

No browser pass. The page behavior was proved on the test handler, not by clicking through Cloudflare Access.
