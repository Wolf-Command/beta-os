# GROK PLAN — Sprint2 P5 Owner Disappear + Continuous Pack Gen — 2026-09-22

- Bound: `beta-factory-packgen-safe`
- **Primary defect:** after Sprint1 A–F, factory IDLE needing Matt/Grok to invent next bound.
- Build `scripts/build-factory/bf_pack_generate.py` (+ tests):
  1. Read OPEN CR NEEDS_ENGINEERING (exclude FIN/HR/Trading reserved)
  2. Read approved architecture / Master Spec pointers / dependency graph
  3. Cluster coherent related safe work into one vertical pack plan markdown
  4. Safety validation (no money/CF/prod/external write/fake maturity)
  5. Write plan under `docs/deliveries/` + propose lane JSON for mission
  6. Peaches veto gate file `state/build-factory/PACK-PROPOSAL-LATEST.json` (auto-accept only if `safety_ok` and bound known)
- Classify founder dependencies found in CR/flows: ELIMINATE / AUTOMATE / AUGMENT / SIMPLIFY / RETAIN — implement only safe E/A/A as read-models + routing (no invent Owner controls away).
- Minimal serve_beta touch; prefer factory scripts only so this runs **parallel** to P1.
- Tests prove: generator produces pack from fixture CR without Matt; refuses reserved domains; refuses unknown policy requirements (block branch, continue elsewhere).
- EXIT with proof. No Production.
