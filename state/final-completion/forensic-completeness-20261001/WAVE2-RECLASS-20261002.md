# WAVE2 honesty-desk reclassification — 2 Oct 2026

Owner correction: an honest gap page is **not** rebuilt software. Classifications below keep functions in the missing/partial register until the **job** works.

| Desk | Prior honesty state | Tags | What must still be built |
|---|---|---|---|
| Declared cash (WAVE2-01) | FAIL_CLOSED; till null; authority 0 | HUMAN_DATA_REQUIRED · REQUIRES_HUMAN_COMMISSIONING · INTERNALLY_BUILDABLE (attach/workflow already eng) · EXTERNAL_BLOCKER (none for software) | Physical till count + evidence attach on night close; Owner amount authority limits (>0); Devi/Matt human loop. Do not invent till. |
| Housekeeping (WAVE2-02) | UNAVAILABLE; vacant≠HK | INTERNALLY_BUILDABLE · REQUIRES_INTEGRATION (Yanolja Bookings/HK APIs) · EXTERNAL_BLOCKER (Bookings write denied / HK routes 404) | Deterministic HK workflow: room list → clean/dirty/inspected → assign → verify — even with status source UNAVAILABLE; wire when Bookings/HK API exists. Honesty badge ≠ endpoint. |
| CRM identity (WAVE2-03) | stores unjoined | INTERNALLY_BUILDABLE · REQUIRES_HISTORICAL_MIGRATION · REQUIRES_INTEGRATION | Deterministic cross-reference / identity resolution view per Round 9 (canonical customer identity graph). Separate stores may remain SoT; Wolf still needs join rules + unresolved queue. |
| Menu engineering (WAVE2-04) | mix without classes | INTERNALLY_BUILDABLE · HUMAN_DATA_REQUIRED (contribution/cost) · REQUIRES_INTEGRATION (usage/sales join) | Stars/dogs classification UI + rules once contribution inputs exist; keep ESB qty; do not invent margin. |
| Content learn-back (WAVE2-05) | performance not feeding briefs | INTERNALLY_BUILDABLE | Wire `performance_records` → brief generation inputs (read path). Metricool WRITE stays off until commissioned. Broken chain is software. |
| Month-end / shareholder (WAVE2-06) | chain broken; Xero ABSENT | INTERNALLY_BUILDABLE · REQUIRES_INTEGRATION (Xero optional later) · REQUIRES_HISTORICAL_MIGRATION (July/Aug PRESERVE) | Deterministic close checklist → reconciliation artefacts → shareholder pack from facts already in Wolf books; Xero remains explicit external dep, not a stop on the Wolf close workflow. |
| Sale readiness (WAVE2-07) | empty system checklist SHELL | INTERNALLY_BUILDABLE · REQUIRES_HUMAN_COMMISSIONING | Real sale-readiness system per Round 13 (evidence, EBITDA quality, concentration, founder-dependency burn-down, buyer mode) — not CAP-SALE-01 empty shell. |

## Ranked internally buildable follow-ups (after/during atrium four)
1. Content learn-back feed into briefs  
2. Housekeeping workflow software (status source may stay UNAVAILABLE)  
3. Month-end/shareholder close workflow without requiring Xero  
