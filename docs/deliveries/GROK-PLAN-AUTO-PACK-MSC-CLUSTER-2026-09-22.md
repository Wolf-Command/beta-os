# GROK PLAN — Auto Pack MSC Management Cluster — 2026-09-22

- Bound: `beta-core-safe`
- Class: NEW vertical compose pack (continuous AUTO after INTG PARKED dead_cursor; Peaches vetoed generator re-propose of DONE BZG + PARKED GGV/INTG)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint

## Goal
One phone-first **MSC Management Cluster** desk on Beta `:8788` that composes existing MSC modules into a single Owner-facing operating loop: Asset Register → Posture Prove → Compliance Pack → Cyber Baseline → Records Defensibility — with honesty EMPTY/UNWIRED/WAITING_DATA strips, derived next actions, and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/msc_asset_register.py` + `dashboards/msc-assets.html`
- `scripts/core/msc_posture_prove.py` + `dashboards/msc-posture.html`
- `scripts/core/msc_compliance_pack.py` + `dashboards/msc-compliance.html`
- `scripts/core/msc_cyber_baseline.py` + `dashboards/msc-cyber.html`
- `scripts/core/msc_records_defensibility.py` + `dashboards/msc-records.html`
- Mirror pattern: `scripts/core/crm_mgmt_cluster.py` / `core_mgmt_cluster.py` / `intel_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/msc_mgmt_cluster.py` — compose assets + posture + compliance + cyber + records into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent live MFA/compliance/legal-hold facts. No Cloudflare/Access mutate. No external write.
2. **Dashboard** `dashboards/msc-mgmt-cluster.html` — phone-first at `/msc-mgmt-cluster`
3. **serve_beta handlers** `_msc_mgmt_*` mirroring `_crm_mgmt_*` / `_core_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/msc-mgmt-cluster`, `/msc-mgmt-cluster.html`, `/api/msc/mgmt-cluster*`
5. **Tests** `scripts/tests/test_msc_mgmt_cluster.py` — PASS required; anon 403; money/CF/Access-mutate/secret-exfil/external-write refuse; CAP/CR not inflated
6. **Claim** `bf-auto-pack-msc-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-7ea69933a9d39ba9 · CAP-MSC-01 Asset & Maintenance Register SPECIFIED
- CR-80296d7bc9c35452 · CAP-MSC-02 Automated Posture Prove BUILT
- CR-1f93c785c88e9564 · CAP-MSC-03 Compliance Pack SPECIFIED
- CR-7dae8b389cce6f9a · CAP-MSC-04 Cybersecurity Baseline SPECIFIED
- CR-2d299c339747f432 · CAP-MSC-05 Documents / Records / Legal Defensibility SPECIFIED

## MUST NOT
- Production mutate / Cloudflare Access write / external write / mint secrets
- Money / bank payment / Zayen / HR / trading / proc-supplier reopen
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live MFA or legal-hold facts
- False-resolve any CR / raise CAP maturity without evidence
- Restart parked GGV v1/v2, INTG, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Break existing msc-assets / posture / compliance / cyber / records routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-MSC-01 stays SPECIFIED; CAP-MSC-02 stays BUILT; CAP-MSC-03..05 stay SPECIFIED; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
