# RULE — Credit Conservation Mode (2026-09-23)

**Owner lock:** Matthew Goss · **Armed:** 23 Sep 2026 WITA · **Governor:** Peaches

## Intent
Slow Cursor/Grok credit burn. Do **not** stop the factory. Optimize **operational capability gained per credit**, not packs completed per day.

## Finish then conserve
1. Let in-flight **MSC Compliance operator depth** (`BF-msc-compliance-operator-depth-20260923`) finish.
2. Then enforce this mode for all new heavy packs.

## Stop auto-breadth
Do **not** automatically build broad operator-depth / management-depth / connective packs merely because eligible CR work exists.

## Priority (highest first)
1. P0/P1 defects
2. Founder-dependency removal
3. Human commissioning feedback fixes
4. Existing capability → real data
5. Existing capability → integration
6. Existing capability → deployed proof
7. Existing capability → staff-ready
8. CR closure
9. Only then new breadth

## Credit gate (before any paid/heavy Cursor or Grok)
Must materially move an existing capability toward **PROVEN / READY / HUMAN COMMISSIONED / LIVE-ADOPTED**, or remove a material blocker / founder dependency.  
If not → **PARK** unless genuine P0/P1.  
Veto code: `PEACHES_VETO_CREDIT_CONSERVATION`.

## Prefer free/local
Audits, registries, indexing, documentation, test analysis, evidence reconciliation, prioritisation, stale-state detection, commissioning preparation.

## Cadence
- One heavy engineering pack at a time.
- No automatic chain of speculative operator-depth packs.
- After each heavy pack, recompute highest-value next action.
- **Idle is acceptable** when the only eligible work is low-value credit-heavy expansion.
- This **supersedes** the prior rule that eligible safe work means idle is always a defect.

## Do not freeze
Continue low-cost/local work, human commissioning, cheap NAS indexing/discovery, evidence/truth reconciliation, autonomous recovery architecture, genuine defects.  
No paid on-demand. No production mutation.

## Human gates (preserve — higher value than empty desks)
Global Navigation Owner · Haikal NAS · Smart Upload retest · Devi BZG · Amanda GGV · AMG operator commissioning

## Honesty
SPECIFIED stays SPECIFIED. BUILT stays BUILT until proven. Empty framework ≠ operating capability. PASS count ≠ business value. Do not game maturity to justify spend.

## State flag
`state/build-factory/CREDIT-CONSERVATION.json` — `enabled: true`
