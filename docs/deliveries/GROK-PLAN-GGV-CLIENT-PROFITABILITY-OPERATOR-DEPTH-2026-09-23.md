# GROK PLAN — GGV Client Profitability Operator Depth — 2026-09-23

- Run id: `BF-ggv-client-profitability-operator-depth-20260923`
- Bound: `beta-ggv-ops-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after AMG Service Improve operator depth DONE ENGINEERING_PASS PASS=214; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; GGV CAP-GGV-03 client profitability operator depth only
- Prior: `ggv_client_profitability.py` skeleton v1 DONE + GGV content-ops / ops-needs-you DONE today; CAP-GGV-03 stays **SPECIFIED**; CR-ccb3287dabe91d4b stays OPEN
- Target OPEN (do not false-resolve): CR-ccb3287dabe91d4b + sibling GGV CRs; Progress/CORE honesty CRs stay OPEN; no invent PROVEN/READY/staff_ready / live P&L / payment amounts / Alchemist books
- Skip: CAP-AMG-01 Yanolja connector. Do not restart parked INTG connector / Devi retest / w12 FIN-PROC. No BZG compose.

## Goal
Deepen the existing GGV Client Profitability surface so authorised Owner/GGV seats can (1) open a profitability stage slot (client→contract→allocation→margin-note→owner→due) or EMPTY when none and see operator detail tied to CAP-GGV-03 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh GGV desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing live P&L / payment / bank / books / Alchemist amounts, **without** money move / Cloudflare Access Include / secret mint / BZG compose / guest blast / public post.

## Already present (reuse)
- `scripts/core/ggv_client_profitability.py` + `dashboards/ggv-client-profitability.html` + GGV mgmt cluster / content-ops / AMG-style operator-depth patterns — deepen, do not orphan / do not new DB
- Mirror AMG service-improve / packages operator-depth honesty/RBAC/action shapes — do **not** copy AMG strips into GGV profitability

## Build (Beta only)
1. New module `scripts/core/ggv_client_profitability_operator_depth.py` + tests; additive `serve_beta` routes under `/api/ggv/client-profitability/operator-depth` (+ rbac / objects / operator-action). Prefer additive panel `#profit-depth` on existing GGV client-profitability / mgmt surface — no new orphan dashboard.
2. Honesty: EMPTY when no profitability evidence; never invent proven / ready / staff_ready / live P&L / payment amounts / bank / books / Alchemist; CAP-GGV-03 stays SPECIFIED; CR stays OPEN.
3. Consequence refresh: recording refreshes GGV desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money / books / guest messaging.
4. RBAC: Owner + authorised GGV seats only for operator-depth actions (reuse existing ggv_ops_pack / profitability seats — do not invent seats); anon 403; outsider / Devi 403 unless an existing GGV seat already grants; refuse proven/ready/staff-ready / payment / bank / books / alchemist-write / access-include / secret mint / money / bzg-compose / production / resolve / invent-live-pnl / guest-blast / public-post.
5. Tests + claim `bf-ggv-client-profitability-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve GGV/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart. No CAP-AMG-01 Yanolja connector.

## MUST NOT
- Production mutate · money move · payment store · bank/books/Alchemist write · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / live P&L / live margin amounts
- False-resolve GGV/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write · guest blast / public post
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE GGV profitability v1 from scratch · restart parked INTG lane · CAP-AMG-01 connector

## Claim
`bf-ggv-client-profitability-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-GGV-03 stays SPECIFIED · no BZG compose · no Access/secret/money/books mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-GGV-CLIENT-PROFITABILITY-OPERATOR-DEPTH-2026-09-23.md`
