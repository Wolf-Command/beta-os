# GROK PLAN — Auto Pack DR Management Cluster — 2026-09-22

- Bound: `beta-core-safe`
- Class: NEW vertical compose pack (continuous AUTO after STRAT DONE PASS; Peaches vetoed generator re-propose of DONE BZG + DONE MSC/AMG/INTEL/CORE/CRM/STRAT + PARKED GGV/INTG/PROC)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint

## Goal
One phone-first **DR Management Cluster** desk on Beta `:8788` that composes existing Disaster Recovery modules into a single Owner-facing operating loop: Restore Drill Framework → Failure Domains Prove → Crown Jewel Protection — with honesty EMPTY/UNWIRED/WAITING_DATA strips, derived next actions, and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/restore_drill.py` + `dashboards/restore-drill.html`
- `scripts/core/failure_domains.py` + `dashboards/failure-domains.html`
- `scripts/core/dr_crown_jewel.py` + `dashboards/crown-jewels.html`
- Mirror pattern: `scripts/core/strat_mgmt_cluster.py` / `msc_mgmt_cluster.py` / `crm_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/dr_mgmt_cluster.py` — compose restore_drill + failure_domains + dr_crown_jewel into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent live restore proof / Production backup facts. No Cloudflare/Access mutate. No external write. No B2 mutate.
2. **Dashboard** `dashboards/dr-mgmt-cluster.html` — phone-first at `/dr-mgmt-cluster`
3. **serve_beta handlers** `_dr_mgmt_*` mirroring `_strat_mgmt_*` / `_msc_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/dr-mgmt-cluster`, `/dr-mgmt-cluster.html`, `/api/dr/mgmt-cluster*`
5. **Tests** `scripts/tests/test_dr_mgmt_cluster.py` — PASS required; anon 403; money/CF/Access-mutate/secret-exfil/external-write/B2-mutate refuse; CAP/CR not inflated; no invent PROVEN/READY
6. **Claim** `bf-auto-pack-dr-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-667f31959d1bbe82 · CAP-DR-01 Backup / Restore Testing / Disaster Recovery SPECIFIED
- CR-01fc21cfe028333b · CAP-DR-02 Crown Jewel Protection SPECIFIED

## MUST NOT
- Production mutate / Cloudflare Access write / external write / mint secrets / B2 mutate
- Money / bank payment / Zayen / HR / trading / proc-supplier reopen
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live restore drill proof (Owner 18 Sep rejected PROVEN for CAP-DR-01 — stay SPECIFIED)
- False-resolve any CR / raise CAP maturity (both SPECIFIED — do not invent BUILT/PROVEN/READY)
- Restart parked GGV v1/v2, INTG, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Re-open DONE BZG/AMG/INTEL/CORE/CRM/MSC/STRAT packs
- Break existing restore-drill / failure-domains / crown-jewels routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-DR-01 stays SPECIFIED; CAP-DR-02 stays SPECIFIED; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
