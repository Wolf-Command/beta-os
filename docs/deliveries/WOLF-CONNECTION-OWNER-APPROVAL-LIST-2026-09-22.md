# Wolf Connection — Owner YES / NO Approval List
Date: 22 Sep 2026 ~20:35 WITA
Evidence snapshot: Beta `/Users/wolfterminal/beta-os` + Mac mounts + Integration Health readonly report.
Honesty: CONFIGURED ≠ CONNECTED ≠ TESTED ≠ COMMISSIONED. Missing = UNKNOWN.

READ approval is NOT WRITE approval.

| # | System | READ (recommend) | WRITE / EXTERNAL ACTION (recommend) | Current evidence (short) | Commissioning state |
|---|--------|------------------|-------------------------------------|--------------------------|---------------------|
| 1 | NAS (01-Media-Library + related SMB) | YES | YES for authorised Wolf Library/upload only | Mounted SMB from 192.168.77.130. `nas_status.connected=true`. ~39986 files maxdepth4 under Media Library. Smart Upload today writes `library_v2` only (`nas_received=false`). | CONNECTED mount; Library path NOT commissioned |
| 2 | Backblaze B2 | YES observe | BACKUP WRITE YES; RESTORE controlled/tested | Historical LaunchAgents + B2-only lock (18 Aug). Docs: B2-R2-MAP, B2-RESTORE-DRILL. Last successful backup / restore prove tonight = UNKNOWN. | UNKNOWN health; TARGET backup/DR |
| 3 | Google Drive / GWS | YES | WRITE controlled only; no bulk migration | Integration Health: Google Workspace NOT_CONFIGURED (no Beta-local reader probed). | UNKNOWN / NOT_CONFIGURED |
| 4 | ESB | YES | NO FOR NOW | Integration Health: READ_OK warehouse file present; settlement_api UNAVAILABLE. | READ path present; WRITE locked |
| 5 | Yanolja | YES | NO FOR NOW | Integration Health: NOT_CONFIGURED — no reader in beta-os. | NOT_CONFIGURED |
| 6 | Alchemist | YES (historical/transition) | NEW WORKFLOW WRITE NO | Integration Health: READ_OK on local db; bridge flag INACCESSIBLE; no write. | READ transitional |
| 7 | Klaviyo | YES | NO until separately commissioned | Habitat Klaviyo reader code exists. Live health tonight = UNKNOWN (not in Integration Health panel). | TRANSITIONAL / UNKNOWN live |
| 8 | Metricool | YES | PUBLISH/SCHEDULE/MODIFY NO | `.env` has Metricool flags; Integration Health: NOT_CONFIGURED because BETA_METRICOOL_ENABLED not on. Write flag separate. | WRITE LOCKED; read not live tonight |
| 9 | Email / Gmail | Authorised READ/SEARCH YES where scoped | AUTOMATED SEND NO blanket | GWS NOT_CONFIGURED in Beta health. Grok Bot Gmail connectors exist outside Beta app. | UNKNOWN in Beta; send locked by default |
| 10 | Cloudflare Access | YES (identity/access) | Admin mutation controlled | Team domain + AUD present; JWT not verified on health read → UNKNOWN. | TARGET identity infra |
| 11 | Google Sheets | YES only if still legitimate source | NEW PARALLEL WORKFLOW WRITE NO | No dedicated Beta Sheets connector prove tonight. | UNKNOWN |
| 12 | AI / model / tool providers | Controlled use inside Wolf YES | Autonomous external actions NO | `.env` keys for OpenAI/Anthropic/Gemini present (values not logged). | TARGET controlled |
| 13 | Beta infrastructure (:8788) | YES | Build/test/commission YES under governance | Live mission ACTIVE; serve_beta Content Engine + library. | COMMISSIONING surface |
| 14 | Production (:8787) | READ/OBSERVE YES where authorised | AUTONOMOUS MUTATION/DEPLOY NO | Pulse: serve.py up; sacred. | WRITE LOCKED |
| 15 | ClickUp | NO | NO | RETIRED. NAS `_clickup-attachment-archive` historical only. | RETIRED |
| 16 | Telegram | NO | NO | RETIRED. No new reads/writes/poll/sync/workflow/auth/notify. | RETIRED |

## Recommended Owner package (one tap)
Approve rows 1–14 recommendations as written; rows 15–16 stay NO/RETIRED.

## NAS go-live honesty (not a YES yet)
- READY FOR STAFF TOMORROW: **NO**
- UPLOAD PATH: Beta `library_v2` + sqlite only today — NAS placement not wired
- HAIKAL HUMAN TEST: not started
- INDEXED into Wolf Library from NAS: not started (inventory shallow only)
- BACKUP STATUS: UNKNOWN (jobs historically loaded; not proved tonight)
- RESTORE STATUS: UNKNOWN (drill docs exist; not proved tonight)

## OWNER DECISION — APPROVED
- When: 2026-09-22 20:33 WITA
- Choice: YES — approve recommended READ/WRITE package; ClickUp and Telegram stay RETIRED
- Effect: authorised commissioning work may proceed under listed READ/WRITE boundaries
- Still NOT staff-commissioned: NAS Library go-live requires engineering prove + Haikal human test
- Production autonomous mutate/deploy: still NO

