# PROGRESS V2.1 SEMANTIC AUDIT — 2026-09-17

## Chip sources (deterministic)

| Chip | Count | Exact calc in `_status_chips` / `waiting_class_for` |
|------|------:|-----------------------------------------------------|
| BUILT | 15 | `sum(built)` — lifecycle SCHEMA_BUILT/BETA/TESTED/… with built=True |
| HUMAN TESTING | 15 | `built and not commissioned and not live` — **same 15** |
| LIVE | 0 | `live` |
| WAITING | 15 | `waiting_class in (WAITING_HUMAN, BLOCKED_SYSTEM)` — **same 15** via `waiting_class_for` on BUILDING/SCHEMA_BUILT/BETA/TESTED + commission≠DONE |
| POLICY NEEDED | 77 | `waiting_class == UNAPPROVED_POLICY` where `waiting_class_for` maps **every SPECIFIED/APPROVED/IDEA** to UNAPPROVED_POLICY |

## Defects
1. **POLICY inflation:** 61/77 are Sale Readiness SPECIFIED rows. Plus Core/Integrations “not built yet” (HR, Procurement, SOP Factory, …). Label implies 77 human policy decisions. **FALSE.**
2. **Double-count chips:** BUILT ≈ HUMAN TESTING ≈ WAITING (15) displayed as if exclusive.
3. **Fake Matt Core queue:** pulse/moves invent “Matt human commission of built Core governance slices” / “Commission Core governance”. Core is proven through verticals. **No approved Matt-per-primitive commission mission.**
4. **Missing real Matt need:** Progress Dashboard UX commissioning (ACTIVE NOW) not listed as NEEDS YOU.
5. **Missing Habitat waiting-on-others:** Haikal/Amanda commissioning not clear vs Core Matt queue.
6. **Builder noise on Empire:** `progress_type`, CSV staleness, overlay, “Why vs prior ~27%” in hero.

## Genuine (evidence)
- NEEDS MATT NOW: Progress Dashboard UX commissioning (this retest).
- WAITING ON OTHERS: Habitat → Haikal/Amanda; Uma Blu → verified closer.
- UNAPPROVED POLICY (real): Uma Blu cash variance threshold. (Authorised Knowledge Resolution = rule approval — Owner decision, list as policy/decision if retained.)

## Denominator (unchanged for mission %)
Core 18 · GGV 3 · BZG 2 · AMG 1 · Intelligence 2 · Integrations 5 · Sale Readiness 61 · **total 92** tracked capabilities. Overall **28%** PARTIAL ESTIMATE — do not change unless scoring inputs change.
