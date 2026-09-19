# GROK PLAN — Model C evidence recon (read-only) — 2026-09-19

## Class
FIX / AUDIT (read-only). Bound: `beta-model-c-evidence-readonly`.
Owner: `model_c_recon_after_devi_p0_stable` = read-only; **no score gaming**.

## Goal
Reconcile the live Model C evidence ledger against CAP-bound files/tests/commits on Beta. Prove honesty. Do **not** invent maturity.

## Must NOT
- Change `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` credits table
- Change scoring rules / catalog denominator (77)
- Hard-code or freeze a dashboard %
- Auto-promote ABSENT/SPECIFIED/BUILT/PROVEN/READY without CAP-bound evidence + Owner-accepted pattern
- Touch Production `:8787`
- Touch WIP four / Alchemist writes / money / HR
- Interrupt Devi human retest (PARKED)

## Build (Beta only)

1. **Read** live ledger `state/model-c-baseline-assessments.json` (77 rows) + tip of `state/model-c-score-history.jsonl`.
2. **Compute** sum_credits / 77 at read time using locked credits (0 / 0.05 / 0.25 / 0.80 / 1.00). Report audited SYSTEM % — never store a dashboard constant.
3. **Sample recon** for at least:
   - Recently moved: CAP-INTEL-01 (expect BUILT), CAP-INTEL-02/03/04 (expect per ledger)
   - Remediation backlog seven (FIN-05, HR-04, INTEL-02/03 if still low, INTG-07, MSC-05, DR-01) — seek CAP-bound evidence only; leave maturity unchanged unless already evidenced and Owner-accepted elsewhere
   - Random ≥5 SPECIFIED with zero code hits (honesty check)
4. **Output** delivery note `docs/deliveries/MODEL-C-EVIDENCE-RECON-2026-09-19.md` with:
   - Before/after state counts (after = same if no honest write)
   - Per-cap findings: KEEP / UNDER-EVIDENCED / OVER-CLAIMED / EVIDENCE-BINDED
   - Explicit “no score gaming” attestation
5. **Ledger write allowed ONLY IF** an existing Owner-accepted evidence bind is missing from the live ledger (honesty fix). Prefer **no write**. If write: append history jsonl event first; never invent PROVEN/READY.
6. **Tests**: small prove script or extend existing — ledger row count=77; credits map locked; recon note exists; WIP four digests unchanged.
7. Build-claim row `bf-model-c-evidence-recon-20260919`.

## Prove bar
PASS when recon note lands, tests green, SYSTEM % matches ledger sum, no unauthorized maturity raise, Production untouched.

## After DONE
close_slice → next PENDING (or IDLE if queue empty). Quiet unless BLOCKED.
