# GROK PLAN — Auto Pack STRAT Management Cluster — 2026-09-22

- Bound: `beta-owner-safe`
- Class: NEW vertical compose pack (continuous AUTO after MSC DONE; Peaches vetoed generator re-propose of DONE BZG + DONE MSC/AMG/INTEL/CORE/CRM + PARKED GGV/INTG/PROC)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint

## Goal
One phone-first **STRAT Management Cluster** desk on Beta `:8788` that composes existing Strategy modules into a single Owner-facing operating loop: 12-Week Year Cadence Prove → Owner Radar / Mission Control — with honesty EMPTY/UNWIRED/WAITING_DATA strips, derived next actions, and fail-closed anon.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/strat_12wy_prove.py` + `dashboards/12wy-prove.html`
- `scripts/core/strat_radar_prove.py` + `dashboards/radar-prove.html`
- Related (do not swallow): `scripts/core/ggv_strategy_machine.py` / `dashboards/ggv-strategy-machine.html` (GGV-scoped; keep separate unless read-only strip)
- Mirror pattern: `scripts/core/msc_mgmt_cluster.py` / `crm_mgmt_cluster.py` / `core_mgmt_cluster.py`

## Pack scope (ONE Cursor pass)
1. **Module** `scripts/core/strat_mgmt_cluster.py` — compose 12wy prove + radar prove into one desk model. Honesty EMPTY/UNWIRED/WAITING_DATA. Derived next_action. No invent live mission scores / AU adoption. No Cloudflare/Access mutate. No external write.
2. **Dashboard** `dashboards/strat-mgmt-cluster.html` — phone-first at `/strat-mgmt-cluster`
3. **serve_beta handlers** `_strat_mgmt_*` mirroring `_msc_mgmt_*` / `_crm_mgmt_*` (quiet/refuse/fail/write_refused/page/get). Owner (+ Pulse/doctor read if pattern exists). Staff fail-closed. Anon **403** not 404.
4. **Routes** `/strat-mgmt-cluster`, `/strat-mgmt-cluster.html`, `/api/strat/mgmt-cluster*`
5. **Tests** `scripts/tests/test_strat_mgmt_cluster.py` — PASS required; anon 403; money/CF/Access-mutate/secret-exfil/external-write refuse; CAP/CR not inflated; AUs stay NOT STARTED
6. **Claim** `bf-auto-pack-strat-20260922` in `state/build-claims/2026-09-22.json`

## OPEN CRs (cluster — stay OPEN; no false-resolve)
- CR-6535f7cb02370850 · CAP-STRAT-01 12-Week Year Cadence BUILT
- CR-7a145ad69d8bf3c5 · CAP-STRAT-02 Owner Radar / Mission Control BUILT

## OUT OF ENGINEERING SCOPE (leave alone)
- CR-d6c1c6769b441944 · AU-STRAT-01-GGV NOT STARTED (adoption)
- CR-df9f073e3c32ac6d · AU-STRAT-02-OWNER NOT STARTED (adoption)

## MUST NOT
- Production mutate / Cloudflare Access write / external write / mint secrets
- Money / bank payment / Zayen / HR / trading / proc-supplier reopen
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live AU start
- False-resolve any CR / raise CAP maturity (both already BUILT — do not invent READY)
- Restart parked GGV v1/v2, INTG, P1, P7, Devi retest, w12 FIN (profit-leakage / proc-supplier)
- Re-open DONE BZG/AMG/INTEL/CORE/CRM/MSC packs
- Break existing 12wy-prove / radar-prove routes (additive only)
- Touch WIP quartet; no shared `serve_beta` completion commit unless isolated

## Acceptance
- Tests PASS; claim present; anon page+API 403; Owner path 200 in-process
- CAP-STRAT-01 stays BUILT; CAP-STRAT-02 stays BUILT; CAP CRs stay OPEN; AUs stay NOT STARTED
- Print `EXIT: SUCCESS` or `EXIT: FAILED` then wrapper records CURSOR_DONE

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
