# RULE — Dashboard is a Projection

**Status:** LOCKED 2026-09-18  
**Authority:** CURSOR-MISSION-DASHBOARD-TRUTH-2026-09-18  
**Surface:** Beta Progress / Owner cockpit (`/progress`)  
**Canonical state:** `state/model-c-baseline-assessments.json`  
**Credits:** `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` (do not edit from this rule)

## RULE

A dashboard is a **projection** of canonical state.

- If the canonical ledger changes, the **next read** must show the new value.
- If the projection cannot be proven against the ledger (or against the rendered page), the dashboard shows **SCORING PROJECTION STALE** and **does not** show a percentage.
- Never copy a percentage by hand into HTML, the read model, or a status note and treat it as live truth.

## SYSTEM dial

```
SYSTEM% = SUM(maturity credits) / 77 × 100
```

Computed on every read. Round half-up to one decimal. Do not store the display percentage.

## Integrity

Same process, three surfaces:

1. Score from the ledger file  
2. Score from the read model / API  
3. Score implied by the rendered Progress page (API-driven; no hard-coded live %)

Disagree → stale. No manual reconciliation by editing the number.

## Out of scope

- Editing maturity rows to make the dial look better  
- Inventing scores for other Model E dials  
- Production `:8787`  
- Hard-coding former build-tracker figures as current progress
