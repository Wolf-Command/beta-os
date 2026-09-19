# MODEL C — EVIDENCE RECON (READ-ONLY)

**Date:** 2026-09-19
**Class:** FIX / AUDIT. Bound: `beta-model-c-evidence-readonly`.
**Decision served:** owner correction `model_c_recon_after_devi_p0_stable` (2026-09-19) — read-only; no score gaming. Not a new system.
**WHERE:** `docs/deliveries/MODEL-C-EVIDENCE-RECON-2026-09-19.md`

No score gaming. Credits table unchanged. Denominator remains 77. No maturity was raised or invented. No PROVEN or READY was written by this recon.

Ledger write: none. Prefer no write. No Owner-accepted bind was missing from the live ledger.

## Read

Live ledger: `state/model-c-baseline-assessments.json` — **77** rows. Catalog `docs/MODEL-C-CAPABILITY-CATALOG.md` — same 77 CAP-IDs.

Locked credits (`MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17`, not stored as a dashboard constant):

| State | Credit |
| --- | ---: |
| ABSENT | 0.00 |
| SPECIFIED | 0.05 |
| BUILT | 0.25 |
| PROVEN | 0.80 |
| READY | 1.00 |

Formula, computed at this read via `compute_system_from_ledger`: `SYSTEM% = SUM(canonical capability maturity credits) / 77 × 100`.

Score-history tip (`state/model-c-score-history.jsonl`, last line only):

- at `2026-09-19T15:05:00+08:00`
- event `pre-INTEL-01-BUILT`
- sum_credits `19.45` / n `77`
- note: snapshot **before** the CAP-INTEL-01 SPECIFIED → BUILT write

That tip is not the current sum. SPECIFIED 0.05 → BUILT 0.25 is +0.20. 19.45 + 0.20 = **19.65**. The live file matches. This recon appended no history line.

## Audited SYSTEM (this read)

| | |
| --- | --- |
| sum_credits | **19.65** |
| denominator | **77** |
| exact | 19.65 / 77 × 100 = 25.519480…% |
| audited (half-up, 1 d.p.) | **25.5%** |
| status | OK |

This percentage is a read-time projection. It is not written into `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` and not frozen into the dashboard.

## Before / after state counts

No ledger write. After = before.

| State | Before | After |
| --- | ---: | ---: |
| ABSENT | 1 | 1 |
| SPECIFIED | 41 | 41 |
| BUILT | 20 | 20 |
| PROVEN | 12 | 12 |
| READY | 3 | 3 |
| rows | 77 | 77 |
| sum_credits | 19.65 | 19.65 |

## Sample method

Code hit = the literal CAP-ID string inside `scripts/**/*.py`, excluding `scripts/tests/test_model_c_evidence_recon.py` and `__pycache__`. Docs and the ledger are not code hits.

Honesty sample: SPECIFIED rows with zero code hits, excluding the three backlog rows already tabled below (`CAP-FIN-05`, `CAP-HR-04`, `CAP-MSC-05`). Pool sorted. `random.Random(20260919).sample(pool, 5)`.

## Findings

Classifications used: KEEP / UNDER-EVIDENCED / OVER-CLAIMED / EVIDENCE-BINDED.

This sample has **zero OVER-CLAIMED** and **zero UNDER-EVIDENCED**. Maturity was not changed. A full 77-row file-by-file audit was not claimed — only the counts above plus this sample.

### Recent INTEL moves

| CAP-ID | Ledger | Finding | Evidence checked |
| --- | --- | --- | --- |
| CAP-INTEL-01 | BUILT | EVIDENCE-BINDED | Expect BUILT. `scripts/core/intel_orchestration.py`, `scripts/tests/test_intel_orchestration.py`, `scripts/serve_beta.py`, `docs/deliveries/CAP-INTEL-01-EVIDENCE-BIND-2026-09-19.md`, commit `9848be2` present. Not PROVEN. Not READY. |
| CAP-INTEL-02 | PROVEN | EVIDENCE-BINDED | Ledger matches owner reconcile `docs/deliveries/MODEL-C-LEDGER-RECONCILE-INTEL-PROVEN-2026-09-18.md` (Matthew Goss owner audit). `scripts/core/authorised_knowledge.py`, `scripts/tests/test_authorised_knowledge.py`, `scripts/tests/test_authorised_knowledge_live.py`, commit `c4ba95a` present. Earlier bind header still says ACCEPTED BUILT; the later owner reconcile supersedes it. Not missing from the ledger. Not READY. |
| CAP-INTEL-03 | PROVEN | EVIDENCE-BINDED | Same owner reconcile and same AKR files as CAP-INTEL-02. Ledger already PROVEN. Not READY. |
| CAP-INTEL-04 | PROVEN | EVIDENCE-BINDED | `docs/deliveries/MODEL-C-LEDGER-RECONCILE-INTEL-04-PROVEN-2026-09-18.md`. `scripts/core/decision_memory.py`, `scripts/tests/test_decision_memory.py`, commits `d50f74c` and review `4095310` present. Not READY. |

History events `pre-INTEL-02-03-PROVEN` and `pre-INTEL-04-PROVEN` remain earlier lines. This recon did not replay them.

### Remediation backlog seven

Seek CAP-bound evidence only. Leave maturity unchanged unless an Owner-accepted bind is already missing. None was missing.

| CAP-ID | Ledger now | Finding | This read |
| --- | --- | --- | --- |
| CAP-FIN-05 | SPECIFIED | KEEP | Zero `scripts/**/*.py` hits. Same conclusion as `docs/deliveries/OVERNIGHT-P1-SPECIFIED-RETAINED-2026-09-17.md`. No raise. |
| CAP-HR-04 | SPECIFIED | KEEP | Zero code hits. Payroll mentions in canon/docs are not a CAP-bound payroll-inputs module. No raise. |
| CAP-INTEL-02 | PROVEN | EVIDENCE-BINDED | Backlog said “if still low”. It is not still low. Owner-accepted PROVEN is already on the ledger. Not raised here. |
| CAP-INTEL-03 | PROVEN | EVIDENCE-BINDED | Same as CAP-INTEL-02. |
| CAP-INTG-07 | SPECIFIED | KEEP | Owner rejected PROVEN 2026-09-18 (`docs/deliveries/CAP-INTG-07-EVIDENCE-BIND-2026-09-17.md`, `docs/deliveries/EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md`). Repo checks and `scripts/tests/test_cap_intg_07_environment_separation.py` are evidence, not PROVEN. `scripts/core/decision_memory.py` records that rejection; those hits are not a new implementation. |
| CAP-MSC-05 | SPECIFIED | KEEP | Zero code hits. No Beta legal-defensibility module located. No raise. |
| CAP-DR-01 | SPECIFIED | KEEP | Owner rejected PROVEN 2026-09-18. Historical B2 drill retained in `docs/deliveries/CAP-DR-01-EVIDENCE-BIND-2026-09-17.md`. Decision-memory hits record the rejection. No deterministic canonical restore-drill proof added. No raise. |

### Random SPECIFIED, zero code hits

| CAP-ID | Name | Ledger | Finding |
| --- | --- | --- | --- |
| CAP-AMG-07 | Service Improvement Loop | SPECIFIED | KEEP |
| CAP-HR-03 | Training & Competency | SPECIFIED | KEEP |
| CAP-BZG-04 | Inventory & Stock Control | SPECIFIED | KEEP |
| CAP-HR-02 | Hiring & Onboarding | SPECIFIED | KEEP |
| CAP-INTG-06 | Technology & Capability Registries | SPECIFIED | KEEP |

Honesty check: these five stay SPECIFIED. Zero code hits. Not promoted.

## Not done

- `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md` not edited.
- Scoring rules and catalog denominator not edited.
- No dashboard percentage stored.
- Production `:8787` not touched.
- WIP four not edited: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- No Alchemist write. No Devi retest interrupt. Devi human retest stays PARKED.
