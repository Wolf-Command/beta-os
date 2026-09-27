# GROK PLAN — Auto Pack CORE Management Cluster — 2026-09-22

- Bound: `beta-core-safe`
- Class: NEW vertical compose pack (continuous AUTO after BZG/AMG/INTEL DONE; GGV v1+v2 PARKED dead_cursor)
- Decision served: 2026-09-19 owner release keep_building_without_matt + Sprint2 keep_building + Peaches veto skip DONE/PARKED families

## Goal
One phone-first **Core Management Cluster** desk on Beta `:8788` that composes existing Core modules into a single Owner-facing operating loop: SOP factory → escalation burn-down → commissioning honesty — with derived next actions and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/sop_factory.py`
- `scripts/core/escalation_burndown.py`
- `scripts/core/core_harden_pack.py` + `dashboards/core-harden-pack.html` + Track F routes
- Core permissions/authority/work-items/approvals/delegations routes already in `serve_beta`
- Mirror pattern: `scripts/core/amg_mgmt_cluster.py` / `bzg_mgmt_cluster.py` / `intel_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/core_mgmt_cluster.py` — compose sop + escalation + harden (+ optional read-only permissions strip) into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent hotel/money facts.
2. **Dashboard** `dashboards/core-mgmt-cluster.html` — phone-first at `/core-mgmt-cluster`
3. **serve_beta handlers** `_core_mgmt_*` mirroring `_bzg_mgmt_*` / `_amg_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/core-mgmt-cluster`, `/core-mgmt-cluster.html`, `/api/core/mgmt-cluster*`
5. **Tests** `scripts/tests/test_core_mgmt_cluster.py` — PASS required; anon 403; money/CF/commission-flip refuse; CAP/CR not inflated
6. **Claim** `bf-auto-pack-core-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-c4ed4e3fa9f15a40 · CAP-CORE-11 SOP Factory SPECIFIED
- CR-6e3fd7b9d7edca0e · CAP-CORE-12 Escalation Burn-down BUILT
- CR-7a022a9394592c75 · CAP-CORE-12 (duplicate OPEN) BUILT

## MUST NOT
- Production mutate / Cloudflare Access write / external write
- Money / bank / payment / Zayen / HR / trading
- Invent PROVEN/READY / COMMISSIONED / ADOPTED
- False-resolve any CR / raise CAP maturity without evidence
- Restart parked GGV v1/v2, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Break Track F harden-pack or A/B/C/E/AMG/BZG/INTEL routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-CORE-11 stays SPECIFIED; CAP-CORE-12 stays BUILT; CRs stay OPEN
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
