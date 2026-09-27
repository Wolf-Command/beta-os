# GROK PLAN — Sprint2 P1 BZG Operator Depth (PR + Receiving) — 2026-09-22

- Bound: `beta-bzg-loop-safe`
- Class: NEW depth pack after P7 Derivation Prove V2 DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose cluster
- Prior: P1-v1 PARKED; P1-v2 DONE PASS (loop shell). This is a **new run_id** — not silent unpark.
- Target OPEN CRs (engineering, not CAP maturity invent):
  - `CR-080362c384f2bf36` — PR — operator detail/action path incomplete (PERS-DEVI / BZG F&B)
  - `CR-b979d19a6ce4b9ce` — Receiving — real goods-receipt input missing (PERS-DEVI / BZG F&B)
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete

## Goal
Deepen Uma Blu Beta loop so an F&B Ops Lead seat can (1) open a PR and take operator detail/correction actions without money/payment, and (2) enter a real goods-receipt / partial-receive input that drives stock/bill *consequence* read-models — not a fake perpetual inventory.

## Already present (reuse)
- `scripts/core/uma_ops_console.py` + P1-v2 loop routes on `:8788`
- `scripts/tests/test_bzg_loop_closure.py` (PASS=117)
- Compose desk `bzg_mgmt_cluster` DONE — do **not** rebuild compose

## Build (Beta only)
1. PR operator detail/action path: endpoint(s) + phone UX so operator can view PR detail and record allowed corrections/notes/actions (no payment exec, no bank, no ESB write).
2. Goods-receipt input: real receive / partial-receive form+API that writes ops receipt rows and refreshes stock-consequence + bill-consequence projections (empty stock ≠ live inventory honesty).
3. RBAC: grant receive + PR-detail actions on `ROLE-BZG-FB-OPS-LEAD` for Beta prove with `PERS-DEVI` fixture — **do not** require live Devi phone commission; Devi retest stays PARKED human branch.
4. Tests + claim; additive `serve_beta` routes only; anon must 403 (not 404).
5. Optional: if evidence proves paths, CR resolution_evidence may close the two ENGINEERING CRs — do **not** invent CAP PROVEN/READY or false-resolve CAP-* CRs. CAP-BZG-01 stays BUILT; CAP-BZG-03 READY; CAP-BZG-02/04/05/06/07 SPECIFIED unless genuine Model C evidence says otherwise (default: leave unchanged).

## MUST NOT
- Production mutate · money/payment/bank/ESB write · CF Access seat mint · secret exfil
- Invent PROVEN/READY/SYSTEM% · second scoring table · reopen parked P7-v1 / GGV-v1/v2 / INTG-v1 / Devi commission / w12 FIN / PROC
- WIP quartet touch (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)
- `git add .` · commit shared serve head unless surgical and reviewed

## Claim
`bf-sprint2-p1-bzg-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
