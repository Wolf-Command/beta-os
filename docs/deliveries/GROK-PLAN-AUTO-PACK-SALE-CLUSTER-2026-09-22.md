# GROK PLAN — Auto Pack SALE Management Cluster — 2026-09-22

- Bound: `beta-connective-safe`
- Class: NEW vertical compose pack (continuous AUTO after DR DONE PASS; Peaches vetoed generator re-propose of DONE BZG + DONE MSC/AMG/INTEL/CORE/CRM/STRAT/DR + PARKED GGV/INTG/PROC)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint

## Goal
One phone-first **SALE Management Cluster** desk on Beta `:8788` that composes existing Sale modules into a single Owner-facing operating loop: Continuous Sale Evidence Pack → Buyer Data Room → Buyer Mode / Controlled Export → Buyer Attack & Transition Readiness — with honesty EMPTY/UNWIRED/WAITING_DATA strips, derived next actions, and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/sale_evidence_pack.py` + `dashboards/sale-evidence-pack.html`
- `scripts/core/sale_buyer_dataroom.py` + `dashboards/buyer-dataroom.html`
- `scripts/core/sale_buyer_mode.py` + `dashboards/buyer-mode.html`
- `scripts/core/sale_attack_audit.py` + `dashboards/attack-audit.html`
- Mirror pattern: `scripts/core/dr_mgmt_cluster.py` / `strat_mgmt_cluster.py` / `msc_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/sale_mgmt_cluster.py` — compose evidence_pack + buyer_dataroom + buyer_mode + attack_audit into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent live buyer grant / filled transition pack / live attack run / PROVEN/READY. No Cloudflare/Access mutate. No external write. No money.
2. **Dashboard** `dashboards/sale-mgmt-cluster.html` — phone-first at `/sale-mgmt-cluster`
3. **serve_beta handlers** `_sale_mgmt_*` mirroring `_dr_mgmt_*` / `_strat_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/sale-mgmt-cluster`, `/sale-mgmt-cluster.html`, `/api/sale/mgmt-cluster*`
5. **Tests** `scripts/tests/test_sale_mgmt_cluster.py` — PASS required; anon 403; money/CF/Access-mutate/secret-exfil/external-write/buyer-grant/live-attack/export-mutate refuse; CAP/CR not inflated; no invent PROVEN/READY
6. **Claim** `bf-auto-pack-sale-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-b7ce6d6668848b6e · CAP-SALE-01 Continuous Sale Evidence Pack SPECIFIED
- CR-766f242208e401ad · CAP-SALE-02 Buyer Data Room SPECIFIED
- CR-b428ac5cbc8986b5 · CAP-SALE-03 Buyer Mode / Controlled Export SPECIFIED
- CR-c6e1a48e4a3e8a91 · CAP-SALE-04 Buyer Attack & Transition Readiness SPECIFIED

## MUST NOT
- Production mutate / Cloudflare Access write / external write / mint secrets
- Money / bank payment / Zayen / HR / trading / proc-supplier reopen
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live buyer grant / filled transition pack / live attack execution
- False-resolve any CR / raise CAP maturity (all four SPECIFIED — do not invent BUILT/PROVEN/READY)
- Restart parked GGV v1/v2, INTG, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Re-open DONE BZG/AMG/INTEL/CORE/CRM/MSC/STRAT/DR packs
- Break existing sale-evidence-pack / buyer-dataroom / buyer-mode / attack-audit routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-SALE-01…04 stay SPECIFIED; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
