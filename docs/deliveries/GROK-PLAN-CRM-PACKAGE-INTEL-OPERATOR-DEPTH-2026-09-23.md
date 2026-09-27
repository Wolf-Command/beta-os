# GROK PLAN — CRM Package Intelligence Operator Depth — 2026-09-23

- Run id: `BF-crm-package-intel-operator-depth-20260923`
- Bound: `beta-crm-loop-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after GGV Intercompany Client operator depth DONE ENGINEERING_PASS PASS=243; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; thin CAP-CRM-03 package intelligence operator depth only
- Prior: `crm_package_intel.py` skeleton v1 DONE + CRM identity operator depth / CRM Needs-You connective DONE today; CAP-CRM-03 stays **SPECIFIED**; CR-e5ff219bb1d585f7 stays OPEN
- Target OPEN (do not false-resolve): `CR-e5ff219bb1d585f7` (CAP-CRM-03); related CRM CRs stay OPEN; CAP-CRM-02 stays **SPECIFIED**; CAP-CRM-01/04 stay **BUILT**; AU-CRM-01-HABITAT stays **NOT STARTED**; Progress/CORE CRs stay OPEN; Haikal human = not_started; Devi retest = parked
- Skip: CAP-AMG-01 Yanolja connector. Do not restart parked INTG connector / Devi retest / w12 FIN-PROC. No BZG compose.

## Goal
Deepen the existing CRM Package Intelligence surface so authorised Owner/CRM seats can (1) open a package / channel / margin-note / evidence / owner / due slot or EMPTY when the register is empty and see operator detail tied to CAP-CRM-03 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh CRM desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing live census / live booking write / price/margin as market truth / Habitat cutover / Klaviyo write, **without** money move / Cloudflare Access Include / secret mint / BZG compose / guest blast / public post.

## Already present (reuse)
- `scripts/core/crm_package_intel.py` + `dashboards/crm-package-intel.html` + CRM mgmt cluster / identity operator-depth honesty/RBAC/action shapes — deepen, do not orphan / do not new DB
- Mirror GGV/CRM identity operator-depth honesty/RBAC/action shapes — do **not** copy AMG packages-as-products compose into CRM package intel

## Build (Beta only)
1. New module `scripts/core/crm_package_intel_operator_depth.py` + tests; additive `serve_beta` routes under `/api/crm/package-intel/operator-depth` (+ `/desk`, `/rbac`, `/objects/{id}`, operator-action aliases). Prefer additive panel `#package-intel-depth` on existing `dashboards/crm-package-intel.html` — no new orphan dashboard. Link from CRM mgmt cluster if missing.
2. Honesty: EMPTY when register empty; never invent proven / ready / staff_ready / live census / live booking / invented price-as-market / Habitat done; CAP-CRM-03 stays SPECIFIED; CR stays OPEN. Package framework/register store is not written by operator-depth.
3. Consequence refresh: recording refreshes CRM desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money / Habitat / Klaviyo.
4. RBAC: Owner + authorised CRM seats only for operator-depth actions (reuse existing CRM seats — do not invent seats); anon 403; outsider / Devi 403 unless an existing CRM seat already grants; refuse proven/ready/staff-ready / payment / bank / books / alchemist-write / access-include / secret mint / money / bzg-compose / production / resolve / invent-live-census / invent-booking / guest-blast / public-post / habitat-cutover / klaviyo-write.
5. Tests + claim `bf-crm-package-intel-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve CRM/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart. No CAP-AMG-01 Yanolja connector.

## MUST NOT
- Production mutate · money move · payment store · bank/books/Alchemist write · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / live census / live booking write / Habitat commissioned / price-as-market-truth
- False-resolve CRM/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write · guest blast / public post · Klaviyo/Metricool send
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE CRM package-intel v1 from scratch · restart parked INTG lane · CAP-AMG-01 connector

## Claim
`bf-crm-package-intel-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-CRM-03 stays SPECIFIED · no BZG compose · no Access/secret/money/Habitat mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-CRM-PACKAGE-INTEL-OPERATOR-DEPTH-2026-09-23.md`
