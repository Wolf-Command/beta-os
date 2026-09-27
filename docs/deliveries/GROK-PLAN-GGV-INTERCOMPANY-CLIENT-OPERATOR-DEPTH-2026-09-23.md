# GROK PLAN — GGV Intercompany Client Operator Depth — 2026-09-23

- Run id: `BF-ggv-intercompany-client-operator-depth-20260923`
- Bound: `beta-ggv-ops-safe` (Beta `:8788` only)
- Class: NEW thin depth pack after GGV Client Profitability operator depth DONE ENGINEERING_PASS PASS=207; Peaches veto generator BZG 6-CR compose (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; GGV CAP-GGV-06 intercompany client-mode operator depth only
- Prior: `ggv_intercompany_client.py` skeleton v1 DONE + GGV client-profitability operator depth DONE today; CAP-GGV-06 stays **SPECIFIED**; CR-6a19c9221cab0178 stays OPEN
- Target OPEN (do not false-resolve): CR-6a19c9221cab0178 + sibling GGV CRs; Progress/CORE honesty CRs stay OPEN; no invent PROVEN/READY/staff_ready / live billing / invoice amounts / AR-AP balances / Alchemist books / tax
- Skip: CAP-AMG-01 Yanolja connector. Do not restart parked INTG connector / Devi retest / w12 FIN-PROC. No BZG compose.

## Goal
Deepen the existing GGV Intercompany Client Mode surface so authorised Owner/GGV seats can (1) open an intercompany stage slot (service_record→invoice→allocation→arms_length→ar_ap→notes) or EMPTY when none and see operator detail tied to CAP-GGV-06 honesty, and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh GGV desk + Needs-You projections — **without** inventing PROVEN/READY/staff_ready, **without** inventing live billing / invoice / allocation / AR-AP / tax / bank / books / Alchemist amounts, **without** money move / Cloudflare Access Include / secret mint / BZG compose / guest blast / public post.

## Already present (reuse)
- `scripts/core/ggv_intercompany_client.py` + dashboard / GGV mgmt cluster / client-profitability operator-depth honesty/RBAC/action shapes — deepen, do not orphan / do not new DB
- Mirror GGV client-profitability operator-depth honesty/RBAC/action shapes — do **not** copy profitability P&L strips into intercompany

## Build (Beta only)
1. New module `scripts/core/ggv_intercompany_client_operator_depth.py` + tests; additive `serve_beta` routes under `/api/ggv/intercompany-client/operator-depth` (+ rbac / objects / operator-action). Prefer additive panel `#interco-depth` on existing GGV intercompany / mgmt surface — no new orphan dashboard. If no dedicated HTML yet, add panel on `dashboards/ggv-intercompany-client.html` (create thin page only if missing) linked from GGV mgmt cluster.
2. Honesty: EMPTY when no intercompany evidence; never invent proven / ready / staff_ready / live billing / invoice amounts / AR-AP / tax / bank / books / Alchemist; CAP-GGV-06 stays SPECIFIED; CR stays OPEN.
3. Consequence refresh: recording refreshes GGV desk + Needs-You projection without a second mutate surface for Cloudflare Access / secrets / production / money / books / guest messaging.
4. RBAC: Owner + authorised GGV seats only for operator-depth actions (reuse existing ggv_ops_pack / intercompany seats — do not invent seats); anon 403; outsider / Devi 403 unless an existing GGV seat already grants; refuse proven/ready/staff-ready / payment / bank / books / alchemist-write / access-include / secret mint / money / bzg-compose / production / resolve / invent-live-billing / invent-invoice / guest-blast / public-post / tax-write.
5. Tests + claim `bf-ggv-intercompany-client-operator-depth-20260923`; prove under temporary `BETA_AUTH_MODE=development_assertion` then restore launchd Beta `cloudflare_access`.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; do **not** false-resolve GGV/Progress/CORE/Global-Nav CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint; ClickUp+Telegram RETIRED.
7. `:8787` pid untouched. No NAS destroy. No Finance/HR/Trading. No parked INTG connector recover. No parked w12 FIN/PROC restart. No CAP-AMG-01 Yanolja connector.

## MUST NOT
- Production mutate · money move · payment store · bank/books/Alchemist write · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / live billing / live invoice / AR-AP balances / tax treatment
- False-resolve GGV/Progress/CORE/Global-Nav CRs · **BZG compose** · NAS destroy · external write · guest blast / public post
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE GGV intercompany v1 from scratch · restart parked INTG lane · CAP-AMG-01 connector

## Claim
`bf-ggv-intercompany-client-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-GGV-06 stays SPECIFIED · no BZG compose · no Access/secret/money/books mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-GGV-INTERCOMPANY-CLIENT-OPERATOR-DEPTH-2026-09-23.md`
