# GROK PLAN — SPRINT TRACK D — INTEL OPS PACK v1 — 2026-09-21

## Class
NEW CAPABILITY vertical pack (compressed sprint). Beta `:8788` only. Production sacred.

## Goal
Largest safe coherent **Owner Intelligence operating loop** on Beta: one Intel Ops desk that composes already-built primitives (orchestration, authorised knowledge resolution, Decision Memory, approve-to-rule skeleton) into a usable Today → ask → provenance → decision recall → learning-stub handoff path — not another empty skeleton shard.

## Already built (reuse — do not rewrite blindly)
- `scripts/core/intel_orchestration.py` + `GET /api/intel/orchestrate` (CAP-INTEL-01 **BUILT**)
- `scripts/core/knowledge_resolution.py` (CAP-INTEL-02/03 path **PROVEN**)
- `scripts/core/decision_memory.py` (CAP-INTEL-04 **PROVEN**) — INSERT-only; no silent rewrite
- `scripts/core/intel_approve_to_rule.py` + `/api/intel/approve-to-rule*` (CAP-INTEL-05 skeleton; ledger stays **SPECIFIED**; CR-be51980bd1194448 **OPEN**)
- `scripts/core/intel_eval_cost.py` + eval-cost routes (read/append only; no billing invent)
- Progress Empire `#intel-sample` panel exists — extend or add dedicated pack page

## Pack scope (ONE Cursor pass)
1. **Owner Intel Ops desk** — one surface (`dashboards/intel-ops-pack.html` + `/api/intel/ops-pack*`):
   - Today strip: last orchestration outcome + next_human_action (honesty flags visible)
   - Ask box → `orchestrate_institutional_question` (reuse; no LLM-as-evidence)
   - Decision Memory recall list (scoped; empty ≠ no decisions ever existed elsewhere)
   - Approve-to-rule queue summary (NOTED/APPROVED/STUB counts) — stub ≠ live rule
2. **Usable loop** — Owner can ask → see provenance labels → recall related decisions → open/create experiment note handoff into approve-to-rule (append-only). No auto-promote. No rule execution.
3. **Permissions** — Owner (and existing intel.rule / decision.memory permission holders) only; staff without perms 403; **no money/bank/payment**; hide finance.
4. **Honesty** — AU-INTEL-02-WOLF stays NOT STARTED / CR-dca0ad62e1b0032e OPEN; CAP-INTEL-05 stays SPECIFIED; CAP-INTEL-01 stays BUILT (not raised to PROVEN/READY); empty recall ≠ invent history; decision_memory dirty WIP digest must not be "fixed" by staging unrelated `wolf_intelligence.py`.
5. **Tests** — `scripts/tests/test_intel_ops_pack.py` PASS; anon `:8788` 403 on pack + mutating intel routes touched; `:8787` untouched.
6. **Deployed proof** — Beta routes live; curl matrix in review; build claim `bf-intel-ops-pack-20260921`.

## MUST NOT
- Production mutate / CF Access / guest blast / external writes
- Bank/payment/folio / Zayen finance / tax / payroll / trading
- Invent PROVEN/READY; false-resolve any CR (esp. CR-be51980bd1194448, CR-dca0ad62e1b0032e)
- Auto-promote rules / execute stubs / claim Cloudflare JWT as evidence
- `git add` or rewrite WIP quartet: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`
- Break Track A Uma / Track B GGV / Track C AMG routes in shared `serve_beta.py` (additive only)
- Restart parked w12 FIN tiny lanes (profit-leakage / proc-supplier)
- Silent rewrite of Standing Rules or Decision Memory rows (correct_decision path only if already exists — no invent)

## Acceptance
- Owner opens Intel Ops pack on Beta, asks one scoped question, sees honest outcome + provenance, recalls decisions, sees approve-to-rule stub queue — without money buttons or auto-promote
- Ledger honesty: INTEL-01 BUILT · 02–04 PROVEN · 05 SPECIFIED unchanged unless real evidence bar met without inventing PROVEN/READY (prefer leave as-is)
- Tests green; anon fail-closed; Production untouched; WIP quartet unstaged

## Bound
`beta-intel-safe` · Intelligence / Decision Memory productize

Armed 2026-09-21 after Track C AMG ops pack PASS under Owner compressed sprint.
