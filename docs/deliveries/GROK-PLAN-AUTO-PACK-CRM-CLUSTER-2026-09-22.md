# GROK PLAN — Auto Pack CRM Management Cluster — 2026-09-22

- Bound: `beta-ggv-loop-safe`
- Class: NEW vertical compose pack (continuous AUTO after CORE DONE; Peaches vetoed generator re-propose of DONE BZG/AMG/INTEL/CORE + PARKED GGV v1/v2)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint

## Goal
One phone-first **CRM Management Cluster** desk on Beta `:8788` that composes existing CRM modules into a single operator/Owner operating loop: Lead Spine → Customer Identity & Memory → Package Intelligence → Email/Klaviyo read wire — with derived next actions and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/lead_spine.py` + `dashboards/lead-spine.html`
- `scripts/core/crm_identity_memory.py` + `dashboards/crm-identity.html`
- `scripts/core/crm_package_intel.py` + `dashboards/crm-package-intel.html`
- `scripts/core/habitat_klaviyo_reader.py` (read-only email marketing wire)
- Mirror pattern: `scripts/core/core_mgmt_cluster.py` / `bzg_mgmt_cluster.py` / `intel_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/crm_mgmt_cluster.py` — compose lead_spine + identity + package_intel + klaviyo reader into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent guest/client/money facts. No CRM write to external (Klaviyo/Metricool send).
2. **Dashboard** `dashboards/crm-mgmt-cluster.html` — phone-first at `/crm-mgmt-cluster`
3. **serve_beta handlers** `_crm_mgmt_*` mirroring `_core_mgmt_*` / `_bzg_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner + Amanda/Haikal/Misa seats if pattern exists. Staff fail-closed. Anon **403** not 404.
4. **Routes** `/crm-mgmt-cluster`, `/crm-mgmt-cluster.html`, `/api/crm/mgmt-cluster*`
5. **Tests** `scripts/tests/test_crm_mgmt_cluster.py` — PASS required; anon 403; money/CF/commission/external-write refuse; CAP/CR not inflated
6. **Claim** `bf-auto-pack-crm-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-ff42f3a7c49caa79 · CAP-CRM-01 Lead CRM BUILT
- CR-820682ce791563fa · CAP-CRM-02 Customer Identity & Memory SPECIFIED
- CR-e5ff219bb1d585f7 · CAP-CRM-03 Package Intelligence SPECIFIED
- CR-c8719063fb940ed4 · CAP-CRM-04 Email Marketing Wire BUILT

## MUST NOT
- Production mutate / Cloudflare Access write / external write / Klaviyo send / Metricool publish
- Money / bank / payment / Zayen / HR / trading
- Invent PROVEN/READY / COMMISSIONED / ADOPTED
- False-resolve any CR / raise CAP maturity without evidence
- Restart parked GGV v1/v2 mgmt FIX, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Break existing lead-spine / identity / package / klaviyo routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated
- Do not include AU-CRM-01-HABITAT NEEDS_ADOPTION as engineering scope

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-CRM-01 stays BUILT; CAP-CRM-02 stays SPECIFIED; CAP-CRM-03 stays SPECIFIED; CAP-CRM-04 stays BUILT; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
