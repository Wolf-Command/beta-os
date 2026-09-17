# CURSOR MISSION — Progress v2.1 semantic correction

Implement `docs/deliveries/GROK-PLAN-PROGRESS-DASHBOARD-V21-2026-09-17.md` + audit `docs/deliveries/PROGRESS-V21-SEMANTIC-AUDIT-2026-09-17.md`.

Workspace `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`. Beta only.

### Code
1. Fix `waiting_class_for`: SPECIFIED/IDEA/APPROVED → PLANNED; never auto-map to UNAPPROVED_POLICY.
2. Overlay `policy_decisions[]` — seed Uma variance threshold (+ optional Knowledge Resolution as Owner decision). Empire shows **individual** policy cards.
3. Curated `commissioning_missions[]` / needs_you / waiting_on_others — Habitat staff, Uma closer, Progress Matt ACTIVE. **Delete** Matt Core governance commission pulse/move.
4. Remove hero chip counts (or legend without counts). Keep BUILT≠COMMISSIONED≠LIVE in HOW CALCULATED.
5. Hide builder noise + why-vs-prior from Empire hero.
6. Rewrite owner_phase copy to natural English.
7. Tests + `beta_restart.py` + `prove_deployed_ui_routes.py` PASS.
8. Commit `fix(progress): v2.1 semantic owner status — kill fake policy/Matt queues`
9. Print CURSOR_DONE + tests + prove.

Preserve dirty-tree Phase2.6 WIP / Habitat discovery docs.
