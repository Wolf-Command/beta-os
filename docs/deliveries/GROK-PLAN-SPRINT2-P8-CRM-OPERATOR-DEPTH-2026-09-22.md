# GROK PLAN — Sprint2 P8 CRM Lead Operator Depth — 2026-09-22

- Bound: `beta-ggv-loop-safe`
- Class: NEW depth pack after P4 INTEL Operator Depth DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose cluster (`auto-pack-bzg-20260922`)
- Prior: CRM mgmt cluster DONE; GGV lead opdepth DONE (CAP-GGV-04 path). This is a **new run_id** — not silent unpark / not compose redo / not GGV opdepth redo.
- Target OPEN CR (engineering depth, not CAP maturity invent):
  - `CR-ff42f3a7c49caa79` — CAP-CRM-01 Lead CRM is BUILT — governed CRM lead operator detail/action path incomplete for staff (keep OPEN; no CRM cutover / no external write)
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete
- Owner priority: finish business-loop connective (Lead CRM staff path) after BZG/GGV/AMG/INTEL opdepth

## Goal
Deepen Beta Lead CRM so an authorised sales/content seat can (1) open a CRM lead object and see operator detail without inventing leads or cutting over Habitat CRM, and (2) record allowed operator actions (note / next-action-touch / ownership-touch / handover-touch / dismiss-noise) that refresh Lead Spine + GGV desk next-action and Owner/staff attention projections — **never** external CRM/Metricool/Klaviyo write.

## Already present (reuse)
- `scripts/core/lead_spine.py` + `ggv_ops_pack.py` + CRM pack / mgmt cluster surfaces on `:8788`
- GGV operator-depth path DONE — reuse consequence refresh patterns; do **not** rebuild GGV opdepth or CRM compose
- Tests under `scripts/tests/test_lead_spine.py` / CRM / GGV loop tests

## Build (Beta only)
1. CRM lead operator detail/action path: endpoint(s) + desk UX so operator can view CRM/lead detail and record allowed note/next-action/ownership/handover/dismiss actions (no external CRM write, no invent leads).
2. Consequence refresh: recording refreshes Lead Spine / GGV Needs-You / Owner attention projections (EMPTY honesty when no leads).
3. RBAC: grant crm-operator / lead-operator actions on existing GGV/CRM staff roles for Beta prove with fixture seats already wired — **do not** require live Habitat commissioning.
4. Tests + claim; additive `serve_beta` routes only; anon must 403 (not 404).
5. Do **not** invent CAP PROVEN/READY or false-resolve CAP-* CRs. CAP-CRM-01 stays BUILT; CAP-CRM-02/03 SPECIFIED; CAP-CRM-04 BUILT unless genuine Model C evidence says otherwise (default: leave unchanged). Target CR stays OPEN unless resolution_evidence is honest and human-gate free.

## MUST NOT
- Production mutate · money/payment/bank/ESB write · CF Access seat mint · secret exfil
- External CRM / Metricool / Klaviyo / Habitat cutover writes · invent leads
- Invent PROVEN/READY/SYSTEM% · second scoring table
- Reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC
- Rebuild DONE BZG/GGV/AMG/INTEL/CRM compose desks or redo P1–P4 entity operator-depth packs
- WIP quartet touch (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)
- Finance/HR/Trading lanes · `git add .` · commit shared serve head unless surgical and reviewed

## Claim
`bf-sprint2-p8-crm-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
