# GROK PLAN — Auto Pack INTG Management Cluster V2 — 2026-09-22

- Bound: `beta-connective-safe`
- Class: NEW vertical compose pack v2 (after SALE DONE PASS; Peaches vetoed generator re-propose of DONE BZG + DONE MSC/AMG/INTEL/CORE/CRM/STRAT/DR/SALE + PARKED GGV/PROC; prior INTG v1 PARKED dead_cursor)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint
- Prior: `docs/deliveries/GROK-PLAN-AUTO-PACK-INTG-CLUSTER-2026-09-22.md` + PARKED `BF-auto-pack-intg-20260922` (dead_cursor after one relaunch; zero artifacts). This v2 is a **new run** with SALE-proven short prompt + shell_tracked launch — not a same-tick FIX2.

## Goal
One phone-first **Integration Management Cluster** desk on Beta `:8788` that composes existing INTG modules into a single Owner-facing operating loop: Connector Contract → Connector Cap Tests → Google Workspace prove → Tech/Capability Registry → Secrets & Env Separation — with honesty EMPTY/UNWIRED/WAITING_DATA strips, derived next actions, and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/intg_connector_contract.py` + `dashboards/connector-contract.html`
- `scripts/core/intg_connector_cap_tests.py` + `dashboards/connector-cap-tests.html`
- `scripts/core/gws_integrate_prove.py` + `dashboards/gws-integrate-prove.html`
- `scripts/core/tech_capability_registry.py` + `dashboards/tech-registry.html`
- `scripts/core/intg_secrets_env.py` + `dashboards/intg-secrets.html`
- Mirror pattern: `scripts/core/sale_mgmt_cluster.py` / `dr_mgmt_cluster.py` / `crm_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/intg_mgmt_cluster.py` — compose contract + cap-tests + gws prove + tech registry + secrets into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent connector live facts. No external write. Bank/Yanolja/ESB/Metricool strips may be honesty-only pointers — never mint credentials, never call bank APIs, never money path.
2. **Dashboard** `dashboards/intg-mgmt-cluster.html` — phone-first at `/intg-mgmt-cluster`
3. **serve_beta handlers** `_intg_mgmt_*` mirroring `_sale_mgmt_*` / `_dr_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/intg-mgmt-cluster`, `/intg-mgmt-cluster.html`, `/api/intg/mgmt-cluster*`
5. **Tests** `scripts/tests/test_intg_mgmt_cluster.py` — PASS required; anon 403; money/CF/commission/secret-exfil/external-write/mint-secret refuse; CAP/CR not inflated; no invent PROVEN/READY
6. **Claim** `bf-auto-pack-intg-v2-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-227e2514ac8dcd02 · CAP-INTG-01 Yanolja Connector ABSENT
- CR-00b1a48e6620ec7f · CAP-INTG-02 ESB Connector BUILT
- CR-260e724b776f2b89 · CAP-INTG-03 Google Workspace Connector BUILT
- CR-859e7cad64e7e4ad · CAP-INTG-04 Bank Statement Connector BUILT
- CR-25e89e3efdb0caf9 · CAP-INTG-05 Metricool Connector BUILT
- CR-44ffb6a57469ff25 · CAP-INTG-06 Technology & Capability Registries SPECIFIED
- CR-273f30371bd52c8a · CAP-INTG-07 Secrets & Environment Separation SPECIFIED

## MUST NOT
- Production mutate / Cloudflare Access write / external write / mint secrets / call bank APIs
- Money / bank payment / Zayen / HR / trading / proc-supplier reopen
- Invent PROVEN/READY / COMMISSIONED / ADOPTED
- False-resolve any CR / raise CAP maturity without evidence (CAP-INTG-01 stays ABSENT)
- Restart parked GGV v1/v2, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Re-open DONE BZG/AMG/INTEL/CORE/CRM/MSC/STRAT/DR/SALE packs
- Break existing connector-contract / cap-tests / gws / tech-registry / secrets routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated
- Do not implement live Yanolja connector (ABSENT stays honest EMPTY)

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-INTG-01 stays ABSENT; CAP-INTG-02..05 stay BUILT; CAP-INTG-06/07 stay SPECIFIED; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
