# GROK PLAN — Sprint2 P3 AMG Day-Loop Operator Depth — 2026-09-22

- Bound: `beta-amg-day-safe`
- Class: NEW depth pack after P2 GGV Lead Operator Depth DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose cluster
- Prior: P3 AMG day-loop shell DONE; AMG compose/mgmt cluster DONE. This is a **new run_id** — not silent unpark / not compose redo.
- Target OPEN CR (engineering depth, not CAP maturity invent):
  - `CR-bc5785d66c981fd4` — CAP-AMG-04 Daily Ops State is SPECIFIED — governed day-object operator detail/action path incomplete for staff (keep OPEN until live hotel operating-state evidence)
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete

## Goal
Deepen AMG Beta day loop so a hotel ops seat can (1) open a day-loop object and see operator detail without inventing PMS/occupancy/ADR, and (2) record allowed operator actions (status/note/recovery/handover-touch) that refresh management + Owner consequence strips — no folio/payment/bank/settlement.

## Already present (reuse)
- `scripts/core/amg_ops_pack.py` + P3 day-loop routes on `:8788`
- `scripts/tests/test_amg_day_loop.py` / AMG ops tests
- Compose desk `amg_mgmt_cluster` DONE — do **not** rebuild compose

## Build (Beta only)
1. Day-object operator detail/action path: endpoint(s) + desk UX so operator can view day-object detail and record allowed status/note/recovery/handover-touch actions (no PMS invent, no payment/folio).
2. Consequence refresh: recording refreshes management-exception + Owner-visibility projections (EMPTY honesty when no day objects).
3. RBAC: grant day-operator actions on existing AMG/Atrium staff roles for Beta prove with fixture seats already wired — **do not** require live hotel commissioning.
4. Tests + claim; additive `serve_beta` routes only; anon must 403 (not 404).
5. Do **not** invent CAP PROVEN/READY or false-resolve CAP-* CRs. All CAP-AMG-01..07 stay SPECIFIED unless genuine Model C evidence says otherwise (default: leave unchanged). Target CR stays OPEN unless resolution_evidence is honest and human-gate free.

## MUST NOT
- Production mutate · money/payment/bank/ESB/folio/settlement write · CF Access seat mint · secret exfil
- Invent PMS occupancy/ADR/RevPAR · invent PROVEN/READY/SYSTEM% · second scoring table
- Reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC
- Rebuild DONE BZG/GGV/AMG compose desks
- WIP quartet touch (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)
- Finance/HR/Trading lanes · `git add .` · commit shared serve head unless surgical and reviewed

## Claim
`bf-sprint2-p3-amg-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
