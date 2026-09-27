# GROK PLAN — AMG Guest Journey Operator Depth — 2026-09-23

- Run id: `BF-amg-journey-operator-depth-20260923`
- Bound: `beta-amg-day-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after AMG Revenue & Yield operator depth DONE ENGINEERING_PASS; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; AMG CAP-AMG-02 guest journey desk operator depth only
- Prior: `amg_journey_workflow.py` skeleton v1 DONE (PASS=236) + AMG revenue/yield / packages / day-ops operator depth DONE; CAP-AMG-02 stays **SPECIFIED**; CR-ce127471ba41692b stays OPEN
- Target OPEN (do not false-resolve): CR-ce127471ba41692b + sibling AMG CRs; Progress/CORE honesty CRs stay OPEN; no invent PROVEN/READY/staff_ready / live journey / booking counts / Yanolja

## Goal
Deepen the existing AMG Guest Journey surface so authorised Owner/AMG seats can (1) open a journey stage slot (enquiry→booking→pre-arrival→arrival→stay→checkout→return) or EMPTY when none and see operator detail tied to CAP-AMG-02 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh AMG desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing live journey/booking/occupancy numbers, **without** Yanolja write / payment / bank / books / Cloudflare Access Include / secret mint / money / BZG compose.

## Already present (reuse)
- `scripts/core/amg_journey_workflow.py` + `dashboards/amg-journey-workflow.html` + AMG mgmt cluster / revenue-yield / packages operator-depth patterns — deepen, do not orphan / do not new DB
- Mirror revenue-yield / packages operator-depth honesty/RBAC/action shapes — do **not** copy packages/yield strips into journey

## Build (Beta only)
1. New module `scripts/core/amg_journey_operator_depth.py` + tests; additive `serve_beta` routes under `/api/amg/journey-workflow/operator-depth` (+ rbac / objects / operator-action). Prefer additive panel on existing AMG journey / mgmt surface — no new orphan dashboard.
2. Honesty: EMPTY when no journey evidence; never invent proven / ready / staff_ready / live hotel / live journey / booking counts / Yanolja write; CAP-AMG-02 stays SPECIFIED; CR stays OPEN.
3. Consequence refresh: recording refreshes AMG desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money / Yanolja / books.
4. RBAC: Owner + authorised AMG seats only for operator-depth actions; anon 403; outsider / Haikal / Devi / Amanda 403 unless an existing AMG seat already grants (do not invent seats); refuse proven/ready/staff-ready / yanolja-write / payment / bank / books / access-include / secret mint / money / bzg-compose / production / resolve / invent-live-journey.
5. Tests + claim `bf-amg-journey-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve AMG/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart.

## MUST NOT
- Production mutate · money · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / live hotel / live journey / booking counts / Yanolja write
- False-resolve AMG/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE AMG journey v1 / revenue-yield operator depth from scratch · restart parked INTG lane

## Claim
`bf-amg-journey-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-AMG-02 stays SPECIFIED · no BZG compose · no Access/secret/Yanolja/books mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-AMG-JOURNEY-OPERATOR-DEPTH-2026-09-23.md`
