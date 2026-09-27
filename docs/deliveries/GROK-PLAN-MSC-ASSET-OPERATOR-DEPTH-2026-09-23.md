# GROK PLAN — MSC Asset / Mgmt Operator Depth — 2026-09-23

- Run id: `BF-msc-asset-operator-depth-20260923`
- Bound: `beta-core-safe` (Beta `:8788` only)
- Class: NEW depth pack after INTG connector operator depth PARKED (dead_cursor inspect_retry_ceiling after recover_once); Peaches veto generator BZG compose spam (`auto-pack-bzg-20260923`) again — this is **not** BZG compose; thin MSC asset/mgmt operator depth only
- Prior: MSC mgmt cluster / asset register / compliance / cyber / records / Needs-You connective present; CAP-MSC-01/03/04/05 stay **SPECIFIED**; CAP-MSC-02 stays **BUILT**; AU-MSC-02-CF-DOORS stays **NOT STARTED**
- Target OPEN (do not false-resolve): `CR-7ea69933a9d39ba9` (CAP-MSC-01) + related MSC CRs (`CR-80296d7bc9c35452`, `CR-1f93c785c88e9564`, `CR-7dae8b389cce6f9a`, `CR-2d299c339747f432`); Progress/CORE CRs stay OPEN; Haikal human = not_started; Devi retest = parked

## Goal
Deepen the existing MSC Management Cluster / Asset & Maintenance Register Beta surface so authorised Owner seats can (1) open an asset / maintenance / MSC desk object and see operator detail tied to register honesty (EMPTY when no assets; SPECIFIED ceiling), and (2) record allowed operator actions (note / next-action-touch / handoff-touch / dismiss-noise / review-decision) that refresh MSC desk + Needs-You projections — **without** inventing a live inventory count, **without** MFA/compliance-done / legal-hold invent, **without** CF Access Include mutate / secret mint, **without** inventing staff_ready / PROVEN / READY.

## Already present (reuse)
- `scripts/core/msc_mgmt_cluster.py` + `msc_asset_register.py` + `msc_compliance_pack.py` + `msc_cyber_baseline.py` + `msc_records_defensibility.py` + `msc_ops_needs_you_connective.py` + dashboards — deepen, do not orphan
- CRM Identity / AMG day-ops operator-depth pattern — mirror honesty/RBAC/action shapes; do **not** copy CRM/AMG strips into MSC

## Build (Beta only)
1. Operator detail/action path on existing MSC / Asset Register desk/API: authorised Owner opens asset (or EMPTY placeholder) and records allowed note/next-action/handoff/dismiss/review-decision actions (no invent inventory_complete / proven).
2. Honesty: surface CAP-MSC-01 SPECIFIED + EMPTY when no rows; never invent inventory_complete / compliance_done / mfa_live / legal_hold_active / proven / ready / staff_ready.
3. Consequence refresh: recording refreshes MSC + MSC Needs-You projections without a second mutate surface for Cloudflare Access / secrets / production.
4. RBAC: Owner (+ existing MSC seats if already granted) only; anon 403; outsider 403; refuse Access-include mutate / secret mint/exfil / money / proven / ready / staff-ready / BZG compose / production paths / live MFA invent.
5. Tests + claim `bf-msc-asset-operator-depth-20260923`; additive `serve_beta` / deepen existing MSC surface only; no new orphan dashboard.
6. Honesty: proven=false ready=false staff_ready=false; haikal_human=not_started; devi_retest=parked; CAP-MSC-01/03/04/05 **SPECIFIED**; CAP-MSC-02 **BUILT**; AU-MSC-02-CF-DOORS **NOT STARTED**; do **not** false-resolve MSC/Progress/CORE CRs; no BZG compose; no money; no CF Access Include mutate; no secret mint.
7. `:8787` pid untouched. ClickUp+Telegram RETIRED. No NAS destroy. No Finance/HR/Trading. No parked w12 FIN/PROC restart. No INTG recover#2.

## MUST NOT
- Production mutate · money · CF Access seat mint / Include mutate · secret exfil/mint
- Invent staff_ready / PROVEN / READY / Haikal done / Devi done / inventory_complete / MFA live / compliance-done / legal-hold
- False-resolve MSC/Progress/CORE CRs · **BZG compose** · NAS destroy · external write
- WIP quartet touch · Finance/HR/Trading · new dashboard sprawl · rebuild DONE MSC frameworks / CRM identity depth from scratch · restart parked INTG lane

## Claim
`bf-msc-asset-operator-depth-20260923` · proven=false · ready=false · staff_ready=false · CAP-MSC-01 stays SPECIFIED · no invent inventory/Access · no BZG compose · no Access/secret mutate

## Exit
`EXIT: SUCCESS` or `EXIT: FAILED` with honest findings + `docs/deliveries/GROK-REVIEW-MSC-ASSET-OPERATOR-DEPTH-2026-09-23.md`
