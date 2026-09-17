# GROK PLAN — Progress Dashboard v2.1 semantic correction — 2026-09-17

**Factory:** `BF-progress-dashboard-v21-20260917`  
**Do NOT redesign.** Fix projection/semantics. Keep visual direction.

## MUST decisions
1. **Remove misleading hero aggregate chip COUNTS** (BUILT 15 / HUMAN TESTING 15 / WAITING 15 / POLICY 77). Categories overlap and POLICY is inflated. Replace Empire legend with **status vocabulary chips without fake exclusive counts** (or omit counts entirely). Keep honesty tooltips under HOW CALCULATED.
2. **Fix `waiting_class_for`:** SPECIFIED/IDEA/APPROVED → `PLANNED` (not UNAPPROVED_POLICY). `UNAPPROVED_POLICY` only from **explicit curated policy decisions** (overlay `policy_decisions[]` or vertical flags like Uma variance).
3. **Human commissioning missions = curated evidence list only** — not every built Core row:
   - Habitat content → Haikal/Amanda (WAITING ON OTHERS)
   - Uma Blu Daily Close → verified closer (WAITING ON OTHERS)
   - Progress Dashboard → Matt UX commissioning ACTIVE NOW (NEEDS YOU)
4. **Remove** pulse/moves inventing Matt Core governance commission queue.
5. **Add Empire sections:** NEEDS YOU · WAITING ON OTHERS · POLICY DECISIONS (individual cards, not a giant count). Desired NEEDS YOU empty = success (except active Progress retest while iterating).
6. **Move builder noise** (progress_type, CSV staleness, overlay required, why-vs-prior orange banner) into HOW CALCULATED / history only.
7. **Owner phase copy** natural English derived from truth (foundations + first GGV/BZG workflows; commissioning underway; AMG/company ops ahead).
8. **Keep 28%** unless scoring inputs change. Document denominator 92 by domain in HOW CALCULATED / audit, not Empire hero.
9. Tests for: no SPECIFIED→POLICY; no Core Matt commission fake; needs_you / waiting_others / policy_decisions shapes; deployed-route prove; beta_restart.

## Files
`scripts/core/progress_read_model.py`, `state/progress/v1_overlay.json`, `dashboards/progress.html`, `docs/canon/PROGRESS-DASHBOARD.md`, tests.

## Forbidden
Production · Metricool/ESB · Habitat workflow mutate · invent Matt work · fake precision · mark HUMAN COMMISSIONED
