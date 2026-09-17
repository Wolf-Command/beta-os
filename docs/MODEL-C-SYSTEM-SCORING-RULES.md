# MODEL C — SYSTEM SCORING RULES (CANONICAL)

**Status:** CANONICAL — scoring RULES locked (not a calculated score)  
**Approved:** Matt APPROVED — LOCK MODEL C SYSTEM SCORING RULES (2026-09-17, chat)  
**Denominator:** `docs/MODEL-C-CAPABILITY-CATALOG.md` (77 capabilities · 14 domains) — unchanged by this lock  
**Design history:** `docs/deliveries/MODEL-C-SYSTEM-SCORING-DESIGN-2026-09-17.md`  
**Approval event:** `docs/deliveries/MODEL-C-SYSTEM-SCORING-RULES-LOCK-EVENT-2026-09-17.md`  
**Companion catalog RULE:** `docs/RULE-Model-C-System-Capability-Denominator-2026-09-17.md`  
**WHERE:** `docs/MODEL-C-SYSTEM-SCORING-RULES.md`

This document locks **how SYSTEM maturity is earned**. It does **not** publish a live SYSTEM%.  
Displayed Progress **28%** remains **LEGACY BUILD-TRACKER ESTIMATE — PENDING MODEL C SCORING MIGRATION**.

CLAIMED ≠ VERIFIED · CLAIMED ≠ APPROVED · DESIGNED ≠ BUILT · BUILT ≠ PROVEN · READY ≠ HUMAN COMMISSIONED

---

## 1. SYSTEM definition

**SYSTEM** = How much of the approved Wolf capability architecture has been correctly implemented and technically proven.

SYSTEM measures **machinery**.

SYSTEM does **not** measure:

| Out of SYSTEM | Model E dimension |
| --- | --- |
| Real-world adoption / human commissioning | OPERATING ADOPTION |
| Outcome measurement / learning from results | DATA / MEASUREMENT |
| Accidental Matt dependency | FOUNDER INDEPENDENCE |
| Trusted cash / books / profitability controls | FINANCIAL CONTROL |
| Buyer understand / inherit / operate | SALE READINESS |

---

## 2. Canonical maturity states (human terminology)

Use these **state names** in UI, audit evidence, and architecture docs.  
Internal numeric indexes may exist for deterministic calculation; documentation must not depend on ambiguous labels such as S1/S2/S3/S4.

| State | Meaning |
| --- | --- |
| **ABSENT** | Capability is canonical mission scope but lacks an approved requirements/specification pack sufficient to build. |
| **SPECIFIED** | Approved requirements/specification exists and is bound to the canonical CAP-ID. |
| **BUILT** | Required implementation exists as locatable code/schema/config/integration/configuration per approved requirements. **DESIGNED ≠ BUILT.** |
| **PROVEN** | Implementation has deterministic verification appropriate to the capability, including required tests and material red-team/review evidence. **BUILT ≠ PROVEN.** |
| **READY** | Capability is technically deployable/available in its intended Beta/runtime environment with required technical dependencies proven. Where a user-facing route is part of the capability: **REPOSITORY TEST ≠ DEPLOYED ROUTE TEST.** **READY ≠ HUMAN COMMISSIONED ≠ LIVE OPERATING ADOPTION.** |

**Active maturity credits (LOCKED `MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17`):** ABSENT 0.00 · SPECIFIED 0.05 · BUILT 0.25 · PROVEN 0.80 · READY 1.00 — applied after Locked Requirement Credit (§4). Canonical table: `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`.

> **SUPERSEDED / history only (do not use for scoring):** An earlier draft table used SPECIFIED 0.25 · BUILT 0.50 · PROVEN 0.75. Those figures are **not** active credits. Readers must not treat 0.50 or 0.75 as current.

---

## 3. Evidence

Maturity must be **evidence-derived**.

Peaches/Grok prose alone is **not** evidence when machine/runtime evidence should exist.

| State | Minimum evidence concept |
| --- | --- |
| SPECIFIED | Approved canon/spec/requirements bound to CAP-ID |
| BUILT | Locatable implementation evidence |
| PROVEN | Deterministic verification + required review/red-team evidence |
| READY | Deployed/runtime/technical dependency proof appropriate to capability |

Evidence must retain **provenance** and **timestamp/version** where applicable.

---

## 4. Partial capability — Locked Requirement Credit

When partial implementation needs representation:

1. Requirements/credits are **subordinate to CAP-ID**.
2. Each approved requirement has a locked weight; weights **sum to 1.0**.
3. Weights are **approved, versioned**, retain historical versions, and **do not change silently**.
4. Split/reword of a requirement **does not** change maturity unless the approved requirement-credit model is **explicitly superseded** under governance.
5. No requirement may silently become a new capability.
6. Capability SYSTEM fraction = Σ (weight × requirement credit); state thresholds use that fraction plus READY deploy/deps gates.

---

## 5. Weighting

- All **77** canonical SYSTEM capabilities receive **equal** capability weight.
- **No** domain weights.
- **No** estimated code constants.
- **No** “important-looking” extra weight without a future explicit constitutional change.

`SYSTEM%` (when calculated later) = mean of 77 capability fractions × 100.

### Scope change

Equal weighting does **not** mean the denominator never changes.

Denominator changes **only** when Matt approves a genuine new/removed canonical mission capability through architecture governance.

Adding a requirement, task, UI, endpoint, control, venue, property, brand, or diligence check does **not** automatically change 77.

Genuine approved mission-scope expansion may. Preserve catalog version history when that occurs.

---

## 6. External systems

Preserve ownership tags: **OWN · INTEGRATE · OBSERVE · DERIVE**.

SYSTEM maturity measures **Wolf’s capability around the boundary**.

Vendor existence or uptime does **not** itself earn Wolf maturity.  
Vendor outage affects **CURRENT HEALTH**, not historical build maturity.

---

## 7. Shared capability / adoption

SYSTEM capability maturity exists **once**.

Entity / venue / property / brand adoption is tracked separately (OPERATING ADOPTION).

Example: Venue Daily Close may become SYSTEM READY once. Uma Blu commissioning affects OPERATING ADOPTION. Adding Rainforest / Merah / Rooftop does **not** lower SYSTEM maturity.

---

## 8. Current health (orthogonal)

CURRENT HEALTH is **separate** from SYSTEM MATURITY.

Minimum health values: **HEALTHY · DEGRADED · FAILING · UNKNOWN**

A READY capability that breaks remains historically READY but becomes DEGRADED or FAILING.

Dashboard must eventually make this distinction obvious. **Do not implement health scoring in this lock.**

---

## 9. Model E definitions (locked)

| Dimension | Definition |
| --- | --- |
| **SYSTEM** | Is the required machinery correctly built and technically proven? |
| **OPERATING ADOPTION** | Are authorised humans actually using the capability correctly in real operations? |
| **DATA / MEASUREMENT** | Can Wolf observe trustworthy outcomes, compare them and learn? |
| **FOUNDER INDEPENDENCE** | Can operations function without accidental Matt dependency while preserving intentional owner authority? |
| **FINANCIAL CONTROL** | Can management trust the relevant cash, accounting, profitability, budgets, forecasts and financial controls? |
| **SALE READINESS** | Can a competent buyer understand, inherit and operate the business with appropriate evidence and transitionability? |

Assign evidence to its **primary** dimension. Avoid double counting the same achievement across dials.

---

## 10. Combined TRANSFORMATION %

**NOT APPROVED.**

Owner Cockpit will eventually show six dimensions independently.  
A future composite requires separate explicit Matt approval and a defensible purpose/formula.

Until then: six honest dials beat one fake number.

---

## 11. Current 28%

Unchanged. Legacy: **PARTIAL ESTIMATE / BUILD-TRACKER ESTIMATE** pending explicit scoring migration.  
Do not present 28% as Model C SYSTEM-derived.

---

## 12. Out of scope of this lock

- Calculating current SYSTEM%
- Replacing 28%
- Progress Dashboard changes
- Application code
- Operational DB / Production mutations
- Health scoring implementation
- Model E dimension weights / TRANSFORMATION composite


---

## Numeric maturity credits (LOCKED MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17)

Canonical credits: `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`

| State | Credit |
| --- | ---: |
| ABSENT | 0.00 |
| SPECIFIED | 0.05 |
| BUILT | 0.25 |
| PROVEN | 0.80 |
| READY | 1.00 |

`SYSTEM% = SUM(credits) / 77 × 100` (equal weights; LRC only with approved pack).

Official SYSTEM baseline (docs, not dashboard): `docs/deliveries/MODEL-C-SYSTEM-BASELINE-OFFICIAL-2026-09-17.md`.  
Displayed Progress **28%** remains legacy until separate dashboard migration approve.

