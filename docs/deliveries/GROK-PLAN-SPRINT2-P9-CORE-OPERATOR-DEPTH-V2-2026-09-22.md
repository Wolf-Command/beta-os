# GROK PLAN — Sprint2 P9-v2 CORE Operator Depth — 2026-09-22

- Bound: `beta-core-safe`
- Class: **RELAUNCH** of parked P9 CORE Operator Depth after dead_cursor (nohup banner-only ×2). New run_id. Launch style **shell_tracked_wait_no_reap_block0** only (no nohup recovery).
- Prior DONE: P8 CRM opdepth; P10 SALE opdepth PASS. Peaches veto DONE BZG compose re-propose.
- Parked prior: `BF-sprint2-p9-core-operator-depth-20260922` stays PARKED (do not mutate its BLOCKED record as success).
- Target OPEN CRs (engineering depth, not CAP maturity invent):
  - `CR-c4ed4e3fa9f15a40` — CAP-CORE-11 SOP loop (keep OPEN)
  - `CR-6e3fd7b9d7edca0e` — CAP-CORE-12 Escalation burn-down (keep OPEN; CAP-CORE-12 stays BUILT)
  - `CR-7a022a9394592c75` — CAP-CORE-12 independence / product exit (keep OPEN)
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete
- Owner priority: CORE retry with durable Shell-tracked launch after SALE staff-ready depth

## Goal
Deepen Beta CORE so an authorised Owner/ops seat can (1) open a CORE SOP or escalation object and see operator detail without inventing maturity or commissioning, and (2) record allowed operator actions (note / next-action-touch / acknowledge / escalate-touch / dismiss-noise / handover-touch) that refresh CORE desk next-action + Owner Empire / staff attention / Needs-You projections — **never** money, CF Access, production, or false PROVEN/READY.

## Already present (reuse)
- `scripts/core/core_mgmt_cluster.py` + sop_factory + escalation_burndown + core_harden on `:8788`
- Operator-depth patterns from BZG/GGV/AMG/INTEL/CRM/SALE — reuse; do **not** rebuild those packs or CORE compose
- P9 plan/prompt/landed-none (cursor died before build) — this v2 is the first real build attempt for CORE opdepth

## Build (Beta only)
1. CORE operator detail/action path + desk UX for SOP/escalation detail and allowed note/next/ack/escalate/handover/dismiss.
2. Consequence refresh into CORE next-action / Owner Empire / staff Needs-You (EMPTY honesty).
3. RBAC on Owner/ops fixture seats for Beta prove — no CF seat mint.
4. Tests + claim; additive serve_beta only; anon 403 on depth/rbac/page/action.
5. CAP-CORE-11 stays SPECIFIED; CAP-CORE-12 stays BUILT; target CRs stay OPEN. No invent PROVEN/READY.

## MUST NOT
- Production · money · CF Access · secret exfil
- Invent PROVEN/READY/SYSTEM% · false-resolve CRs
- Reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC (P9 original stays PARKED archive)
- Rebuild DONE compose desks or redo P1–P4/P8/P10 opdepth
- WIP quartet · Finance/HR/Trading · `git add .` · commit shared serve unless surgical
- nohup relaunch path (use Shell-tracked wait_no_reap only)

## Claim
`bf-sprint2-p9-core-operator-depth-v2-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
