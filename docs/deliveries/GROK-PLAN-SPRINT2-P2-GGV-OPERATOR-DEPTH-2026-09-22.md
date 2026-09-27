# GROK PLAN — Sprint2 P2 GGV Lead Operator Depth — 2026-09-22

- Bound: `beta-ggv-loop-safe`
- Class: NEW depth pack after P1 BZG Operator Depth DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose cluster
- Prior: GGV loop shell DONE; GGV mgmt v3 DONE; GGV-v1/v2 PARKED. This is a **new run_id** — not silent unpark.
- Target OPEN CR (engineering depth, not CAP maturity invent):
  - `CR-f089b11530ab4673` — CAP-GGV-04 Lead Triage & Speed-to-Lead is BUILT — governed operator detail/next-action path incomplete for staff
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete

## Goal
Deepen GGV Beta loop so a Content/Sales seat can (1) open a lead and see operator detail without inventing leads, and (2) record allowed next-action / note / ownership-touch actions that refresh pipeline consequence read-models — no external CRM/Metricool/Klaviyo writes.

## Already present (reuse)
- `scripts/core/ggv_ops_pack.py` + `lead_spine.py` + P2 loop routes on `:8788`
- `scripts/tests/test_ggv_loop_closure.py` / mgmt cluster tests
- Compose desk `ggv_mgmt_cluster` DONE — do **not** rebuild compose

## Build (Beta only)
1. Lead operator detail/action path: endpoint(s) + desk UX so operator can view lead detail and record allowed next-action/notes (no CRM write, no invent leads).
2. Next-action consequence: recording refreshes speed-to-lead / pipeline consequence projections (EMPTY honesty when no leads).
3. RBAC: grant lead-operator actions on existing GGV staff roles for Beta prove with fixture seats (Amanda/Haikal/Misa as already wired) — **do not** require live Habitat commissioning.
4. Tests + claim; additive `serve_beta` routes only; anon must 403 (not 404).
5. Do **not** invent CAP PROVEN/READY or false-resolve CAP-* CRs. CAP-GGV-04 stays BUILT; CAP-GGV-01/05 BUILT; CAP-GGV-02 READY; CAP-GGV-03/06 SPECIFIED unless genuine Model C evidence says otherwise (default: leave unchanged). Target CR stays OPEN unless resolution_evidence is honest and human-gate free.

## MUST NOT
- Production mutate · money/payment/bank/ESB write · CF Access seat mint · secret exfil
- External CRM / Metricool / Klaviyo writes · invent leads
- Invent PROVEN/READY/SYSTEM% · second scoring table · reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC
- Rebuild DONE BZG/GGV/AMG compose desks
- WIP quartet touch (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)
- `git add .` · commit shared serve head unless surgical and reviewed

## Claim
`bf-sprint2-p2-ggv-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
