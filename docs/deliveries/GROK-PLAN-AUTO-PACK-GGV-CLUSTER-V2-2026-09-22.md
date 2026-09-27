# GROK PLAN — Auto Pack GGV Management Cluster V2 FIX — 2026-09-22

- Bound: `beta-ggv-loop-safe`
- Class: FIX of FAIL review `docs/deliveries/GROK-REVIEW-AUTO-PACK-GGV-CLUSTER-2026-09-22.md`
- Prior run `BF-auto-pack-ggv-20260922` PARKED after one dead FIX (incomplete). This is a **new** lane (v2), not a second recovery of the dead child.

## Already present (do not rebuild)
- `scripts/core/ggv_mgmt_cluster.py`
- `dashboards/ggv-mgmt-cluster.html`
- `serve_beta` import + route call-sites for `/ggv-mgmt-cluster` and `/api/ggv/mgmt-cluster*`

## Missing (ONLY this pack)
1. Handler methods on Beta `serve_beta` mirroring `_bzg_mgmt_*`:
   `_ggv_mgmt_quiet`, `_ggv_mgmt_refuse_code`, `_ggv_mgmt_fail`, `_ggv_mgmt_write_refused`, `_ggv_mgmt_page`, `_ggv_mgmt_get`
   Seats: Amanda / Haikal / Misa + Owner. Anon fail-closed 403.
2. `scripts/tests/test_ggv_mgmt_cluster.py` — PASS required
3. Claim `bf-auto-pack-ggv-v2-20260922` in `state/build-claims/2026-09-22.json`
4. After Beta-safe reload path: anon page+API **403** (not 404). No invent PROVEN/READY. No false-resolve CRs. No money/CRM write/CF/Production. No WIP quartet. Do not touch parked P1/P7/BZG.

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED` then ensure wrapper can record `CURSOR_DONE`.
