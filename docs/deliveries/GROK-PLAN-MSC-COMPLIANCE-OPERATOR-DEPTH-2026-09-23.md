# GROK PLAN — MSC Compliance Pack Operator Depth — 2026-09-23

- Run id: `BF-msc-compliance-operator-depth-20260923`
- Bound: `beta-msc-loop-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after CRM Package Intelligence operator depth DONE ENGINEERING_PASS PASS=233; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; thin CAP-MSC-03 compliance pack operator depth only
- Prior: `msc_compliance_pack.py` skeleton v1 + MSC asset operator depth / MSC Needs-You connective DONE; CAP-MSC-03 stays **SPECIFIED**; CR-1f93c785c88e9564 stays OPEN
- Target OPEN (do not false-resolve): `CR-1f93c785c88e9564` (CAP-MSC-03); related MSC CRs stay OPEN; CAP-MSC-01/04/05 stay **SPECIFIED**; CAP-MSC-02 stays **BUILT**; AU-MSC-02-CF-DOORS stays **NOT STARTED**; Progress/CORE CRs stay OPEN; Haikal human = not_started; Devi retest = parked
- Skip: CAP-AMG-01 Yanolja connector. Do not restart parked INTG connector / Devi retest / w12 FIN-PROC. No BZG compose. No CF Access Include mutate.

## Goal
Deepen the existing MSC Compliance Pack surface so authorised Owner/MSC seats can (1) open a licence / statutory / policy / evidence / owner / due slot or EMPTY when the pack is empty and see operator detail tied to CAP-MSC-03 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh MSC desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing licence_status=current / compliance_proved / payment, **without** money move / Cloudflare Access Include / secret mint / BZG compose / guest blast / public post.

## Already present (reuse)
- `scripts/core/msc_compliance_pack.py` + `dashboards/msc-compliance.html` + MSC mgmt cluster / asset operator-depth honesty/RBAC/action shapes — deepen, do not orphan / do not new DB
- Mirror MSC asset / CRM package-intel operator-depth honesty/RBAC/action shapes — do **not** invent Access posture flips

## Build (Beta only)
1. New module `scripts/core/msc_compliance_operator_depth.py` + tests; additive `serve_beta` routes under `/api/msc/compliance/operator-depth` (+ `/desk`, `/rbac`, `/objects/{id}`, operator-action aliases). Prefer additive panel `#compliance-depth` on existing `dashboards/msc-compliance.html` — no new orphan dashboard. Link from MSC mgmt cluster if missing.
2. Honesty: EMPTY when pack empty; never invent proven / ready / staff_ready / licence current / compliance_proved / payment; CAP-MSC-03 stays SPECIFIED; CR stays OPEN. Compliance pack store is not written by operator-depth.
3. Consequence refresh: recording refreshes MSC desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money.
4. RBAC: Owner + authorised MSC seats only for operator-depth actions (reuse existing MSC seats — do not invent seats); anon 403; outsider / Devi 403 unless an existing MSC seat already grants; refuse proven/ready/staff-ready / payment / bank / books / alchemist-write / access-include / secret mint / money / bzg-compose / production / resolve / invent-licence-current / invent-compliance-proved / guest-blast / public-post.
5. Tests + claim `bf-msc-compliance-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve MSC/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart. No CAP-AMG-01 Yanolja connector.

## MUST NOT
- Production mutate · money move · payment store · bank/books/Alchemist write · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / licence_status=current / compliance_proved / payment as truth
- False-resolve MSC/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write · guest blast / public post · Klaviyo/Metricool send
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE MSC compliance v1 from scratch · restart parked INTG lane · CAP-AMG-01 connector

## Claim
`bf-msc-compliance-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-MSC-03 stays SPECIFIED · no BZG compose · no Access/secret/money mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-MSC-COMPLIANCE-OPERATOR-DEPTH-2026-09-23.md`
