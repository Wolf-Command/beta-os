# GROK PLAN — Sprint2 P9 CORE Operator Depth — 2026-09-22

- Bound: `beta-core-safe`
- Class: NEW depth pack after P8 CRM Operator Depth DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose cluster (`auto-pack-bzg-20260922`)
- Prior: CORE mgmt cluster DONE (compose desk). This is a **new run_id** — not silent unpark / not compose redo / not CRM or entity opdepth redo.
- Target OPEN CRs (engineering depth, not CAP maturity invent):
  - `CR-c4ed4e3fa9f15a40` — CAP-CORE-11 SOP loop evidence-learn-approve-version-train-use incomplete for staff operator path (keep OPEN)
  - `CR-6e3fd7b9d7edca0e` — CAP-CORE-12 Escalation burn-down + independence tests incomplete for operator action path (keep OPEN; CAP-CORE-12 stays BUILT)
  - `CR-7a022a9394592c75` — CAP-CORE-12 independence / full product exit still OPEN
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete
- Owner priority: Owner disappearance ELIMINATE/AUTOMATE/AUGMENT — staff-usable CORE SOP + escalation operator path after BZG/GGV/AMG/INTEL/CRM opdepth

## Goal
Deepen Beta CORE so an authorised Owner/ops seat can (1) open a CORE SOP or escalation object and see operator detail without inventing maturity or commissioning, and (2) record allowed operator actions (note / next-action-touch / acknowledge / escalate-touch / dismiss-noise / handover-touch) that refresh CORE desk next-action + Owner Empire / staff attention / Needs-You projections — **never** money, CF Access, production, or false PROVEN/READY.

## Already present (reuse)
- `scripts/core/core_mgmt_cluster.py` + sop_factory + escalation_burndown + core_harden on `:8788`
- Entity operator-depth patterns from BZG/GGV/AMG/INTEL/CRM — reuse consequence refresh + RBAC prove patterns; do **not** rebuild those packs or CORE compose
- Tests under `scripts/tests/test_core_mgmt_cluster.py` / sop / escalation suites

## Build (Beta only)
1. CORE operator detail/action path: endpoint(s) + desk UX so operator can view SOP/escalation detail and record allowed note/next-action/acknowledge/escalate/handover/dismiss actions (no invent SOP versions as PROVEN; no auto-approve rules).
2. Consequence refresh: recording refreshes CORE mgmt next-action / Owner Empire attention / staff Needs-You (EMPTY honesty when no items).
3. RBAC: grant `core.operator` (or equivalent) on existing Owner/ops fixture seats for Beta prove — **do not** mint CF Access seats.
4. Tests + claim; additive `serve_beta` routes only; anon must 403 (not 404) on depth/rbac/page/action.
5. Do **not** invent CAP PROVEN/READY or false-resolve CRs. CAP-CORE-11 stays SPECIFIED; CAP-CORE-12 stays BUILT unless genuine Model C evidence says otherwise (default: leave unchanged). Target CRs stay OPEN.

## MUST NOT
- Production mutate · money/payment/bank/ESB write · CF Access seat mint · secret exfil
- Invent PROVEN/READY/SYSTEM% · second scoring table · auto-promote SOP to policy
- Reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC
- Rebuild DONE BZG/GGV/AMG/INTEL/CRM/CORE compose desks or redo P1–P4/P8 entity/CRM operator-depth packs
- WIP quartet touch (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)
- Finance/HR/Trading lanes · `git add .` · commit shared serve head unless surgical and reviewed

## Claim
`bf-sprint2-p9-core-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
