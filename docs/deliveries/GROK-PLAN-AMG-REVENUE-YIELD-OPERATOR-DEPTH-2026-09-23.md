# GROK PLAN — AMG Revenue & Yield Operator Depth — 2026-09-23

- Run id: `BF-amg-revenue-yield-operator-depth-20260923`
- Bound: `beta-amg-day-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after AMG Packages operator depth DONE ENGINEERING_PASS; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; AMG CAP-AMG-05 revenue/yield desk operator depth only
- Prior: `amg_revenue_yield.py` skeleton v1 DONE (PASS=263) + AMG packages operator depth / day-ops / Needs-You connective DONE; CAP-AMG-05 stays **SPECIFIED**; CR-49f6461020b693fc stays OPEN
- Target OPEN (do not false-resolve): CR-49f6461020b693fc + sibling AMG CRs; Progress/CORE honesty CRs stay OPEN; no invent PROVEN/READY/staff_ready / live rates / occupancy / ADR / RevPAR / Yanolja

## Goal
Deepen the existing AMG Revenue & Yield surface so authorised Owner/AMG seats can (1) open a rates/occupancy/ADR/RevPAR/yield/notes slot (or EMPTY when none) and see operator detail tied to CAP-AMG-05 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh AMG desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing live rates/occupancy/ADR/RevPAR/yield numbers, **without** Yanolja write / payment / bank / books / Cloudflare Access Include / secret mint / money / BZG compose.

## Already present (reuse)
- `scripts/core/amg_revenue_yield.py` + `dashboards/amg-revenue-yield.html` + AMG mgmt cluster / packages operator-depth patterns — deepen, do not orphan / do not new DB
- AMG packages / MSC asset / Owner Commissioning operator-depth honesty/RBAC/action shapes — mirror; do **not** copy packages/MSC/Progress strips into revenue yield

## Build (Beta only)
1. New module `scripts/core/amg_revenue_yield_operator_depth.py` + tests; additive `serve_beta` routes under `/api/amg/revenue-yield/operator-depth` (+ rbac / objects / operator-action). Prefer additive panel on existing AMG revenue-yield / mgmt surface — no new orphan dashboard.
2. Honesty: EMPTY when no yield evidence; never invent proven / ready / staff_ready / live hotel / live rates / occupancy / ADR / RevPAR / yield IDR / yanolja-write; CAP-AMG-05 stays SPECIFIED; CR stays OPEN.
3. Consequence refresh: recording refreshes AMG desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money / Yanolja / books.
4. RBAC: Owner + authorised AMG seats only for operator-depth actions; anon 403; outsider / Haikal / Devi / Amanda 403 unless an existing AMG seat already grants (do not invent seats); refuse proven/ready/staff-ready / yanolja-write / payment / bank / books / access-include / secret mint / money / bzg-compose / production / resolve / invent-live-rates.
5. Tests + claim `bf-amg-revenue-yield-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve AMG/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart.

## MUST NOT
- Production mutate · money · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / live hotel / live rates / occupancy / ADR / RevPAR / yield IDR / Yanolja write
- False-resolve AMG/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE AMG revenue-yield v1 / packages operator depth from scratch · restart parked INTG lane

## Claim
`bf-amg-revenue-yield-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-AMG-05 stays SPECIFIED · no BZG compose · no Access/secret/Yanolja/books mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-AMG-REVENUE-YIELD-OPERATOR-DEPTH-2026-09-23.md`
