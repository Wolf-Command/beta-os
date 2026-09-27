# GROK REVIEW — CRM Ops × Needs-You Connective — 2026-09-23

- Run: `BF-crm-ops-needs-you-connective-20260923`
- Plan: `docs/deliveries/GROK-PLAN-CRM-OPS-NEEDS-YOU-CONNECTIVE-2026-09-23.md`
- Bound: `beta-crm-loop-safe` (Beta `:8788` only)
- Claim: `bf-crm-ops-needs-you-connective-20260923`
- Decision served: keep_building_without_matt (owner-autonomous-release-2026-09-19)
- Reviewed: 2026-09-23 ~12:15 WITA
- Verdict: **ENGINEERING_PASS** (this session PASS=177 FAIL=0; launchd Beta cloudflare_access pid 38820; prod pid 15975 untouched)

## Decision served

keep_building_without_matt (owner-autonomous-release-2026-09-19) after BZG Ops × Needs-You connective ENGINEERING_PASS. Authorised CRM / Lead seats (Owner, and Amanda because `ASG-AMANDA-CM-1` / `ROLE-CONTENT-MGMT` / `SCOPE-CRM-HABITAT-LEAD` is already active) on the existing Lead Spine desk see derived CRM/Lead/Habitat-scoped Needs-You / Morning Commissioning / lead-loop next-actions. No invent staff_ready / PROVEN / READY / Haikal done / Devi done / Habitat commissioned. No BZG compose. No CRM cutover. No Metricool/Klaviyo write. No money. Do not false-resolve CRM/Progress/CORE CRs.

## What landed

- `scripts/core/crm_ops_needs_you_connective.py` — CRM/Lead/Habitat-scoped Needs-You connective strip (`wolf.crm-ops-needs-you-connective.v1`), attached from Lead Spine list and triage. Owner sees the full CRM-scoped commissioning and recorded Habitat lead-loop rows. Amanda sees in-scope rows only when that existing assignment is already active (named rows plus Habitat lead-loop; Owner-only `NEEDS_MATT` rows stay off her seat). A missing assignment is 403. Commission is not inserted. EMPTY honesty when none. Counts are the in-scope length. Desk `next_action` prefers an in-scope row over the generic Lead Spine href. Detail + acknowledge of commissioning rows writes the existing Needs-You operator state (no second mutate surface). Lead-loop acknowledge is `handoff_only` (405) so the existing Lead Spine actions stay the mutate path. Wrong-scope 403. The GGV Ops Needs-You strip is not copied.
- `scripts/serve_beta.py` — additive routes on the existing Lead Spine desk: `GET /api/leads/needs-you`, `GET /api/leads/needs-you/items/{id}`, `POST .../acknowledge`. Refuse haikal-done / devi-done / habitat-done / staff-ready invent / proven / ready / money / CRM cutover / Klaviyo / Metricool / BZG compose.
- `dashboards/lead-spine.html` — Needs-You connective strip on the existing Lead Spine home (no orphan dashboard).
- `scripts/core/wolf_shell.py` — honesty flag `crm_ops_needs_you_connective=true`
- `scripts/tests/test_crm_ops_needs_you_connective.py` — **PASS=177 FAIL=0** · `EXIT: SUCCESS`

## Evidence table

| Check | Claimed | Verified |
|---|---|---|
| Tests | PASS=177 FAIL=0 | PASS=177 FAIL=0 |
| Anon strip | 403 | live `:8788` → **403** `missing_subject` under `development_assertion` |
| Owner strip | CRM-scoped | 200 · count 3 = items 3 · next `LEAD-356124ad-10dd-4aad-b2bd-96977f63f62f` · bound `beta-crm-loop-safe` |
| Owner kinds | lead-loop only | morning_seed 0 · waiting_others 0 · needs_you 0 · lead_loop 3 |
| Owner excludes other businesses | AMG / GGV / NAS / BZG / Progress out | `CMQ-AMG-DAY` absent · `CMQ-AMANDA-GGV` absent · `CMQ-NAS-HAIKAL` absent · `CMQ-DEVI-UMA-MOBILE` absent · `CMQ-PROGRESS-NEEDS-YOU` absent |
| Owner next | preferred over pack | `needs_you_connective` · preferred_over_pack true · desk same |
| Lead loop | recorded triage only | 3 existing Habitat demo leads that already need triage · parked/closed demo leads absent · demo marked true |
| Foreign detail | not CRM | `CMQ-AMG-DAY` **404** `not_found` |
| Amanda | existing CRM seat | **200** · seat `crm_lead` · sees_full_crm false · same 3 lead-loop rows |
| Haikal / Misa / Devi | not this CRM seat | **403** / **403** / **403** |
| Outsider | 403 | 403 `no_person` |
| Acknowledge lead-loop | existing surface | Amanda ack lead-loop **405** `handoff_only` · recorded not set |
| Acknowledge commissioning | existing surface | temp-state prove recorded · commissioned false · actor `PERS-AMANDA` · human_commissioned false |
| haikal-done / habitat-done / money / cutover | refused | 405 `haikal_done_refused` · 405 `habitat_done_refused` · 405 `money_refused` · 405 `crm_cutover_refused` |
| CAP-CRM-01 | BUILT | BUILT |
| CAP-CRM-02/03 | SPECIFIED | SPECIFIED |
| CAP-CRM-04 | BUILT | BUILT |
| AU-CRM-01-HABITAT | NOT STARTED | NOT STARTED |
| Denominator | 77 | 77 |
| CRM CRs | OPEN | `CR-ff42f3a7c49caa79` OPEN · `CR-820682ce791563fa` OPEN · `CR-e5ff219bb1d585f7` OPEN · `CR-c8719063fb940ed4` OPEN |
| Progress/CORE CRs (4) | OPEN | OPEN ×4 |
| ClickUp + Telegram | RETIRED | `integration_health.build_report` honesty `clickup_telegram` RETIRED |
| Ports | 8787/8788 up | True / True |
| Production pid | 15975 | **15975** untouched; prod strip **404** |
| Auth restore | cloudflare_access | launchd Beta restored pid **38820**; spoof `X-Wolf-Subject` on CRM Needs-You → **403** `missing_auth`; anon 403 `missing_auth` |
| WIP quartet | not edited by this pack | hash-object readable (4); those four files were not edited |

## Red team

- CLAIMED≠PROVEN/READY invent: CAP-CRM-01 stays **BUILT**; CAP-CRM-04 stays **BUILT**; CAP-CRM-02/03 stay **SPECIFIED**; staff_ready=false; haikal_human=not_started; devi_retest=parked; AU-CRM-01-HABITAT stays **NOT STARTED**
- Skeleton≠usable loop: desk strip + preferred next_action + in-scope detail + acknowledge on the existing Needs-You operator state; lead-loop acknowledge is `handoff_only` (405)
- EMPTY when the seat has no CRM-scoped commissioning and no recorded Habitat lead-loop attention (count 0, next_action null, desk keeps the Lead Spine href)
- Owner-only `NEEDS_MATT` commissioning is not copied onto Amanda (fixture prove). Live morning seeds are GGV/BZG/AMG/System, so the live CRM morning count is 0
- Live lead-loop rows are the three Habitat demo leads that already need triage. They are marked demo. They are not a live Habitat commission and not a CRM cutover
- Amanda on a catalog with no `ASG-AMANDA-CM-1` is **403**. The check reads that assignment; it does not insert a role or commission
- Haikal and Misa hold `SCOPE-CRM-HABITAT-LEAD` on other roles and still receive **403**. This strip does not treat that shared scope as the Amanda CRM seat
- Target CRM and Progress/CORE CRs remain **OPEN** (no false-resolve)
- Anon fail-closed 403; outsider 403; Haikal/Misa/Devi 403; haikal-done, habitat-done, money, and CRM cutover refused
- No money · no invent Haikal/Devi/Habitat human done · no CF seats · no NAS destroy · no orphan dashboard · no BZG compose · no GGV strip copy · no Metricool/Klaviyo write
- Production untouched
- Live lead-loop acknowledge did not write operator state. Commissioning acknowledge was proved against a temporary operator-state file

## Live prove (temporary `development_assertion`)

1. `launchctl bootout` Beta only (`net.wolfcommand.serve-beta`); start `BETA_AUTH_MODE=development_assertion` on `:8788` (temp listen pid 38692). Auth mode payload was `development_assertion`. Production pid stayed **15975**
2. Anon strip → **403** `missing_subject`; Owner strip 200 count=3 next `LEAD-356124ad-10dd-4aad-b2bd-96977f63f62f`; desk next `needs_you_connective`; AMG detail 404; Amanda 200; Haikal/Misa/Devi 403; outsider 403
3. Amanda acknowledge of the lead-loop row → **405** `handoff_only`; haikal-done 405; habitat-done 405; money 405; crm-cutover 405
4. CAP-CRM-01 BUILT; CAP-CRM-02 SPECIFIED; CAP-CRM-03 SPECIFIED; CAP-CRM-04 BUILT; AU-CRM-01-HABITAT NOT STARTED; CRM CRs OPEN×4; Progress/CORE CRs OPEN×4; prod strip **404**; prod pid **15975**
5. Kill temp server; `launchctl bootstrap` + `kickstart` Beta (no `BETA_AUTH_MODE` ⇒ `cloudflare_access`)
6. Spoof `X-Wolf-Subject` on `/api/leads/needs-you` → **403** `missing_auth`; anon 403 `missing_auth`; Production pid **15975** unchanged; Beta listen pid **38820**

## Honesty

- proven=false · ready=false · staff_ready=false
- haikal_human=not_started · devi_retest=parked · live_habitat_commission=false · AU-CRM-01-HABITAT **NOT STARTED**
- CAP-CRM-01 stays **BUILT** · CAP-CRM-04 stays **BUILT** · CAP-CRM-02/03 stay **SPECIFIED**
- Do **not** false-resolve `CR-ff42f3a7c49caa79`, `CR-820682ce791563fa`, `CR-e5ff219bb1d585f7`, `CR-c8719063fb940ed4`, `e38d9812128a4535b4a6f59f3a3a0319`, `CR-c4ed4e3fa9f15a40`, `CR-6e3fd7b9d7edca0e`, `CR-7a022a9394592c75` — stay **OPEN**
- Empty in-scope projection = EMPTY honesty. Empty morning seed is not a live CRM order. Recorded demo lead-loop attention is not Habitat commissioned and not money

## Exit

```
EXIT: SUCCESS
PASS=177 FAIL=0
```
