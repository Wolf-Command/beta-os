# GROK PLAN — SPRINT TRACK A — BZG OPERATING SYSTEM PACK v1 — 2026-09-21

## Class
NEW CAPABILITY vertical pack (compressed sprint). Beta `:8788` only. Production sacred.

## Goal
Largest safe coherent Uma Blu / BZG F&B **operating loop** so Devi (BZG F&B Ops Lead) can run Today → buy → receive → stock awareness → petty → Daily Close → history/issues on phone Beta — not another skeleton shard.

## Already built (reuse — do not rewrite)
- `scripts/core/uma_ops_console.py` — PR create/transition, petty day/movements, today_cards, history, issues, commissioning_readiness
- `scripts/core/uma_devi_p0.py`, `uma_alchemist_ro.py` (read-only Alchemist/ESB truth)
- Dashboards: `uma-blu-close.html`, Uma ops console surfaces from prior missions
- CAP-BZG-02/04/05/06 skeletons exist (venue P&L, variance, allocation, BOM) — **do not expand into Zayen finance authority**
- Devi scope: OPERATIONAL ≠ UNLIMITED MONETARY (standing lock)

## Pack scope (ONE Cursor pass)
1. **Phone Today loop** — single mobile-first board: open PRs, awaiting receive, petty status, close status, exceptions; human language; no empty cards without wait reason.
2. **PR lifecycle complete** — create → submit → approve(ops) → receive / partial receive → close PR with evidence slots (photo/note ids); refuse payment execution.
3. **Receiving + partial receiving** — quantities, variance flag, evidence required; no invent stock counts as verified truth.
4. **Stock/inventory framework** — read model + variance hooks tied to receive; empty ≠ live perpetual inventory; honesty flags.
5. **Petty cash ops** — movements + count + day close handoff already present; harden UX + permissions for Devi role; no bank/payment.
6. **Daily Close pack** — wire close perform/submit to Today; previous closes list; exceptions surface.
7. **Issues + history** — list + create issue from exception; manager/owner read views (Owner vs Devi scopes).
8. **Permissions** — Role→Assignment→Scope for PERS-DEVI F&B ops; hide buttons she cannot execute; Owner sees more.
9. **Tests** — focused prove pack PASS; anon `:8788` 403 on mutating APIs; `:8787` untouched.
10. **Deployed proof** — Beta routes live; curl matrix in review.

## MUST NOT
- Production mutate / CF Access / Metricool/Klaviyo writes
- Bank/payment/purchase execution / contract / billing
- Invent ESB/Alchemist financial facts as Wolf-verified
- Invent PROVEN/READY; false-resolve CR
- Zayen finance layer / payroll / tax
- Parallel-edit AMG/GGV/INTEL shared chrome carelessly

## Acceptance
- Devi-scoped identity can complete: create PR → receive (incl partial) → record petty → perform Daily Close on Beta phone viewport
- Owner can open manager view of same day without money execution controls
- Tests green; honesty flags true for empty/framework slots
- CAP-BZG-03 / AU-BZG-03-UMA evidence updated toward BUILT usable loop (still not commissioned until Devi human retest)
- CR rows touched stay OPEN until truthful; no fake resolve

## Bound
`beta-bzg-ops-safe` · venue BZG-UMA · phone-first

Armed 2026-09-21 18:35 WITA under Owner compressed sprint.
