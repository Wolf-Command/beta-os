# GROK PLAN — SPRINT TRACK C — AMG HOTEL OPS PACK v1 — 2026-09-21

## Class
NEW CAPABILITY vertical pack (compressed sprint). Beta `:8788` only. Production sacred.

## Goal
Largest safe coherent **Atrium / AMG hotel operating loop** on Beta so hotel ops can run a single Today → arrivals/departures/in-house/OOO → journey tasks → SLA/incidents → service notes path — not another empty skeleton shard.

## Already built (reuse — do not rewrite blindly)
- `scripts/core/amg_daily_ops_state.py` + `dashboards/amg-daily-ops-state.html` (CAP-AMG-04 skeleton)
- `scripts/core/amg_journey_workflow.py` + dashboard (CAP-AMG-02)
- `scripts/core/amg_sla_incident.py`, `amg_service_improve.py`, `amg_pms_orchestration.py`, `amg_packages_products.py`, `amg_revenue_yield.py` + dashboards
- Existing `/api/amg/*` routes in `scripts/serve_beta.py`
- CAP-AMG-01…07 all **SPECIFIED**; CRs OPEN (e.g. CR-bc5785d66c981fd4 CAP-AMG-04)

## Pack scope (ONE Cursor pass)
1. **Phone/desk Today board** — one AMG ops pack surface: occupancy/arrivals/departures/in-house/OOO/notes slots with honesty (empty ≠ live hotel state); human language wait reasons.
2. **Usable daily loop** — create/update notes + mark slot attention; wire journey workflow items for today; surface open SLA/incidents; service-improve handoff entry — still framework-honest when empty.
3. **Permissions** — Owner/hotel-ops read+ops actions only; **no money/bank/payment/folio settlement execution**; hide finance controls.
4. **PMS honesty** — Yanolja/PMS remains SoT when present; empty Wolf slots ≠ live occupancy/ADR/RevPAR; no invent guest/revenue facts.
5. **Tests** — `scripts/tests/test_amg_ops_pack.py` PASS; anon `:8788` 403 on mutating `/api/amg/ops-pack*` (and pack routes); `:8787` untouched.
6. **Deployed proof** — Beta routes live; curl matrix in review; build claim `bf-amg-ops-pack-20260921`.

## MUST NOT
- Production mutate / CF Access / guest blast
- Bank/payment/folio/settlement execution / Zayen finance / tax / payroll
- Invent Yanolja occupancy, ADR, RevPAR, or live PMS writes
- Invent PROVEN/READY; false-resolve any CR (CR-bc5785d66c981fd4 stays OPEN)
- Touch Uma/BZG Track A surfaces or GGV Track B logic except additive `serve_beta.py` routes
- Parallel-edit Intel Track D shared chrome carelessly
- Restart parked w12 FIN finance tiny lanes

## Acceptance
- Operator can open AMG ops pack Today on Beta, see honest empty/framework state, add a note, open a journey item, see SLA list — without money buttons
- CAP-AMG-* ledger states stay SPECIFIED unless real BUILT evidence bar met without inventing PROVEN/READY (prefer leave SPECIFIED)
- Tests green; anon fail-closed; Production untouched

## Bound
`beta-amg-ops-safe` · AMG / Atrium hotel ops

Armed 2026-09-21 ~19:16 WITA after Track A PASS under Owner compressed sprint.
