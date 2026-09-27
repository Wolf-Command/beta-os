# GROK PLAN — CAP-INTEL-05 Learning policy v2 — 2026-09-23

**Run id:** `BF-intel-learning-policy-v2-20260923`
**Prior:** `BF-intel-learning-policy-v1-20260920` BLOCKED (inspect_retry_ceiling empty log); approve-to-rule skeleton PASS=161 (CAP-INTEL-05 stays SPECIFIED; CR-be51980bd1194448 OPEN).
**Bound:** Beta `:8788` only. Production `:8787` sacred — no mutate.
**Lane after:** GGV Content x NAS Haikal prep v2 ENGINEERING_PASS (morning Haikal human = Needs Staff; do not invent).

## Goal
Deepen the approve-to-rule learning loop beyond skeleton on Beta: experiment note → Owner/role approve → versioned append-only rule stub → Decision Memory / operator next-action **read** surface. Fail closed. No auto-promote. No live rule execution that mutates operating behaviour outside Beta read models.

## In scope
1. Extend `scripts/core/intel_approve_to_rule.py` (and/or thin `intel_learning_policy.py`) so approved stubs are listable/filterable and project into an Intel operator next-action read model (honest empty states).
2. Wire minimal Beta routes only if missing: list/get stubs; refuse PUT shortcut; refuse promote without Owner/role approve; anon 403.
3. Connective tissue: Decision Memory or Intel connective pack can **see** approved stubs as recommendations (read-only); do not auto-apply.
4. Tests: unit + live Beta prove under temporary `development_assertion`, then restore `cloudflare_access`. Honesty: CAP-INTEL-05 stays SPECIFIED (in-code ceiling BUILT ok); do **not** false-resolve CR-be51980bd1194448; proven=false ready=false staff_ready=false.
5. `:8787` pid untouched. ClickUp+Telegram stay RETIRED.

## Out of scope
- Auto-promote to live operating rules; invent PROVEN/READY; ledger/score/credits write
- False-resolve CR-be51980bd1194448
- FIN/HR/Trading; money; Devi retest; Haikal human fake; Metricool publish; Email send
- Production deploy; NAS destroy; Cloudflare seats

## Success / EXIT
- Suite PASS FAIL=0
- GROK-REVIEW-INTEL-LEARNING-POLICY-V2-2026-09-23.md with red-team table
- Claim honesty: CAP stays SPECIFIED; CR stays OPEN; Production untouched

## Cursor rules
- ASCII prompts only; Shell-tracked short pointer prompt to this plan
- Prefer surgical serve_beta edits; do not sprawl dashboards (Global Nav lock)
- Do not invent maturity. Do not touch WIP-quartet unless required for compile — prefer not.

EXIT: SUCCESS when tests + review evidence written.
