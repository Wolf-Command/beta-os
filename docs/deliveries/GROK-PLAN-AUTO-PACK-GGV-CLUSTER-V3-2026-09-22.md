# GROK PLAN — Auto Pack GGV Management Cluster V3 FIX — 2026-09-22

- Bound: `beta-ggv-loop-safe`
- Class: NEW FIX pack v3 after P1 BZG Loop Closure V2 DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose + DONE MSC/AMG/INTEL/CORE/CRM/STRAT/DR/SALE/INTG-v2 + PARKED PROC/P7/AUTO-INTG-v1/P1-v1
- Prior: `BF-auto-pack-ggv-20260922` + `BF-auto-pack-ggv-v2-20260922` PARKED (dead_cursor; handlers+tests still missing). This v3 is a **new run_id** — not a silent unpark of parked GGV v1/v2.
- Decision served: keep_building_without_matt + Sprint2 continuous pack + Owner compressed sprint

## Goal
Wire the already-present GGV management cluster compose desk so it is served on Beta `:8788` with tests + claim — not another orphan module.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/ggv_mgmt_cluster.py` + `dashboards/ggv-mgmt-cluster.html`
- Partial `serve_beta` call-sites (`hasattr` guards) for `/ggv-mgmt-cluster` and `/api/ggv/mgmt-cluster*` that currently return **404 not_wired**
- Mirror `_bzg_mgmt_*` / `_intg_mgmt_*` / `_sale_mgmt_*` handler pattern

## Pack scope (ONE Cursor pass)
1. Add `def _ggv_mgmt_quiet/_refuse_code/_fail/_write_refused/_page/_get` on `serve_beta` mirroring `_bzg_mgmt_*` bound to `ggv_mgmt_cluster`; seats Amanda / Haikal / Misa + Owner; anon fail-closed **403** not 404.
2. Tests `scripts/tests/test_ggv_mgmt_cluster.py` — PASS required; money/CRM-write/CF/Access/Production/secret-exfil/PROVEN invent refuse; no false-resolve CRs.
3. Claim `bf-auto-pack-ggv-v3-20260922` in `state/build-claims/2026-09-22.json`.
4. Honesty: CAP-GGV-01/04/05 stay BUILT; CAP-GGV-02 READY; CAP-GGV-03/06 SPECIFIED unchanged; five GGV CRs stay OPEN. Empty desk strips ≠ invent clients/leads/Metricool write.

## MUST NOT
- Production mutate / Cloudflare Access write / money / CRM cutover / external write / Zayen / HR / trading
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live connector health
- False-resolve GGV CRs; do not reopen DONE AUTO compose desks (BZG/AMG/INTEL/CORE/CRM/MSC/STRAT/DR/SALE/INTG-v2) as false-done
- Restart parked P7 / AUTO-GGV-v1/v2 (this is new v3) / AUTO-INTG-v1 / Devi / w12 FIN / PROC / P1-v1
- Touch WIP quartet carelessly; commit deferred OK if shared serve_beta WIP
- Silent unpark of parked GGV runs

## Acceptance
- Tests PASS; claim present; live anon page+API **403** (not 404/not_wired)
- Print `EXIT: SUCCESS` or `EXIT: FAILED`

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
