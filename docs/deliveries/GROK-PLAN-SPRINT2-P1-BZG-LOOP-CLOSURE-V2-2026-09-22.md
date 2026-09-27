# GROK PLAN — Sprint2 P1 BZG Loop Closure V2 — 2026-09-22

- Bound: `beta-bzg-loop-safe`
- Class: NEW vertical loop-closure pack v2 (after INTG Management Cluster v2 DONE PASS; Peaches vetoed generator re-propose of DONE BZG compose + DONE MSC/AMG/INTEL/CORE/CRM/STRAT/DR/SALE/INTG-v2 + PARKED GGV/PROC/P7/AUTO-INTG-v1; prior P1 PARKED dead_cursor)
- Decision served: keep_building_without_matt + Sprint2 continuous pack gen + Owner compressed sprint (business loops first)
- Prior: `docs/deliveries/GROK-PLAN-SPRINT2-P1-BZG-LOOP-CLOSURE-2026-09-22.md` + PARKED `BF-sprint2-p1-bzg-loop-closure-20260922` (dead_cursor after one relaunch). This v2 is a **new run** with SALE/INTG-proven short prompt + shell_tracked launch — not a silent unpark of the parked run.

## Goal
Close the Uma Blu / BZG F&B operator loop on Beta `:8788` as one continuous phone-first path:

Today → PR → approval boundary → **ordering state** → receiving → **partial receiving** → **stock consequence** → **supplier/bill consequence** → petty/cash record → Daily Close → **exception** → **handover** → **manager visibility** → **Owner exception**.

## Already present (reuse — do not rewrite blindly)
- `scripts/core/uma_ops_console.py` + Uma Blu dashboards / Today / PR / receive / petty / close / history
- `scripts/core/bzg_*` allocation / BOM / ops pack modules as landed
- Mirror honesty patterns from INTG/SALE mgmt clusters for refuse paths

## Pack scope (ONE Cursor pass)
1. Extend Uma ops console + related modules so missing stages are **first-class objects** (ordering state after approval; partial receive → stock/bill consequence views; exception + handover + manager/Owner strips) — not stubs, not orphan dashboards.
2. Additive `serve_beta` routes/handlers only for this pack; anon **403** not 404.
3. Tests `scripts/tests/test_bzg_loop_closure.py` (new or extend) — PASS required; money/ESB-write/payment-exec/CF/Access/Production/secret-exfil refuse; no invent PROVEN/READY.
4. Claim `bf-sprint2-p1-bzg-loop-v2-20260922` in `state/build-claims/2026-09-22.json`.
5. Honesty: empty stock ≠ live inventory; no ESB write; no payment execution; no Zayen; no CF widen; CAP maturity only if evidence supports (prefer leave unchanged over invent).

## MUST NOT
- Production mutate / Cloudflare Access write / ESB write / money / bank payment / Zayen / HR / trading
- Invent PROVEN/READY / COMMISSIONED / ADOPTED / live ESB inventory
- False-resolve adoption CRs; do not reopen DONE AUTO compose desks as false-done
- Restart parked P7 / GGV auto / AUTO-INTG-v1 / Devi human retest / w12 FIN (profit-leakage / proc-supplier) / PROC as money path
- Touch WIP quartet carelessly; commit deferred OK if shared serve_beta WIP
- Silent unpark of `BF-sprint2-p1-bzg-loop-closure-20260922` — this is a new run_id

## Acceptance
- Tests PASS; claim present; anon 403; Owner/ops seat path 200 in-process where intended
- Loop stages visible as objects with EMPTY/UNWIRED/WAITING honesty where data absent
- Print `EXIT: SUCCESS` or `EXIT: FAILED`

## EXIT
Print `EXIT: SUCCESS` or `EXIT: FAILED`.
