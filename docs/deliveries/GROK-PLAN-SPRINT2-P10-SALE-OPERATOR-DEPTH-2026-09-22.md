# GROK PLAN — Sprint2 P10 SALE Operator Depth — 2026-09-22

- Bound: `beta-connective-safe`
- Class: NEW depth pack after P8 CRM Operator Depth DONE PASS; P9 CORE opdepth PARKED (dead_cursor after one relaunch / nohup transport); Peaches vetoed DONE BZG compose re-propose
- Prior: SALE mgmt cluster DONE (compose desk). This is a **new run_id** — not compose redo / not CRM redo / not unpark P9
- Target OPEN CRs (engineering depth, not CAP maturity invent):
  - `CR-b7ce6d6668848b6e` — CAP-SALE-01 Evidence pack automation (keep OPEN)
  - `CR-766f242208e401ad` — CAP-SALE-02 VDR product (keep OPEN)
  - `CR-b428ac5cbc8986b5` — CAP-SALE-03 Buyer mode (keep OPEN)
  - `CR-c6e1a48e4a3e8a91` — CAP-SALE-04 Attack audit (keep OPEN)
- Decision served: keep_building_without_matt + compressed sprint 2 + staff-ready ≠ code-complete
- Owner priority: staff-ready Sale readiness connective after business-loop / CRM opdepth; CORE parked transport — retry CORE later with Shell-tracked launch

## Goal
Deepen Beta SALE so an authorised Owner seat can (1) open a sale evidence / buyer-mode / attack-audit object and see operator detail without inventing buyer grants or live attacks, and (2) record allowed operator actions (note / next-action-touch / evidence-touch / dismiss-noise / handover-touch) that refresh SALE desk next-action + Owner Empire / Sale Readiness projections — **never** buyer-grant, live-attack, export-to-buyer, money, CF, or production.

## Already present (reuse)
- `scripts/core/sale_mgmt_cluster.py` + sale_evidence_pack / buyer_dataroom / buyer_mode / attack_audit on `:8788`
- Operator-depth patterns from CRM/BZG/GGV/AMG/INTEL — reuse; do **not** rebuild those packs or SALE compose

## Build (Beta only)
1. SALE operator detail/action path + desk UX for evidence/buyer-mode/attack-audit detail and allowed note/next-action/evidence/handover/dismiss actions.
2. Consequence refresh into SALE next-action / Owner Empire / Sale Readiness (EMPTY honesty).
3. RBAC on Owner fixture seats for Beta prove — no CF seat mint; refuse buyer-grant / live-attack / export.
4. Tests + claim; additive serve_beta only; anon 403 on depth/rbac/page/action.
5. CAP-SALE-01…04 stay SPECIFIED; target CRs stay OPEN. No invent PROVEN/READY.

## MUST NOT
- Production · money · CF Access · secret exfil · buyer-grant · live-attack · export-to-buyer
- Invent PROVEN/READY/SYSTEM% · false-resolve CRs
- Reopen parked P1-v1 / P7-v1 / GGV-v1/v2 / INTG-v1 / Devi / w12 FIN / PROC / P9 CORE
- Rebuild DONE compose desks or redo P1–P4/P8 opdepth
- WIP quartet · Finance/HR/Trading · `git add .` · commit shared serve unless surgical

## Claim
`bf-sprint2-p10-sale-operator-depth-20260922`

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings.
