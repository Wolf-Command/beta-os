# MODEL C SYSTEM EVIDENCE BASELINE

**Date:** 2026-09-17
**Status:** COMPLETE (read-only)
**Canon rules/catalog:** UNCHANGED
**28%:** UNCHANGED — not tuned
**SIMULATED SYSTEM %:** NOT APPROVED

## A. STATE BASELINE (factual under canon)

| State | n |
| --- | ---: |
| ABSENT | 1 |
| SPECIFIED | 45 |
| BUILT | 19 |
| PROVEN | 9 |
| READY | 3 |
| **TOTAL** | **77** |

## B. NUMERIC MAPPINGS (simulation only — not canonised)

| Mapping | Credits ABSENT to READY | Claims | Simulated SYSTEM% |
| --- | --- | --- | ---: |
| A Linear | 0 / 0.25 / 0.50 / 0.75 / 1.0 | Even steps; paperwork (SPECIFIED) earns 25% | 39.6% |
| **B Proof-heavy (recommended)** | 0 / 0.10 / 0.30 / 0.60 / 1.0 | Spec cheap; proof + ready expensive | **24.2%** |
| C Ready-gated | 0 / 0.15 / 0.35 / 0.55 / 1.0 | READY carries most weight | 27.7% |

### Red-team of mappings
- A: over-rewards SPECIFIED paperwork; under-differentiates PROVEN vs READY.
- B: resists catalog-only inflation; still gives BUILT real credit; READY valuable but not only score.
- C: can undervalue PROVEN machinery waiting on route prove; gaming via premature READY claims.

**Recommended mapping: B Proof-heavy** — best gaming resistance for current evidence shape (many SPECIFIED, few READY). **Not canonised.**

Alternative-mapping range: **24.2%–39.6%**

## READY red-team (3/3)
- `CAP-CORE-02`: challenged — file checks + factory review path; human commissioning excluded from SYSTEM
- `CAP-GGV-02`: challenged — file checks + factory review path; human commissioning excluded from SYSTEM
- `CAP-BZG-03`: challenged — file checks + factory review path; human commissioning excluded from SYSTEM

## PROVEN red-team (9/9)
- `CAP-CORE-01`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-03`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-04`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-05`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-06`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-07`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-08`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-09`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove
- `CAP-CORE-10`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove

## Low-maturity random sample (>=10)
- `CAP-INTG-07` was SPECIFIED: search hits=9; code_hits=['scripts/core/audit.py', 'scripts/core/evidence.py']
- `CAP-AMG-06` was SPECIFIED: search hits=2; code_hits=[]
- `CAP-DR-02` was SPECIFIED: search hits=3; code_hits=[]
- `CAP-FIN-05` was SPECIFIED: search hits=1; code_hits=[]
- `CAP-HR-03` was SPECIFIED: search hits=1; code_hits=[]
- `CAP-INTEL-04` was SPECIFIED: search hits=37; code_hits=['scripts/core/venue_close.py', 'scripts/core/audit.py', 'scripts/core/approvals.py', 'scripts/core/rbac.py', 'scripts/core/sod.py']
- `CAP-HR-02` was SPECIFIED: search hits=3; code_hits=['scripts/core/identity.py']
- `CAP-CORE-11` was SPECIFIED: search hits=38; code_hits=['scripts/core/esb_close_snapshot.py', 'scripts/core/work_items.py', 'scripts/core/venue_close.py', 'scripts/core/audit.py', 'scripts/core/approvals.py']
- `CAP-AMG-07` was SPECIFIED: search hits=9; code_hits=['scripts/core/audit.py']
- `CAP-PROC-01` was SPECIFIED: search hits=19; code_hits=['scripts/core/progress_read_model.py', 'scripts/core/evidence.py']
- `CAP-DR-01` was SPECIFIED: search hits=21; code_hits=['scripts/core/cf_access.py', 'scripts/core/progress_read_model.py']
- `CAP-FIN-07` was SPECIFIED: search hits=9; code_hits=['scripts/core/esb_close_snapshot.py', 'scripts/core/venue_close.py', 'scripts/core/progress_read_model.py']

## Biggest evidence gaps
1. No approved Locked Requirement Credit packs (all PARTIAL CREDIT NOT AVAILABLE)
2. AMG hotel OS / Yanolja INTEGRATE largely ABSENT/SPECIFIED
3. SOP Factory (CAP-CORE-11) still SPECIFIED only
4. Sale SYSTEM capabilities SPECIFIED without VDR/buyer-mode build
5. Finance/Procurement often BUILT/SPECIFIED without CAP-bound Model C prove packs

## Surprising findings
1. Only **3** capabilities clear SYSTEM READY under conservative rules — Core auth, Habitat Publish Gate, Venue Daily Close
2. Core governance is largely **PROVEN** not READY (honest withhold on deployed CAP prove)
3. CAP-CORE-12 Delegation module is strong but burn-down/independence tests keep it **BUILT**
4. Authorised Knowledge Resolution stays **SPECIFIED** despite strong RULE docs (docs are not READY)
5. Simulated % under recommended mapping (**24.2%**) is **not** tuned to legacy 28%

## Integrity
- OLD TRACKER SHORTCUT USED: NO
- HUMAN ADOPTION COUNTED IN SYSTEM: NO
- CURRENT HEALTH KEPT SEPARATE: YES
- CURRENT 28% COMPARED/TUNED AGAINST: NO
- CATALOG CHANGED: NO
- SCORING RULES CHANGED: NO
- DASHBOARD/APP/DB/PRODUCTION: NONE

## Recommended next action
**LOCK NUMERIC MATURITY CREDITS (mapping B or Matt choice)** — then optional dashboard migration design. Do not replace 28% until mapping locked.
