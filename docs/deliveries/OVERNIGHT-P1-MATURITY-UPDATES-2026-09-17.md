# OVERNIGHT P1 — MATURITY UPDATES

**Date:** 2026-09-17
**Starting SYSTEM baseline:** 22.3%
**Candidate SYSTEM baseline after P1:** 24.3%
**Dashboard 28%:** UNCHANGED
**Catalog 77 / credits v1.0 / Model E rules:** UNCHANGED

| CAP-ID | From | To | Evidence |
| --- | --- | --- | --- |
| CAP-DR-01 | SPECIFIED | PROVEN | CAP-DR-01-EVIDENCE-BIND-2026-09-17.md + bound B2 restore drill 2026-08-29 |
| CAP-INTG-07 | SPECIFIED | PROVEN | CAP-INTG-07-EVIDENCE-BIND-2026-09-17.md + test_cap_intg_07 PASS |

Retained SPECIFIED: CAP-FIN-05, CAP-HR-04, CAP-INTEL-02, CAP-INTEL-03, CAP-MSC-05

State counts now: {'PROVEN': 11, 'READY': 3, 'SPECIFIED': 43, 'BUILT': 19, 'ABSENT': 1}

---

## Owner audit note — 2026-09-18

Matt **REJECTED** the two overnight PROVEN proposals (**CAP-DR-01**, **CAP-INTG-07**); both remain **SPECIFIED**.  
Separately, Matt **ACCEPTED BUILT** for **CAP-INTEL-02**, **CAP-INTEL-03**, and **CAP-INTEL-04** (not PROVEN).  
Reconciled ledger: `state/model-c-baseline-assessments.json` (sum 17.80 → displayed 23.1%).
