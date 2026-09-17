# CURSOR MISSION — Progress Dashboard v2 Owner Cockpit — 2026-09-17

Read and implement `docs/deliveries/GROK-PLAN-PROGRESS-DASHBOARD-V2-2026-09-17.md` exactly.

Workspace: `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`. Beta only.

## Must ship
1. **Scoring:** Remove Factory health from mission weighted %. Separate `factory_health.status` ∈ {HEALTHY,DEGRADED,FAILING}. Renormalize weights. Update calculation English + canon.
2. **Read-model API:** Empire payload includes `owner_phase` (derived), `status_chips`, `owner_pulse`, `next_moves` (≤3 with class), `recent_wins`, `milestone_road`, domain `plain_phase` + `biggest_gap` + `visual_pct`. Hide raw IDs in owner fields; keep in `technical_details`.
3. **UI:** Rewrite Empire viewport in `dashboards/progress.html` — Owner Cockpit hierarchy; progress bars on domain cards; progressive disclosure; mobile-first; keep dark/gold Wolf look. Move engineering noise to DETAILS/SOURCE/HOW CALCULATED/BUILD FACTORY panels.
4. **Honesty preserved:** BUILT≠COMMISSIONED≠LIVE; WAITING≠BLOCKED; ESTIMATE labelled.
5. **Tests** updated for new fields + factory excluded from mission %.
6. `python3 scripts/beta_restart.py` then `python3 scripts/prove_deployed_ui_routes.py` MUST PASS.
7. Commit: `feat(progress): Owner Cockpit v2 — factory health split + Empire UX`
8. Print CURSOR_DONE + git log -1 + test counts.

Preserve dirty-tree Phase2.6 WIP and Habitat discovery docs — do not delete/reset.

When done print CURSOR_DONE.
