# CAP-INTEL-01 — EVIDENCE BIND (orchestration v1)

**Date:** 2026-09-19
**CAP:** CAP-INTEL-01 Orchestration / Reasoning Surface
**Prior:** SPECIFIED → **Accepted this slice:** **BUILT** (not PROVEN, not READY)
**Class:** NEW CAPABILITY (bounded)
**Lane:** intel-foundation · Beta `:8788` only

## Implementation

- `scripts/core/intel_orchestration.py` — `orchestrate_institutional_question`
- Pipeline: DATA (scope + optional work item) → TOOLS (`knowledge_resolution`, optional `blocker_explain`) → REASONING (fixed outcome enum) → SYNTHESIS (one sentence + provenance labels) → HUMAN (`next_human_action`)
- GET `/api/intel/orchestrate` on Beta serve. Anon and non-Owner → 403. No Production `:8787` route.
- Progress Empire panel `#intel-sample` shows one live sample: summary, status, provenance, next_human_action
- Plan: `docs/deliveries/GROK-PLAN-INTEL-FOUNDATION-2026-09-19.md`

## Deterministic verification

```bash
python3 scripts/tests/test_intel_orchestration.py
python3 scripts/tests/test_knowledge_resolution.py
python3 scripts/tests/test_blocker_explain.py
```

## Completion register

`CR-85ef88d8e1da110c` resolved only. `resolution_evidence` is the implementation commit plus `scripts/tests/test_intel_orchestration.py`.

Commit: stamped in `wolf_completion_items.resolution_evidence` after the implementation commit.

## Why not PROVEN

- No sustained Owner workflow use
- Does not claim Cloudflare JWT authenticated the answer
- SYSTEM numeric credits table unchanged
- Dashboard percentage stays computed from the ledger; this bind does not hard-code a %

## Honesty

- No LLM-as-evidence. No chain-of-thought.
- No new agents. No finance or HR lane. No Alchemist writes.
- `scripts/wolf_intelligence.py` not edited.
