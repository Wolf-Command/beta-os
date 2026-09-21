# GROK PLAN — SPRINT TRACK E — OWNER EMPIRE / COMMAND PACK v1 — 2026-09-21

## Class
NEW CAPABILITY vertical pack (compressed sprint). Beta `:8788` only. Production sacred.

## Goal
Largest safe coherent **Owner Command operating loop** on Beta: one Owner Empire desk that composes already-built Progress (honest SYSTEM%), Radar prove, 12WY prove, and pack handoff attention into a usable Today → truth → next-human-action path — not another empty skeleton shard.

## Already built (reuse — do not rewrite blindly)
- `scripts/core/progress_read_model.py` + `/api/progress*` / `_progress_empire` (Progress dashboard; honesty flags)
- `scripts/core/strat_radar_prove.py` + `/api/strat/radar-prove` + `dashboards/radar-prove.html`
- `scripts/core/strat_12wy_prove.py` + `/api/strat/12wy-prove` + `dashboards/12wy-prove.html`
- `dashboards/progress.html` Empire surface
- Tracks A/B/C ops packs live in working tree (Uma / GGV / AMG) — **read handoff summaries only**; do not rewrite those packs
- CAP-STRAT-01 / CAP-STRAT-02 prove packs exist — do **not** invent PROVEN/READY or fake 12WY %

## Pack scope (ONE Cursor pass)
1. **Owner Empire Command desk** — one surface (`dashboards/owner-empire-pack.html` + `/api/owner/empire-pack*`):
   - Today strip: honest Progress SYSTEM% (ledger-derived or loud EMPTY/UNWIRED — never a frozen/invented %) + next human actions
   - Radar strip: CAP-STRAT-02 prove summary with EMPTY/UNWIRED loud when unwired
   - 12WY strip: CAP-STRAT-01 prove summary — **refuse invented execution %**; honesty flags required
   - Pack handoffs: read-only cards for BZG/GGV/AMG ops-pack attention (from existing APIs if present; else honest EMPTY)
   - Intel strip: optional link/status only — Track D parked; do not build intel-ops-pack here
2. **Usable loop** — Owner opens desk → sees truthful Progress → sees Radar/12WY honesty → picks one next human action (link into existing board) without inventing pace or money.
3. **Permissions** — Owner only; staff without Owner 403; **no money/bank/payment**; hide finance/Zayen/HR/Trading.
4. **Honesty** — No invent SYSTEM% / 12WY%; no false-resolve CR; CAP-STRAT-* stay at evidence-backed states (prefer leave unchanged); EMPTY ≠ invent tactics.
5. **Tests** — `scripts/tests/test_owner_empire_pack.py` PASS; anon `:8788` 403 on pack + mutating owner routes; `:8787` untouched.
6. **Deployed proof** — Beta routes live; curl matrix in review; build claim `bf-owner-empire-pack-20260921`.

## MUST NOT
- Production mutate / CF Access / guest blast / external writes
- Bank/payment/folio / Zayen finance / tax / payroll / trading / HRIS broaden
- Invent PROVEN/READY; invent 12WY% or frozen Progress %; false-resolve any CR
- Restart parked Track D intel-ops or w12 FIN tiny lanes (profit-leakage / proc-supplier)
- `git add` or rewrite WIP quartet: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`
- Break Track A Uma / Track B GGV / Track C AMG routes in shared `serve_beta.py` (additive only)
- Devi human retest / CF seat widen

## Acceptance
- Owner opens Empire Command pack on Beta, sees honest Progress + Radar/12WY honesty + at least one real next-action link into an existing board — without money buttons or invented %
- Ledger honesty: STRAT caps not inflated; Progress not a second scoring table
- Tests green; anon fail-closed; Production untouched; WIP quartet unstaged

## Bound
`beta-owner-safe` · Owner Command / Empire productize

Armed 2026-09-21 20:05 WITA after Track D parked (dead Cursor after one relaunch) under Owner compressed sprint.
